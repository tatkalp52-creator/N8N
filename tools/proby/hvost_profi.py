# Хвост по-аниматорски: цепочка позвонков, у каждого свой поворот; все повторяют одну кривую основания,
# каждый следующий позже (задержка от основания к кончику), к кончику гибкость больше. Форму не задаём — она складывается сама.
import sys, math, numpy as np, subprocess
from PIL import Image, ImageDraw, ImageFont
OUT7_ = sys.argv[1]; MODE7_ = sys.argv[2] if len(sys.argv) > 2 else 'lines'
sys.argv = ['x', '/dev/null', 'none']
exec(open('duga2.py').read().split("def ss(")[0])
TOTAL = 190.0          # на сколько градусов в сумме поворачиваются все позвонки, когда хвост наверху
FLEX = 1.6             # во сколько раз кончик гибче основания
DELAY = 0.55           # за сколько секунд импульс доходит от основания до кончика
HOLD, UP, TOP, DOWN = 5.0, 2.6, 0.5, 1.4   # лежит, медленно вверх, зависает, быстрее вниз
dens = 1 + (FLEX - 1) * s; dens = dens / dens.sum() * math.radians(TOTAL)   # поворот на каждый позвонок
def ease(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
def f(t):              # кривая основания: 0 — лежит, 1 — наверху
    t -= HOLD
    if t < 0: return 0.0
    if t < UP: return ease(t / UP)
    t -= UP
    if t < TOP: return 1.0
    return 1 - ease((t - TOP) / DOWN)
def at(t):
    rot = np.array([f(t - DELAY * x) for x in s]) * dens   # поворот каждого позвонка в этот миг
    return th0 + np.cumsum(rot), np.ones(len(s))            # угол звена = нарисованный + сумма поворотов до него
CYCLE = HOLD + UP + TOP + DOWN + DELAY + 0.3
if MODE7_ == 'lines':
    Z = 4; im = Image.fromarray(np.clip(O, 0, 255).astype(np.uint8)).resize(((x1 - x0) * Z, (y1 - y0) * Z), Image.LANCZOS)
    d = ImageDraw.Draw(im); fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 24)
    T = np.arange(HOLD, CYCLE, 0.35)
    for k, t in enumerate(T):
        up = t < HOLD + UP + TOP * 0.5
        col = (255, 60, 60) if up else (255, 255, 255)
        Pp = (build_p(*at(t)) - [x0, y0]) * Z
        d.line([tuple(p) for p in Pp], fill=col, width=4, joint='curve')
        d.text(tuple(Pp[-1] + [-12, -28]), str(k + 1), fill=col, font=fnt, stroke_width=3, stroke_fill=(0, 0, 0))
    d.text((14, 10), 'каждые 0.35 с: красное — вверх, белое — вниз', fill=(255, 240, 200), font=fnt, stroke_width=3, stroke_fill=(0, 0, 0))
    im.save(OUT7_); sys.exit()
fps = 24; n = int(round(CYCLE * fps)); w, h = x1 - x0, y1 - y0
crop = MODE7_ == 'crop'; size = (w, h) if crop else (690, 750)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '10' if crop else '16', '-pix_fmt', 'yuv444p' if crop else 'yuv420p', OUT7_], stdin=subprocess.PIPE)
for rep in range(1 if crop else 2):
    for fi in range(n):
        im = Image.fromarray(np.clip(frame_p(*at(fi / fps)), 0, 255).astype(np.uint8))
        p.stdin.write(np.asarray(im if crop else im.resize(size, Image.LANCZOS)).tobytes())
p.stdin.close(); p.wait()
