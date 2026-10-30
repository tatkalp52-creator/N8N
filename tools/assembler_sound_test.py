# (28.10) Звук сборщика — только из колонок 🎬: разрез по тишине, края, тема по метке, паузы, фейды, EQ.
# Нет колонок — нет обработки. Запуск: python3 tools/assembler_sound_test.py  (нужен ffmpeg)
import sys, os, tempfile, shutil, zipfile, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assembler'))
import app as A
d = tempfile.mkdtemp(prefix='sndtest_')
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'sine=f=440:d=40', '-ar', '48000', '-ac', '2', os.path.join(d, '00 Theme.wav')], check=True)
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'sine=f=330:d=150', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo:d=8',
                '-f', 'lavfi', '-i', 'sine=f=550:d=130', '-filter_complex',
                '[0:a]aformat=sample_rates=48000:channel_layouts=stereo[a];[2:a]aformat=sample_rates=48000:channel_layouts=stereo[c];[a][1:a][c]concat=n=3:v=0:a=1',
                os.path.join(d, '01 Lane.wav')], check=True)
z = os.path.join(d, 'a.zip')
with zipfile.ZipFile(z, 'w') as f:
    for n in ('00 Theme.wav', '01 Lane.wav'): f.write(os.path.join(d, n), n)
A.download_file = lambda url, dest: shutil.copy(z, dest) or dest
TMPL = {'splitSilenceDb': '-40', 'splitSilenceSeconds': '6', 'splitMinTrackSeconds': '119',
        'trimSilenceDb': '-40', 'trimSilenceSeconds': '1', 'themeMark': '00', 'gapSeconds': '1',
        'fadeInSeconds': '1.5', 'fadeOutSeconds': '3',
        'eq1Hz': '80', 'eq1Db': '-2', 'eq1Q': '0.71'}
snd = A.sound_settings(TMPL)
print('settings', snd)
w = tempfile.mkdtemp()
path, dur = A.build_audio_track('http://x/a.zip', w, snd, loudness_report=[])
print('duration', round(dur, 1))
assert 595 < dur < 612, dur
snd0 = A.sound_settings({})
assert snd0['split'] is None and snd0['trim'] is None and snd0['eq'] == '' and snd0['fade_in'] is None
w2 = tempfile.mkdtemp()
p2, d2 = A.build_audio_track('http://x/a.zip', w2, snd0)
print('no columns duration', round(d2, 1))
assert 650 < d2 < 662, d2
for bad in ({'splitSilenceDb': '-40'}, {'eq2Hz': '300'}):
    try:
        A.sound_settings(bad); raise SystemExit('should fail')
    except RuntimeError as e: print('ok error:', e)
assert A.is_theme_file('/x/00 Theme.wav', '00') and not A.is_theme_file('/x/001 a.wav', '00') and not A.is_theme_file('/x/00 a.wav', '')
print('ALL OK')
