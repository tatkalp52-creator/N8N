import sys, math, subprocess, numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.argv = ['x', '../font/cat.img', 'erased.jpg', 'x', 'inside.npy']
exec(open('hvost.py').read().split("if __name__")[0])
def prof(t, up, hold, down):
    if t <= 0: return 0.0
    if t < up: return ss(t / up)
    if t < up + hold: return 1.0
    return 1 - ss((t - up - hold) / down)
def A(t):   # мягкое обмахивание: весь хвост чуть-чуть, кончик догоняет позже
    o = np.zeros(NJ)
    for j, s in enumerate(JS):
        e = ss((s - 0.15) / 0.85)
        o[j] = math.radians(1.6 * e * prof(t - 0.75 * s, 1.3, 0.5, 1.8))
    return o
def B(t):   # кончик постукивает два раза
    o = np.zeros(NJ)
    for j, s in enumerate(JS):
        e = ss((s - 0.6) / 0.35)
        tap = prof(t - 0.2 * s, 0.4, 0.1, 0.5) + 0.8 * prof(t - 1.3 - 0.2 * s, 0.4, 0.1, 0.6)
        o[j] = math.radians(3.0 * e * tap)
    return o
def Cc(t):  # медленное покачивание без остановки (как фоновые петли)
    o = np.zeros(NJ)
    for j, s in enumerate(JS):
        e = ss((s - 0.15) / 0.85)
        o[j] = math.radians(1.0 * e * (0.5 - 0.5 * math.cos(2 * math.pi * (t - 0.8 * s) / 4.0)))
    return o
fps = 24
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 34)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '660x420', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', 'variants.mp4'], stdin=subprocess.PIPE)
for name, fn, sec in (('A  обмахивание', A, 6), ('B  постукивание', B, 5), ('C  покачивание', Cc, 8)):
    for rep in range(2):
        for f in range(fps * sec):
            F = frame(fn(f / fps - 0.3))
            img = (F * WN + (O + F - rest) * (1 - WN))
            im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((660, 420), Image.LANCZOS)
            d = ImageDraw.Draw(im); d.text((14, 10), name, font=font, fill=(255, 235, 180), stroke_width=3, stroke_fill=(0, 0, 0))
            p.stdin.write(np.asarray(im).tobytes())
p.stdin.close(); p.wait()
for fn in (A, B, Cc): print([round(math.degrees(fn(t).sum()), 1) for t in np.arange(0, 6, 0.5)])
