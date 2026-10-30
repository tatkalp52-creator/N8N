# Один цикл хвоста в родном размере куска (для вклейки поверх ролика в x0, y0).
import sys, numpy as np, subprocess
from PIL import Image
OUT_ = sys.argv[1]
sys.argv = ['x', '/dev/null', 'none']
exec(open('duga2.py').read().split("fps = 24; n =")[0])
fps = 24; n = int(round((HOLD + UP + TOP + DOWN + LAG) * fps)); w, h = x1 - x0, y1 - y0
print('crop', x0, y0, w, h, 'frames', n)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '10', '-pix_fmt', 'yuv444p', OUT_], stdin=subprocess.PIPE)
for fi in range(n):
    th_, sc = at(fi / fps); F = frame_p(th_, sc)
    p.stdin.write(np.clip(F, 0, 255).astype(np.uint8).tobytes())
p.stdin.close(); p.wait()
