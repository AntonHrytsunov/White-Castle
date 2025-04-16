import pygame
import json
from PIL import Image
import logging
from utils.resource_loader import resource_path, load_settings, save_progress


class Scene1:
    def __init__(self, scene_manager, audio_manager):
        self.name = "scene_1"
        self.scene_manager = scene_manager
        self.audio_manager = audio_manager
        self.settings = load_settings()

        pygame.mouse.set_visible(False)
        self.screen = pygame.display.get_surface()

        self.music_playlist = [
            ("assets/scene/intro/house.mp3", 1),
            ("assets/scene/intro/intro.mp3", 2000),
        ]
        self.image_sequence = [
            ("assets/scene/intro/house.gif", 10000, 2000, 2000),
            ("assets/scene/intro/village.gif", 10000, 2000, 2000),
            ("assets/scene/intro/village2.gif", 10000, 2000, 3000),
            ("assets/scene/intro/black.png", 8000, 2000, 0),
            ("assets/scene/intro/house2.gif", 5000, 2000, 1000),
            ("assets/scene/intro/map.png", 4750, 1000, 0),
            ("assets/scene/intro/house3.gif", 4000, 0, 100),
            ("assets/scene/intro/village_war.png", 4000, 100, 100),
            ("assets/scene/intro/image2.png", 8000, 0, 1000),
            ("assets/scene/intro/image3.png", 10000, 500, 3000),
            ("assets/scene/intro/black.png", 3000, 1500, 1500),
            ("assets/scene/intro/dark_wood.gif", 13000, 4000, 0),
        ]
        self.texts = [
            (" ", 2000, 0, 0),
            ("Наш герой мав усе, про що можна було мріяти.", 8000, 2000, 1000),
            ("Спокійне життя, затишок і безтурботні дні.", 10000, 1000, 2000),
            ("Його дім стояв на околиці мирного містечка.", 10000, 2000, 3000),
            ("", 2000, 0, 0),
            ("Але він не здогадувався...", 4000, 500, 2000),
            ("", 2000, 0, 0),
            ("...що з півночі та сходу насувається темрява.", 5000, 2000, 1000),
            ("Королівство стоїть на межі загибелі...", 4750, 0, 0),
            ("В одну мить він утратив усе.", 4000, 0, 100),
            ("Його місто впало під натиском ворога.", 4000, 100, 0),
            ("Армії пітьми спопелили його рідний край.", 8000, 100, 1000),
            ("Нечисть залишає по собі лише попіл і смерть.", 10000, 1000, 3000),
            (" ", 4000, 0, 0),
            ("Герой дивом уцілів і, рятуючись, зник у темних хащах...", 7000, 1000, 1000),
            (" ", 10000, 0, 0),
        ]

        self.image_data = []
        for path, *_ in self.image_sequence:
            full_path = resource_path(path)
            if path.endswith(".gif"):
                gif = Image.open(full_path)
                frames = []
                durations = []
                previous_frame = None

                for frame in range(gif.n_frames):
                    gif.seek(frame)
                    duration = 300
                    "duration = gif.info.get('duration', 100)"

                    # Конвертуємо в RGBA для прозорості
                    current_frame = gif.convert("RGBA")

                    if previous_frame is not None:
                        # Поєднуємо попередній кадр з поточним (щоб зберегти повну картинку)
                        composed = Image.alpha_composite(previous_frame, current_frame)
                    else:
                        composed = current_frame.copy()

                    previous_frame = composed.copy()

                    # Конвертація до Surface
                    frame_surface = pygame.image.fromstring(
                        composed.tobytes(), composed.size, composed.mode
                    ).convert_alpha()

                    scaled_surface = pygame.transform.scale(frame_surface, self.screen.get_size())
                    frames.append(scaled_surface)
                    durations.append(duration)

                self.image_data.append({
                    "type": "gif",
                    "frames": frames,
                    "durations": durations
                })
            else:
                image = pygame.image.load(full_path).convert_alpha()
                self.image_data.append({"type": "static", "image": image})

        self.font = pygame.font.Font(resource_path("assets/menu_font.otf"), 40)

        self.current_image_index = 0
        self.current_text_index = 0
        self.fade_alpha = 0
        self.text_alpha = 0
        self.fading_in = True
        self.fading_out = False
        self.text_fading_in = True
        self.text_fading_out = False

        self.is_paused = False
        self.music_paused = False
        self.music_position = 0.0
        self.current_music_index = 0

        self.start_time = pygame.time.get_ticks()
        self.text_start_time = pygame.time.get_ticks()

        self.gif_frame_index = 0
        self.gif_frame_time = 0

        pygame.mixer.music.set_endevent(pygame.USEREVENT + 10)
        self.pause_before_next_track = 0

    def start(self):
        pygame.mixer.music.stop()

        self.current_image_index = 0
        self.current_text_index = 0
        self.fade_alpha = 0
        self.text_alpha = 0
        self.fading_in = True
        self.fading_out = False
        self.text_fading_in = True
        self.text_fading_out = False
        self.is_paused = False
        self.start_time = pygame.time.get_ticks()
        self.text_start_time = pygame.time.get_ticks()

        self.current_music_index = 0

        self.music_paused = False
        self.play_next_track()

        self.gif_frame_index = 0
        self.gif_frame_time = 0
        self.last_tick = pygame.time.get_ticks()

    def play_next_track(self):
        if self.current_music_index < len(self.music_playlist):
            track, pause = self.music_playlist[self.current_music_index]

            pygame.mixer.music.set_endevent(pygame.USEREVENT + 10)
            self.audio_manager.play_music(track, loops=0)

            self.pause_before_next_track = pause
            self.current_music_index += 1

    def update(self):
        if self.is_paused:
            return

        current_time = pygame.time.get_ticks()
        elapsed = current_time - self.start_time
        # Якщо GIF, оновлюємо кадр
        current_image_data = self.image_data[self.current_image_index]
        if current_image_data["type"] == "gif":
            # Вираховуємо скільки мс минуло з моменту початку анімації зображення
            gif_elapsed = pygame.time.get_ticks() - self.start_time
            durations = current_image_data["durations"]
            total_duration = sum(durations)

            # Робимо так, щоб gif циклічно прокручувався в межах total_duration
            gif_elapsed %= total_duration

            cumulative = 0
            for i, dur in enumerate(durations):
                cumulative += dur
                if gif_elapsed < cumulative:
                    self.gif_frame_index = i
                    break

        text_elapsed = current_time - self.text_start_time

        # --- Тривалість кадру ---
        _, img_duration, fade_in, fade_out = self.image_sequence[self.current_image_index]
        _, text_duration, text_fade_in, text_fade_out = self.texts[self.current_text_index]

        if self.fading_in:
            self.fade_alpha = min(255, (elapsed / fade_in) * 255) if fade_in else 255
            if self.fade_alpha >= 255:
                self.fading_in = False

        if self.text_fading_in:
            self.text_alpha = min(255, (text_elapsed / text_fade_in) * 255) if text_fade_in else 255
            if self.text_alpha >= 255:
                self.text_fading_in = False

        if not self.fading_out and elapsed > img_duration - fade_out:
            self.fading_out = True
        if not self.text_fading_out and text_elapsed > text_duration - text_fade_out:
            self.text_fading_out = True

        if self.fading_out:
            fade_elapsed = elapsed - (img_duration - fade_out)
            self.fade_alpha = max(0, 255 - (fade_elapsed / fade_out) * 255) if fade_out else 0

        if self.text_fading_out:
            fade_elapsed = text_elapsed - (text_duration - text_fade_out)
            self.text_alpha = max(0, 255 - (fade_elapsed / text_fade_out) * 255) if text_fade_out else 0

        if elapsed > img_duration:
            self.current_image_index += 1
            if self.current_image_index >= len(self.image_data):
                self.scene_manager.change_scene("HeroCreator")
                return
            self.start_time = current_time
            self.fading_in = True
            self.fading_out = False
            self.fade_alpha = 0

        if text_elapsed > text_duration:
            self.current_text_index += 1
            self.text_start_time = current_time
            self.text_fading_in = True
            self.text_fading_out = False
            self.text_alpha = 0

    def render(self, screen):
        current_image_data = self.image_data[self.current_image_index]
        if current_image_data["type"] == "gif":
            current_image = current_image_data["frames"][self.gif_frame_index]
        else:
            current_image = pygame.transform.scale(current_image_data["image"], screen.get_size())
        scaled = pygame.transform.scale(current_image, screen.get_size())
        faded = scaled.copy()
        faded.fill((255, 255, 255, int(self.fade_alpha)), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(faded, (0, 0))

        if self.current_text_index < len(self.texts):
            text = self.font.render(self.texts[self.current_text_index][0], True, (255, 255, 255))
            text.set_alpha(self.text_alpha)
            rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() - 60))
            screen.blit(text, rect)

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.audio_manager.stop_music()
                    self.scene_manager.change_scene("HeroCreator")
                elif event.key == pygame.K_ESCAPE:
                    self.pause()


            elif event.type == pygame.USEREVENT + 10:
                pygame.time.set_timer(pygame.USEREVENT + 11, self.pause_before_next_track, loops=1)

            elif event.type == pygame.USEREVENT + 11:
                self.play_next_track()

    def pause(self):
        self.is_paused = True
        pygame.mixer.music.pause()
        self.music_paused = True
        self.scene_manager.change_scene("pause")
        save_progress(self.name)

    def resume(self):
        self.is_paused = False
        if self.music_paused:
            pygame.mixer.music.unpause()
            self.music_paused = False

    def stop(self):
        pygame.mixer.music.stop()
        pygame.mixer.stop()
        pygame.time.set_timer(pygame.USEREVENT + 1, 0)

    def destroy(self):
        self.stop()
        self.image_data.clear()
