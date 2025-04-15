class SceneManager:
    """
    Керує сценами гри: дозволяє перемикатися між ними, повертатися назад, знищувати старі сцени та зберігати стан.
    """
    def __init__(self, audio_manager):
        self.scenes = {}              # {"menu": lambda: MainMenu(...)}
        self.current_scene = None
        self.previous_scene = None    # Зберігає попередню сцену для "повернення"
        self.audio_manager = audio_manager
        self.running = True

    def add_scene(self, name, scene_factory):
        """Додає сцену (як функцію створення) до менеджера."""
        self.scenes[name] = scene_factory

    def change_scene(self, name):
        """Перемикається на нову сцену, створюючи її динамічно."""
        if name not in self.scenes:
            return

        if self.current_scene:
            if name == "pause":
                if self.previous_scene is None:
                    self.previous_scene = self.current_scene
            else:
                # Знищуємо стару сцену (повне очищення ресурсів)
                if hasattr(self.current_scene, "destroy"):
                    self.current_scene.destroy()
                self.current_scene = None

                # Якщо починається нова гра — обнуляємо попередню сцену
                if name == "scene_1":
                    self.previous_scene = None

        # Створюємо нову сцену через фабрику
        factory = self.scenes.get(name)
        self.current_scene = factory() if callable(factory) else factory

        if self.previous_scene and name == self.previous_scene.name:
            self.current_scene.resume()
            self.previous_scene = None
        else:
            self.current_scene.start()

    def return_to_previous_scene(self):
        if self.previous_scene:
            if hasattr(self.current_scene, "destroy"):
                self.current_scene.destroy()
            self.current_scene = self.previous_scene
            self.previous_scene = None  # ← ЦЕ ВАЖЛИВО
            self.current_scene.resume()

    def reset(self):
        """
        Закриває всі сцени, очищає попередню та поточну.
        """
        if self.current_scene:
            self.current_scene.stop()
        self.previous_scene = None
        self.current_scene = None

    def get_current_scene_name(self):
        """Повертає ім’я поточної сцени."""
        for name, factory in self.scenes.items():
            if self.current_scene and factory == self.current_scene:
                return name
        return None

    def handle_events(self, events):
        """Передає обробку подій поточній сцені."""
        if self.current_scene:
            self.current_scene.handle_events(events)

    def update(self):
        """Оновлює логіку поточної сцени."""
        if self.current_scene:
            self.current_scene.update()

    def render(self, screen):
        """Відмальовує поточну сцену."""
        if self.current_scene:
            self.current_scene.render(screen)

    def quit_game(self):
        """Завершує гру."""
        self.running = False