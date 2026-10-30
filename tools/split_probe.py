# Проба (27.10): одна дорожка из Suno Studio (треки подряд с паузами) → сборщик режет её по паузам.
# Меряет время резки и даёт послушать куски (с короткими fade in/out) на /pages/split/. Сборщик не меняется.
import os, shutil, subprocess, sys, tempfile, time
sys.path.insert(0, "/app")
import app as A
ff = "/app/bin/ffmpeg" if os.path.exists("/app/bin/ffmpeg") else "ffmpeg"
A.FFMPEG_BIN = ff
src = os.environ.get("SRC", "").strip()
work = tempfile.mkdtemp(prefix="split_")
print("качаю…")
t0 = time.time()
d, _ = A.resolve_audio_tracks_dir(src, work)
print(f"скачано за {time.time() - t0:.0f} с")
files = sorted(f for f in os.listdir(d) if f.lower().endswith((".wav", ".mp3")))
print("файлы:", files)
out_dir = os.path.join(A.PAGES_DIR, "split")
shutil.rmtree(out_dir, ignore_errors=True); os.makedirs(out_dir)
n = 0
for fi, f in enumerate(files):
    t1 = time.time()
    parts = A.split_by_silence(os.path.join(d, f), work, split_dir_name=f"s{fi}", min_segment_seconds=20)
    print(f"{f}: кусков {len(parts)}, резка {time.time() - t1:.0f} с")
    for p in parts:
        n += 1
        s, e = A.get_content_bounds(p)
        dur = e - s
        out = os.path.join(out_dir, f"{n}.mp3")
        subprocess.run([ff, "-v", "error", "-y", "-ss", str(s), "-to", str(e), "-i", p,
                        "-af", f"afade=t=in:st=0:d=1.5,afade=t=out:st={max(0, dur - 3):.2f}:d=3",
                        "-c:a", "libmp3lame", "-b:a", "192k", out], check=True)
        print(f"   кусок {n}: {int(dur // 60)}:{int(dur % 60):02d}   /pages/split/{n}.mp3")
print(f"всего {time.time() - t0:.0f} с")
shutil.rmtree(work, ignore_errors=True)
