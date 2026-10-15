# Хвост по схеме аниматора Micah Buzan («How To Animate a TAIL», 1:32 — 8 пронумерованных поз, основание в одной точке).
# Его позы сняты с кадра; на нашего кота переносим ИЗМЕНЕНИЕ формы относительно его лежачей позы 4 (наш нарисованный хвост остаётся как есть).
# Порядок для подъёма-опускания: 4 → 5 → 6 → 7 → 8 (вверх, медленно), 1 → 2 → 3 → 4 (вниз, быстрее).
import sys, math, numpy as np, subprocess
from PIL import Image, ImageDraw, ImageFont
OUT8_ = sys.argv[1]; MODE8_ = sys.argv[2] if len(sys.argv) > 2 else 'lines'
sys.argv = ['x', '/dev/null', 'none']
exec(open('duga2.py').read().split("def ss(")[0])
B = (325, 242)
HIS = {   # точки от основания к кончику, координаты его кадра
 4: [B, (318, 236), (300, 222), (275, 214), (250, 212), (232, 222), (215, 238), (195, 254), (170, 260), (150, 256), (138, 250)],
 5: [B, (330, 215), (325, 185), (310, 155), (290, 138), (265, 133), (240, 140), (218, 154), (198, 170)],
 6: [B, (345, 222), (352, 190), (345, 150), (325, 120), (300, 104), (275, 98), (240, 100)],
 7: [B, (352, 225), (366, 190), (369, 150), (362, 115), (348, 92), (330, 78)],
 8: [B, (360, 238), (392, 215), (412, 185), (424, 150), (424, 120), (418, 97)],
 1: [B, (305, 228), (280, 214), (258, 198), (242, 178), (234, 150), (232, 125), (232, 108)],
 2: [B, (327, 215), (318, 196), (298, 183), (270, 186), (245, 199), (222, 208), (202, 198), (184, 178), (172, 158), (165, 143)],
 3: [B, (322, 225), (308, 210), (290, 199), (268, 197), (245, 203), (220, 212), (195, 222), (170, 232), (148, 235), (134, 228), (128, 218)],
}
def angles(pts):
    P = np.array(pts, float); d = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    u = np.linspace(0, d[-1], 300); X = np.interp(u, d, P[:, 0]); Y = np.interp(u, d, P[:, 1])
    a = np.unwrap(np.arctan2(np.gradient(Y), np.gradient(X)))
    a = np.convolve(np.pad(a, 12, mode='edge'), np.ones(25) / 25, 'valid')
    return np.interp(s, np.linspace(0, 1, len(a)), a)
A = {k: angles(v) for k, v in HIS.items()}
for k in A:                                           # одна ветка углов у всех поз (без скачков на 360°)
    A[k] += 2 * math.pi * round((A[4][0] - A[k][0]) / (2 * math.pi))
def chord(pts): (ax, ay), (bx, by) = pts[0], pts[-1]; return math.atan2(by - ay, bx - ax)
P_rest = build_p(th0, np.ones(len(s))); ROT = math.atan2(P_rest[-1, 1] - P_rest[0, 1], P_rest[-1, 0] - P_rest[0, 0]) - chord(HIS[4])
POSE = {k: A[k] + ROT for k in A}                     # его формы как есть; весь его кадр повёрнут так, чтобы его лежачая поза 4 легла как наш хвост
ORDER = [4, 5, 6, 7, 8, 1, 2, 3, 4]
if MODE8_ == 'his':
    Z = 4; im = Image.new('RGB', ((x1 - x0) * Z, (y1 - y0) * Z), (40, 40, 40))
if MODE8_ in ('lines', 'his'):
    Z = 4; im = Image.fromarray(np.clip(O, 0, 255).astype(np.uint8)).resize(((x1 - x0) * Z, (y1 - y0) * Z), Image.LANCZOS)
    d = ImageDraw.Draw(im); fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 26)
    for k in [5, 6, 7, 8, 1, 2, 3, 4]:
        col = (255, 60, 60) if k in (5, 6, 7, 8) else (255, 255, 255)
        Pp = (build_p(POSE[k], np.ones(len(s))) - [x0, y0]) * Z
        d.line([tuple(p) for p in Pp], fill=col, width=5, joint='curve')
        d.text(tuple(Pp[-1] + [-12, -30]), str(k), fill=col, font=fnt, stroke_width=3, stroke_fill=(0, 0, 0))
    d.text((14, 10), 'его формы как есть: красное 5-8, белое 1-4', fill=(255, 240, 200), font=fnt, stroke_width=3, stroke_fill=(0, 0, 0))
    im.save(OUT8_); sys.exit()
