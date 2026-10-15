import sys; sys.argv=['x','/dev/null','check']
src=open('ozhivlenie.py').read().split("KEYS = [")[0]; exec(src)
from PIL import ImageDraw, ImageFont
f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
def tip_up(th, deg, start=0.45):
    x = np.clip((s - start) / (1 - start), 0, 1); return th + math.radians(deg) * x * x * (3 - 2 * x)
items = [('2 было', P['вверх 2 (прямее)'], .98), ('2: кончик ниже', tip_down(P['вверх 2 (прямее)'], 32), .98),
         ('3 было (горб)', P['вверх 3 (горб)'], .94), ('3: горб → загиб', tip_up(P['вверх 3 (горб)'], 70), .92),
         ('4 крючок', P['вверх 4 (крючок)'], .88)]
cv = Image.new('RGB', (5 * 345, 375))
for i, (nm, th, sc) in enumerate(items):
    im = Image.fromarray(np.clip(frame_p(th, np.full(len(s), sc)), 0, 255).astype(np.uint8)).resize((345, 375), Image.LANCZOS)
    ImageDraw.Draw(im).text((8, 6), nm, fill=(255, 230, 170), font=f, stroke_width=3, stroke_fill=(0, 0, 0)); cv.paste(im, (i * 345, 0))
cv.save('pozy_2_3.png')
