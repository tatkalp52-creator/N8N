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

import subprocess, sys, os, glob, shutil, random, json, re
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
# Дальше работаем только с этим куском (+5 с запаса с каждой стороны) — так в разы быстрее
PAD = 5
cut_from = max(0.0, start - PAD)
sh(f'ffmpeg -loglevel error -y -ss {cut_from} -t {CLIP_SECONDS + 2 * PAD} -i /tmp/lab/orig.wav /tmp/lab/piece.wav')
shutil.move('/tmp/lab/piece.wav', '/tmp/lab/orig.wav')
start = start - cut_from

from audio_separator.separator import Separator
def clean(inp, model, tag, arch_overlap=4):
    out_dir = f'/tmp/lab/{tag}'; os.makedirs(out_dir, exist_ok=True)
    sep = Separator(output_dir=out_dir, output_format='WAV', model_file_dir='/tmp/models',
                    mdxc_params={'segment_size': 256, 'overlap': arch_overlap, 'batch_size': 1})
    sep.load_model(model_filename=model)
    outs = [os.path.join(out_dir, os.path.basename(o)) for o in sep.separate(inp)]
    # «чистая» часть: (dry) у denoise-моделей, (No Noise) у UVR-DeNoise
    # смотрим на ПОСЛЕДНЮЮ метку в скобках: в имени могут остаться метки прошлых проходов, напр. «(dry)»
    lab = lambda o: (re.findall(r'\(([^)]+)\)', os.path.basename(o)) or [''])[-1].lower()
    keep = [o for o in outs if lab(o) in ('dry', 'no noise', 'instrumental')]
    if not keep:  # на всякий случай — любой выход, кроме самого шума
        keep = [o for o in outs if lab(o) not in ('noise', 'other', 'bleed')]
    print(tag, '→', [os.path.basename(o) for o in outs], '| беру:', os.path.basename((keep or outs)[0]))
    NOISE[tag] = [o for o in outs if o not in keep]  # отдельная дорожка шума — пригодится для «возврата гармоник»
    return (keep or outs)[0]
NOISE = {}

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

# ПО СЛОЯМ: разложить на инструменты → почистить каждый отдельно →
# вернуть каждому его прежнюю громкость (то, что чистка «съела» вместе с шумом) → сложить обратно.
def layered(model_sep):
    d = f'/tmp/lab/stems_{model_sep.split(".")[0]}'; os.makedirs(d, exist_ok=True)
    sep = Separator(output_dir=d, output_format='WAV', model_file_dir='/tmp/models')
    sep.load_model(model_filename=model_sep)
    stems = [os.path.join(d, os.path.basename(o)) for o in sep.separate('/tmp/lab/orig.wav')]
    print('Слои:', [os.path.basename(s) for s in stems])
    total = None
    for i, st in enumerate(stems):
        x, _ = sf.read(st)
        rms_before = np.sqrt(np.mean(x ** 2)) + 1e-9
        if rms_before < 1e-4:          # пустой слой (например, вокала нет) — пропускаем
            continue
        y, _ = sf.read(clean(st, AGGR, f'layer{i}'))
        n = min(len(x), len(y)); y = y[:n]
        gain = min(rms_before / (np.sqrt(np.mean(y ** 2)) + 1e-9), 10 ** (3 / 20))  # подтянуть, но не больше +3 дБ
        y = y * gain
        total = y if total is None else total[:n] + y[:len(total[:n])]
    peak = np.max(np.abs(total)) + 1e-9
    orig_peak = np.max(np.abs(sf.read('/tmp/lab/orig.wav')[0]))
    total = total * min(1.0, orig_peak / peak)
    out = f'/tmp/lab/layered_{model_sep.split(".")[0]}.wav'
    sf.write(out, total, sr)
    return out

for model_sep, name in [('BS-Roformer-SW.ckpt', 'по слоям (BS-Roformer 6 слоёв)'),
                        ('htdemucs_6s.yaml', 'по слоям (Demucs 6 слоёв)')]:
    try:
        variants[name] = layered(model_sep)
        break  # хватит одного способа разложения
    except Exception as e:
        print(f'⚠️ {name} не получилось: {e}')

# ШУМ ОТДЕЛЬНОЙ ДОРОЖКОЙ → УДАЛИТЬ → РУЧКИ ПО ИНСТРУМЕНТАМ (схема автора):
# 1) чистка выделяет шум в свою дорожку — её просто выбрасываем (остаётся чистая «a»);
# 2) исходник и чистый трек раскладываются на инструменты одной и той же моделью;
# 3) для каждого инструмента сравниваем его тембр ДО и ПОСЛЕ чистки (средний спектр по полосам)
#    и крутим «эквалайзер» на всю длину стема, возвращая то, что ушло вместе с шумом:
#    только поднимаем, плавно, не больше +6 дБ — это тембр, а не шорох, поэтому песок не возвращается;
# 4) складываем обратно.
from scipy.signal import stft, istft
def split(path, model_sep, tag):
    d = f'/tmp/lab/split_{tag}'; os.makedirs(d, exist_ok=True)
    sep = Separator(output_dir=d, output_format='WAV', model_file_dir='/tmp/models')
    sep.load_model(model_filename=model_sep)
    res = {}
    for o in sep.separate(path):
        labels = re.findall(r'\(([^)]+)\)', os.path.basename(o))
        res[labels[-1].lower() if labels else os.path.basename(o)] = os.path.join(d, os.path.basename(o))
    return res

def band_envelope(x, nfft=4096):
    mono = x.mean(axis=1) if x.ndim > 1 else x
    _, _, Z = stft(mono, fs=sr, nperseg=nfft)
    return np.mean(np.abs(Z), axis=1) + 1e-9

def smooth(v, width=9):
    k = np.ones(width) / width
    return np.convolve(np.pad(v, width // 2, mode='edge'), k, mode='valid')

def apply_eq(x, gain_lin, nfft=4096):
    out = np.zeros_like(x)
    for ch in range(x.shape[1] if x.ndim > 1 else 1):
        sig = x[:, ch] if x.ndim > 1 else x
        _, _, Z = stft(sig, fs=sr, nperseg=nfft)
        _, y = istft(Z * gain_lin[:, None], fs=sr, nperseg=nfft)
        y = y[:len(sig)]
        if x.ndim > 1: out[:len(y), ch] = y
        else: out[:len(y)] = y
    return out

import re
for model_sep in ('BS-Roformer-SW.ckpt', 'htdemucs_6s.yaml'):
    try:
        before = split('/tmp/lab/orig.wav', model_sep, 'before')
        after = split(a, model_sep, 'after')
        total = None
        for label, p_after in after.items():
            y, _ = sf.read(p_after)
            if np.sqrt(np.mean(y ** 2)) < 1e-4:
                continue
            if label in before:
                x, _ = sf.read(before[label])
                n = min(len(x), len(y)); x, y = x[:n], y[:n]
                g_db = 20 * np.log10(band_envelope(x) / band_envelope(y))
                g_db = np.clip(smooth(g_db), 0, 6)          # только вернуть, плавно, максимум +6 дБ
                print(f'{label}: подъём до {g_db.max():.1f} дБ')
                y = apply_eq(y, 10 ** (g_db / 20))
            total = y if total is None else total[:min(len(total), len(y))] + y[:min(len(total), len(y))]
        peak = np.max(np.abs(total)) + 1e-9
        orig_peak = np.max(np.abs(sf.read('/tmp/lab/orig.wav')[0]))
        out = '/tmp/lab/noise_out_knobs.wav'
        sf.write(out, total * min(1.0, orig_peak / peak), sr)
        variants['шум отдельно → удалить → ручки по инструментам'] = out
        break
    except Exception as e:
        print(f'⚠️ «ручки по инструментам» с {model_sep} не получились: {e}')

# Отрывки под буквами, в случайном порядке — слушать вслепую
names = list(variants); random.shuffle(names)
answers = []
for letter, name in zip('ABCDEFGHIJKL', names):
    sh(f'ffmpeg -loglevel error -y -ss {start} -t {CLIP_SECONDS} -i "{variants[name]}" '
       f'-af "afade=t=in:d=0.5,afade=t=out:st={CLIP_SECONDS - 1}:d=1" -c:a libmp3lame -q:a 0 "{OUT}/{letter}.mp3"')
    answers.append(f'{letter} — {name}')
open(f'{OUT}/ответы.txt', 'w').write('\n'.join(answers) + '\n')

# ЦИФРЫ к ушам — по тем же буквам (вслепую). Смысл колонок:
#   громкость — средний уровень, дБ;
#   дно — уровень в самых тихих местах (чем ниже, тем меньше шума в паузах), дБ;
#   верха — энергия 8–16 кГц относительно всего звука (где живут и воздух, и песок), дБ;
#   шершавость — насколько верха похожи на шум, а не на звук инструмента (0 — чистый тон, 1 — чистый шум);
#   яркость — «центр тяжести» спектра, Гц (упала сильно — звук стал глухим).
def metrics(path):
    x, _ = sf.read(path)
    x = x[int(start * sr): int((start + CLIP_SECONDS) * sr)]
    m = x.mean(axis=1) if x.ndim > 1 else x
    frames = m[: len(m) // 2048 * 2048].reshape(-1, 2048)
    rms = np.sqrt((frames ** 2).mean(axis=1)) + 1e-9
    f, _, Z = stft(m, fs=sr, nperseg=4096)
    P = np.abs(Z) ** 2 + 1e-12
    hf = (f >= 8000) & (f <= 16000)
    flat = np.exp(np.mean(np.log(P[hf]), axis=0)) / np.mean(P[hf], axis=0)
    centroid = np.sum(f[:, None] * P, axis=0) / np.sum(P, axis=0)
    return (20 * np.log10(np.sqrt(np.mean(m ** 2)) + 1e-9),
            20 * np.log10(np.percentile(rms, 10)),
            10 * np.log10(P[hf].sum() / P.sum()),
            float(np.median(flat)),
            float(np.median(centroid)))
rows = ['буква | громкость дБ | дно дБ | верха дБ | шершавость | яркость Гц']
for letter, name in zip('ABCDEFGHIJKL', names):
    try:
        v = metrics(variants[name])
        rows.append(f'{letter} | {v[0]:6.1f} | {v[1]:6.1f} | {v[2]:6.1f} | {v[3]:.2f} | {v[4]:6.0f}')
    except Exception as e:
        rows.append(f'{letter} | ошибка: {e}')
open(f'{OUT}/цифры.txt', 'w').write('\n'.join(rows) + '\n')
print('\n'.join(rows))

# ВЕРДИКТ ПРИБОРОВ (по буквам, вслепую). Считаем, ЧТО ИМЕННО вычтено из исходника, по полосам:
#   «убрано верхов» 8–16 кГц — там живёт песок: чем больше (ближе к 0 дБ), тем сильнее чистка;
#   «задето середины» 1–5 кГц — там сами инструменты: чем больше, тем выше риск повредить музыку;
#   «баланс» = убрано верхов минус задето середины: чем больше, тем прицельнее чистка.
#   Все числа — уровень вычтенного относительно исходника, дБ (−10 — заметно, −30 — почти ничего).
from scipy.signal import welch
def removed_db(path, lo, hi):
    o, _ = sf.read(variants['исходник (без чистки)']); x, _ = sf.read(path)
    o = o.mean(axis=1) if o.ndim > 1 else o; x = x.mean(axis=1) if x.ndim > 1 else x
    n = min(len(o), len(x)); a, b = int(start * sr), int((start + CLIP_SECONDS) * sr)
    o, x = o[:n][a:b], x[:n][a:b]
    f, Po = welch(o, sr, nperseg=8192); _, Pd = welch(o - x, sr, nperseg=8192)
    m = (f >= lo) & (f < hi)
    return 10 * np.log10(Pd[m].sum() / (Po[m].sum() + 1e-20) + 1e-20)
try:
    ref_name = 'исходник (без чистки)'
    scored = []
    for letter, name in zip('ABCDEFGHIJKL', names):
        if name == ref_name:
            continue
        hi_ = removed_db(variants[name], 8000, 16000)
        mid = removed_db(variants[name], 1000, 5000)
        notes = []
        if hi_ < -25: notes.append('почти ничего не убрано')
        if mid > -15: notes.append('задета музыка — слушать внимательно')
        scored.append((hi_ - mid, letter, hi_, mid, notes))
    scored.sort(reverse=True)
    lines = ['Место | буква | убрано верхов, дБ | задето середины, дБ | баланс | замечания']
    for k, (bal, letter, hi_, mid, notes) in enumerate(scored, 1):
        lines.append(f'{k} | {letter} | {hi_:6.1f} | {mid:6.1f} | {bal:5.1f} | {", ".join(notes) or "—"}')
    open(f'{OUT}/вердикт приборов.txt', 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
except Exception as e:
    print(f'⚠️ вердикт не посчитался: {e}')

# СПЕКТРОГРАММЫ по буквам — «картинка звука»: песок виден как серая сыпь в верхней части
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for letter, name in zip('ABCDEFGHIJKL', names):
        x, _ = sf.read(variants[name])
        x = x[int(start * sr): int((start + CLIP_SECONDS) * sr)]
        m = x.mean(axis=1) if x.ndim > 1 else x
        plt.figure(figsize=(12, 4))
        plt.specgram(m, NFFT=2048, Fs=sr, noverlap=1024, cmap='magma', vmin=-120, vmax=-20)
        plt.ylim(0, 18000); plt.title(f'{letter}'); plt.ylabel('Гц'); plt.xlabel('с')
        plt.tight_layout(); plt.savefig(f'{OUT}/спектр_{letter}.png', dpi=80); plt.close()
except Exception as e:
    print(f'⚠️ спектрограммы не нарисовались: {e}')
print('ГОТОВО: в Output отрывки A…', letter, '.mp3 и ответы.txt (открыть после прослушивания)')
