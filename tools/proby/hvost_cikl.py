# Хвост по позам, снятым с образца (Kling), с замкнутым циклом.
# Вход: KEYS — [(секунда, [(x,y) основание → кончик]), ...]; последняя поза возвращается в первую.
# Наш нарисованный хвост гнётся вдоль линии каждой позы (длина может меняться — это перспектива).
import sys, math, numpy as np, subprocess
from PIL import Image, ImageFilter
args = sys.argv[1:]
sys.argv = ['x', '../font/cat.img', 'erased.jpg', 'x', 'inside.npy']
exec(open('poses2.py').read().split("if __name__")[0])
_sw = open('sway.py').read(); exec(_sw[_sw.index("TIGHT = np.load"):_sw.index("ALPHA =")])
sys.path.insert(0, '../kling'); from keys import KEYS
out = args[0]; RETURN = float(args[1]) if len(args) > 1 else 0.7   # сколько секунд на возврат в исходную позу
T_END = KEYS[-1][0] + RETURN
keys = KEYS + [(T_END, KEYS[0][1])]
KP = [resample(p)[0] for _, p in keys]            # каждая поза — N точек равномерно по её длине
KT = [t for t, _ in keys]
def pose_at(t):
    t = t % T_END
    i = max(k for k in range(len(KT) - 1) if KT[k] <= t)
    u = (t - KT[i]) / (KT[i + 1] - KT[i])
    p0, p1, p2, p3 = KP[(i - 1) % (len(KP) - 1)], KP[i], KP[i + 1], KP[(i + 2) % (len(KP) - 1)]
    # Catmull-Rom по времени: движение проходит через все позы плавно, без остановок на каждой
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)
def frame_curve(Pimg):
    DE = ext(Pimg); DT = tangents(DE); DN = np.stack([-DT[:, 1], DT[:, 0]], -1)
    d2 = ((Q[:, :, None, :] - DE[None, None]) ** 2).sum(-1); i = d2.argmin(-1)
    v = Q - DE[i]; n = (v * DN[i]).sum(-1); t = (v * DT[i]).sum(-1)
    # длина хвоста в позе может отличаться от покоя: переводим позицию вдоль линии в позицию на исходном хвосте
    src = RE[i] + n[..., None] * RN[i] + t[..., None] * RT[i]
    a = (sample(M, src) * (np.sqrt(d2.min(-1)) < 16))[..., None]
    return C * (1 - a) + sample(O, src) * a
restC = frame_curve(KP[0])
fps = 24; nf = int(round(T_END * fps))
zoom = 'z' in out
size = (796, 436) if zoom else (1920, 1080)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
for rep in range(2):
    for f in range(nf):
        F = frame_curve(pose_at(f / fps)); img = F * WN + (O + F - restC) * (1 - WN)
        if zoom: im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)
        else:
            fr = orig.copy(); fr[y0:y1, x0:x1] = img; im = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)
        p.stdin.write(np.asarray(im).tobytes())
p.stdin.close(); p.wait()
print('frames', nf, 'loop', T_END)
