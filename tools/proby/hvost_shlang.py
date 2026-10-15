# Хвост как шланг: одна ручка — насколько поднят. Изгиб ровный по длине (как у шланга), без перегибов;
# хвост целиком с обводкой, толщина не меняется, основание прибито. Кадры: синий → красный → бирюзовый → жёлтый.
import sys, math, numpy as np, subprocess
from PIL import Image
src = open('kadry4.py').read().split("FR = ")[0]
sys_argv = sys.argv[:]
exec(src)
out = sys_argv[1]
ramp = np.clip((s - 0.15) / 0.85, 0, 1)                 # ровная кривизна от 15 % длины до кончика
bend = np.cumsum(ramp); bend /= bend[-1]
LEVELS = [-4, 28, 56, 84]                               # градусы на кончике: синий, красный, бирюзовый, жёлтый
def thv(u):                                             # u 0…3 по кадрам, плавно
    i = min(int(u), 2); f = u - i; f = f * f * (3 - 2 * f)
    return TH[0] + math.radians(LEVELS[i] + (LEVELS[i + 1] - LEVELS[i]) * f) * bend
def ss(x): return x * x * (3 - 2 * x)
fps = 24; HOLD, UP, TOP, DOWN = 5.0, 2.0, 0.6, 2.4
seq = [0.0] * int(HOLD * fps) + [3 * ss(t / (UP * fps)) for t in range(int(UP * fps))] + [3.0] * int(TOP * fps) + [3 * (1 - ss(t / (DOWN * fps))) for t in range(int(DOWN * fps))]
WN = (np.asarray(Image.fromarray((M > 0.02).astype(np.uint8) * 255).resize(M.shape[::-1]), np.float32) / 255)
restF = frame(thv(0))
size = (660, 420)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
for rep in range(2):
    for u in seq:
        F = frame(thv(u))
        p.stdin.write(np.asarray(Image.fromarray(np.clip(F, 0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)).tobytes())
p.stdin.close(); p.wait()
