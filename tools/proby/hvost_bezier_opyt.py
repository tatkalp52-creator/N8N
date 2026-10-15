# Опыт только с геометрией средней линии (по ТЗ): покой — точный нарисованный хвост; поднятая поза — 3 кубических Безье
# с явными касательными у основания, в изгибе и у кончика; форма между ними — несколько параметров (углы касательной
# в 6 узлах вдоль хвоста), один плавный ход t, без задержек. Длина — наша (точки строятся постоянным шагом).
import sys, math, numpy as np
from PIL import Image, ImageDraw, ImageFont
OUTD_ = sys.argv[1]; MODED_ = sys.argv[2] if len(sys.argv) > 2 else 'debug'
sys.argv = ['x', OUTD_, 'none']
exec(open('buzan2.py').read().split("UPP = ")[0])
# поднятая поза: точки картинки (x, y); основание = BASE, выход из основания почти как у лежащего хвоста
SEGS = [[(1206, 613), (1192, 612), (1172, 607), (1160, 593)],     # основание: спокойно влево, начинает подниматься
        [(1160, 593), (1150, 581), (1144, 562), (1147, 545)],     # широкий изгиб вверх
        [(1147, 545), (1149, 534), (1158, 527), (1167, 528)]]     # кончик чуть загибается к спине
def bez(P, u): P = np.array(P, float); return ((1-u)**3)[:, None]*P[0] + (3*(1-u)**2*u)[:, None]*P[1] + (3*(1-u)*u**2)[:, None]*P[2] + (u**3)[:, None]*P[3]
pts = np.concatenate([bez(S, np.linspace(0, 1, 200)) for S in SEGS])
d_ = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]; L_b = d_[-1]
u_ = np.linspace(0, d_[-1], 600); X = np.interp(u_, d_, pts[:, 0]); Y = np.interp(u_, d_, pts[:, 1])
a_ = np.unwrap(np.arctan2(np.gradient(Y), np.gradient(X)))
TH_UP = np.interp(s, np.linspace(0, 1, len(a_)), a_)                  # касательная поднятой позы по длине хвоста
TH_UP += 2 * math.pi * round((th0[0] - TH_UP[0]) / (2 * math.pi))
KN = np.array([0, 0.15, 0.35, 0.6, 0.85, 1.0])                         # узлы: компактное описание формы
def pchip(xk, yk, x):
    h = np.diff(xk); dl = np.diff(yk) / h; m = np.zeros_like(yk)
    for i in range(1, len(xk) - 1):
        m[i] = 0 if dl[i-1] * dl[i] <= 0 else (2 * h[i] + h[i-1] + h[i] + 2 * h[i-1]) / ((2 * h[i] + h[i-1]) / dl[i-1] + (h[i] + 2 * h[i-1]) / dl[i])
    m[0], m[-1] = dl[0], dl[-1]
    i = np.clip(np.searchsorted(xk, x) - 1, 0, len(xk) - 2); t = (x - xk[i]) / h[i]
    return (2*t**3 - 3*t**2 + 1) * yk[i] + (t**3 - 2*t**2 + t) * h[i] * m[i] + (-2*t**3 + 3*t**2) * yk[i+1] + (t**3 - t**2) * h[i] * m[i+1]
DK = np.interp(KN, s, TH_UP - th0)                                    # 6 чисел: насколько повернуть касательную в узлах
def ease(t): t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)
def shape_new(t):  return th0 + pchip(KN, DK * ease(t), s)             # новая модель: 6 параметров, один ход
def shape_old(t):  return th0 * (1 - ease(t)) + TH_UP * ease(t)        # прежняя: смешиваем 160 углов
if MODED_ == 'debug':
    Z = 3; base = Image.fromarray(np.clip(O, 0, 255).astype(np.uint8)).resize(((x1 - x0) * Z, (y1 - y0) * Z), Image.LANCZOS)
    fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20); out = Image.new('RGB', (base.width * 2, base.height))
    cols = [(120, 220, 255), (255, 200, 60), (255, 120, 60), (255, 60, 160), (255, 60, 60)]
    for k, (title, fn) in enumerate([('НОВАЯ: 6 параметров', shape_new), ('ПРЕЖНЯЯ: 160 углов', shape_old)]):
        im = base.copy(); d = ImageDraw.Draw(im)
        for j, t in enumerate([0, 0.25, 0.5, 0.75, 1.0]):
            Pp = (build_p(fn(t), np.ones(len(s))) - [x0, y0]) * Z
            d.line([tuple(p) for p in Pp], fill=cols[j], width=3, joint='curve')
            d.text(tuple(Pp[-1] + [-10, -24]), str(t), fill=cols[j], font=fnt, stroke_width=3, stroke_fill=(0, 0, 0))
        if k == 0:
            for S in SEGS:                                             # контрольные точки Безье поднятой позы
                Q = (np.array(S, float) - [x0, y0]) * Z
                d.line([tuple(q) for q in Q], fill=(160, 160, 160), width=1)
                for q in Q: d.ellipse([q[0]-4, q[1]-4, q[0]+4, q[1]+4], outline=(255, 255, 255))
        d.text((10, 8), title + ' — t = 0, .25, .5, .75, 1', fill=(255, 240, 200), font=fnt, stroke_width=3, stroke_fill=(0, 0, 0))
        out.paste(im, (k * base.width, 0))
    out.save(OUTD_)
    print('длина Безье', round(L_b, 1), 'длина хвоста', round(step * (N - 1), 1))
