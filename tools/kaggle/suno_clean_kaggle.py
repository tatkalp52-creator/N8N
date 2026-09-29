# Чистка треков Suno (Kaggle, одна ячейка, блокнот suno-clean).
# Результат — «… (clean).zip» во вкладке Output; сервер забирает его по ссылке на блокнот.

# ===== НАСТРОЙКИ =====
TRACKS_LINK = ""     # ссылка на zip с треками на Google Диске (доступ «всем, у кого есть ссылка»)
MODE = "aggressive"  # способ чистки — то, что победило в звуковой лаборатории:
#   "aggressive"  — aufr33 aggressive (как было)
#   "aggressive2" — aufr33 aggressive, два прохода
#   "normal"      — aufr33 normal (бережнее)
#   "gabox"       — gabox denoise-debleed
#   "uvr"         — UVR-DeNoise
#   "layers"      — по слоям: разложить на инструменты, почистить каждый, вернуть громкость
#   "knobs"       — шум отдельно → удалить → ручки по инструментам (EQ до/после, только подъём ≤ +6 дБ)
SPEED = "quality"    # "quality" — аккуратнее; "fast" — вдвое быстрее
# =====================

import subprocess, sys, os, glob, shutil, zipfile, re
subprocess.run([sys.executable, '-m', 'pip', '-q', 'install', 'audio-separator[gpu]', 'gdown'], check=True)
import torch, gdown, numpy as np, soundfile as sf
from scipy.signal import stft, istft
assert torch.cuda.is_available(), 'Нет видеокарты: Settings → Accelerator → GPU T4 x2'
print('Видеокарта:', torch.cuda.get_device_name(0), '| способ:', MODE)

assert TRACKS_LINK.strip(), 'Вставь ссылку на архив в TRACKS_LINK'
shutil.rmtree('/tmp/src', ignore_errors=True); os.makedirs('/tmp/src')
src = gdown.download(TRACKS_LINK.strip(), output='/tmp/src/', fuzzy=True, quiet=False)
assert src and src.lower().endswith('.zip'), f'Скачалось не то (нужен .zip): {src}. Проверь доступ по ссылке.'

work = '/tmp/work'; shutil.rmtree(work, ignore_errors=True); os.makedirs(f'{work}/in')
with zipfile.ZipFile(src) as z:
    order = [n for n in z.namelist() if n.lower().endswith(('.wav', '.mp3', '.flac')) and not n.startswith('__MACOSX')]
    z.extractall(f'{work}/in')
print('Треков:', len(order))

from audio_separator.separator import Separator
OVERLAP = 2 if SPEED == 'fast' else 4
MODELS = {'aggressive': 'denoise_mel_band_roformer_aufr33_aggr_sdr_27.9768.ckpt',
          'normal': 'denoise_mel_band_roformer_aufr33_sdr_27.9959.ckpt',
          'gabox': 'mel_band_roformer_denoise_debleed_gabox.ckpt',
          'uvr': 'UVR-DeNoise.pth'}
_seps = {}
def run_model(model, path, out_dir):
    # модель грузится один раз и пишет в свою постоянную папку; результаты сразу переносим в out_dir
    sep_dir = '/tmp/sepout/' + re.sub(r'\W', '_', model)
    if model not in _seps:
        os.makedirs(sep_dir, exist_ok=True)
        s = Separator(output_dir=sep_dir, output_format='WAV', model_file_dir='/tmp/models',
                      mdxc_params={'segment_size': 256, 'overlap': OVERLAP, 'batch_size': 1})
        s.load_model(model_filename=model)
        _seps[model] = s
    os.makedirs(out_dir, exist_ok=True)
    moved = []
    for o in _seps[model].separate(path):
        dst = os.path.join(out_dir, os.path.basename(o))
        shutil.move(os.path.join(sep_dir, os.path.basename(o)), dst)
        moved.append(dst)
    return moved

def denoise(path, model, out_dir):
    outs = run_model(model, path, out_dir)
    # смотрим на ПОСЛЕДНЮЮ метку в скобках: в имени могут остаться метки прошлых проходов, напр. «(dry)»
    lab = lambda o: (re.findall(r'\(([^)]+)\)', os.path.basename(o)) or [''])[-1].lower()
    keep = [o for o in outs if lab(o) in ('dry', 'no noise', 'instrumental')]
    if not keep:
        keep = [o for o in outs if lab(o) not in ('noise', 'other', 'bleed')]
    for o in outs:  # шумовую дорожку выбрасываем
        if o not in keep[:1]:
            try: os.remove(o)
            except FileNotFoundError: pass
    return (keep or outs)[0]

SPLIT_MODELS = ('BS-Roformer-SW.ckpt', 'htdemucs_6s.yaml')
def split(path, out_dir):
    last = None
    for m in SPLIT_MODELS:
        try:
            res = {}
            for o in run_model(m, path, out_dir):
                labels = re.findall(r'\(([^)]+)\)', os.path.basename(o))
                res[labels[-1].lower() if labels else os.path.basename(o)] = o
            return res
        except Exception as e:
            last = e; print(f'⚠️ разложение {m} не вышло: {e}')
    raise last

def envelope(x, nfft=4096):
    mono = x.mean(axis=1) if x.ndim > 1 else x
    _, _, Z = stft(mono, fs=44100, nperseg=nfft)
    return np.mean(np.abs(Z), axis=1) + 1e-9

def smooth(v, width=9):
    return np.convolve(np.pad(v, width // 2, mode='edge'), np.ones(width) / width, mode='valid')

def apply_eq(x, gain, nfft=4096):
    out = np.zeros_like(x)
    for ch in range(x.shape[1] if x.ndim > 1 else 1):
        sig = x[:, ch] if x.ndim > 1 else x
        _, _, Z = stft(sig, fs=44100, nperseg=nfft)
        _, y = istft(Z * gain[:, None], fs=44100, nperseg=nfft)
        y = y[:len(sig)]
        if x.ndim > 1: out[:len(y), ch] = y
        else: out[:len(y)] = y
    return out

def mix(parts, ref_path, out_path):
    n = min(len(p) for p in parts)
    total = sum(p[:n] for p in parts)
    ref_peak = np.max(np.abs(sf.read(ref_path)[0]))
    total = total * min(1.0, ref_peak / (np.max(np.abs(total)) + 1e-9))
    sf.write(out_path, total, 44100)
    return out_path

def to44k(path, out_path):
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', path, '-ar', '44100', '-ac', '2', out_path], check=True)
    return out_path

def clean_track(path, i):
    d = f'{work}/t{i}'; os.makedirs(d, exist_ok=True)
    wav = to44k(path, f'{d}/orig.wav')
    if MODE in MODELS:
        return denoise(wav, MODELS[MODE], f'{d}/dn')
    if MODE == 'aggressive2':
        once = denoise(wav, MODELS['aggressive'], f'{d}/dn1')
        return denoise(once, MODELS['aggressive'], f'{d}/dn2')
    if MODE == 'layers':
        parts = []
        for label, st in split(wav, f'{d}/stems').items():
            x, _ = sf.read(st)
            r0 = np.sqrt(np.mean(x ** 2)) + 1e-9
            if r0 < 1e-4:
                continue
            y, _ = sf.read(denoise(st, MODELS['aggressive'], f'{d}/dn_{label}'))
            y = y[:len(x)]
            y = y * min(r0 / (np.sqrt(np.mean(y ** 2)) + 1e-9), 10 ** (3 / 20))
            parts.append(y)
        return mix(parts, wav, f'{d}/clean.wav')
    if MODE == 'knobs':
        dry = denoise(wav, MODELS['aggressive'], f'{d}/dn')
        before, after = split(wav, f'{d}/before'), split(dry, f'{d}/after')
        parts = []
        for label, p in after.items():
            y, _ = sf.read(p)
            if np.sqrt(np.mean(y ** 2)) < 1e-4:
                continue
            if label in before:
                x, _ = sf.read(before[label])
                n = min(len(x), len(y)); x, y = x[:n], y[:n]
                g = np.clip(smooth(20 * np.log10(envelope(x) / envelope(y))), 0, 6)
                y = apply_eq(y, 10 ** (g / 20))
            parts.append(y)
        return mix(parts, wav, f'{d}/clean.wav')
    raise ValueError(f'Неизвестный MODE: {MODE}')

clean = {}
for i, name in enumerate(order, 1):
    clean[name] = clean_track(os.path.join(f'{work}/in', name), i)
    print(f'{i}/{len(order)} готов: {os.path.basename(name)}')

base = os.path.splitext(os.path.basename(src))[0]
dst = f'/kaggle/working/{base} (clean).zip'
for old in glob.glob('/kaggle/working/*.zip'):
    os.remove(old)
with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as z:
    for name in order:  # те же имена и тот же порядок, что в исходном архиве
        z.write(clean[name], arcname=os.path.basename(name).rsplit('.', 1)[0] + '.wav')
shutil.rmtree(work, ignore_errors=True)
print('ГОТОВО:', os.path.basename(dst), round(os.path.getsize(dst) / 1e6), 'МБ — способ', MODE)
