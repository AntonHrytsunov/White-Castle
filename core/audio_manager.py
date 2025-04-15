import pygame
import random
import logging
from utils.resource_loader import resource_path


class AudioManager:
    """
    Менеджер звуку: музика, ефекти, гучність, кешування.
    """
    def __init__(self, music_volume=0.5, sound_volume=0.5):
        pygame.mixer.init()

        self.music_volume = music_volume
        self.sound_volume = sound_volume
        self.current_music = None
        self.sounds = {}

        pygame.mixer.music.set_volume(self.music_volume)
        self.update_sound_channels()

    def play_music(self, file_path, loops=-1):
        full_path = resource_path(file_path)
        self.stop_music()
        try:
            pygame.mixer.music.load(full_path)
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(loops)
            self.current_music = full_path
        except Exception as e:
            pass

    def stop_music(self):
        pygame.mixer.music.stop()
        self.current_music = None

    def stop_music_fade(self, fade_time=2000):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.fadeout(fade_time)
            self.current_music = None

    def pause_music(self):
        pygame.mixer.music.pause()

    def resume_music(self):
        pygame.mixer.music.unpause()

    def play_sound(self, file_or_sound):
        try:
            if isinstance(file_or_sound, pygame.mixer.Sound):
                sound = file_or_sound
            else:
                file_path = file_or_sound
                if file_path not in self.sounds:
                    full_path = resource_path(file_path)
                    self.sounds[file_path] = pygame.mixer.Sound(full_path)

                sound = self.sounds[file_path]

            sound.set_volume(self.sound_volume)
            sound.play()

        except Exception as e:
            pass

    def set_music_volume(self, volume):
        self.music_volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.music_volume)

    def set_sfx_volume(self, volume):
        self.sound_volume = max(0.0, min(1.0, volume))
        self.update_sound_channels()

    def update_sound_channels(self):
        pygame.mixer.set_num_channels(8)
        for i in range(pygame.mixer.get_num_channels()):
            channel = pygame.mixer.Channel(i)
            channel.set_volume(self.sound_volume)

    def play_looping_sound(self, file_path, loops=-1):
        """
        Відтворення звуку в циклі. Повертає канал, у якому відтворюється звук.
        """
        try:
            if file_path not in self.sounds:
                full_path = resource_path(file_path)
                self.sounds[file_path] = pygame.mixer.Sound(full_path)

            sound = self.sounds[file_path]
            sound.set_volume(self.sound_volume)

            # Знайти вільний канал і програти
            channel = pygame.mixer.find_channel()
            if channel:
                channel.play(sound, loops=loops)
                return channel
            else:
                return None

        except Exception as e:
            return None

def play_random_menu_sound(audio_manager):
    sounds = [
        "assets/sfx/menu_click1.mp3",
        "assets/sfx/menu_click2.mp3"
    ]
    audio_manager.play_sound(random.choice(sounds))

def play_return_sound(audio_manager):
    audio_manager.play_sound("assets/sfx/return.mp3")

