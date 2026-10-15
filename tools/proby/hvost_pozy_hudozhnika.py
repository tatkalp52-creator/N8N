# Проба: позы хвоста от Художника → движение перетеканием по оптическому потоку, только в области хвоста.
import cv2, numpy as np, subprocess, sys
P = [cv2.imread(f'p{i}.png').astype(np.float32) for i in range(4)]
g = [cv2.cvtColor(p.astype(np.uint8), cv2.COLOR_BGR2GRAY) for p in P]
# область, где что-то меняется (хвост), с запасом
m = np.zeros(g[0].shape, np.uint8)
for i in (1, 2, 3):
    d = np.abs(cv2.GaussianBlur(g[i], (0, 0), 3).astype(float) - cv2.GaussianBlur(g[0], (0, 0), 3).astype(float))
    m |= (d > 22).astype(np.uint8)
m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
m = cv2.dilate(m, np.ones((41, 41), np.uint8))
M = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 12)[..., None]
cv2.imwrite('mask.png', (M[..., 0] * 255).astype(np.uint8))
dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_ULTRAFAST + 2)
H, W = g[0].shape
gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
def morph(a, b, n):
    fab = dis.calc(g[a], g[b], None); fba = dis.calc(g[b], g[a], None)
    out = []
    for k in range(1, n + 1):
        t = k / n; t = t * t * (3 - 2 * t)
        wa = cv2.remap(P[a], gx - t * fba[..., 0] * -1 * 0 + (-t) * fab[..., 0] * 0 + gx * 0 + 0, gy, cv2.INTER_LINEAR) if False else None
        Ia = cv2.remap(P[a], gx + t * fba[..., 0], gy + t * fba[..., 1], cv2.INTER_LINEAR)
        Ib = cv2.remap(P[b], gx + (1 - t) * fab[..., 0], gy + (1 - t) * fab[..., 1], cv2.INTER_LINEAR)
        I = Ia * (1 - t) + Ib * t
        out.append(P[0] * (1 - M) + I * M)
    return out
fps = 24
seq = [P[0]] * 36 + morph(0, 3, 18) + [P[0] * (1 - M) + P[3] * M] * 6 + morph(3, 1, 18) + [P[0] * (1 - M) + P[1] * M] * 18 + morph(1, 0, 24)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
                      '-vf', 'crop=900:520:300:380', '-c:v', 'libx264', '-crf', '17', '-pix_fmt', 'yuv420p', 'morph.mp4'], stdin=subprocess.PIPE)
for rep in range(2):
    for f in seq: p.stdin.write(np.clip(f, 0, 255).astype(np.uint8).tobytes())
p.stdin.close(); p.wait()
