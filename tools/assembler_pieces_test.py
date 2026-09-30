# Локальная проверка сборки кусками (4 вида тела). Запуск из папки с img.jpg, src_loop.mp4, src_event.mp4, audio.wav.
import sys, os, time, shutil
sys.path.insert(0, '/home/user/N8N/assembler')
import app as A
A.download_media = lambda url, dest: shutil.copy(url.replace('http://x/', ''), dest) or dest
font = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
alpha = "if(lt(t,5),t/5,if(lt(t,15),1,if(lt(t,21),(21-t)/6,0)))"
sh, mn = [], []  # локальный ffmpeg без drawtext
base = f"scale={A.VIDEO_WIDTH}:{A.VIDEO_HEIGHT}," + ",".join(A.old_film_filters(2))
audio_chain = "afade=t=in:st=0:d=1.5:curve=tri,afade=t=out:st=147:d=3:curve=tri"
cases = {'static': {}, 'loop': {'fx_LoopUrl': 'http://x/src_loop.mp4'},
         'events': {'fx_EventUrls': 'http://x/src_event.mp4\nhttp://x/src_event.mp4'},
         'mix': {'fx_LoopUrl': 'http://x/src_loop.mp4', 'fx_EventUrls': 'http://x/src_event.mp4'}}
for name, extra in cases.items():
    d = {'eventGapMinSeconds': '20', 'eventGapMaxSeconds': '40', **extra}
    wd = f'w_{name}'; shutil.rmtree(wd, ignore_errors=True); os.makedirs(wd)
    t0 = time.time()
    A.build_video_from_pieces(d, wd, 'img.jpg', 'audio.wav', 150.0, base, sh, mn, '8', 21.0,
                              audio_chain, f'out_{name}.mp4', 'P1')
    print(name, 'сек сборки', round(time.time() - t0, 1))
