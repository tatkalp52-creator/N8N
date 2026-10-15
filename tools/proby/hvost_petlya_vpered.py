# Петля по образцу (Kling) только ВПЕРЁД: в ролике ищется пара кадров, где хвост почти совпадает (LOOP_A ≈ LOOP_B),
# и движение крутится между ними; стык — на спокойном месте с коротким смешиванием. Остановки — плавное торможение и разгон.
import sys, numpy as np, subprocess, glob
from PIL import Image
orig_path, video_frames, out, mask_path = sys.argv[1:5]
CROP = (880, 385, 544)
FPS = 24; OW, OH = 1920, 1080; K = OW / 1536
LOOP_A, LOOP_B = 25, 109          # найдено поиском: кадры, где хвост почти одинаковый
STOP1, STOP2 = 60, 98             # спокойные позы: свешен справа, у лап
HOLD1, HOLD2 = 2.0, 2.0           # сколько стоять, секунд
SLOW = 1.25                       # движение чуть медленнее образца
XF = 5                            # кадров смешивания на стыке
orig = Image.open(orig_path).convert('RGB').resize((OW, OH), Image.LANCZOS)
cx, cy, cw = CROP; ch = cw * 9 / 16
bx, by, bw, bh = round(cx * K), round(cy * K), round(cw * K), round(ch * K)
fr = [np.asarray(Image.open(f).convert('RGB').resize((bw, bh), Image.LANCZOS)).astype(np.float32) for f in sorted(glob.glob(video_frames))]
base = np.asarray(orig).astype(np.float32)[by:by + bh, bx:bx + bw]
MASK = (np.asarray(Image.open(mask_path).convert('L').resize((bw, bh))).astype(np.float32) / 255)[..., None]
L = LOOP_B - LOOP_A
def raw(x):
    i = int(np.floor(x)); u = x - i; i = max(0, min(i, len(fr) - 1)); j = min(i + 1, len(fr) - 1)
    return fr[i] * (1 - u) + fr[j] * u
def at(v):                        # «виртуальный» кадр на бесконечной петле
    v = LOOP_A + (v - LOOP_A) % L
    if v > LOOP_B - XF:           # подходим к стыку: плавно смешиваем с тем же местом в начале петли
        w = (v - (LOOP_B - XF)) / XF; w = w * w * (3 - 2 * w)
        return raw(v) * (1 - w) + raw(v - L) * w
    return raw(v)
def ease(u): return u * u * (3 - 2 * u)
def move(a, b):                   # a → b вперёд по петле
    if b <= a: b += L
    n = int(round((b - a) / FPS * SLOW * FPS * 1.25))   # плавный разгон/торможение съедают скорость — даём чуть больше времени
    return [a + (b - a) * ease(t / n) for t in range(1, n + 1)]
REST_HOLD = float(sys.argv[5]) if len(sys.argv) > 5 else 8.0   # пауза у лап между взмахами, секунд
def sweep(a):                     # один полный круг вперёд из позы a в неё же
    n = int(round(L / FPS * SLOW * FPS * 1.25))
    return [a + L * ease(t / n) for t in range(1, n + 1)]
REST = LOOP_B                     # покой — хвост обнимает лапы (это же и стык петли: стык прячется в паузе)
seq = [float(REST)] * int(REST_HOLD * FPS) + sweep(REST)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}', '-r', str(FPS), '-i', '-',
                      '-c:v', 'libx264', '-crf', '17', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
full = np.asarray(orig).copy()
for rep in range(2):
    for v in seq:
        f = base * (1 - MASK) + at(v) * MASK
        img = full.copy(); img[by:by + bh, bx:bx + bw] = np.clip(f, 0, 255).astype(np.uint8)
        p.stdin.write(img.tobytes())
p.stdin.close(); p.wait()
print('круг', round(len(seq) / FPS, 1), 'с')
