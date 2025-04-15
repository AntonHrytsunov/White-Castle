#!/bin/zsh

# 📌 Отримуємо абсолютний шлях до кореня проєкту
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PYINSTALLER="$PROJECT_ROOT/.venv/bin/pyinstaller"
ICON_PATH="$PROJECT_ROOT/assets/icon.icns"

echo "⚙️  Збірка White Castle.app через PyInstaller..."

cd "$PROJECT_ROOT"

"$PYINSTALLER" \
  --name "White Castle" \
  --windowed \
  --clean \
  --noconfirm \
  --icon "$ICON_PATH" \
  --add-data "assets:assets" \
  --add-data "core:core" \
  --add-data "objects:objects" \
  --add-data "scenes:scenes" \
  --add-data "utils:utils" \
  --add-data "main.py:." \
  main.py > /dev/null 2>&1

if [[ ! -d "dist/White Castle.app" ]]; then
  echo "❌ Помилка: .app не створено"
  exit 1
fi

echo "🧹 Очищення тимчасових файлів..."
rm -f "White Castle.spec" > /dev/null 2>&1
rm -rf build > /dev/null 2>&1

echo "✅ Збірка завершена"
