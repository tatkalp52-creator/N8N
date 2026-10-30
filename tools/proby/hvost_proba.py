import numpy as np, subprocess, sys, math
from PIL import Image
src = sys.argv[1]; out = sys.argv[2]
img = np.asarray(Image.open(src).convert('RGB')).astype(np.float32)
H, W, _ = img.shape
# хвост: от основания к кончику (пиксели исходника 1536x864)
pts = np.array([(1215, 603), (1170, 608), (1125, 618), (1100, 628), (1085, 642)], float)
# плотная ломаная
seg = []
for a, b in zip(pts[:-1], pts[1:]):
    for u in np.linspace(0, 1, 30, endpoint=False):
        seg.append(a + (b - a) * u)
seg.append(pts[-1]); seg = np.array(seg)
L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(seg, axis=0), axis=1))]; s_of = L / L[-1]
x0, x1, y0, y1 = 1040, 1250, 560, 690
yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
P = np.stack([xx, yy], -1)
d2 = ((P[:, :, None, :] - seg[None, None]) ** 2).sum(-1)
k = d2.argmin(-1); dist = np.sqrt(d2.min(-1)); s = s_of[k]
R = 14.0
sm = lambda e0, e1, v: np.clip((v - e0) / (e1 - e0), 0, 1) ** 2 * (3 - 2 * np.clip((v - e0) / (e1 - e0), 0, 1))
roi = img[y0:y1, x0:x1]
luma = roi @ np.array([0.299, 0.587, 0.114], np.float32)
# маска хвоста: тёмные пиксели у линии хвоста, дальше основания
m = (sm(R + 3, R - 3, dist)) * sm(70, 45, luma) * sm(0.15, 0.3, s)
# blur маски для мягкого края
def blur(a, n=2):
    for _ in range(n):
        a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 5
    return a
m = blur(m, 2)
# чистый фон под хвостом: диффузия из окрестности
hole = blur((m > 0.05).astype(np.float32), 3) > 0.01
clean = roi.copy(); known = ~hole
clean[hole] = roi[known].mean(0)
for _ in range(400):
    av = (np.roll(clean, 1, 0) + np.roll(clean, -1, 0) + np.roll(clean, 1, 1) + np.roll(clean, -1, 1)) / 4
    clean[hole] = av[hole]
wsp = sm(0.35, 1.0, s)
piv = seg[np.searchsorted(s_of, 0.35)]
fps, sec = 24, 12
A = math.radians(7)
def bump(t, c, w):  # гладкий всплеск, 0 вне [c-w, c+w]
    x = (t - c) / w
    return np.where(abs(x) < 1, np.cos(x * math.pi / 2) ** 2, 0.0)
def sample(im, sx, sy):
    sx = np.clip(sx, 0, W - 1.001); sy = np.clip(sy, 0, H - 1.001)
    ix = sx.astype(int); iy = sy.astype(int); fx = (sx - ix)[..., None]; fy = (sy - iy)[..., None]
    return (im[iy, ix] * (1 - fx) * (1 - fy) + im[iy, ix + 1] * fx * (1 - fy)
            + im[iy + 1, ix] * (1 - fx) * fy + im[iy + 1, ix + 1] * fx * fy)
rest = clean * (1 - m[..., None]) + roi * m[..., None]
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                      '-r', str(fps), '-i', '-', '-vf', 'scale=1920:1080:flags=lanczos', '-c:v', 'libx264', '-crf', '18',
                      '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
for rep in range(2):
    for f in range(fps * sec):
        t = f / (fps * sec)
        th = A * (bump(t, 0.20, 0.035) + 0.7 * bump(t, 0.29, 0.03) + 0.5 * bump(t, 0.70, 0.06))
        a = -th * wsp
        dx = P[..., 0] - piv[0]; dy = P[..., 1] - piv[1]
        sx = piv[0] + np.cos(a) * dx - np.sin(a) * dy
        sy = piv[1] + np.sin(a) * dx + np.cos(a) * dy
        sxl = sx - x0; syl = sy - y0
        ix = np.clip(np.round(sxl).astype(int), 0, x1 - x0 - 1); iy = np.clip(np.round(syl).astype(int), 0, y1 - y0 - 1)
        mw = m[iy, ix][..., None]
        tl = sample(img, sx, sy)
        comp = clean * (1 - mw) + tl * mw
        fr = img.copy(); fr[y0:y1, x0:x1] = roi + (comp - rest)
        p.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
p.stdin.close(); p.wait()
