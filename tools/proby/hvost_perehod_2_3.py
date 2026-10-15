import sys; OUT6_ = sys.argv[1]
exec(open('pozy_plavno.py').read().split("if __name__ == '__main__':")[0])
from PIL import ImageDraw, ImageFont
Z = 4; f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 26)
PT = dict(POSES)
x_ = np.clip((0.85 - s) / 0.7, 0, 1); w_ = x_ * x_ * (3 - 2 * x_)
wave = PT['3 горб → загиб'] * w_ + PT['2 кончик ниже'] * (1 - w_)
sets = [('как сейчас: 2, середина пути, 3', [('2', PT['2 кончик ниже'], (255, 60, 60)), ('сер.', (PT['2 кончик ниже'] + PT['3 горб → загиб']) / 2, (255, 255, 255)), ('3', PT['3 горб → загиб'], (255, 200, 60))]),
        ('предлагаю: волна от основания', [('2', PT['2 кончик ниже'], (255, 60, 60)), ('2½ волна', wave, (255, 255, 255)), ('3', PT['3 горб → загиб'], (255, 200, 60))])]
out = Image.new('RGB', (2 * (x1 - x0) * Z, (y1 - y0) * Z))
for k, (title, lines) in enumerate(sets):
    im = Image.fromarray(np.clip(O, 0, 255).astype(np.uint8)).resize(((x1 - x0) * Z, (y1 - y0) * Z), Image.LANCZOS); d = ImageDraw.Draw(im)
    for nm, th, col in lines:
        Pp = (build_p(th, np.ones(len(s))) - [x0, y0]) * Z
        d.line([tuple(p) for p in Pp], fill=col, width=6, joint='curve'); d.text(tuple(Pp[-1] + [-20, -32]), nm, fill=col, font=f, stroke_width=3, stroke_fill=(0, 0, 0))
    d.text((14, 10), title, fill=(255, 240, 200), font=f, stroke_width=3, stroke_fill=(0, 0, 0)); out.paste(im, (k * (x1 - x0) * Z, 0))
out.save(OUT6_)
