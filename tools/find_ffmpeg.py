# Находит сборку ffmpeg, на которой склейка сборщика не виснет, и ставит её (25.10).
# Запуск (сервер): docker exec -i <сборщик> python3 - < find_ffmpeg.py
# 1) копирует куски видео и 60 с звука из идущей сборки; 2) останавливает зависшую склейку;
# 3) проверяет текущий ffmpeg, потом сборки BtbN день за днём назад (не новее 22.10 18:22);
# 4) первую, которая склеила пробу, ставит в /usr/local/bin (прежняя остаётся как *.prev).
import glob, json, os, shutil, subprocess, tarfile, urllib.request

work = sorted(glob.glob("/tmp/assemble_*"), key=os.path.getmtime)
work = [w for w in work if os.path.exists(w + "/pieces/list.txt")]
if not work:
    raise SystemExit("нет папки сборки с кусками — сначала «пересобери», потом снова эту команду")
w = work[-1]
src = "/tmp/probe_src"
shutil.rmtree(src, ignore_errors=True); os.makedirs(src)
with open(w + "/pieces/list.txt") as f:
    lines = [l for l in f if l.strip()][:3]          # начало + две петли
with open(src + "/list.txt", "w") as f:
    f.writelines(lines)
audio = (glob.glob(w + "/audio_loop_*.wav") or glob.glob(w + "/audio_final*.wav"))[0]
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", audio, "-t", "70", "-c", "copy", src + "/a.wav"], check=True)
subprocess.run(["pkill", "-9", "-f", "pieces/list.txt"])
print("взяла пробу из", w)


def probe(ff):
    out = src + "/p.mp4"
    cmd = [ff, "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", src + "/list.txt",
           "-i", src + "/a.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy",
           "-af", "afade=t=in:st=0:d=1.5:curve=tri,afade=t=out:st=57:d=3.0:curve=tri",
           "-c:a", "aac", "-b:a", "384k", "-t", "60", "-movflags", "+faststart", out]
    try:
        r = subprocess.run(cmd, timeout=60, capture_output=True)
        ok = r.returncode == 0 and os.path.getsize(out) > 1_000_000
    except subprocess.TimeoutExpired:
        ok = False
    if os.path.exists(out): os.remove(out)
    return ok


ver = lambda ff: subprocess.run([ff, "-version"], capture_output=True, text=True).stdout.split("\n")[0]
if probe("/usr/local/bin/ffmpeg"):
    raise SystemExit("текущий ffmpeg склеивает нормально: " + ver("/usr/local/bin/ffmpeg"))
print("текущий виснет:", ver("/usr/local/bin/ffmpeg"))

rs = json.load(urllib.request.urlopen("https://api.github.com/repos/BtbN/FFmpeg-Builds/releases?per_page=60"))
rs = sorted([r for r in rs if r["published_at"] <= "2026-10-22T18:22"], key=lambda r: r["published_at"], reverse=True)
for r in rs[:8]:
    a = [x for x in r["assets"] if x["name"].startswith("ffmpeg-N") and x["name"].endswith("linux64-gpl.tar.xz")]
    if not a: continue
    d = "/tmp/ffcand"; shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    urllib.request.urlretrieve(a[0]["browser_download_url"], d + "/f.tar.xz")
    t = tarfile.open(d + "/f.tar.xz")
    for m in t.getmembers():
        if m.name.endswith(("/bin/ffmpeg", "/bin/ffprobe")):
            m.name = os.path.basename(m.name); t.extract(m, d)
    os.remove(d + "/f.tar.xz")
    os.chmod(d + "/ffmpeg", 0o755); os.chmod(d + "/ffprobe", 0o755)
    if probe(d + "/ffmpeg"):
        for b in ("ffmpeg", "ffprobe"):
            dst = "/usr/local/bin/" + b
            shutil.copy(dst, dst + ".prev"); shutil.copy(d + "/" + b, dst)
        shutil.rmtree(d, ignore_errors=True); shutil.rmtree(src, ignore_errors=True)
        raise SystemExit("ПОСТАВИЛА рабочую: " + ver("/usr/local/bin/ffmpeg") + "  — теперь в боте «пересобери»")
    print("виснет и эта:", r["published_at"][:10])
shutil.rmtree("/tmp/ffcand", ignore_errors=True)
print("рабочей среди 8 последних сборок нет — ничего не менял")
