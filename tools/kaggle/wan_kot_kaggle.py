# Оживление куска картинки петлёй (Wan 2.1 Fun 1.3B) — Kaggle (блокнот wan-loop), видеокарта T4.
# Модели даётся КУСОК картинки вокруг того, что оживляем (не вся картинка) — так он почти в родном
# размере и не мылится. Первый и последний кадр — сама картинка: петля бесшовная.
# Вклейку в наш кадр, паузы и остановки делает потом наш код (tools/proby/hvost_petlya_vpered.py).
#
# Kaggle: Settings → Accelerator → GPU T4 x2, Internet on. Одна ячейка (код лежит на Диске):
#   IMAGE_LINK = "ссылка на картинку на Диске (доступ «всем, у кого есть ссылка»)"
#   !pip -q install gdown && gdown -q --fuzzy "<ссылка на этот файл>" -O /kaggle/working/wan_kot.py
#   exec(open('/kaggle/working/wan_kot.py').read())

# ===== НАСТРОЙКИ (можно переопределить перед exec) =====
IMAGE_LINK = globals().get('IMAGE_LINK', '')   # ссылка на картинку на Google Диске
PROMPT = globals().get('PROMPT', 'a black cat sits still with eyes closed; only its tail moves: the tail sweeps softly along the top of the book, swings out and curls back around its front paws. Static camera, still illustration, pencil drawing, nothing else moves')
SECONDS = globals().get('SECONDS', 4)       # длина петли, секунд (больше — дольше считать)
SEED = globals().get('SEED', 42)
WIDTH = globals().get('WIDTH', 640)         # ширина для модели; 640 влезает в T4
# =====================

import subprocess, sys, os, glob, re, shutil, time
def sh(cmd):
    print('>', cmd); subprocess.run(cmd, shell=True, check=True)
t0 = time.time()
OUT = '/kaggle/working/wan_out'
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)

# 1. Установка
if not os.path.exists('/tmp/VideoX-Fun'):
    sh('git clone --depth 1 https://github.com/aigc-apps/VideoX-Fun /tmp/VideoX-Fun')
sh(f'{sys.executable} -m pip -q install -r /tmp/VideoX-Fun/requirements.txt')
sh(f'{sys.executable} -m pip -q install huggingface_hub')
import torch
assert torch.cuda.is_available(), 'Нет видеокарты: Settings → Accelerator → GPU T4 x2'
print('Видеокарта:', torch.cuda.get_device_name(0))

# 2. Модель (~7 ГБ, первый раз 3–5 минут)
from huggingface_hub import snapshot_download
MODEL = '/tmp/VideoX-Fun/models/Diffusion_Transformer/Wan2.1-Fun-1.3B-InP'
snapshot_download('alibaba-pai/Wan2.1-Fun-1.3B-InP', local_dir=MODEL)

# 3. Картинка
sh(f'{sys.executable} -m pip -q install gdown')
import gdown
from PIL import Image
assert IMAGE_LINK.strip(), 'Вставь ссылку на картинку в IMAGE_LINK (первая строка ячейки)'
src = gdown.download(IMAGE_LINK.strip(), output='/tmp/src_img', fuzzy=True, quiet=False)
orig = Image.open(src).convert('RGB')
W, H = orig.size
mw = WIDTH // 16 * 16; mh = int(H * WIDTH / W) // 16 * 16
orig.resize((mw, mh), Image.LANCZOS).save('/tmp/start.png')
print('Картинка:', (W, H), '→ модель', (mw, mh))

# 4. Оживляем
script = '/tmp/VideoX-Fun/examples/wan2.1_fun/predict_i2v.py'
s = open(script).read()
fps = 16
vals = {
    'GPU_memory_mode': '"sequential_cpu_offload"',  # T4: модель в видеокарту по частям, иначе не хватает памяти
    'model_name': repr(MODEL),
    'sample_size': f'[{mh}, {mw}]',
    'video_length': str(SECONDS * fps + 1),
    'fps': str(fps),
    'weight_dtype': 'torch.float16',               # T4 не умеет bfloat16
    'prompt': repr(PROMPT),
    'negative_prompt': repr('camera movement, zoom, pan, morphing, distortion, blurry, deformed cat, cat moves its head or body, text changes'),
    'validation_image_start': repr('/tmp/start.png'),
    'validation_image_end': repr('/tmp/start.png'),   # тот же кадр в конце — бесшовная петля
    'seed': str(SEED),
    'save_path': repr('/tmp/wan_raw'),
}
missing = []
for k, v in vals.items():
    s2, n = re.subn(rf'^{k}\s*=.*$', f'{k} = {v}', s, count=1, flags=re.M)
    if n: s = s2
    else: missing.append(k)
if missing:
    print('⚠️ не нашла в скрипте:', missing, '— пришли это Клоду')
loop_script = os.path.join(os.path.dirname(script), 'predict_loop.py')
open(loop_script, 'w').write(s)
sh(f'cd /tmp/VideoX-Fun && PYTORCH_ALLOC_CONF=expandable_segments:True PYTHONPATH=/tmp/VideoX-Fun python {loop_script}')
vids = sorted(glob.glob('/tmp/wan_raw/**/*.mp4', recursive=True), key=os.path.getmtime)
assert vids, 'Видео не появилось — пришли Клоду последние строки лога'
shutil.copy(vids[-1], f'{OUT}/wan_kot.mp4')
print(f'ГОТОВО за {int((time.time() - t0) / 60)} мин: Output → wan_out → wan_kot.mp4 — скачай и пришли Клоду')
