import sys; OUTF_ = sys.argv[1]
src = open('tri_pozy.py').read().split("Z = 3; base")[0]; sys.argv = ['x', OUTF_]; exec(src)
from PIL import ImageDraw, ImageFont
Z = 3; base = Image.fromarray(np.clip(O, 0, 255).astype(np.uint8)).resize(((x1 - x0) * Z, (y1 - y0) * Z), Image.LANCZOS)
fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20); out = Image.new('RGB', (base.width * 2, base.height))
sets = [('начало: t = 0, .05, .1, .15, .25', [0, 0.05, 0.1, 0.15, 0.25]), ('конец: t = .75, .85, .9, .95, 1', [0.75, 0.85, 0.9, 0.95, 1.0])]
cols = [(120, 220, 255), (255, 200, 60), (255, 120, 60), (255, 60, 160), (255, 60, 60)]
for k, (title, T) in enumerate(sets):
    im = base.copy(); d = ImageDraw.Draw(im)
    for j, t in enumerate(T):
        Pp = (build_p(on_surface(shape3(t, MID_A)), np.ones(len(s))) - [x0, y0]) * Z
        d.line([tuple(p) for p in Pp], fill=cols[j], width=3, joint='curve')
        d.text(tuple(Pp[-1] + [-10, -24]), str(t), fill=cols[j], font=fnt, stroke_width=3, stroke_fill=(0, 0, 0))
    d.text((10, 8), 'А — ' + title, fill=(255, 240, 200), font=fnt, stroke_width=3, stroke_fill=(0, 0, 0)); out.paste(im, (k * base.width, 0))
out.save(OUTF_)
