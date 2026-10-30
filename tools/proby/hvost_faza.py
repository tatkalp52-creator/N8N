# Хвост по формуле со сдвигом фазы (FK-цепочка с задержкой): у позвонка j свой поворот
#   rot_j(t) = A_j · f(t − j·δ)        — та же кривая основания f, каждый следующий позвонок позже на δ
#   угол звена i = нарисованный угол i + Σ_{j≤i} rot_j      — хвост гнётся сам, S на развороте сама
# A_j: у самого крепления почти ноль (первые ~20 % длины жёсткие), дальше растёт к кончику.
# f: 0 лежит → 1 наверху (медленно вверх, зависание, быстрее вниз). Хвост не ниже книги, длина постоянная.
import sys, math, numpy as np, subprocess
from PIL import Image, ImageDraw, ImageFont
OUTB_ = sys.argv[1]; MODEB_ = sys.argv[2] if len(sys.argv) > 2 else 'lines'
sys.argv = ['x', OUTB_, 'none']
exec(open('buzan2.py').read().split("UPP = ")[0])          # нарисованный хвост, перенос на картинку, книга (on_surface)
NSEG = len(s); TOTAL = math.radians(215)                    # сумма поворотов всех позвонков наверху
STIFF = 0.15                                                # жёсткая часть у крепления (доля длины)
x = np.clip((s - STIFF) / (1 - STIFF), 0, 1); A = x ** 0.8 + 0.02; A = A / A.sum() * TOTAL
DELTA = 0.6                                                 # за сколько секунд импульс доходит до кончика
HOLD, UP, TOP, DOWN = 5.0, 2.6, 0.4, 1.5
def ease(u): u = min(max(u, 0.0), 1.0); return u * u * (3 - 2 * u)
def f(t):
    t -= HOLD
    if t < 0: return 0.0
    if t < UP: return ease(t / UP)
    t -= UP
    if t < TOP: return 1.0
    return 1 - ease((t - TOP) / DOWN)
def at(t):
    rot = A * np.array([f(t - DELTA * sj) for sj in s])
    return on_surface(th0 + np.cumsum(rot)), np.ones(NSEG)
CYCLE = HOLD + UP + TOP + DOWN + DELTA + 0.3
if MODEB_ == 'lines':
    Z = 3; base = Image.fromarray(np.clip(O, 0, 255).astype(np.uint8)).resize(((x1 - x0) * Z, (y1 - y0) * Z), Image.LANCZOS)
    fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22); out = Image.new('RGB', (base.width * 2, base.height))
    panels = [('ВВЕРХ (каждые 0.5 с)', np.arange(HOLD + 0.5, HOLD + UP + TOP + 0.01, 0.5), (255, 60, 60)),
              ('ВНИЗ (каждые 0.35 с)', np.arange(HOLD + UP + TOP, CYCLE - 0.2, 0.35), (255, 255, 255))]
    for k, (title, T, col) in enumerate(panels):
        im = base.copy(); d = ImageDraw.Draw(im)
        Pp = (build_p(th0, np.ones(NSEG)) - [x0, y0]) * Z; d.line([tuple(p) for p in Pp], fill=(120, 220, 255), width=4)
        for i, t in enumerate(T):
            Pp = (build_p(*at(t)) - [x0, y0]) * Z
            d.line([tuple(p) for p in Pp], fill=col, width=3, joint='curve')
            d.text(tuple(Pp[-1] + [-8, -24]), str(i + 1), fill=col, font=fnt, stroke_width=3, stroke_fill=(0, 0, 0))
        d.text((10, 8), title + ', голубой — нарисованный', fill=(255, 240, 200), font=fnt, stroke_width=3, stroke_fill=(0, 0, 0))
        out.paste(im, (k * base.width, 0))
    out.save(OUTB_); sys.exit()
fps = 24; n = int(round(CYCLE * fps)); w_, h_ = x1 - x0, y1 - y0
crop = MODEB_ == 'crop'; size = (w_, h_) if crop else (690, 750)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '10' if crop else '16', '-pix_fmt', 'yuv444p' if crop else 'yuv420p', OUTB_], stdin=subprocess.PIPE)
for rep in range(1 if crop else 2):
    for fi in range(n):
        im = Image.fromarray(np.clip(frame_p(*at(fi / fps)), 0, 255).astype(np.uint8))
        p.stdin.write(np.asarray(im if crop else im.resize(size, Image.LANCZOS)).tobytes())
p.stdin.close(); p.wait()
