# Хвост по образцу (кот на красном фоне): волна изгиба бежит от основания к кончику, изгибы в разные стороны (S),
# медленно и без остановок. Меняются не углы поворота, а кривизна по длине.
import sys, math, numpy as np, subprocess
from PIL import Image, ImageFilter
args = sys.argv[1:]
sys.argv = ['x', '../font/cat.img', 'erased.jpg', 'x', 'inside.npy']
exec(open('poses.py').read().split("if __name__")[0])
_sw = open('sway.py').read(); exec(_sw[_sw.index("TIGHT = np.load"):_sw.index("ALPHA =")])
TIP = float(args[1]) if len(args) > 1 else 14.0     # наибольшее отклонение кончика, градусы
PERIOD = float(args[2]) if len(args) > 2 else 6.0
CURL_BIAS = float(args[3]) if len(args) > 3 else 0.45   # волна смещена в сторону загиба: вниз почти не уходит
SIGN = float(args[4]) if len(args) > 4 else 1.0
LAMBDA = 1.1                                         # длина волны ≈ длина хвоста → одна S
s = np.linspace(0, 1, N - 1); ds = 1.0 / (N - 1)
A = np.array([ss(x / 0.35) * (0.4 + 1.2 * x) for x in s])   # у тела почти ноль, к концу — сильнее (крючок)
def dtheta(t):
    k = A * (CURL_BIAS + (1 - CURL_BIAS) * np.sin(2 * math.pi * (t / PERIOD - s / LAMBDA))) * SIGN
    return np.cumsum(k) * ds
_mx = max(abs(dtheta(t)[-1]) for t in np.linspace(0, PERIOD, 60))
GAIN = math.radians(TIP) / _mx
out = args[0]; zoom = 'z' in out
fps = 24; sec = int(PERIOD * 2)
size = (660, 420) if zoom else (1920, 1080)
# покой = форма при t, где отклонение ноль; чтобы петля начиналась с нарисованного хвоста, сдвигаем фазу
t0 = min(np.linspace(0, PERIOD, 400), key=lambda t: np.abs(dtheta(t)).max())
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
for f in range(fps * sec):
    t = f / fps
    env = ss(t / 1.5) * ss((sec - t) / 1.5)          # мягко начинается и мягко стихает — как событие
    F = frame(TH[0] + env * GAIN * dtheta(t)); img = F * WN + (O + F - rest) * (1 - WN)
    if zoom: im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)
    else:
        fr = orig.copy(); fr[y0:y1, x0:x1] = img; im = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)
    p.stdin.write(np.asarray(im).tobytes())
p.stdin.close(); p.wait()
