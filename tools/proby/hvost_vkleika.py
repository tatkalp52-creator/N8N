# Видео-образец (Kling) вклеивается в наш кадр только там, где двигается хвост; в конце — плавный возврат в исходный кадр (цикл).
import sys, numpy as np, subprocess, glob
from PIL import Image, ImageFilter
orig_path, video_frames, out = sys.argv[1], sys.argv[2], sys.argv[3]
CROP = (880, 385, 544)            # откуда в оригинале (1536×864) вырезан кадр для Kling: x, y, ширина (16:9)
RET = float(sys.argv[4]) if len(sys.argv) > 4 else 0.8   # секунд на возврат
FPS = 24; OW, OH = 1920, 1080; K = OW / 1536
orig = Image.open(orig_path).convert('RGB').resize((OW, OH), Image.LANCZOS)
cx, cy, cw = CROP; ch = cw * 9 / 16
bx, by, bw, bh = round(cx * K), round(cy * K), round(cw * K), round(ch * K)
files = sorted(glob.glob(video_frames))
fr = [np.asarray(Image.open(f).convert('RGB').resize((bw, bh), Image.LANCZOS)).astype(np.float32) for f in files]
base = np.asarray(orig).astype(np.float32)[by:by + bh, bx:bx + bw]
# где двигается хвост: всё, что заметно меняется относительно первого кадра, + запас, мягкий край
def blur(a, r): return np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))).astype(np.float32)
f0 = blur(fr[0].mean(-1), 2)
acc = np.zeros(f0.shape, bool)
for f in fr: acc |= np.abs(blur(f.mean(-1), 2) - f0) > 14
m = Image.fromarray(acc.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(9))   # убрать крошки
m = m.filter(ImageFilter.MaxFilter(25)).filter(ImageFilter.GaussianBlur(10))
MASK = (np.asarray(m).astype(np.float32) / 255)[..., None]
Image.fromarray((MASK[..., 0] * 255).astype(np.uint8)).save(out.rsplit('.', 1)[0] + '_maska.png')
def ss(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
nret = int(round(RET * FPS)); nin = 6
frames = []
for i, f in enumerate(fr):
    w = ss(i / nin)                                    # вход: с нашего кадра в кадр образца
    frames.append(base * (1 - w * MASK) + f * (w * MASK))
last = fr[-1]
for j in range(1, nret + 1):                           # возврат: с последнего кадра образца в наш исходный кадр
    w = 1 - ss(j / nret)
    frames.append(base * (1 - w * MASK) + last * (w * MASK))
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}', '-r', str(FPS), '-i', '-',
                      '-c:v', 'libx264', '-crf', '17', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
full = np.asarray(orig).copy()
for rep in range(2):
    for f in frames:
        img = full.copy(); img[by:by + bh, bx:bx + bw] = np.clip(f, 0, 255).astype(np.uint8)
        p.stdin.write(img.tobytes())
p.stdin.close(); p.wait()
print('кадров', len(frames), 'секунд', len(frames) / FPS)
