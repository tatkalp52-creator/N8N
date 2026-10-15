# Позы хвоста максимально плавные: угол вдоль хвоста — гладкая кубика от основания (кривизна течёт без изломов),
# длина везде одна (без укорачивания), крючок наверху мягче.
import sys, math, numpy as np
from PIL import Image, ImageDraw, ImageFont
OUT3_ = sys.argv[1]
sys.argv = ['x', '/dev/null', 'check']
exec(open('ozhivlenie.py').read().split("KEYS = [")[0])
def tip_up(th, deg, start=0.45):
    x = np.clip((s - start) / (1 - start), 0, 1); return th + math.radians(deg) * x * x * (3 - 2 * x)
def smooth(th):                                      # гладкая кубика через основание: θ(0) = как у нарисованного хвоста
    A = np.stack([s, s ** 2, s ** 3], 1); c, *_ = np.linalg.lstsq(A, th - th0[0], rcond=None)
    return th0[0] + A @ c
def curve(a, b, c=0.0):                             # угол: от основания плавно, гибкость растёт к кончику (s², s³)
    return th0[0] + np.radians(a * s + b * s ** 2 + c * s ** 3)
hook = P['вверх 4 (крючок)']; hump = P['вверх 3 (горб)']
POSES = [
    ('1 лежит', th0),
    ('2 кончик ниже', curve(78, -118)),
    ('3 горб → загиб', curve(28, 72)),
    ('4 подзавис вверху', curve(30, 105)),
    ('5 основание пошло вниз', curve(6, 45, 92)),
    ('6 J', curve(12, 0, 88)),
    ('7 основание легло', smooth(lying_base(115))),
    ('8 лежит', th0),
]
if __name__ == '__main__':
    f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
    cv = Image.new('RGB', (4 * 345, 2 * 375))
    for i, (nm, th) in enumerate(POSES):
        im = Image.fromarray(np.clip(frame_p(th, np.ones(len(s))), 0, 255).astype(np.uint8)).resize((345, 375), Image.LANCZOS)
        ImageDraw.Draw(im).text((8, 6), nm, fill=(255, 230, 170), font=f, stroke_width=3, stroke_fill=(0, 0, 0))
        cv.paste(im, ((i % 4) * 345, (i // 4) * 375))
    cv.save(OUT3_)
