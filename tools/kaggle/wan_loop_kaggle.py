# Оживление картинки петлёй (Wan 2.1 Fun 1.3B) — Kaggle, одна ячейка.
# Двигается только найденная область (пар, гирлянда…), всё остальное — исходная картинка.
# Первый и последний кадр — сама картинка, поэтому петля бесшовная.
# Результат (и превью рамки) — во вкладке Output.

# ===== НАСТРОЙКИ =====
IMAGE_LINK = ""        # ссылка на картинку на Google Диске (доступ «всем, у кого есть ссылка»)
PROMPT = "steam gently rising from the cup, static camera, still illustration, nothing else moves"
WHAT = "cup"           # что искать на картинке, по-английски: cup, string lights, candle, lamp…
ABOVE = True           # True — движение НАД предметом (пар, дым); False — сам предмет (гирлянда, свеча)
AREA = "auto"          # "auto" — найти самому; или вручную "слева,сверху,ширина,высота" в процентах
SECONDS = 3            # длина петли, 2–5
SEED = 42
# =====================

import subprocess, sys, os, glob, re, shutil
def sh(cmd):
    print('>', cmd); subprocess.run(cmd, shell=True, check=True)

OUT = '/kaggle/working'
for f in glob.glob(f'{OUT}/*'):
    os.remove(f) if os.path.isfile(f) else shutil.rmtree(f, ignore_errors=True)

# 1. Установка
if not os.path.exists('/tmp/VideoX-Fun'):
    sh('git clone --depth 1 https://github.com/aigc-apps/VideoX-Fun /tmp/VideoX-Fun')
sh(f'{sys.executable} -m pip -q install -r /tmp/VideoX-Fun/requirements.txt')
sh(f'{sys.executable} -m pip -q install gdown huggingface_hub')
import torch
assert torch.cuda.is_available(), 'Нет видеокарты: Settings → Accelerator → GPU T4 x2'
print('Видеокарта:', torch.cuda.get_device_name(0))

# 2. Модель (~7 ГБ)
from huggingface_hub import snapshot_download
MODEL = '/tmp/VideoX-Fun/models/Diffusion_Transformer/Wan2.1-Fun-1.3B-InP'
snapshot_download('alibaba-pai/Wan2.1-Fun-1.3B-InP', local_dir=MODEL)

# 3. Картинка
import gdown
from PIL import Image, ImageDraw, ImageFilter
assert IMAGE_LINK.strip(), 'Вставь ссылку на картинку в IMAGE_LINK'
shutil.rmtree('/tmp/img', ignore_errors=True); os.makedirs('/tmp/img')
src = gdown.download(IMAGE_LINK.strip(), output='/tmp/img/', fuzzy=True, quiet=False)
orig = Image.open(src).convert('RGB')
W, H = orig.size
scale = 832 / max(W, H)
mw, mh = int(W * scale) // 16 * 16, int(H * scale) // 16 * 16
orig.resize((mw, mh), Image.LANCZOS).save('/tmp/start.png')
print('Картинка:', (W, H), '→ модель', (mw, mh))

# 4. Где движение
if AREA.strip().lower() in ('auto', 'авто', ''):
    from transformers import Owlv2Processor, Owlv2ForObjectDetection
    proc = Owlv2Processor.from_pretrained('google/owlv2-base-patch16-ensemble')
    det = Owlv2ForObjectDetection.from_pretrained('google/owlv2-base-patch16-ensemble')
    inp = proc(text=[[WHAT]], images=orig, return_tensors='pt')
    with torch.no_grad():
        o = det(**inp)
    side = max(W, H)  # OWLv2 дополняет картинку до квадрата
    # В новых transformers эта функция переехала из процессора в image_processor
    post = getattr(proc, 'post_process_object_detection', None) or proc.image_processor.post_process_object_detection
    res = post(o, threshold=0.05, target_sizes=torch.tensor([[side, side]]))[0]
    assert len(res['scores']), f'Не нашла «{WHAT}» — поменяй WHAT или задай AREA числами'
    i = int(res['scores'].argmax())
    x1, y1, x2, y2 = [float(v) for v in res['boxes'][i]]
    print(f'Нашла «{WHAT}», уверенность {float(res["scores"][i]):.2f}')
    bw, bh = x2 - x1, y2 - y1
    if ABOVE:
        x1, x2, y1, y2 = x1 - bw * 0.3, x2 + bw * 0.3, y1 - bh * 2.0, y1 + bh * 0.3
    else:
        x1, x2, y1, y2 = x1 - bw * 0.1, x2 + bw * 0.1, y1 - bh * 0.1, y2 + bh * 0.1
    BOX = (max(0, int(x1)), max(0, int(y1)), min(W, int(x2)), min(H, int(y2)))
    del det
    torch.cuda.empty_cache()
else:
    x, y, w, h = [float(v) for v in AREA.split(',')]
    BOX = (int(W * x / 100), int(H * y / 100), int(W * (x + w) / 100), int(H * (y + h) / 100))
pct = [round(BOX[0] / W * 100), round(BOX[1] / H * 100), round((BOX[2] - BOX[0]) / W * 100), round((BOX[3] - BOX[1]) / H * 100)]
print('Область в процентах (для AREA вручную):', ','.join(map(str, pct)))
prev = orig.copy(); ImageDraw.Draw(prev).rectangle(BOX, outline=(255, 0, 0), width=max(3, W // 300))
prev.save(f'{OUT}/рамка.jpg', quality=85)

# 5. Оживляем
script = '/tmp/VideoX-Fun/examples/wan2.1_fun/predict_i2v.py'
s = open(script).read()
fps = 16
vals = {
    'GPU_memory_mode': '"model_cpu_offload"',
    'model_name': repr(MODEL),
    'sample_size': f'[{mh}, {mw}]',
    'video_length': str(SECONDS * fps + 1),
    'fps': str(fps),
    'weight_dtype': 'torch.float16',  # T4 не умеет bfloat16
    'prompt': repr(PROMPT),
    'negative_prompt': repr('camera movement, zoom, pan, morphing, distortion, blurry, deformed character, text changes'),
    'validation_image_start': repr('/tmp/start.png'),
    'validation_image_end': repr('/tmp/start.png'),  # тот же кадр в конце — бесшовная петля
    'seed': str(SEED),
    'save_path': repr('/tmp/out'),
}
missing = []
for k, v in vals.items():
    s2, n = re.subn(rf'^{k}\s*=.*$', f'{k} = {v}', s, count=1, flags=re.M)
    if n: s = s2
    else: missing.append(k)
if missing:
    print('⚠️ не нашла в скрипте:', missing, '— пришли это Клоду')
open('/tmp/predict_loop.py', 'w').write(s)
sh('cd /tmp/VideoX-Fun && python /tmp/predict_loop.py')
vids = sorted(glob.glob('/tmp/out/**/*.mp4', recursive=True), key=os.path.getmtime)
assert vids, 'Видео не появилось — пришли Клоду последние строки лога'
raw = vids[-1]

# 6. Двигается только область, остальное — исходная картинка
mask = Image.new('L', (W, H), 0); mask.paste(255, BOX)
feather = max(8, int(min(BOX[2] - BOX[0], BOX[3] - BOX[1]) * 0.15))
mask = mask.filter(ImageFilter.GaussianBlur(feather))
for d in ('/tmp/fr', '/tmp/comp'):
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
sh(f'ffmpeg -loglevel error -i "{raw}" /tmp/fr/%04d.png')
for f in sorted(glob.glob('/tmp/fr/*.png')):
    fr = Image.open(f).convert('RGB').resize((W, H), Image.LANCZOS)
    Image.composite(fr, orig, mask).save(f.replace('/fr/', '/comp/'))
sh(f'ffmpeg -loglevel error -y -framerate {fps} -i /tmp/comp/%04d.png -c:v libx264 -pix_fmt yuv420p -crf 16 "{OUT}/петля.mp4"')
shutil.copy(raw, f'{OUT}/сырое.mp4')
print('ГОТОВО: во вкладке Output — петля.mp4 (итог), сырое.mp4 (как нарисовал Ван), рамка.jpg (где искал)')
