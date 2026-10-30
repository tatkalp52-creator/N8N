# Минута ролика по строке 37: петля эффектов (гирлянда) + все листья по-настоящему (лежат и тают как в ролике) + хвост.
import sys, os, importlib.util
REPO = '/home/user/N8N'
spec = importlib.util.spec_from_file_location('app', REPO + '/assembler/app.py'); app = importlib.util.module_from_spec(spec); spec.loader.exec_module(app)
app.LEAF_LIB_DIR = REPO + '/assembler/leaves'
img, tail, out = sys.argv[1], sys.argv[2], sys.argv[3]
fx = open('fx.txt').read(); data = {}
work = os.path.abspath('work'); os.makedirs(work, exist_ok=True)
loop = f'{work}/loop.mp4'
app.render_effects_loop(img, app.parse_effects(fx), data, 24, loop)
leaves, edge = app.parse_leaves(fx, data); occ = app.parse_occluders(fx)
TOTAL = 60.0; clips = []
for j, leaf in enumerate(leaves):
    ev, mk = f'{work}/leaf{j}.mp4', f'{work}/leaf{j}_m.mp4'
    app.render_leaf_event(img, leaf, edge, 24, 1.3 + 2.9 * j, ev, mk, occluders=occ)
    clips.append((ev, mk, 2.0 + 7.5 * j)); print('лист', j + 1, app.media_duration(ev))
args = ['-stream_loop', '-1', '-t', f'{TOTAL}', '-i', loop]
g, last = [], '[0:v]'
for i, (ev, mk, t0) in enumerate(clips):
    args += ['-itsoffset', f'{t0:.2f}', '-i', ev, '-itsoffset', f'{t0:.2f}', '-i', mk]
    a, b = 1 + 2 * i, 2 + 2 * i
    g.append(f'[{b}:v]format=gray[m{i}];[{a}:v]format=yuv420p[e{i}];[e{i}][m{i}]alphamerge[l{i}];{last}[l{i}]overlay=0:0:eof_action=pass[o{i}]'); last = f'[o{i}]'
k = len(clips) * 2 + 1
args += ['-stream_loop', '-1', '-t', f'{TOTAL}', '-i', tail]
g.append(f'{last}[{k}:v]overlay=1030:450:shortest=0[t];[t]scale=1920:1080:flags=lanczos[v]')
app.run_ffmpeg(args + ['-filter_complex', ';'.join(g), '-map', '[v]', '-t', f'{TOTAL}', '-r', '24', '-c:v', 'libx264', '-crf', '20', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an', out])
