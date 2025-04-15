import pygame
import random
import math
import re
import os
import logging
from utils.resource_loader import resource_path

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Crow:
    # === 🔧 Налаштовувані параметри ===
    MIN_TRIGGER_DISTANCE = 300
    MAX_TRIGGER_DISTANCE = 500

    ACCELERATION = 1
    INITIAL_SPEED = 15
    MAX_SPEED = 35
    FLIGHT_ANGLE_MIN = 40
    FLIGHT_ANGLE_MAX = 100

    OFFSCREEN_DELAY = 3000

    SCREEN_MARGIN = 100
    FLIGHT_DELAY_RANGE = (0, 500)

    WALK_SPEED = 150
    WALK_DECISION_INTERVAL = (2000, 5000)     # Час до прийняття рішення про рух
    WALK_DURATION_RANGE = (1000, 3000)        # Скільки часу ворона буде ходити
    WALK_PROBABILITY = 0.1                    # Ймовірність, що ворона буде ходити

    def __init__(self, x, y, idle_frames, fly_frames, walk_frames, audio_manager, start_frame=0):
        self.x_world = x  # Світова позиція
        self.y = y
        self.audio_manager = audio_manager
        self.manager = None

        self.FRAME_DELAY = 100
        self.FLIGHT_SOUND_DELAY = random.randint(0, 400)

        self.is_flying = False
        self.pending_flight = False
        self.off_screen = False
        self.trigger_distance = random.randint(self.MIN_TRIGGER_DISTANCE, self.MAX_TRIGGER_DISTANCE)

        self.speed = self.INITIAL_SPEED
        self.flipped = random.choice([True, False])

        idle = [f.copy() for f in idle_frames]
        fly = [f.copy() for f in fly_frames]
        if self.flipped:
            idle = [pygame.transform.flip(f, True, False) for f in idle]
            fly = [pygame.transform.flip(f, True, False) for f in fly]
        self.idle_frames = idle
        # Картання (caw)
        self.caw_frames = self.load_caw_frames()
        self.cawing = False
        self.caw_probability = 0.1  # Ймовірність почати "картати" при кожному update
        self.caw_sound_played = False

        self.fly_frames = fly

        self.current_animation = "idle"
        self.current_frame = start_frame
        self.frame_timer = 0
        self.frame_delay = self.FRAME_DELAY

        self.flight_sound_delay = self.FLIGHT_SOUND_DELAY
        self.flight_sound_timer = 0
        self.sound_played = False

        self.flight_started_at = None
        self.flight_start_delay = 0
        self.flight_delay_timer = 0

        # Ходьба
        self.walk_frames_original = [f.copy() for f in walk_frames]
        self.walk_frames = (
            self.walk_frames_original if not self.flipped
            else [pygame.transform.flip(f, True, False) for f in self.walk_frames_original]
        )
        self.walking = False
        self.walk_direction = 0
        self.walk_speed = self.WALK_SPEED
        self.walk_timer = 0
        self.next_walk_decision = random.randint(*self.WALK_DECISION_INTERVAL)
        self.walk_duration = 0
        self.walk_elapsed = 0

    def update(self, hero_world_x, dt, scroll_velocity):
        if self.off_screen:
            return

        if self.pending_flight:
            self.flight_delay_timer += dt
            if self.flight_delay_timer >= self.flight_start_delay:
                self.pending_flight = False
                self.is_flying = True
                self.flight_started_at = pygame.time.get_ticks()
                self.current_frame = 0
                self.frame_timer = 0
            else:
                return

        if self.is_flying:
            if not hasattr(self, 'flight_angle'):
                self.flight_angle = random.uniform(self.FLIGHT_ANGLE_MIN, self.FLIGHT_ANGLE_MAX)
            self.speed = min(self.speed + self.ACCELERATION * dt / 1000, self.MAX_SPEED)
            dx = self.speed * math.cos(math.radians(self.flight_angle))
            dy = -self.speed * math.sin(math.radians(self.flight_angle))
            self.x_world += dx
            self.y += dy

            screen = pygame.display.get_surface()
            if pygame.time.get_ticks() - self.flight_started_at > self.OFFSCREEN_DELAY:
                if (
                    self.x_world  < -self.SCREEN_MARGIN or self.x_world  > screen.get_width() + self.SCREEN_MARGIN or
                    self.y < -self.SCREEN_MARGIN or self.y > screen.get_height() + self.SCREEN_MARGIN
                ):
                    self.off_screen = True

            if not self.sound_played:
                self.flight_sound_timer += dt
                if self.flight_sound_timer >= self.flight_sound_delay:
                    self.play_caw_sound()
                    self.sound_played = True

        if not self.is_flying and not self.pending_flight:
            self.walk_timer += dt
            if self.walk_timer >= self.next_walk_decision:
                self.walk_timer = 0
                self.next_walk_decision = random.randint(*self.WALK_DECISION_INTERVAL)

                if random.random() < self.WALK_PROBABILITY:
                    self.walk_direction = random.choice([-1, 1])
                    self.walk_duration = random.randint(*self.WALK_DURATION_RANGE)
                    self.walk_elapsed = 0
                    self.walking = True
                    self.current_frame = 0
                    self.flipped = self.walk_direction == -1
                    self.walk_frames = (
                        [pygame.transform.flip(f, True, False) for f in self.walk_frames_original]
                        if self.flipped else self.walk_frames_original
                    )
                else:
                    self.walk_direction = 0
                    self.walking = False
                    # 🔇 Не чіпаємо current_frame — продовжується idle-анімація

                if not self.is_flying and not self.pending_flight and not self.walking and not self.cawing:
                    if random.random() < self.caw_probability:
                        self.cawing = True
                        self.current_frame = 0
                        self.frame_timer = 0
                        self.caw_sound_played = False

                self.walking = self.walk_direction != 0
                self.flipped = self.walk_direction == -1
                self.walk_frames = (
                    [pygame.transform.flip(f, True, False) for f in self.walk_frames_original]
                    if self.flipped else self.walk_frames_original
                )

            if self.walking:
                self.walk_elapsed += dt
                if self.walk_elapsed >= self.walk_duration:
                    self.walking = False
                    self.walk_direction = 0
                else:
                    delta = min(self.walk_speed * dt / 1000, 5)
                    self.x_world += delta * self.walk_direction

        self.frame_timer += dt
        frames = self.get_current_frames()

        if self.cawing:
            frames = self.caw_frames
            while self.frame_timer >= self.frame_delay:
                self.frame_timer -= self.frame_delay
                self.current_frame += 1

                if not self.caw_sound_played and self.current_frame >= 1:
                    self.audio_manager.play_sound(resource_path("assets/level_1/crow/idle/caw/caw.mp3"))
                    self.caw_sound_played = True

                if self.current_frame >= len(frames):
                    self.cawing = False
                    self.current_frame = 0

        while self.frame_timer >= self.frame_delay:
            self.frame_timer -= self.frame_delay
            if frames:
                self.current_frame = (self.current_frame + 1) % len(frames)

    def draw(self, screen, world_x):
        if self.off_screen:
            return
        current_image = self.get_current_frames()[self.current_frame]
        screen_x = int(self.x_world - world_x)
        screen.blit(current_image, (screen_x, self.y))

    def play_caw_sound(self):
        folder = resource_path("assets/level_1/crow")
        sound_files = [f for f in os.listdir(folder) if f.endswith((".mp3", ".wav", ".ogg"))]
        if sound_files:
            sound_path = os.path.join(folder, random.choice(sound_files))
            self.audio_manager.play_sound(sound_path)

    def start_flight(self):
        if self.is_flying or self.off_screen or self.pending_flight:
            return
        self.flight_start_delay = random.randint(*self.FLIGHT_DELAY_RANGE)
        self.flight_delay_timer = 0
        self.pending_flight = True

    def get_current_frames(self):
        if self.cawing:
            return self.caw_frames
        elif self.is_flying:
            return self.fly_frames
        elif self.walking:
            return self.walk_frames
        else:
            return self.idle_frames

    def load_caw_frames(self):
        folder = resource_path("assets/level_1/crow/idle/caw")
        frames = []
        try:
            filenames = sorted(
                [f for f in os.listdir(folder) if f.endswith(".png")],
                key=lambda name: int(re.match(r"(\d+)\.png", name).group(1))
            )
            for filename in filenames:
                img = pygame.image.load(os.path.join(folder, filename)).convert_alpha()
                if self.flipped:
                    img = pygame.transform.flip(img, True, False)
                frames.append(pygame.transform.scale(
                    img,
                    (int(img.get_width()), int(img.get_height()))  # масштаб можна адаптувати
                ))
        except Exception as e:
            logger.warning(f"[Crow] Не вдалося завантажити caw-кадри: {e}")
        return frames


class CrowManager:
    def __init__(self, audio_manager, screen, scale_x, scale_y):
        self.audio_manager = audio_manager
        self.active_sounds = []
        self.screen = screen
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.crows = []
        self.next_crow_x = 3500
        self.crow_spacing = random.randint(100000, 100000)

        self.idle_frames = []
        self.fly_frames = []
        self.walk_frames = []

    def load_animations(self):
        def load_frames(folder):
            frames = []
            try:
                def extract_number(filename):
                    match = re.match(r"(\d+)\.png", filename)
                    return int(match.group(1)) if match else float('inf')  # несумісні файли підуть в кінець

                for filename in sorted(os.listdir(folder), key=extract_number):
                    if filename.endswith(".png"):
                        frame = pygame.image.load(os.path.join(folder, filename)).convert_alpha()
                        scaled = pygame.transform.scale(
                            frame,
                            (int(frame.get_width() * self.scale_x), int(frame.get_height() * self.scale_y))
                        )
                        frames.append(scaled)
            except Exception as e:
                logger.error(f"[CrowManager] Помилка завантаження анімації з {folder}: {e}")
            return frames


        self.idle_frames = load_frames(resource_path("assets/level_1/crow/idle"))
        self.fly_frames = load_frames(resource_path("assets/level_1/crow/fly"))
        self.walk_frames = load_frames(resource_path("assets/level_1/crow/walk"))

    def spawn_group(self, x):
        group_size = random.randint(2, 4)
        spacing = int(random.randint(80, 130) * self.scale_x)
        group_id = random.randint(10000, 99999)

        for i in range(group_size):
            idle = [frame.copy() for frame in self.idle_frames]
            fly = [frame.copy() for frame in self.fly_frames]
            walk = [frame.copy() for frame in self.walk_frames]

            y = int(random.randint(650, 730) * self.scale_y) + random.randint(-20, 20)
            crow_x = x + i * spacing
            start_frame = random.randint(0, len(idle) - 1)

            crow = Crow(
                x=crow_x,
                y=y,
                idle_frames=idle,
                fly_frames=fly,
                walk_frames=walk,
                audio_manager=self.audio_manager,
                start_frame=start_frame
            )
            crow.group_id = group_id
            crow.trigger_distance = random.randint(300, 500)
            crow.manager = self
            self.crows.append(crow)

            logger.debug(f"[CrowManager] Створено ворону (група {group_id}) на x={crow_x}, y={y}")

    def update(self, hero_world_x, world_x, scroll_velocity, screen_width, dt):
        if world_x + screen_width > self.next_crow_x:
            self.spawn_group(self.next_crow_x)
            self.next_crow_x += random.randint(self.crow_spacing - 300, self.crow_spacing + 300)

        triggered_groups = set()
        for crow in self.crows:
            if not crow.is_flying and not crow.off_screen:
                dist = abs(crow.x_world - hero_world_x)
                if dist < crow.trigger_distance:
                    triggered_groups.add(getattr(crow, "group_id", None))

        for group_id in triggered_groups:
            for crow in self.crows:
                if not crow.is_flying and not crow.off_screen and crow.group_id == group_id:
                    crow.start_flight()

        for crow in self.crows:
            crow.update(hero_world_x, dt, scroll_velocity)

        self.crows = [c for c in self.crows if not c.off_screen]

    def draw(self, screen, world_x):
        for crow in self.crows:
            crow.draw(screen, world_x)

    def reset(self):
        self.crows.clear()
        self.next_crow_x = 2000
        self.crow_spacing = random.randint(2500, 4000)

    def stop_all_sounds(self):
        for sound_or_channel in self.active_sounds:
            try:
                sound_or_channel.stop()
            except Exception as e:
                pass
        self.active_sounds.clear()