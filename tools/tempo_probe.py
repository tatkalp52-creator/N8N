# Проба (27.10): вернуть трекам из мультитрека Suno Studio их родной темп по числу в имени.
# Запуск (сервер): wget -qO- <raw этого файла> | docker exec -i -e SRC='<ссылка на zip на Диске>' <сборщик> python3 -u -
# Темп проекта = число в имени ПЕРВОГО трека (порядок в архиве); каждый трек ускоряется/замедляется
# в «родной / проекта» раз без смены высоты, тишина по краям обрезается. Результат — mp3 на страничке
# /pages/tempo/ сборщика; ничего в сборщике не меняется.
import os, re, shutil, subprocess, sys, tempfile
sys.path.insert(0, "/app")
import app as A

ff = "/app/bin/ffmpeg" if os.path.exists("/app/bin/ffmpeg") else "ffmpeg"
A.FFMPEG_BIN = ff        # официальный: ночной виснет на фильтрах звука по длинным файлам
has_rb = "rubberband" in subprocess.run([ff, "-hide_banner", "-filters"], capture_output=True, text=True).stdout
src = os.environ.get("SRC", "").strip()
if not src:
    raise SystemExit("нет ссылки SRC")
work = tempfile.mkdtemp(prefix="tempo_")
d, zip_order = A.resolve_audio_tracks_dir(src, work)
files = [f for f in os.listdir(d) if f.lower().endswith((".wav", ".mp3"))]
files.sort(key=lambda f: (zip_order or {}).get(f, 10**6))
print("файлы по порядку в архиве:")
for f in files:
    print("  ", f)

def bpm_of(name):
    nums = re.findall(r"\d+(?:[.,]\d+)?", os.path.splitext(name)[0])
    return float(nums[-1].replace(",", ".")) if nums else None

project = bpm_of(files[0])
print("темп проекта (первый трек):", project, "| растяжение:", "rubberband" if has_rb else "atempo")
out_dir = os.path.join(A.PAGES_DIR, "tempo")
shutil.rmtree(out_dir, ignore_errors=True); os.makedirs(out_dir)
for f in files:
    bpm = bpm_of(f)
    if not bpm or not project:
        print("  пропускаю (нет числа в имени):", f); continue
    path = os.path.join(d, f)
    start, end = A.get_content_bounds(path)
    k = bpm / project
    out = os.path.join(out_dir, f"{int(bpm)}.mp3")
    subprocess.run([ff, "-v", "error", "-y", "-ss", str(start), "-to", str(end), "-i", path,
                    "-af", (f"rubberband=tempo={k:.6f}:pitchq=quality" if has_rb else f"atempo={k:.6f}"), "-c:a", "libmp3lame", "-b:a", "192k", out], check=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out],
                               capture_output=True, text=True).stdout.strip() or 0)
    print(f"  {f}: родной {bpm:g}, ×{k:.3f} → {int(dur // 60)}:{int(dur % 60):02d}   /pages/tempo/{int(bpm)}.mp3")
shutil.rmtree(work, ignore_errors=True)
print("готово")
