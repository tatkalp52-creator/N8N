# Третья (средняя) поза на t = 0.5: хвост поднят наполовину, но уже плавная дуга. Интерполяция по участкам
# покой → середина и середина → верх (6 параметров формы, один ход t, без задержек). Два варианта середины:
# А — горб с рисунка автора (красная линия 3 «вверх»); Б — середина, заданная кривыми Безье.
import sys, math, numpy as np
from PIL import Image, ImageDraw, ImageFont
OUTE_ = sys.argv[1]
exec(open('bezier.py').read().split("if MODED_ == 'debug':")[0])
Kk = 544 / 1920; OXk, OYk = 880, 385
HUMP = [(1165,770),(1080,795),(1000,772),(940,738),(900,712),(840,700),(800,705),(785,715)]   # её горб (кадр кота 1920)
def tang(pts):
    P = np.array(pts, float); dd = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    uu = np.linspace(0, dd[-1], 600); Xx = np.interp(uu, dd, P[:, 0]); Yy = np.interp(uu, dd, P[:, 1])
    aa = np.unwrap(np.arctan2(np.gradient(Yy), np.gradient(Xx))); aa = np.convolve(np.pad(aa, 20, mode='edge'), np.ones(41) / 41, 'valid')
    th = np.interp(s, np.linspace(0, 1, len(aa)), aa); return th + 2 * math.pi * round((th0[0] - th[0]) / (2 * math.pi))
MID_A = tang([(OXk + x * Kk, OYk + y * Kk) for x, y in HUMP]); MID_A += th0[0] - MID_A[0]     # основание — как у нарисованного
SEG_B = [[(1206, 613), (1192, 611), (1172, 604), (1158, 592)], [(1158, 592), (1146, 582), (1128, 574), (1112, 578)]]
pB = np.concatenate([bez(S_, np.linspace(0, 1, 200)) for S_ in SEG_B]); MID_B = tang(pB)
def shape3(t, MID):
    dm = np.interp(KN, s, MID - th0); u = ease(t)
    dk = dm * (u / 0.5) if u <= 0.5 else dm + (DK - dm) * ((u - 0.5) / 0.5)
    return th0 + pchip(KN, dk, s)
Z = 3; base = Image.fromarray(np.clip(O, 0, 255).astype(np.uint8)).resize(((x1 - x0) * Z, (y1 - y0) * Z), Image.LANCZOS)
fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20); out = Image.new('RGB', (base.width * 2, base.height))
cols = [(120, 220, 255), (255, 200, 60), (255, 120, 60), (255, 60, 160), (255, 60, 60)]
for k, (title, MID) in enumerate([('А: середина = твой горб', MID_A), ('Б: середина = дуга Безье', MID_B)]):
    im = base.copy(); d = ImageDraw.Draw(im)
    for j, t in enumerate([0, 0.25, 0.5, 0.75, 1.0]):
        Pp = (build_p(on_surface(shape3(t, MID)), np.ones(len(s))) - [x0, y0]) * Z
        d.line([tuple(p) for p in Pp], fill=cols[j], width=3, joint='curve')
        d.text(tuple(Pp[-1] + [-10, -24]), str(t), fill=cols[j], font=fnt, stroke_width=3, stroke_fill=(0, 0, 0))
    d.text((10, 8), title + ' — t = 0, .25, .5, .75, 1', fill=(255, 240, 200), font=fnt, stroke_width=3, stroke_fill=(0, 0, 0))
    out.paste(im, (k * base.width, 0))
out.save(OUTE_)
