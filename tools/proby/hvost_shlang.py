# Хвост как шланг: одна ручка — насколько поднят. Изгиб ровный по длине (как у шланга), без перегибов;
# хвост целиком с обводкой, толщина не меняется, основание прибито. Кадры: синий → красный → бирюзовый → жёлтый.
import sys, math, numpy as np, subprocess
from PIL import Image
src = open('kadry4.py').read().split("FR = ")[0]
sys_argv = sys.argv[:]
exec(src)
out = sys_argv[1]
bend = s ** 1.4                                         # позвонки от самой попы; к кончику каждый гнётся чуть сильнее — хвост остаётся дугой, не палкой
LAG = 0.35                                              # импульс бежит от попы к кончику: кончик отстаёт на 0.35 с
LEVELS = [-4, 28, 56, 84]                               # градусы на кончике: синий, красный, бирюзовый, жёлтый
def thv_t(t):                                           # у каждого позвонка своё время: чем дальше от попы, тем позже
    ts = t - LAG * s
    u = np.array([ku(x) for x in ts])
    ang = np.interp(u, [0, 1, 2, 3], LEVELS)
    return TH[0] + np.radians(ang) * bend
def ss(x): return x * x * (3 - 2 * x)
fps = 24; HOLD, UP, TOP, DOWN = 5.0, 2.0, 0.6, 2.4
def ku(t):
    if t < HOLD: return 0.0
    t -= HOLD
    if t < UP: return 3 * ss(t / UP)
    t -= UP
    if t < TOP: return 3.0
    t -= TOP
    if t < DOWN: return 3 * (1 - ss(t / DOWN))
    return 0.0
TOTAL = HOLD + UP + TOP + DOWN + LAG
seq = [f / fps for f in range(int(TOTAL * fps))]
WN = (np.asarray(Image.fromarray((M > 0.02).astype(np.uint8) * 255).resize(M.shape[::-1]), np.float32) / 255)

size = (660, 420)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
for rep in range(2):
    for t in seq:
        F = frame(thv_t(t))
        p.stdin.write(np.asarray(Image.fromarray(np.clip(F, 0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)).tobytes())
p.stdin.close(); p.wait()
