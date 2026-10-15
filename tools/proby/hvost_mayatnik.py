# Хвост — цепочка-маятник (по присланной инструкции): 8 звеньев, крутим ТОЛЬКО звено 0 у основания,
# каждое следующее звено каждый кадр догоняет предыдущее: angle_i += (angle_{i-1} − angle_i) · DAMP.
# Наш хвост нарисован изогнутым, поэтому звенья догоняют не абсолютный угол, а поворот от нарисованной формы
# (иначе хвост в покое стал бы прямой палкой). Координаты — шаг за шагом от основания, кривая гладкая через суставы.
# Основание крутим не бесконечной синусоидой, а нашим циклом: лежит → медленно вверх → зависает → быстрее вниз.
import sys, math, numpy as np, subprocess
from PIL import Image, ImageDraw, ImageFont
OUTC_ = sys.argv[1]; MODEC_ = sys.argv[2] if len(sys.argv) > 2 else 'lines'
sys.argv = ['x', OUTC_, 'none']
exec(open('buzan2.py').read().split("UPP = ")[0])
NJ = 8; DAMP = 0.2; MAXANG = math.radians(95); fps = 24
HOLD, UP, TOP, DOWN = 5.0, 2.6, 0.4, 1.5
def ease(u): u = min(max(u, 0.0), 1.0); return u * u * (3 - 2 * u)
def base_drive(t):
    t -= HOLD
    if t < 0: return 0.0
    if t < UP: return ease(t / UP)
    t -= UP
    if t < TOP: return 1.0
    return 1 - ease((t - TOP) / DOWN)
CYCLE = HOLD + UP + TOP + DOWN + 2.0
n = int(round(CYCLE * fps)); off = np.zeros(NJ); HIST = []
for fi in range(2 * n):                                  # прогоняем два цикла, берём второй (цепочка «разогрета»)
    t = (fi % n) / fps
    off[0] = MAXANG * base_drive(t)
    for i in range(1, NJ):
        off[i] += (off[i - 1] - off[i]) * DAMP
    if fi >= n: HIST.append(off.copy())
JS = np.linspace(0, 1, NJ)
def at_frame(k):
    o = np.interp(s, JS, HIST[k])                        # поворот звеньев → плавно по всей длине
    return on_surface(th0 + o), np.ones(len(s))
if MODEC_ == 'lines':
    Z = 3; base = Image.fromarray(np.clip(O, 0, 255).astype(np.uint8)).resize(((x1 - x0) * Z, (y1 - y0) * Z), Image.LANCZOS)
    fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22); out = Image.new('RGB', (base.width * 2, base.height))
    panels = [('ВВЕРХ (каждые 0.5 с)', np.arange(HOLD + 0.5, HOLD + UP + TOP + 0.01, 0.5), (255, 60, 60)),
              ('ВНИЗ (каждые 0.35 с)', np.arange(HOLD + UP + TOP, CYCLE - 0.5, 0.35), (255, 255, 255))]
    for k, (title, T, col) in enumerate(panels):
        im = base.copy(); d = ImageDraw.Draw(im)
        Pp = (build_p(th0, np.ones(len(s))) - [x0, y0]) * Z; d.line([tuple(p) for p in Pp], fill=(120, 220, 255), width=4)
        for i, t in enumerate(T):
            Pp = (build_p(*at_frame(min(int(round(t * fps)), n - 1))) - [x0, y0]) * Z
            d.line([tuple(p) for p in Pp], fill=col, width=3, joint='curve')
            d.text(tuple(Pp[-1] + [-8, -24]), str(i + 1), fill=col, font=fnt, stroke_width=3, stroke_fill=(0, 0, 0))
        d.text((10, 8), title + ', голубой — нарисованный', fill=(255, 240, 200), font=fnt, stroke_width=3, stroke_fill=(0, 0, 0))
        out.paste(im, (k * base.width, 0))
    out.save(OUTC_); sys.exit()
w_, h_ = x1 - x0, y1 - y0; crop = MODEC_ == 'crop'; size = (w_, h_) if crop else (690, 750)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '10' if crop else '16', '-pix_fmt', 'yuv444p' if crop else 'yuv420p', OUTC_], stdin=subprocess.PIPE)
for rep in range(1 if crop else 2):
    for k in range(n):
        im = Image.fromarray(np.clip(frame_p(*at_frame(k)), 0, 255).astype(np.uint8))
        p.stdin.write(np.asarray(im if crop else im.resize(size, Image.LANCZOS)).tobytes())
p.stdin.close(); p.wait()
