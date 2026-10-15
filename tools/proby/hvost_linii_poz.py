import sys; OUT4_ = sys.argv[1]
exec(open('pozy_plavno.py').read().split("if __name__ == '__main__':")[0])
from PIL import ImageDraw, ImageFont
Z = 4; im = Image.fromarray(np.clip(O, 0, 255).astype(np.uint8)).resize(((x1 - x0) * Z, (y1 - y0) * Z), Image.LANCZOS)
d = ImageDraw.Draw(im); f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 26)
cols = [(255, 60, 60)] * 4 + [(255, 255, 255)] * 3
for i, (nm, th) in enumerate(POSES[1:]):
    Pp = (build_p(th, np.ones(len(s))) - [x0, y0]) * Z
    d.line([tuple(p) for p in Pp], fill=cols[i], width=5, joint='curve')
    d.text(tuple(Pp[-1] + [-14, -30]), str(i + 2), fill=cols[i], font=f, stroke_width=3, stroke_fill=(0, 0, 0))
im.save(OUT4_)
