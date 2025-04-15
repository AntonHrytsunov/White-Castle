import pygame
import json
import logging
from PIL import Image, ImageSequence

from utils.resource_loader import resource_path, load_settings, load_progress, save_progress, get_save_path
from core.audio_manager import play_random_menu_sound, play_return_sound

SAVE_FILE = "progress.json"


class MainMenu:
    def __init__(self, scene_manager, audio_manager, last_scene=None):
        self.name = "menu"
        self.scene_manager = scene_manager
        self.audio_manager = audio_manager
        self.last_scene = last_scene or load_progress()
        self.screen = None

        self.options = ["Нова гра", "Продовжити гру", "Налаштування", "Вийти"]
        self.selected_option = 0
        self.settings = load_settings()

        # Анімація фону
        self.bg_frames = []
        self.frame_index = 0
        self.reverse = False
        self.frame_delay = 2
        self.current_delay = 0

    def start(self):
        self.screen = pygame.display.get_surface()

        if not pygame.mixer.music.get_busy():
            self.audio_manager.play_music("assets/menu/menu_ost/menu_ost.mp3")

        self.last_scene = load_progress()
        self.load_gif_frames("assets/menu/menu_bg/image_menu.gif")

    def load_gif_frames(self, gif_path):
        try:
            pil_image = Image.open(resource_path(gif_path))
            self.bg_frames = []
            for frame in ImageSequence.Iterator(pil_image):
                frame = frame.convert("RGBA")
                data = frame.tobytes()
                size = frame.size
                mode = frame.mode
                surface = pygame.image.fromstring(data, size, mode).convert_alpha()
                self.bg_frames.append(surface)
        except Exception as e:
            pass

    def update_background_animation(self):
        if self.current_delay < self.frame_delay:
            self.current_delay += 1
            return
        self.current_delay = 0
        if not self.reverse:
            self.frame_index += 1
            if self.frame_index >= len(self.bg_frames) - 1:
                self.reverse = True
        else:
            self.frame_index -= 1
            if self.frame_index <= 0:
                self.reverse = False

    def stop(self):
        pass

    def destroy(self):
        self.bg_frames.clear()

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    play_random_menu_sound(self.audio_manager)
                    self.selected_option = (self.selected_option - 1) % len(self.options)

                elif event.key == pygame.K_DOWN:
                    play_random_menu_sound(self.audio_manager)
                    self.selected_option = (self.selected_option + 1) % len(self.options)

                elif event.key == pygame.K_RETURN:
                    play_return_sound(self.audio_manager)
                    self.execute_selected_option()

                elif event.key == pygame.K_ESCAPE:
                    self.scene_manager.change_scene("ConfirmOut")
                    play_return_sound(self.audio_manager)

    def execute_selected_option(self):
        save_exists = False
        saved_scene = None

        try:
            with open(get_save_path(SAVE_FILE), "r", encoding="utf-8") as file:
                save_data = json.load(file)
                saved_scene = save_data.get("last_scene")

                if saved_scene:
                    save_exists = True

        except (FileNotFoundError, json.JSONDecodeError) as e:
            pass

        if self.selected_option == 0:  # Нова гра
            if save_exists:
                self.scene_manager.change_scene("ConfirmNewGame")
            else:
                self.audio_manager.stop_music()
                save_progress("scene_1")
                self.scene_manager.change_scene("scene_1")

        elif self.selected_option == 1:  # Продовжити гру
            if save_exists:
                self.scene_manager.reset()
                self.scene_manager.change_scene(saved_scene)
            else:
                pass

        elif self.selected_option == 2:  # Налаштування
            self.scene_manager.change_scene("settings")

        elif self.selected_option == 3:  # Вийти
            self.scene_manager.change_scene("ConfirmOut")

    def update(self):
        self.update_background_animation()

    def render(self, screen):
        if self.bg_frames:
            bg = self.bg_frames[self.frame_index]
            bg_scaled = pygame.transform.smoothscale(bg, screen.get_size())
            screen.blit(bg_scaled, (0, 0))

        font = pygame.font.Font(resource_path("assets/menu_font.otf"), 50)
        padding_x, padding_y = 40, 20
        max_width = 0
        rendered = []

        for option in self.options:
            text = font.render(option, True, (255, 255, 255))
            rect = text.get_rect()
            max_width = max(max_width, rect.width)
            rendered.append((text, rect))

        item_h = font.get_height() + padding_y
        menu_x = screen.get_width() // 2
        menu_y = screen.get_height() // 2 - len(self.options) * item_h // 2
        bg_w = max_width + padding_x

        for i, (text, rect) in enumerate(rendered):
            is_selected = (i == self.selected_option)
            color = (255, 255, 255) if is_selected else (150, 150, 150)
            if i == 1 and not self.last_scene:
                color = (100, 100, 100)

            alpha = 200 if is_selected else 128
            bg_surface = pygame.Surface((bg_w, item_h), pygame.SRCALPHA)

            for x in range(bg_w):
                a = int(alpha * (1 - abs((x - bg_w / 2) / (bg_w / 2))))
                pygame.draw.line(bg_surface, (0, 0, 0, a), (x, 0), (x, item_h))

            option_x = menu_x - bg_w // 2
            option_y = menu_y + i * item_h
            screen.blit(bg_surface, (option_x, option_y))

            text = font.render(self.options[i], True, color)
            screen.blit(text, (menu_x - rect.width // 2, option_y + padding_y // 2))