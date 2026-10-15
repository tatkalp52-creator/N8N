# Один мягкий жест «как у аниматоров»: основание прибито, хвост плавно гнётся к одной позе и обратно (ping-pong).
import sys, math, numpy as np, subprocess
from PIL import Image
args = sys.argv[1:]
sys.argv = ['x', '../font/cat.img', 'erased.jpg', 'x', 'inside.npy']
exec(open('poses.py').read().split("if __name__")[0])
ALPHA = float(args[1]) if len(args) > 1 else 0.6
s = np.linspace(0, 1, N - 1)
pin = np.array([ss((x - 0.08) / 0.4) for x in s])        # у тела не двигается, дальше — плавно сильнее
TARGET = TH[0] + pin * ALPHA * (TH[1] - TH[0])
def k_at(t):   # «раз» — быстро вверх (0.45 с, мягко в конце), «два-три-четыре» — медленно вниз (1.9 с)
    if t < 0.4: return 0.0
    if t < 0.85: x = (t - 0.4) / 0.45; return 1 - (1 - x) ** 3
    if t < 1.0: return 1.0
    if t < 2.9: return 1 - ss((t - 1.0) / 1.9)
    return 0.0
LAG = 0.25
def th(t):
    k = np.array([k_at(t - LAG * x) for x in s])
    return TH[0] * (1 - k) + TARGET * k
out = args[0]; zoom = 'z' in out
fps, sec = 24, 4
size = (660, 420) if zoom else (1920, 1080)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
for rep in range(2):
    for f in range(fps * sec):
        F = frame(th(f / fps)); img = F * WN + (O + F - rest) * (1 - WN)
        if zoom: im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)
        else:
            fr = orig.copy(); fr[y0:y1, x0:x1] = img; im = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)
        p.stdin.write(np.asarray(im).tobytes())
p.stdin.close(); p.wait()
