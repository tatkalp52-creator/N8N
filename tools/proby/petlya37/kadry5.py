# Четыре кадра хвоста (без видео): хвост целиком с его чёрной обводкой (вся обводка автора + линия + 1 px),
# толщину не трогаем; основание прибито; кончик поднимается и к концу закругляется «бубликом».
import sys, math, numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont
import os
sys.argv = ['x', os.environ.get('TAIL_IMG', '../font/cat.img'), os.environ.get('TAIL_CLEAN', 'erased.jpg'), 'x', 'inside.npy']
exec(open('poses2.py').read().split("if __name__")[0])
a0 = np.asarray(Image.open('../tail3/outline2.jpg').convert('RGB')).astype(int)[y0:y1, x0:x1]
r, g, b = a0[..., 0], a0[..., 1], a0[..., 2]
redline = (r - (g + b) / 2 > 22) & (r > 55)
full = INS | redline
full = np.asarray(Image.fromarray((full * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3)), np.float32) > 127
full[:, 1203 - x0:] = False
M = np.asarray(Image.fromarray((full * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255
s = np.linspace(0, 1, N - 1)
def ss(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)
def th(lift, curl):
    w = ss((s - 0.33) / 0.67)                    # подъём — плавно от трети длины
    b1 = np.cumsum(w); b1 /= b1[-1]
    w2 = ss((s - 0.7) / 0.3) ** 2                # «бублик» — изгиб собран у самого кончика
    b2 = np.cumsum(w2); b2 /= b2[-1]
    return TH[0] + math.radians(lift) * b1 + math.radians(curl) * b2
FR = [(0, 0), (18, 0), (35, 25), (45, 75)]
f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
ims = []
for k, (l, c) in enumerate(FR):
    F = frame(th(l, c)) if k else frame(TH[0])
    im = Image.fromarray(np.clip(F, 0, 255).astype(np.uint8)).crop((20, 20, 200, 120)).resize((540, 300), Image.LANCZOS)
    ImageDraw.Draw(im).text((10, 6), str(k + 1), fill=(255, 230, 170), font=f, stroke_width=3, stroke_fill=(0, 0, 0)); ims.append(im)
cv = Image.new('RGB', (1080, 600))
for k, im in enumerate(ims): cv.paste(im, ((k % 2) * 540, (k // 2) * 300))
cv.save(sys.argv[0] if False else '/home/user/N8N/table_drafts/hvost_4_kadra.png')
