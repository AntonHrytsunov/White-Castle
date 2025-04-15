#!/bin/zsh

APP_NAME="White Castle"
APP_PATH="$(pwd)/dist/$APP_NAME.app"
DMG_NAME="$APP_NAME.dmg"
VOL_NAME="Install $APP_NAME"
OUTPUT_PATH="$(pwd)/dist/$DMG_NAME"
BACKGROUND="$(pwd)/publisher/dmg_assets/background.png"

echo "📦 Створення $DMG_NAME..."

rm -f "$OUTPUT_PATH"

create-dmg \
  --volname "$VOL_NAME" \
  --volicon "$(pwd)/assets/icon.icns" \
  --background "$BACKGROUND" \
  --window-size 1024 1024 \
  --icon-size 120 \
  --icon "$APP_NAME.app" 350 300 \
  --app-drop-link 670 300 \
  "$OUTPUT_PATH" \
  "$APP_PATH" > /dev/null 2>&1

if [[ $? -eq 0 ]]; then
    echo "✅ $DMG_NAME створено."
else
    echo "❌ Помилка створення .dmg"
fi