# Позы хвоста по рисунку автора (красное — вверх, белое — вниз). Линии сняты с её рисунка на кадре кота
# (кусок x880 y385 w544 → 1920), переведены в размер картинки. Хвост гнётся по форме линии, длина и толщина — его собственные;
# длину линии не берём (автор рисовала только изгибы): длина — хвоста, перспектива своя — поднятый хвост на экране чуть короче.
import sys, math, numpy as np
from PIL import Image, ImageDraw, ImageFont
OUT_ = sys.argv[1]
sys.argv = ['x', '/dev/null', 'none']
exec(open('duga2.py').read().split("def ss(")[0])
K = 544 / 1920; OX, OY = 880, 385
LINES = {
 'вверх 2 (прямее)': [(1150,762),(1080,798),(1000,800),(930,790),(870,778),(820,775),(775,790),(740,820)],
 'вверх 3 (горб)':   [(1165,770),(1080,795),(1000,772),(940,738),(900,712),(840,700),(800,705),(785,715)],
 'вверх 4 (крючок)': [(1165,770),(1080,790),(1000,775),(950,750),(910,718),(900,680),(902,640),(922,608),(955,586),(990,577)],
 'вниз 1':           [(1168,763),(1080,760),(1000,745),(950,715),(922,680),(920,642),(945,610),(995,595)],
 'вниз 2 (J)':       [(1168,765),(1080,782),(1000,786),(960,776),(900,750),(870,725),(856,690),(852,640)],
 'вниз 3':           [(1168,768),(1050,786),(960,786),(890,772),(830,775),(790,790),(760,815),(740,855)],
}
L_rest = step * (N - 1)
def pose(pts):
    P = np.array([(OX + x * K, OY + y * K) for x, y in pts], float)
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]; Lh = d[-1]
    u = np.linspace(0, Lh, 400); X = np.interp(u, d, P[:, 0]); Y = np.interp(u, d, P[:, 1])
    ang = np.unwrap(np.arctan2(np.gradient(Y), np.gradient(X)))
    ang = np.convolve(np.pad(ang, 15, mode='edge'), np.ones(31) / 31, 'valid')     # сглаживаем дрожь руки
    th = np.interp(s, np.linspace(0, 1, len(ang)), ang)
    th += th0[0] - th[0] if abs(th[0] - th0[0]) < 0.6 else 0      # начало — по нарисованному хвосту
    th = np.unwrap(np.r_[th0[0], th])[1:]
    return th
if __name__ == '__main__':
    f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
    PERSP = [0.98, 0.94, 0.88, 0.88, 0.92, 0.97]
    items = [('лежит', th0, 1.0)] + [(k, pose(v), PERSP[i]) for i, (k, v) in enumerate(LINES.items())] + [('лежит', th0, 1.0)]
    cv = Image.new('RGB', (4 * 345, 2 * 375))
    for i, (nm, th, sc) in enumerate(items):
        F = frame_p(th, np.full(len(s), sc))
        im = Image.fromarray(np.clip(F, 0, 255).astype(np.uint8)).resize((345, 375), Image.LANCZOS)
        ImageDraw.Draw(im).text((8, 6), f'{i + 1}. {nm}', fill=(255, 230, 170), font=f, stroke_width=3, stroke_fill=(0, 0, 0))
        cv.paste(im, ((i % 4) * 345, (i // 4) * 375))
    cv.save(OUT_)
