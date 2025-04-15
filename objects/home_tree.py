import pygame
import logging
from utils.resource_loader import resource_path

class HomeTree:
    def __init__(self, position_x, scale_x, scale_y, screen_height):
        logging.info("[HomeTree] Ініціалізація Дерева лісовика")

        # Координата X у світі
        self.position_x_world = position_x

        # Завантаження текстури
        original_image = pygame.image.load(resource_path("assets/level_1/home_tree/home_tree.png")).convert_alpha()

        # Масштабування зображення
        self.image = pygame.transform.scale(
            original_image,
            (
                int(original_image.get_width() * scale_x),
                int(original_image.get_height() * scale_y)
            )
        )

        self.rect = self.image.get_rect()
        self.rect.bottom = screen_height - int(screen_height * 0.065)  # Вирівнювання по шару ближніх дерев

        self.player_near = False

    def update(self, hero_world_x):
        # Розрахунок дистанції між героєм та деревом
        distance_to_player = abs(self.position_x_world - hero_world_x)

        # Перевірка відстані
        if distance_to_player <= 300 and not self.player_near:
            self.player_near = True
            print("Гравець біля дерева")
            logging.info("[HomeTree] Гравець наблизився до дерева")

        elif distance_to_player > 300 and self.player_near:
            self.player_near = False

    def draw(self, screen, world_x):
        # Визначення екранних координат
        screen_x = self.position_x_world - world_x
        self.rect.x = screen_x
        screen.blit(self.image, self.rect)