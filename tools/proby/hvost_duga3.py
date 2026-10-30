# Хвост: лежит → поднимается горбом (середина вверх, кончик висит) → горб переходит во впадину, кончик скругляется калачиком →
# падает: первым основание, кончик последним доходит до своего места и замирает.
import sys, math, numpy as np, subprocess
from PIL import Image
OUT_ = sys.argv[1]; MODE_ = sys.argv[2] if len(sys.argv) > 2 else 'video'
sys.argv = ['x', '/dev/null', 'none']
exec(open('duga2.py').read().split("def ss(")[0])
def arc(R, K):                                       # поворот основания R и изгиб K (растёт к кончику), градусы
    return th0[0] + math.radians(R) + math.radians(K) * s ** 2
REST = th0
HUMP = arc(55, -85)                                  # горб: основание вверх, кончик свисает
CURL = arc(14, 165)                                  # впадина в середине, кончик калачиком
def ss(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
HOLD, UP, TURN, TOP, DOWN, LAG = 5.0, 1.8, 0.9, 0.5, 1.1, 0.45
def seg_shape(t, j):
    t = t - LAG * s[j]                               # каждое звено чуть позже предыдущего: импульс от основания
    if t < HOLD: return REST[j]
    t -= HOLD
    if t < UP: a = ss(t / UP); return REST[j] * (1 - a) + HUMP[j] * a
    t -= UP
    if t < TURN: a = ss(t / TURN); return HUMP[j] * (1 - a) + CURL[j] * a
    t -= TURN
    if t < TOP: return CURL[j]
    t -= TOP
    if t < DOWN: a = ss(t / DOWN); return CURL[j] * (1 - a) + REST[j] * a
    return REST[j]
def lift(t):                                         # насколько хвост поднят (для перспективы), 0…1
    t -= HOLD
    if t < 0: return 0.0
    if t < UP: return ss(t / UP)
    if t < UP + TURN + TOP: return 1.0
    return 1 - ss((t - UP - TURN - TOP) / DOWN)
def at(t):
    th_ = np.array([seg_shape(t, j) for j in range(len(s))])
    sc = 1 - 0.15 * np.array([lift(t - LAG * x) for x in s]) * s
    return th_, sc
CYCLE = HOLD + UP + TURN + TOP + DOWN + LAG
if MODE_ == 'stills':
    from PIL import ImageDraw, ImageFont
    f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
    T = [0, HOLD + UP * 0.5, HOLD + UP + 0.3, HOLD + UP + TURN * 0.6, HOLD + UP + TURN + 0.3, HOLD + UP + TURN + TOP + DOWN * 0.45]
    cv = Image.new('RGB', (1380, 1000))
    for k, t in enumerate(T):
        th_, sc = at(t); F = frame_p(th_, sc)
        im = Image.fromarray(np.clip(F, 0, 255).astype(np.uint8)).resize((460, 500), Image.LANCZOS)
        ImageDraw.Draw(im).text((10, 6), str(k + 1), fill=(255, 230, 170), font=f, stroke_width=3, stroke_fill=(0, 0, 0))
        cv.paste(im, ((k % 3) * 460, (k // 3) * 500))
    cv.save(OUT_); sys.exit()
fps = 24; n = int(round(CYCLE * fps)); w, h = x1 - x0, y1 - y0
crop = MODE_ == 'crop'; size = (w, h) if crop else (690, 750)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '10' if crop else '16', '-pix_fmt', 'yuv444p' if crop else 'yuv420p', OUT_], stdin=subprocess.PIPE)
for rep in range(1 if crop else 2):
    for fi in range(n):
        th_, sc = at(fi / fps); im = Image.fromarray(np.clip(frame_p(th_, sc), 0, 255).astype(np.uint8))
        p.stdin.write(np.asarray(im if crop else im.resize(size, Image.LANCZOS)).tobytes())
p.stdin.close(); p.wait()
