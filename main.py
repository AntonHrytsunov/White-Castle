import pygame
import logging
import time
import traceback
import sys
import os

from core.scene_manager import SceneManager
from core.audio_manager import AudioManager
from utils.resource_loader import load_settings, load_progress
from scenes.menu import MainMenu
from scenes.pause import PauseMenu
from scenes.settings import SettingsMenu
from scenes.confirm_new_game import ConfirmNewGame
from scenes.confirm_out import ConfirmOut
from scenes.scene_1 import Scene1
from scenes.hero_creator import HeroCreator
from scenes.level_1 import Level1


def get_save_path(filename):
    base_dir = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "White_Castle")
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, filename)

SAVE_FILE = get_save_path("progress.json")
SETTINGS_FILE = get_save_path("settings.json")

def log_uncaught_exceptions(ex_cls, ex, tb):
    text = ''.join(traceback.format_exception(ex_cls, ex, tb))
    print("❌ Невиловлена помилка:\n", text)  # Виводить у консоль
    with open("/tmp/white_castle_error.log", "w") as f:
        f.write(text)

sys.excepthook = log_uncaught_exceptions


# ⏯️ Завантаження налаштувань
settings = load_settings()

# 🔊 Ініціалізація Pygame
pygame.init()
pygame.mixer.init()

# 🖱️ Приховати курсор
last_mouse_move_time = time.time()
mouse_visible = True
HIDE_DELAY = 3  # секунд

# 📺 Створення екрану
if settings["fullscreen"]:
    screen = pygame.display.set_mode((settings["screen_width"], settings["screen_height"]), pygame.FULLSCREEN)
else:
    screen = pygame.display.set_mode((settings["screen_width"], settings["screen_height"]))
pygame.display.set_caption("White Castle")

# 🎧 Менеджер звуку
audio_manager = AudioManager(
    music_volume=settings["music_volume"] / 10,
    sound_volume=settings["sound_volume"] / 10
)

# 🎮 Менеджер сцен
scene_manager = SceneManager(audio_manager)

# 🔗 Додавання сцен як функцій-фабрик
scene_manager.add_scene("menu", lambda: MainMenu(scene_manager, audio_manager, load_progress()))
scene_manager.add_scene("settings", lambda: SettingsMenu(scene_manager, audio_manager, settings))
scene_manager.add_scene("ConfirmNewGame", lambda: ConfirmNewGame(scene_manager, audio_manager))
scene_manager.add_scene("ConfirmOut", lambda: ConfirmOut(scene_manager, audio_manager))
scene_manager.add_scene("pause", lambda: PauseMenu(scene_manager, audio_manager))
scene_manager.add_scene("scene_1", lambda: Scene1(scene_manager, audio_manager))
scene_manager.add_scene("HeroCreator", lambda: HeroCreator(scene_manager, audio_manager))
scene_manager.add_scene("level_1", lambda: Level1(scene_manager, audio_manager))

# ▶️ Стартова сцена
scene_manager.change_scene("menu")

# 🔁 Головний цикл гри
clock = pygame.time.Clock()
while scene_manager.running:
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            scene_manager.quit_game()

        # 📎 Сполучення клавіш: Command + Esc
        if event.type == pygame.KEYDOWN:
            keys = pygame.key.get_pressed()
            if (keys[pygame.K_LMETA] or keys[pygame.K_RMETA]) and keys[pygame.K_ESCAPE]:
                scene_manager.quit_game()

        # 🖱️ Відстеження руху миші
        if event.type == pygame.MOUSEMOTION:
            last_mouse_move_time = time.time()
            if not mouse_visible:
                pygame.mouse.set_visible(True)
                mouse_visible = True

    # 🕶️ Приховати мишу, якщо не рухалась понад HIDE_DELAY
    if mouse_visible and time.time() - last_mouse_move_time > HIDE_DELAY:
        pygame.mouse.set_visible(False)
        mouse_visible = False

    scene_manager.handle_events(events)
    scene_manager.update()
    scene_manager.render(screen)

    pygame.display.flip()
    clock.tick(30)

pygame.quit()