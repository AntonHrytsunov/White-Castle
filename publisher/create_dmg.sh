#!/bin/zsh

APP_NAME="White Castle"
APP_PATH="../dist/$APP_NAME.app"
DMG_NAME="$APP_NAME.dmg"
VOL_NAME="Install $APP_NAME"
OUTPUT_PATH="../dist/$DMG_NAME"
BACKGROUND="$(pwd)/dmg_assets/background.png"

echo "📦 Створення красивого $DMG_NAME..."

rm -f "$OUTPUT_PATH"

create-dmg \
  --volname "$VOL_NAME" \
  --volicon "../assets/icon.icns" \
  --background "$BACKGROUND" \
  --window-size 1024 1024 \
  --icon-size 120 \
  --icon "$APP_NAME.app" 350 300 \
  --app-drop-link 670 300 \
  "$OUTPUT_PATH" \
  "$APP_PATH"

if [[ $? -eq 0 ]]; then
    echo "✅ $DMG_NAME створено з фоном"
else
    echo "❌ Помилка створення красивого .dmg"
fi