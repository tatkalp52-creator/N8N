# Хвост v4: плавный изгиб (много шарниров, вес по длине), волна от основания к кончику.
import numpy as np, subprocess, sys, math
from PIL import Image, ImageFilter
orig = np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(np.float32)
clean = np.asarray(Image.open(sys.argv[2]).convert('RGB').resize((orig.shape[1], orig.shape[0]), Image.LANCZOS)).astype(np.float32)
out = sys.argv[3]; INS0 = np.load(sys.argv[4])
H, W, _ = orig.shape
x0, x1, y0, y1 = 1040, 1260, 560, 700
O = orig[y0:y1, x0:x1]; C = clean[y0:y1, x0:x1]
pts = np.array([(1206, 613), (1186, 614), (1166, 616), (1146, 615), (1126, 616), (1110, 622), (1100, 628), (1092, 636), (1086, 641)], float)
seg = []
for a, b in zip(pts[:-1], pts[1:]):
    for u in np.linspace(0, 1, 30, endpoint=False): seg.append(a + (b - a) * u)
seg.append(pts[-1]); seg = np.array(seg)
L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(seg, axis=0), axis=1))]; sof = L / L[-1]
yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
P = np.stack([xx, yy], -1)
def arcpos(Q):
    d2 = ((Q[:, :, None, :] - seg[None, None]) ** 2).sum(-1)
    i = d2.argmin(-1); return sof[i], seg[i]
S0, NEAR = arcpos(P)
# маска: обводка автора; расширяем только вниз и у кончика (сверху тело кота — его не тащим)
INS = INS0[y0:y1, x0:x1]
dil = np.asarray(Image.fromarray((INS * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7))) > 0
below = (P[..., 1] - NEAR[..., 1]) > 0
m = INS | (dil & (below | (S0 > 0.8)))
M = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32) / 255
# шарниры
NJ = 12
JS = np.linspace(0.22, 0.95, NJ)
JP = [seg[np.searchsorted(sof, j)] for j in JS]
BW = 0.05   # ширина мягкого сгиба вокруг шарнира (доля длины)
def rot(p, c, a):
    ca, sa = np.cos(a), np.sin(a)
    dx, dy = p[..., 0] - c[0], p[..., 1] - c[1]
    return np.stack([c[0] + ca * dx - sa * dy, c[1] + sa * dx + ca * dy], -1)
def sample(img, q):
    sx = np.clip(q[..., 0] - x0, 0, x1 - x0 - 1.001); sy = np.clip(q[..., 1] - y0, 0, y1 - y0 - 1.001)
    ix = sx.astype(int); iy = sy.astype(int); fx = sx - ix; fy = sy - iy
    if img.ndim == 3: fx = fx[..., None]; fy = fy[..., None]
    return img[iy, ix] * (1 - fx) * (1 - fy) + img[iy, ix + 1] * fx * (1 - fy) + img[iy + 1, ix] * (1 - fx) * fy + img[iy + 1, ix + 1] * fx * fy
SG = sample(S0, P)  # S как картинка для выборки
def inverse(angles):
    # для каждой точки кадра ищем, откуда в исходнике она пришла: 3 итерации по положению на хвосте
    s = S0.copy()
    for _ in range(3):
        q = P.copy()
        for j in range(NJ):
            w = np.clip((s - JS[j]) / BW + 0.5, 0, 1)
            q = rot(q, JP[j], -angles[j] * w)
        s = sample(S0, q)
    return q
def frame(angles):
    q = inverse(angles)
    a = sample(M, q)[..., None]
    return C * (1 - a) + sample(O, q) * a
rest = frame(np.zeros(NJ))
_w = Image.fromarray((M > 0.02).astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.GaussianBlur(4))
WN = (np.asarray(_w).astype(np.float32) / 255)[..., None]
# движение: ленивый подъём кончика с загибом → пара затухающих взмахов кончиком → медленно ложится
def ss(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
def angles_at(t):
    out = np.zeros(NJ)
    for j, s in enumerate(JS):
        e = ss((s - 0.45) / 0.5)            # у основания почти ноль, к кончику — больше
        tt = t - 0.35 * s                    # волна идёт от основания к кончику
        lift = ss(tt / 1.1) * (1 - ss((tt - 2.6) / 1.6))
        fl = math.exp(-max(tt - 1.0, 0) / 0.7) * math.sin(2 * math.pi * 1.6 * (tt - 1.0)) if tt > 1.0 else 0.0
        curl = e * e                         # загиб сильнее всего у кончика
        out[j] = math.radians(2.0 * e * lift + 6.0 * curl * lift + 4.0 * curl * fl * lift)
    return out
if __name__ == '__main__':
    fps, sec = 24, 7
    p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
                          '-vf', 'scale=1920:1080:flags=lanczos', '-c:v', 'libx264', '-crf', '17', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    for rep in range(2):
        for f in range(fps * sec):
            F = frame(angles_at(f / fps - 0.5))
            fr = orig.copy(); fr[y0:y1, x0:x1] = F * WN + (O + F - rest) * (1 - WN)
            p.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait()
