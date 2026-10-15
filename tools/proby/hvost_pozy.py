# Хвост по позам автора: средняя линия хвоста гнётся по её нарисованным кривым (интерполяция углов по длине).
import numpy as np, subprocess, sys, math
from PIL import Image, ImageFilter
orig = np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(np.float32)
clean = np.asarray(Image.open(sys.argv[2]).convert('RGB').resize((orig.shape[1], orig.shape[0]), Image.LANCZOS)).astype(np.float32)
out = sys.argv[3]; INS0 = np.load(sys.argv[4])
H, W, _ = orig.shape
x0, x1, y0, y1 = 1040, 1260, 560, 700
O = orig[y0:y1, x0:x1]; C = clean[y0:y1, x0:x1]
BASE = (1206, 613)
REST = [BASE, (1186, 614), (1166, 616), (1146, 615), (1126, 616), (1110, 622), (1100, 628), (1092, 636), (1086, 641)]
POSES = [
    [BASE, (1190, 612), (1150, 626), (1115, 632), (1098, 627), (1090, 615), (1085, 596)],
    [BASE, (1190, 616), (1160, 632), (1130, 640), (1110, 640), (1102, 632), (1100, 620), (1101, 609)],
    [BASE, (1199, 618), (1200, 630), (1190, 645), (1170, 655), (1145, 658), (1125, 652), (1120, 640), (1121, 622)],
]
N = 160
def resample(pts, n=N):
    pts = np.array(pts, float)
    # сглаживаем ломаную (Catmull-Rom) и берём равные шаги по длине
    P = np.vstack([pts[0], pts, pts[-1]]); dense = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, 40, endpoint=False):
            dense.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    dense.append(pts[-1]); dense = np.array(dense)
    L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(dense, axis=0), axis=1))]
    u = np.linspace(0, L[-1], n)
    return np.stack([np.interp(u, L, dense[:, 0]), np.interp(u, L, dense[:, 1])], -1), L[-1]
REST_P, REST_L = resample(REST)
def angles(P):
    d = np.diff(P, axis=0); return np.unwrap(np.arctan2(d[:, 1], d[:, 0]))
TH = [angles(REST_P)] + [angles(resample(p)[0]) for p in POSES]
for k in range(1, len(TH)):            # одинаковая ветвь углов с покоем
    TH[k] += 2 * math.pi * round((TH[0][0] - TH[k][0]) / (2 * math.pi))
step = REST_L / (N - 1)
def build(th):
    P = np.zeros((N, 2)); P[0] = BASE
    P[1:] = BASE + np.cumsum(np.stack([np.cos(th), np.sin(th)], -1) * step, 0)
    return P
yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
Q = np.stack([xx, yy], -1)
def ext(P):   # продлеваем линию за кончик и за основание, чтобы край хвоста не обрезался
    t0 = P[1] - P[0]; t1 = P[-1] - P[-2]
    pre = [P[0] - t0 * k for k in range(12, 0, -1)]; post = [P[-1] + t1 * k for k in range(1, 13)]
    return np.vstack([pre, P, post])
def tangents(P):
    t = np.gradient(P, axis=0); return t / np.linalg.norm(t, axis=1, keepdims=True)
RE = ext(REST_P); RT = tangents(RE); RN = np.stack([-RT[:, 1], RT[:, 0]], -1)
INS = INS0[y0:y1, x0:x1]
dil = np.asarray(Image.fromarray((INS * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7))) > 0
# расширяем маску только вниз и у кончика (сверху тело кота)
d2r = ((Q[:, :, None, :] - RE[None, None]) ** 2).sum(-1); ir = d2r.argmin(-1)
below = ((Q - RE[ir]) * RN[ir]).sum(-1) * np.sign(RN[ir][..., 1] + 1e-6) > 0
m = INS | (dil & (below | (ir > N * 0.8)))
M = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32) / 255
def sample(img, q):
    sx = np.clip(q[..., 0] - x0, 0, x1 - x0 - 1.001); sy = np.clip(q[..., 1] - y0, 0, y1 - y0 - 1.001)
    ix = sx.astype(int); iy = sy.astype(int); fx = sx - ix; fy = sy - iy
    if img.ndim == 3: fx = fx[..., None]; fy = fy[..., None]
    return img[iy, ix] * (1 - fx) * (1 - fy) + img[iy, ix + 1] * fx * (1 - fy) + img[iy + 1, ix] * (1 - fx) * fy + img[iy + 1, ix + 1] * fx * fy
def frame(th):
    DE = ext(build(th)); DT = tangents(DE); DN = np.stack([-DT[:, 1], DT[:, 0]], -1)
    d2 = ((Q[:, :, None, :] - DE[None, None]) ** 2).sum(-1); i = d2.argmin(-1)
    v = Q - DE[i]
    n = (v * DN[i]).sum(-1); t = (v * DT[i]).sum(-1)
    src = RE[i] + n[..., None] * RN[i] + t[..., None] * RT[i]
    a = sample(M, src) * (np.sqrt(d2.min(-1)) < 16)
    a = a[..., None]
    return C * (1 - a) + sample(O, src) * a
def ss(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
def pose_at(u):   # u: 0 покой, 1..3 — позы автора
    u = min(max(u, 0.0), len(TH) - 1.0); k = min(int(u), len(TH) - 2); f = u - k
    return TH[k] * (1 - f) + TH[k + 1] * f
KEYS = [(0.0, 0), (0.6, 0), (1.8, 1), (2.6, 2), (3.4, 3), (4.2, 3), (6.0, 0)]
def u_at(t):
    for (ta, ua), (tb, ub) in zip(KEYS, KEYS[1:]):
        if t <= tb: return ua + (ub - ua) * ss((t - ta) / (tb - ta))
    return KEYS[-1][1]
LAG = 0.5
def th_at(t):
    s = np.linspace(0, 1, N - 1)
    us = np.array([u_at(t - LAG * x) for x in s])
    k = np.clip(us.astype(int), 0, len(TH) - 2); f = us - k
    T = np.stack(TH)
    return T[k, np.arange(N - 1)] * (1 - f) + T[k + 1, np.arange(N - 1)] * f
rest = frame(TH[0])
_w = Image.fromarray((M > 0.02).astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.GaussianBlur(4))
WN = (np.asarray(_w).astype(np.float32) / 255)[..., None]
if __name__ == '__main__':
    fps, sec = 24, 7
    zoom = len(sys.argv) > 5
    size = (660, 420) if zoom else (1920, 1080)
    p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', str(fps), '-i', '-',
                          '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    for rep in range(2):
        for f in range(fps * sec):
            F = frame(th_at(f / fps))
            img = F * WN + (O + F - rest) * (1 - WN)
            if zoom:
                im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)
            else:
                fr = orig.copy(); fr[y0:y1, x0:x1] = img
                im = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)
            p.stdin.write(np.asarray(im).tobytes())
    p.stdin.close(); p.wait()
