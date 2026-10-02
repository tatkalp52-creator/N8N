# Архив для обучения Flux LoRA на fal: те же вырезки, без дополнения до квадрата;
# в подписях только слово pengui + то, что меняется (герой и стиль привязываются к слову).
# Запуск: S=<папка, где src/<id>.png> python3 tools/lora/build_fal_zip.py
import os, shutil, zipfile
src = open('tools/lora/pengui_lora_kaggle.py').read()
start = src.index('T = "pengui'); end = src.index('import gdown', start)
ns = {}; exec(src[start:end].replace('\n    ', '\n'), ns)
from PIL import Image
S = os.environ['S']; DS = S + '/pengui_fal2'
shutil.rmtree(DS, ignore_errors=True); os.makedirs(DS)
cache = {}
T = ns['T']
for i, (fid, box, cap) in enumerate(ns['ITEMS']):
    if fid not in cache: cache[fid] = Image.open(f'{S}/src/{fid}.png').convert('RGB')
    c = cache[fid].crop(box); w, h = c.size; k = 1024 / max(w, h)
    c.resize((round(w*k), round(h*k)), Image.LANCZOS).save(f'{DS}/{i:02d}.png')
    # постоянные черты героя и стиль не описываем — пусть привяжутся к слову pengui
    rest = cap[len(T):].strip(', ')
    rest = rest.replace(', beige paper', '').replace(', light paper', '')
    open(f'{DS}/{i:02d}.txt', 'w').write(f'pengui, {rest}' if rest else 'pengui')
z = S + '/pengui_fal.zip'
with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
    for f in sorted(os.listdir(DS)): zf.write(f'{DS}/{f}', f)
print(z, os.path.getsize(z))
for f in ['00','07','10','21']: print(open(f'{DS}/{f}.txt').read())
