# Оживление поз хвоста по рисунку автора: позы 1…8 связаны плавно (без остановок в каждой позе),
# каждое звено чуть позже предыдущего (импульс от основания), падение «щух», остановка чёткая.
import sys, math, numpy as np, subprocess
from PIL import Image
OUT2_ = sys.argv[1]; MODE2_ = sys.argv[2] if len(sys.argv) > 2 else 'video'
src = open('pozy_avtora2.py').read().split("if __name__ == '__main__':")[0]
sys.argv = ['x', 'none']; exec(src)
def tip_down(th, deg, start=0.5):                    # кончик чуть ниже
    x = np.clip((s - start) / (1 - start), 0, 1); return th - math.radians(deg) * x * x * (3 - 2 * x)
def lying_base(up_deg, start=0.45):
    x = np.clip((s - start) / (1 - start), 0, 1); return th0 + math.radians(up_deg) * x * x * (3 - 2 * x)
P = {k: pose(v) for k, v in LINES.items()}
KEYS = [  # (время от начала движения, поза, перспектива)
    (0.00, th0, 1.00),
    (1.10, tip_down(P['вверх 2 (прямее)'], 18), 0.98),   # лениво вверх
    (2.00, P['вверх 3 (горб)'], 0.94),
    (2.40, P['вверх 4 (крючок)'], 0.88),                 # перелом — быстро, работает кончик
    (2.85, P['вниз 1'], 0.88),                           # загиб чуть больше, зависает
    (3.15, P['вниз 1'], 0.88),
    (3.50, P['вниз 2 (J)'], 0.92),                       # «щух» вниз от основания
    (3.80, lying_base(115), 0.97),
    (4.15, th0, 1.00),                                   # кончик лёг последним, замер
]
HOLD, LAG = 5.0, 0.12
KT = np.array([k[0] for k in KEYS]); KTH = np.array([k[1] for k in KEYS]); KSC = np.array([k[2] for k in KEYS])
def hermite(t, V):                                   # плавно через все позы (Катмулл-Ром), на концах — с нулевой скоростью
    if t <= KT[0]: return V[0]
    if t >= KT[-1]: return V[-1]
    i = np.searchsorted(KT, t) - 1; t0, t1 = KT[i], KT[i + 1]; u = (t - t0) / (t1 - t0)
    def tan(j):
        if j == 0 or j == len(KT) - 1 or np.allclose(V[j - 1], V[j + 1]) and np.allclose(V[j], V[j - 1]): return 0 * V[j]
        return (V[j + 1] - V[j - 1]) / (KT[j + 1] - KT[j - 1])
    m0, m1 = tan(i) * (t1 - t0), tan(i + 1) * (t1 - t0)
    if np.allclose(V[i], V[i + 1]): m0 = m1 = 0 * V[i]   # зависание — без дрожи
    h00 = 2*u**3 - 3*u**2 + 1; h10 = u**3 - 2*u**2 + u; h01 = -2*u**3 + 3*u**2; h11 = u**3 - u**2
    return h00 * V[i] + h10 * m0 + h01 * V[i + 1] + h11 * m1
def at(t):
    t = t - HOLD
    th_ = np.array([hermite(t - LAG * x, KTH)[j] for j, x in enumerate(s)])
    sc = np.array([float(hermite(t - LAG * x, KSC)) for x in s])
    return th_, sc
CYCLE = HOLD + KT[-1] + LAG + 0.2
fps = 24; n = int(round(CYCLE * fps)); w, h = x1 - x0, y1 - y0
crop = MODE2_ == 'crop'; size = (w, h) if crop else (690, 750)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '10' if crop else '16', '-pix_fmt', 'yuv444p' if crop else 'yuv420p', OUT2_], stdin=subprocess.PIPE)
for rep in range(1 if crop else 2):
    for fi in range(n):
        th_, sc = at(fi / fps); im = Image.fromarray(np.clip(frame_p(th_, sc), 0, 255).astype(np.uint8))
        p.stdin.write(np.asarray(im if crop else im.resize(size, Image.LANCZOS)).tobytes())
p.stdin.close(); p.wait()
