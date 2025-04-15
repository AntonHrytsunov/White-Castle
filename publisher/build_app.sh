#!/bin/zsh

echo "⚙️  Збірка White Castle.app через PyInstaller..."

cd ..
PYINSTALLER="./.venv/bin/pyinstaller"
ICON_PATH="assets/icon.icns"

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

echo "🧹 Очищення тимчасових файлів..."

rm -f "White Castle.spec" > /dev/null 2>&1
rm -rf build > /dev/null 2>&1

echo "✅ Збірка завершена"