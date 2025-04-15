#!/bin/zsh

APP_PATH="/Users/antonhrytsunov/Desktop/White Castle/dist/White Castle.app"
IDENTITY="Anton Hrytsunov"

echo "🔐 Підписування White Castle.app..."

# 🔍 Перевірка наявності .app
if [[ ! -d "$APP_PATH" ]]; then
  echo "❌ Помилка: файл $APP_PATH не існує"
  exit 1
fi

# 🧹 Очистка метаданих і Finder-сміття
xattr -cr "$APP_PATH"
dot_clean "$APP_PATH"

# 🔐 Підпис
codesign --deep --force --verbose=0 \
  --sign "$IDENTITY" \
  "$APP_PATH"
