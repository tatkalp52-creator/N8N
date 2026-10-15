# Петля 12 с для fx_LoopUrl строки 37: гирлянда (эффект сборщика, петля 6 с × 2) + хвост (цикл ровно 12 с),
# всё на картинке в цветах сборщика (colorMute 0.08, colorCool 1.5 — как сделает grade_image). Листья кладёт сборщик поверх.
import os, sys, subprocess, importlib.util, numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); TAIL = os.path.join(HERE, '..', 'tail5')
spec = importlib.util.spec_from_file_location('app', '/home/user/N8N/assembler/app.py'); app = importlib.util.module_from_spec(spec); spec.loader.exec_module(app)
img = os.path.join(HERE, 'cat_g.jpg')
GARLAND = 'гирлянда: 44.3, 16.7; яркость 2; мерцание 5; ореол 12'
g6 = os.path.join(HERE, 'girlyanda6.mp4')
app.render_effects_loop(img, app.parse_effects(GARLAND), {}, 24, g6)
# хвост: тот же скрипт, но на картинках в цветах сборщика и с покоем 6.8 с, чтобы цикл был ровно 12 с
os.environ['TAIL_IMG'] = img; os.environ['TAIL_CLEAN'] = os.path.join(HERE, 'erased_g.jpg')
os.chdir(TAIL); sys.argv = ['x', '/dev/null', 'none']
src = open('tri_vniz.py').read().split("CYCLE =")[0].replace("HOLD, UP, TOPH, DOWN = 5.0, 2.8, 0.4, 1.6", "HOLD, UP, TOPH, DOWN = 6.8, 2.8, 0.4, 1.6")
exec(src)
fps = 24; n = 12 * fps; w_, h_ = x1 - x0, y1 - y0
gf = subprocess.run(['ffmpeg', '-loglevel', 'error', '-stream_loop', '1', '-i', g6, '-frames:v', str(n), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
W_, H_ = Image.open(img).size; G = np.frombuffer(gf, np.uint8).reshape(-1, H_, W_, 3)
assert len(G) == n, len(G)
out = os.path.join(HERE, 'kot37_petlya.mp4')
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W_}x{H_}', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '15', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
for fi in range(n):
    fr = G[fi].copy()
    fr[y0:y1, x0:x1] = np.clip(frame_p(*at(fi / fps)), 0, 255).astype(np.uint8)
    p.stdin.write(fr.tobytes())
p.stdin.close(); p.wait(); print('готово', out)
