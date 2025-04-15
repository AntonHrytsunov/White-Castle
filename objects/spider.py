import pygame
import os
import random
import logging
from utils.resource_loader import resource_path

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Spider:

    _frame_cache = {}  # Ключ: (animation, scale, scale_x, scale_y) => value: [Surface, ...]
    _sound_cache = {}

    # 🔧 Основні параметри анімації та поведінки
    FRAME_DELAY = 50  # ⏱️ Затримка між кадрами анімації в мілісекундах (загальна швидкість анімацій)
    WALK_SPEED = 3  # 🚶 Базова швидкість ходьби (пікс/кадр)
    AGGRO_SPEED_INITIAL = 2  # 😡 Початкова швидкість при вході в агресивний режим (пікс/кадр)
    AGGRO_ACCELERATION = 0.01  # 🔼 Прискорення у агресивному режимі (пікс/кадр²)
    AGGRO_SPEED_MAX = 3.5  # 🚀 Максимальна швидкість пересування в режимі агресії (пікс/кадр)
    AGGRO_DISTANCE = 500  # 👀 Відстань, з якої павук "бачить" гравця та активується (пікселі)
    STOP_DISTANCE = 200  # ⛔ Павук зупиняється на цій відстані від гравця перед атакою (пікселі)
    AGGRO_PAUSE_DURATION = 200  # ⏸️ Пауза перед тим, як почати переслідування після агресії (мс)

    # 🤖 Поведінка при блужданні (рандомна ходьба, коли неактивний)
    WALK_PROBABILITY = 0.6  # 🎲 Ймовірність того, що павук вирішить піти у випадковий напрямок
    WALK_DECISION_INTERVAL = (2000, 5000)  # 🧠 Інтервал часу між рішеннями (мс)
    WALK_DURATION_RANGE = (1000, 2000)  # 🕓 Тривалість однієї прогулянки, якщо вибрано рух (мс)

    # 🐞 Поведінка при агресії (випадкові зупинки під час переслідування)
    AGGRO_STOP_PROBABILITY = 0.01  # ❓ Ймовірність зробити паузу під час агресивного руху (кожен кадр)
    AGGRO_STOP_MIN_DURATION = 500  # 🛑 Мінімальна тривалість такої зупинки (мс)
    AGGRO_STOP_MAX_DURATION = 1000  # 🛑 Максимальна тривалість зупинки (мс)

    # 🦘 Стрибок
    JUMP_PAUSE_DURATION = random.randint(300, 600)  # ⏱️ Пауза після завершення стрибка перед новими діями (мс)
    JUMP_GRAVITY = 1700  # 🌍 Гравітація під час стрибка — наскільки швидко павук "падає" (пікс/с²)

    # 🦘 Поведінка при великій дистанції (іноді стрибає, іноді просто йде)
    FAR_JUMP_PROBABILITY = 0.1  # Ймовірність стрибка, якщо гравець далеко
    FAR_JUMP_CHECK_INTERVAL = (2000, 3500)  # Інтервал між перевірками стрибка

    def __init__(self, x, y, audio_manager, scale_x=1.0, scale_y=1.0, scale=None):
        self.audio_manager = audio_manager
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.x = x
        self.y = y
        self.scale = scale if scale is not None else random.uniform(0.5, 1.3)
        self.flipped = random.choice([True, False])
        self.manager = None

        # 🎞️ Завантаження анімацій
        self.stay_frames = self.load_frames("stay")
        self.walk_frames_original = self.load_frames("walk")
        self.walk_frames = self.walk_frames_original.copy()
        self.attack_frames_original = self.load_frames("atack")
        self.attack_frames = self.attack_frames_original.copy()
        self.jump_frames_original = self.load_frames("jump")
        self.jump_frames = self.jump_frames_original.copy()
        self.dead_frames = self.load_frames("dead")

        # 🧠 Стани анімації
        self.current_frame = 0
        self.frame_timer = 0
        self.frame_delay = self.FRAME_DELAY

        # 🚶 Ходьба
        self.walking = False
        self.walk_direction = 0
        self.walk_elapsed = 0
        self.walk_duration = 0
        self.walk_timer = 0
        self.next_walk_decision = random.randint(*self.WALK_DECISION_INTERVAL)
        self.walk_speed = self.WALK_SPEED / (0.5 + self.scale / 2)

        # 😡 Агресія
        self.aggro = False
        self.aggro_wait_timer = 0
        self.aggro_paused = False
        self.aggro_stopping = False
        self.aggro_stop_timer = 0
        self.aggro_stop_duration = 0

        scale_modifier = 0.7 + self.scale / 8
        self.aggro_current_speed = self.AGGRO_SPEED_INITIAL / scale_modifier
        self.aggro_speed_max_scaled = self.AGGRO_SPEED_MAX / scale_modifier
        self.aggro_acceleration_scaled = self.AGGRO_ACCELERATION / scale_modifier

        # 🦘 Стрибок
        self.jumping = False
        self.jumping_non_attack = False
        self.jump_animation_done = False
        self.jump_vx = 0
        self.jump_vy = 0
        self.jump_gravity = self.JUMP_GRAVITY
        self.jump_target_x = 0
        self.jump_start_y = 0
        self.after_jump_pause = False
        self.after_jump_timer = 0
        self.jump_total_dx = 0
        self.jump_travelled_dx = 0
        self.has_attacked_this_jump = False
        self.attack_count = 0

        self.far_jump_check_timer = 0
        self.far_jump_check_cooldown = random.randint(*Spider.FAR_JUMP_CHECK_INTERVAL)

        # Смерть
        self.dead = False
        self.dead_animation_done = False
        self.ground_y = self.y
        self.fade_alpha = 255  # Початкова повна непрозорість
        self.fade_out_started = False
        self.fade_timer = 0
        self.fade_duration = 2000  # Тривалість затухання в мілісекундах (2 секунди)

        # 🎵 Аудіо
        vol = self.audio_manager.sound_volume

        walk_sound_file = os.path.join("assets", "level_1", "spider", "walk", "Spider_walk.mp3")
        self.walk_sound = Spider.load_sound_cached(resource_path(walk_sound_file), vol)

        self.jump_sound_path = resource_path(os.path.join("assets", "level_1", "spider", "jump", "spider_jump.mp3"))
        self.jump_sound = Spider.load_sound_cached(self.jump_sound_path, vol)

        # 🪦 Звук смерті
        death_sound_path = os.path.join("assets", "level_1", "spider", "dead", "dead.mp3")
        self.death_sound = Spider.load_sound_cached(resource_path(death_sound_path), vol)

        self.attack_sounds = []
        attack_sound_folder = resource_path(os.path.join("assets", "level_1", "spider", "atack"))
        for file in os.listdir(attack_sound_folder):
            if file.endswith((".mp3", ".wav", ".ogg")):
                path = os.path.join(attack_sound_folder, file)
                sound = Spider.load_sound_cached(path, volume=vol)
                if sound:
                    self.attack_sounds.append(sound)

        # 🖋️ Шрифт
        self.font = pygame.font.SysFont("Arial", int(20 * self.scale))

        # 🔄 Віддзеркалення
        if self.flipped:
            self.flip_images()

    def load_frames(self, animation_name):
        key = (animation_name, round(self.scale, 2), round(self.scale_x, 2), round(self.scale_y, 2))

        if key in Spider._frame_cache:
            return Spider._frame_cache[key]

        folder = resource_path(os.path.join("assets", "level_1", "spider", animation_name))
        files = sorted(f for f in os.listdir(folder) if f.endswith(".png"))
        frames = []

        for filename in files:
            image = pygame.image.load(os.path.join(folder, filename)).convert_alpha()
            width = int(image.get_width() * self.scale * self.scale_x)
            height = int(image.get_height() * self.scale * self.scale_y)
            scaled = pygame.transform.scale(image, (width, height))
            frames.append(scaled)

        Spider._frame_cache[key] = frames  # Кешуємо
        return frames

    @staticmethod
    def load_sound_cached(path, volume):
        """
        Завантажує звук із кешем, щоб не створювати кілька Sound-обʼєктів для однакового файлу.
        """
        if path in Spider._sound_cache:
            return Spider._sound_cache[path]
        try:
            sound = pygame.mixer.Sound(path)
            Spider._sound_cache[path] = sound
            sound.set_volume(volume)
            return sound
        except Exception as e:
            logger.warning(f"Не вдалося завантажити звук: {path}: {e}")
            return None

    def flip_images(self):
        """
        Віддзеркалює всі основні анімації павука по горизонталі, якщо обрано випадкову орієнтацію.
        Це робить ворога "дивлячись ліворуч" замість праворуч.
        """
        self.stay_frames = [
            pygame.transform.flip(frame, True, False) for frame in self.stay_frames
        ]
        self.walk_frames = [
            pygame.transform.flip(frame, True, False) for frame in self.walk_frames_original
        ]
        self.attack_frames = [
            pygame.transform.flip(frame, True, False) for frame in self.attack_frames_original
        ]
        self.jump_frames = [
            pygame.transform.flip(frame, True, False) for frame in self.jump_frames_original
        ]
        self.dead_frames = [
            pygame.transform.flip(frame, True, False) for frame in self.dead_frames
        ]

    def reload_scaled_frames(self):
        """
        Повторно завантажує та масштабує всі фрейми анімацій павука згідно з поточними масштабами.
        Цей метод корисний при зміні масштабу або параметрів екрану.

        Також виконує перевірку на необхідність горизонтального фліпу після оновлення.
        """

        # 🧍 Стан спокою
        self.stay_frames = self.load_frames("stay")

        # 🚶 Ходьба
        self.walk_frames_original = self.load_frames("walk")
        self.walk_frames = self.walk_frames_original.copy()

        # 🕷️ Атака
        self.attack_frames_original = self.load_frames("atack")
        self.attack_frames = self.attack_frames_original.copy()

        # 🦘 Стрибок
        self.jump_frames_original = self.load_frames("jump")
        self.jump_frames = self.jump_frames_original.copy()

        # 🔁 Якщо павук має бути віддзеркалена — фліпаємо кадри
        if self.flipped:
            self.flip_images()

    def update(self, dt, player_x, world_x, scale_x, scale_y):
        """
        Оновлює стан павука:
        - Масштабує зображення, якщо змінився масштаб екрану
        - Визначає дистанцію до гравця та активує агресію
        - Керує поведінкою: блуканням, агресією, стрибками, атаками, смертю
        - Оновлює звук
        """
        # Якщо павук помер
        if self.dead:
            # Якщо мертвий і ще не торкнувся землі — продовжуємо обробку падіння
            if self.jumping and self.y < self.ground_y:
                self.handle_jump(self.scale_y, player_x)
            self.animate(dt)
            return

        # 🖼️ Оновлення масштабу (якщо змінено масштаб екрана)
        if self.scale_x != scale_x or self.scale_y != scale_y:
            self.scale_x = scale_x
            self.scale_y = scale_y
            self.reload_scaled_frames()

        # ⛔ Якщо немає координат гравця — нічого не робимо
        if player_x is None:
            return

        # 📏 Визначення дистанції до гравця (по центру павука)
        spider_center_x = self.x + self.walk_frames[0].get_width() // 2
        distance = abs(spider_center_x - player_x)

        # 😡 Перехід у стан агресії
        if not self.aggro and distance <= self.AGGRO_DISTANCE:
            self.aggro = True
            self.aggro_paused = True  # Невелика пауза перед активною поведінкою
            self.aggro_wait_timer = 0
            self.set_walking(False)
            self.walk_direction = 0
            self.aggro_current_speed = self.AGGRO_SPEED_INITIAL

        # 🚶 Режим випадкового блукання, якщо не агресивний
        if not self.aggro:
            self.handle_random_walk(dt, player_x)
            return

        # ⏸️ Пауза перед початком агресивної дії
        if self.aggro_paused:
            self.set_walking(False)
            self.aggro_wait_timer += dt
            if self.aggro_wait_timer >= self.AGGRO_PAUSE_DURATION:
                self.aggro_paused = False
                self.set_walking(True)
            return

        # 🦘 Якщо гравець далеко — іноді стрибає, іноді просто йде
        if self.aggro and not self.jumping and not self.after_jump_pause:
            if distance >= 600:
                self.far_jump_check_timer += dt
                if self.far_jump_check_timer >= self.far_jump_check_cooldown:
                    self.far_jump_check_timer = 0
                    self.far_jump_check_cooldown = random.randint(*Spider.FAR_JUMP_CHECK_INTERVAL)

                    if random.random() < Spider.FAR_JUMP_PROBABILITY:
                        self.set_walking(False)
                        self.walk_direction = 0
                        self.start_directional_jump(player_x)
                        return

        # 🛫 Стрибок у процесі — оновлюємо тільки рух
        if self.jumping:
            self.handle_jump(world_x, player_x)
            self.animate(dt)
            return

        # 🕒 Пауза після стрибка — чекаємо, не рухаємось
        if self.after_jump_pause:
            self.after_jump_timer += dt
            if self.after_jump_timer >= self.JUMP_PAUSE_DURATION:
                self.after_jump_pause = False
            return

        # ⚔️ Поведінка у режимі агресії: наближення, атака тощо
        self.handle_aggro_attack(dt, player_x, world_x)

        # 🔁 Якщо під час атаки почався стрибок — оновлюємо його
        if self.jumping:
            self.handle_jump(world_x, player_x)
            self.animate(dt)
            return

        # 🔉 Зменшення гучності кроків залежно від відстані
        self.update_sound_volume_by_distance(self.walk_sound, distance)

    def handle_random_walk(self, dt, player_x):
        """
        Випадкове блукання павука:
        - Час від часу павук вирішує почати рух у випадковому напрямку
        - Рух триває задану кількість часу
        - Після цього павук зупиняється й чекає наступного рішення
        """
        self.walk_timer += dt  # ⏱️ Час, що минув з останнього рішення
        distance = abs(self.x - player_x)
        self.update_sound_volume_by_distance(self.walk_sound, distance)

        if self.dead:
            return

        if self.walking:
            # 🚶 Активний рух: оновлюємо позицію та перевіряємо тривалість
            self.walk_elapsed += dt
            self.x += self.walk_direction * self.walk_speed

            # 🛑 Час руху вичерпано — зупиняємося
            if self.walk_elapsed >= self.walk_duration:
                self.set_walking(False)
                self.walk_timer = 0
                self.walk_direction = 0
                # Встановлюємо, коли наступного разу буде прийнято рішення про рух
                self.next_walk_decision = random.randint(*self.WALK_DECISION_INTERVAL)

        else:
            # 🧠 Час ухвалювати нове рішення?
            if self.walk_timer >= self.next_walk_decision:
                if random.random() < self.WALK_PROBABILITY:
                    # ✅ Починаємо нову прогулянку
                    self.set_walking(True)
                    self.walk_elapsed = 0
                    self.walk_duration = random.randint(*self.WALK_DURATION_RANGE)
                    self.walk_direction = random.choice([-1, 1])

                    # 🔄 Фліпаємо зображення, якщо рухаємося вправо
                    self.flipped = self.walk_direction == 1
                    self.walk_frames = [
                        pygame.transform.flip(f, True, False) for f in self.walk_frames_original
                    ] if self.flipped else self.walk_frames_original

                # Перезапускаємо таймер незалежно від того, вирішили йти чи ні
                self.walk_timer = 0
                self.next_walk_decision = random.randint(*self.WALK_DECISION_INTERVAL)

        # 🎞️ Оновлюємо кадр анімації
        self.animate(dt)

    def handle_aggro_attack(self, dt, player_x, world_x):
        """
        Поведінка павука в агресивному режимі:
        - Прискорене наближення до гравця
        - Випадкові зупинки для природнішої поведінки
        - Ініціація стрибкової атаки при достатньому наближенні
        """

        if self.dead:
            return

        # ⛔ Якщо павук зараз стрибає або у післястрибковій паузі — не атакує
        if self.jumping or self.after_jump_pause:
            return

        # 🐞 Імітація пауз у пересуванні (іноді павук "стопиться")
        if self.aggro_stopping:
            self.set_walking(False)
            self.aggro_stop_timer += dt
            if self.aggro_stop_timer >= self.aggro_stop_duration:
                # Зупинка завершена — відновлюємо переслідування
                self.aggro_stopping = False
                self.aggro_stop_timer = 0
            return

        # 📏 Обчислення позиції та напрямку до гравця
        spider_center_x = self.x + self.walk_frames[0].get_width() // 2

        # Стоп-дистанція — павук не підходить впритул, зупиняється на відстані
        spider_center_x = self.x + self.walk_frames[0].get_width() // 2
        target_x = player_x - self.STOP_DISTANCE*self.scale if spider_center_x < player_x else player_x + self.STOP_DISTANCE*self.scale
        self.flipped = spider_center_x < player_x
        direction = 1 if target_x > spider_center_x else -1

        # 🚀 Прискорення (аж поки не досягне максимального)
        if self.aggro_current_speed < self.aggro_speed_max_scaled:
            self.aggro_current_speed += self.AGGRO_ACCELERATION / self.scale
            self.aggro_current_speed = min(self.aggro_current_speed, self.aggro_speed_max_scaled)

        # ➡️ Завжди пересуваємось із урахуванням dt
        self.x += direction * self.aggro_current_speed

        # ➡️ Пересування в напрямку до цільової позиції
        if self.aggro_current_speed < self.AGGRO_SPEED_MAX:
            self.x += direction * self.aggro_current_speed
        else:
            self.x += direction * self.aggro_current_speed

        # 🐜 Випадкова зупинка — симуляція непередбачуваної поведінки
        if random.random() < self.AGGRO_STOP_PROBABILITY:
            self.aggro_stopping = True
            self.aggro_stop_duration = random.randint(
                self.AGGRO_STOP_MIN_DURATION,
                self.AGGRO_STOP_MAX_DURATION
            )
            self.aggro_stop_timer = 0
            return

        # 🐾 Анімація ходьби + правильне відображення (фліп або ні)
        self.set_walking(True)
        self.walk_direction = direction
        if self.flipped:
            self.flip_images()
        else:
            self.walk_frames = self.walk_frames_original
            self.stay_frames = self.load_frames("stay")  # оновлення фреймів у нефліпнутому вигляді

        # 🦘 Початок атаки, якщо підійшов досить близько
        if abs(spider_center_x - target_x) <= 15:
            self.set_walking(False)
            self.walk_direction = 0
            self.start_jump_attack(player_x)

        # 🎞️ Оновлення кадру анімації
        self.animate(dt)

    def start_jump_attack(self, player_x):
        """
        Ініціює стрибкову атаку павука в напрямку гравця.
        Встановлює параметри стрибка, обчислює напрям і швидкість, готує анімацію та звук.
        """

        if self.dead:
            self.ground_y = self.y
            return

        # 🎯 Активуємо стан стрибка
        self.jumping = True
        self.jumping_non_attack = False  # Це — атакувальний стрибок
        self.current_frame = 0

        # 📍 Позиція на старті
        self.jump_start_y = self.y
        self.jump_target_x = player_x

        # 📏 Обчислюємо відстань до гравця по X та фіксовану висоту стрибка по Y
        dx = player_x - (self.x + self.walk_frames[0].get_width() // 2)
        dy = -150  # вершина дуги (від'ємне значення — вгору)

        # 🔒 Обмежуємо дистанцію стрибка, щоб не перелітати за межі
        total_distance = max(-600, min(dx, 600))
        min_distance = 100 * self.scale
        if 0 < total_distance < min_distance:
            total_distance = min_distance
        elif -min_distance < total_distance < 0:
            total_distance = -min_distance

        # ⚙️ Встановлюємо параметри руху
        self.jump_total_dx = total_distance
        self.jump_travelled_dx = 0
        self.jump_vx = total_distance / 27  # горизонтальна швидкість (фіксовано ~30 кадрів)
        self.jump_vy = 2 * dy / 40  # вертикальна швидкість для імітації дуги

        # 🔄 Встановлення напрямку та фліп кадрів стрибка
        self.flipped = dx > 0
        self.jump_frames = (
            [pygame.transform.flip(f, True, False) for f in self.jump_frames_original]
            if self.flipped else self.jump_frames_original.copy()
        )

        # 🔉 Відтворення звуків атаки зі зниженням гучності залежно від дистанції
        distance = abs(self.x - player_x)
        self.update_sound_volume_by_distance(self.jump_sound, distance)
        if self.attack_sounds:
            attack_sound = random.choice(self.attack_sounds)
            self.update_sound_volume_by_distance(attack_sound, distance)
            attack_sound.play()
            if self.manager:
                self.manager.active_sounds.append(attack_sound)

    def start_directional_jump(self, player_x):
        """
        Ініціює неатакувальний (переміщувальний) стрибок павука у напрямку до гравця.
        Використовується, коли гравець знаходиться на великій відстані.
        """

        if self.dead:
            return

        # 🚀 Вмикаємо режим стрибка
        self.jumping = True
        self.jumping_non_attack = True  # Це не атака, лише стрибок у напрямку
        self.current_frame = 0

        # 🎯 Встановлюємо координати старту і цілі
        self.jump_start_y = self.y
        self.jump_target_x = player_x

        # 📏 Обчислення горизонтального зміщення
        dx = player_x - (self.x + self.walk_frames[0].get_width() // 2)

        # 🎯 Випадкова висота дуги стрибка (щоб виглядало природніше)
        dy = random.randint(-130, -110)

        # 🔒 Обмеження максимальної відстані стрибка (вліво або вправо)
        total_distance = max(-600, min(dx, 600))

        # ⚙️ Параметри польоту
        self.jump_total_dx = total_distance
        self.jump_travelled_dx = 0
        self.jump_vx = total_distance / 40  # трохи повільніший, ніж у бойовому стрибку
        self.jump_vy = 2 * dy / 40  # вертикальна складова — дуга

        # 🔄 Орієнтація павука
        self.flipped = dx > 0
        self.jump_frames = (
            [pygame.transform.flip(f, True, False) for f in self.jump_frames_original]
            if self.flipped else self.jump_frames_original
        )

        # 🎞️ Скидаємо стан анімації
        self.jump_animation_done = False

        # 🔉 Звук стрибка
        distance = abs(self.x - player_x)
        self.update_sound_volume_by_distance(self.jump_sound, distance)
        self.jump_sound.play()
        if self.manager:
            self.manager.active_sounds.append(self.jump_sound)

    def handle_jump(self, scale_y, player_x):
        """
        Оновлює координати павука під час стрибка.
        Застосовує гравітацію, перевіряє атаку під час стрибка та завершення польоту.
        """

        if self.dead and not self.jumping:
            return

        # 🔁 Якщо мертвий, але ще не приземлився — дозволяємо падати
        if self.dead and self.y >= self.ground_y:
            self.jumping = False
            self.y = self.ground_y
            return

        self.scale_y = scale_y

        # ⛅ Рух по X і Y
        self.x += self.jump_vx
        self.y += self.jump_vy
        self.jump_travelled_dx += abs(self.jump_vx)

        # ⬇️ Гравітація (імітація дуги польоту)
        FRAME_TIME = 1 / 60  # 60 FPS
        self.jump_vy += self.jump_gravity * FRAME_TIME ** 2

        # 🗡️ Атака під час стрибка (одноразова)
        if not self.has_attacked_this_jump and not self.jumping_non_attack:
            spider_center_x = self.x + self.get_current_frames()[self.current_frame].get_width() // 2
            distance_to_player = abs(spider_center_x - player_x)

            if distance_to_player < 30 * self.scale_x * self.scale:
                self.has_attacked_this_jump = True
                self.attack_count += 1

                if self.manager:
                    self.manager.damage_player(int(10 * self.scale))  # Урон залежить від розміру

            if self.attack_count >= 5:
                self.die()

        # 🛬 Завершення стрибка (павук торкнувся землі)
        if self.y >= self.ground_y:
            self.y = self.ground_y
            self.jumping = False
            self.jumping_non_attack = False
            self.has_attacked_this_jump = False
            self.current_frame = 0

            # ⏸️ Післястрибкова пауза перед відновленням активності
            self.after_jump_pause = True
            self.after_jump_timer = 0
            self.aggro_paused = False

    def die(self):
        """
        Запускає процес смерті павука:
        - Встановлює стан `dead`
        - Зупиняє ходьбу, агресію, стрибки
        - Скидає кадри анімації
        """
        if self.dead:
            return  # Уже мертвий

        logger.info("[Spider] Павук загинув.")
        self.dead = True
        self.dead_animation_done = False
        self.set_walking(False)
        self.aggro = False
        self.aggro_paused = False
        self.jumping_non_attack = False
        self.after_jump_pause = False
        self.current_frame = 0
        self.frame_timer = 0
        # 🔉 Відтворення звуку смерті
        if self.death_sound:
            self.update_sound_volume_by_distance(self.death_sound, 0)  # Максимальна гучність
            self.death_sound.play()
            if self.manager:
                self.manager.active_sounds.append(self.death_sound)

    def animate(self, dt):
        """
        Оновлює кадр анімації залежно від часу.
        """
        self.frame_timer += dt
        frames = self.get_current_frames()

        if self.dead:
            if self.current_frame < len(frames) - 1:
                # 🎞️ Основна анімація смерті
                if self.frame_timer >= self.frame_delay:
                    self.frame_timer = 0
                    self.current_frame += 1
            else:
                # ✅ Основна смерть завершена — запускаємо "хаотичне здригання"
                self.dead_animation_done = True

                if not hasattr(self, "_death_twitch_timer"):
                    self._death_twitch_timer = 0
                    self._death_twitch_delay = 200
                    self._death_twitch_time = 0

                self._death_twitch_time += dt

                if self._death_twitch_time >= 5000:
                    self.current_frame = len(frames) - 1
                    # ⬇️ Починаємо зникнення
                    if not self.fade_out_started:
                        self.fade_out_started = True
                        self.fade_timer = 0

                else:
                    self._death_twitch_timer += dt
                    base_delay = 200
                    growth = 0.0017
                    decay_factor = 1 + growth * self._death_twitch_time
                    adjusted_delay = int(base_delay * decay_factor)

                    if self._death_twitch_timer >= self._death_twitch_delay:
                        self._death_twitch_timer = 0
                        self._death_twitch_delay = random.randint(adjusted_delay, adjusted_delay + 500)
                        self.current_frame = random.choice([
                            len(frames) - 1,
                            len(frames) - 2,
                            len(frames) - 3
                        ])

        # ⬇️ fade-out працює незалежно від "twitch"
        if self.dead_animation_done:
            spider_center_x = self.x + self.get_current_frames()[self.current_frame].get_width() // 2
            distance = abs(spider_center_x - self.manager.player_x if self.manager else 0)

            if distance > 500:
                if not self.fade_out_started:
                    self.fade_out_started = True
                    self.fade_timer = 0
                else:
                    self.fade_timer += dt
                    progress = self.fade_timer / self.fade_duration
                    self.fade_alpha = max(0, int(255 * (1 - progress)))

        # 🔁 Інші анімації
        elif not self.dead:
            if self.frame_timer >= self.frame_delay:
                self.frame_timer = 0

                if self.jumping:
                    if self.current_frame < len(frames) - 1:
                        self.current_frame += 1
                    else:
                        self.jump_animation_done = True
                else:
                    self.current_frame = (self.current_frame + 1) % len(frames)

    def draw(self, screen, world_x):
        frames = self.get_current_frames()
        if not frames:
            logger.warning("[Spider] Немає кадрів для поточного стану — пропуск промальовки.")
            return

        if self.current_frame >= len(frames):
            logger.warning(f"[Spider] Поточний кадр {self.current_frame} > {len(frames) - 1} — обнуляємо.")
            self.current_frame = 0

        current_image = frames[self.current_frame]
        screen_x = int(self.x - world_x)
        screen_y = int(self.y - current_image.get_height())

        image_with_alpha = current_image.copy()
        image_with_alpha.set_alpha(self.fade_alpha)

        screen.blit(image_with_alpha, (screen_x, screen_y))

        if self.fade_alpha > 0:
            attack_text = self.font.render(f"Atk: {self.attack_count}", True, (255, 255, 255))
            screen.blit(attack_text, (screen_x, screen_y - 20))

    def set_walking(self, walking: bool):
        """
        Встановлює стан ходьби павука:
        - скидає анімацію, якщо стан змінено
        - вмикає або вимикає звук кроків
        """
        # 🔄 Якщо стан змінився — скидаємо кадр анімації
        if self.walking != walking:
            self.current_frame = 0
        self.walking = walking

        # 🎵 Керуємо звуком кроків
        channel = getattr(self, "walk_channel", None)

        if walking:
            # 🔊 Запускаємо звук, якщо ще не грає
            if channel is None or not channel.get_busy():
                self.walk_channel = self.walk_sound.play(loops=-1)
                if self.manager:
                    self.manager.active_sounds.append(self.walk_channel)
        else:
            # 🔇 Зупиняємо, якщо йде звук
            if channel and channel.get_busy():
                channel.stop()
                self.walk_channel = None

    def update_sound_volume_by_distance(self, sound, distance):
        """
        Змінює гучність звуку залежно від відстані до гравця.
        Чим далі павук — тим тихіше звук.

        :param sound: pygame.mixer.Sound — об'єкт звуку
        :param distance: float — відстань до гравця
        """
        if not sound:
            return

        # 📏 Налаштування гучності
        MAX_DISTANCE = 1500  # Після цієї межі — звук не чутно
        MIN_VOLUME = 0.1  # Мінімальна гучність при віддаленні
        MAX_VOLUME = 1.0  # Базова гучність поруч

        if distance >= MAX_DISTANCE:
            volume = 0  # 🔇 Зовсім не чутно
        else:
            ratio = distance / MAX_DISTANCE
            # 📉 Плавне затухання (квадратична крива)
            volume = max(MIN_VOLUME, MAX_VOLUME * (1 - ratio) ** 2)
            volume = volume * self.audio_manager.sound_volume

        sound.set_volume(volume)

    def get_current_frames(self):
        """
        Повертає набір кадрів для поточної анімації павука залежно від його стану.
        """
        if self.dead:
            return self.dead_frames
        if self.jumping:
            return self.jump_frames if self.jumping_non_attack else self.attack_frames
        return self.walk_frames if self.walking else self.stay_frames

    def should_be_removed(self, player_x):
        if not self.dead:
            return False

        spider_center_x = self.x + self.get_current_frames()[self.current_frame].get_width() // 2
        distance = abs(spider_center_x - player_x)

        if self.fade_alpha <= 0 and distance > 600:
            return True
        else:
            return False


class SpiderManager:
    """
    Керує всіма об'єктами павуків на рівні:
    - спавн
    - оновлення
    - промальовка
    - скидання
    """
    def __init__(self, screen_height, scale_y, audio_manager, scale_x):
        self.spiders = []
        self.active_sounds = []
        self.screen_height = screen_height
        self.scale_y = scale_y
        self.scale_x = scale_x
        self.audio_manager = audio_manager

    def spawn_initial_spiders(self):
        x_positions = [
            (12000, 0.6),
            (12050, 0.65),
            (12950, 0.55),
            (12100, 0.4),
            (12100, 0.4),
            (12100, 0.4),
            (12100, 0.4),
            (12100, 0.4),
            (12100, 0.4),
            (12500, 1.3),
        ]

        self.spiders = []

        for x, scale in x_positions:
            y_relative = 770*self.scale_y + (scale * 50*self.scale_y)
            y_base = int(y_relative * self.scale_y)

            spider = Spider(
                x=x,
                y=y_base,
                audio_manager=self.audio_manager,
                scale_x=self.scale_x,
                scale_y=self.scale_y,
                scale=scale
            )
            spider.manager = self
            self.spiders.append(spider)

    def update(self, dt, hero_world_x, player_width, scale_y, scale_x, player):
        """
        Оновлює всіх павуків на рівні та видаляє тих, хто мертвий і далеко.
        """
        player_center_x = hero_world_x + player_width // 2
        new_spiders = []
        self.player_x = player_center_x

        for spider in self.spiders:
            spider.update(
                dt=dt,
                player_x=player_center_x,
                world_x=hero_world_x,
                scale_y=scale_y,
                scale_x=scale_x
            )

            # Якщо павука не потрібно видаляти — залишаємо в списку
            if not spider.should_be_removed(player_center_x):
                new_spiders.append(spider)
            else:
                pass

        self.player = player

        self.spiders = new_spiders

    def damage_player(self, amount):
        if hasattr(self, "player") and self.player:
            self.player.hp -= amount
            if self.player.hp < 0:
                self.player.hp = 0
            logging.info(f"[SpiderManager] Гравець отримав {amount} урону. HP: {self.player.hp}")

    def draw(self, screen, world_x):
        """
        Малює всіх павуків на екрані у правильному порядку по Y (для глибини).
        """
        for spider in sorted(self.spiders, key=lambda s: s.y):
            spider.draw(screen, world_x)

    def reset(self):
        """
        Повністю очищає всіх павуків (наприклад, при перезапуску рівня).
        """
        self.spiders.clear()

    def stop_all_sounds(self):
        for sound_or_channel in self.active_sounds:
            try:
                sound_or_channel.stop()
            except Exception as e:
                pass
        self.active_sounds.clear()

