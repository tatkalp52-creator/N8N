# Обучение «мини-модели» Пингви (LoRA для SDXL) — Kaggle, одна ячейка.
# Settings → Accelerator → GPU T4 x2; Internet → On. Ничего вставлять не нужно:
# картинки берутся из папки Visual reference по ссылкам (она открыта по ссылке).
# Время: ~1,5–2 ч (обучение) + ~5 мин (пробные картинки). Итог — во вкладке Output:
#   pengui_lora.safetensors — сама мини-модель
#   проба_1.png … проба_4.png — пробные сцены, их и смотрим
# Если упадёт с «CUDA out of memory» — поставь RES = 768 и запусти ещё раз.

# ===== НАСТРОЙКИ =====
# (в ячейке перед запуском можно задать свои, например RES = 768)
RES = globals().get('RES', 1024)        # размер обучающих картинок
STEPS = globals().get('STEPS', 1200)    # шагов обучения
RANK = globals().get('RANK', 16)        # «ёмкость» мини-модели
LR = globals().get('LR', 1e-4)
# =====================

import subprocess, sys, os, json, shutil, glob
def sh(cmd):
    print('>', cmd); subprocess.run(cmd, shell=True, check=True)

OUT = '/kaggle/working'
for f in glob.glob(f'{OUT}/*'):
    os.remove(f) if os.path.isfile(f) else shutil.rmtree(f, ignore_errors=True)

# 1. Установка
if not os.path.exists('/tmp/diffusers'):
    sh('git clone -q --depth 1 https://github.com/huggingface/diffusers /tmp/diffusers')
sh(f'{sys.executable} -m pip -q install -e /tmp/diffusers')
sh(f'{sys.executable} -m pip -q install -r /tmp/diffusers/examples/dreambooth/requirements_sdxl.txt')
sh(f'{sys.executable} -m pip -q install -U peft bitsandbytes gdown datasets')
# старый torchao из образа Kaggle ломает свежий diffusers; нам он не нужен
sh(f'{sys.executable} -m pip -q uninstall -y torchao')
# свежий peft — в свою папку, и обучение смотрит туда первым (в образе Kaggle
# старый peft лежит так, что обычное обновление его не перекрывает)
sh(f'{sys.executable} -m pip -q install --no-deps --upgrade --target /tmp/pylibs peft')
os.environ['PYTHONPATH'] = '/tmp/pylibs' + (':' + os.environ['PYTHONPATH'] if os.environ.get('PYTHONPATH') else '')
sys.path.insert(0, '/tmp/pylibs')
sh(f'cd /tmp/diffusers/examples/dreambooth && {sys.executable} -c "import peft; print(\'peft\', peft.__version__, peft.__file__); '
   f'from diffusers import AutoencoderKL, StableDiffusionXLPipeline; import diffusers.loaders.peft; print(\'ПРОВЕРКА ПРОШЛА\')"')
import torch
assert torch.cuda.is_available(), 'Нет видеокарты: Settings → Accelerator → GPU T4 x2'
print('Видеокарта:', torch.cuda.get_device_name(0))

# Уже обученная мини-модель лежит на Диске? Тогда LORA_ID = 'id файла' в ячейке —
# обучение пропускается, сразу рисуются пробы.
LORA_ID = globals().get('LORA_ID')
if LORA_ID:
    import gdown
    gdown.download(id=LORA_ID, output=f'{OUT}/pengui_lora.safetensors', quiet=False)
    assert os.path.getsize(f'{OUT}/pengui_lora.safetensors') > 10_000_000, 'Файл не скачался: открой доступ по ссылке'
else:
    # 2. Набор картинок: только Visual reference. (id, рамка, подпись) — подпись называет
    # всё, что меняется (наушники, поза, место), чтобы это можно было просить или не просить.
    T = "pengui, a small penguin with a red knitted scarf, eyes closed, rosy cheeks, soft colored pencil storybook illustration"
    CHALLAH = "1613T_hq9nk9YyiPWJDjzKyd8jBjwZPrs"
    BIBLE = "1yy52ryUeE8qr1YdXcQK856U6eSz3XyZe"
    STRETCH = "1bhkS6ALdSgd7krau333bEWtwXLKpWmdN"
    GUIDE = "1UIGLQhSptHVOrvRK_wsujWYJcPGjTe84"
    BEACH = "1h7M_lKxgLIThWqwlbwO2mLPlaohBCdK8"
    METRO = "1IIMKOYjHimRH_XFgbzflA4psSeoRGoBt"
    HERRING = "14HDl8xuGTDIC89xYp262qABqQD-tJ0jx"
    ITEMS = [
        (CHALLAH, (770, 230, 960, 420), f"{T}, stirring a bowl with a wooden spoon, no headphones, beige paper"),
        (CHALLAH, (1000, 230, 1190, 420), f"{T}, mixing dough in a bowl, a bag of flour, no headphones, beige paper"),
        (CHALLAH, (1230, 230, 1420, 420), f"{T}, kneading dough on a floured table, no headphones, beige paper"),
        (CHALLAH, (1440, 230, 1630, 420), f"{T}, covering a bowl with a checked towel, no headphones, beige paper"),
        (CHALLAH, (740, 672, 960, 892), f"{T}, shaping a spiral of dough, no headphones, beige paper"),
        (CHALLAH, (980, 668, 1200, 888), f"{T}, brushing a round loaf with egg wash, no headphones, beige paper"),
        (CHALLAH, (1220, 655, 1475, 910), f"{T}, taking a baked round bread out with oven mitts, a window with the city, no headphones, beige paper"),
        (BIBLE, (15, 645, 168, 822), f"{T}, standing, front view, no headphones, light paper"),
        (BIBLE, (190, 645, 338, 822), f"{T}, standing, side view, no headphones, light paper"),
        (BIBLE, (348, 645, 495, 822), f"{T}, standing, back view, no headphones, light paper"),
        (BIBLE, (535, 700, 870, 940), f"{T}, tiny in a snowy city street among tall people, carrying a paper bag, no headphones"),
        (BIBLE, (900, 700, 1055, 940), f"{T}, sitting at a cafe table with a cup, no headphones"),
        (BIBLE, (1055, 700, 1210, 940), f"{T}, reading a book among library shelves, no headphones"),
        (STRETCH, (440, 80, 700, 430), f"{T}, wearing headphones, standing, tilting his head, beige paper"),
        (STRETCH, (760, 80, 1110, 430), f"{T}, wearing headphones, stretching his wings wide, beige paper"),
        (STRETCH, (1100, 80, 1370, 430), f"{T}, wearing headphones, bending to the side, beige paper"),
        (STRETCH, (90, 600, 360, 828), f"{T}, wearing headphones, curled forward on the floor, beige paper"),
        (STRETCH, (410, 510, 690, 850), f"{T}, wearing headphones, sitting on the floor, twisting, beige paper"),
        (STRETCH, (780, 580, 1090, 840), f"{T}, wearing headphones, lying on his back holding his feet, beige paper"),
        (STRETCH, (1100, 508, 1370, 838), f"{T}, wearing headphones, standing tall, beige paper"),
        (GUIDE, (430, 150, 1060, 780), f"{T}, wearing headphones, dozing on a subway seat, a newspaper, the city in the window"),
        (BEACH, (450, 180, 1134, 864), f"{T}, wearing headphones, lounging on a striped beach chair under a beach umbrella, a tin of sardines, an old suitcase, sand and sea"),
        (METRO, (560, 180, 1220, 840), f"{T}, wearing headphones, sitting on a subway seat, a newspaper slipping down"),
        (HERRING, (230, 220, 750, 740), f"{T}, hurrying along a snowy street at night with a paper bag of herring and bread, scarf flying, warm shop window light"),
    ]

    import gdown
    from PIL import Image
    SRC = '/tmp/src'; DS = '/tmp/pengui_ds'
    os.makedirs(SRC, exist_ok=True)
    shutil.rmtree(DS, ignore_errors=True); os.makedirs(DS)
    cache = {}
    meta = []
    for i, (fid, box, cap) in enumerate(ITEMS):
        if fid not in cache:
            p = f'{SRC}/{fid}.png'
            if not os.path.exists(p):
                gdown.download(id=fid, output=p, quiet=True)
            cache[fid] = Image.open(p).convert('RGB')
        c = cache[fid].crop(box)
        w, h = c.size; s = max(w, h)
        edge = c.resize((1, 1), Image.BOX).getpixel((0, 0))  # дополняем до квадрата цветом бумаги
        sq = Image.new('RGB', (s, s), edge); sq.paste(c, ((s - w) // 2, (s - h) // 2))
        name = f'{i:02d}.png'
        sq.resize((RES, RES), Image.LANCZOS).save(f'{DS}/{name}')
        meta.append({'file_name': name, 'text': cap})
    with open(f'{DS}/metadata.jsonl', 'w') as f:
        for m in meta:
            f.write(json.dumps(m, ensure_ascii=False) + '\n')
    print('Картинок в наборе:', len(meta))

    # 3. Обучение
    # Полоска прогресса пишется через \r, и в логе Kaggle её не видно часами.
    # Поэтому вывод режем по \r и печатаем отдельной строкой каждые 50 шагов.
    import re, time
    def train(cmd):
        print('>', cmd, flush=True)
        t0 = time.time(); last = -1; tail = []
        pr = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        buf = b''
        while True:
            ch = pr.stdout.read(4096)
            if not ch:
                break
            buf += ch
            parts = re.split(rb'[\r\n]', buf); buf = parts.pop()
            for ln in parts:
                t = ln.decode('utf-8', 'replace').strip()
                if not t:
                    continue
                tail = (tail + [t])[-40:]
                m = re.search(r'Steps:\s*\d+%.*?(\d+)/(\d+)', t)
                if m:
                    n = int(m.group(1))
                    if n // 50 != last // 50 or (n == int(m.group(2)) and n != last):
                        last = n
                        print(f'ШАГ {n}/{m.group(2)} · {int((time.time() - t0) // 60)} мин', flush=True)
        if pr.wait() != 0:
            print('\n'.join(tail))
            raise SystemExit('Обучение упало — пришли этот лог')
    train(f'cd /tmp/diffusers/examples/dreambooth && accelerate launch --mixed_precision=fp16 --num_processes=1 '
       f'train_dreambooth_lora_sdxl.py '
       f'--pretrained_model_name_or_path=stabilityai/stable-diffusion-xl-base-1.0 '
       f'--pretrained_vae_model_name_or_path=madebyollin/sdxl-vae-fp16-fix '
       f'--dataset_name={DS} --image_column=image --caption_column=text '
       f'--instance_prompt="pengui" '
       f'--output_dir=/tmp/lora_out --resolution={RES} --random_flip '
       f'--train_batch_size=1 --gradient_accumulation_steps=1 --gradient_checkpointing '
       f'--use_8bit_adam --learning_rate={LR} --lr_scheduler=constant --lr_warmup_steps=0 '
       f'--rank={RANK} --max_train_steps={STEPS} --checkpointing_steps=100000 '
       f'--mixed_precision=fp16 --seed=42')
    shutil.copy('/tmp/lora_out/pytorch_lora_weights.safetensors', f'{OUT}/pengui_lora.safetensors')

# 4. Пробные сцены
# diffusers поставлен в этой же сессии (-e), ядро его само не видит — показываем путь
sys.path.insert(0, '/tmp/diffusers/src')
import importlib; importlib.invalidate_caches()
from diffusers import StableDiffusionXLPipeline, AutoencoderKL
vae = AutoencoderKL.from_pretrained('madebyollin/sdxl-vae-fp16-fix', torch_dtype=torch.float16)
pipe = StableDiffusionXLPipeline.from_pretrained('stabilityai/stable-diffusion-xl-base-1.0', vae=vae,
                                                 torch_dtype=torch.float16, variant='fp16').to('cuda')
pipe.load_lora_weights(f'{OUT}/pengui_lora.safetensors')
STYLE = "soft colored pencil storybook illustration, aged cream paper texture, muted palette, light and airy, no headphones"
SCENES = [
    "pengui sitting in a cozy armchair by a window reading a book, a mug of coffee on a small side table, autumn New York brownstones outside, small in the left third of the frame",
    "pengui at a small kitchen table by the window writing a postcard, a birdcage with a yellow canary on the windowsill",
    "pengui walking in an autumn park with fallen leaves, carrying a paper bag, small figure in a wide scene",
    "pengui sitting on a little bridge over a pond with a fishing rod, quiet morning, small in the frame",
]
NEG = "photo, 3d render, text, letters, watermark, deformed, extra limbs, big eyes, open eyes, headphones"
for k, sc in enumerate(SCENES, 1):
    img = pipe(prompt=f"{sc}, {STYLE}", negative_prompt=NEG, width=1344, height=768,
               num_inference_steps=30, guidance_scale=6.0,
               generator=torch.Generator('cuda').manual_seed(100 + k)).images[0]
    img.save(f'{OUT}/проба_{k}.png')
    print('готово:', k)
print('ГОТОВО: во вкладке Output — pengui_lora.safetensors и проба_1…4.png')
