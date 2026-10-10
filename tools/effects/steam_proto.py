# Проба «рисованного пара» (01.10, автор: «это ГЕНИАЛЬНО»). Прототип для сборщика:
# три карандашные струйки с завитками рождаются у поверхности напитка, текут вверх
# и тают; петля 3 с бесшовная (всё периодично по t). Без нейросетей.
# Запуск: python3 steam_proto.py картинка.jpg cx sy out_dir   (cx, sy — точка поверхности напитка, px)
import sys, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

src = Image.open(sys.argv[1]).convert('RGB')
cx, sy = int(sys.argv[2]), int(sys.argv[3])
out_dir = sys.argv[4]
os.makedirs(out_dir, exist_ok=True)
W, H = src.size
base = np.asarray(src, float)
bw, bh = 150, 165            # область пара (при кадре 1536x864)
x0, y0 = cx - bw // 2, sy - bh
SS = 4                       # суперсэмплинг — мягкие края штрихов
fps, T = 24, 3.0
N = int(fps * T)
rng = np.random.default_rng(3)
wisps = [dict(bx=-10, A=15, f=1.6, ph=0.0, m=2.0, mp=0.1, w=1.1),
         dict(bx=1, A=19, f=1.4, ph=2.3, m=2.4, mp=0.55, w=1.3),
         dict(bx=11, A=13, f=1.8, ph=4.1, m=1.8, mp=0.85, w=1.0)]
# неподвижное «бумажное зерно», как у карандаша
grain = np.asarray(Image.fromarray(rng.uniform(0, 255, (bh, bw)).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)), float) / 255
grain = 0.6 + 0.4 * grain
color = np.array([246, 241, 231], float)
for fr in range(N):
    t = fr / N
    can = Image.new('L', (bw * SS, bh * SS), 0)
    d = ImageDraw.Draw(can)
    for w in wisps:
        S = 140
        pts = []
        for k in range(S + 1):
            s = k / S
            x = bw / 2 + w['bx'] * (1 - 0.5 * s) + w['A'] * s ** 0.9 * math.sin(2 * math.pi * (w['f'] * s - t) + w['ph'])
            y = bh - 1 - s * (bh - 6)
            pts.append((x, y, s))
        for k in range(S):
            xa, ya, s = pts[k]
            xb, yb, _ = pts[k + 1]
            fade = min(1, s / 0.04) * max(0, min(1, (0.95 - s) / 0.45))
            dash = 0.5 + 0.5 * math.sin(2 * math.pi * (w['m'] * s - 2 * t) + w['mp'] * 6.28)
            a = fade * (0.3 + 0.7 * dash ** 1.3)
            if a <= 0.01:
                continue
            width = (2.0 + 3.8 * s) * w['w']
            d.line([(xa * SS, ya * SS), (xb * SS, yb * SS)], fill=int(255 * a), width=max(1, int(width * SS)))
    alpha = np.asarray(can.resize((bw, bh), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.9)), float) / 255
    alpha = alpha * grain * 0.62
    out = base.copy()
    reg = out[y0:y0 + bh, x0:x0 + bw]
    out[y0:y0 + bh, x0:x0 + bw] = reg * (1 - alpha[..., None]) + color * alpha[..., None]
    Image.fromarray(out.astype(np.uint8)).save(f'{out_dir}/{fr:03d}.png')
