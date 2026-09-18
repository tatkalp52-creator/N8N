import os
import re
import json
import subprocess
import tempfile
import zipfile
import shutil
import glob
import requests
import gdown
from flask import Flask, request, jsonify, send_file, after_this_request

app = Flask(__name__)

# НОВОЕ: строка-маркер, которую нужно вручную поднимать при каждом
# значимом изменении этого файла. Смысл не в самой строке, а в /health —
# сверив то, что реально отвечает работающий сервер, с тем, что стоит
# здесь в git на нужной ветке, можно за один curl проверить, действительно
# ли на сервере сейчас код из репозитория, а не что-то, что туда попало
# в обход обычной сборки (см. историю с ручным wget поверх persistent
# storage при восстановлении после падения 17.09) — без блуждания по SSH
# и логам, когда есть подозрение на рассинхронизацию.
ASSEMBLER_VERSION = "2026-09-18-audio-investigation"

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
    "Pengui Hand": "/usr/share/fonts/truetype/pengui-hand/PenguiHand.ttf",
}
DEFAULT_FONT_PATH = FONT_MAP["Pengui Hand"]


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
        # НОВОЕ: якорь не от края кадра, а от вертикальных линий, за которые
        # текст не заходит (кадр мысленно поделён по горизонтали). Раньше
        # линии стояли на третях (2/3 центра под объект) — с длинными
        # словами при крупном шрифте текст почти упирался в край кадра.
        # Сдвинуто на пятые: центральная зона под объект уже (1/5 вместо
        # 1/3), а по бокам, наоборот, больше места на рост текста (2/5
        # вместо 1/3 с каждой стороны). "left" — правый край текста
        # упирается в левую линию, текст растёт влево. "right" — левый
        # край текста упирается в правую линию, текст растёт вправо.
        # margin тут больше не участвует.
        "left":          "x=2*w/5-text_w:y=(h-text_h)/2",
        "right":         "x=3*w/5:y=(h-text_h)/2",
    }


def measure_text_width(text, font_path, font_size):
    """Настоящая ширина строки в пикселях для КОНКРЕТНОГО шрифта и размера —
    нужна только для одного решения (влезает ли оверлей в одну строку или
    его надо разбить на две), а не для самого позиционирования на кадре
    (это по-прежнему делает сам ffmpeg через text_w в drawtext). Импорт
    Pillow — намеренно здесь, а не в начале файла: раньше падение всего
    сборщика целиком из-за отсутствия Pillow означало, что и сборка
    видео, вообще не связанная с оверлеем, переставала работать тоже.
    Теперь при отсутствии Pillow ломается только решение про перенос
    строки (см. вызов ниже), а не весь сервис."""
    from PIL import ImageFont
    font = ImageFont.truetype(font_path, int(round(float(font_size))))
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0]


def build_overlay_drawtext(overlay_text, position, font_path, font_size,
                            font_color, shadow_color, shadow_opacity,
                            overlay_alpha, margin=60):
    """Собирает список (shadow_filters, main_filters) для оверлея — либо
    одну строку как раньше, либо, если текст не помещается в отведённую
    по бокам зону (см. build_overlay_positions), автоматический стек из
    двух строк: правило канала — оверлей всегда из двух слов, первое
    короткое ("Just" и т.п.). Обе строки прижимаются К ОДНОЙ И ТОЙ ЖЕ
    вертикальной линии тем же краем, каким прижималась бы одна строка —
    короткое слово просто "висит" ближе к линии, а не гуляет само по
    себе, поэтому раскладка предсказуема независимо от длины слова."""
    text = overlay_text.strip()
    if not text:
        return [], []

    positions = build_overlay_positions(margin)
    pos = positions.get(position, positions["center"])

    def esc(t):
        return t.replace("'", "\\'").replace(":", "\\:")

    words = text.split(" ", 1)
    zone_width = (2 * VIDEO_WIDTH / 5 - 40) if position in ("left", "right") else None
    needs_stack = False
    if len(words) == 2 and zone_width is not None:
        try:
            needs_stack = measure_text_width(text, font_path, font_size) > zone_width
        except Exception as e:
            print(f"[overlay] не удалось измерить ширину текста, оставляю одну строку: {e}")

    def layer(line_text, xy_part, color, opacity=None):
        color_part = f"0x{color}@{opacity}" if opacity is not None else f"0x{color}"
        return (
            f"drawtext=text='{esc(line_text)}':fontfile={font_path}:"
            f"fontcolor={color_part}:fontsize={font_size}:{xy_part}:"
            f"alpha='{overlay_alpha}':enable='between(t,0,18)'"
        )

    if not needs_stack:
        return [layer(text, pos, shadow_color, shadow_opacity)], [layer(text, pos, font_color)]

    # НОВОЕ: стек из двух строк. Межстрочный интервал — 0.875 от размера
    # шрифта (подобрано глазами на тесте, при 120px это ~105px), обе
    # строки центрируются как единый блок по вертикали кадра.
    line1, line2 = words[0], words[1]
    size = float(font_size)
    line_pitch = round(size * 0.875)
    block_h = line_pitch + size
    y1 = round((VIDEO_HEIGHT - block_h) / 2)
    y2 = y1 + line_pitch

    if position == "left":
        x_expr = "2*w/5-text_w"
    elif position == "right":
        x_expr = "3*w/5"
    else:
        x_expr = "(w-text_w)/2"

    xy1 = f"x={x_expr}:y={y1}"
    xy2 = f"x={x_expr}:y={y2}"

    shadow_filters = [
        layer(line1, xy1, shadow_color, shadow_opacity),
        layer(line2, xy2, shadow_color, shadow_opacity),
    ]
    main_filters = [
        layer(line1, xy1, font_color),
        layer(line2, xy2, font_color),
    ]
    return shadow_filters, main_filters


def natural_sort_key(path, zip_order=None):
    """Сортирует по числу, стоящему в НАЧАЛЕ имени файла, как по настоящему числу,
    а не как по тексту. Studio-номер студии (0, 1, 2 ... 19) всегда встаёт первым
    в имени файла — именно по нему и сортируем. Если числа в начале нет,
    но известен порядок файлов внутри исходного zip-архива (см. zip_order) —
    используем его. Если неизвестен и он — такой файл уходит в конец списка,
    отсортированный по алфавиту.

    Suno Studio при скачивании треков по одному (поставил трек на
    дорожку — скачал — убрал — поставил следующий) называет все файлы
    одинаково "01", но добавляет диапазон времени в скобках, например
    "01 [9m33s-12m50s].wav" — начало этого диапазона растёт с каждым
    следующим скачанным треком (дорожка в Studio продвигается вперёд), и
    поэтому надёжно отражает порядок скачивания, даже когда сам "01"
    у всех одинаковый. Если такой диапазон есть в имени — сортируем по
    его началу (в секундах), это приоритетнее обычного числа в начале
    имени.

    zip_order (Suno стемы, скачанные одним архивом сразу): словарь
    {имя_файла: позиция в архиве} — архив хранит записи в том порядке,
    в котором дорожки были в нём сложены, независимо от того, как эти
    дорожки названы (не 1/2/3 и не А/Б/В). Используется, только если ни
    временной диапазон, ни числовой префикс в имени не нашлись — так
    работающие правила выше не трогаем."""
    filename = os.path.basename(path)
    range_match = re.search(r"\[(\d+)m(\d+)s-", filename)
    if range_match:
        minutes, seconds = int(range_match.group(1)), int(range_match.group(2))
        return (0, minutes * 60 + seconds, filename)
    match = re.match(r"^(\d+)", filename)
    if match:
        return (1, int(match.group(1)), filename)
    if zip_order and filename in zip_order:
        return (2, zip_order[filename], filename)
    return (3, 0, filename)


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
        # Порядок файлов в папке Google Drive ничего не гарантирует —
        # ключей для zip_order тут нет.
        return extract_dir, None

    zip_path = download_file(source_url, os.path.join(work_dir, "audio.zip"))
    with zipfile.ZipFile(zip_path, "r") as z:
        # namelist() отдаёт записи в том порядке, в котором они реально лежат
        # в архиве (порядок добавления), а не по алфавиту — это тот самый
        # "как в папке разложено, так и собрать" порядок для стемов без
        # цифр/букв в имени.
        zip_order = {os.path.basename(name): i for i, name in enumerate(z.namelist())}
        z.extractall(extract_dir)
    return extract_dir, zip_order


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


# НОВОЕ: раньше и /trackinfo (тайм-коды в описании), и сама сборка отдельно
# считали длину трека по меткам тишины (content_end - content_start) — это
# ТЕОРЕТИЧЕСКОЕ число, а не реальная длина файла после обрезки. При обрезке
# с перекодированием (без "-c copy") реальная длина готового файла может на
# доли секунды отличаться от теоретической — по отдельности незаметно, но
# на кластере из ~20 треков расхождение накапливается трек за треком и к
# последней границе (там, где ставится метка "Repeat") набегает уже на
# секунды — отсюда был слышен хвост предыдущего трека при переходе на повтор.
# Теперь оба места вызывают ОДНУ и ту же функцию и используют РЕАЛЬНО
# измеренную (через ffprobe) длину уже обрезанного файла — расходиться
# больше нечему, потому что источник числа один и тот же код.
def trim_to_content(input_path, out_path, noise_threshold="-40dB", min_silence_duration=1.0):
    content_start, content_end = get_content_bounds(input_path, noise_threshold, min_silence_duration)
    run_ffmpeg(["-i", input_path, "-ss", str(content_start), "-to", str(content_end), out_path])
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out_path],
        capture_output=True, text=True
    )
    real_duration = float(probe.stdout.strip())
    return real_duration


# НОВОЕ: режет ОДИН длинный файл (например, экспортированный из Suno Studio
# как Full Song с паузами тишины между треками) на отдельные куски по этим
# паузам. Возвращает список путей к нарезанным кускам, уже пронумерованных
# по порядку (0, 1, 2...), чтобы дальше они шли в ту же самую сборку, что и
# треки из ZIP.
def split_by_silence(input_path, work_dir, noise_threshold="-40dB", min_silence_duration=1.5, split_dir_name="split_tracks", min_segment_seconds=119):
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
        # НОВОЕ: короткий громкий обрывок (щелчок, обрезанный край записи,
        # шум) между двумя настоящими паузами тишины раньше засчитывался
        # как отдельный "трек" наравне с настоящими — попадал в сборку
        # своим собственным куском и своим таймкодом. Реальные треки автор
        # никогда не берёт короче ~2 минут, так что всё, что короче этого
        # порога, отбрасываем как шумовой артефакт, а не как трек.
        if end - start < min_segment_seconds:
            continue
        out_path = os.path.join(split_dir, f"{i}_track.wav")
        # НОВОЕ: было "-c copy" — стрим-копия режет только по границе кадра
        # кодека, а не по точной секунде; для сжатых форматов (mp3 и т.п.)
        # это даёт неточный, часто щёлкающий рез прямо на границе. Без
        # "-c copy" ffmpeg честно перекодирует кусок в PCM — рез становится
        # сэмпл-точным, без щелчка на стыке.
        run_ffmpeg(["-i", input_path, "-ss", str(start), "-to", str(end), out_path])
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


# НОВОЕ: первый проход двухпроходного loudnorm — только измеряет реальные
# параметры входного файла, ничего не пишет. Однопроходный режим (как было
# раньше) сам оценивает эти значения "на лету" и может заметно промахиваться
# мимо цели — от этого разные треки, формально нормализованные к одной и той
# же цифре в LUFS, всё равно звучали неровно относительно друг друга.
# Двухпроходный режим с measured_* и linear=true — стандартная рекомендация
# самого ffmpeg для точной, профессиональной нормализации.
def measure_loudnorm(input_path, target_lufs):
    result = subprocess.run(
        [FFMPEG_BIN, "-i", input_path, "-af",
         f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11:print_format=json",
         "-f", "null", "-"],
        capture_output=True, text=True
    )
    match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", result.stderr)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except (ValueError, KeyError):
        return None


def loudnorm_filter(input_path, target_lufs):
    measured = measure_loudnorm(input_path, target_lufs)
    if not measured:
        # Не удалось измерить — откатываемся на однопроходный режим, лучше
        # неидеальная нормализация, чем упавшая сборка. НО именно этот режим
        # (динамический, покадровый) раньше уже давал слышимую зернистость/
        # шорох (см. комментарий у финального loudnorm ниже) — если он вдруг
        # снова начинает подставляться молча, эту деградацию раньше никак
        # нельзя было заметить, кроме как на слух в готовом видео. Печатаем
        # явно в лог сервера, чтобы это было видно сразу, а не только по факту.
        print(f"[loudnorm] измерение не удалось для {input_path} — откат на однопроходный динамический режим")
        return f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11"
    return (
        f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11:"
        f"measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:"
        f"measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}:"
        "linear=true"
    )


def build_audio_track(audio_source_url, work_dir, target_lufs=-16, fade_in_seconds=1.5, fade_out_seconds=3, gap_seconds=0, loop_count=None, mix_seconds=None):
    extract_dir, zip_order = resolve_audio_tracks_dir(audio_source_url, work_dir)

    tracks_raw = sorted(
        glob.glob(os.path.join(extract_dir, "*.mp3"))
        + glob.glob(os.path.join(extract_dir, "*.wav")),
        key=lambda p: natural_sort_key(p, zip_order)
    )

    tracks_raw = split_all_by_silence(tracks_raw, work_dir)

    if not tracks_raw:
        raise RuntimeError("No .mp3/.wav files found in ZIP or folder")

    trimmed_dir = os.path.join(work_dir, "trimmed")
    os.makedirs(trimmed_dir, exist_ok=True)
    tracks = []
    durations = []
    for i, raw_path in enumerate(tracks_raw):
        trimmed_path = os.path.join(trimmed_dir, f"track_{i}.wav")
        # НОВОЕ: то же самое, что и в split_by_silence — без "-c copy" рез
        # становится сэмпл-точным, а не привязанным к границе кадра кодека.
        # Именно это, судя по всему, было причиной щелчка/резкого обрыва на
        # стыке треков: fade вправду применялся, но накладывался поверх уже
        # испорченного стыка от неточного стрим-копи реза. Реальная (не
        # теоретическая) длина — см. комментарий у trim_to_content выше.
        real_duration = trim_to_content(raw_path, trimmed_path)
        tracks.append(trimmed_path)
        durations.append(real_duration)

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
        # Двухпроходный режим (см. loudnorm_filter выше) — точнее однопроходного.
        af_parts = [
            loudnorm_filter(trimmed_path, target_lufs),
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

    # НОВОЕ (18.09): раньше здесь после склейки стоял ЕЩЁ ОДИН двухпроходный
    # loudnorm (см. историю ниже) — но ffmpeg's loudnorm в двухпроходном
    # linear-режиме молча откатывается на покадровый (нелинейный, "адаптивный")
    # режим, если посчитанное линейное усиление рискует пробить целевой true
    # peak — а на уже склеенном полном файле, где встречаются и тихие, и
    # громкие треки, именно это условие срабатывает регулярно. Адаптивный
    # режим активно "подтягивает" тихие участки к целевой громкости в
    # реальном времени — а фейд-ин и есть намеренно тихий участок: его
    # результат — фейд-ин, который не слышен (звук уже "подтянут" почти
    # к полной громкости почти сразу), и фейд-аут, который кажется длиннее
    # положенного (алгоритм какое-то время тянет угасающий уровень обратно
    # вверх, прежде чем отпустить). Всё это никак не логировалось — при
    # обычном linear=true ffmpeg не предупреждает о таком откате.
    #
    # Чтобы фейды, построенные вручную по кривой выше, не могла испортить
    # никакая последующая адаптивная обработка, здесь применяется не
    # loudnorm, а простая линейная поправка громкости (volume=...dB),
    # посчитанная из той же самой измеренной интегральной громкости — это
    # ровно то же число, которое loudnorm использовал бы для линейного
    # усиления, но без встроенного в фильтр права молча передумать и
    # переключиться на покадровый режим.
    measured = measure_loudnorm(concat_out, target_lufs)
    if measured:
        gain_db = target_lufs - float(measured["input_i"])
    else:
        print(f"[loudnorm] измерение громкости не удалось для {concat_out} — поправка громкости не применяется (0 дБ)")
        gain_db = 0.0
    gain_corrected = os.path.join(work_dir, "audio_gain_corrected.wav")
    run_ffmpeg(["-i", concat_out, "-af", f"volume={gain_db}dB", gain_corrected])

    # НОВОЕ: компрессор и лимитер идут ПОСЛЕДНИМИ, после поправки громкости —
    # раньше лимитер стоял ДО финального loudnorm, то есть громкость могла
    # ещё раз измениться уже после того, как лимитер отработал, и новые пики
    # уже ничем не были защищены от превышения. Теперь лимитер — правда
    # последний шаг перед выходом, гарантированно ловит любые пики независимо
    # от того, что было до него. acompressor (attack=10ms) — резкий транзиент
    # (например, снейр на 2 и 4 долю — характерная черта лофая, которую
    # убирать не нужно) не должен звучать жёстким щелчком; alimiter — честный
    # лимитер с lookahead и быстрой атакой (5мс) для тех же коротких пиков.
    normalized_out = os.path.join(work_dir, "audio_final.wav")
    run_ffmpeg([
        "-i", gain_corrected,
        "-af", "acompressor=threshold=-20dB:attack=10:release=100:ratio=3:makeup=1,alimiter=limit=0.95:attack=5:release=50",
        normalized_out
    ])

    probe_single = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration", "-of", "csv=p=0", normalized_out],
        capture_output=True, text=True
    )
    single_pass_duration = float(probe_single.stdout.strip())

    # НОВОЕ (13.09): если число циклов не задано вручную из таблицы — решаем
    # сами по реальной длине одного прохода: короче часа, значит, зациклится
    # дважды, час и длиннее — оставляем как есть. Явно заданное автором число
    # (в том числе 1) всегда в приоритете и это решение не трогает.
    if loop_count is None:
        loop_count = 2 if single_pass_duration < 3600 else 1

    # НОВОЕ (09.09): зацикливание готового прохода — просто повторяем готовый
    # файл сам с собой нужное число раз, тем же способом склейки.
    final_out = normalized_out
    if loop_count > 1:
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
    """НОВОЕ: раньше только предупреждала в серверном логе, который никто не
    читает, — картинка так и оставалась темнее цели. Теперь при заметном
    отставании реально приподнимает яркость (eq=brightness, мягкий сдвиг,
    не пересвечивая), а не просто жалуется в логи. Порог на срабатывание
    специально мягкий, чтобы не трогать осознанно тёмные ночные сцены —
    только то, что заметно темнее разумной нормы для веба."""
    try:
        result = subprocess.run(
            ["ffprobe", "-f", "lavfi", "-i", f"movie={image_path},signalstats",
             "-show_entries", "frame_tags=lavfi.signalstats.YAVG",
             "-of", "csv=p=0", "-v", "quiet"],
            capture_output=True, text=True
        )
        yavg = float(result.stdout.strip())
    except Exception as e:
        print(f"[brightness-check] не удалось проверить: {e}")
        return
    diff = target_yavg - yavg
    if diff <= 20:
        print(f"[brightness-check] ок: {yavg:.0f} (норма ~{target_yavg:.0f})")
        return
    # eq=brightness — плоский сдвиг в диапазоне -1..1 (0 = без изменений,
    # 1 = белый), в долях от полной шкалы 0-255. Ограничиваем сверху, чтобы
    # даже сильно тёмная сцена приподнималась мягко, а не резко пересвечивалась
    # за один проход.
    boost = min(diff / 255.0, 0.12)
    corrected_path = image_path + ".brightened.jpg"
    try:
        run_ffmpeg(["-i", image_path, "-vf", f"eq=brightness={boost:.4f}", corrected_path])
        os.replace(corrected_path, image_path)
        print(f"[brightness-check] было {yavg:.0f} (норма ~{target_yavg:.0f}) — приподняли на {boost:.3f}")
    except Exception as e:
        print(f"[brightness-check] ВНИМАНИЕ: яркость {yavg:.0f} заметно ниже нормы (~{target_yavg:.0f}), но коррекция не удалась: {e}")


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

    # НОВОЕ: раньше work_dir никогда не удалялся — ни при успехе, ни при
    # ошибке, ни если клиент (n8n) отваливался по таймауту, пока сборка ещё
    # шла. За недели тестов это тихо съело почти весь диск (десятки ГБ
    # брошенных временных файлов). after_this_request чистит папку уже
    # после того, как ответ клиенту полностью сформирован/отправлен —
    # безопасно даже если сама отправка не удалась, потому что клиент
    # успел отключиться first.
    @after_this_request
    def cleanup(response):
        shutil.rmtree(work_dir, ignore_errors=True)
        return response

    try:
        image_path = download_file(image_url, os.path.join(work_dir, "image.jpg"))

        target_lufs = int(data.get("targetLUFS", -16))
        target_brightness = float(data.get("targetBrightness", 64))
        check_brightness(image_path, target_brightness)
        fade_in_seconds = float(data.get("fadeInSeconds", 1.5))
        fade_out_seconds = float(data.get("fadeOutSeconds", 3))
        gap_seconds = float(data.get("gapSeconds", 0))
        loop_count_raw = data.get("loopCount")
        loop_count = int(loop_count_raw) if loop_count_raw not in (None, "") else None
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

        font_name = data.get("overlayFont")
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

        # НОВОЕ: тень раньше была жёсткой копией текста со сдвигом на 2px
        # (shadowx/shadowy у drawtext не умеет размытие в принципе). Раз
        # шрифт Pengui Hand тонкий и рукописный, жёсткая тень выглядела
        # тяжелее самих букв. Теперь тень — отдельный текстовый слой на
        # прозрачном фоне размером с кадр, размытый по-настоящему через
        # gblur, и только потом наложенный под основной (чёткий) текст.
        # overlayShadowBlur — радиус размытия (sigma), overlayShadowOpacity —
        # непрозрачность тени на пике (до применения общего fade-in/out).
        shadow_color = data.get("overlayShadow", "E7DFCF").lstrip("#")
        shadow_blur = data.get("overlayShadowBlur", "4")
        shadow_opacity = data.get("overlayShadowOpacity", "0.55")

        base_chain = ",".join(video_filters)
        shadow_layers, main_layers = build_overlay_drawtext(
            overlay_text, overlay_position, font_path, font_size,
            font_color, shadow_color, shadow_opacity, overlay_alpha,
            margin=overlay_margin,
        )

        # НОВОЕ: плавное появление/затухание ВСЕГО готового видео целиком
        # (не между треками внутри — то уже есть через acrossfade). Первые
        # и последние 0.5 секунды кадра — из чёрного и в чёрный.
        video_fade = f"fade=t=in:st=0:d=0.5,fade=t=out:st={duration-0.5}:d=0.5"

        if shadow_layers:
            # Собираем отдельный граф: [0:v] -> база со scale/эффектами;
            # прозрачный слой того же размера -> текст тенью (одна или две
            # строки, см. build_overlay_drawtext) -> размытие -> наложение
            # под базу -> резкий текст поверх -> fade всего кадра.
            shadow_chain = ";".join(
                f"[{'shadowbg' if i == 0 else f'sh{i}'}]{f}[sh{i + 1}]"
                for i, f in enumerate(shadow_layers)
            )
            main_chain = ";".join(
                f"[{'with_shadow' if i == 0 else f'm{i}'}]{f}[{f'm{i + 1}' if i + 1 < len(main_layers) else 'texted'}]"
                for i, f in enumerate(main_layers)
            )
            video_chain_graph = (
                f"[0:v]{base_chain}[base];"
                f"color=c=black@0.0:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:d={duration}[shadowbg];"
                f"{shadow_chain};"
                f"[sh{len(shadow_layers)}]gblur=sigma={shadow_blur}[shadow_blurred];"
                f"[base][shadow_blurred]overlay=0:0[with_shadow];"
                f"{main_chain};"
                f"[texted]{video_fade}[v]"
            )
        else:
            video_chain_graph = f"[0:v]{base_chain},{video_fade}[v]"

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
            f"{video_chain_graph};[1:a]{audio_chain}[a]",
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
        return jsonify({"status": "ok", "ffmpeg": "reachable", "version": ASSEMBLER_VERSION})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e), "version": ASSEMBLER_VERSION}), 500


@app.route("/trackinfo", methods=["POST"])
def trackinfo():
    data = request.json
    audio_zip_url = data["audioZipUrl"]

    work_dir = tempfile.mkdtemp(prefix="trackinfo_")

    @after_this_request
    def cleanup(response):
        shutil.rmtree(work_dir, ignore_errors=True)
        return response

    try:
        extract_dir, zip_order = resolve_audio_tracks_dir(audio_zip_url, work_dir)
        tracks_raw = sorted(
            glob.glob(os.path.join(extract_dir, "*.mp3"))
            + glob.glob(os.path.join(extract_dir, "*.wav")),
            key=lambda p: natural_sort_key(p, zip_order)
        )

        tracks_raw = split_all_by_silence(tracks_raw, work_dir)

        if not tracks_raw:
            return jsonify({"error": "No .mp3/.wav files found in ZIP or folder"}), 400

        mix_seconds_raw = data.get("mixSeconds")
        MIX_SECONDS = float(mix_seconds_raw) if mix_seconds_raw else None
        GAP_SECONDS = float(data.get("gapSeconds", 0))
        result = []
        cumulative_start = 0.0
        trackinfo_trim_dir = os.path.join(work_dir, "trackinfo_trim")
        os.makedirs(trackinfo_trim_dir, exist_ok=True)

        for i, raw_path in enumerate(tracks_raw):
            # НОВОЕ: та же функция, что и в реальной сборке (trim_to_content) —
            # значит те же самые реальные числа, а не отдельная теоретическая
            # оценка, которая могла разойтись с тем, что реально соберётся.
            duration = trim_to_content(raw_path, os.path.join(trackinfo_trim_dir, f"{i}.wav"))
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
