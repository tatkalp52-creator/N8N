import numpy as np, subprocess, sys, math
from PIL import Image, ImageFilter
orig = np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(np.float32)
clean = np.asarray(Image.open(sys.argv[2]).convert('RGB').resize((orig.shape[1], orig.shape[0]), Image.LANCZOS)).astype(np.float32)
out = sys.argv[3]
H, W, _ = orig.shape
x0, x1, y0, y1 = 1040, 1260, 560, 700
O = orig[y0:y1, x0:x1]; C = clean[y0:y1, x0:x1]
# ось хвоста: основание → кончик
pts = np.array([(1215, 603), (1170, 608), (1125, 618), (1100, 628), (1085, 642)], float)
seg = []
for a, b in zip(pts[:-1], pts[1:]):
    for u in np.linspace(0, 1, 40, endpoint=False): seg.append(a + (b - a) * u)
seg.append(pts[-1]); seg = np.array(seg)
L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(seg, axis=0), axis=1))]; sof = L / L[-1]
yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
P = np.stack([xx, yy], -1)
d2 = ((P[:, :, None, :] - seg[None, None]) ** 2).sum(-1)
S = sof[d2.argmin(-1)]; dist = np.sqrt(d2.min(-1))
# маска хвоста = где стёрто (разница оригинала и чистого фона), рядом с осью
diff = np.abs(O - C).sum(-1)
m = ((diff > 28) & (dist < 22)).astype(np.float32)
mi = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
M = np.asarray(mi).astype(np.float32) / 255
# шарниры по длине хвоста
J = [0.28, 0.5, 0.7, 0.86]
jp = [seg[np.searchsorted(sof, j)] for j in J]
def rot(p, c, a):
    ca, sa = math.cos(a), math.sin(a)
    return np.stack([c[0] + ca * (p[..., 0] - c[0]) - sa * (p[..., 1] - c[1]), c[1] + sa * (p[..., 0] - c[0]) + ca * (p[..., 1] - c[1])], -1)
def sample(img, q):
    sx = np.clip(q[..., 0] - x0, 0, x1 - x0 - 1.001); sy = np.clip(q[..., 1] - y0, 0, y1 - y0 - 1.001)
    ix = sx.astype(int); iy = sy.astype(int); fx = sx - ix; fy = sy - iy
    if img.ndim == 3: fx = fx[..., None]; fy = fy[..., None]
    return img[iy, ix] * (1 - fx) * (1 - fy) + img[iy, ix + 1] * fx * (1 - fy) + img[iy + 1, ix] * (1 - fx) * fy + img[iy + 1, ix + 1] * fx * fy
bounds = [0.0] + J + [1.01]
OV = 0.04   # куски заходят друг на друга — без щели на сгибе
def segmask(k):
    a, b = bounds[k] - (OV if k else 0), bounds[k + 1] + OV
    return M * ((S >= a) & (S < b))
SEGM = [segmask(k) for k in range(len(bounds) - 1)]
def frame(angles):
    acc = C.copy()
    for k in range(len(SEGM)):
        q = P
        for j in range(k, 0, -1):             # обратное преобразование куска k: сначала R1^-1 … Rk^-1
            pass
        q = P.copy()
        for j in range(k):                    # T_k^-1 = R_k^-1 ∘ … ∘ R_1^-1, применяем R_1^-1 первым
            q = rot(q, jp[j], -angles[j])
        a = sample(SEGM[k], q)[..., None]
        acc = acc * (1 - a) + sample(O, q) * a
    return acc
rest = frame([0] * len(J))
fps, sec = 24, 12
def bump(t, c, w):
    x = (t - c) / w
    return math.cos(x * math.pi / 2) ** 2 if abs(x) < 1 else 0.0
amp = [math.radians(a) for a in (4, 6, 8, 11)]
lag = 0.012                                   # волна от основания к кончику (доля петли ≈ 0.15 с)
def angles_at(t):
    out = []
    for k, A in enumerate(amp):
        tt = t - lag * k
        out.append(A * (bump(tt, 0.20, 0.05) + 0.7 * bump(tt, 0.32, 0.045) + 0.45 * bump(tt, 0.72, 0.08)))
    return out
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
                      '-vf', 'scale=1920:1080:flags=lanczos', '-c:v', 'libx264', '-crf', '17', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
for rep in range(2):
    for f in range(fps * sec):
        fr = orig.copy(); fr[y0:y1, x0:x1] = O + (frame(angles_at(f / (fps * sec))) - rest)
        p.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
p.stdin.close(); p.wait()
Image.fromarray((M * 255).astype(np.uint8)).resize(((x1 - x0) * 3, (y1 - y0) * 3)).save(out.rsplit('.', 1)[0] + '_mask.png')
