# Один мягкий жест «как у аниматоров»: основание прибито, хвост плавно гнётся к одной позе и обратно (ping-pong).
import sys, math, numpy as np, subprocess
from PIL import Image, ImageFilter
args = sys.argv[1:]
sys.argv = ['x', '../font/cat.img', 'erased.jpg', 'x', 'inside.npy']
exec(open('poses.py').read().split("if __name__")[0])
TIGHT = np.load('tight.npy')[y0:y1, x0:x1]   # маска точно по чёрной линии хвоста (без тени снаружи)
# сверху (где хвост касается тела) — строго внутри красной линии автора, без самой линии
INNER = np.asarray(Image.fromarray((INS * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3))) > 0
TIGHT = np.where(below | (ir > N * 0.85), TIGHT, INNER)
TIGHT[:, 1203 - x0:] = False    # за основанием — тело кота
M = np.asarray(Image.fromarray((TIGHT * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))).astype(np.float32) / 255
rest = frame(TH[0])
_w = Image.fromarray((M > 0.02).astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.GaussianBlur(4))
WN = (np.asarray(_w).astype(np.float32) / 255)[..., None]
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
def th(t):
    # гибкость: вверх кончик чуть отстаёт и перелетает (+12%), вниз основание идёт первым, кончик плывёт следом
    ks = []
    for x in s:
        up = k_at(t - 0.10 * x) if t < 1.0 + 0.10 * x else None
        if up is not None and t < 0.85 + 0.10 * x:
            k = up
        else:
            td = t - 0.30 * x * x                        # на спуске запаздывание растёт к кончику
            k = k_at(max(td, 0.86)) if td > 0.86 else 1.0
            ov = 0.12 * x * math.exp(-max(t - 0.85, 0) / 0.25) * math.sin(math.pi * min(max((t - 0.85) / 0.5, 0), 1))
            k = k + ov
        ks.append(k)
    k = np.array(ks)
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
