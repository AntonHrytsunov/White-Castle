import pygame
import random
import json
from utils.resource_loader import resource_path
from utils.resource_loader import save_progress
from core.audio_manager import play_random_menu_sound, play_return_sound
from PIL import Image, ImageSequence
import math
import textwrap
import logging


class HeroCreator:
    """
    Перший рівень гри. Містить логіку старту, збереження, оновлення та обробки подій.
    """
    def __init__(self, scene_manager, audio_manager):
        self.name = "HeroCreator"
        self.scene_manager = scene_manager
        self.audio_manager = audio_manager
        self.character_cache = {}  # Кеш готових зображень персонажів
        self.filtered_character_cache = {}
        self.old_character_key = None
        self.character_key = None
        self.screen = None
        self.selected_index = 0
        self.saved_state = {}
        self.audio_file = resource_path("assets/scene/hero_creator/dark_wood.mp3")
        self.music_paused = False
        pygame.mouse.set_visible(False)

        # Завантаження анімації GIF
        self.gif_file = resource_path("assets/scene/hero_creator/dark_wood.gif")
        self.current_frame = 0
        self.animation_direction = 1  # 1 - вперед, -1 - назад
        self.animation_speed = 5  # Кількість оновлень перед зміною кадру
        self.animation_counter = 0

        self.options = {
            "Раса": ["Людина", "Ельф", "Гном", "Звіролюд"],
            "Стать": ["Чоловіча", "Жіноча"],
            "Зовнішність": ["Світла", "Темна"]
        }

        self.current_selection = {
            "Раса": random.randint(0,3),
            "Стать": random.randint(0,1),
            "Зовнішність": random.randint(0,1)
        }

        self.menu_items = list(self.options.keys()) + ["Почати"]

        # Анімаційні змінні для зміни персонажа
        self.character_image = None
        self.old_character_image = None
        self.character_alpha = 0  # Початкова прозорість нового персонажа
        self.old_character_alpha = 255  # Прозорість старого персонажа
        self.character_x = 0  # Початкова позиція нового персонажа
        self.old_character_x = 0  # Початкова позиція старого персонажа
        self.animation_in_progress = False  # Чи відбувається анімація

    def load_resources_with_progress(self):
        """Поступово завантажує ресурси з візуальним прогресбаром."""
        screen = pygame.display.get_surface()
        screen_width, screen_height = screen.get_size()

        loading_steps = [
            ("Завантаження фону...",
             lambda: setattr(self, "frames", self.load_gif_frames(self.gif_file, screen.get_size()))),
            ("Завантаження музики...", lambda: self.audio_manager.play_music(self.audio_file)),
            ("Генерація початкового героя...", self.update_character_image),
        ]

        total_steps = len(loading_steps)
        progress_height = 30
        font = pygame.font.Font(resource_path("assets/menu_font.otf"), 36)

        for i, (text, action) in enumerate(loading_steps):
            action()

            # Очистка екрану
            screen.fill((0, 0, 0))

            # Відображення тексту
            loading_text = font.render(text, True, (200, 200, 200))
            screen.blit(loading_text, (screen_width // 2 - loading_text.get_width() // 2, screen_height // 2 - 60))

            # Прогресбар
            pygame.draw.rect(screen, (60, 60, 60),
                             (screen_width // 4, screen_height // 2, screen_width // 2, progress_height))
            pygame.draw.rect(screen, (180, 180, 255), (
                screen_width // 4, screen_height // 2,
                int((i + 1) / total_steps * screen_width // 2), progress_height))

            pygame.display.flip()
            pygame.time.delay(400)  # Затримка для видимості, можна прибрати

    def get_character_description(self):
        """Повертає художній опис вибраного персонажа."""
        race = self.options["Раса"][self.current_selection["Раса"]]
        gender = self.options["Стать"][self.current_selection["Стать"]]

        descriptions = {
            ("Людина",
             "Чоловіча"): "Високий, з твердим поглядом і шрамами, що свідчать про пережиті битви, він стоїть на роздоріжжі свого шляху. В його очах – відблиск надії й тінь сумнівів, адже людина завжди шукає більше, ніж має. Його руки міцні, а дух – ще міцніший, загартований труднощами життя. Він не володіє чарами крові чи силою предків, але його рішучість сильніша за будь-яке прокляття. Він вірить у власний вибір і творить власну долю – чи то мечем, чи словом.",
            ("Людина",
             "Жіноча"): "Її постава горда, кроки впевнені, а вуста таять у собі загадкову усмішку – вона знає, що світ належить тим, хто не боїться його взяти. В її руках – тонка рівновага між хитрістю і силою, м’якістю і безжальністю. Вона вміє слухати, але її слова мають вагу, що може зрівнятися з вагою сталі. Вона не покладається на долю чи прихильність богів – лише на власний розум і витримку. Її шлях – це історія, що ще не написана, і вона сама вирішує, якою вона буде.",
            ("Ельф",
             "Чоловіча"): "Його рухи легкі, немов вітер, що гуляє верхівками дерев. Очі світяться тисячолітньою мудрістю, а серце сповнене тінню самотності. Його голос нагадує шепіт стародавніх лісів, де час тече інакше. Він не живе поспіхом, але кожен його крок – продуманий, немов хід у великій грі, яку смертні навіть не розуміють. Він несе в собі пам’ять століть і тягар очікувань предків, що ніколи не дозволять йому бути просто воїном чи магом – він повинен бути чимось більшим.",
            ("Ельф",
             "Жіноча"): "Її постать мов виткана з місячного світла, а кожен рух сповнений невимушеної грації. Її очі бачать більше, ніж дозволяє смертне життя – у них відображаються зорі, що вже давно згасли. Вона слухає пісню вітру і розмовляє з тишею. Її слова рідкісні, але кожне – гостре, як клинок. Вона не квапиться діяти, але коли вирішує – її рука не хибить. Вона – спогад про стародавній світ, відлуння чогось вічного, що ніколи не буде забуте.",
            ("Гном",
             "Чоловіча"): "Його сміх гримить, мов удар молота об ковадло, а сам він – наче жива скеля, що нікого не підпускає надто близько. Він не вірить у випадковість – усе, що він має, здобуте потом, кров’ю та працею. Його руки шорсткі від роботи, а серце б’ється у такт із глибинами землі. У світі, сповненому хитких рішень і слабкодухих, він – як непорушна гора. Його вороги знають: коли гном бере до рук зброю, він б’ється не за славу, а за щось значно більше – за родину, честь і свою власну істину.",
            ("Гном",
             "Жіноча"): "Її голос дзвінкий, як срібло, але всередині палає полум’я, гарячіше за лаву. Вона не потребує чиєїсь згоди – вона сама собі господиня. Її руки не знають відпочинку: чи то тримаючи молот, чи майстерно керуючи переговорами, вона завжди досягає свого. Її предки шепочуть їй про старі традиції, але вона створює нові. Хтось бачить у ній лише силу, але мудрі знають: її гострий розум – її справжня зброя. Вона не боїться викликів, бо гноми не з тих, хто відступає.",
            ("Звіролюд",
             "Чоловіча"): "Його дихання – це ритм диких лісів, а тіло – втілення хижої грації. Його очі мерехтять у темряві, вишукуючи найменший рух, і він відчуває світ шкірою, ніби частина чогось більшого. Його інстинкти загострені, а свобода – його єдина справжня релігія. Він не терпить кайданів, ні фізичних, ні невидимих, якими сковує суспільство. Його світ – це полювання, боротьба, виживання, де слабкі залишаються позаду. Його місце там, де вітер несе запах землі, а кров змішується з росою на траві.",
            ("Звіролюд",
             "Жіноча"): "Її хода безшумна, як тінь, а посмішка приховує в собі хижу загадку. Вона – нічний вітер, що проходить крізь дерева, залишаючи за собою лише шепіт. Світ навчив її бути жорсткою, але вона знає: найсильніший той, хто вміє чекати і вибирати правильний момент. Вона рухається між світами, не належачи нікому – ні звірам, ні людям. Вона вільна, як зорі на небі, і ніщо не змусить її стати на коліна. Хто думає, що приручив її, той уже приречений."
        }

        desc = descriptions.get((race, gender), "Невідомий персонаж.")
        return desc

    def apply_night_filter(self, image, key):
        """Застосовує ефект нічного освітлення з кешуванням."""
        if key in self.filtered_character_cache:
            return self.filtered_character_cache[key]

        filtered_image = pygame.Surface(image.get_size(), pygame.SRCALPHA)
        for x in range(image.get_width()):
            for y in range(image.get_height()):
                color = image.get_at((x, y))
                if color.a > 0:
                    r, g, b, a = color
                    r = int(r * 0.5)
                    g = int(g * 0.6)
                    b = int(b * 0.6)
                    filtered_image.set_at((x, y), (r, g, b, int(a * 0.95)))

        self.filtered_character_cache[key] = filtered_image
        return filtered_image

    def update_character_image(self):
        """Оновлює зображення персонажа з кешем."""
        race_map = {"Людина": "human", "Ельф": "elf", "Гном": "dwarf", "Звіролюд": "beast"}
        gender_map = {"Чоловіча": "man", "Жіноча": "girl"}
        appearance_map = {"Темна": "black.png", "Світла": "white.png"}

        selected_race = self.options["Раса"][self.current_selection["Раса"]]
        selected_gender = self.options["Стать"][self.current_selection["Стать"]]
        selected_appearance = self.options["Зовнішність"][self.current_selection["Зовнішність"]]

        key = (selected_race, selected_gender, selected_appearance)
        self.old_character_key = self.character_key  # Зберігаємо попередній ключ
        self.character_key = key  # Зберігаємо новий ключ

        if key in self.character_cache:
            new_character_image = self.character_cache[key]
        else:
            image_path = resource_path(
                f"assets/characters/{race_map[selected_race]}/{gender_map[selected_gender]}/{appearance_map[selected_appearance]}"
            )
            try:
                image = pygame.image.load(image_path).convert_alpha()
                screen_width, screen_height = self.screen.get_size()
                new_height = screen_height // 1.8
                scale_factor = new_height / image.get_height()

                if selected_gender == "Жіноча":
                    scale_factor *= 0.9
                if selected_race == "Гном":
                    scale_factor *= 0.9

                new_width = int(image.get_width() * scale_factor)
                new_height = int(image.get_height() * scale_factor)
                image = pygame.transform.scale(image, (new_width, new_height))

                self.character_cache[key] = image  # Зберігаємо в кеш
                new_character_image = image
            except pygame.error:
                return

        # Анімація як і раніше
        screen_width = self.screen.get_width()
        center_x = (screen_width - new_character_image.get_width()) // 2 + screen_width // 20

        self.old_character_image = self.character_image
        self.old_character_x = center_x
        self.old_character_alpha = 255
        self.character_x = center_x - screen_width // 10
        self.character_alpha = 0
        self.character_image = new_character_image
        self.animation_in_progress = True

    def save(self):
        save_progress("HeroCreator")

    def load_gif_frames(self, gif_path, screen_size):
        """Завантажує та масштабує кадри GIF під розмір екрану."""
        gif = Image.open(gif_path)
        frames = []
        for frame in ImageSequence.Iterator(gif):
            frame = frame.convert("RGBA")  # Конвертація для коректного кольору
            frame = frame.resize(screen_size, Image.Resampling.LANCZOS)  # Масштабування під екран

            # Конвертація у pygame Surface
            frame_surface = pygame.image.fromstring(frame.tobytes(), frame.size, frame.mode).convert()
            frame_surface.set_colorkey((0, 0, 0))  # Встановлюємо чорний як прозорий, щоб уникнути білого мерехтіння
            frames.append(frame_surface)
        return frames

    def save_hero(self):
        from utils.resource_loader import get_save_path
        full_path = get_save_path("progress.json")

        try:
            with open(full_path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}

        data["last_scene"] = "level_1"

        selected_race = self.options["Раса"][self.current_selection["Раса"]]
        selected_gender = self.options["Стать"][self.current_selection["Стать"]]
        selected_appearance = self.options["Зовнішність"][self.current_selection["Зовнішність"]]

        # Базові показники для кожної раси
        stats_by_race = {
            "Людина": {"hp": 100, "mana": 70, "stamina": 80},
            "Ельф": {"hp": 80, "mana": 120, "stamina": 60},
            "Гном": {"hp": 120, "mana": 60, "stamina": 70},
            "Звіролюд": {"hp": 90, "mana": 40, "stamina": 120},
        }

        # Корекція показників за статтю (чоловіки — трохи більше HP, жінки — трохи більше Mana)
        gender_modifiers = {
            "Чоловіча": {"hp": 1.1, "mana": 1.0, "stamina": 1.05},
            "Жіноча": {"hp": 1.0, "mana": 1.1, "stamina": 1.0},
        }

        base_stats = stats_by_race.get(selected_race, {"hp": 100, "mana": 100, "stamina": 100})
        gender_mod = gender_modifiers.get(selected_gender, {"hp": 1.0, "mana": 1.0, "stamina": 1.0})

        final_stats = {
            "HP": int(base_stats["hp"] * gender_mod["hp"]),
            "Mana": int(base_stats["mana"] * gender_mod["mana"]),
            "Stamina": int(base_stats["stamina"] * gender_mod["stamina"])
        }

        data["hero"] = {
            "Раса": selected_race,
            "Стать": selected_gender,
            "Зовнішність": selected_appearance,
            **final_stats
        }

        with open(full_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

    def start(self):
        """Запуск сцени створення героя з поступовим завантаженням."""
        self.screen = pygame.display.get_surface()
        pygame.mixer.music.stop()
        pygame.mixer.stop()
        save_progress("HeroCreator")
        self.load_resources_with_progress()

    def stop(self):
        """Зупиняє рівень 1."""
        pygame.mixer.music.stop()

    def destroy(self):
        """Знищує ресурси сцени створення героя та очищає пам’ять."""
        pygame.mixer.music.stop()
        pygame.mixer.stop()

        if hasattr(self, "frames"):
            del self.frames

        self.character_cache.clear()
        self.filtered_character_cache.clear()
        self.character_image = None
        self.old_character_image = None
        self.screen = None

    def pause(self):
        """Призупиняє рівень, зберігаючи його стан."""
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.music_paused = True

    def resume(self):
        """Відновлює рівень після паузи."""
        if self.music_paused:
            pygame.mixer.music.unpause()
            self.music_paused = False

    def handle_events(self, events):
        """Обробляє події користувача, перемикання параметрів героя."""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.music_paused = True
                    self.pause()
                    self.scene_manager.change_scene("pause")  # Перехід у меню паузи
                if event.key == pygame.K_DOWN:
                    play_random_menu_sound(self.audio_manager)
                    self.selected_index = (self.selected_index + 1) % len(self.menu_items)
                elif event.key == pygame.K_UP:
                    play_random_menu_sound(self.audio_manager)
                    self.selected_index = (self.selected_index - 1) % len(self.menu_items)
                elif event.key == pygame.K_LEFT:
                    if self.selected_index < len(self.options):
                        play_random_menu_sound(self.audio_manager)
                        key = self.menu_items[self.selected_index]
                        self.current_selection[key] = (self.current_selection[key] - 1) % len(self.options[key])
                        self.update_character_image()

                elif event.key == pygame.K_RIGHT:
                    if self.selected_index < len(self.options):
                        play_random_menu_sound(self.audio_manager)
                        key = self.menu_items[self.selected_index]
                        self.current_selection[key] = (self.current_selection[key] + 1) % len(self.options[key])
                        self.update_character_image()
                elif event.key == pygame.K_RETURN:
                    if self.selected_index == len(self.options):
                        play_return_sound(self.audio_manager)
                        self.save_hero()
                        self.scene_manager.change_scene("level_1")

    def update(self):
        """Оновлення стану рівня, анімації зміни персонажа."""
        self.animation_counter += 1
        if self.animation_counter >= self.animation_speed:
            self.animation_counter = 0
            self.current_frame += self.animation_direction
            if self.current_frame >= len(self.frames):
                self.current_frame = len(self.frames) - 1
                self.animation_direction = -1
            elif self.current_frame < 0:
                self.current_frame = 0
                self.animation_direction = 1

        # Анімація зміни персонажа
        if self.animation_in_progress:
            speed = 13  # Швидкість руху персонажа
            fade_speed = 30  # Швидкість зміни прозорості

            if self.old_character_image:
                self.old_character_x -= speed  # Старий персонаж рухається вліво
                self.old_character_alpha = max(0, self.old_character_alpha - fade_speed)  # Прозоріє

            if self.character_image:
                self.character_x += speed  # Новий персонаж рухається вправо
                self.character_alpha = min(255, self.character_alpha + fade_speed)  # Поступово проявляється

            # Перевірка, чи новий персонаж досяг центру
            target_x = (self.screen.get_width() - self.character_image.get_width()) // 2 + self.screen.get_width() // 20

            if self.character_x >= target_x:
                self.character_x = target_x
                self.animation_in_progress = False  # Анімація завершена

        self.get_character_description()

    def render(self, screen):
        """Відображає рівень на екрані, малюючи фон, текст та кнопку переходу."""
        screen.blit(self.frames[self.current_frame], (0, 0))  # Відображення анімованого фону
        font = pygame.font.Font(resource_path("assets/menu_font.otf"), 50)

        # Заголовок
        title_text = font.render("  То хто ви такий?", True, (255, 255, 255))  # Холодніший колір
        screen.blit(title_text, (50, 50))

        # Відображення персонажів з анімацією
        base_y = screen.get_height() * 0.85  # Фіксоване положення нижнього краю персонажа

        def apply_night_filter(image):
            """Застосовує ефект туману, нічного освітлення, затемнення та зниження контрастності без перетворення в чорно-біле."""
            filtered_image = pygame.Surface(image.get_size(), pygame.SRCALPHA)
            for x in range(image.get_width()):
                for y in range(image.get_height()):
                    color = image.get_at((x, y))
                    if color.a > 0:  # Тільки непрозорі пікселі
                        r, g, b, a = color
                        r = r*0.5
                        g = g*0.6
                        b = b*0.6


                        filtered_image.set_at((x, y), (r, g, b, int(a * 0.95)))  # Легкий туман
            return filtered_image

        if self.old_character_image:
            key_old = ("filtered",) + self.old_character_key if self.old_character_key else None
            old_char_copy = self.apply_night_filter(self.old_character_image.copy(), key_old)
            old_char_copy.set_alpha(self.old_character_alpha)
            screen.blit(old_char_copy, (self.old_character_x - 50, base_y - old_char_copy.get_height()))

        if self.character_image:
            key_new = ("filtered",) + self.character_key if self.character_key else None
            char_copy = self.apply_night_filter(self.character_image.copy(), key_new)
            char_copy.set_alpha(self.character_alpha)
            screen.blit(char_copy, (self.character_x - 50, base_y - char_copy.get_height()))

        # Створення затемненого градієнта в нижній частині екрана
        screen_width, screen_height = screen.get_size()
        gradient_height = screen_height // 2
        gradient_surface = pygame.Surface((screen_width, gradient_height), pygame.SRCALPHA)

        for y in range(gradient_height):
            alpha = int(255 * math.sqrt(y / gradient_height))  # Чим ближче до низу, тим темніше
            pygame.draw.line(gradient_surface, (0, 0, 0, alpha), (0, y), (screen_width, y))

        screen.blit(gradient_surface, (0, screen_height - gradient_height))  # Накладання градієнта на нижню частину



        # Відображення меню
        desc_width = screen_width // 2
        menu_height = len(self.menu_items) * 65 + 200  # Висота меню
        desc_height = screen_height - menu_height  # Від меню до низу екрана
        description_font = pygame.font.Font(resource_path("assets/menu_font.otf"), 24)
        fixed_width = 400
        padding_x, padding_y = 90, 20
        bg_height = font.get_height() + padding_y
        last_option_y = 150  # Позиція останнього пункту меню

        for i, item in enumerate(self.menu_items):
            text = f"{item}: {self.options[item][self.current_selection[item]]}" if i < len(self.options) else "Почати"
            is_selected = i == self.selected_index
            bg_alpha = 200 if is_selected else 128

            option_x, option_y = 0, 150 + i * 65
            last_option_y = option_y + bg_height

            gradient_surface = pygame.Surface((fixed_width, bg_height), pygame.SRCALPHA)
            for x in range(fixed_width):
                alpha = int(bg_alpha * (1 - x / fixed_width))
                pygame.draw.line(gradient_surface, (0, 0, 0, alpha), (x, 0), (x, bg_height))
            screen.blit(gradient_surface, (option_x, option_y))

            color = (255, 255, 255) if is_selected else (150, 150, 150)
            rendered_text = font.render(text, True, color)
            screen.blit(rendered_text, (option_x + padding_x // 2, option_y + padding_y // 2))

        # Опис персонажа під меню
        description_text = self.get_character_description()
        wrapped_text = textwrap.wrap(description_text, width=50)
        desc_surface = pygame.Surface((desc_width, desc_height), pygame.SRCALPHA)

        for i, line in enumerate(wrapped_text):
            rendered_line = description_font.render(line, True, (200, 200, 200))
            desc_surface.blit(rendered_line, (10, i * 40))

        screen.blit(desc_surface, (10, last_option_y + 20))

        for x in range(fixed_width):
                alpha = int(bg_alpha * (1 - x / fixed_width))
                pygame.draw.line(desc_surface, (0, 0, 0, alpha), (x, 0), (x, bg_height))


