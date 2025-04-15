import pygame
import logging
from PIL import Image, ImageSequence

from utils.resource_loader import resource_path, load_settings, save_settings
from core.audio_manager import play_return_sound, play_random_menu_sound


class SettingsMenu:
    def __init__(self, scene_manager, audio_manager, settings):
        self.name = "settings"
        self.scene_manager = scene_manager
        self.audio_manager = audio_manager
        self.settings = settings



        self.screen = None

        self.options = ["Гучність музики", "Гучність ефектів", "Розмір екрану", "Назад"]
        self.selected_option = 0
        self.screen_sizes = [(1024, 864), (1280, 720), (1440, 900), (1920, 1200)]
        self.original_screen_size = (self.settings["screen_width"], self.settings["screen_height"])
        self.screen_size_changed = False

        self.bg_frames = []
        self.frame_index = 0
        self.frame_delay = 2
        self.current_delay = 0
        self.reverse = False
        self.load_gif_frames(resource_path("assets/menu/menu_bg/setting_menu.gif"))

        self.font = pygame.font.Font(resource_path("assets/menu_font.otf"), 50)

    def load_gif_frames(self, gif_path):
        try:
            pil_image = Image.open(gif_path)
            for frame in ImageSequence.Iterator(pil_image):
                frame = frame.convert("RGBA")
                surface = pygame.image.fromstring(frame.tobytes(), frame.size, frame.mode).convert_alpha()
                self.bg_frames.append(surface)
        except Exception as e:
            pass

    def start(self):
        self.screen = pygame.display.get_surface()
        self.audio_manager.set_music_volume(self.settings["music_volume"] / 10)
        self.audio_manager.set_sfx_volume(self.settings["sound_volume"] / 10)

    def stop(self):
        save_settings(self.settings)
        self.audio_manager.set_sound_volume(self.settings["sound_volume"] / 10)

    def destroy(self):
        self.bg_frames.clear()

    def pause(self): pass

    def resume(self): pass

    def update(self):
        self.update_background_animation()

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
                if event.key in [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]:
                    self.play_menu_navigation_sound()

                if event.key == pygame.K_UP:
                    self.selected_option = (self.selected_option - 1) % len(self.options)
                elif event.key == pygame.K_DOWN:
                    self.selected_option = (self.selected_option + 1) % len(self.options)
                elif event.key == pygame.K_LEFT:
                    self.adjust_setting(-1)
                elif event.key == pygame.K_RIGHT:
                    self.adjust_setting(1)
                elif event.key in [pygame.K_RETURN, pygame.K_ESCAPE]:
                    self.play_safe_return_sound()
                    self.scene_manager.change_scene("menu")


    def adjust_setting(self, delta):
        if self.selected_option == 0:
            self.settings["music_volume"] = max(0, min(10, self.settings["music_volume"] + delta))
            self.audio_manager.set_music_volume(self.settings["music_volume"] / 10)
        elif self.selected_option == 1:
            self.settings["sound_volume"] = max(0, min(10, self.settings["sound_volume"] + delta))
            self.audio_manager.set_sfx_volume(self.settings["sound_volume"] / 10)
        elif self.selected_option == 2:
            cur_size = (self.settings["screen_width"], self.settings["screen_height"])
            index = self.screen_sizes.index(cur_size) if cur_size in self.screen_sizes else 0
            new_size = self.screen_sizes[(index + delta) % len(self.screen_sizes)]
            self.settings["screen_width"], self.settings["screen_height"] = new_size
            self.screen_size_changed = new_size != self.original_screen_size

        save_settings(self.settings)

    def render(self, screen):
        if self.bg_frames:
            bg = self.bg_frames[self.frame_index]
            scaled = pygame.transform.smoothscale(bg, screen.get_size())
            screen.blit(scaled, (0, 0))

        screen_width, screen_height = screen.get_size()
        padding_x, padding_y = 40, 20
        menu_x = screen_width // 2
        font_height = self.font.get_height()
        max_width = max(self.font.size(self.options[i])[0] for i in range(len(self.options)))
        button_w = max_width + padding_x
        button_h = font_height + padding_y
        menu_y = screen_height // 2 - len(self.options) * button_h // 2

        for i, label in enumerate(self.options):
            if i == 0:
                text = f"{label}: {self.settings['music_volume']}"
            elif i == 1:
                text = f"{label}: {self.settings['sound_volume']}"
            elif i == 2:
                text = f"{label}: {self.settings['screen_width']}x{self.settings['screen_height']}"
            else:
                text = label

            is_selected = self.selected_option == i
            color = (255, 255, 255) if is_selected else (150, 150, 150)
            alpha = 200 if is_selected else 120
            x = menu_x - button_w // 2
            y = menu_y + i * button_h

            button_surface = pygame.Surface((button_w, button_h), pygame.SRCALPHA)
            for px in range(button_w):
                a = int(alpha * (1 - abs((px - button_w / 2) / (button_w / 2))))
                pygame.draw.line(button_surface, (0, 0, 0, a), (px, 0), (px, button_h))
            screen.blit(button_surface, (x, y))

            rendered = self.font.render(text, True, color)
            screen.blit(rendered, rendered.get_rect(center=(x + button_w // 2, y + button_h // 2)))

        if self.screen_size_changed:
            warning = pygame.font.Font(None, 28).render(
                "Зміни екрану вступлять в силу після перезапуску гри", True, (255, 200, 0)
            )
            screen.blit(warning, warning.get_rect(center=(screen_width // 2, screen_height - 40)))

    def play_menu_navigation_sound(self):
        self.audio_manager.set_sfx_volume(self.settings["sound_volume"] / 10)
        play_random_menu_sound(self.audio_manager)

    def play_safe_return_sound(self):
        self.audio_manager.set_sfx_volume(self.settings["sound_volume"] / 10)
        play_return_sound(self.audio_manager)