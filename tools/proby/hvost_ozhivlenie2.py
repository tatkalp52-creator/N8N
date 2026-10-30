# Оживление плавных поз (pozy_plavno.py): медленно вверх, быстрее вниз; позы связаны плавно, звенья чуть позже от основания.
import sys, numpy as np, subprocess
OUT5_ = sys.argv[1]; MODE5_ = sys.argv[2] if len(sys.argv) > 2 else 'video'
exec(open('pozy_plavno.py').read().split("if __name__ == '__main__':")[0])
PT = dict(POSES)
KEYS = [(0.00, '1 лежит'), (1.50, '2 кончик ниже'), (2.80, '3 горб → загиб'), (3.70, '4 подзавис вверху'),
        (4.10, '4 подзавис вверху'),                                                # медленно вверх, зависает
        (4.50, '5 основание пошло вниз'), (4.85, '6 J'), (5.20, '7 основание легло'), (5.60, '8 лежит')]   # быстрее вниз           # быстрее вниз, кончик последним
HOLD, LAG = 5.0, 0.12
KT = np.array([k[0] for k in KEYS]); KTH = np.array([PT[k[1]] for k in KEYS])
def hermite(t):
    if t <= KT[0]: return KTH[0]
    if t >= KT[-1]: return KTH[-1]
    i = np.searchsorted(KT, t) - 1; t0, t1 = KT[i], KT[i + 1]; u = (t - t0) / (t1 - t0)
    def tan(j):
        if j == 0 or j == len(KT) - 1 or np.allclose(KTH[j], KTH[j - 1]) or np.allclose(KTH[j], KTH[j + 1]): return 0 * KTH[j]
        return (KTH[j + 1] - KTH[j - 1]) / (KT[j + 1] - KT[j - 1])
    m0, m1 = tan(i) * (t1 - t0), tan(i + 1) * (t1 - t0)
    h00 = 2*u**3 - 3*u**2 + 1; h10 = u**3 - 2*u**2 + u; h01 = -2*u**3 + 3*u**2; h11 = u**3 - u**2
    return h00 * KTH[i] + h10 * m0 + h01 * KTH[i + 1] + h11 * m1
def at(t):
    t -= HOLD
    return np.array([hermite(t - LAG * x)[j] for j, x in enumerate(s)]), np.ones(len(s))
CYCLE = HOLD + KT[-1] + LAG + 0.2
fps = 24; n = int(round(CYCLE * fps)); w, h = x1 - x0, y1 - y0
crop = MODE5_ == 'crop'; size = (w, h) if crop else (690, 750)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '10' if crop else '16', '-pix_fmt', 'yuv444p' if crop else 'yuv420p', OUT5_], stdin=subprocess.PIPE)
for rep in range(1 if crop else 2):
    for fi in range(n):
        th_, sc = at(fi / fps); im = Image.fromarray(np.clip(frame_p(th_, sc), 0, 255).astype(np.uint8))
        p.stdin.write(np.asarray(im if crop else im.resize(size, Image.LANCZOS)).tobytes())
p.stdin.close(); p.wait()
