import sys, math, subprocess, numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.argv = ['x', '../font/cat.img', 'erased.jpg', 'x', 'inside.npy']
exec(open('hvost.py').read().split("if __name__")[0])
NJ = 12
JS = np.linspace(0.03, 0.92, NJ)          # первый шарнир — у самого тела
JP = [seg[np.searchsorted(sof, j)] for j in JS]
BW = 0.08
def prof(t, up, hold, down):
    if t <= 0: return 0.0
    if t < up: return ss(t / up)
    if t < up + hold: return 1.0
    return 1 - ss((t - up - hold) / down)
def wave(sign, base, rest_bend):
    def f(t):
        o = np.zeros(NJ)
        for j, s in enumerate(JS):
            k = prof(t - 0.6 * s, 1.2, 0.6, 1.6)            # кончик догоняет с опозданием
            amp = base if j == 0 else rest_bend * (0.6 + s)  # от тела — главный поворот, дальше — мягкий изгиб
            o[j] = sign * math.radians(amp * k)
        return o
    return f
D = wave(-1, 4.0, 0.9)    # вниз по книге — к лапам
E = wave(+1, 4.0, 0.9)    # приподнять от основания
fps = 24
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 34)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '660x420', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', 'variants2.mp4'], stdin=subprocess.PIPE)
for name, fn, sec in (('D  к лапам', D, 6), ('E  от основания вверх', E, 6)):
    for rep in range(2):
        for f in range(fps * sec):
            F = frame(fn(f / fps - 0.3))
            img = (F * WN + (O + F - rest) * (1 - WN))
            im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((660, 420), Image.LANCZOS)
            d = ImageDraw.Draw(im); d.text((14, 10), name, font=font, fill=(255, 235, 180), stroke_width=3, stroke_fill=(0, 0, 0))
            p.stdin.write(np.asarray(im).tobytes())
p.stdin.close(); p.wait()
for fn in (D, E): print([round(math.degrees(fn(t).sum()), 1) for t in np.arange(0, 5, 0.5)])
