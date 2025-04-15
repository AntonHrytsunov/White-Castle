import pygame
import json
import logging
from PIL import Image, ImageSequence

from core.audio_manager import play_random_menu_sound, play_return_sound
from utils.resource_loader import resource_path, save_progress


SAVE_FILE = "progress.json"


class ConfirmNewGame:
    """
    Екран підтвердження початку нової гри. Показує попередження про втрату збереження.
    """
    def __init__(self, scene_manager, audio_manager):
        self.name = "ConfirmNewGame"
        self.scene_manager = scene_manager
        self.audio_manager = audio_manager
        self.options = ["Так", "Ні"]
        self.selected_option = 1
        self.background = None
        self.font = pygame.font.Font(resource_path("assets/menu_font.otf"), 50)

        # Анімація фону
        self.bg_frames = []
        self.frame_index = 0
        self.reverse = False
        self.frame_delay = 2
        self.current_delay = 0

    def start(self):
        self.screen = pygame.display.get_surface()
        self.load_gif_frames("assets/menu/menu_bg/ConfirmNewGame.gif")

    def stop(self):
        pass
    def destroy(self):
        self.background = None

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

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_DOWN):
                    direction = -1 if event.key == pygame.K_UP else 1
                    self.selected_option = (self.selected_option + direction) % len(self.options)
                    play_random_menu_sound(self.audio_manager)

                elif event.key == pygame.K_RETURN:
                    play_return_sound(self.audio_manager)
                    if self.selected_option == 1:  # Ні
                        self.scene_manager.change_scene("menu")
                    else:  # Так — почати нову гру
                        self.audio_manager.stop_music()

                        # Скидаємо прогрес
                        save_progress("scene_1")

                        self.scene_manager.change_scene("scene_1")

                elif event.key == pygame.K_ESCAPE:
                    play_return_sound(self.audio_manager)
                    self.scene_manager.change_scene("menu")

    def update(self):
        self.update_background_animation()

    def render(self, screen):
        screen_width, screen_height = screen.get_size()
        if self.bg_frames:
            bg = self.bg_frames[self.frame_index]
            bg_scaled = pygame.transform.smoothscale(bg, screen.get_size())
            screen.blit(bg_scaled, (0, 0))

        # Текст попередження
        question_texts = [
            "Почати нову гру?",
            "Минуле збереження буде втрачено!"
        ]
        padding = 20
        y_offset = screen_height // 5.5

        for i, text in enumerate(question_texts):
            rendered = self.font.render(text, True, (255, 255, 255))
            rect = rendered.get_rect(center=(screen_width // 2, y_offset + i * (self.font.get_height() + padding)))
            self.draw_text_background(screen, rect)
            screen.blit(rendered, rect)

        # Кнопки
        option_padding_x = 140
        option_padding_y = 20
        font_height = self.font.get_height()
        button_width = max(self.font.size(opt)[0] for opt in self.options) + option_padding_x
        button_height = font_height + option_padding_y

        base_y = screen_height // 2.2
        for i, option in enumerate(self.options):
            is_selected = (i == self.selected_option)
            color = (255, 255, 255) if is_selected else (150, 150, 150)
            alpha = 200 if is_selected else 100

            x = screen_width // 2 - button_width // 2
            y = base_y + i * button_height

            self.draw_button_background(screen, x, y, button_width, button_height, alpha)

            text_rendered = self.font.render(option, True, color)
            text_rect = text_rendered.get_rect(center=(x + button_width // 2, y + button_height // 2))
            screen.blit(text_rendered, text_rect)

    def draw_text_background(self, screen, rect, alpha=180):
        surface = pygame.Surface((rect.width + 20, rect.height + 10), pygame.SRCALPHA)
        for x in range(surface.get_width()):
            a = int(alpha * (1 - abs((x - surface.get_width() / 2) / (surface.get_width() / 2))))
            pygame.draw.line(surface, (0, 0, 0, a), (x, 0), (x, surface.get_height()))
        screen.blit(surface, (rect.x - 10, rect.y - 5))

    def draw_button_background(self, screen, x, y, w, h, alpha):
        surface = pygame.Surface((w, h), pygame.SRCALPHA)
        for px in range(w):
            a = int(alpha * (1 - abs((px - w / 2) / (w / 2))))
            pygame.draw.line(surface, (0, 0, 0, a), (px, 0), (px, h))
        screen.blit(surface, (x, y))