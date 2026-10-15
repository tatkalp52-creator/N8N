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
# (1) ровная толщина: измеряем полуширину хвоста по длине и у пушистого кончика поджимаем поперёк
_T = tangents(REST_P); _Nn = np.stack([-_T[:, 1], _T[:, 0]], -1)
def _edge(c, d):
    for r in np.arange(0, 30, 0.5):
        q = c + d * r; xx_, yy_ = int(round(q[0])) - x0, int(round(q[1])) - y0
        if not (0 <= xx_ < x1 - x0 and 0 <= yy_ < y1 - y0) or M[yy_, xx_] < 0.5: return r
    return 30.0
HW = np.array([_edge(REST_P[i], _Nn[i]) + _edge(REST_P[i], -_Nn[i]) for i in range(N)]) / 2
HW = np.convolve(np.pad(HW, 8, mode='edge'), np.ones(17) / 17, 'valid')
target = float(np.median(HW[int(N * 0.3):int(N * 0.7)]))
G = np.clip(HW / target, 1.0, 1.6)            # >1 — берём шире из исходника, хвост выходит уже
GE = np.concatenate([np.full(12, G[0]), G, np.full(12, G[-1])])
LUMB = C @ np.array([0.299, 0.587, 0.114], np.float32)
def frame(thv):
    DE = ext(build(thv)); DT = tangents(DE); DN = np.stack([-DT[:, 1], DT[:, 0]], -1)
    d2 = ((Q[:, :, None, :] - DE[None, None]) ** 2).sum(-1); i = d2.argmin(-1)
    v = Q - DE[i]; n = (v * DN[i]).sum(-1) * GE[i]; t = (v * DT[i]).sum(-1)
    src = RE[i] + n[..., None] * RN[i] + t[..., None] * RT[i]
    a = sample(M, src) * (np.sqrt(d2.min(-1)) < 22)
    out = C * (1 - a[..., None]) + sample(O, src) * a[..., None]
    # (2) контур: там, где хвост лежит на тёмном теле, по краю хвоста — тонкая светлая линия
    am = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    ring = (np.asarray(am.filter(ImageFilter.MaxFilter(3)), np.float32) - np.asarray(am.filter(ImageFilter.MinFilter(3)), np.float32)) / 255
    ring = np.clip(ring, 0, 1) * (np.clip((60 - LUMB) / 25, 0, 1)) * (a > 0.15)
    if REST_A is not None:          # только там, где хвост ушёл с места и лёг на тело; в покое контура нет
        ring = ring * (1 - REST_A)
    out = out * (1 - 0.35 * ring[..., None]) + np.array([110, 104, 92], np.float32) * 0.35 * ring[..., None]
    return out
REST_A = None
def _rest_alpha():
    DE = ext(build(TH[0])); d2 = ((Q[:, :, None, :] - DE[None, None]) ** 2).sum(-1); i = d2.argmin(-1)
    DT = tangents(DE); DN = np.stack([-DT[:, 1], DT[:, 0]], -1); v = Q - DE[i]
    src = RE[i] + ((v * DN[i]).sum(-1) * GE[i])[..., None] * RN[i] + ((v * DT[i]).sum(-1))[..., None] * RT[i]
    a = sample(M, src) * (np.sqrt(d2.min(-1)) < 22)
    return np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7)), np.float32) / 255
REST_A = _rest_alpha()
rest = frame(TH[0])
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
