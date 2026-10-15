# Танец хвоста Micah Buzan на нашем коте С УЧЁТОМ ПОВЕРХНОСТИ: его кривые как есть, но хвост не уходит ниже книги —
# где его линия ныряет вниз, хвост ложится на обложку и скользит по ней (длина та же).
# Вверх: его 5 → 6 → 7 (верх). Вниз: его 1 → 2 → 3 → лежит (наш нарисованный).
import sys, math, numpy as np
from PIL import Image, ImageDraw, ImageFont
OUT9_ = sys.argv[1]; MODE9_ = sys.argv[2] if len(sys.argv) > 2 else 'lines'
sys.argv = ['x', OUT9_, 'none']
exec(open('buzan.py').read().split("ORDER = ")[0])
R = build_p(th0, np.ones(len(s)))                       # лежащий хвост = низ: ниже него книга
order = np.argsort(R[:, 0]); RX, RY = R[order, 0], R[order, 1]
def floor_y(x):                                         # верх обложки под хвостом (левее кончика — как у кончика)
    return np.interp(x, RX, RY, left=RY[0], right=RY[-1]) + 1.5
def on_surface(th):
    out = th.copy(); p = np.array(BASE, float)
    for j in range(len(th)):
        a = out[j]
        for _ in range(400):                            # ныряет в книгу — поворачиваем звено вверх, пока не ляжет на обложку
            q = p + step * np.array([math.cos(a), math.sin(a)])
            if q[1] <= floor_y(q[0]): break
            a += math.radians(1) if math.cos(a) < 0 else -math.radians(1)
        out[j] = a; p = q
    return out
UPP = [5, 6, 7]; DOWNP = [1, 2, 3]
SP = {k: on_surface(POSE[k]) for k in UPP + DOWNP}
if MODE9_ == 'lines':
    Z = 4; im = Image.fromarray(np.clip(O, 0, 255).astype(np.uint8)).resize(((x1 - x0) * Z, (y1 - y0) * Z), Image.LANCZOS)
    d = ImageDraw.Draw(im); fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 26)
    for k in UPP + DOWNP:
        col = (255, 60, 60) if k in UPP else (255, 255, 255)
        Pp = (build_p(SP[k], np.ones(len(s))) - [x0, y0]) * Z
        d.line([tuple(p) for p in Pp], fill=col, width=5, joint='curve')
        d.text(tuple(Pp[-1] + [-12, -30]), str(k), fill=col, font=fnt, stroke_width=3, stroke_fill=(0, 0, 0))
    d.text((14, 10), 'его кривые, хвост не ниже книги: вверх 5-6-7, вниз 1-2-3', fill=(255, 240, 200), font=fnt, stroke_width=3, stroke_fill=(0, 0, 0))
    im.save(OUT9_)
