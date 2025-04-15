import os
from PIL import Image

def process_image(image_path):
    image = Image.open(image_path).convert("RGBA")
    pixels = image.load()

    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = pixels[x, y]
            if a != 0:
                pixels[x, y] = (0, 0, 0, a)

    image.save(image_path)

def process_all_pngs(root_folder):
    for root, dirs, files in os.walk(root_folder):
        for file in files:
            if file.lower().endswith(".png"):
                full_path = os.path.join(root, file)
                print(f"Обробка: {full_path}")
                process_image(full_path)

# 🔁 Запусти обробку для поточної директорії
if __name__ == "__main__":
    current_folder = os.getcwd()
    process_all_pngs(current_folder)