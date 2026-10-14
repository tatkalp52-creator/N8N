# Силуэт хвоста по поперечным срезам: на каждом срезе край там, где оригинал становится светлее
# середины между хвостом и чистой книгой (книга — из стёртой картинки). Внутри — сплошная заливка.
import numpy as np, sys
from PIL import Image, ImageDraw, ImageFilter
O = Image.open(sys.argv[1]).convert('L'); C = Image.open(sys.argv[2]).convert('L').resize(O.size)
ins = np.load(sys.argv[3]); out = sys.argv[4]
lo = np.asarray(O.filter(ImageFilter.GaussianBlur(1.0))).astype(float)
lc = np.asarray(C.filter(ImageFilter.GaussianBlur(2.0))).astype(float)
lim = np.asarray(Image.fromarray((ins * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9))) > 0
# ось — середина обводки автора по столбцам (хвост лежит почти горизонтально)
_ys, _xs = np.nonzero(ins)
pts = np.array([(x, _ys[_xs == x].mean()) for x in range(_xs.max() - 2, _xs.min() - 1, -6) if (_xs == x).any()], float)
def at(a, x, y):
    x = np.clip(x, 0, a.shape[1] - 1.001); y = np.clip(y, 0, a.shape[0] - 1.001)
    ix, iy = int(x), int(y); fx, fy = x - ix, y - iy
    return a[iy, ix] * (1 - fx) * (1 - fy) + a[iy, ix + 1] * fx * (1 - fy) + a[iy + 1, ix] * (1 - fx) * fy + a[iy + 1, ix + 1] * fx * fy
L, R = [], []
dense = []
for a, b in zip(pts[:-1], pts[1:]):
    n = int(np.linalg.norm(b - a))
    for u in np.linspace(0, 1, n, endpoint=False): dense.append(a + (b - a) * u)
dense = np.array(dense)
for i, c in enumerate(dense):
    d = dense[min(i + 1, len(dense) - 1)] - dense[max(i - 1, 0)]; d /= np.linalg.norm(d) + 1e-9
    nrm = np.array([-d[1], d[0]])
    core = np.median([at(lo, *(c + nrm * t)) for t in (-2, -1, 0, 1, 2)])
    edges = []
    for sgn in (1, -1):
        e = None
        for t in np.arange(1, 22, 0.5):
            p = c + nrm * t * sgn
            if not lim[int(p[1]), int(p[0])]: e = t - 0.5; break
            book = at(lc, *p)
            if at(lo, *p) > (core + book) / 2 and book - core > 6: e = t; break
        edges.append(e if e is not None else 21)
    if np.median([at(lc, *(c + nrm * t)) for t in (-1, 0, 1)]) - core < 5:
        edges = [0, 0]   # тут под осью не хвост
    L.append(c + nrm * edges[0]); R.append(c - nrm * edges[1])
poly = [tuple(p) for p in L] + [tuple(p) for p in R[::-1]]
m = Image.new('L', O.size, 0); ImageDraw.Draw(m).polygon(poly, fill=255)
m = m.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
np.save(out, np.asarray(m) > 127)
print('slices', len(L), 'of', len(dense))
m.crop((1040, 560, 1260, 700)).resize((660, 420)).save(out.replace('.npy', '.png'))
