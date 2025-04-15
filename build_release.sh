#!/bin/zsh

echo "🔧 Запуск повної збірки релізу White Castle..."

echo ""
echo "1️⃣ Збірка .app..."
./publisher/build_app.sh || { echo "❌ Помилка під час збірки .app"; exit 1 }

echo ""
echo "3️⃣ Створення .dmg..."
./publisher/create_dmg.sh || { echo "❌ Помилка під час створення .dmg"; exit 1 }

echo ""
echo "4️⃣ Завантаження на GitHub Release..."
./publisher/upload_release.sh || { echo "❌ Помилка під час завантаження на GitHub"; exit 1 }

echo ""
echo "5️⃣ Перевірка завантаженого релізу..."
./publisher/verify_release.sh || { echo "❌ Помилка перевірки релізу"; exit 1 }

echo ""
echo "✅ Реліз White Castle завершено успішно!"