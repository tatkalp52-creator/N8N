# Хвост как резиновая трубочка: наш нарисованный хвост, основание прибито, длина и толщина постоянны.
# Добавочный изгиб: 0 до трети длины, дальше плавно растёт к кончику (кончик поднимается и загибается вверх).
import sys, math, numpy as np, subprocess
from PIL import Image, ImageFilter
args = sys.argv[1:]
sys.argv = ['x', '../font/cat.img', 'erased.jpg', 'x', 'inside.npy']
exec(open('poses.py').read().split("if __name__")[0])
_sw = open('sway.py').read(); exec(_sw[_sw.index("TIGHT = np.load"):_sw.index("ALPHA =")])
out = args[0]; MAXDEG = float(args[1]) if len(args) > 1 else 80.0
s = np.linspace(0, 1, N - 1)
def ss(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)
w = ss((s - 0.33) / 0.67)                       # кривизна: 0 до трети, к кончику растёт
bend = np.cumsum(w); bend = bend / bend[-1]     # угол поворота по длине, у кончика = 1
def th(k): return TH[0] + math.radians(MAXDEG) * k * bend   # «+» — кончик вверх
STEPS = [0, 1 / 3, 2 / 3, 1]
if 'stills' in out:
    ims = []
    for k in STEPS:
        F = frame(th(k)); im = Image.fromarray(np.clip(F, 0, 255).astype(np.uint8)).resize((440, 280), Image.LANCZOS); ims.append(im)
    c = Image.new('RGB', (880, 560))
    for i, im in enumerate(ims): c.paste(im, ((i % 2) * 440, (i // 2) * 280))
    c.save(out); sys.exit()
fps = 24; HOLD, UP, TOP, DOWN = 5.0, 1.6, 0.5, 2.0
def kt(t):
    if t < HOLD: return 0.0
    t -= HOLD
    if t < UP: return float(ss(t / UP))
    t -= UP
    if t < TOP: return 1.0
    t -= TOP
    return float(1 - ss(t / DOWN))
n = int((HOLD + UP + TOP + DOWN) * fps)
size = (660, 420)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
for rep in range(2):
    for f in range(n):
        F = frame(th(kt(f / fps))); img = F * WN + (O + F - rest) * (1 - WN)
        p.stdin.write(np.asarray(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)).tobytes())
p.stdin.close(); p.wait()
