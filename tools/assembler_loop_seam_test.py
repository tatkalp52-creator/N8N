"""Плавные петли эффектов не должны дёргаться — ни на стыке петли, ни внутри, при ЛЮБЫХ ручках.
(10.10: ручка «завитки» крутила завиток в 1.7 раза быстрее струйки — на каждом проходе струйки пар
прыгал; заметили только на живом выпуске.) Проверка: идём по петле кадр за кадром (24 к/с, включая
переход через конец петли) и ищем скачок — разницу между соседними кадрами, во много раз больше обычной.
Моргание и пузыри сюда не входят: у них резкие события по замыслу.
Запуск перед каждой правкой эффектов:  python3 tools/assembler_loop_seam_test.py   (numpy, pillow, flask, gdown)"""
import os, sys, tempfile
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "assembler"))
import app  # noqa: E402

rng = np.random.default_rng(1)
H, W = 864, 1536
img = rng.uniform(60, 200, (H, W, 3)).astype(np.uint8)
img[300:340, 900:910] = (255, 200, 90)  # тёплое пятно — «пламя» для свечи
path = os.path.join(tempfile.mkdtemp(), "img.png")
Image.fromarray(img).save(path)

LINES = {
    "пар: 50, 60": ("густота", "толщина", "высота", "скорость", "завитки", "прозрачность"),
    "пар: область 40 70, 60 70, 60 80, 40 80; облако 35 40, 65 40, 65 82, 35 82": ("густота", "высота", "скорость"),
    "дымок: 30, 30": ("густота", "толщина", "высота", "скорость"),
    "свеча: 59, 36": ("ореол", "раскачка"),
    "дождь: 70, 10, 90, 40": ("густота", "яркость", "капли"),
}
FPS, RATIO = 24, 2.0   # обычное движение даёт ≤ 1.3 медианы, рывок «завитков» 10.10 — 4.5…9
n = int(app.EFFECTS_LOOP_SECONDS * FPS)
bad = 0
for line, knobs in LINES.items():
    for word in knobs:
        for v in (1, 10):
            spec = app.parse_effects(f"{line}; {word} {v}")
            fr = [app.render_effects_loop(path, spec, {}, FPS, None, still_at=i / FPS) for i in range(n + 2)]
            d = np.array([np.abs(fr[i + 1] - fr[i]).mean() for i in range(n + 1)])
            med = float(np.median(d)) or 1e-9
            lim = RATIO * (2.0 if line.startswith("свеча") else 1.0)   # пламя трепещет по замыслу (быстрая частота 29 за петлю) — даёт до 3.2
            if d.max() > lim * med and d.max() > 0.002:
                bad += 1
                print(f"ДЁРГАЕТСЯ: «{line}; {word} {v}» — скачок в кадре {int(d.argmax())}, в {d.max() / med:.1f} раза больше обычного")
print("problems:", bad)
sys.exit(1 if bad else 0)
