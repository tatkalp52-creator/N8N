# Хвост живёт по кадрам образца (Kling): замирает в спокойных позах и переходит между ними
# по пути образца вперёд или назад, с плавным разгоном/торможением. Наш нарисованный хвост не используется.
import sys, numpy as np, subprocess, glob
from PIL import Image, ImageFilter
orig_path, video_frames, out = sys.argv[1], sys.argv[2], sys.argv[3]
CROP = (880, 385, 544)
FPS = 24; OW, OH = 1920, 1080; K = OW / 1536
STOPS = {'A': 0, 'B': 60, 'C': 98}            # кадры образца, где хвост почти стоит (0 = первый)
PLAN = ['A', 2.0, 'B', 2.5, 'C', 2.5, 'B', 2.0, 'C', 2.0, 'B', 1.5, 'A', 0.0]   # поза, сколько стоять, следующая поза…
SLOW = 1.25                                   # переход чуть медленнее образца
orig = Image.open(orig_path).convert('RGB').resize((OW, OH), Image.LANCZOS)
cx, cy, cw = CROP; ch = cw * 9 / 16
bx, by, bw, bh = round(cx * K), round(cy * K), round(cw * K), round(ch * K)
fr = [np.asarray(Image.open(f).convert('RGB').resize((bw, bh), Image.LANCZOS)).astype(np.float32) for f in sorted(glob.glob(video_frames))]
base = np.asarray(orig).astype(np.float32)[by:by + bh, bx:bx + bw]
MASK = (np.asarray(Image.open(sys.argv[4]).convert('L').resize((bw, bh))).astype(np.float32) / 255)[..., None]
def at(x):                                    # кадр образца в дробной позиции: смешиваем соседние
    i = int(np.floor(x)); u = x - i; i = max(0, min(i, len(fr) - 1)); j = min(i + 1, len(fr) - 1)
    return fr[i] * (1 - u) + fr[j] * u
def ease(u): return u * u * (3 - 2 * u)
seq = []
for k in range(0, len(PLAN) - 2, 2):
    a, hold, b = STOPS[PLAN[k]], PLAN[k + 1], STOPS[PLAN[k + 2]]
    seq += [float(a)] * int(round(hold * FPS))
    n = int(round(abs(b - a) / FPS * SLOW * FPS))
    seq += [a + (b - a) * ease(t / n) for t in range(1, n + 1)]
seq += [float(STOPS[PLAN[-2]])] * int(round(PLAN[-1] * FPS))
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}', '-r', str(FPS), '-i', '-',
                      '-c:v', 'libx264', '-crf', '17', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
full = np.asarray(orig).copy()
for rep in range(2):
    for x in seq:
        f = base * (1 - MASK) + at(x) * MASK
        img = full.copy(); img[by:by + bh, bx:bx + bw] = np.clip(f, 0, 255).astype(np.uint8)
        p.stdin.write(img.tobytes())
p.stdin.close(); p.wait()
print('секунд в круге', round(len(seq) / FPS, 1))
