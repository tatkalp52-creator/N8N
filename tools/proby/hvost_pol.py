# Хвост движется по ПОЛУ (по обложке книги в перспективе), а не в плоскости рисунка.
# Средняя линия переводится в координаты обложки, там гнётся цепочкой (основание ведёт, кончик мягко следует),
# потом проецируется обратно на рисунок.
import sys, math, numpy as np, subprocess
from PIL import Image, ImageFilter
args = sys.argv[1:]
sys.argv = ['x', '../font/cat.img', 'erased.jpg', 'x', 'inside.npy']
exec(open('poses.py').read().split("if __name__")[0])
_sw = open('sway.py').read(); exec(_sw[_sw.index("TIGHT = np.load"):_sw.index("ALPHA =")])
out = args[0]
SWEEP = float(args[1]) if len(args) > 1 else 22.0     # мах основания по полу, градусы (знак — в какую сторону)
LAGT = float(args[2]) if len(args) > 2 else 0.5
DEPTH = float(args[3]) if len(args) > 3 else 0.55     # насколько сплющена глубина обложки на рисунке
E1 = np.array([0.98, 0.19]); E2 = np.array([0.935, -0.355]) * DEPTH   # край обложки и её глубина на рисунке
A = np.stack([E1, E2], 1); Ai = np.linalg.inv(A)
B = np.array(BASE, float)
FL = (Ai @ (REST_P - B).T).T                          # средняя линия хвоста в координатах пола
seg = np.diff(FL, axis=0); LEN = np.linalg.norm(seg, axis=1); ANG = np.unwrap(np.arctan2(seg[:, 1], seg[:, 0]))
NSEG = len(LEN)
def curve(off):                                       # off — добавка к углам звеньев на полу
    a = ANG + off
    F = np.vstack([[0, 0], np.cumsum(np.stack([np.cos(a), np.sin(a)], -1) * LEN[:, None], 0)])
    return B + (A @ F.T).T
def frame_curve(Pimg):
    DE = ext(Pimg); DT = tangents(DE); DN = np.stack([-DT[:, 1], DT[:, 0]], -1)
    d2 = ((Q[:, :, None, :] - DE[None, None]) ** 2).sum(-1); i = d2.argmin(-1)
    v = Q - DE[i]; n = (v * DN[i]).sum(-1); t = (v * DT[i]).sum(-1)
    src = RE[i] + n[..., None] * RN[i] + t[..., None] * RT[i]
    a = (sample(M, src) * (np.sqrt(d2.min(-1)) < 16))[..., None]
    return C * (1 - a) + sample(O, src) * a
def ss(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
# плавное ровное движение без пружин: хвост метёт по полу вперёд и так же плавно обратно (косинус),
# изгиб нарастает от тела к кончику, кончик чуть запаздывает — только сдвигом фазы
PERIOD = float(args[4]) if len(args) > 4 else 5.0
LAGP = 0.12                                          # запаздывание кончика, доля периода
fps = 24; sec = int(PERIOD)
sN = np.linspace(0, 1, 40)
AMP = np.array([ss((x - 0.03) / 0.6) for x in sN])   # у тела почти 0, к середине и кончику — полный мах
def off_at(t):
    ph = 2 * math.pi * (t / PERIOD - LAGP * sN)
    return math.radians(SWEEP) * AMP * (0.5 - 0.5 * np.cos(ph))
offs = [off_at(f / fps) for f in range(fps * sec)]
sS = np.linspace(0, 1, NSEG)
restC = frame_curve(curve(np.zeros(NSEG)))
zoom = 'z' in out
size = (660, 420) if zoom else (1920, 1080)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
for rep in range(2):
    for f in range(fps * sec):
        F = frame_curve(curve(np.interp(sS, sN, offs[f]))); img = F * WN + (O + F - restC) * (1 - WN)
        if zoom: im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)
        else:
            fr = orig.copy(); fr[y0:y1, x0:x1] = img; im = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)
        p.stdin.write(np.asarray(im).tobytes())
p.stdin.close(); p.wait()
print('tip', [round(math.degrees(o[-1]), 1) for o in offs[::12]])
