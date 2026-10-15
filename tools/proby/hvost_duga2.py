# Хвост как ровная дуга (все звенья гнутся одинаково); меняется кривизна: покой → почти прямо → дуга вверх → к полукругу.
# Импульс от попы к кончику (каждое звено позже), при подъёме звенья чуть укорачиваются (перспектива). Длина звеньев одна.
import sys, math, numpy as np, subprocess
from PIL import Image
argv = sys.argv[:]
exec(open('kadry5.py').read().split("FR = ")[0])
out = argv[1]; mode = argv[2] if len(argv) > 2 else 'video'
th0 = TH[0]; rest_total = math.degrees(th0[-1] - th0[0])
TOTALS = [0.0, 10.0, 75.0, 165.0]           # поворот кончика относительно основания; гнётся сильнее к кончику (кривизна растёт к концу)
BASEROT = [0.0, 4.0, 10.0, 16.0]            # основание жёсткое: поворачивается чуть-чуть
def shape(level, persp):
    tot = math.radians(np.interp(level, [0, 1, 2, 3], TOTALS)); br = math.radians(np.interp(level, [0, 1, 2, 3], BASEROT))
    arc = th0[0] + br + tot * s ** 2                # у попы почти не гнётся, к кончику всё сильнее
    w = min(1.0, level)
    return th0 * (1 - w) + arc * w
_build = build
def build_p(thv, scale):
    P = np.zeros((N, 2)); P[0] = BASE
    P[1:] = BASE + np.cumsum(np.stack([np.cos(thv), np.sin(thv)], -1) * step * scale[:, None], 0)
    return P
def frame_p(thv, scale):
    DE = ext(build_p(thv, scale)); DT = tangents(DE); DN = np.stack([-DT[:, 1], DT[:, 0]], -1)
    d2 = ((Q[:, :, None, :] - DE[None, None]) ** 2).sum(-1); i = d2.argmin(-1)
    v = Q - DE[i]; n = (v * DN[i]).sum(-1); t = (v * DT[i]).sum(-1)
    k_ = np.concatenate([np.full(12, scale[0]), np.r_[scale[0], scale], np.full(12, scale[-1])])[i]
    src = RE[i] + n[..., None] * RN[i] + (t / k_)[..., None] * RT[i]
    a = (sample(M, src) * (np.sqrt(d2.min(-1)) < 22))[..., None]
    return C * (1 - a) + sample(O, src) * a
def ss(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
HOLD, UP, TOP, DOWN, LAG = 5.0, 2.2, 0.7, 2.6, 0.35
def lvl(t):
    if t < HOLD: return 0.0
    t -= HOLD
    if t < UP: return 3 * ss(t / UP)
    t -= UP
    if t < TOP: return 3.0
    t -= TOP
    if t < DOWN: return 3 * (1 - ss(t / DOWN))
    return 0.0
def at(t):
    # каждое звено своё время: импульс от попы к кончику
    ls = np.array([lvl(t - LAG * x) for x in s])
    shapes = np.array([shape(l, 0)[j] for j, l in enumerate(ls)])
    scale = 1 - 0.18 * (ls / 3) * s                 # перспектива: поднятые звенья на экране короче, сильнее к кончику
    return shapes, scale
if mode == 'stills':
    from PIL import ImageDraw, ImageFont
    f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22); ims = []
    for k in range(4):
        sc = 1 - 0.18 * (k / 3) * s
        F = frame_p(shape(k, 0), sc); im = Image.fromarray(np.clip(F, 0, 255).astype(np.uint8)).resize((460, 500), Image.LANCZOS)
        ImageDraw.Draw(im).text((10, 6), str(k + 1), fill=(255, 230, 170), font=f, stroke_width=3, stroke_fill=(0, 0, 0)); ims.append(im)
    cv = Image.new('RGB', (920, 1000))
    for k, im in enumerate(ims): cv.paste(im, ((k % 2) * 460, (k // 2) * 500))
    cv.save(out); sys.exit()
fps = 24; n = int((HOLD + UP + TOP + DOWN + LAG) * fps); size = (690, 750)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
for rep in range(2):
    for fi in range(n):
        th_, sc = at(fi / fps); F = frame_p(th_, sc)
        p.stdin.write(np.asarray(Image.fromarray(np.clip(F, 0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)).tobytes())
p.stdin.close(); p.wait()
