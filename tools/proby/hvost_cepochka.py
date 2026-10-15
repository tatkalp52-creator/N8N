# Хвост как цепочка на пружинках (урок Micah Buzan): двигаем только основание, остальное волочится и «щёлкает» само.
import sys, math, numpy as np, subprocess
from PIL import Image, ImageFilter
args = sys.argv[1:]
sys.argv = ['x', '../font/cat.img', 'erased.jpg', 'x', 'inside.npy']
exec(open('poses.py').read().split("if __name__")[0])
_sw = open('sway.py').read(); exec(_sw[_sw.index("TIGHT = np.load"):_sw.index("ALPHA =")])
out = args[0]
BASE_DEG = float(args[1]) if len(args) > 1 else 9.0     # насколько основание поднимает хвост
LAGT = float(args[2]) if len(args) > 2 else 0.35       # на сколько кончик отстаёт от основания, с
ZETA_TIP = float(args[3]) if len(args) > 3 else 0.45    # затухание у кончика (меньше — сильнее «щёлкает»)
NS = 12                                                 # звеньев в цепочке
s_seg = (np.arange(NS) + 0.5) / NS
REL = np.interp(s_seg, np.linspace(0, 1, N - 1), TH[0])  # форма покоя
def ss(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
def drive(t):   # «раз» — быстро вверх, «два-три-четыре» — медленно вниз
    if t < 0.3: return 0.0
    if t < 0.8: x = (t - 0.3) / 0.5; return 1 - (1 - x) ** 3
    if t < 1.0: return 1.0
    if t < 2.9: return 1 - ss((t - 1.0) / 1.9)
    return 0.0
PIN = 3                                    # первые звенья у тела: ими управляем напрямую (основание)
_n = NS - PIN
ZETA = np.r_[np.zeros(PIN), np.full(_n - 3, 0.85), np.full(3, ZETA_TIP)]
W = np.r_[np.zeros(PIN), 2 * ZETA[PIN:] / (LAGT / _n)]     # задержка звена ≈ 2ζ/ω
KK = W ** 2; DD = 2 * ZETA * W
def simulate(T, fps):
    dt = 1 / 4800; steps = int(T / dt)
    off = np.zeros(NS); vel = np.zeros(NS)  # отклонение абсолютного угла звена от покоя
    res = []; every = int(round(1 / (fps * dt)))
    for k in range(steps):
        t = k * dt
        b = math.radians(BASE_DEG) * drive(t)
        prev = off[:PIN].copy()
        for i in range(PIN): off[i] = b * (i + 1) / PIN
        vel[:PIN] = (off[:PIN] - prev) / dt
        acc = np.zeros(NS)
        acc[PIN:] = KK[PIN:] * (off[PIN - 1:-1] - off[PIN:]) - DD[PIN:] * (vel[PIN:] - vel[PIN - 1:-1])
        vel += acc * dt; off[PIN:] += vel[PIN:] * dt
        if k % every == 0: res.append(off.copy())
    return res
fps = 24; sec = 4
offs = simulate(sec + 0.1, fps)
def th_from(off):
    return TH[0] + np.interp(np.linspace(0, 1, N - 1), s_seg, off)
zoom = 'z' in out
size = (660, 420) if zoom else (1920, 1080)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
for rep in range(2):
    for f in range(fps * sec):
        F = frame(th_from(offs[f])); img = F * WN + (O + F - rest) * (1 - WN)
        if zoom: im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)
        else:
            fr = orig.copy(); fr[y0:y1, x0:x1] = img; im = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)
        p.stdin.write(np.asarray(im).tobytes())
p.stdin.close(); p.wait()
print('tip deg', [round(math.degrees(o[-1]), 1) for o in offs[:40:2]])
print('mid deg', [round(math.degrees(o[NS // 2]), 1) for o in offs[:40:2]])
