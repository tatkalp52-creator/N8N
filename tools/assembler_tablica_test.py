# (28.10) Сборка целиком — только из таблицы: кадр, надпись, шрифт по имени, звук, оживление словами из листа «Слова».
# Чего-то нет в таблице — сборщик говорит, чего. Запуск: python3 tools/assembler_tablica_test.py  (нужен ffmpeg)
import sys, os, json, tempfile, shutil, zipfile, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'assembler'))
import app as A

d = tempfile.mkdtemp(prefix='tabtest_')
img = os.path.join(d, 'img.jpg')
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'gradients=s=1536x864:d=1', '-frames:v', '1', img], check=True)
for name, f, sec in (('01 One.wav', 330, 25), ('02 Two.wav', 550, 25)):
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', f'sine=f={f}:d={sec}', '-ar', '48000', '-ac', '2',
                    os.path.join(d, name)], check=True)
z = os.path.join(d, 'a.zip')
with zipfile.ZipFile(z, 'w') as zf:
    for n in ('01 One.wav', '02 Two.wav'):
        zf.write(os.path.join(d, n), n)

def fake_download(url, dest):
    shutil.copy(img if url.endswith('.jpg') else z, dest)
    return dest
A.download_file = fake_download

WORDS = json.load(open(os.path.join(HERE, 'effects', 'slova.json')))
BASE = {
    'projectId': 'T1', 'imageUrl': 'http://x/i.jpg', 'audioZipUrl': 'http://x/a.zip',
    'videoWidth': '1920', 'videoHeight': '1072', 'stillFps': '5', 'videoFps': '12', 'loopCount': '1',
    'gapSeconds': '1', 'fadeInSeconds': '1', 'fadeOutSeconds': '2',
    'overlayText': 'Quiet Night', 'overlayFont': 'Pengui Hand', 'overlaySize': '90', 'overlayColor': '#E7DFCF',
    'overlayShadow': '#2C3036', 'overlayShadowBlur': '8', 'overlayShadowOpacity': '0.6', 'overlayMargin': '100',
    'overlayPosition': 'right', 'overlayHoldSeconds': '8', 'overlayFadeInSeconds': '2', 'overlayFadeOutSeconds': '2',
    'overlayLineSpacing': '0.75', 'overlayBorder': '1',
    'eventGapMinSeconds': '8', 'eventGapMaxSeconds': '12', 'leafVariants': '1', 'leafLieSeconds': '3',
    'fx_Effects': 'пар: 30, 60; густота 6\nсвеча: 60, 40; ореол 7\nморгание: 50, 30\n'
                  'листья: 40, 5 → 42, 60; клён; жёлтый; раз в 10\nобложка Б: кадр 10 10 — 70 70, оверлей справа',
    'fxWords': WORDS,
    'fxTable': [{'mech': 'steam_cup', 'knobs': 'густота 5 · толщина 7'}],
}
c = A.app.test_client()
r = c.post('/assemble', json=BASE)
print('assemble', r.status_code, r.headers.get('Content-Type'), len(r.data))
assert r.status_code == 200 and len(r.data) > 100000, r.data[:500]
assert c.get('/thumbnail/T1').status_code == 200
print('covers', c.get('/covers/T1').get_json())

# Нет нужного в таблице — сборщик говорит, чего не хватает (а не подставляет своё)
for drop, words in (('overlayFont', 'overlayFont'), ('overlayHoldSeconds', 'overlayHoldSeconds'), ('videoWidth', 'VideoWidth'),
                    ('stillFps', 'StillFps'), ('fxWords', 'Слова'), ('eventGapMinSeconds', 'EventGapMinSeconds')):
    bad = dict(BASE); bad.pop(drop)
    rr = c.post('/assemble', json=bad)
    txt = (rr.get_json(silent=True) or {}).get('error') or rr.get_data(as_text=True)
    assert rr.status_code >= 400 and words in txt, (drop, rr.status_code, txt[:300])
    print('нет', drop, '→', rr.status_code, 'говорит про', words)
bad = dict(BASE, overlayFont='Нет Такого Шрифта')
rr = c.post('/assemble', json=bad); assert 'не найден' in (rr.get_json(silent=True) or {}).get('error', ''), rr.get_data(as_text=True)[:300]
print('ALL OK')
