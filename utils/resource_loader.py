import os
import sys
import json

def resource_path(relative_path):
    """Повертає абсолютний шлях до ресурсу (працює і з PyInstaller, і під час розробки)"""
    try:
        base_path = sys._MEIPASS  # для PyInstaller
    except AttributeError:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return os.path.join(base_path, relative_path)


def load_settings(filename="settings.json"):
    full_path = get_save_path(filename)
    if not os.path.exists(full_path):
        return {
            "screen_width": 1280,
            "screen_height": 720,
            "fullscreen": True,
            "music_volume": 5,
            "sound_volume": 5
        }
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {}

def save_settings(settings, settings_file="settings.json"):
    """Зберігає налаштування у JSON-файл у постійну директорію користувача"""
    full_path = get_save_path(settings_file)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)

def save_progress(scene_name):
    path = get_save_path("progress.json")

    try:
        # Спроба завантажити існуючі дані
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                data = {}
    except (FileNotFoundError, json.JSONDecodeError):
        # Якщо файл не існує або пошкоджений — створюємо новий словник
        data = {}

    # Оновлюємо тільки сцену
    data["last_scene"] = scene_name

    # Записуємо назад
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_progress(filename="progress.json"):
    full_path = get_save_path(filename)
    if not os.path.exists(full_path):
        return None
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("last_scene")
    except Exception as e:
        return None


def load_hero_stats(filename="progress.json"):
    """
    Завантажує дані про героя з файлу збереження.
    Завжди повертає словник (можливо, порожній).
    """
    full_path = get_save_path(filename)

    if not os.path.exists(full_path):
        return {}

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            hero_data = data.get("hero")
            if isinstance(hero_data, dict):
                return hero_data
            else:
                return {}
    except Exception as e:
        return {}

def get_user_data_path():
    """Повертає директорію для збереження користувацьких файлів (на кшталт save/settings)"""
    if getattr(sys, 'frozen', False):  # Якщо збірка через PyInstaller
        if sys.platform == "darwin":  # macOS
            base_dir = os.path.expanduser("~/Library/Application Support/White_Castle")
        elif sys.platform == "win32":
            base_dir = os.path.join(os.environ.get("APPDATA", "."), "White_Castle")
        else:  # Linux або інше
            base_dir = os.path.expanduser("~/.white_castle")
    else:
        # Під час розробки — у папку проєкту
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    os.makedirs(base_dir, exist_ok=True)
    return base_dir


def get_save_path(filename):
    base_dir = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "White_Castle")
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, filename)