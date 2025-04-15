import pygame
import logging
from PIL import Image, ImageSequence

from utils.resource_loader import resource_path, load_settings, save_progress
from core.audio_manager import play_random_menu_sound, play_return_sound


class PauseMenu:
    """
    Сцена паузи з трьома опціями: продовжити, головне меню, вийти з гри.
    """

    def __init__(self, scene_manager, audio_manager):
        self.name = "pause"
        self.scene_manager = scene_manager
        self.audio_manager = audio_manager

        self.options = ["Продовжити", "Головне меню", "Вийти"]
        self.selected_option = 0

        self.font = pygame.font.Font(resource_path("assets/menu_font.otf"), 50)
        self.settings = load_settings()

        # Анімація фону
        self.bg_frames = []
        self.frame_index = 0
        self.reverse = False
        self.frame_delay = 2
        self.current_delay = 0

        # Підтвердження виходу
        self.confirming = False
        self.confirm_action = None  # "menu" або "quit"
        self.confirm_options = ["Так", "Ні"]
        self.selected_confirm_option = 0

    def start(self):
        self.screen = pygame.display.get_surface()
        self.background = pygame.image.load(resource_path("assets/menu/menu_bg/pause_menu.jpeg")).convert()
        self.load_gif_frames("assets/menu/menu_bg/pause_menu.gif")

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
        pass

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.confirming:
                    if event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                        self.selected_confirm_option = (self.selected_confirm_option + 1) % 2
                        play_random_menu_sound(self.audio_manager)
                    elif event.key == pygame.K_RETURN:
                        play_return_sound(self.audio_manager)
                        if self.selected_confirm_option == 0:
                            if self.confirm_action == "menu":
                                self.scene_manager.reset()
                                self.scene_manager.change_scene("menu")
                                self.destroy()
                            elif self.confirm_action == "quit":
                                self.scene_manager.quit_game()
                        else:
                            self.confirming = False
                    elif event.key == pygame.K_ESCAPE:
                        self.confirming = False
                else:
                    if event.key == pygame.K_UP:
                        self.selected_option = (self.selected_option - 1) % len(self.options)
                        play_random_menu_sound(self.audio_manager)
                    elif event.key == pygame.K_DOWN:
                        self.selected_option = (self.selected_option + 1) % len(self.options)
                        play_random_menu_sound(self.audio_manager)
                    elif event.key == pygame.K_ESCAPE:
                        self.selected_option = 0
                        self.scene_manager.return_to_previous_scene()
                    elif event.key == pygame.K_RETURN:
                        play_return_sound(self.audio_manager)
                        self.execute_selected_option()

    def execute_selected_option(self):
        selected = self.options[self.selected_option]

        if selected == "Продовжити":
            self.scene_manager.return_to_previous_scene()
        elif selected == "Головне меню":
            self.confirming = True
            self.confirm_action = "menu"
            self.selected_confirm_option = 1
        elif selected == "Вийти":
            self.confirming = True
            self.confirm_action = "quit"
            self.selected_confirm_option = 1

    def update(self):
        self.update_background_animation()

    def render(self, screen):
        # Фон
        screen_size = screen.get_size()
        if self.bg_frames:
            bg = self.bg_frames[self.frame_index]
            bg_scaled = pygame.transform.smoothscale(bg, screen.get_size())
            screen.blit(bg_scaled, (0, 0))

        # Текстові кнопки
        padding_x, padding_y = 40, 20
        font_height = self.font.get_height()
        button_width = max(self.font.size(opt)[0] for opt in self.options) + padding_x
        button_height = font_height + padding_y

        center_x = screen_size[0] // 2
        start_y = screen_size[1] // 2 - (len(self.options) * button_height) // 2

        for i, option in enumerate(self.options):
            is_selected = (i == self.selected_option)
            color = (255, 255, 255) if is_selected else (150, 150, 150)
            alpha = 200 if is_selected else 100

            x = center_x - button_width // 2
            y = start_y + i * button_height

            self._draw_button(screen, x, y, button_width, button_height, color, alpha, option)

        if self.confirming:
            self.render_confirmation_dialog(screen)

    def render_confirmation_dialog(self, screen):
        screen_w, screen_h = screen.get_size()

        # Розміри діалогу: 50% ширини і 20% висоти екрану
        dialog_width = screen_w // 2
        dialog_height = screen_h // 5
        x = (screen_w - dialog_width) // 2
        y = (screen_h - dialog_height) // 2

        # Тло
        pygame.draw.rect(screen, (30, 30, 30, 230), (x, y, dialog_width, dialog_height), border_radius=12)
        pygame.draw.rect(screen, (255, 255, 255), (x, y, dialog_width, dialog_height), 3, border_radius=12)

        # Текст
        message = "Весь прогрес буде втрачено. Продовжити?"
        message_font = pygame.font.Font(resource_path("assets/menu_font.otf"), int(dialog_height * 0.2))
        message_surface = message_font.render(message, True, (255, 255, 255))
        message_rect = message_surface.get_rect(center=(screen_w // 2, y + dialog_height // 3))
        screen.blit(message_surface, message_rect)

        # Кнопки "Так" і "Ні"
        button_font = pygame.font.Font(resource_path("assets/menu_font.otf"), int(dialog_height * 0.25))
        button_y = y + int(dialog_height * 0.65)

        for i, option in enumerate(self.confirm_options):
            color = (255, 255, 255) if i == self.selected_confirm_option else (150, 150, 150)
            btn_surface = button_font.render(option, True, color)
            offset = 100  # відстань від центру
            btn_x = screen_w // 2 - offset if i == 0 else screen_w // 2 + offset
            btn_rect = btn_surface.get_rect(center=(btn_x, button_y))
            screen.blit(btn_surface, btn_rect)

    def _draw_button(self, screen, x, y, w, h, text_color, alpha, text):
        # Фон з градієнтною прозорістю
        surface = pygame.Surface((w, h), pygame.SRCALPHA)
        for px in range(w):
            a = int(alpha * (1 - abs((px - w / 2) / (w / 2))))
            pygame.draw.line(surface, (0, 0, 0, a), (px, 0), (px, h))
        screen.blit(surface, (x, y))

        # Текст
        rendered_text = self.font.render(text, True, text_color)
        text_rect = rendered_text.get_rect(center=(x + w // 2, y + h // 2))
        screen.blit(rendered_text, text_rect)