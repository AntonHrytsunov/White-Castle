import pygame
import os
import random
from PIL import Image, ImageEnhance, ImageFilter
import logging

from utils.resource_loader import resource_path, save_progress
from objects.player_level1 import Player
from objects.crow import CrowManager
from objects.spider import SpiderManager
from objects.home_tree import HomeTree
from objects.dialog_box import DialogBox
from utils.resource_loader import load_hero_stats


class Level1:
    def __init__(self, scene_manager, audio_manager):

        # === Основні менеджери та екран ===
        self.name = "level_1"
        self.scene_manager = scene_manager
        self.audio_manager = audio_manager
        self.screen = pygame.display.get_surface()
        self.started = False
        self.current_progress = 0.0
        self.dialog_box = DialogBox(self.screen, "assets/menu_font.otf")

        # === Масштаб екрана ===
        self.scale_x = self.screen.get_width() / 1440
        self.scale_y = self.screen.get_height() / 900

        # === Прокрутка та геометрія рівня ===
        self.level_long = 12000
        self.world_x = 0
        self.scroll_velocity = 0
        self.scroll_acceleration = 1
        self.scroll_friction = 0.8

        # Швидкості паралаксу
        self.scroll_speed_trees = 1
        self.scroll_speed_ground = 1
        self.scroll_speed_trees2 = 2
        self.scroll_speed_fog = 1.9
        self.scroll_speed_fog2 = 0.9

        # Для генерації дерев
        self.trees_on_layer = 3000
        self.min_distance = 200
        self.max_distance = 450

        # === Дерево лісовика ===
        self.home_tree = HomeTree(
            position_x=8000,
            scale_x=self.scale_x,
            scale_y=self.scale_y,
            screen_height=self.screen.get_height()
        )

        # === Герой ===
        hero_data = load_hero_stats()
        self.player = Player(self.screen, self.scale_x, self.scale_y, hero_data)

        # === Музика рівня ===
        self.audio_file = resource_path("assets/scene/hero_creator/dark_wood.mp3")
        self.music_paused = False

        # === Ворони ===
        self.crows = []
        self.next_crow_x = 2000
        self.crow_spacing = random.randint(2500, 4000)
        self.crow_manager = CrowManager(audio_manager, self.screen, self.scale_x, self.scale_y)

        # === Павуки ===
        self.spider_manager = SpiderManager(self.screen.get_height(), self.scale_y, audio_manager, self.scale_x)
        self.spider_manager.player = self.player

        # === Дерево чарівника ===
        self.tree_dialog_shown = False

        # === Звуки вовків ===
        self.howl_checkpoints = [
            random.randint(6000, 6000),
            random.randint(8500, 8500),
        ]
        self.howl_played_flags = [False] * len(self.howl_checkpoints)
        wolf_sounds_folder = resource_path("assets/level_1/wolf")
        self.howl_sounds = []
        for f in os.listdir(wolf_sounds_folder):
            if f.endswith((".wav", ".ogg", ".mp3")):
                sound = pygame.mixer.Sound(os.path.join(wolf_sounds_folder, f))
                sound.set_volume(self.audio_manager.sound_volume)
                self.howl_sounds.append(sound)

        # === Фонові текстури (будуть завантажуватись пізніше) ===
        self.bg_trees_texture = None
        self.bg_trees2_texture = None
        self.fog_texture = None
        self.fog2_texture = None
        self.ground_texture = None
        self.sky_image = None

        self.bg_trees_width = 0
        self.bg_trees2_width = 0
        self.fog_width = 0
        self.fog2_width = 0
        self.ground_width = 0
        self.ground_height = 0

        self.bg_trees_positions = []
        self.bg_trees2_positions = []
        self.fog_positions = []
        self.fog2_positions = []
        self.ground_positions = []

        # === Небо ===
        original_sky = pygame.image.load(resource_path("assets/level_1/bg/sky.png")).convert()
        sky_width = self.screen.get_width()
        sky_height = int(original_sky.get_height() * self.scale_y)
        self.sky_image = pygame.transform.scale(original_sky, (sky_width, sky_height))

        # === Туман (змінна швидкість) ===
        self.fogs_on_layer = 80
        self.fog_scroll_base = 0.2
        self.fog_scroll_min = 0.1
        self.fog_scroll_max = 0.4
        self.fog_scroll_target = random.uniform(self.fog_scroll_min, self.fog_scroll_max)
        self.fog_scroll_change_speed = 0.0005

    def start(self):
        # === Перевірка повторного запуску ===
        save_progress(self.name)

        # === Оновлення surface (на випадок зміни екрану) ===
        self.screen = pygame.display.get_surface()

        # === Кроки підготовки сцени (етапи завантаження) ===
        steps = [
            ("Генеруємо дерева...", 0.3, lambda: self.create_bg(self.level_long, self.trees_on_layer)),
            ("Генеруємо туман...", 0.4, lambda: self.create_fog(self.level_long, self.fogs_on_layer)),
            ("Генеруємо землю...", 0.5, lambda: self.create_ground(self.level_long)),
            ("Завантажуємо шари...", 0.6, self.load_background_layers),
            ("Завантажуємо ворон...", 0.7, self.crow_manager.load_animations),
            ("Завантажуємо павуків...", 0.9 , self.spider_manager.spawn_initial_spiders)
        ]

        # === Відображення екрану завантаження поетапно ===
        for text, progress, action in steps:
            self.show_loading_screen(text, progress)
            action()

        # === Початкове положення героя ===
        self.player.reset()

        # === Запуск музики та фіналізація стану ===
        self.audio_manager.stop_music()
        self.audio_manager.play_music(self.audio_file)
        self.started = True
        self.current_progress = 1.0

        self.spider_manager.spawn_initial_spiders()

    def show_loading_screen(self, stage_text, target_progress):
        """Відображає екран завантаження з анімованим прогресбаром у стилі HeroCreator."""
        screen_width, screen_height = self.screen.get_size()
        font = pygame.font.Font(resource_path("assets/menu_font.otf"), 36)
        subfont = pygame.font.Font(resource_path("assets/menu_font.otf"), 24)

        bar_width = screen_width // 2
        bar_height = 30
        bar_x = screen_width // 2 - bar_width // 2
        bar_y = screen_height // 2 + 20

        duration_ms = 400
        start_time = pygame.time.get_ticks()
        start_progress = self.current_progress

        while self.current_progress < target_progress:
            now = pygame.time.get_ticks()
            t = min((now - start_time) / duration_ms, 1.0)
            self.current_progress = start_progress + (target_progress - start_progress) * t

            # === Темне тло з легким шумом чи градієнтом (опційно) ===
            self.screen.fill((0, 0, 0))

            # === Заголовок і підпис ===
            title_surface = font.render("Завантаження...", True, (220, 220, 220))
            self.screen.blit(title_surface, (
                screen_width // 2 - title_surface.get_width() // 2,
                bar_y - 80
            ))

            subtitle_surface = subfont.render(stage_text, True, (180, 180, 180))
            self.screen.blit(subtitle_surface, (
                screen_width // 2 - subtitle_surface.get_width() // 2,
                bar_y - 40
            ))

            # === Рамка прогресбару ===
            pygame.draw.rect(self.screen, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height), border_radius=8)

            # === Заповнена частина ===
            pygame.draw.rect(
                self.screen,
                (180, 180, 255),
                (bar_x, bar_y, int(bar_width * self.current_progress), bar_height),
                border_radius=8
            )

            # === Оновлення екрану ===
            pygame.display.flip()
            pygame.time.delay(16)

    def load_background_layers(self):

        # === Внутрішня функція: завантаження, масштабування і розміщення текстур ===
        def load_and_assign(path, attr, pos_attr):
            try:
                # Завантаження зображення з прозорістю
                texture = pygame.image.load(path).convert_alpha()

                # Масштабування з урахуванням масштабу екрана
                scaled_texture = pygame.transform.scale(
                    texture,
                    (int(texture.get_width() * self.scale_x), int(texture.get_height() * self.scale_y))
                )

                # Зберігаємо текстуру
                setattr(self, attr, scaled_texture)

                # Зберігаємо ширину текстури (наприклад, bg_trees_width)
                setattr(self, attr.replace("texture", "width"), scaled_texture.get_width())

                # Генеруємо початкові позиції для шарів (повторюються 3 рази для паралаксу)
                setattr(self, pos_attr, [i * scaled_texture.get_width() for i in range(3)])

            except Exception as e:
                pass

        # === Завантаження всіх необхідних фонових шарів ===
        load_and_assign(resource_path("assets/level_1/bg_create/bg_trees.png"), "bg_trees_texture",
                        "bg_trees_positions")
        load_and_assign(resource_path("assets/level_1/bg_create/bg_trees2.png"), "bg_trees2_texture",
                        "bg_trees2_positions")
        load_and_assign(resource_path("assets/level_1/bg_create/fog.png"), "fog_texture", "fog_positions")
        load_and_assign(resource_path("assets/level_1/bg_create/fog2.png"), "fog2_texture", "fog2_positions")
        load_and_assign(resource_path("assets/level_1/bg_create/ground.png"), "ground_texture", "ground_positions")

    def load_crow_animations(self):

        # === Внутрішня функція: завантаження і масштабування кадрів з папки ===
        def load_animation(folder_path):
            frames = []
            try:
                for filename in sorted(os.listdir(folder_path)):
                    if filename.endswith(".png"):
                        frame = pygame.image.load(os.path.join(folder_path, filename)).convert_alpha()

                        # Масштабування кадру відповідно до розміру екрана
                        scaled_frame = pygame.transform.scale(
                            frame,
                            (int(frame.get_width() * self.scale_x), int(frame.get_height() * self.scale_y))
                        )

                        frames.append(scaled_frame)

            except Exception as e:
                pass
            return frames

        # === Завантаження основних анімацій ворони ===
        self.crows_idle_frames = load_animation(resource_path("assets/level_1/crow/idle"))
        self.crows_fly_frames = load_animation(resource_path("assets/level_1/crow/fly"))

        # === Завантаження анімації ходьби ворони ===
        self.crows_walk_frames = load_animation(resource_path("assets/level_1/crow/walk"))

    def create_ground(self, long):

        # === Перевірка, чи зображення землі вже існує ===
        output_path = resource_path("assets/level_1/bg_create/ground.png")
        if os.path.exists(output_path):
            ground_img = Image.open(output_path)
            _, self.ground_height = ground_img.size  # Отримуємо лише висоту
            return

        # === Вихідна текстура землі для повторного заповнення ===
        input_path = resource_path("assets/level_1/bg/ground.png")

        try:
            # Завантаження початкового тайла землі
            ground_img = Image.open(input_path)
            ground_width, self.ground_height = ground_img.size

            # Створення нового зображення з повтором землі на всю довжину рівня
            new_image = Image.new("RGBA", (long, self.ground_height), (0, 0, 0, 0))

            # === Прокладка землі тайлами з чергуванням фліпу ===
            x_offset = 0
            flip = False
            tile_count = 0

            while x_offset < long:
                tile = ground_img.transpose(Image.FLIP_LEFT_RIGHT) if flip else ground_img
                tile_width = min(ground_width, long - x_offset)
                new_image.paste(tile.crop((0, 0, tile_width, self.ground_height)), (x_offset, 0))
                x_offset += tile_width
                flip = not flip
                tile_count += 1

            # === Збереження фінального зображення землі ===
            new_image.save(output_path)

        except Exception as e:
            pass

    def create_fog(self, long, fog):

        # === Шляхи до папки з текстурами та вихідних файлів ===
        fog_folder = resource_path("assets/level_1/fog")
        output_files = [
            resource_path("assets/level_1/bg_create/fog.png"),
            resource_path("assets/level_1/bg_create/fog2.png")
        ]

        # === Якщо обидва шари туману вже згенеровані — пропускаємо ===
        if all(os.path.exists(f) for f in output_files):
            return

        try:
            # === Завантаження всіх PNG-файлів туману з папки ===
            fog_images = [Image.open(os.path.join(fog_folder, f))
                          for f in os.listdir(fog_folder) if f.endswith(".png")]

            # === Максимальна висота шару туману (з запасом для нижньої межі) ===
            max_height = max(img.height for img in fog_images) + 200
            fog_image_1 = Image.new("RGBA", (long, max_height), (0, 0, 0, 0))

            # === Генерація першого шару туману ===
            for i in range(fog):
                fog = random.choice(fog_images)

                # Позиціонування туману на випадкову X-координату
                x = random.randint(0, long - fog.width)
                y = max_height - fog.height
                fog_image_1.paste(fog, (x, y), fog)

                # Півпрозорий дубль для подальшого використання
                fog = fog.copy()
                alpha = fog.split()[3]
                alpha = ImageEnhance.Brightness(alpha).enhance(0.5)
                fog.putalpha(alpha)

            fog_image_1.save(output_files[0])

            # === Генерація другого шару туману (дзеркальний і стилізований) ===
            fog_image_2 = fog_image_1.transpose(Image.FLIP_LEFT_RIGHT)
            fog_image_2 = ImageEnhance.Brightness(fog_image_2).enhance(0.7)
            fog_image_2 = ImageEnhance.Contrast(fog_image_2).enhance(0.7)
            fog_image_2 = fog_image_2.filter(ImageFilter.GaussianBlur(2))

            fog_image_2.save(output_files[1])

        except Exception as e:
            pass

    def create_bg(self, long, trees):

        # === Шляхи до ресурсів ===
        tree_folder = resource_path("assets/level_1/trees")
        web_folder = resource_path("assets/level_1/spider_web")
        output_files = [
            resource_path("assets/level_1/bg_create/bg_trees.png"),
            resource_path("assets/level_1/bg_create/bg_trees2.png")
        ]

        # === Пропуск генерації, якщо фон вже існує ===
        if all(os.path.exists(f) for f in output_files):
            return

        try:
            # === Завантаження зображень дерев і павутин ===
            tree_images = [Image.open(os.path.join(tree_folder, f)) for f in os.listdir(tree_folder) if
                           f.endswith(".png")]
            web_images = [Image.open(os.path.join(web_folder, f)) for f in os.listdir(web_folder) if f.endswith(".png")]

            # === Підготовка основного полотна ===
            max_height = max(img.height for img in tree_images) + 200
            bg_image_1 = Image.new("RGBA", (long, max_height), (0, 0, 0, 0))

            tree_positions = []  # Центри дерев по X
            tree_bases = []  # Бази дерев для розміщення павутин

            # === Додавання першого дерева вручну ===
            x = 0
            tree = tree_images[0].copy()

            # Можлива трансформація
            if random.random() < 0.5:
                tree = tree.transpose(Image.FLIP_LEFT_RIGHT)
            scale = random.uniform(0.95, 1.05)
            tree = tree.resize((int(tree.width * scale), int(tree.height * scale)), Image.LANCZOS)

            y = max_height - tree.height
            tree_positions.append(x + tree.width // 2)
            tree_bases.append((x + tree.width // 2, y))
            bg_image_1.paste(tree, (x, y), tree)

            # === Генерація решти дерев ===
            for _ in range(trees - 1):
                tree = random.choice(tree_images).copy()

                # Трансформації
                if random.random() < 0.5:
                    tree = tree.transpose(Image.FLIP_LEFT_RIGHT)
                scale = random.uniform(0.95, 1.05)
                tree = tree.resize((int(tree.width * scale), int(tree.height * scale)), Image.LANCZOS)

                tree_width, tree_height = tree.size
                valid_position = False
                attempts = 0

                # Пошук валідної позиції для дерева
                while not valid_position and attempts < 10000:
                    last_x = tree_positions[-1]
                    new_x = last_x + random.randint(self.min_distance, self.max_distance)
                    if 0 <= new_x - tree_width // 2 < long - tree_width:
                        valid_position = True
                        tree_positions.append(new_x)
                    attempts += 1

                if valid_position:
                    x = new_x - tree_width // 2
                    y = max_height - tree_height
                    bg_image_1.paste(tree, (x, y), tree)
                    tree_bases.append((x + tree_width // 2, y))

                    # === Павутина між деревами ===
                    if web_images:
                        web = random.choice(web_images).convert("RGBA")
                        prev_x, prev_y = tree_bases[-2]
                        curr_x, curr_y = tree_bases[-1]

                        distance = abs(curr_x - prev_x)
                        min_width = 40
                        if distance < min_width:
                            distance = min_width

                        aspect_ratio = web.height / web.width
                        new_width = distance
                        new_height = int(new_width * aspect_ratio)

                        web = web.resize((new_width, new_height), Image.LANCZOS)
                        web = ImageEnhance.Brightness(web).enhance(1.8)  # Збільшити яскравість на 50%
                        web = ImageEnhance.Contrast(web).enhance(1.5)  # Збільшити контраст
                        mid_x = (prev_x + curr_x) // 2
                        web_x = mid_x - web.width // 2
                        web_y = max_height - int(web.height * random.randint(5, 15) // 10)
                        bg_image_1.paste(web, (web_x, web_y), web)

            # === Ефекти на основний шар дерев ===
            bg_image_1 = ImageEnhance.Brightness(bg_image_1).enhance(0.9)
            bg_image_1 = ImageEnhance.Contrast(bg_image_1).enhance(0.6)
            bg_image_1 = bg_image_1.filter(ImageFilter.GaussianBlur(1.3))
            bg_image_1.save(output_files[0])

            # === Другий фоновий шар: дзеркалення, масштабування, стилізація ===
            bg_image_2 = bg_image_1.transpose(Image.FLIP_LEFT_RIGHT)
            new_size = (int(bg_image_2.width * 0.90), int(bg_image_2.height * 0.90))
            bg_image_2 = bg_image_2.resize(new_size)
            bg_image_2 = ImageEnhance.Brightness(bg_image_2).enhance(0.85)
            bg_image_2 = ImageEnhance.Contrast(bg_image_2).enhance(0.7)
            bg_image_2 = bg_image_2.filter(ImageFilter.GaussianBlur(2))
            bg_image_2.save(output_files[1])

        except Exception as e:
            pass

    def update(self):
        if self.dialog_box.active and self.dialog_box.pause_player:
            now = pygame.time.get_ticks()
            self.last_update_time = now  # ⏱️ оновлюємо таймер, щоб уникнути стрибка
            self.dialog_box.update(0)
            return
        # --- ОНОВЛЕННЯ ФОНУ ---
        for i in range(len(self.bg_trees_positions)):
            if self.bg_trees_positions[i] <= -self.bg_trees_width:
                self.bg_trees_positions[i] += self.bg_trees_width * len(self.bg_trees_positions)
            if self.bg_trees2_positions[i] <= -self.bg_trees2_width:
                self.bg_trees2_positions[i] += self.bg_trees2_width * len(self.bg_trees2_positions)
            if self.fog_positions[i] <= -self.fog_width:
                self.fog_positions[i] += self.fog_width * len(self.fog_positions)
            if self.fog2_positions[i] <= -self.fog2_width:
                self.fog2_positions[i] += self.fog2_width * len(self.fog2_positions)
            if self.ground_positions[i] <= -self.ground_width:
                self.ground_positions[i] += self.ground_width * len(self.ground_positions)

        # --- ПЛАВНА ЗМІНА ШВИДКОСТІ ТУМАНУ ---
        now = pygame.time.get_ticks()
        dt = now - getattr(self, 'last_update_time', now)
        self.last_update_time = now
        if abs(self.fog_scroll_base - self.fog_scroll_target) < 0.01:
            self.fog_scroll_target = random.uniform(self.fog_scroll_min, self.fog_scroll_max)
        else:
            if self.fog_scroll_base < self.fog_scroll_target:
                self.fog_scroll_base += self.fog_scroll_change_speed * dt
            else:
                self.fog_scroll_base -= self.fog_scroll_change_speed * dt

        fog_idle_scroll = self.fog_scroll_base
        for i in range(len(self.fog_positions)):
            self.fog_positions[i] -= fog_idle_scroll
            if self.fog_positions[i] <= -self.fog_width:
                self.fog_positions[i] += self.fog_width * len(self.fog_positions)
        for i in range(len(self.fog2_positions)):
            self.fog2_positions[i] -= fog_idle_scroll * 0.5
            if self.fog2_positions[i] <= -self.fog2_width:
                self.fog2_positions[i] += self.fog2_width * len(self.fog2_positions)


        # --- ОНОВЛЕННЯ ГЕРОЯ ---
        self.player.handle_input(dt)
        self.player.update(dt)

        # --- ПРОКРУТКА ---
        if self.player.rect.x + self.player.velocity_x < 0:
            self.player.rect.x = 0
            self.player.velocity_x = 0

        if self.player.rect.x + self.player.velocity_x < self.player.left_boundary:
            self.player.rect.x += self.player.velocity_x
            self.scroll_velocity = 0
        else:
            target_scroll = self.player.velocity_x if self.player.rect.x >= self.player.left_boundary else 0
            scroll_diff = target_scroll - self.scroll_velocity

            if abs(scroll_diff) < self.scroll_acceleration:
                self.scroll_velocity = target_scroll
            else:
                self.scroll_velocity += self.scroll_acceleration if scroll_diff > 0 else -self.scroll_acceleration

            if target_scroll == 0:
                self.scroll_velocity *= self.scroll_friction
                if abs(self.scroll_velocity) < 0.2:
                    self.scroll_velocity = 0

            for i in range(len(self.bg_trees_positions)):
                self.bg_trees_positions[i] -= self.scroll_velocity // self.scroll_speed_trees
                self.bg_trees2_positions[i] -= self.scroll_velocity // self.scroll_speed_trees2
                self.fog_positions[i] -= self.scroll_velocity // self.scroll_speed_fog
                self.fog2_positions[i] -= self.scroll_velocity // self.scroll_speed_fog2
                self.ground_positions[i] -= self.scroll_velocity // self.scroll_speed_ground

            self.player.rect.x = self.player.left_boundary

        # --- Звук вовків ---
        for i, checkpoint in enumerate(self.howl_checkpoints):
            if self.world_x >= checkpoint and not self.howl_played_flags[i]:
                self.audio_manager.play_sound(random.choice(self.howl_sounds))
                self.howl_played_flags[i] = True

        hero_world_x = self.player.rect.x + self.world_x

        # Оновлення дерева лісовика
        self.home_tree.update(hero_world_x)

        # === Взаємодія з деревом лісовика ===
        if (
                abs(hero_world_x - self.home_tree.x_world) < 100 and
                not self.dialog_box.active and
                not self.tree_dialog_shown
        ):
            self.tree_dialog_shown = True  # 🚫 Показуємо лише один раз
            self.dialog_box.show(
                "Ти бачиш старе дерево з дуплом. У ньому щось блимає...",
                ["Зазирнути всередину", "Відійти"],
                on_select=self.handle_tree_choice,
                pause_player=True
            )

        # Оновлення ворон
        self.crow_manager.update(
            hero_world_x=hero_world_x,
            world_x=self.world_x,
            scroll_velocity=self.scroll_velocity,
            screen_width=self.screen.get_width(),
            dt=dt
        )

        # --- Оновлення павуків ---
        self.spider_manager.update(
            dt,
            hero_world_x,
            self.player.width,
            scale_x=self.scale_x,
            scale_y=self.scale_y,
            player = self.player
        )

        # --- Оновлення глобального зсуву сцени ---
        self.world_x += self.scroll_velocity

    def handle_events(self, events):
        for event in events:
            # 🟢 Пауза працює завжди
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.music_paused = True
                self.pause()
                self.scene_manager.change_scene("pause")
                return  # ⏹️ після паузи інші події не обробляємо

        # 🟡 Обробка діалогу, якщо активний
        if self.dialog_box.active:
            for event in events:
                self.dialog_box.handle_event(event)
            return

    def render(self, screen):
        # --- Темний базовйи фон ---
        pygame.draw.rect(screen, (0, 0, 0),
                         (0, 0, self.screen.get_width(), self.screen.get_height()))
        # --- Небо ---
        screen.blit(self.sky_image, (0, 0))  # Виводимо зображення неба

        # --- Допоміжна функція для промальовки шарів ---
        def draw_layer(screen, texture, positions, y_percent):
            y_offset = int(screen.get_height() * y_percent)  # Y-позиція шару в залежності від відсотка висоти
            offset_x = int(screen.get_width() * 0.2930)  # Зсув по X (паралакс)
            for pos_x in positions:
                screen.blit(texture, (pos_x - offset_x, y_offset))  # Малюємо шар зі зсувом

        # --- Промальовка фонових шарів у порядку глибини ---
        draw_layer(screen, self.fog2_texture, self.fog2_positions, 0.0810)  # Далекий туман
        draw_layer(screen, self.bg_trees2_texture, self.bg_trees2_positions, 0.0347)  # Далекі дерева
        draw_layer(screen, self.fog_texture, self.fog_positions, 0.0810)  # Ближчий туман

        # --- Шар землі ---
        for pos_x in self.bg_trees_positions:
            screen.blit(
                self.ground_texture,
                (pos_x - 300, self.screen.get_height() - self.ground_height * self.scale_y)
            )

        # --- Ближчі дерева ---
        draw_layer(screen, self.bg_trees_texture, self.bg_trees_positions, 0.0579)

        # Дерево лісовика
        self.home_tree.draw(screen, self.world_x)

        # --- Ворони ---
        self.crow_manager.draw(screen, self.world_x)

        # --- Павуки ---
        self.spider_manager.draw(screen, self.world_x)

        # --- Герой (виклик метода класу Player) ---
        self.player.draw(screen)

        # --- Завершальний шар туману для глибини ---
        draw_layer(screen, self.fog2_texture, self.fog2_positions, 0.0810)

        self.dialog_box.draw()

    def stop(self):
        self.started = False

        # --- Скидання таймерів ---
        self.last_update_time = 0

        # --- Скидання стану гравця ---
        self.player.reset()

        # --- Скидання позицій прокрутки та інерції ---
        self.world_x = 0
        self.scroll_velocity = 0
        self.fog_scroll_base = 0.2
        self.fog_scroll_target = random.uniform(self.fog_scroll_min, self.fog_scroll_max)

        # --- Скидання позицій фонів до початкових значень ---
        self.bg_trees_positions = [i * self.bg_trees_width for i in range(3)]
        self.bg_trees2_positions = [i * self.bg_trees2_width for i in range(3)]
        self.fog_positions = [i * self.fog_width for i in range(3)]
        self.fog2_positions = [i * self.fog2_width for i in range(3)]
        self.ground_positions = [i * self.ground_width for i in range(3)]

        # Скидання дерева лісовика
        self.home_tree = None

        # --- Зупинка музики ---
        pygame.mixer.music.stop()

        # --- Очистка ворон ---
        self.crow_manager.reset()

        # --- Знищення павуків ---
        self.spider_manager.reset()
        self.spider_manager.stop_all_sounds()
        self.crow_manager.stop_all_sounds()

        # --- Очистка графічних ресурсів ---
        self.bg_trees_texture = None
        self.bg_trees2_texture = None
        self.fog_texture = None
        self.fog2_texture = None
        self.ground_texture = None
        self.sky_image = None

        # --- Очистка аудіоресурсів ---
        self.howl_sounds.clear()
        self.howl_played_flags = [False] * len(self.howl_checkpoints)

        # --- Скидання посилань на об’єкти менеджерів та екран ---
        self.screen = None
        self.scene_manager = None
        self.audio_manager = None

    def pause(self):
        # --- Пауза музики і оновлення прапорця ---
        pygame.mixer.music.pause()
        self.music_paused = True
        self.spider_manager.stop_all_sounds()
        self.crow_manager.stop_all_sounds()

    def resume(self):
        # --- Відновлення музики та прапорця ---
        pygame.mixer.music.unpause()
        self.music_paused = False
        self.last_update_time = pygame.time.get_ticks()

    def handle_tree_choice(self, index, option_text):
        if index == 0:
            print("🧙‍♂️ Гравець зазирнув у дупло — щось трапиться...")
            # TODO: тут можеш додати новий діалог або змінити стан
        elif index == 1:
            print("🚶 Гравець відійшов.")