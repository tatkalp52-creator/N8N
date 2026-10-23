#!/bin/sh
# Обновление сборщика и страничек одной командой (в терминале контейнера сборщика):
#   wget -qO- https://raw.githubusercontent.com/tatkalp52-creator/N8N/ccr-592d85a5-ljre1x/assembler/update.sh | sh
# Потом Restart (не Deploy). Пока идёт сборка — не запускать.
B=https://raw.githubusercontent.com/tatkalp52-creator/N8N/ccr-592d85a5-ljre1x
ok=1
get() { wget -qO "$2.new" "$B/$1" && [ -s "$2.new" ] && mv "$2.new" "$2" || { rm -f "$2.new"; echo "не скачалось: $1"; ok=0; }; }
mkdir -p /app/pages/leaves /app/pages/refs
old=$(grep -m1 'ASSEMBLER_VERSION =' /app/app.py 2>/dev/null)
get assembler/app.py /app/app.py
get table_drafts/razmetka_animacii.html /app/pages/razmetka.html
get table_drafts/pult_zvuka.html /app/pages/pult.html
get table_drafts/suno_sborshik.html /app/pages/suno.html
# референсы художника — на своём сервере, чтобы не зависеть от приватности репозитория (23.10)
get table_drafts/refs/ref2_bez_slov.png /app/pages/refs/ref2_bez_slov.png
for i in 01 02 03 04 05 06 07 08 09 10 11 12; do get table_drafts/leaves_thumbs/t$i.png /app/pages/leaves/t$i.png; done
new=$(grep -m1 'ASSEMBLER_VERSION =' /app/app.py)
echo "$new"
if [ $ok != 1 ]; then echo "что-то не скачалось — старые файлы остались, сборщик рабочий"
elif [ "$old" = "$new" ]; then echo "готово — сборщик тот же, Restart НЕ нужен (странички уже обновились)"
else echo "готово — сборщик новый, теперь Restart"; fi
