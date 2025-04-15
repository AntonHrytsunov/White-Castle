#!/bin/zsh

REPO="AntonHrytsunov/White-Castle"
TAG="v0.1.0"
DMG_NAME="White.Castle.dmg"
HASH_NAME="White.Castle.dmg.sha256.txt"
DOWNLOAD_DIR="$(pwd)/release_verify"


mkdir -p "$DOWNLOAD_DIR"
cd "$DOWNLOAD_DIR"

echo "📥 Завантаження файлів з релізу $TAG..."

gh release download "$TAG" --repo "$REPO" --pattern "$DMG_NAME" --pattern "$HASH_NAME" --clobber > /dev/null 2>&1

if [[ ! -f "$DMG_NAME" || ! -f "$HASH_NAME" ]]; then
  echo "❌ Не вдалося завантажити файли"
  exit 1
fi

echo "🔍 Перевірка SHA256..."

EXPECTED_HASH=$(cut -d ' ' -f1 < "$HASH_NAME")
ACTUAL_HASH=$(shasum -a 256 "$DMG_NAME" | cut -d ' ' -f1)

cd ..

if [ "$EXPECTED_HASH" = "$ACTUAL_HASH" ]; then
  echo "✅ Хеш сума вірна — файл не змінено"
  rm -rf "$DOWNLOAD_DIR"
else
  echo "❌ Хеш сума не збігається — файл може бути пошкоджений або змінений"
  rm -rf "$DOWNLOAD_DIR"
  exit 2
fi
