# Опускание не по тому же пути назад (тогда первым опустился бы кончик), а основанием первым, кончик последним:
# верх → J с её рисунка (основание ниже, кончик ещё вверху) → основание легло, кончик поднят → лежит.
import sys, math, numpy as np
OUTG_ = sys.argv[1]; MODEG_ = sys.argv[2] if len(sys.argv) > 2 else 'lines'
src = open('tri_pozy.py').read().split("Z = 3; base")[0]; sys.argv = ['x', OUTG_]; exec(src)
from PIL import Image, ImageDraw, ImageFont
J_LINE = [(1168,765),(1080,782),(1000,786),(960,776),(900,750),(870,725),(856,690),(852,640)]   # её «вниз 2 (J)»
MID_J = tang([(OXk + x * Kk, OYk + y * Kk) for x, y in J_LINE]); MID_J += th0[0] - MID_J[0]
xx = np.clip((s - 0.45) / 0.55, 0, 1); LAYB = th0 + math.radians(115) * xx * xx * (3 - 2 * xx)   # основание легло, кончик поднят
HALF = th0 + math.radians(50) * xx * xx * (3 - 2 * xx)          # основание лежит, кончик опущен наполовину (её просьба)
DOWN_POSES = [TH_UP, MID_J, LAYB, HALF, th0]
def _pts(th): return build_p(th0 + pchip(KN, np.interp(KN, s, th - th0), s), np.ones(len(s)))
_dist = [0.5 * np.hypot(*(_pts(a) - _pts(b)).T).mean() + 0.5 * np.hypot(*(_pts(a) - _pts(b)).T).max() for a, b in zip(DOWN_POSES[:-1], DOWN_POSES[1:])]
_ts = np.r_[0, np.cumsum(_dist)] / sum(_dist)                    # моменты поз — по пройденному пути: скорость ровная, без затыка
DOWN_KEYS = list(zip(_ts, DOWN_POSES))
def shape_down(t):
    u = ease(t); dks = [np.interp(KN, s, P_ - th0) for _, P_ in DOWN_KEYS]; ts = [k for k, _ in DOWN_KEYS]
    i = min(np.searchsorted(ts, u, side='right') - 1, len(ts) - 2); a = (u - ts[i]) / (ts[i + 1] - ts[i])
    return th0 + pchip(KN, dks[i] + (dks[i + 1] - dks[i]) * a, s)
HOLD, UP, TOPH, DOWN = 5.0, 2.8, 0.4, 1.6                 # медленно вверх, быстрее вниз
def at(t):
    t -= HOLD
    if t <= 0: th = th0
    elif t < UP: th = shape3(t / UP, MID_A)
    elif t < UP + TOPH: th = shape3(1.0, MID_A)
    elif t < UP + TOPH + DOWN: th = shape_down((t - UP - TOPH) / DOWN)
    else: th = th0
    return on_surface(th), np.ones(len(s))
CYCLE = HOLD + UP + TOPH + DOWN + 0.4
if MODEG_ == 'lines':
    Z = 3; im = Image.fromarray(np.clip(O, 0, 255).astype(np.uint8)).resize(((x1 - x0) * Z, (y1 - y0) * Z), Image.LANCZOS)
    d = ImageDraw.Draw(im); fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
    for j, t in enumerate([0, 0.2, 0.4, 0.55, 0.7, 0.85, 1.0]):
        Pp = (build_p(on_surface(shape_down(t)), np.ones(len(s))) - [x0, y0]) * Z
        d.line([tuple(p) for p in Pp], fill=(255, 255, 255), width=3, joint='curve')
        d.text(tuple(Pp[-1] + [-10, -24]), str(t), fill=(255, 255, 255), font=fnt, stroke_width=3, stroke_fill=(0, 0, 0))
    d.text((10, 8), 'ВНИЗ: t = 0 … 1, основание первым', fill=(255, 240, 200), font=fnt, stroke_width=3, stroke_fill=(0, 0, 0)); im.save(OUTG_); sys.exit()
import subprocess
fps = 24; n = int(round(CYCLE * fps)); w_, h_ = x1 - x0, y1 - y0; crop = MODEG_ == 'crop'; size = (w_, h_) if crop else (690, 750)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '10' if crop else '16', '-pix_fmt', 'yuv444p' if crop else 'yuv420p', OUTG_], stdin=subprocess.PIPE)
for rep in range(1 if crop else 2):
    for fi in range(n):
        im = Image.fromarray(np.clip(frame_p(*at(fi / fps)), 0, 255).astype(np.uint8))
        p.stdin.write(np.asarray(im if crop else im.resize(size, Image.LANCZOS)).tobytes())
p.stdin.close(); p.wait()
