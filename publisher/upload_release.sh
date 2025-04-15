#!/bin/zsh

APP_NAME="White Castle"
DMG_NAME="$APP_NAME.dmg"
DMG_PATH="$(pwd)/dist/$DMG_NAME"
HASH_PATH="$(pwd)/dist/$DMG_NAME.sha256.txt"
RELEASE_TAG="v0.1.0"

echo "🔐 Генерація SHA256..."

shasum -a 256 "$DMG_PATH" > "$HASH_PATH"

echo "🚀 Завантаження $DMG_NAME і хешу на GitHub Release $RELEASE_TAG..."

# Створює реліз (ігнорує, якщо вже існує)
gh release create "$RELEASE_TAG" --title "$RELEASE_TAG" --notes "White Castle Release $RELEASE_TAG" || true

# Завантажує файли
gh release upload "$RELEASE_TAG" "$DMG_PATH" "$HASH_PATH" --clobber

echo "✅ Файли успішно завантажено на GitHub Release"