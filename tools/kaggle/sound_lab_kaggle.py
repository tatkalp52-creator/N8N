# Звуковая лаборатория (Kaggle, одна ячейка).
# Берёт ОДИН трек, чистит его разными способами и кладёт в Output короткие
# отрывки из самого «густого» (громкого, плотного) места трека — там, где
# шум остаётся. Имена отрывков — буквы A, B, C…; что есть что — в файле
# ответы.txt (открыть ПОСЛЕ прослушивания, чтобы слушать вслепую).
# Запускать в ОТДЕЛЬНОМ блокноте (не suno-clean!).

# ===== НАСТРОЙКИ =====
TRACK_LINK = ""     # ссылка на ОДИН трек (.wav/.mp3) на Google Диске, доступ «всем, у кого есть ссылка»
CLIP_SECONDS = 40   # длина отрывка для прослушивания
# =====================

import subprocess, sys, os, glob, shutil, random, json
def sh(cmd):
    print('>', cmd); subprocess.run(cmd, shell=True, check=True)

sh(f'{sys.executable} -m pip -q install "audio-separator[gpu]" gdown')
import torch, gdown
assert torch.cuda.is_available(), 'Нет видеокарты: Settings → Accelerator → GPU T4 x2'

OUT = '/kaggle/working'
for f in glob.glob(f'{OUT}/*'):
    os.remove(f) if os.path.isfile(f) else shutil.rmtree(f, ignore_errors=True)
shutil.rmtree('/tmp/lab', ignore_errors=True); os.makedirs('/tmp/lab/src')
assert TRACK_LINK.strip(), 'Вставь ссылку на трек в TRACK_LINK'
src = gdown.download(TRACK_LINK.strip(), output='/tmp/lab/src/', fuzzy=True, quiet=False)
sh(f'ffmpeg -loglevel error -y -i "{src}" -ar 44100 -ac 2 /tmp/lab/orig.wav')

# Самое плотное место трека: окно с наибольшей средней громкостью
import numpy as np, soundfile as sf
audio, sr = sf.read('/tmp/lab/orig.wav')
mono = np.abs(audio).mean(axis=1) if audio.ndim > 1 else np.abs(audio)
win = CLIP_SECONDS * sr
if len(mono) > win:
    csum = np.concatenate([[0], np.cumsum(mono ** 2)])
    step = sr
    starts = range(0, len(mono) - win, step)
    start = max(starts, key=lambda s: csum[s + win] - csum[s]) / sr
else:
    start = 0
print(f'Отрывок: с {start:.0f} с, {CLIP_SECONDS} с')

from audio_separator.separator import Separator
def clean(inp, model, tag, arch_overlap=4):
    out_dir = f'/tmp/lab/{tag}'; os.makedirs(out_dir, exist_ok=True)
    sep = Separator(output_dir=out_dir, output_format='WAV', model_file_dir='/tmp/models',
                    mdxc_params={'segment_size': 256, 'overlap': arch_overlap, 'batch_size': 1})
    sep.load_model(model_filename=model)
    outs = [os.path.join(out_dir, os.path.basename(o)) for o in sep.separate(inp)]
    # «чистая» часть: (dry) у denoise-моделей, (No Noise) у UVR-DeNoise
    keep = [o for o in outs if any(k in o for k in ('(dry)', '(Dry)', '(No Noise)', '(No noise)', '(Instrumental)'))]
    if not keep:  # на всякий случай — любой выход, кроме самого шума
        keep = [o for o in outs if not any(k in o.lower() for k in ('(noise)', 'bleed)', '(other)'))]
    print(tag, '→', [os.path.basename(o) for o in outs], '| беру:', os.path.basename((keep or outs)[0]))
    return (keep or outs)[0]

AGGR = 'denoise_mel_band_roformer_aufr33_aggr_sdr_27.9768.ckpt'
variants = {}
variants['исходник (без чистки)'] = '/tmp/lab/orig.wav'
a = clean('/tmp/lab/orig.wav', AGGR, 'aggr')
variants['aufr33 aggressive (как сейчас)'] = a
variants['aufr33 aggressive ×2 (два прохода)'] = clean(a, AGGR, 'aggr2')
variants['aufr33 normal'] = clean('/tmp/lab/orig.wav', 'denoise_mel_band_roformer_aufr33_sdr_27.9959.ckpt', 'normal')
for model, name in [('mel_band_roformer_denoise_debleed_gabox.ckpt', 'gabox denoise-debleed'),
                    ('UVR-DeNoise.pth', 'UVR-DeNoise')]:
    try:
        variants[name] = clean('/tmp/lab/orig.wav', model, name.split()[0])
    except Exception as e:
        print(f'⚠️ {name} не получилось: {e}')

# Отрывки под буквами, в случайном порядке — слушать вслепую
names = list(variants); random.shuffle(names)
answers = []
for letter, name in zip('ABCDEFGH', names):
    sh(f'ffmpeg -loglevel error -y -ss {start} -t {CLIP_SECONDS} -i "{variants[name]}" '
       f'-af "afade=t=in:d=0.5,afade=t=out:st={CLIP_SECONDS - 1}:d=1" -c:a libmp3lame -q:a 0 "{OUT}/{letter}.mp3"')
    answers.append(f'{letter} — {name}')
open(f'{OUT}/ответы.txt', 'w').write('\n'.join(answers) + '\n')
print('ГОТОВО: в Output отрывки A…', letter, '.mp3 и ответы.txt (открыть после прослушивания)')
