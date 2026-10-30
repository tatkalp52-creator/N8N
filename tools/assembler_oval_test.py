# Овалы пара и моргания: python3 tools/assembler_oval_test.py
import sys, os, json, tempfile
sys.path.insert(0, ''+__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)),'..')+'/assembler')
import numpy as np
from PIL import Image, ImageDraw
import app as A
A.set_vocab({'fxWords': json.load(open(''+__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)),'..')+'/tools/effects/slova.json'))}); A.EFFECTS_LOOP_SECONDS = 6.0
img = Image.new('RGB', (1536, 864), (180, 150, 110)); d = ImageDraw.Draw(img)
d.ellipse((760, 420, 800, 440), fill=(20, 20, 20))      # горизонтальный «глаз»
path = os.path.join(tempfile.mkdtemp(), 'i.png'); img.save(path)
spec = A.parse_effects('моргание: 50.78, 49.77; овал 20 × 10; наклон 0\nпар: 30, 60; овал 40 × 8; наклон 10; скорость -5')
print([(k, n.oval, n.tilt, n.knobs) for k, n in spec])
assert spec[0][1].oval == (20.0, 10.0) and spec[1][1].oval == (40.0, 8.0) and spec[1][1].tilt == 10.0
base = np.asarray(img, np.float32)
closed, soft, bx0, by0 = A.blink_patch(img, base, 780, 430, 1.0, 4, False, None, (20, 10), 0)
closed2, *_ = A.blink_patch(img, base, 780, 430, 1.0, 4, False, None, (10, 20), 0)
# горизонтальный овал закрывает глаз по ширине, вертикальный — по высоте: результаты разные
print('patch', closed.shape, float(np.abs(closed - closed2).mean()))
fr = A.render_effects_loop(path, [spec[1]], {}, 24, None, still_at=0.5)
print('steam frame', np.asarray(fr).shape)
print('OK')
