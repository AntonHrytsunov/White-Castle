import pygame
import logging
import os
import pygame.surfarray
import numpy as np

from utils.resource_loader import resource_path

class Player:
    _frame_cache = {}

    def __init__(self, screen, scale_x, scale_y, hero_data):
        self.screen = screen
        self.scale_x = scale_x
        self.scale_y = scale_y

        self.hero_scale = 2
        base_height = int(screen.get_height() * 0.15)
        target_height = int(base_height * self.hero_scale)
        height_offset = target_height - base_height
        self.base_y = int(screen.get_height() * 0.75) - height_offset
        self.width = int(screen.get_width() * 0.05)

        # Stats
        self.max_hp = hero_data.get("HP", 100)
        self.hp = self.max_hp
        self.max_mana = hero_data.get("Mana", 100)
        self.mana = self.max_mana
        self.max_stamina = hero_data.get("Stamina", 100)
        self.stamina = self.max_stamina

        # Stamina mechanics
        self.stamina_regen_rate = 10
        self.stamina_run_cost = 20
        self.stamina_jump_cost = 15
        self.stamina_delay = 1000
        self.last_stamina_use = pygame.time.get_ticks()

        # Physics
        self.speed = 5
        self.velocity_x = 0
        self.velocity_y = 0
        self.acceleration = 1.2
        self.friction = 0.8
        self.jump_power = -18
        self.gravity = 2
        self.on_ground = True

        self.left_boundary = int(screen.get_width() * 0.4)

        # Animation
        self.current_frame_index = 0
        self.animation_timer = 0
        self.animation_speed = 12
        self.current_animation = "idle"

        self.load_animations(hero_data, target_height)

        if self.walk_frames_right:
            first_img = self.walk_frames_right[0]
            self.rect = first_img.get_rect(bottomleft=(100, self.base_y))
            self.image = first_img
        else:
            self.rect = pygame.Rect(100, self.base_y, 50, target_height)
            self.image = None

    def load_animations(self, hero_data, target_height):
        walk_path, cache_key, _ = self.get_animation_path_and_key(self.screen, hero_data, self.hero_scale, self.scale_x, self.scale_y)
        self.walk_frames_right, self.walk_frames_left = self.load_animation_set(walk_path, cache_key, target_height)

        jump_path = walk_path.replace("walk", "jump")
        jump_cache_key = (jump_path, self.hero_scale, self.scale_x, self.scale_y)
        self.jump_frames_right, self.jump_frames_left = self.load_animation_set(jump_path, jump_cache_key, target_height)

    def load_animation_set(self, path, cache_key, target_height):
        if cache_key in Player._frame_cache:
            return Player._frame_cache[cache_key]

        frames_right = []
        frames_left = []

        if os.path.isdir(path):
            for filename in sorted(os.listdir(path)):
                if filename.endswith(".png"):
                    image = pygame.image.load(os.path.join(path, filename)).convert_alpha()
                    orig_width, orig_height = image.get_size()
                    aspect_ratio = orig_width / orig_height
                    target_width = int(target_height * aspect_ratio)
                    scaled_image = pygame.transform.scale(image, (target_width, target_height))

                    night_image = self.apply_night_filter(scaled_image.copy())
                    frames_right.append(night_image)
                    frames_left.append(pygame.transform.flip(night_image.copy(), True, False))

        Player._frame_cache[cache_key] = (frames_right, frames_left)
        return frames_right, frames_left

    @staticmethod
    def get_animation_path_and_key(screen, hero_data, hero_scale, scale_x, scale_y):
        race_map = {"людина": "human", "ельф": "elf", "гном": "dwarf", "звіролюд": "beast"}
        gender_map = {"чоловіча": "man", "жіноча": "girl"}
        appearance_map = {"світла": "white", "темна": "black"}

        race = race_map.get(hero_data.get("Раса", "людина").lower(), "human")
        gender = gender_map.get(hero_data.get("Стать", "чоловіча").lower(), "man")
        appearance = appearance_map.get(hero_data.get("Зовнішність", "темна").lower(), "black")

        base_path = os.path.join("assets", "characters", race, gender, appearance)
        walk_path = resource_path(os.path.join(base_path, "walk"))
        base_height = int(screen.get_height() * 0.15)
        target_height = int(base_height * hero_scale)
        cache_key = (walk_path, hero_scale, scale_x, scale_y)
        return walk_path, cache_key, target_height

    @staticmethod
    def apply_night_filter(surface):
        surface = surface.copy().convert_alpha()
        arr_rgb = pygame.surfarray.pixels3d(surface)
        arr_alpha = pygame.surfarray.pixels_alpha(surface)
        arr_rgb[:, :, 0] = (arr_rgb[:, :, 0] * 0.4).astype(np.uint8)
        arr_rgb[:, :, 1] = (arr_rgb[:, :, 1] * 0.4).astype(np.uint8)
        arr_rgb[:, :, 2] = (arr_rgb[:, :, 2] * 0.5 + 10).astype(np.uint8)
        del arr_rgb
        del arr_alpha
        return surface

    def handle_input(self, dt):
        keys = pygame.key.get_pressed()
        mods = pygame.key.get_mods()
        direction = 0

        if keys[pygame.K_RIGHT]:
            direction = 1
        elif keys[pygame.K_LEFT]:
            direction = -1

        # Біг зі Shift — тільки якщо є стаміна
        is_running = mods & pygame.KMOD_SHIFT and self.stamina >= self.stamina_run_cost * dt / 1000
        speed_multiplier = 2 if is_running else 1
        acceleration = self.acceleration * (2 if is_running else 1)

        # Витрати стаміни на біг
        if is_running and direction != 0:
            self.stamina -= self.stamina_run_cost * dt / 1000
            self.last_stamina_use = pygame.time.get_ticks()

        # Рух
        target_speed = self.speed * speed_multiplier * direction
        speed_diff = target_speed - self.velocity_x

        if abs(speed_diff) < acceleration:
            self.velocity_x = target_speed
        else:
            self.velocity_x += acceleration if speed_diff > 0 else -acceleration

        if direction == 0:
            self.velocity_x *= self.friction
            if abs(self.velocity_x) < 0.5:
                self.velocity_x = 0

        # Стрибок — тільки якщо є стаміна
        if keys[pygame.K_SPACE] and self.on_ground and self.stamina >= self.stamina_jump_cost:
            self.velocity_y = self.jump_power
            self.on_ground = False
            self.stamina -= self.stamina_jump_cost
            self.last_stamina_use = pygame.time.get_ticks()
            logging.debug(f"[Hero] Стрибок — стаміна: {self.stamina:.1f}")

    def update(self, dt):
        # Гравітація і вертикальний рух
        self.velocity_y += self.gravity
        self.rect.y += self.velocity_y

        if self.rect.y >= self.base_y:
            self.rect.y = self.base_y
            self.velocity_y = 0
            self.on_ground = True

        # Горизонтальний рух
        self.rect.x += self.velocity_x

        # --- Анімація ---
        self.facing_left = self.velocity_x < 0
        moving = self.velocity_x != 0

        # === Анімація стрибка (один прохід) ===
        if not self.on_ground and hasattr(self, "jump_frames_right") and self.jump_frames_right:
            if self.current_animation != "jump":
                self.current_animation = "jump"
                self.current_frame_index = 0
                self.animation_timer = 0

            frame_count = len(self.jump_frames_right)
            if self.current_frame_index < frame_count:
                self.animation_timer += dt
                if self.animation_timer >= self.animation_speed:
                    self.animation_timer = 0
                    self.current_frame_index += 1
                index = min(self.current_frame_index, frame_count - 1)
                self.image = self.jump_frames_left[index] if self.facing_left else self.jump_frames_right[index]

        # === Анімація ходьби ===
        elif moving:
            if self.current_animation != "walk":
                self.current_animation = "walk"
                self.current_frame_index = 0
                self.animation_timer = 0

            speed_factor = abs(self.velocity_x) / self.speed
            adjusted_speed = max(30, int(self.animation_speed / speed_factor))

            self.animation_timer += dt
            if self.animation_timer >= adjusted_speed:
                self.animation_timer = 0
                self.current_frame_index = (self.current_frame_index + 1) % len(self.walk_frames_right)

            self.image = self.walk_frames_left[self.current_frame_index] if self.facing_left else \
            self.walk_frames_right[self.current_frame_index]

        else:
            # Якщо стоїть — просто перша поза ходьби
            self.image = self.walk_frames_left[0] if self.facing_left else self.walk_frames_right[0]
            self.current_animation = "idle"

        # Регенерація стаміни
        now = pygame.time.get_ticks()
        if now - self.last_stamina_use > self.stamina_delay and self.stamina < self.max_stamina:
            self.stamina += self.stamina_regen_rate * dt / 1000
            if self.stamina > self.max_stamina:
                self.stamina = self.max_stamina

    def reset(self):
        self.rect.x = 100
        self.rect.y = self.base_y
        self.velocity_x = 0
        self.velocity_y = 0
        self.on_ground = True

    def draw(self, screen):
        if self.image:
            img_rect = self.image.get_rect(midbottom=self.rect.midbottom)
            screen.blit(self.image, img_rect)
        else:
            pygame.draw.rect(screen, (255, 0, 0), self.rect)

        # === Стилізовані прогресбари (напівпрозорі) ===
        bar_width = int(self.rect.width * 0.5)
        bar_height = 6
        spacing = 3
        corner_radius = 3

        start_x = self.rect.centerx - bar_width // 2
        start_y = self.rect.y - 45*self.scale_y  # вище

        def draw_bar(value, max_value, color_fn, y_offset):
            ratio = max(0.0, min(1.0, value / max_value))
            bg_rect = pygame.Rect(start_x, start_y + y_offset, bar_width, bar_height)
            fill_rect = pygame.Rect(start_x, start_y + y_offset, int(bar_width * ratio), bar_height)

            # Створюємо прозору поверхню для фону
            bar_surface = pygame.Surface((bar_width, bar_height), pygame.SRCALPHA)
            pygame.draw.rect(bar_surface, (30, 30, 30, 120), bar_surface.get_rect(), border_radius=corner_radius)
            screen.blit(bar_surface, (start_x, start_y + y_offset))

            # Прозора поверхня для кольорової заливки
            fill_surface = pygame.Surface((fill_rect.width, bar_height), pygame.SRCALPHA)
            fill_surface.fill((*color_fn(ratio), 180))  # додаємо прозорість
            pygame.draw.rect(fill_surface, (*color_fn(ratio), 180), fill_surface.get_rect(),
                             border_radius=corner_radius)
            screen.blit(fill_surface, (start_x, start_y + y_offset))

        def color_hp(ratio):
            if ratio > 0.6:
                return (180, 40, 40)
            elif ratio > 0.3:
                return (200, 140, 20)
            else:
                return (180, 20, 20)

        def color_mana(ratio):
            return (60, 60, int(200 + 30 * ratio))

        def color_stamina(ratio):
            if ratio > 0.6:
                return (60, 200, 60)
            elif ratio > 0.3:
                return (160, 160, 40)
            else:
                return (140, 60, 20)

        draw_bar(self.hp, self.max_hp, color_hp, 0)
        draw_bar(self.mana, self.max_mana, color_mana, bar_height + spacing)
        draw_bar(self.stamina, self.max_stamina, color_stamina, 2 * (bar_height + spacing))