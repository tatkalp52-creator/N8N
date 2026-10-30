# Проба Apollo (Kaggle, одна ячейка; запускать в блокноте звуковой лаборатории, НЕ в suno-clean).
# Apollo — нейросеть-РЕСТАВРАТОР (не чистильщик): дорисовывает звук, испорченный сжатием/кодеком.
# Берёт ОДИН трек, делает отрывок из самого плотного места и 4 варианта вслепую: A, B, C, D.
# Что есть что — в ответы.txt (открыть ПОСЛЕ прослушивания). Время работы — в время.txt.

# ===== НАСТРОЙКИ =====
TRACK_LINK = ""     # ссылка на Google Диске (доступ «всем, у кого есть ссылка»): ОДИН трек ИЛИ .zip выпуска
TRACK_NUMBER = 12   # если .zip — какой трек взять (12 — тот же, что в прошлых пробах)
CLIP_SECONDS = 40
CLIP_FROM = "auto"  # "auto" — самое плотное место; "end" — конец; или секунда начала, напр. "95"
# =====================

import subprocess, sys, os, glob, shutil, random, re, time
def sh(cmd):
    print('>', cmd); subprocess.run(cmd, shell=True, check=True)

sh(f'{sys.executable} -m pip -q install "audio-separator[gpu]" gdown omegaconf huggingface_hub')
if not os.path.exists('/tmp/Apollo'):
    sh('git clone -q --depth 1 https://github.com/JusperLee/Apollo.git /tmp/Apollo')
import torch, gdown, numpy as np, soundfile as sf
assert torch.cuda.is_available(), 'Нет видеокарты: Settings → Accelerator → GPU T4 x2'

OUT = '/kaggle/working'
for f in glob.glob(f'{OUT}/*'):
    os.remove(f) if os.path.isfile(f) else shutil.rmtree(f, ignore_errors=True)
shutil.rmtree('/tmp/lab', ignore_errors=True); os.makedirs('/tmp/lab/src')
assert TRACK_LINK.strip(), 'Вставь ссылку в TRACK_LINK'
src = gdown.download(TRACK_LINK.strip(), output='/tmp/lab/src/', fuzzy=True, quiet=False)
if src.lower().endswith('.zip'):
    import zipfile
    with zipfile.ZipFile(src) as z:
        tracks = [n for n in z.namelist() if n.lower().endswith(('.wav', '.mp3', '.flac')) and not n.startswith('__MACOSX')]
        assert 1 <= TRACK_NUMBER <= len(tracks), f'В архиве {len(tracks)} треков, а TRACK_NUMBER = {TRACK_NUMBER}'
        pick = tracks[TRACK_NUMBER - 1]
        z.extract(pick, '/tmp/lab/src/')
    src = os.path.join('/tmp/lab/src', pick)
    print('Трек из архива:', pick)
sh(f'ffmpeg -loglevel error -y -i "{src}" -ar 44100 -ac 2 /tmp/lab/full.wav')

# отрывок — как в звуковой лаборатории
audio, sr = sf.read('/tmp/lab/full.wav')
mono = np.abs(audio).mean(axis=1)
win = CLIP_SECONDS * sr
if len(mono) <= win:
    start = 0
elif str(CLIP_FROM).strip().lower() == 'end':
    start = (len(mono) - win) / sr - 1
elif str(CLIP_FROM).strip().lower() not in ('auto', ''):
    start = min(float(CLIP_FROM), (len(mono) - win) / sr)
else:
    csum = np.concatenate([[0], np.cumsum(mono ** 2)])
    start = max(range(0, len(mono) - win, sr), key=lambda s: csum[s + win] - csum[s]) / sr
start = max(0.0, start)
PAD = 5
cut_from = max(0.0, start - PAD)
sh(f'ffmpeg -loglevel error -y -ss {cut_from} -t {CLIP_SECONDS + 2 * PAD} -i /tmp/lab/full.wav /tmp/lab/orig.wav')
start -= cut_from
print(f'Отрывок: {CLIP_SECONDS} с')

times = {}
# чистка aufr33 aggressive, один проход — как в первой (тёплой) версии выпуска
from audio_separator.separator import Separator
t0 = time.time()
sep = Separator(output_dir='/tmp/lab/dn', output_format='WAV', model_file_dir='/tmp/models',
                mdxc_params={'segment_size': 256, 'overlap': 4, 'batch_size': 1})
sep.load_model(model_filename='denoise_mel_band_roformer_aufr33_aggr_sdr_27.9768.ckpt')
outs = [os.path.join('/tmp/lab/dn', os.path.basename(o)) for o in sep.separate('/tmp/lab/orig.wav')]
lab = lambda o: (re.findall(r'\(([^)]+)\)', os.path.basename(o)) or [''])[-1].lower()
aggr = [o for o in outs if lab(o) == 'dry'][0]
times['чистка aggressive'] = time.time() - t0
del sep; torch.cuda.empty_cache()

def apollo(inp, out, tag):
    t0 = time.time()
    sh(f'cd /tmp/Apollo && {sys.executable} inference.py --in_wav="{inp}" --out_wav="{out}" --device=cuda '
       f'--chunk-seconds=6 --overlap-seconds=1 --chunk-pad-seconds=1')
    times[tag] = time.time() - t0
    return out

ap_orig = apollo('/tmp/lab/orig.wav', '/tmp/lab/apollo_orig.wav', 'Apollo по исходнику')
ap_aggr = apollo(aggr, '/tmp/lab/apollo_aggr.wav', 'Apollo после чистки')

variants = {
    'исходник Suno (без обработки)': '/tmp/lab/orig.wav',
    'aggressive 1 проход (как тёплая версия выпуска)': aggr,
    'Apollo по исходнику': ap_orig,
    'Apollo после чистки aggressive': ap_aggr,
}
names = list(variants); random.shuffle(names)
answers = []
for letter, name in zip('ABCD', names):
    sh(f'ffmpeg -loglevel error -y -ss {start} -t {CLIP_SECONDS} -i "{variants[name]}" -ar 44100 -b:a 256k "{OUT}/{letter}.mp3"')
    answers.append(f'{letter} — {name}')
open(f'{OUT}/ответы.txt', 'w').write('\n'.join(answers) + '\n')
clip_len = CLIP_SECONDS + 2 * PAD
with open(f'{OUT}/время.txt', 'w') as f:
    for k, v in times.items():
        f.write(f'{k}: {v:.0f} с на {clip_len} с звука → ~{v / clip_len * 180 / 60:.1f} мин на 3-минутный трек\n')
print(open(f'{OUT}/время.txt').read())
print('ГОТОВО: A–D.mp3, ответы.txt (открыть после прослушивания), время.txt')
