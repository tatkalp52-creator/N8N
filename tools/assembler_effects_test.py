# Локальная проверка эффектов (пар, пузыри, моргание). Запуск из папки с img.jpg и audio.wav (20 с).
import sys, os, re, time, shutil, subprocess
sys.path.insert(0, '/home/user/N8N/assembler')
import app as A
import json as _json
_W = _json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'effects', 'slova.json')))
A.set_vocab({'fxWords': _W}); A.set_frame({'videoWidth': 1920, 'videoHeight': 1072}); A.EFFECTS_LOOP_SECONDS = 6.0   # (28.10) слова и кадр — из таблицы
if not shutil.which('ffprobe'):  # локально может не быть ffprobe — длительность читаем из ffmpeg
    def _dur(p):
        e = subprocess.run(['ffmpeg', '-i', p], capture_output=True, text=True).stderr
        h, m, s = re.search(r'Duration: (\d+):(\d+):([\d.]+)', e).groups()
        return int(h) * 3600 + int(m) * 60 + float(s)
    A.media_duration = _dur
spec = 'пар: 68.4, 58.4\nпузыри: 86.9, 73.6, 67.0\nморгание: 74.0, 63.0\nчто-то непонятное'
assert [k for k, _ in A.parse_effects(spec)] == ['steam', 'bubbles', 'blink']
assert A.parse_effects('') == [] and A.parse_effects('steam: 10,20') == [('steam', [10.0, 20.0])]
base = f"scale={A.VIDEO_WIDTH}:{A.VIDEO_HEIGHT}," + ",".join(A.old_film_filters(2))
audio_chain = "afade=t=in:st=0:d=1.5:curve=tri"
wd = 'w_fx'; shutil.rmtree(wd, ignore_errors=True); os.makedirs(wd)
t0 = time.time()
A.build_video_from_pieces({'fx_Effects': spec, 'videoFps': 24, 'eventGapMinSeconds': 60, 'eventGapMaxSeconds': 240}, wd, 'img.jpg', 'audio.wav', 20.0, base, [], [], '8', 9.0,
                          audio_chain, 'out_fx.mp4', 'P1')
print('сек сборки', round(time.time() - t0, 1))
