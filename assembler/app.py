import os
import re
import subprocess
import tempfile
import zipfile
import shutil
import glob
import requests
import gdown
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

FFMPEG_BIN = "ffmpeg"
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1072
FONT_PATH = "/home/node/.n8n/ffmpeg-root/usr/share/fonts"

# Готовые обложки живут здесь постоянно (не в tempdir, который чистится после
# каждой сборки) — чтобы n8n мог прийти за ними ПОСЛЕ того, как видео уже
# отдано и его временная папка удалена.
THUMBNAIL_DIR = "/tmp/pengui_thumbnails"
os.makedirs(THUMBNAIL_DIR, exist_ok=True)

FONT_MAP = {
    "Courier Prime": "/usr/share/fonts/truetype/courier-prime/CourierPrime-Regular.ttf",
    "DejaVu Sans": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
}
DEFAULT_FONT_PATH = FONT_MAP["Courier Prime"]


# Раньше отступ от края (60px) был жёстко зашит в каждую строку ниже.
# Теперь это функция: принимает отступ (margin) и строит те же самые
# позиции, но с настраиваемым числом — margin приходит из таблицы
# (OverlayStyle: "margin:100"), с запасным значением 60, если в таблице
# этого параметра нет (старые проекты, где колонку ещё не обновили).
def build_overlay_positions(margin=60):
    return {
        "top-left":      f"x={margin}:y={margin}",
        "top-center":    f"x=(w-text_w)/2:y={margin}",
        "top-right":     f"x=w-text_w-{margin}:y={margin}",
        "center-left":   f"x={margin}:y=(h-text_h)/2",
        "center":        "x=(w-text_w)/2:y=(h-text_h)/2",
        "center-right":  f"x=w-text_w-{margin}:y=(h-text_h)/2",
        "bottom-left":   f"x={margin}:y=h-text_h-{margin}",
        "bottom-center": f"x=(w-text_w)/2:y=h-text_h-{margin}",
        "bottom-right":  f"x=w-text_w-{margin}:y=h-text_h-{margin}",
        # В таблице позиция хранится простым словом ("left"/"right"/"center"),
        # поэтому добавляем такие же простые псевдонимы на вертикальный центр —
        # раньше "left"/"right" в этом списке не было вообще, и код молча
        # подставлял "center" по умолчанию.
        # НОВОЕ: якорь не от края кадра, а от линий третей (кадр мысленно
        # поделён на 3 равные части). "left" — правый край текста упирается
        # в первую линию трети, текст растёт влево. "right" — левый край
        # текста (первая буква) упирается во вторую линию трети, текст
        # растёт вправо. margin тут больше не участвует.
        "left":          "x=w/3-text_w:y=(h-text_h)/2",
        "right":         "x=2*w/3:y=(h-text_h)/2",
    }


def natural_sort_key(path):
    """Сортирует по числу, стоящему в НАЧАЛЕ имени файла, как по настоящему числу,
    а не как по тексту. Studio-номер студии (0, 1, 2 ... 19) всегда встаёт первым
    в имени файла — именно по нему и сортируем. Если числа в начале нет —
    такой файл уходит в конец списка, отсортированный по алфавиту.

    НОВОЕ: Suno Studio при скачивании треков по одному (поставил трек на
    дорожку — скачал — убрал — поставил следующий) называет все файлы
    одинаково "01", но добавляет диапазон времени в скобках, например
    "01 [9m33s-12m50s].wav" — начало этого диапазона растёт с каждым
    следующим скачанным треком (дорожка в Studio продвигается вперёд), и
    поэтому надёжно отражает порядок скачивания, даже когда сам "01"
    у всех одинаковый. Если такой диапазон есть в имени — сортируем по
    его началу (в секундах), это приоритетнее обычного числа в начале
    имени."""
    filename = os.path.basename(path)
    range_match = re.search(r"\[(\d+)m(\d+)s-", filename)
    if range_match:
        minutes, seconds = int(range_match.group(1)), int(range_match.group(2))
        return (0, minutes * 60 + seconds, filename)
    match = re.match(r"^(\d+)", filename)
    if match:
        return (1, int(match.group(1)), filename)
    return (2, 0, filename)


def run_ffmpeg(args):
    cmd = [FFMPEG_BIN, "-y"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr[-3000:]}")
    return result


def download_file(url, dest_path):
    if "drive.google.com" in url or "drive.usercontent.google.com" in url:
        id_match = re.search(r"[?&/]id[=/]([a-zA-Z0-9_-]+)", url) or re.search(r"/d/([a-zA-Z0-9_-]+)", url)
        if id_match:
            file_id = id_match.group(1)
            gdown.download(id=file_id, output=dest_path, quiet=True)
            return dest_path

    r = requests.get(url, stream=True, timeout=120)
    r.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    return dest_path


# НОВОЕ: раньше источник треков всегда должен был быть ZIP-архивом — если
# автор присылал ссылку на открытую папку Google Drive с отдельными файлами
# внутри (без зип-обёртки), download_file получал HTML-страницу папки
# вместо архива, и zipfile.ZipFile падала с ошибкой "не похоже на zip".
# Теперь источник определяется по самой ссылке: обычная ссылка на файл
# (в т.ч. ZIP на Google Drive) — распаковывается как раньше; ссылка на
# папку (.../drive/folders/<id>) — файлы внутри неё скачиваются напрямую,
# без архива, тем же способом (gdown), каким уже скачивались одиночные файлы.
# Дальше по коду ничего не меняется — что зип, что папка, на выходе всегда
# просто папка с .mp3/.wav файлами внутри.
def resolve_audio_tracks_dir(source_url, work_dir):
    extract_dir = os.path.join(work_dir, "audio_tracks")
    os.makedirs(extract_dir, exist_ok=True)

    folder_match = re.search(r"drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)", source_url)
    if folder_match:
        gdown.download_folder(id=folder_match.group(1), output=extract_dir, quiet=True, use_cookies=False)
        return extract_dir

    zip_path = download_file(source_url, os.path.join(work_dir, "audio.zip"))
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_dir)
    return extract_dir


def get_real_duration(input_path, noise_threshold="-40dB", min_silence_duration=1.0):
    """Оставлена как есть — только конец файла, для обратной совместимости
    с местами, которые ждут именно одно число (например, /trackinfo)."""
    content_start, content_end = get_content_bounds(input_path, noise_threshold, min_silence_duration)
    return content_end


# НОВОЕ: находит настоящие начало И конец звука в файле, отрезая тишину
# с ОБЕИХ сторон — не только в конце (как было раньше), но и в начале,
# если она там есть. Нужно для сценария "каждый трек на своей дорожке,
# у второго и следующих может быть тишина и в начале, и в конце сразу".
def get_content_bounds(input_path, noise_threshold="-40dB", min_silence_duration=1.0):
    full_duration_probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", input_path],
        capture_output=True, text=True
    )
    full_duration = float(full_duration_probe.stdout.strip())

    detect = subprocess.run(
        [FFMPEG_BIN, "-i", input_path, "-af",
         f"silencedetect=noise={noise_threshold}:d={min_silence_duration}",
         "-f", "null", "-"],
        capture_output=True, text=True
    )
    starts = [float(m) for m in re.findall(r"silence_start:\s*([\d.]+)", detect.stderr)]
    ends = [float(m) for m in re.findall(r"silence_end:\s*([\d.]+)", detect.stderr)]

    content_start = 0.0
    # Если самая первая найденная тишина начинается почти с нулевой отметки —
    # значит, в начале файла реально есть тишина, обрезаем до её конца.
    if starts and starts[0] < 0.2:
        content_start = ends[0] if ends else 0.0
    content_end = full_duration
    for start, end in zip(starts, ends):
        if end >= full_duration - 0.5:
            content_end = start

    return content_start, content_end


# НОВОЕ: режет ОДИН длинный файл (например, экспортированный из Suno Studio
# как Full Song с паузами тишины между треками) на отдельные куски по этим
# паузам. Возвращает список путей к нарезанным кускам, уже пронумерованных
# по порядку (0, 1, 2...), чтобы дальше они шли в ту же самую сборку, что и
# треки из ZIP.
def split_by_silence(input_path, work_dir, noise_threshold="-40dB", min_silence_duration=1.5, split_dir_name="split_tracks"):
    detect = subprocess.run(
        [FFMPEG_BIN, "-i", input_path, "-af",
         f"silencedetect=noise={noise_threshold}:d={min_silence_duration}",
         "-f", "null", "-"],
        capture_output=True, text=True
    )
    starts = [float(m) for m in re.findall(r"silence_start:\s*([\d.]+)", detect.stderr)]
    ends = [float(m) for m in re.findall(r"silence_end:\s*([\d.]+)", detect.stderr)]

    full_duration_probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", input_path],
        capture_output=True, text=True
    )
    full_duration = float(full_duration_probe.stdout.strip())

    # Границей между треками считаем только паузу СТРОГО ВНУТРИ файла —
    # не у самого начала и не у самого конца. Пауза у края файла — это не
    # граница между двумя треками, а обычная ведущая/хвостовая тишина
    # (например, "паддинг" тишиной до длины самого длинного трека, когда
    # стемы экспортируются из мультитрека Suno одинаковой длины) — её уже
    # отдельно подрезает get_content_bounds ниже по конвейеру. Если считать
    # её границей и здесь, каждый обычный отдельный трек с таким хвостом
    # ошибочно резался бы на две части: сам трек и лишний кусок тишины.
    boundaries = [0.0]
    for s, e in zip(starts, ends):
        if s < 0.2 or e >= full_duration - 0.5:
            continue
        boundaries.append((s + e) / 2)
    boundaries.append(full_duration)

    # split_dir_name даёт каждому исходному файлу свою отдельную подпапку —
    # без этого при разбивке НЕСКОЛЬКИХ файлов подряд (см. ниже) их куски
    # с одинаковыми именами "0_track.wav", "1_track.wav" затирали бы друг
    # друга в одной общей папке.
    split_dir = os.path.join(work_dir, split_dir_name)
    os.makedirs(split_dir, exist_ok=True)
    paths = []
    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]
        out_path = os.path.join(split_dir, f"{i}_track.wav")
        run_ffmpeg(["-i", input_path, "-ss", str(start), "-to", str(end), "-c", "copy", out_path])
        paths.append(out_path)
    return paths


# НОВОЕ: раньше разбивка по тишине срабатывала только если в папке был
# РОВНО ОДИН файл — не подходило для сценария "несколько файлов-кластеров,
# в каждом склеено по несколько треков" (например, автор объединяет треки
# из Suno Studio по 5 штук за раз, чтобы обойти лимит на длину экспорта).
# Теперь разбивка по тишине применяется к КАЖДОМУ файлу отдельно и результаты
# склеиваются по порядку — обычный отдельный трек без внутренних пауз просто
# вернётся как один кусок, ничего не меняя, а кластер из нескольких треков
# правильно разрежется на составляющие. Порядок между самими файлами
# по-прежнему определяет natural_sort_key (имя файла/номер в нём).
def split_all_by_silence(tracks_raw, work_dir):
    result = []
    for i, raw_path in enumerate(tracks_raw):
        result.extend(split_by_silence(raw_path, work_dir, split_dir_name=f"split_{i}"))
    return result


def build_audio_track(audio_source_url, work_dir, target_lufs=-16, fade_in_seconds=1.5, fade_out_seconds=3, gap_seconds=0, loop_count=1, mix_seconds=None):
    extract_dir = resolve_audio_tracks_dir(audio_source_url, work_dir)

    tracks_raw = sorted(
        glob.glob(os.path.join(extract_dir, "*.mp3"))
        + glob.glob(os.path.join(extract_dir, "*.wav")),
        key=natural_sort_key
    )

    tracks_raw = split_all_by_silence(tracks_raw, work_dir)

    if not tracks_raw:
        raise RuntimeError("No .mp3/.wav files found in ZIP or folder")

    trimmed_dir = os.path.join(work_dir, "trimmed")
    os.makedirs(trimmed_dir, exist_ok=True)
    tracks = []
    durations = []
    for i, raw_path in enumerate(tracks_raw):
        content_start, content_end = get_content_bounds(raw_path)
        trimmed_path = os.path.join(trimmed_dir, f"track_{i}.wav")
        run_ffmpeg(["-i", raw_path, "-ss", str(content_start), "-to", str(content_end), "-c", "copy", trimmed_path])
        tracks.append(trimmed_path)
        durations.append(content_end - content_start)

    # НОВОЕ (09.09): фейд-ин и фейд-аут у КАЖДОГО трека без исключений — в том
    # числе у самого первого и самого последнего. Раньше первый/последний были
    # особым случаем — но это усложняло зацикливание: при повторе трек-листа
    # стык между концом и новым началом оставался жёстким. Единая логика для
    # всех треков решает обе задачи сразу, без особых случаев.
    faded_dir = os.path.join(work_dir, "faded")
    os.makedirs(faded_dir, exist_ok=True)
    faded_tracks = []
    for i, (trimmed_path, duration) in enumerate(zip(tracks, durations)):
        fade_out_start = max(0, duration - fade_out_seconds)
        # НОВОЕ: нормализуем громкость КАЖДОГО трека отдельно, до склейки —
        # раньше loudnorm применялся один раз на весь уже склеенный файл, и
        # если один трек от Suno был от природы громче другого, единая
        # цифра на выходе не убирала эту разницу внутри самого файла, только
        # средний уровень по всей дорожке. Нормализация до фейдов и склейки
        # выравнивает треки друг относительно друга, а не только "в среднем".
        af_parts = [
            f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
            f"afade=t=in:st=0:d={fade_in_seconds}:curve=log",
            f"afade=t=out:st={fade_out_start}:d={fade_out_seconds}:curve=log",
        ]
        faded_path = os.path.join(faded_dir, f"faded_{i}.wav")
        run_ffmpeg(["-i", trimmed_path, "-af", ",".join(af_parts), faded_path])
        faded_tracks.append(faded_path)

    # НОВОЕ (09.09): два взаимоисключающих режима склейки, оба на уже
    # готовых (сглаженных) треках — MIX (mix_seconds задан) просто честно
    # складывает уже готовые сигналы внахлёст, без какой-либо повторной кривой
    # затухания поверх. GAP (по умолчанию) — ставит треки друг за другом,
    # с паузой между ними, если gap_seconds > 0.
    use_mix = bool(mix_seconds and mix_seconds > 0)

    gap_path = None
    if not use_mix and gap_seconds > 0:
        gap_path = os.path.join(work_dir, "gap_silence.wav")
        run_ffmpeg([
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-t", str(gap_seconds),
            gap_path
        ])

    def join_tracks(pieces, piece_durations, prefix):
        if len(pieces) == 1:
            return pieces[0]
        current = pieces[0]
        current_duration = piece_durations[0]
        for i in range(1, len(pieces)):
            nxt = pieces[i]
            nxt_duration = piece_durations[i]
            step_out = os.path.join(work_dir, f"{prefix}_{i}.wav")
            if use_mix:
                delay_ms = int(round(max(0, current_duration - mix_seconds) * 1000))
                run_ffmpeg([
                    "-i", current, "-i", nxt,
                    "-filter_complex",
                    f"[1:a]adelay={delay_ms}|{delay_ms}[b_delayed];"
                    f"[0:a][b_delayed]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[out]",
                    "-map", "[out]",
                    step_out
                ])
                current_duration = max(0, current_duration - mix_seconds) + nxt_duration
            elif gap_path:
                run_ffmpeg([
                    "-i", current, "-i", gap_path, "-i", nxt,
                    "-filter_complex", "concat=n=3:v=0:a=1",
                    step_out
                ])
                current_duration = current_duration + gap_seconds + nxt_duration
            else:
                run_ffmpeg([
                    "-i", current, "-i", nxt,
                    "-filter_complex", "concat=n=2:v=0:a=1",
                    step_out
                ])
                current_duration = current_duration + nxt_duration
            current = step_out
        return current

    concat_out = os.path.join(work_dir, "audio_concat.wav")
    result_path = join_tracks(faded_tracks, durations, "audio_step")
    shutil.copy(result_path, concat_out)

    compressed_out = os.path.join(work_dir, "audio_compressed.wav")
    run_ffmpeg([
        "-i", concat_out,
        "-af", "acompressor=threshold=-20dB:attack=10:release=100:ratio=3:makeup=1",
        compressed_out
    ])

    normalized_out = os.path.join(work_dir, "audio_final.wav")
    run_ffmpeg([
        "-i", compressed_out,
        "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
        normalized_out
    ])

    # НОВОЕ (09.09): зацикливание готового прохода — просто повторяем готовый
    # файл сам с собой нужное число раз, тем же способом склейки.
    final_out = normalized_out
    if loop_count > 1:
        probe_single = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "csv=p=0", normalized_out],
            capture_output=True, text=True
        )
        single_pass_duration = float(probe_single.stdout.strip())
        final_out = join_tracks([normalized_out] * loop_count, [single_pass_duration] * loop_count, "audio_loop")

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration", "-of", "csv=p=0", final_out],
        capture_output=True, text=True
    )
    duration = float(probe.stdout.strip())

    return final_out, duration


# НОВОЕ: измеряет реальную громкость уже готового файла по стандарту EBU R128
# (то же самое, чем измеряют вещательные студии) — не применяет ничего, а
# просто СМОТРИТ и предупреждает в логах сервера, если итоговая громкость
# заметно разъехалась с целевой. Это страховка "на всякий случай", не
# блокирует сборку — если она не сработает идеально, видео всё равно соберётся.
def check_brightness(image_path, target_yavg=64.0):
    """Проверяет среднюю яркость картинки (YAVG, шкала 0-255) — не блокирует
    сборку, только предупреждает в логе. Порог специально мягкий, чтобы не
    поднимать ложную тревогу на осознанно тёмных ночных сценах — только на
    том, что заметно темнее разумной нормы для веба."""
    try:
        result = subprocess.run(
            ["ffprobe", "-f", "lavfi", "-i", f"movie={image_path},signalstats",
             "-show_entries", "frame_tags=lavfi.signalstats.YAVG",
             "-of", "csv=p=0", "-v", "quiet"],
            capture_output=True, text=True
        )
        yavg = float(result.stdout.strip())
        diff = target_yavg - yavg
        if diff > 20:
            print(f"[brightness-check] ВНИМАНИЕ: яркость кадра {yavg:.0f}, заметно темнее нормы (~{target_yavg:.0f})")
        else:
            print(f"[brightness-check] ок: {yavg:.0f} (норма ~{target_yavg:.0f})")
    except Exception as e:
        print(f"[brightness-check] не удалось проверить: {e}")


def check_loudness(audio_path, target_lufs):
    try:
        result = subprocess.run(
            [FFMPEG_BIN, "-i", audio_path, "-af", "ebur128", "-f", "null", "-"],
            capture_output=True, text=True
        )
        match = re.search(r"I:\s*(-?[\d.]+)\s*LUFS", result.stderr)
        if match:
            measured = float(match.group(1))
            diff = abs(measured - target_lufs)
            if diff > 2.0:
                print(f"[loudness-check] ВНИМАНИЕ: цель {target_lufs} LUFS, реально получилось {measured} LUFS (разница {diff:.1f})")
            else:
                print(f"[loudness-check] ок: {measured} LUFS (цель {target_lufs})")
    except Exception as e:
        print(f"[loudness-check] не удалось измерить: {e}")


def fx_zoom(value, duration_frames):
    speed = float(value) if value else 0.0015
    return f"zoompan=z='min(zoom+{speed},1.5)':d={duration_frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}"


def fx_vinylnoise(value):
    return "highpass=f=200,lowpass=f=4000,volume=0.05"


EFFECT_VIDEO_REGISTRY = {
    "fx_ZoomEnabled": fx_zoom,
}
EFFECT_AUDIO_REGISTRY = {
    "fx_VinylNoise": fx_vinylnoise,
}

def collect_fx_filters(data, registry, *args):
    filters = []
    for key, value in data.items():
        if not key.startswith("fx_"):
            continue
        if not value:
            continue
        if key in registry:
            filters.append(registry[key](value, *args) if args else registry[key](value))
        else:
            print(f"[video-assembler] unknown effect '{key}', skipping")
    return filters


@app.route("/assemble", methods=["POST"])
def assemble():
    data = request.json
    project_id = data.get("projectId", "unknown")
    image_url = data["imageUrl"]
    audio_zip_url = data["audioZipUrl"]
    overlay_text = data.get("overlayText", "")
    overlay_position = data.get("overlayPosition", "center")

    work_dir = tempfile.mkdtemp(prefix=f"assemble_{project_id}_")
    try:
        image_path = download_file(image_url, os.path.join(work_dir, "image.jpg"))

        target_lufs = int(data.get("targetLUFS", -16))
        target_brightness = float(data.get("targetBrightness", 64))
        check_brightness(image_path, target_brightness)
        fade_in_seconds = float(data.get("fadeInSeconds", 1.5))
        fade_out_seconds = float(data.get("fadeOutSeconds", 3))
        gap_seconds = float(data.get("gapSeconds", 0))
        loop_count = int(data.get("loopCount", 1))
        audio_path, duration = build_audio_track(
            audio_zip_url, work_dir,
            target_lufs=target_lufs,
            fade_in_seconds=fade_in_seconds,
            fade_out_seconds=fade_out_seconds,
            gap_seconds=gap_seconds,
            loop_count=loop_count,
        )

        # НОВОЕ: проверка громкости готового файла — не блокирует сборку,
        # просто пишет в лог сервера, если что-то разъехалось с целью.
        check_loudness(audio_path, target_lufs)

        fps = 5
        duration_frames = int(duration * fps)

        video_filters = collect_fx_filters(data, EFFECT_VIDEO_REGISTRY, duration_frames)
        if not video_filters:
            video_filters.append(f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}")

        overlay_margin = int(data.get("overlayMargin", 60))
        overlay_positions = build_overlay_positions(overlay_margin)
        pos = overlay_positions.get(overlay_position, overlay_positions["center"])
        safe_text = overlay_text.replace("'", "\\'").replace(":", "\\:")

        font_name = data.get("overlayFont", "Courier Prime")
        font_path = FONT_MAP.get(font_name, DEFAULT_FONT_PATH)
        font_size = data.get("overlaySize", "44")
        font_color = data.get("overlayColor", "#FFFFFF").lstrip("#")

        # НОВОЕ: было только "if(lt(t,15),1,if(lt(t,18),(18-t)/3,0))" — то есть
        # мгновенное появление, потом 3 секунды угасания. Добавлено
        # симметричное появление: первые 3 секунды текст плавно проявляется,
        # с 3 по 15 держится на полной видимости, с 15 по 18 гаснет.
        overlay_alpha = (
            "if(lt(t,3),t/3,"
            "if(lt(t,15),1,"
            "if(lt(t,18),(18-t)/3,0)))"
        )
        shadow_color = data.get("overlayShadow", "E7DFCF").lstrip("#")
        drawtext = (
            f"drawtext=text='{safe_text}':fontfile={font_path}:"
            f"fontcolor=0x{font_color}:fontsize={font_size}:{pos}:alpha='{overlay_alpha}':"
            f"shadowcolor=0x{shadow_color}@0.6:shadowx=2:shadowy=2:enable='between(t,0,18)'"
        )

        # НОВОЕ: плавное появление/затухание ВСЕГО готового видео целиком
        # (не между треками внутри — то уже есть через acrossfade). Первые
        # и последние 0.5 секунды кадра — из чёрного и в чёрный.
        video_fade = f"fade=t=in:st=0:d=0.5,fade=t=out:st={duration-0.5}:d=0.5"

        video_chain = ",".join(video_filters + [drawtext, video_fade])

        audio_filters = collect_fx_filters(data, EFFECT_AUDIO_REGISTRY)
        # НОВОЕ: та же логика fade, но для звука — тихий, плавный вход/выход
        # у всей аудиодорожки целиком.
        audio_fade = f"afade=t=in:st=0:d=0.5,afade=t=out:st={duration-0.5}:d=0.5"
        audio_chain = ",".join(audio_filters + [audio_fade]) if audio_filters else audio_fade

        output_path = os.path.join(work_dir, f"{project_id}.mp4")
        run_ffmpeg([
            "-loop", "1", "-i", image_path,
            "-i", audio_path,
            "-filter_complex",
            f"[0:v]{video_chain}[v];[1:a]{audio_chain}[a]",
            "-map", "[v]", "-map", "[a]",
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-r", str(fps),
            output_path
        ])

        # НОВОЕ: вырезаем один кадр в момент полной видимости оверлея
        # (середина стабильного окна 3-15 сек — берём 9-ю секунду, с запасом
        # от обоих краёв fade) и сохраняем его ОТДЕЛЬНО, в постоянную папку,
        # не в work_dir — чтобы файл дожил до момента, когда n8n придёт за
        # ним уже ПОСЛЕ того, как получит и обработает само видео.
        thumbnail_path = os.path.join(THUMBNAIL_DIR, f"{project_id}.jpg")
        try:
            run_ffmpeg(["-ss", "9", "-i", output_path, "-frames:v", "1", thumbnail_path])
        except Exception as thumb_error:
            print(f"[thumbnail] не удалось вырезать кадр для {project_id}: {thumb_error}")

        return send_file(output_path, mimetype="video/mp4",
                          as_attachment=True, download_name=f"{project_id}.mp4")

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# НОВОЕ: отдельный, маленький маршрут — n8n вызывает его ПОСЛЕ того, как
# видео уже загружено на YouTube, чтобы забрать заранее подготовленную
# обложку и отправить её отдельным запросом через thumbnails.set.
@app.route("/thumbnail/<project_id>", methods=["GET"])
def get_thumbnail(project_id):
    thumbnail_path = os.path.join(THUMBNAIL_DIR, f"{project_id}.jpg")
    if not os.path.exists(thumbnail_path):
        return jsonify({"error": "thumbnail not found, may not have been generated yet"}), 404
    return send_file(thumbnail_path, mimetype="image/jpeg")


@app.route("/health", methods=["GET"])
def health():
    try:
        run_ffmpeg(["-version"])
        return jsonify({"status": "ok", "ffmpeg": "reachable"})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500


@app.route("/trackinfo", methods=["POST"])
def trackinfo():
    data = request.json
    audio_zip_url = data["audioZipUrl"]

    work_dir = tempfile.mkdtemp(prefix="trackinfo_")
    try:
        extract_dir = resolve_audio_tracks_dir(audio_zip_url, work_dir)
        tracks_raw = sorted(
            glob.glob(os.path.join(extract_dir, "*.mp3"))
            + glob.glob(os.path.join(extract_dir, "*.wav")),
            key=natural_sort_key
        )

        tracks_raw = split_all_by_silence(tracks_raw, work_dir)

        if not tracks_raw:
            return jsonify({"error": "No .mp3/.wav files found in ZIP or folder"}), 400

        mix_seconds_raw = data.get("mixSeconds")
        MIX_SECONDS = float(mix_seconds_raw) if mix_seconds_raw else None
        GAP_SECONDS = float(data.get("gapSeconds", 0))
        result = []
        cumulative_start = 0.0

        for i, raw_path in enumerate(tracks_raw):
            duration = get_real_duration(raw_path)
            filename = os.path.splitext(os.path.basename(raw_path))[0]

            result.append({
                "index": i,
                "filename": filename,
                "durationSeconds": round(duration, 2),
                "startSeconds": round(cumulative_start, 2)
            })

            if i < len(tracks_raw) - 1:
                if MIX_SECONDS and MIX_SECONDS > 0:
                    cumulative_start += duration - MIX_SECONDS
                else:
                    cumulative_start += duration + GAP_SECONDS
            else:
                cumulative_start += duration

        return jsonify({"tracks": result, "totalDurationSeconds": round(cumulative_start, 2)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8100)
