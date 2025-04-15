#!/bin/zsh

APP_PATH="../dist/White Castle.app"
IDENTITY="Anton Hrytsunov"

echo "🔐 Підписування White Castle.app..."

# Очистка метаданих
xattr -cr "$APP_PATH"

# Підпис
codesign --deep --force --verbose=0 \
  --sign "$IDENTITY" \
  "$APP_PATH"

# Перевірка
VERIFY_RESULT=$(codesign --verify --deep --verbose=2 "$APP_PATH" 2>&1)

if [[ $? -eq 0 ]]; then
    echo "✅ Підпис перевірено успішно"
else
    echo "❌ Помилка перевірки підпису:"
    echo "$VERIFY_RESULT"
fi