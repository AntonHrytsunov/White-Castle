import pygame
import logging
from PIL import Image, ImageSequence

from utils.resource_loader import resource_path
from core.audio_manager import play_random_menu_sound, play_return_sound

logger = logging.getLogger("ConfirmOut")

class ConfirmOut:
    """
    Сцена підтвердження виходу з гри.
    """

    def __init__(self, scene_manager, audio_manager):
        self.name = "ConfirmOut"
        self.scene_manager = scene_manager
        self.audio_manager = audio_manager

        self.options = ["Так", "Ні"]
        self.selected_option = 1

        # Анімація фону
        self.bg_frames = []
        self.frame_index = 0
        self.reverse = False
        self.frame_delay = 2
        self.current_delay = 0

        self.font = pygame.font.Font(resource_path("assets/menu_font.otf"), 46)

    def start(self):
        logger.info("[ConfirmOut] Сцена активна")
        self.screen = pygame.display.get_surface()
        self.load_gif_frames(resource_path("assets/menu/menu_bg/out_img.gif"))
        self.frame_index = 0

    def stop(self):
        logger.info("[ConfirmOut] Сцена зупинена")

    def destroy(self):
        logger.info("[ConfirmOut] Звільнення ресурсів")

    def load_gif_frames(self, gif_path):
        try:
            pil_image = Image.open(gif_path)
            self.bg_frames = []

            for frame in ImageSequence.Iterator(pil_image):
                frame = frame.convert("RGBA")
                surface = pygame.image.fromstring(frame.tobytes(), frame.size, frame.mode).convert_alpha()
                self.bg_frames.append(surface)

        except Exception as e:
            logger.error(f"[ConfirmOut] Помилка завантаження GIF: {e}")

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_DOWN):
                    direction = -1 if event.key == pygame.K_UP else 1
                    self.selected_option = (self.selected_option + direction) % len(self.options)
                    play_random_menu_sound(self.audio_manager)
                elif event.key == pygame.K_RETURN:
                    play_return_sound(self.audio_manager)
                    if self.selected_option == 1:
                        logger.info("[ConfirmOut] Повернення до головного меню")
                        self.scene_manager.change_scene("menu")
                    else:
                        logger.info("[ConfirmOut] Завершення гри")
                        self.scene_manager.quit_game()
                elif event.key == pygame.K_ESCAPE:
                    play_return_sound(self.audio_manager)
                    logger.info("[ConfirmOut] ESC → Повернення до меню")
                    self.scene_manager.change_scene("menu")

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

        progress = self.frame_index / (len(self.bg_frames) - 1)
        self.frame_delay = int(5 * (1 - abs(2 * progress - 1))) + 1

        if self.current_delay < self.frame_delay:
            self.current_delay += 1
            return

        self.current_delay = 0
        if self.frame_index < len(self.bg_frames) - 1:
            self.frame_index += 1

    def render(self, screen):
        if self.bg_frames:
            frame = self.bg_frames[self.frame_index]
            scaled = pygame.transform.smoothscale(frame, screen.get_size())
            screen.blit(scaled, (0, 0))

        # Питання
        text_surface = self.font.render("Завершити пригоду?", True, (255, 255, 255))
        self._draw_text_with_background(screen, text_surface, y_offset=screen.get_height() // 5.5)

        # Кнопки
        button_w = 300
        button_h = 70
        base_y = screen.get_height() // 2.2

        for i, option in enumerate(self.options):
            is_selected = i == self.selected_option
            color = (255, 255, 255) if is_selected else (150, 150, 150)
            alpha = 200 if is_selected else 100
            x = screen.get_width() // 2 - button_w // 2
            y = base_y + i * (button_h + 10)
            self._draw_button(screen, option, x, y, button_w, button_h, color, alpha)

    def _draw_text_with_background(self, screen, text_surface, y_offset):
        padding_x, padding_y = 60, 20
        alpha = 180
        rect = text_surface.get_rect(center=(screen.get_width() // 2, y_offset))
        bg_surface = pygame.Surface((rect.width + padding_x, rect.height + padding_y), pygame.SRCALPHA)

        for x in range(bg_surface.get_width()):
            a = int(alpha * (1 - abs((x - bg_surface.get_width() / 2) / (bg_surface.get_width() / 2))))
            pygame.draw.line(bg_surface, (0, 0, 0, a), (x, 0), (x, bg_surface.get_height()))

        screen.blit(bg_surface, (rect.x - padding_x // 2, rect.y - padding_y // 2))
        screen.blit(text_surface, rect)

    def _draw_button(self, screen, text, x, y, w, h, text_color, alpha):
        button_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        for px in range(w):
            a = int(alpha * (1 - abs((px - w / 2) / (w / 2))))
            pygame.draw.line(button_surface, (0, 0, 0, a), (px, 0), (px, h))
        screen.blit(button_surface, (x, y))

        rendered_text = self.font.render(text, True, text_color)
        text_rect = rendered_text.get_rect(center=(x + w // 2, y + h // 2))
        screen.blit(rendered_text, text_rect)