import pygame
from utils.resource_loader import resource_path


class DialogBox:
    def __init__(self, screen, font_path, pause_player=True):
        self.screen = screen
        self.font = pygame.font.Font(resource_path(font_path), 24)
        self.active = False
        self.text = ""
        self.options = []
        self.selected_index = 0
        self.pause_player = pause_player
        self.on_select = None  # Функція, яка викликається при виборі

    def show(self, text, options, on_select=None, pause_player=True):
        self.text = text
        self.options = options
        self.selected_index = 0
        self.active = True
        self.on_select = on_select
        self.pause_player = pause_player

    def handle_event(self, event):
        if not self.active:
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_index = (self.selected_index - 1) % len(self.options)
            elif event.key == pygame.K_DOWN:
                self.selected_index = (self.selected_index + 1) % len(self.options)
            elif event.key == pygame.K_RETURN:
                if self.on_select:
                    self.on_select(self.selected_index, self.options[self.selected_index])
                self.active = False

    def update(self, dt):
        pass  # Для анімацій, якщо додаватимеш

    def draw(self):
        if not self.active:
            return

        box_width = self.screen.get_width() * 0.6
        box_height = self.screen.get_height() * 0.3
        box_x = (self.screen.get_width() - box_width) // 2
        box_y = self.screen.get_height() - box_height - 40

        pygame.draw.rect(self.screen, (20, 20, 20), (box_x, box_y, box_width, box_height), border_radius=12)
        pygame.draw.rect(self.screen, (100, 100, 255), (box_x, box_y, box_width, box_height), 3, border_radius=12)

        # Вивід тексту
        wrapped_text = self.wrap_text(self.text, box_width - 40)
        for i, line in enumerate(wrapped_text):
            surface = self.font.render(line, True, (230, 230, 230))
            self.screen.blit(surface, (box_x + 20, box_y + 20 + i * 28))

        # Вивід опцій
        for i, option in enumerate(self.options):
            prefix = " " if i == self.selected_index else "   "
            color = (255, 255, 255) if i == self.selected_index else (180, 180, 180)
            option_surface = self.font.render(prefix + option, True, color)
            self.screen.blit(option_surface, (box_x + 40, box_y + 120 + i * 30))

    def wrap_text(self, text, max_width):
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + word + " "
            if self.font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word + " "
        lines.append(current_line)
        return lines