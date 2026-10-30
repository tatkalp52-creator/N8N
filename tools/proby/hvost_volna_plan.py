# По плану аниматоров: две ключевые позы — 1 (нарисованный хвост) и верх (поза 4 со схемы Buzan, перед котом);
# промежуточные кадры — изгиб едет по длине хвоста от основания к кончику (волна): основание первым, кончик последним.
# Вниз так же от основания: основание уже опускается, кончик по инерции ещё вверху — S сама. Хвост не ниже книги.
import sys, math, numpy as np, subprocess
from PIL import Image, ImageDraw, ImageFont
OUTA_ = sys.argv[1]; MODEA_ = sys.argv[2] if len(sys.argv) > 2 else 'lines'
sys.argv = ['x', OUTA_, 'none']
exec(open('buzan2.py').read().split("if MODE9_ == 'lines':")[0])
TOP = SP[1]; TOP = TOP + 2 * math.pi * round((th0[0] - TOP[0]) / (2 * math.pi))   # та же ветка углов, что у нарисованного (без петель)
W = 0.45                                   # ширина изгиба, который едет по хвосту (доля длины)
HOLD, UP, TOPHOLD, DOWN = 5.0, 2.6, 0.4, 1.5
def ease(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)
def front(u):                              # где сейчас изгиб: от «до основания» до «за кончиком»
    return -W + (1 + 2 * W) * ease(u)
def wave(u):                               # доля «перешедших» звеньев: основание раньше, кончик позже
    return ease((front(u) - s) / W + 0.5)
def at(t):
    t -= HOLD
    if t <= 0: th = th0
    elif t < UP: w = wave(t / UP); th = th0 * (1 - w) + TOP * w
    elif t < UP + TOPHOLD: th = TOP
    elif t < UP + TOPHOLD + DOWN: w = wave((t - UP - TOPHOLD) / DOWN); th = TOP * (1 - w) + th0 * w
    else: th = th0
    return on_surface(th), np.ones(len(s))
CYCLE = HOLD + UP + TOPHOLD + DOWN + 0.3
if MODEA_ == 'lines':
    Z = 4; im = Image.fromarray(np.clip(O, 0, 255).astype(np.uint8)).resize(((x1 - x0) * Z, (y1 - y0) * Z), Image.LANCZOS)
    d = ImageDraw.Draw(im); fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 24)
    T = [HOLD + UP * f for f in (0.18, 0.36, 0.54, 0.72)] + [HOLD + UP + 0.1] + [HOLD + UP + TOPHOLD + DOWN * f for f in (0.4, 0.6, 0.8)]
    for k, t in enumerate(T):
        col = (255, 60, 60) if t < HOLD + UP + 0.2 else (255, 255, 255)
        Pp = (build_p(*at(t)) - [x0, y0]) * Z
        d.line([tuple(p) for p in Pp], fill=col, width=4, joint='curve')
        d.text(tuple(Pp[-1] + [-12, -28]), str(k + 2), fill=col, font=fnt, stroke_width=3, stroke_fill=(0, 0, 0))
    Pp = (build_p(th0, np.ones(len(s))) - [x0, y0]) * Z
    d.line([tuple(p) for p in Pp], fill=(120, 220, 255), width=4); d.text(tuple(Pp[-1] + [-12, -28]), '1', fill=(120, 220, 255), font=fnt, stroke_width=3, stroke_fill=(0, 0, 0))
    d.text((14, 10), '1 нарисованный; вверх 2-6 (6 = верх), вниз 7-9; изгиб едет от основания', fill=(255, 240, 200), font=fnt, stroke_width=3, stroke_fill=(0, 0, 0))
    im.save(OUTA_); sys.exit()
fps = 24; n = int(round(CYCLE * fps)); w_, h_ = x1 - x0, y1 - y0
crop = MODEA_ == 'crop'; size = (w_, h_) if crop else (690, 750)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '10' if crop else '16', '-pix_fmt', 'yuv444p' if crop else 'yuv420p', OUTA_], stdin=subprocess.PIPE)
for rep in range(1 if crop else 2):
    for fi in range(n):
        im = Image.fromarray(np.clip(frame_p(*at(fi / fps)), 0, 255).astype(np.uint8))
        p.stdin.write(np.asarray(im if crop else im.resize(size, Image.LANCZOS)).tobytes())
p.stdin.close(); p.wait()
