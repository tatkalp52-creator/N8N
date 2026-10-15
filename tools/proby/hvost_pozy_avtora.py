# Хвост по позам, нарисованным автором синим маркером: наш нарисованный хвост ложится на каждую её линию,
# между позами — плавное перетекание; пауза на позе «у лап», взмах по её позам, петля.
import sys, json, math, numpy as np, subprocess
from PIL import Image, ImageFilter
args = sys.argv[1:]
sys.argv = ['x', '../font/cat.img', 'erased.jpg', 'x', 'inside.npy']
exec(open('poses2.py').read().split("if __name__")[0])
_sw = open('sway.py').read(); exec(_sw[_sw.index("TIGHT = np.load"):_sw.index("ALPHA =")])
L = json.load(open('../blue/lines.json'))
POS = [[BASE] + [tuple(p) for p in L[k]] for k in sorted(L, key=int)]
KP = [resample(p)[0] for p in POS]
def frame_curve(Pimg):
    DE = ext(Pimg); DT = tangents(DE); DN = np.stack([-DT[:, 1], DT[:, 0]], -1)
    d2 = ((Q[:, :, None, :] - DE[None, None]) ** 2).sum(-1); i = d2.argmin(-1)
    v = Q - DE[i]; n = (v * DN[i]).sum(-1); t = (v * DT[i]).sum(-1)
    src = RE[i] + n[..., None] * RN[i] + t[..., None] * RT[i]
    a = (sample(M, src) * (np.sqrt(d2.min(-1)) < 16))[..., None]
    return C * (1 - a) + sample(O, src) * a
out = args[0]
mode = args[1] if len(args) > 1 else 'video'
if mode == 'stills':
    ims = []
    for P in KP:
        F = frame_curve(P); fr = orig.copy(); fr[y0:y1, x0:x1] = F
        ims.append(Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).crop((1000, 540, 1300, 700)).resize((600, 320), Image.LANCZOS))
    c = Image.new('RGB', (1200, 640))
    for k, im in enumerate(ims): c.paste(im, ((k % 2) * 600, (k // 2) * 320))
    c.save(out); sys.exit()
HOLD = float(args[2]) if len(args) > 2 else 6.0
SWEEP = float(args[3]) if len(args) > 3 else 3.0
order = [0, 1, 2, 3, 0]                     # у лап → … → у лап
def ss(x): return x * x * (3 - 2 * x)
def pose(u):                                 # u 0…1 по взмаху, Catmull-Rom через позы
    seg = u * (len(order) - 1); i = min(int(seg), len(order) - 2); f = seg - i
    p0, p1, p2, p3 = (KP[order[max(i - 1, 0)]], KP[order[i]], KP[order[i + 1]], KP[order[min(i + 2, len(order) - 1)]])
    return 0.5 * ((2 * p1) + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f + (-p0 + 3 * p1 - 3 * p2 + p3) * f ** 3)
fps = 24
seq = [KP[0]] * int(HOLD * fps) + [pose(ss(t / (SWEEP * fps))) for t in range(1, int(SWEEP * fps) + 1)]
restC = frame_curve(KP[0])
zoom = 'z' in out
size = (796, 436) if zoom else (1920, 1080)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
for rep in range(2):
    for P in seq:
        F = frame_curve(P); img = F * WN + (O + F - restC) * (1 - WN) if False else F
        if zoom: im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)
        else:
            fr = orig.copy(); fr[y0:y1, x0:x1] = img; im = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)
        p.stdin.write(np.asarray(im).tobytes())
p.stdin.close(); p.wait()
