import os
import re
import math
import random
import time
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
ASSEMBLER_VERSION = "2026-10-05-snap"

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
                            overlay_alpha, margin=60, line_spacing=0.875, visible_until=18):
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
            width = measure_text_width(text, font_path, font_size)
        except Exception as e:
            # НОВОЕ (27.09): на сервере не оказалось Pillow — ширина не мерилась,
            # надпись оставалась одной строкой и уходила за край кадра. Теперь
            # без Pillow ширина оценивается по числу букв с запасом (у рукописного
            # шрифта канала буква в среднем ~0.37 от размера, берём 0.45): при
            # сомнении лучше перенести на две строки, чем вылезти за край.
            width = len(text) * float(font_size) * 0.45
            print(f"[overlay] Pillow недоступен ({e}), ширина оценена по буквам: {width:.0f}px")
        needs_stack = width > zone_width

    def layer(line_text, xy_part, color, opacity=None):
        color_part = f"0x{color}@{opacity}" if opacity is not None else f"0x{color}"
        return (
            f"drawtext=text='{esc(line_text)}':fontfile={font_path}:"
            f"fontcolor={color_part}:fontsize={font_size}:{xy_part}:"
            f"alpha='{overlay_alpha}':enable='between(t,0,{visible_until})'"
        )

    if not needs_stack:
        return [layer(text, pos, shadow_color, shadow_opacity)], [layer(text, pos, font_color)]

    # НОВОЕ: стек из двух строк. Межстрочный интервал — 0.875 от размера
    # шрифта (подобрано глазами на тесте, при 120px это ~105px), обе
    # строки центрируются как единый блок по вертикали кадра.
    line1, line2 = words[0], words[1]
    size = float(font_size)
    # НОВОЕ (24.09): интервал из таблицы (🎬tmpl_OverlayLineSpacing, доля
    # от размера шрифта); 0.875 — прежнее значение по умолчанию.
    line_pitch = round(size * line_spacing)
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


# НОВОЕ (28.09): треки можно брать прямо из результата блокнота Kaggle
# (чистка шума). Автор отправляет боту ссылку на блокнот вида
# https://www.kaggle.com/code/<автор>/<блокнот> — сервер сам спрашивает
# у Kaggle список файлов последнего запуска (вкладка Output) и скачивает
# оттуда .zip. Ключ Kaggle — переменная KAGGLE_API_TOKEN или файл
# /app/kaggle_token.txt (persistent storage, переживает Restart).
# Сервер ничего не открывает наружу — только сам ходит в Kaggle.
KAGGLE_OUTPUT_API = "https://api.kaggle.com/v1/kernels.KernelsApiService/ListKernelSessionOutput"


def kaggle_token():
    token = os.environ.get("KAGGLE_API_TOKEN", "").strip()
    if not token and os.path.exists("/app/kaggle_token.txt"):
        with open("/app/kaggle_token.txt") as f:
            token = f.read().strip()
    return token


def download_kaggle_output_file(url, dest_path, ext=".zip", prefer=None, must_contain=None):
    m = re.search(r"kaggle\.com/code/([^/?#]+)/([^/?#]+)", url)
    if not m:
        raise RuntimeError(f"Не понимаю ссылку на Kaggle: {url}")
    token = kaggle_token()
    if not token:
        raise RuntimeError("Нет ключа Kaggle: положите его в /app/kaggle_token.txt")
    files, page = [], None
    while True:
        body = {"userName": m.group(1), "kernelSlug": m.group(2)}
        if page:
            body["pageToken"] = page
        r = requests.post(KAGGLE_OUTPUT_API, json=body,
                          headers={"Authorization": f"Bearer {token}"}, timeout=60)
        r.raise_for_status()
        data = r.json()
        files += data.get("files") or []
        page = data.get("nextPageToken")
        if not page:
            break
    zips = [f for f in files if str(f.get("fileName", "")).lower().endswith(ext) and f.get("url")]
    if prefer:
        zips.sort(key=lambda f: os.path.basename(str(f.get("fileName", ""))) != prefer)
    if must_contain:
        zips = [f for f in zips if must_contain in str(f.get("fileName", ""))]
        if not zips:
            raise RuntimeError(f"В результате Kaggle нет архива с меткой {must_contain} — это чужие треки")
    if not zips:
        raise RuntimeError(f"В результате блокнота Kaggle нет {ext} — запуск ещё идёт или упал")
    with requests.get(zips[0]["url"], stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
    return dest_path


def download_kaggle_output_zip(url, dest_path):
    return download_kaggle_output_file(url, dest_path)



# НОВОЕ (01.10): ЧИСТКА В KAGGLE «ПО СОБЫТИЮ». Сервер ничего долго не ждёт:
#   POST /clean_start  — подставляет в код чистки (/app/suno_clean_kaggle.py)
#                        ссылку на треки, способ, метку запуска и адрес, куда
#                        блокнот постучится в конце; запускает блокнот и сразу
#                        отвечает. Если блокнот занят другим выпуском — «занят».
#   POST /clean_status — как там чистка; если готово — сразу забирает архив
#                        с этой меткой к себе (/app/clean_cache), чтобы
#                        следующая чистка в том же блокноте его не затёрла.
# Ждёт и решает n8n (стук блокнота или будильник), сервер только исполняет.
KAGGLE_API = "https://api.kaggle.com/v1/kernels.KernelsApiService/"
CLEAN_CODE_PATH = "/app/suno_clean_kaggle.py"
CLEAN_CACHE_DIR = "/app/clean_cache"
CLEAN_KEEP = 3  # сколько почищенных альбомов держать на диске


def kaggle_call(method, body, timeout=60):
    token = kaggle_token()
    if not token:
        raise RuntimeError("Нет ключа Kaggle: положите его в /app/kaggle_token.txt")
    r = requests.post(KAGGLE_API + method, json=body,
                      headers={"Authorization": f"Bearer {token}"}, timeout=timeout)
    if r.status_code in (401, 403):
        raise RuntimeError("Ключ Kaggle не принят (истёк или удалён?)")
    r.raise_for_status()
    return r.json()


def set_setting_line(code, name, value_repr):
    new, n = re.subn(rf"^{name}\s*=.*$", lambda m: f"{name} = {value_repr}", code, count=1, flags=re.M)
    if not n:
        raise RuntimeError(f"В коде чистки нет строки настройки {name}")
    return new


def notebook_ref(url):
    m = re.search(r"kaggle\.com/code/([^/?#]+)/([^/?#]+)", str(url or ""))
    if not m:
        raise RuntimeError("Не задан блокнот чистки (🎬tmpl_CleanNotebook — ссылка на блокнот Kaggle)")
    return m.group(1), m.group(2)


def kaggle_status(user, slug):
    st = kaggle_call("GetKernelSessionStatus", {"userName": user, "kernelSlug": slug})
    status = st.get("status", "")
    status = {0: "QUEUED", 1: "RUNNING", 2: "COMPLETE", 3: "ERROR"}.get(status, str(status)).upper()
    for word in ("QUEUED", "RUNNING", "COMPLETE", "ERROR", "CANCEL", "NEW_SCRIPT"):
        if word in status:
            return word, st.get("failureMessage") or ""
    return status, st.get("failureMessage") or ""


def clean_cache_path(tag):
    return os.path.join(CLEAN_CACHE_DIR, re.sub(r"[^\w.-]", "_", tag) + ".zip")


def clean_start(data):
    user, slug = notebook_ref(data.get("cleanNotebook"))
    state, _ = kaggle_status(user, slug)
    if state in ("QUEUED", "RUNNING"):
        return {"ok": False, "busy": True,
                "error": "Блокнот чистки сейчас занят другим запуском — пришлите ссылку, когда он закончит"}
    if not os.path.exists(CLEAN_CODE_PATH):
        raise RuntimeError(f"Нет кода чистки на сервере: {CLEAN_CODE_PATH}")
    tag = f"{data.get('projectId', 'P')}-{int(time.time())}"
    code = open(CLEAN_CODE_PATH, encoding="utf-8").read()
    code = set_setting_line(code, "TRACKS_LINK", repr(str(data["tracksUrl"])))
    code = set_setting_line(code, "MODE", repr(str(data.get("cleanMode")).strip()))
    if data.get("cleanBlend") not in (None, ""):
        code = set_setting_line(code, "BLEND", str(float(data.get("cleanBlend"))))
    if data.get("cleanBlendStems") not in (None, ""):
        code = set_setting_line(code, "BLEND_STEMS", repr(str(data.get("cleanBlendStems"))))
    # НОВОЕ (02.10): любые прочие ручки чистки из таблицы (🎬tmpl_CleanXxx →
    # cleanSettings {"Xxx": ...}) — в строку XXX блокнота, если такая строка есть.
    # Новая ручка = новая строка в блокноте + столбец в таблице, без правки сервера и бота.
    for key, value in (data.get("cleanSettings") or {}).items():
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", str(key)).upper()
        if name in ("MODE", "TRACKS_LINK", "RUN_TAG", "CALLBACK_URL") or str(value).strip() == "":
            continue
        if not re.search(rf"^{name}\s*=", code, flags=re.M):
            continue
        text = str(value).strip()
        try:
            float(text)
            value_repr = text
        except ValueError:
            value_repr = repr(text)
        code = set_setting_line(code, name, value_repr)
    code = set_setting_line(code, "RUN_TAG", repr(tag))
    code = set_setting_line(code, "CALLBACK_URL", repr(str(data.get("callbackUrl") or "")))
    notebook = {"cells": [{"cell_type": "code", "metadata": {}, "execution_count": None,
                           "outputs": [], "source": code}],
                "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}},
                "nbformat": 4, "nbformat_minor": 4}
    res = kaggle_call("SaveKernel", {
        "slug": f"{user}/{slug}", "text": json.dumps(notebook), "language": "python",
        "kernelType": "notebook", "isPrivate": True, "enableGpu": True, "enableInternet": True,
        "machineShape": "NvidiaTeslaT4"})
    if res.get("error"):
        return {"ok": False, "error": f"Kaggle не принял запуск чистки: {res['error']}"}
    print(f"[clean] запущена версия {res.get('versionNumber')} ({data.get('cleanMode')}), метка {tag}")
    return {"ok": True, "tag": tag, "version": res.get("versionNumber"),
            "notebookUrl": f"https://www.kaggle.com/code/{user}/{slug}"}


def clean_status(data):
    user, slug = notebook_ref(data.get("cleanNotebook"))
    tag = str(data.get("tag") or "")
    cached = clean_cache_path(tag)
    if tag and os.path.exists(cached):
        return {"state": "complete", "cached": True}
    state, failure = kaggle_status(user, slug)
    if state == "COMPLETE":
        try:
            os.makedirs(CLEAN_CACHE_DIR, exist_ok=True)
            download_kaggle_output_file(f"https://www.kaggle.com/code/{user}/{slug}", cached + ".part",
                                        must_contain=tag)
            os.replace(cached + ".part", cached)
            old = sorted(glob.glob(os.path.join(CLEAN_CACHE_DIR, "*.zip")), key=os.path.getmtime)
            for f in old[:-CLEAN_KEEP]:
                os.remove(f)
            return {"state": "complete", "cached": True}
        except Exception as e:
            # готово, но архива с нашей меткой нет — значит, блокнот уже перезапустили другим выпуском
            return {"state": "error", "message": f"Чистка закончилась, но архив не забран: {e}"}
    if state in ("ERROR", "CANCEL"):
        return {"state": "error", "message": failure or "Kaggle сообщил об ошибке без подробностей"}
    return {"state": "running", "kaggle": state}



def download_file(url, dest_path):
    if "kaggle.com/code/" in url:
        # «#run=<метка>» дописывает авточистка: брать только архив этого запуска
        tag = (re.search(r"#run=([^&]+)", url) or [None, None])[1]
        if tag and os.path.exists(clean_cache_path(tag)):
            shutil.copy(clean_cache_path(tag), dest_path)
            return dest_path
        return download_kaggle_output_file(url, dest_path, must_contain=tag)
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
# НОВОЕ (18.09): помимо самой обрезки, здесь же — первым делом, до любой
# работы с громкостью — срезаются неслышимые крайние частоты (ниже 30Гц,
# выше 19кГц). Это гул/цифровой мусор, которого сам по себе не слышно, но
# который у нейросетевой генерации (Suno) иногда остаётся на краях спектра
# и который компрессор/лимитер дальше по цепочке всё равно "видят" и
# реагируют на них наравне со слышимым звуком — попытка почистить трек, а
# не полосу частот, дальше по цепочке легко перепутать с реальным сигналом.
# Срезается на этом шаге, а не позже, чтобы ни громкость, ни фейды, ни
# компрессор с лимитером его вообще не видели.
# НОВОЕ (18.09, испр.): порог верхнего среза подняли с 16000 до 19000 —
# на реальном рендере 16кГц оказался слишком консервативным и срезал не
# только мусор, но и настоящий "воздух"/блеск (обертоны, которые дают
# ощущение яркости), из-за чего звук стал восприниматься глуховатым,
# будто через подушку — не как осознанный лоуфай-эффект, а именно как
# потеря яркости. 19кГц — уже на самом краю слышимого диапазона у
# взрослого человека, куда генерация обычно и мусорит сильнее всего.
def trim_to_content(input_path, out_path, noise_threshold="-40dB", min_silence_duration=1.0):
    content_start, content_end = get_content_bounds(input_path, noise_threshold, min_silence_duration)
    run_ffmpeg([
        "-i", input_path, "-ss", str(content_start), "-to", str(content_end),
        "-af", "highpass=f=30,lowpass=f=19000",
        out_path
    ])
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
# НОВОЕ (18.09): порог поднят с 1.5 до 6 секунд. Раньше эта функция
# применялась вслепую к КАЖДОМУ файлу (см. split_all_by_silence) — включая
# обычные отдельные стемы, где один файл = одна цельная песня, а не
# несколько бонсированных подряд. У тихого/эмбиентного материала (именно
# то, что называется "Quiet Afternoon"/"Quiet Coziness") обычная пауза
# между фразами внутри ОДНОЙ песни спокойно превышает 1.5 секунды —
# проверено: синтетический трек с одной такой паузой посередине честно
# разрезается этой функцией на два "трека", каждый из которых потом
# получает СВОЮ отдельную нормализацию громкости и свои фейд-ин/фейд-аут —
# то есть посреди естественной музыкальной паузы, где ничего разрывать не
# нужно, искусственно вставляется затухание-в-тишину-и-обратно (и, если
# громкость двух фрагментов измерилась чуть по-разному, ещё и скачок
# уровня) — то, что слышно как щелчок/потрескивание ПОСРЕДИ трека, а не на
# стыке с соседним. Настоящий разрыв между двумя разными бонсированными
# песнями (сценарий, для которого эта функция изначально написана) —
# это пауза, которую автор расставляет намеренно при склейке, обычно
# заметно длиннее любой паузы внутри одной фразы; 6 секунд отделяет одно
# от другого с запасом, не трогая исходный сценарий.
def split_by_silence(input_path, work_dir, noise_threshold="-40dB", min_silence_duration=6.0, split_dir_name="split_tracks", min_segment_seconds=119):
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


# НОВОЕ (18.09): раньше здесь стоял сам фильтр ffmpeg loudnorm в
# двухпроходном linear-режиме — но ffmpeg сам, внутри фильтра, решает
# откатиться на покадровый ("динамический") режим, если посчитанное
# линейное усиление рискует пробить целевой true peak, и делает это
# молча, без предупреждения (видно только в его собственной диагностике
# как normalization_type=dynamic). Именно этот покадровый режим — самое
# вероятное объяснение шороха/потрескивания ("будто электрический сигнал"),
# который то пропадал, то возвращался без единой смены кода: срабатывание
# зависит от измеренных цифр конкретного трека, а не от версии сборщика.
# Здесь та же самая защита от превышения пика считается вручную, а сам
# сигнал корректируется простым статичным volume=...dB — фильтром, у
# которого физически нет покадрового режима, ему неоткуда провалиться.
def linear_gain_filter(input_path, target_lufs, target_tp=-1.5):
    measured = measure_loudnorm(input_path, target_lufs)
    if not measured:
        print(f"[loudnorm] измерение не удалось для {input_path} — поправка громкости не применяется (0 дБ)")
        return "volume=0dB"
    measured_i = float(measured["input_i"])
    measured_tp = float(measured["input_tp"])
    gain_db = target_lufs - measured_i
    # Если поднятие до целевой громкости вывело бы пик выше безопасного
    # потолка — урезаем усиление до потолка вместо целевой громкости.
    # Это безопаснее, чем рисковать настоящим клиппингом (жёстким,
    # необратимым искажением, которое никаким лимитером после уже не
    # вылечить) — и, в отличие от отката на другой алгоритм, это видно
    # в логе.
    if measured_tp + gain_db > target_tp:
        capped_gain_db = target_tp - measured_tp
        print(f"[loudnorm] {input_path}: усиление {gain_db:.2f}dB подняло бы пик выше {target_tp}dB, урезано до {capped_gain_db:.2f}dB")
        gain_db = capped_gain_db
    return f"volume={gain_db:.4f}dB"


# НОВОЕ (27.09, «версия 3» по прослушиванию автора): громкость доводим до
# цели ЦЕЛИКОМ, без урезания по пику — пики после этого ловит лимитер с
# выключенным автоподъёмом (level=disabled). Раньше усиление урезалось по
# пику, и тихие треки оставались тише цели, а финальный компрессор и
# лимитер с автоподъёмом (у alimiter он включён по умолчанию) сминали
# динамику: LRA падал с 2-3 до 1.6-1.9, фон поднимался на 7-9 дБ.
def gain_to_target(input_path, target_lufs):
    measured = measure_loudnorm(input_path, target_lufs)
    if not measured:
        print(f"[gain] измерение не удалось для {input_path} — поправка громкости не применяется (0 дБ)")
        return "volume=0dB"
    return f"volume={target_lufs - float(measured['input_i']):.4f}dB"


# НОВОЕ (02.10): отчёт о громкости по трекам — только замер, звук не меняет.
# Автор слышит, что на стыке некоторые треки «выстреливают» громче соседей,
# хотя каждый выровнен по средней громкости. Отчёт показывает по каждому
# треку: среднюю громкость до выравнивания, разброс (LRA), пик, поправку и
# громкость первых и последних 15 секунд уже готового трека; ниже — стыки,
# где конец одного и начало следующего расходятся на 3 дБ и больше.
def segment_loudness(path, start, length):
    result = subprocess.run(
        [FFMPEG_BIN, "-ss", f"{max(0.0, start):.2f}", "-t", f"{length:.2f}", "-i", path,
         "-af", "ebur128", "-f", "null", "-"],
        capture_output=True, text=True
    )
    found = re.findall(r"I:\s*(-?[\d.]+)\s*LUFS", result.stderr)
    return float(found[-1]) if found else None


def track_loudness_entry(n, raw_path, source_path, faded_path, duration, target_lufs, fade_in, fade_out):
    m = measure_loudnorm(source_path, target_lufs) or {}
    num = lambda k: float(m[k]) if k in m else None
    src_i = num("input_i")
    window = min(15.0, max(1.0, duration / 3))
    return {
        "n": n, "name": os.path.basename(raw_path), "duration": round(duration, 1),
        "sourceLufs": src_i, "lra": num("input_lra"), "peak": num("input_tp"),
        "gainDb": round(target_lufs - src_i, 2) if src_i is not None else None,
        "headLufs": segment_loudness(faded_path, fade_in, window),
        "tailLufs": segment_loudness(faded_path, duration - fade_out - window, window),
    }


def format_loudness_report(entries, target_lufs):
    f = lambda v: "—" if v is None else f"{v:g}"
    lines = [f"Громкость по трекам (цель {target_lufs} LUFS)",
             "№ | длит, с | было LUFS | разброс LRA | пик | поправка дБ | начало | конец | файл"]
    for e in entries:
        lines.append(" | ".join([str(e["n"]), f(e["duration"]), f(e["sourceLufs"]), f(e["lra"]), f(e["peak"]),
                                 f(e["gainDb"]), f(e["headLufs"]), f(e["tailLufs"]), e["name"]]))
    lines.append("")
    lines.append("Стыки (конец трека → начало следующего, разница 3 дБ и больше):")
    jumps = 0
    for a, b in zip(entries, entries[1:]):
        if a["tailLufs"] is None or b["headLufs"] is None:
            continue
        diff = b["headLufs"] - a["tailLufs"]
        if abs(diff) >= 3:
            jumps += 1
            lines.append(f"{a['n']} → {b['n']}: {a['tailLufs']:g} → {b['headLufs']:g} ({diff:+.1f} дБ)")
    if not jumps:
        lines.append("нет")
    return "\n".join(lines)


# Потолок лимитера на отдельном треке: -1.5 dBFS — тот же запас по пику,
# что и в linear_gain_filter выше.
TRACK_PEAK_LIMIT = 10 ** (-1.5 / 20)


def build_audio_track(
    audio_source_url, work_dir, target_lufs=-16, fade_in_seconds=1.5, fade_out_seconds=3,
    gap_seconds=0, loop_count=None, mix_seconds=None,
    compressor_threshold_db=-20, compressor_ratio=2, compressor_attack_sec=0.02, compressor_release_sec=0.25,
    limiter_ceiling=0.89, limiter_attack_ms=5, limiter_release_ms=50,
    denoise_amount=0, loudness_report=None, highs_db=0.0, highs_hz=7000.0,
):
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
        # Двухпроходный режим (см. linear_gain_filter выше) — точнее
        # однопроходного, и без права молча провалиться в покадровый режим.
        # НОВОЕ (18.09): было curve=log на обоих фейдах. Проверено по формуле
        # самого ffmpeg (libavfilter/af_afade.c): у log почти весь подъём
        #/спад сосредоточен в первые/последние доли секунды (для 5-секундного
        # фейд-ина громкость уже 40% на 5-й миллисекунде), а не растянут на
        # всю заданную длительность — отсюда фейд-ин, который не слышно (звук
        # практически сразу на полной громкости), и фейд-аут, который держит
        # почти полную громкость до последней доли секунды, а потом резко
        # обрывается. Резкий подъём огибающей за единицы миллисекунд поверх
        # уже приведённого к целевой громкости сигнала (loudnorm выше по
        # цепочке) слышен как щелчок. curve=tri (линейная) это уже исправила,
        # но остаточный лёгкий шорох в начале некоторых треков — как игла на
        # пластинку — остался: даже линейный подъём начинает расти сразу же
        # с t=0. НОВОЕ (19.09): фейд-ин переведён на curve=qua (квадратичная,
        # "ease-in"), в теории ради мягкого "подержать у нуля". ОТКАЧЕНО
        # (20.09): на реальном прослушивании оказалось, что qua ощущается
        # просто как слишком медленный, тягучий фейд-ин — вернули обратно
        # на tri (линейная), ту же кривую, что и у фейд-аута, на который
        # жалоб не было.
        # НОВОЕ (20.09): опциональное шумоподавление (afftdn) — по умолчанию
        # выключено (denoise_amount=0, тогда фильтр вообще не добавляется в
        # цепочку). Автор явно попросила ручку под конкретные шумные треки
        # от Suno (виниловое шипение/потрескивание), а не всегда включённую
        # обработку. denoise_amount — это параметр 'nr' у afftdn (сила
        # подавления в dB, официальный диапазон 0.01-97, дефолт самого
        # ffmpeg — 12) — чем больше, тем агрессивнее чистка и тем выше риск
        # "подводного" призвука на деталях (например, рояль). Начинать
        # стоит с малых значений (5-10) и слушать, не с дефолтных 12+.
        # НОВОЕ (27.09): порядок «версии 3». Сначала чистка (если задана) —
        # отдельным проходом, чтобы громкость мерилась уже по чистому звуку.
        # Потом громкость ровно в цель и лимитер пиков трека (без автоподъёма);
        # лимитер мог чуть убавить — второй замер добивает точно в цель.
        # Фейды — последними, по уже готовому уровню.
        track_limiter = (
            f"alimiter=limit={TRACK_PEAK_LIMIT:.4f}:attack={limiter_attack_ms}:"
            f"release={limiter_release_ms}:level=disabled"
        )
        source_path = trimmed_path
        if denoise_amount:
            source_path = os.path.join(faded_dir, f"denoised_{i}.wav")
            run_ffmpeg(["-i", trimmed_path, "-af", f"afftdn=nr={denoise_amount}", source_path])
        # НОВОЕ (05.10): мягко приглушить верха (стеклянное пианино Suno) — 🎬 HighsDb / HighsHz.
        # Полка с пологим наклоном: переход широкий, без ступеньки; громкость дальше меряется уже после неё.
        if highs_db:
            eq_path = os.path.join(faded_dir, f"highs_{i}.wav")
            run_ffmpeg(["-i", source_path, "-af", f"treble=g={highs_db:.2f}:f={highs_hz:.0f}:t=s:w=0.35", eq_path])
            source_path = eq_path
        leveled_path = os.path.join(faded_dir, f"leveled_{i}.wav")
        run_ffmpeg(["-i", source_path, "-af", f"{gain_to_target(source_path, target_lufs)},{track_limiter}", leveled_path])
        af_parts = [
            gain_to_target(leveled_path, target_lufs),
            track_limiter,
            f"afade=t=in:st=0:d={fade_in_seconds}:curve=tri",
            f"afade=t=out:st={fade_out_start}:d={fade_out_seconds}:curve=tri",
        ]
        faded_path = os.path.join(faded_dir, f"faded_{i}.wav")
        run_ffmpeg(["-i", leveled_path, "-af", ",".join(af_parts), faded_path])
        faded_tracks.append(faded_path)
        if loudness_report is not None:
            try:
                loudness_report.append(track_loudness_entry(
                    i + 1, tracks_raw[i], source_path, faded_path, duration,
                    target_lufs, fade_in_seconds, fade_out_seconds))
            except Exception as report_error:
                print(f"[громкость] трек {i + 1}: замер не удался: {report_error}")

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

    # НОВОЕ (18.09): раньше здесь после склейки стоял ЕЩЁ ОДИН полнофайловый
    # шаг коррекции громкости (сначала loudnorm, потом статичный volume=...dB
    # взамен него) — избыточный: каждый трек уже приведён к target_lufs
    # ПООТДЕЛЬНОСТИ выше по коду (см. linear_gain_filter в цикле фейдов), и
    # склейка уже приведённых к одной цели отрезков не должна заметно уводить
    # общую громкость от той же цели. Лишняя стадия, трогающая громкость ещё
    # раз поверх уже нормализованных треков, — ровно тот риск наслоения,
    # который стоило убрать: чем меньше отдельных шагов трогают уровень
    # сигнала, тем меньше шансов на кумулятивные артефакты. Компрессор и
    # лимитер остаются единственной финальной стадией — они не выравнивают
    # громкость, а только страхуют от пиков/резких транзиентов.
    #
    # УПРОЩЕНО (20.09): 19.09 ночью здесь стоял трёхполосный mcompand
    # (отдельно бас/середина/верха, 12 параметров) — задумывался, чтобы
    # длинные басовые ноты не вызывали эффект "дышащей подушки" от одного
    # компрессора на весь спектр. По факту три полосы утроили число мест,
    # где что-то может звучать не так (в том числе саму гулкость/
    # самовозбуждение на басу, ради которого их и завели) — и добавили
    # 12 чисел в таблицу, большинство из которых никто не может объяснить
    # на слух. Автор явно попросила вернуться к одному простому компрессору
    # на весь спектр + отдельный лимитер для пиков — с прицелом: если бас
    # всё-таки "задышит" на одной полосе, разбираться с этим осознанно и
    # точечно, а не носить сложность по умолчанию. Синтаксис `acompressor`
    # (`threshold` в дБ через суффикс, `ratio`, `attack`/`release` в мс) —
    # официальный, стандартный параметр самого фильтра, не мой домысел.
    #
    # Лимитер (alimiter) остаётся последней, отдельной ступенью — не общая
    # окраска тембра, а аварийная защита от пиков (то, что автор явно
    # попросила оставить). Потолок 0.89 (не 1.0) — запас на случай, что
    # YouTube при пережатии слегка поднимет пики между сэмплами (true peak),
    # которые alimiter у ffmpeg не видит технически.
    # НОВОЕ (27.09, «версия 3»): компрессор — только если в таблице ratio > 1
    # (при ratio 1 он ничего не делает, лишний проход не нужен). Дальше:
    # замер → громкость ровно в цель → лимитер ПОСЛЕДНИМ, без автоподъёма
    # (level=disabled), чтобы он только ловил пики и не поднимал фон.
    bus_in = concat_out
    if float(compressor_ratio or 1) > 1:
        bus_in = os.path.join(work_dir, "audio_compressed.wav")
        run_ffmpeg([
            "-i", concat_out,
            "-af", (
                f"acompressor=threshold={compressor_threshold_db}dB:ratio={compressor_ratio}:"
                f"attack={compressor_attack_sec * 1000}:release={compressor_release_sec * 1000}"
            ),
            bus_in
        ])
    normalized_out = os.path.join(work_dir, "audio_final.wav")
    limiter = (
        f"alimiter=limit={limiter_ceiling}:attack={limiter_attack_ms}:"
        f"release={limiter_release_ms}:level=disabled"
    )
    run_ffmpeg([
        "-i", bus_in,
        "-af", f"{gain_to_target(bus_in, target_lufs)},{limiter}",
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

    # ОТКАЧЕНО (23.09): пробовала здесь отдельный короткий кроссфейд вместо
    # обычной склейки — но это тихой сапой убирало секундную паузу между
    # проходами (GapSeconds=1.0 у pengui), которая на обычных стыках между
    # треками сохраняется. Не тронутая пауза важнее непроверенной гипотезы —
    # возвращаем зацикливание на ту же функцию join_tracks, что и обычные
    # стыки между треками, с тем же самым разрывом-тишиной. Причина щелчка
    # на стыке повтора ПО-ПРЕЖНЕМУ не найдена (см. её же обсуждение выше по
    # файлу) — это откат к прежнему поведению, а не фикс. Нужен реальный
    # прогон и внимательное прослушивание именно этого стыка: щёлкает ровно
    # в начале паузы, ровно в конце, или посреди самой тишины — это разные
    # причины, и без такого наблюдения дальше двигаться вслепую.
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
    # за один проход. НОВОЕ (20.09, утро): потолок 0.12 не давал реально
    # тёмным картинкам (diff 40-50+) дотянуться до цели даже близко — видео
    # оставалось заметно темнее нормы. Поднято до 0.20 — для типичного
    # случая (diff ~50) этого хватает почти полностью, а сильно засветить
    # кадр плоским сдвигом такой величины по-прежнему нельзя.
    boost = min(diff / 255.0, 0.20)
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


def old_film_filters(strength):
    """НОВОЕ (24.09): лёгкая "старая плёнка" — редкие царапины и пылинки,
    вспыхивающие на доли секунды, каждая в своём месте и со своим ритмом.
    strength из таблицы (🎬tmpl_OldFilm): 2 — подобрано автором на тестах
    (4 царапины, 12 мелких тёмных и 7 мелких светлых пылинок), 1 — вдвое
    реже. Случайность с фиксированным зерном: рисунок одинаковый в каждой
    сборке. drawbox рисует только в свои моменты (enable), остальные кадры
    не меняются — вес файла почти не растёт."""
    import random
    rnd = random.Random(20260924)
    filters = []
    for i in range(round(2 * strength)):
        x = rnd.uniform(0.06, 0.94); w = rnd.choice([1, 2, 2, 3])
        color = f"white@{rnd.uniform(0.16, 0.2):.2f}" if i % 3 == 2 else f"black@{rnd.uniform(0.32, 0.4):.2f}"
        period = rnd.uniform(7, 19); phase = rnd.uniform(0, period); dur = rnd.uniform(0.4, 0.9)
        filters.append(f"drawbox=x=iw*{x:.3f}:y=0:w={w}:h=ih:color={color}:t=fill:"
                       f"enable='lt(mod(t+{phase:.2f},{period:.2f}),{dur:.2f})'")
    for _ in range(round(6 * strength)):
        x = rnd.uniform(0.03, 0.97); y = rnd.uniform(0.05, 0.95); w = rnd.randint(4, 7); h = rnd.randint(4, 6)
        color = rnd.choice(["black@0.6", "black@0.55"])
        period = rnd.uniform(3, 9); phase = rnd.uniform(0, period); dur = rnd.choice([0.2, 0.4])
        filters.append(f"drawbox=x=iw*{x:.3f}:y=ih*{y:.3f}:w={w}:h={h}:color={color}:t=fill:"
                       f"enable='lt(mod(t+{phase:.2f},{period:.2f}),{dur:.2f})'")
    for _ in range(round(3.5 * strength)):
        x = rnd.uniform(0.03, 0.97); y = rnd.uniform(0.05, 0.95); w = rnd.randint(3, 5); h = rnd.randint(3, 5)
        color = rnd.choice(["white@0.55", "white@0.5"])
        period = rnd.uniform(4, 12); phase = rnd.uniform(0, period)
        filters.append(f"drawbox=x=iw*{x:.3f}:y=ih*{y:.3f}:w={w}:h={h}:color={color}:t=fill:"
                       f"enable='lt(mod(t+{phase:.2f},{period:.2f}),0.20)'")
    return filters


def pixel_shift_filters(px):
    """НОВОЕ (24.09): невидимый сдвиг пикселей для OLED-экранов — картинка
    чуть больше кадра, окно кадра за 10-15 минут медленно гуляет на ±px
    (целые пиксели: между сдвигами кадры одинаковые, вес почти не растёт)."""
    return [
        f"scale={VIDEO_WIDTH + 2 * px}:{VIDEO_HEIGHT + 2 * px}",
        f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}:x='{px}+round({px}*sin(2*PI*t/600))':y='{px}+round({px}*cos(2*PI*t/900))'",
    ]


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
        if key in MEDIA_FX_KEYS:
            continue
        if key in registry:
            filters.append(registry[key](value, *args) if args else registry[key](value))
        else:
            print(f"[video-assembler] unknown effect '{key}', skipping")
    return filters



# НОВОЕ (01.10): сборка видео КУСКАМИ. Каждый кусок (вступление с надписью,
# минута статики, петля, событие) рендерится один раз коротким клипом с
# одинаковыми параметрами кодека, а длинное видео склеивается из копий этих
# кусков без пересчёта (concat, -c:v copy). Поэтому всё видео идёт в одной
# частоте кадров (по умолчанию 24) и собирается не дольше прежнего.
# Тело видео выбирается тем, что лежит в строке проекта:
#   fx_LoopUrl пусто, fx_EventUrls пусто  -> статика
#   только fx_LoopUrl                      -> бесконечная петля
#   только fx_EventUrls                    -> статика + события с паузами
#   оба                                    -> петля + события поверх неё
# Петля и события должны начинаться и заканчиваться исходной картинкой
# (так их делает блокнот Wan: первый кадр = последний = картинка).
MEDIA_FX_KEYS = ("fx_LoopUrl", "fx_EventUrls", "fx_Effects")


def piece_codec_args(fps):
    # одинаковые для ВСЕХ кусков — иначе склейка копированием не сработает
    return ["-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-r", str(fps),
            "-g", str(fps * 2), "-video_track_timescale", str(fps * 1000)]


def media_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(r.stdout.strip())


def download_media(url, dest_path):
    # Kaggle-блокнот Wan: берём петля.mp4 из его результата; иначе — как обычный файл
    if "kaggle.com/code/" in url:
        return download_kaggle_output_file(url, dest_path, ext=".mp4", prefer="петля.mp4")
    return download_file(url, dest_path)


def normalize_clip(src, out, fps):
    # любой клип (Wan отдаёт 16 кадров/с и свой размер) -> размер кадра и общая частота
    run_ffmpeg(["-i", src, "-vf",
                f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:flags=lanczos,setsar=1,fps={fps}",
                "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
                "-pix_fmt", "yuv420p", out])
    return out


def render_still_piece(image_path, seconds, base_chain, fps, out):
    run_ffmpeg(["-loop", "1", "-framerate", str(fps), "-t", f"{seconds:g}", "-i", image_path,
                "-vf", base_chain] + piece_codec_args(fps) + [out])
    return out


def render_loop_piece(loop_path, seconds, base_chain, fps, out):
    run_ffmpeg(["-stream_loop", "-1", "-i", loop_path, "-t", f"{seconds:g}",
                "-vf", base_chain] + piece_codec_args(fps) + [out])
    return out


def render_event_piece(event_path, image_path, loop_path, seconds, base_chain, fps, out):
    # без петли — сам клип события; с петлёй — движение события поверх петли:
    # маска там, где кадр события отличается от исходной картинки
    if not loop_path:
        run_ffmpeg(["-i", event_path, "-t", f"{seconds:g}", "-vf",
                    f"tpad=stop_mode=clone:stop_duration={seconds:g},{base_chain}"]
                   + piece_codec_args(fps) + [out])
        return out
    graph = (
        f"[0:v]tpad=stop_mode=clone:stop_duration={seconds:g},split[ev][evm];"
        f"[1:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},setsar=1,format=yuv420p[st];"
        f"[evm][st]blend=all_mode=difference,format=gray,"
        f"geq=lum='if(gt(lum(X\\,Y)\\,10)\\,255\\,0)',boxblur=8[m];"
        f"[ev][m]alphamerge[eva];"
        f"[2:v][eva]overlay=0:0:shortest=1,{base_chain}[v]"
    )
    run_ffmpeg(["-i", event_path,
                "-loop", "1", "-framerate", str(fps), "-t", f"{seconds:g}", "-i", image_path,
                "-stream_loop", "-1", "-t", f"{seconds:g}", "-i", loop_path,
                "-filter_complex", graph, "-map", "[v]", "-t", f"{seconds:g}"]
               + piece_codec_args(fps) + [out])
    return out


def render_masked_event_piece(event_path, mask_path, image_path, loop_path, seconds, base_chain, fps, out):
    """Событие со своей маской (листья): кладём ровно то, что нарисовано, поверх петли или картинки."""
    bg = (["-stream_loop", "-1", "-t", f"{seconds:g}", "-i", loop_path] if loop_path
          else ["-loop", "1", "-framerate", str(fps), "-t", f"{seconds:g}", "-i", image_path])
    graph = (
        f"[0:v]tpad=stop_mode=clone:stop_duration={seconds:g},format=yuv420p[ev];"
        f"[1:v]tpad=stop_mode=clone:stop_duration={seconds:g},format=gray[m];"
        f"[ev][m]alphamerge[eva];"
        f"[2:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},setsar=1,format=yuv420p[bg];"
        f"[bg][eva]overlay=0:0:shortest=1,{base_chain}[v]"
    )
    run_ffmpeg(["-i", event_path, "-i", mask_path] + bg +
               ["-filter_complex", graph, "-map", "[v]", "-t", f"{seconds:g}"]
               + piece_codec_args(fps) + [out])
    return out


def render_intro_piece(image_path, loop_path, seconds, base_chain, shadow_layers, main_layers,
                       shadow_blur, fps, out):
    src = (["-stream_loop", "-1", "-i", loop_path] if loop_path
           else ["-loop", "1", "-framerate", str(fps), "-i", image_path])
    if shadow_layers:
        shadow_chain = ";".join(
            f"[{'shadowbg' if i == 0 else f'sh{i}'}]{f}[sh{i + 1}]" for i, f in enumerate(shadow_layers))
        main_chain = ";".join(
            f"[{'with_shadow' if i == 0 else f'm{i}'}]{f}[{f'm{i + 1}' if i + 1 < len(main_layers) else 'v'}]"
            for i, f in enumerate(main_layers))
        graph = (f"[0:v]{base_chain}[base];"
                 f"color=c=black@0.0:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:r={fps}:d={seconds:g}[shadowbg];"
                 f"{shadow_chain};[sh{len(shadow_layers)}]gblur=sigma={shadow_blur}[shadow_blurred];"
                 f"[base][shadow_blurred]overlay=0:0[with_shadow];{main_chain}")
    else:
        graph = f"[0:v]{base_chain}[v]"
    run_ffmpeg(src + ["-t", f"{seconds:g}", "-filter_complex", graph, "-map", "[v]",
                      "-t", f"{seconds:g}"] + piece_codec_args(fps) + [out])
    return out


def plan_body(duration, intro, loop_len, event_lens, gap_min, gap_max, seed):
    """Список кусков тела после вступления: ('still', сек) / ('loop', сек) / ('event', номер).
    С петлёй все паузы кратны длине петли — петля не сбивается с шага."""
    rnd = random.Random(seed)
    parts, t = [], intro
    unit = loop_len if loop_len else 10.0
    big = unit * max(1, round(60 / unit))
    base = "loop" if loop_len else "still"
    if not event_lens:
        while t < duration:
            parts.append((base, big)); t += big
        return parts, big
    k = 0
    while t < duration:
        gap = rnd.uniform(gap_min, gap_max)
        n_big, rest = int(gap // big), gap % big
        parts += [(base, big)] * n_big
        n_small = int(round(rest / unit))
        parts += [(base, unit)] * n_small
        t += n_big * big + n_small * unit
        if t >= duration:
            break
        i = k % len(event_lens); k += 1
        parts.append(("event", i)); t += event_lens[i]
    return parts, big


# ЦВЕТ (02.10): один общий фильтр на картинку выпуска — чтобы лента канала была
# одним целым. Три ручки из таблицы (🎬tmpl_ColorMute / ColorCool / ColorHaze),
# пусто или 0 — картинка не трогается:
#   colorMute — насколько приглушить цвет (0.3 = на 30 % меньше насыщенности)
#   colorCool — насколько снять желтизну (единицы Lab b*, 5 — заметно, но мягко)
#   colorHaze — «сфумато»: мягче контраст, немного воздуха и лёгкая дымка (1 — как в пробе)
# Рисунок и линии не меняются. Делается до всего остального: и видео, и эффекты,
# и обложка берут уже отфильтрованную картинку.
def _srgb_to_lab(rgb):
    import numpy as np
    c = np.where(rgb > 0.04045, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)
    m = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = c @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def _lab_to_srgb(lab):
    import numpy as np
    fy = (lab[..., 0] + 16) / 116
    f = np.stack([fy + lab[..., 1] / 500, fy, fy - lab[..., 2] / 200], -1)
    xyz = np.where(f > 6 / 29, f ** 3, 3 * (6 / 29) ** 2 * (f - 4 / 29)) * np.array([0.95047, 1.0, 1.08883])
    m = np.array([[3.2404542, -1.5371385, -0.4985314],
                  [-0.9692660, 1.8760108, 0.0415560],
                  [0.0556434, -0.2040259, 1.0572252]])
    c = np.clip(xyz @ m.T, 0, 1)
    return np.where(c > 0.0031308, 1.055 * c ** (1 / 2.4) - 0.055, 12.92 * c)


def grade_image(image_path, data):
    def _num(key):
        try:
            return float(str(data.get(key, "") or 0).replace(",", "."))
        except ValueError:
            return 0.0
    mute, cool, haze = _num("colorMute"), _num("colorCool"), _num("colorHaze")
    if not (mute or cool or haze):
        return
    import sys as _sys
    if "/app/pylibs" not in _sys.path:  # numpy и pillow — там же, где у эффектов
        _sys.path.insert(0, "/app/pylibs")
    import numpy as np
    from PIL import Image, ImageChops, ImageFilter
    src = Image.open(image_path).convert("RGB")
    lab = _srgb_to_lab(np.asarray(src, np.float64) / 255.0)
    lab[..., 2] -= cool
    lab[..., 1:] *= max(0.0, 1.0 - mute)
    if haze:
        mean = lab[..., 0].mean()
        lab[..., 0] = (lab[..., 0] - mean) * (1 - 0.12 * haze) + mean
        lift = 0.07 * haze
        lab[..., 0] = lab[..., 0] * (1 - lift) + 92 * lift
    out = Image.fromarray((_lab_to_srgb(lab) * 255 + 0.5).astype(np.uint8))
    if haze:
        # дымка только «светится» поверх: светлое чуть расплывается, а тёмные линии
        # карандаша остаются чёткими (смешение «светлее», а не простое размытие)
        soft = out.filter(ImageFilter.GaussianBlur(4 * haze * src.width / 1536))
        out = ImageChops.lighter(out, Image.blend(out, soft, min(1.0, 0.35 * haze)))
    out.save(image_path, format="JPEG", quality=97, subsampling=0)  # без потерь цвета
    print(f"[grade] цвет: приглушить {mute}, холоднее {cool}, дымка {haze}")


# ЭФФЕКТЫ (01.10): нарисованная поверх картинки анимация без нейросетей — пар над
# чашкой, пузыри у рыбки, моргание. Строка проекта fx_Effects, по строчке на эффект,
# числа — проценты кадра:
#   пар: 68.4, 58.4             (точка поверхности напитка или край кружки)
#   пузыри: 86.9, 73.6, 67.0    (рот рыбки; высота поверхности воды)
#   моргание: 74.0, 63.0        (глаз; точный центр сборщик находит сам рядом)
# Из этого рисуется бесшовная петля EFFECTS_LOOP_SECONDS и идёт как обычная петля.
# Вид — 🎬-настройки (steamOpacity, steamHeight); пусто — как в утверждённой пробе.
EFFECTS_LOOP_SECONDS = 6.0
EFFECT_NAMES = {"пар": "steam", "steam": "steam", "пузыри": "bubbles", "bubbles": "bubbles",
                "моргание": "blink", "blink": "blink", "глаз": "blink",
                "дымок": "smoke", "дым": "smoke", "smoke": "smoke",
                "свеча": "candle", "свечи": "candle", "candle": "candle",
                "дождь": "rain", "rain": "rain"}
# Строки листьев и края — не петля, а события (см. ЛИСТЬЯ ниже)
EVENT_EFFECT_WORDS = ("листья", "лист", "leaves", "leaf", "край", "edge")


def parse_effects(text):
    out = []
    for line in str(text or "").splitlines():
        if line.strip().lower().startswith(EVENT_EFFECT_WORDS):
            continue
        m = re.match(r"\s*([^\d:,\-]+?)\s*[:\-]?\s*(-?[\d.].*)$", line)
        if not m:
            continue
        kind = EFFECT_NAMES.get(m.group(1).strip().lower())
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", m.group(2))]
        if kind and len(nums) >= 2:
            out.append((kind, nums))
        else:
            print(f"[effects] не поняла строку: {line!r}")
    return out


# ── ПРИМАГНИЧИВАНИЕ (05.10): точки, которые можно найти счётом, а не глазом ──
# Пламя — самое яркое тёплое пятно рядом с точкой; стекло окна — тёмная область рядом
# с прямоугольником. Глаз птицы ищется в своём узле (самое тёмное круглое пятно).
def snap_flame(arr, px, py, W, H, search_pct=4.0):
    import numpy as np
    r = int(search_pct / 100 * W)
    x0, y0 = max(0, int(px) - r), max(0, int(py) - r)
    x1, y1 = min(W, int(px) + r), min(H, int(py) + r)
    win = arr[y0:y1, x0:x1].astype(np.float32)
    if win.size == 0:
        return px, py
    score = win.mean(axis=2) + 0.6 * (win[..., 0] - win[..., 2])      # светло и тепло
    thr = np.percentile(score, 99.93)                                  # сердцевина пламени, не банка
    if thr < 170:                                                     # огня рядом нет — точку не трогаем
        return px, py
    ys, xs = np.nonzero(score >= thr)
    return x0 + float(xs.mean()), y0 + float(ys.mean())


def snap_glass(arr, rx0, ry0, rx1, ry1, W, H):
    import numpy as np
    from PIL import Image, ImageFilter
    w, h = rx1 - rx0, ry1 - ry0
    ex0, ey0 = max(0, int(rx0 - 0.6 * w)), max(0, int(ry0 - 0.6 * h))
    ex1, ey1 = min(W, int(rx1 + 0.6 * w)), min(H, int(ry1 + 0.6 * h))
    lum = np.asarray(Image.fromarray(arr[ey0:ey1, ex0:ex1].astype(np.uint8)).convert("L")
                     .filter(ImageFilter.GaussianBlur(3)), np.float32)
    inner = lum[max(0, ry0 - ey0):ry1 - ey0, max(0, rx0 - ex0):rx1 - ex0]
    if inner.size == 0:
        return rx0, ry0, rx1, ry1
    blue = arr[ey0:ey1, ex0:ex1, 2].astype(np.float32) - arr[ey0:ey1, ex0:ex1, 0].astype(np.float32)
    thr = float(np.percentile(lum, 25))
    dark = (lum <= thr) & (blue > -5)                                  # тёмное и не тёплое — стекло, не рама
    if dark.sum() < 50:
        return rx0, ry0, rx1, ry1
    # самая большая тёмная область и все сопоставимые с ней (стёкла между перекладинами)
    small = Image.fromarray((dark * 255).astype(np.uint8)).resize((max(1, dark.shape[1] // 4), max(1, dark.shape[0] // 4)))
    m = np.asarray(small) > 127
    lab = np.zeros(m.shape, np.int32); n = 0; sizes = []
    for yy in range(m.shape[0]):
        for xx in range(m.shape[1]):
            if m[yy, xx] and not lab[yy, xx]:
                n += 1; stack = [(yy, xx)]; lab[yy, xx] = n; c = 0
                while stack:
                    a, b = stack.pop(); c += 1
                    for na, nb in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                        if 0 <= na < m.shape[0] and 0 <= nb < m.shape[1] and m[na, nb] and not lab[na, nb]:
                            lab[na, nb] = n; stack.append((na, nb))
                sizes.append(c)
    if not sizes:
        return rx0, ry0, rx1, ry1
    big = max(sizes)
    keep = np.isin(lab, [i + 1 for i, c in enumerate(sizes) if c >= 0.25 * big])
    ys, xs = np.nonzero(keep)
    return (ex0 + xs.min() * 4, ey0 + ys.min() * 4, ex0 + (xs.max() + 1) * 4, ey0 + (ys.max() + 1) * 4)


def render_effects_loop(image_path, spec, data, fps, out_path, still_at=None):
    import sys as _sys
    if "/app/pylibs" not in _sys.path:  # numpy и pillow ставятся сюда (переживают Deploy)
        _sys.path.insert(0, "/app/pylibs")
    import math
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter

    def _num(key, default):
        try:
            v = float(data.get(key))
            return v if v > 0 else default
        except (TypeError, ValueError):
            return default
    steam_opacity = _num("steamOpacity", 0.62)
    steam_height = _num("steamHeight", 1.0)

    src = Image.open(image_path).convert("RGB")
    W, H = src.size
    base = np.asarray(src, np.float32)
    k = H / 864.0  # пробу рисовали на кадре 1536x864
    SS = 4
    rng = np.random.default_rng(3)
    n_frames = int(round(EFFECTS_LOOP_SECONDS * fps))
    layers = []

    for kind, nums in spec:
        px, py = nums[0] / 100 * W, nums[1] / 100 * H
        if kind == "steam" and len(nums) >= 3 and nums[2] > 0:
            # ПАР НАД ВАННОЙ (04.10): третья цифра — ширина водной глади (% кадра). Три широкие,
            # сильно размытые, еле заметные струи по всей ширине; петля — вся 6-секундная.
            span = nums[2] / 100 * W
            bw, bh = int(span + 90 * k), int(200 * k * steam_height)
            x0, y0 = int(px - bw / 2), int(py - bh)
            grain = np.asarray(Image.fromarray(rng.uniform(0, 255, (bh, bw)).astype(np.uint8))
                               .filter(ImageFilter.GaussianBlur(2.0 * k)), np.float32) / 255
            grain = 0.7 + 0.3 * grain
            wide = [dict(bx=(f - 0.5) * span, A=26, f=1.0, ph=p_, mp=m_)
                    for f, p_, m_ in ((0.2, 0.0, 0.15), (0.52, 2.2, 0.6), (0.82, 4.3, 0.35))]

            def steam(t, bw=bw, bh=bh, x0=x0, y0=y0, grain=grain, wide=wide):
                t = (t % EFFECTS_LOOP_SECONDS) / EFFECTS_LOOP_SECONDS
                can = Image.new("L", (bw * SS, bh * SS), 0)
                d = ImageDraw.Draw(can)
                for w in wide:
                    S = 120
                    pts = []
                    for i in range(S + 1):
                        s_ = i / S
                        x = bw / 2 + w["bx"] + k * w["A"] * s_ ** 0.9 * math.sin(2 * math.pi * (w["f"] * s_ - t) + w["ph"])
                        pts.append((x, bh - 1 - s_ * (bh - 6), s_))
                    for i in range(S):
                        xa, ya, s_ = pts[i]
                        xb, yb, _ = pts[i + 1]
                        fade = min(1, s_ / 0.08) * max(0, min(1, (0.95 - s_) / 0.5))
                        dash = 0.5 + 0.5 * math.sin(2 * math.pi * (1.5 * s_ - t) + w["mp"] * 6.28)
                        a = fade * (0.4 + 0.6 * dash)
                        if a > 0.01:
                            d.line([(xa * SS, ya * SS), (xb * SS, yb * SS)], fill=int(255 * a),
                                   width=max(1, int((9 + 16 * s_) * k * SS)))
                al = np.asarray(can.resize((bw, bh), Image.LANCZOS).filter(ImageFilter.GaussianBlur(7 * k)),
                                np.float32) / 255 * grain * steam_opacity * 0.42
                return x0, y0, al, np.array([246, 241, 231], np.float32)
            layers.append(steam)

        elif kind == "steam":
            bw, bh = int(150 * k), int(165 * k * steam_height)
            x0, y0 = int(px - bw / 2), int(py - bh)
            grain = np.asarray(Image.fromarray(rng.uniform(0, 255, (bh, bw)).astype(np.uint8))
                               .filter(ImageFilter.GaussianBlur(0.6 * k)), np.float32) / 255
            grain = 0.6 + 0.4 * grain
            wisps = [dict(bx=-10, A=15, f=1.6, ph=0.0, m=2.0, mp=0.1, w=1.1),
                     dict(bx=1, A=19, f=1.4, ph=2.3, m=2.4, mp=0.55, w=1.3),
                     dict(bx=11, A=13, f=1.8, ph=4.1, m=1.8, mp=0.85, w=1.0)]

            def steam(t, bw=bw, bh=bh, x0=x0, y0=y0, grain=grain, wisps=wisps):
                t = (t % 3.0) / 3.0  # своя петля 3 с, в 6-секундной — дважды
                can = Image.new("L", (bw * SS, bh * SS), 0)
                d = ImageDraw.Draw(can)
                for w in wisps:
                    S = 140
                    pts = []
                    for i in range(S + 1):
                        s = i / S
                        x = bw / 2 + k * (w["bx"] * (1 - 0.5 * s) + w["A"] * s ** 0.9 *
                                          math.sin(2 * math.pi * (w["f"] * s - t) + w["ph"]))
                        pts.append((x, bh - 1 - s * (bh - 6), s))
                    for i in range(S):
                        xa, ya, s = pts[i]
                        xb, yb, _ = pts[i + 1]
                        fade = min(1, s / 0.04) * max(0, min(1, (0.95 - s) / 0.45))
                        dash = 0.5 + 0.5 * math.sin(2 * math.pi * (w["m"] * s - 2 * t) + w["mp"] * 6.28)
                        a = fade * (0.3 + 0.7 * dash ** 1.3)
                        if a > 0.01:
                            d.line([(xa * SS, ya * SS), (xb * SS, yb * SS)], fill=int(255 * a),
                                   width=max(1, int((2.0 + 3.8 * s) * w["w"] * k * SS)))
                al = np.asarray(can.resize((bw, bh), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.9 * k)),
                                np.float32) / 255 * grain * steam_opacity
                return x0, y0, al, np.array([246, 241, 231], np.float32)
            layers.append(steam)

        elif kind == "bubbles":
            surf = (nums[2] / 100 * H) if len(nums) > 2 else py - 0.07 * H
            bw, bh = int(70 * k), int(py - surf + 20 * k)
            x0, y0 = int(px - 35 * k), int(surf - 10 * k)

            def bubbles(t, px=px, py=py, surf=surf, bw=bw, bh=bh, x0=x0, y0=y0):
                items = []
                for start in (0.6, 3.6):
                    for j in range(3):
                        age = t - (start + j * 0.28)
                        life = 1.45
                        if 0 <= age <= life:
                            p = age / life
                            y = py - p * (py - surf)
                            x = px + k * (-2 - j * 1.2 + 2.2 * math.sin(2 * math.pi * (p * 1.6 + j * 0.3)))
                            a = min(1, age / 0.12) * (1 if p < 0.85 else max(0, (1 - p) / 0.15))
                            items.append((x, y, k * (1.5 + 1.3 * p), a))
                if not items:
                    return None
                ring = Image.new("L", (bw * SS, bh * SS), 0)
                fill = Image.new("L", (bw * SS, bh * SS), 0)
                dr, df = ImageDraw.Draw(ring), ImageDraw.Draw(fill)
                for x, y, r, a in items:
                    X, Y, R = (x - x0) * SS, (y - y0) * SS, r * SS
                    dr.ellipse([X - R, Y - R, X + R, Y + R], outline=int(255 * a), width=max(1, int(0.8 * k * SS)))
                    df.ellipse([X - R, Y - R, X + R, Y + R], fill=int(255 * a * 0.15))
                    hr = R * 0.3
                    df.ellipse([X - R * 0.45 - hr, Y - R * 0.45 - hr, X - R * 0.45 + hr, Y - R * 0.45 + hr],
                               fill=int(255 * a * 0.8))
                al = np.maximum(np.asarray(ring.resize((bw, bh), Image.LANCZOS), np.float32),
                                np.asarray(fill.resize((bw, bh), Image.LANCZOS), np.float32)) / 255 * 0.8
                return x0, y0, al, np.array([236, 240, 236], np.float32)
            layers.append(bubbles)

        elif kind == "smoke":
            # ДЫМОК (04.10): одна тонкая белая струйка из трубы, чуть сносится ветром.
            # Точка — верх трубы. Вид — 🎬 smokeOpacity / smokeSize.
            s_op = _num("smokeOpacity", 0.8)
            s_sz = _num("smokeSize", 1.0)
            thick = nums[4] if len(nums) >= 5 and nums[4] > 0 else 1.0
            lean_px = 0.6 * 38 * k * s_sz                 # снос ветром по умолчанию
            if len(nums) >= 4:   # верхний конец струйки задан: высота и снос — как нарисовано
                top_y = nums[3] / 100 * H
                s_sz = max(0.3, (py - top_y) / (150 * k))
                lean_px = (nums[2] / 100 * W) - px
            sbw = int(max(90 * k * s_sz, abs(lean_px) + 60 * k * s_sz))
            sbh = int(150 * k * s_sz)
            # нарисованный верх — докуда струйку ещё видно: гаснет только в последней трети
            tail = 0.35 if len(nums) >= 4 else 0.6
            anchor = 0.3 if lean_px >= 0 else 0.7
            sx0, sy0 = int(px - sbw * anchor), int(py - sbh + 3 * k)
            sgrain = np.asarray(Image.fromarray(rng.uniform(0, 255, (sbh, sbw)).astype(np.uint8))
                                .filter(ImageFilter.GaussianBlur(0.6 * k)), np.float32) / 255
            sgrain = 0.55 + 0.45 * sgrain

            def smoke(t, sbw=sbw, sbh=sbh, sx0=sx0, sy0=sy0, sgrain=sgrain, s_op=s_op, s_sz=s_sz,
                      lean_px=lean_px, anchor=anchor, thick=thick, tail=tail):
                t = (t % EFFECTS_LOOP_SECONDS) / EFFECTS_LOOP_SECONDS
                can = Image.new("L", (sbw * SS, sbh * SS), 0)
                d = ImageDraw.Draw(can)
                S = 160
                pts = []
                for i in range(S + 1):
                    s_ = i / S
                    x = sbw * anchor + lean_px * s_ ** 1.4 + k * s_sz * 9 * s_ ** 0.8 * math.sin(2 * math.pi * (1.3 * s_ - t))
                    pts.append((x, sbh - 1 - s_ * (sbh - 4), s_))
                for i in range(S):
                    xa, ya, s_ = pts[i]
                    xb, yb, _ = pts[i + 1]
                    fade = (0.9 + 0.1 * min(1, s_ / 0.12)) * max(0, min(1, (1.0 - s_) / tail))
                    puff = 0.5 + 0.5 * math.sin(2 * math.pi * (2.2 * s_ - 2 * t))
                    a = fade * ((0.95 - 0.35 * s_) * (0.65 + 0.35 * puff ** 1.5))
                    if a > 0.01:
                        d.line([(xa * SS, ya * SS), (xb * SS, yb * SS)], fill=int(255 * a),
                               width=max(1, int((4.0 + 6.0 * s_) * k * min(s_sz, 1.6) * thick * SS)))
                al = np.asarray(can.resize((sbw, sbh), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.8 * k)),
                                np.float32) / 255 * sgrain * s_op
                return sx0, sy0, al, np.array([248, 246, 240], np.float32)
            layers.append(smoke)

        elif kind == "candle":
            # СВЕЧА (04.10): точка — середина пламени. Пламя подрагивает и дышит яркостью,
            # вокруг — тёплый ореол. Все частоты кратны петле — шва нет. Вид — 🎬 candleGlow.
            glow = _num("candleGlow", 1.0)
            px, py = snap_flame(base, px, py, W, H)      # точка — к самому яркому тёплому пятну рядом
            ph = rng.uniform(0, 2 * math.pi, 4)
            R = int(60 * k)
            gx0, gy0 = int(px - R), int(py - R)
            yy, xx = np.mgrid[0:2 * R, 0:2 * R].astype(np.float32)
            halo = np.exp(-((xx - R) ** 2 + (yy - R) ** 2) / (2 * (R * 0.42) ** 2))
            fw, fh = 3.2 * k, 8.5 * k

            def candle(t, gx0=gx0, gy0=gy0, halo=halo, R=R, ph=ph, glow=glow, fw=fw, fh=fh, px=px, py=py):
                L = EFFECTS_LOOP_SECONDS
                f = (0.55 * math.sin(2 * math.pi * 7 * t / L + ph[0]) + 0.3 * math.sin(2 * math.pi * 13 * t / L + ph[1])
                     + 0.15 * math.sin(2 * math.pi * 29 * t / L + ph[2]))
                sway = 1.6 * k * math.sin(2 * math.pi * 5 * t / L + ph[3])
                a = halo * (0.2 + 0.09 * f) * glow
                can = Image.new("L", (2 * R * SS, 2 * R * SS), 0)
                d = ImageDraw.Draw(can)
                cx, cy = (px - gx0 + sway) * SS, (py - gy0) * SS
                h_ = fh * (1 + 0.22 * f) * SS
                d.ellipse([cx - fw * SS, cy - h_ * 0.75, cx + fw * SS, cy + h_ * 0.35], fill=255)
                core = np.asarray(can.resize((2 * R, 2 * R), Image.LANCZOS)
                                  .filter(ImageFilter.GaussianBlur(1.2 * k)), np.float32) / 255
                a = np.maximum(a, core * (0.36 + 0.2 * f))
                col = np.empty((2 * R, 2 * R, 3), np.float32)
                col[...] = (255, 196, 120)
                col[core > 0.05] = (255, 238, 190)
                return gx0, gy0, np.clip(a, 0, 1), col
            layers.append(candle)

        elif kind == "rain" and len(nums) >= 4:
            # ДОЖДЬ ЗА ОКНОМ (04.10): прямоугольник стекла (левый верх → правый низ). За стеклом
            # тонкие струи, по стеклу изредка сползают капли. Видно только на тёмном стекле
            # (рама, цветок на подоконнике не трогаются). Петля бесшовная. Вид — 🎬 rainOpacity.
            r_op = _num("rainOpacity", 1.0)
            rx0, ry0 = int(min(nums[0], nums[2]) / 100 * W), int(min(nums[1], nums[3]) / 100 * H)
            rx1, ry1 = int(max(nums[0], nums[2]) / 100 * W), int(max(nums[1], nums[3]) / 100 * H)
            rx0, ry0, rx1, ry1 = (int(v) for v in snap_glass(base, rx0, ry0, rx1, ry1, W, H))   # к тёмному стеклу
            rw, rh = max(4, rx1 - rx0), max(4, ry1 - ry0)
            lum = base[ry0:ry0 + rh, rx0:rx0 + rw].mean(axis=2)
            dark = np.clip((175 - lum) / 90, 0, 1)            # стекло тёмное — там видно дождь
            n_st = max(12, int(rw * rh / (900 * k * k)))
            streaks = [dict(x=rng.uniform(0, rw), y=rng.uniform(0, rh), L=rng.uniform(10, 24) * k,
                            m=int(rng.integers(3, 6)), a=rng.uniform(0.35, 0.8)) for _ in range(n_st)]
            n_dr = max(2, int(rw / (90 * k)))
            drops = [dict(x=rng.uniform(0.08, 0.92) * rw, ph=rng.uniform(0, 1), wob=rng.uniform(0, 6.28))
                     for _ in range(n_dr)]
            slant = 0.12

            def rain(t, rx0=rx0, ry0=ry0, rw=rw, rh=rh, dark=dark, streaks=streaks, drops=drops, r_op=r_op):
                L = EFFECTS_LOOP_SECONDS
                can = Image.new("L", (rw * SS, rh * SS), 0)
                d = ImageDraw.Draw(can)
                for st in streaks:
                    span = rh + st["L"]
                    y = (st["y"] + st["m"] * span * t / L) % span - st["L"]
                    x = st["x"] + slant * y
                    d.line([(x * SS, y * SS), ((x + slant * st["L"]) * SS, (y + st["L"]) * SS)],
                           fill=int(255 * st["a"]), width=max(1, int(0.9 * k * SS)))
                for dr in drops:
                    u = (dr["ph"] + t / L) % 1.0                  # одна капля проходит стекло за петлю
                    y = u * (rh + 20 * k) - 10 * k
                    x = dr["x"] + 2.0 * k * math.sin(2 * math.pi * 2 * t / L + dr["wob"])
                    r = 2.4 * k
                    d.line([(x * SS, (y - 26 * k) * SS), (x * SS, y * SS)], fill=70, width=max(1, int(1.2 * k * SS)))
                    d.ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r * 1.3) * SS], fill=230)
                al = np.asarray(can.resize((rw, rh), Image.LANCZOS), np.float32) / 255 * 0.32 * r_op * dark
                return rx0, ry0, np.clip(al, 0, 1), np.array([214, 224, 236], np.float32)
            layers.append(rain)

        elif kind == "blink":
            # точный центр глаза — самая тёмная точка рядом с указанной
            # (тёмное рядом бывает и клювом — поэтому дальние точки «дороже»)
            # ищем шире (глаз рядом, но точка может промахнуться на пару процентов): тёмное круглое
            # пятно; размытие гасит тонкие линии рисунка, дальние точки чуть «дороже»
            rad = int(max(7 * k, 0.03 * W))
            gx0, gy0 = max(0, int(px) - rad), max(0, int(py) - rad)
            crop_l = src.convert("L").crop((gx0, gy0, gx0 + 2 * rad, gy0 + 2 * rad))
            lum = np.asarray(crop_l.filter(ImageFilter.GaussianBlur(1.2 * k)), np.float32)
            wide = np.asarray(crop_l.filter(ImageFilter.GaussianBlur(5.0 * k)), np.float32)
            gy_, gx_ = np.mgrid[0:lum.shape[0], 0:lum.shape[1]].astype(np.float32)
            # глаз — маленькое тёмное пятно на более светлом (пёрышки вокруг), а не просто тень
            cost = (lum - wide) + 0.25 * lum + 0.8 / k * np.hypot(gx_ + gx0 - px, gy_ + gy0 - py)
            iy, ix = np.unravel_index(np.argmin(cost), cost.shape)
            ex, ey = gx0 + ix + 0.5, gy0 + iy + 0.5
            # размер глаза меряем: тёмное пятно вокруг найденной точки (у канарейки глаз крошечный)
            loc = np.hypot(gx_ - ix, gy_ - iy) <= 8 * k          # окрестность самого глаза, не всё окно
            ring_l = float(np.median(lum[loc]))
            dark_ = lum < (lum[iy, ix] + ring_l) / 2
            near = np.hypot(gx_ - ix, gy_ - iy) <= 6 * k
            r = float(np.clip(math.sqrt(max(1.0, float((dark_ & near).sum())) / math.pi) + 0.8 * k, 1.6 * k, 5 * k))
            pad = int(r * 2.2)
            bx0, by0, bw, bh = int(ex) - pad, int(ey) - pad, 2 * pad, 2 * pad
            patch = base[by0:by0 + bh, bx0:bx0 + bw].copy()
            yy, xx = np.mgrid[0:bh, 0:bw].astype(np.float32)
            dist = np.hypot(xx + bx0 - ex, yy + by0 - ey)
            ring = (dist > r * 1.3) & (dist < r * 2.0)
            feather = patch[ring].mean(axis=0)  # цвет пёрышек вокруг глаза
            cover = np.clip((r * 1.25 - dist) / (0.5 * k + 1e-6), 0, 1)[..., None]
            closed = patch * (1 - cover) + feather * cover
            lid = Image.new("L", (bw * SS, bh * SS), 0)
            dl = ImageDraw.Draw(lid)
            q = r / (5 * k)   # веко — по размеру глаза
            dl.line([((ex - bx0 + dx) * SS, (ey - by0 + 0.4 * k * q + 1.8 * k * q * (1 - (dx / (4.2 * k * q)) ** 2)) * SS)
                     for dx in np.linspace(-4.2 * k * q, 4.2 * k * q, 20)],
                    fill=255, width=max(1, int(1.3 * k * max(q, 0.6) * SS)), joint="curve")
            la = np.asarray(lid.resize((bw, bh), Image.LANCZOS), np.float32)[..., None] / 255 * 0.85
            closed = closed * (1 - la) + np.array([78, 56, 34], np.float32) * la
            soft = np.clip((pad - np.maximum(abs(xx - pad), abs(yy - pad))) / (0.3 * pad), 0, 1)

            def blink(t, closed=closed, soft=soft, bx0=bx0, by0=by0):
                c = 0.0
                for at in (1.75, 4.40, 4.62):
                    if abs(t - at) < 0.09:
                        c = 1.0 if abs(t - at) < 0.045 else 0.5
                if not c:
                    return None
                return bx0, by0, soft * c, closed
            layers.append(blink)

    def compose(t):
        out = base.copy()
        for layer in layers:
            res = layer(t)
            if res is None:
                continue
            x0, y0, al, color = res
            h, w = al.shape[:2]
            ya, yb, xa, xb = max(0, y0), min(H, y0 + h), max(0, x0), min(W, x0 + w)
            a = al[ya - y0:yb - y0, xa - x0:xb - x0]
            a = a[..., None] if a.ndim == 2 else a
            col = color[ya - y0:yb - y0, xa - x0:xb - x0] if color.ndim == 3 else color
            out[ya:yb, xa:xb] = out[ya:yb, xa:xb] * (1 - a) + col * a
        return out

    if still_at is not None:   # превью: один кадр петли
        return compose(still_at)
    frames_dir = out_path + "_frames"
    os.makedirs(frames_dir, exist_ok=True)
    for f in range(n_frames):
        t = f / fps
        out = base.copy()
        for layer in layers:
            res = layer(t)
            if res is None:
                continue
            x0, y0, al, color = res
            h, w = al.shape[:2]
            ya, yb, xa, xb = max(0, y0), min(H, y0 + h), max(0, x0), min(W, x0 + w)
            a = al[ya - y0:yb - y0, xa - x0:xb - x0]
            a = a[..., None] if a.ndim == 2 else a
            col = color[ya - y0:yb - y0, xa - x0:xb - x0] if color.ndim == 3 else color
            out[ya:yb, xa:xb] = out[ya:yb, xa:xb] * (1 - a) + col * a
        Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(os.path.join(frames_dir, f"{f:04d}.png"))
    run_ffmpeg(["-framerate", str(fps), "-i", os.path.join(frames_dir, "%04d.png"),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", out_path])
    shutil.rmtree(frames_dir, ignore_errors=True)
    print(f"[effects] петля {EFFECTS_LOOP_SECONDS:g} с: " + ", ".join(k_ for k_, _ in spec))
    return out_path


# ЛИСТЬЯ (04.10): редкие события — лист срывается с ветки, падает и уходит за край
# (забор, скамейку) или ложится на землю переднего плана и растворяется в листве.
# Рисуется формулами, без нейросетей. Строки в fx_Effects строки выпуска:
#   листья: 46, 14 → 47, 88; продолговатый; раз в 240
#   листья: 46, 14 → 43, 45 → 47, 88   (путь через точки — как нарисовано)
#   листья: 23.5, 41 → 25, 63.5; круглый; маленький; вглубь; за край; раз в 120
#   край: 0 60.5, 16 61, 24 61.5, 40 64.5, 100 65
# Координаты — проценты кадра (откуда → куда). Слова: форма (продолговатый / круглый /
# клён), цвет (жёлтый, красный, оранжевый, охра, бурый; без цвета — из самой картинки),
# маленький / крупный, вглубь (уменьшается по пути), за край (прячется за линию «край»),
# раз в N (секунд; «раз в 4 мин» — минут), падает N (секунд полёта).
# Общий вид — 🎬 leafSize (длина листа в пикселях кадра высотой 864) и leafFallSeconds.
LEAF_COLORS = {
    "жёлт": (214, 168, 58), "желт": (214, 168, 58), "yellow": (214, 168, 58),
    "красн": (176, 62, 42), "red": (176, 62, 42),
    "оранж": (204, 112, 46), "orange": (204, 112, 46),
    "охр": (178, 128, 66), "ochre": (178, 128, 66),
    "бур": (128, 82, 48), "brown": (128, 82, 48),
}


def parse_leaves(text, data):
    """Строки «листья:» и «край:» из fx_Effects → список листьев и линия края."""
    def _num(key, default):
        try:
            v = float(data.get(key))
            return v if v > 0 else default
        except (TypeError, ValueError):
            return default
    size0 = _num("leafSize", 30.0)
    fall0 = _num("leafFallSeconds", 6.0)
    leaves, edge = [], []
    for line in str(text or "").splitlines():
        low = line.strip().lower()
        if low.startswith(("край", "edge")):
            body = low.split(":", 1)[-1]
            for pair in body.split(","):
                nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", pair)]
                if len(nums) >= 2:
                    edge.append((nums[0], nums[1]))
            continue
        if not low.startswith(("листья", "лист", "leaves", "leaf")):
            continue
        parts = [x.strip() for x in low.split(":", 1)[-1].split(";")]
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", parts[0])]
        if len(nums) < 4:
            print(f"[leaves] не поняла строку (нужно «x, y → x, y»): {line!r}")
            continue
        pairs = [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
        leaf = dict(frm=pairs[0], to=pairs[-1], via=pairs if len(pairs) > 2 else None, shape="long", colors=[],
                    size=size0, fall=fall0, shrink=1.0, behind=False, period=None)
        for w in parts[1:]:
            if "кругл" in w or "round" in w:
                leaf["shape"] = "round"
            elif "клён" in w or "клен" in w or "maple" in w:
                leaf["shape"] = "maple"
            elif "продолг" in w or "long" in w:
                leaf["shape"] = "long"
            if "маленьк" in w or "small" in w:
                leaf["size"] = size0 * 0.63
            if "крупн" in w or "больш" in w or "big" in w:
                leaf["size"] = size0 * 1.3
            if "вглубь" in w or "deep" in w:
                leaf["shrink"] = 0.75
            if "за край" in w or "за забор" in w or "behind" in w:
                leaf["behind"] = True
            m = re.search(r"раз в\s*(\d+(?:\.\d+)?)\s*(мин)?", w)
            if m:
                leaf["period"] = float(m.group(1)) * (60 if m.group(2) else 1)
            m = re.search(r"пада\w*\s*(\d+(?:\.\d+)?)", w)
            if m:
                leaf["fall"] = float(m.group(1))
            for name, rgb in LEAF_COLORS.items():
                if name in w:
                    leaf["colors"].append(rgb)
        leaves.append(leaf)
    return leaves, edge


def _leaf_outline_long(L):
    left, right, mid = [], [], []
    for i in range(61):
        u = i / 60
        w = 0.24 * L * math.sin(math.pi * u ** 0.75) ** 0.85 * (1 - 0.25 * u)
        teeth = 1 + (0.06 * (1 if math.sin(u * 34 * math.pi) > 0 else -1) if 0.12 < u < 0.92 else 0)
        bend = 0.05 * L * math.sin(math.pi * u)
        x = (u - 0.5) * L
        left.append((x, bend - w * teeth)); right.append((x, bend + 0.88 * w * teeth)); mid.append((x, bend))
    return left, right, mid


def _leaf_outline_round(L):
    left, right, mid = [], [], []
    for i in range(61):
        u = i / 60
        w = 0.40 * L * math.sin(math.pi * u ** 0.9) ** 0.6 * (1 - 0.15 * u)
        x = (u - 0.5) * L * 0.85
        bend = 0.03 * L * math.sin(math.pi * u)
        left.append((x, bend - w)); right.append((x, bend + 0.92 * w)); mid.append((x, bend))
    return left, right, mid


MAPLE_LOBES = [(-90, 1.0), (-35, 0.9), (35, 0.9), (-140, 0.62), (140, 0.62)]


def _leaf_outline_maple(L):
    pts = []
    for i in range(240):
        a = -180 + 360 * i / 240
        r = 0.34
        for ang, ln in MAPLE_LOBES:
            d = abs((a - (ang + 90) + 180) % 360 - 180)
            r = max(r, ln * (1 - (d / 34) ** 0.9) if d < 34 else 0)
        db = abs((a - 180 + 180) % 360 - 180)
        if db < 20:
            r *= 0.55 + 0.45 * db / 20
        r *= 0.5 * L * (1 + 0.04 * math.sin(math.radians(a) * 30))
        t = math.radians(a)
        pts.append((r * math.cos(t), r * math.sin(t)))
    return pts


def leaf_sprite(shape, color, ang, flip, L):
    """Непрозрачный рисованный лист: две половинки разного тона, контур и жилки карандашом.
    flip (−1…1) — поворот вокруг своей оси: сужает лист; при отрицательном видна светлая изнанка."""
    import numpy as np
    from PIL import Image, ImageDraw
    SS = 4
    R = int(L * 0.8) + 2
    can = Image.new("RGBA", (2 * R * SS, 2 * R * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(can)
    sq = 0.22 + 0.78 * abs(flip)
    under = flip < 0
    base_c = np.array(color, np.float32) * (1.12 if under else 1.0)
    light = tuple(int(min(255, v)) for v in base_c * 1.08)
    dark = tuple(int(v) for v in base_c * 0.82)
    line = tuple(int(v) for v in base_c * 0.42)
    ca, sa = math.cos(ang), math.sin(ang)
    T = lambda x, y: (R * SS + (x * ca - y * sq * sa) * SS, R * SS + (x * sa + y * sq * ca) * SS)
    lw = max(1, int(L / 30 * SS))
    if shape == "maple":
        pts = _leaf_outline_maple(L)
        d.polygon([T(*q) for q in pts], fill=(light if not under else dark) + (255,))
        half = [q for q in pts if q[1] >= 0] + [(0, 0)]
        d.polygon([T(*q) for q in half], fill=(dark if not under else light) + (255,))
        d.line([T(*q) for q in pts + pts[:1]], fill=line + (255,), width=lw)
        for ang_l, ln in MAPLE_LOBES:
            t = math.radians(ang_l + 90)
            d.line([T(0, 0), T(0.425 * L * ln * math.cos(t), 0.425 * L * ln * math.sin(t))],
                   fill=line + (170,), width=max(1, lw // 2 + 1))
        d.line([T(-0.08 * L, 0), T(-0.42 * L, 0.03 * L)], fill=line + (255,), width=lw + 1)
    else:
        left, right, mid = (_leaf_outline_round if shape == "round" else _leaf_outline_long)(L)
        d.polygon([T(*q) for q in left + mid[::-1]], fill=(light if not under else dark) + (255,))
        d.polygon([T(*q) for q in right + mid[::-1]], fill=(dark if not under else light) + (255,))
        d.line([T(*q) for q in left], fill=line + (255,), width=lw)
        d.line([T(*q) for q in right], fill=line + (255,), width=lw)
        d.line([T(*q) for q in mid], fill=line + (230,), width=lw)
        for j in range(1, 7):
            i = int(len(mid) * j / 8)
            for side_pts in (left, right):
                mx, my = mid[i]
                ex, ey = side_pts[min(len(side_pts) - 1, i + 6)]
                d.line([T(mx, my), T(mx + (ex - mx) * 0.85, my + (ey - my) * 0.85)],
                       fill=line + (150,), width=max(1, lw // 2 + 1))
        bx = left[0][0]
        d.line([T(bx, 0), T(bx - 0.18 * L, 0.04 * L)], fill=line + (255,), width=lw + 1)
    return np.asarray(can.resize((2 * R, 2 * R), Image.LANCZOS), np.float32)


def leaf_path(x0, y0, x1, y1, seconds, fps, seed, swing, half=1.15, via=None):
    """Полёт по физике падающей пластинки (Andersen, Pesavento, Wang, 2005) и правилу дуг:
    лист скользит дугой вбок — в середине быстрее и ниже, носом по ходу; у края дуги
    замедляется, чуть приподнимается, на миг встаёт ребром и скользит обратно.
    Первая дуга короче — лист только что сорвался. Дуги немного разные."""
    import numpy as np
    r = np.random.default_rng(int(seed * 1000) + 1)
    n = max(2, int(round(seconds / half)))
    durs = r.uniform(0.85, 1.15, n)
    durs = durs / durs.sum() * seconds
    amps = r.uniform(0.75, 1.2, n) * swing
    amps[0] *= 0.45
    drops = r.uniform(0.8, 1.2, n)
    drops[0] *= 0.5
    drops = drops / drops.sum() * (y1 - y0)
    tumble = r.random(n) < 0.25
    d0 = 1 if r.random() < 0.5 else -1
    path, t_acc, y_acc, side, i = [], 0.0, 0.0, 1.0, 0
    for f in range(int(seconds * fps) + 1):
        t = f / fps
        while i < n - 1 and t > t_acc + durs[i]:
            t_acc += durs[i]; y_acc += drops[i]
            if tumble[i]:
                side = -side
            i += 1
        s_ = min(1.0, (t - t_acc) / durs[i])
        dirn = d0 * (1 if i % 2 == 0 else -1)
        A, d = amps[i], drops[i]
        p = (y_acc + d * s_) / (y1 - y0)
        if via:   # путь, нарисованный автором: середина качания идёт по её линии
            vy = [q[1] for q in via]
            order = np.argsort(vy)
            cx = float(np.interp(y0 + y_acc + d * s_, np.array(vy)[order], np.array([q[0] for q in via])[order]))
        else:
            cx = x0 + (x1 - x0) * p
        x = cx + dirn * A * -math.cos(math.pi * s_)
        y = y0 + y_acc + d * s_ - 0.36 * d * (1 - math.sin(math.pi * s_))
        ang = dirn * 0.55 * math.sin(math.pi * s_) + 0.15
        flip = side * (0.3 + 0.7 * math.sin(math.pi * s_) ** 0.6)
        path.append((x, y, ang, flip))
    return path


def render_leaf_event(image_path, leaf, edge, fps, seed, out_path, mask_path):
    """Клип события: картинка + один падающий лист, и рядом маска — где лист и насколько
    он непрозрачен (поверх петли лист кладётся по этой маске, без догадок по разнице кадров).
    Начинается и кончается чистой картинкой."""
    import sys as _sys
    if "/app/pylibs" not in _sys.path:
        _sys.path.insert(0, "/app/pylibs")
    import numpy as np
    from PIL import Image
    src = Image.open(image_path).convert("RGB")
    W, H = src.size
    base = np.asarray(src, np.float32)
    k = H / 864.0
    rng = np.random.default_rng(int(seed * 1000) + 7)
    if leaf["colors"]:
        color = np.array(leaf["colors"][int(rng.integers(len(leaf["colors"])))], np.float32)
    else:  # из самой картинки: самые насыщенные тёплые цвета
        pix = base.reshape(-1, 3)
        sat = pix[(pix[:, 0] - pix[:, 2] > 75) & (pix[:, 0] > 120)]
        if len(sat) < 50:
            color = np.array(LEAF_COLORS["охр"], np.float32)
        else:
            sat = sat[np.argsort(sat[:, 0] - sat[:, 2])][-max(50, len(sat) // 5):]
            pal = [np.median(c, axis=0) * 0.92 for c in np.array_split(sat[np.argsort(sat[:, 1])], 3)]
            color = pal[int(rng.integers(len(pal)))]
    P = lambda xy: (xy[0] / 100 * W, xy[1] / 100 * H)
    L0 = leaf["size"] * k
    fall = leaf["fall"]
    rest = 0.0 if leaf["behind"] else 4.0      # на переднем плане — лежит и растворяется в листве
    (x0, y0), (x1, y1) = P(leaf["frm"]), P(leaf["to"])
    via = [P(q) for q in leaf["via"]] if leaf.get("via") else None
    path = leaf_path(x0, y0, x1, y1, fall, fps, seed, L0 * 1.1, via=via)
    ex = [e[0] / 100 * W for e in edge] if (leaf["behind"] and edge) else None
    ey = [e[1] / 100 * H for e in edge] if ex else None
    frames_dir = out_path + "_frames"
    masks_dir = out_path + "_masks"
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(masks_dir, exist_ok=True)
    n = int((fall + rest + 0.5) * fps)
    for f in range(n):
        age = f / fps
        out = base.copy()
        mask = np.zeros((H, W), np.float32)
        if age <= fall + rest:
            x, y, ang, flip = path[min(len(path) - 1, int(age * fps))]
            lying = age > fall
            if lying:
                ang, flip = 0.35, 1.0
            L = L0 * (1 + (leaf["shrink"] - 1) * min(1.0, age / fall))
            spr = leaf_sprite(leaf["shape"], color, ang, flip, L)
            al = spr[..., 3] / 255 * min(1, age / 0.3)
            if lying:
                al = al * (1 - (age - fall) / rest) ** 1.6
            h, w = al.shape
            lx0, ly0 = int(x - w / 2), int(y - h / 2)
            if ex:   # ниже края — за краем: не рисуем
                fy = np.interp(np.arange(w) + lx0, ex, ey)
                al = al * ((np.arange(h) + ly0)[:, None] < fy[None, :])
            ya, yb, xa, xb = max(0, ly0), min(H, ly0 + h), max(0, lx0), min(W, lx0 + w)
            if ya < yb and xa < xb:
                a = al[ya - ly0:yb - ly0, xa - lx0:xb - lx0][..., None]
                c = spr[ya - ly0:yb - ly0, xa - lx0:xb - lx0, :3]
                out[ya:yb, xa:xb] = out[ya:yb, xa:xb] * (1 - a) + c * a
                mask[ya:yb, xa:xb] = a[..., 0]
        Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(os.path.join(frames_dir, f"{f:04d}.png"))
        Image.fromarray(np.clip(mask * 255, 0, 255).astype(np.uint8)).save(os.path.join(masks_dir, f"{f:04d}.png"))
    for d_, o_ in ((frames_dir, out_path), (masks_dir, mask_path)):
        run_ffmpeg(["-framerate", str(fps), "-i", os.path.join(d_, "%04d.png"),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-pix_fmt", "yuv420p", o_])
        shutil.rmtree(d_, ignore_errors=True)
    return out_path


def plan_body_periodic(duration, intro, loop_len, events, seed):
    """Как plan_body, но у каждого события своя частота: events = [(длина, период_сек)].
    Моменты событий — вокруг кратных периоду, с разбросом ±25 %; совпали — следующее позже."""
    rnd = random.Random(seed)
    unit = loop_len if loop_len else 10.0
    big = unit * max(1, round(60 / unit))
    base = "loop" if loop_len else "still"
    times = []
    for i, (ln, period) in enumerate(events):
        t = intro + rnd.uniform(0.3, 1.0) * period
        while t < duration:
            times.append((t, i))
            t += period * rnd.uniform(0.75, 1.25)
    times.sort()
    parts, cur = [], intro

    def fill(gap):
        n_big, rest = int(gap // big), gap % big
        n_small = int(round(rest / unit))
        parts.extend([(base, big)] * n_big + [(base, unit)] * n_small)
        return n_big * big + n_small * unit

    for t, i in times:
        if t > cur:
            cur += fill(t - cur)
        if cur >= duration:
            break
        parts.append(("event", i)); cur += events[i][0]
    while cur < duration:
        parts.append((base, big)); cur += big
    return parts, big



def build_video_from_pieces(data, work_dir, image_path, audio_path, duration, base_chain,
                            shadow_layers, main_layers, shadow_blur, overlay_visible_until,
                            audio_chain, output_path, project_id):
    def _f(key, default):
        try:
            v = float(data.get(key) or default)
            return v if v > 0 else default
        except (TypeError, ValueError):
            return default
    fps = int(_f("videoFps", 24))
    gap_min = _f("eventGapMinSeconds", 60)
    gap_max = max(gap_min, _f("eventGapMaxSeconds", 240))
    loop_url = str(data.get("fx_LoopUrl") or "").strip()
    event_urls = [u for u in re.split(r"[\s,;]+", str(data.get("fx_EventUrls") or "")) if u.startswith("http")]
    pdir = os.path.join(work_dir, "pieces"); os.makedirs(pdir, exist_ok=True)

    loop_path, loop_len = None, 0.0
    if loop_url:
        raw = download_media(loop_url, os.path.join(pdir, "loop_src.mp4"))
        loop_path = normalize_clip(raw, os.path.join(pdir, "loop_norm.mp4"), fps)
        loop_len = media_duration(loop_path)
    effects = parse_effects(data.get("fx_Effects"))
    if effects and loop_path:
        print("[effects] есть fx_LoopUrl — эффекты пропускаю (одна петля на видео)")
    elif effects:
        raw = render_effects_loop(image_path, effects, data, fps, os.path.join(pdir, "effects_src.mp4"))
        loop_path = normalize_clip(raw, os.path.join(pdir, "loop_norm.mp4"), fps)
        loop_len = media_duration(loop_path)
    events = []
    periods = []
    masks = {}   # номер события → его маска (у листьев); у остальных маски нет
    for i, u in enumerate(event_urls):
        raw = download_media(u, os.path.join(pdir, f"event{i}_src.mp4"))
        ev = normalize_clip(raw, os.path.join(pdir, f"event{i}_norm.mp4"), fps)
        ln = media_duration(ev)
        if loop_len:  # событие поверх петли — длина кратна петле
            ln = loop_len * max(1, -(-ln // loop_len))
        events.append((ev, ln))
        periods.append(None)
    leaves, edge = parse_leaves(data.get("fx_Effects"), data)
    for j, leaf in enumerate(leaves):
        try:
            raw = render_leaf_event(image_path, leaf, edge, fps, 1.3 + 2.9 * j,
                                    os.path.join(pdir, f"leaf{j}_src.mp4"), os.path.join(pdir, f"leaf{j}_mask_src.mp4"))
            mask = normalize_clip(os.path.join(pdir, f"leaf{j}_mask_src.mp4"), os.path.join(pdir, f"leaf{j}_mask.mp4"), fps)
        except Exception as leaf_error:  # лист — украшение, сборку не роняем
            print(f"[leaves] лист {j + 1} не получился: {leaf_error}")
            continue
        ev = normalize_clip(raw, os.path.join(pdir, f"leaf{j}_norm.mp4"), fps)
        ln = media_duration(ev)
        if loop_len:
            ln = loop_len * max(1, -(-ln // loop_len))
        events.append((ev, ln))
        masks[len(events) - 1] = mask
        periods.append(leaf["period"] or (gap_min + gap_max) / 2)
    if leaves:
        print(f"[leaves] листьев: {len(leaves)}, раз в " + ", ".join(f"{p:g} с" for p in periods if p))
    mode = ("петля + события" if loop_path and events else "петля" if loop_path
            else "события" if events else "статика")
    print(f"[video] тело: {mode}, {fps} кадров/с")

    intro = float(int(overlay_visible_until) + 2)
    if loop_len:
        intro = loop_len * max(1, -(-intro // loop_len))
    pieces = [render_intro_piece(image_path, loop_path, intro, base_chain, shadow_layers,
                                 main_layers, shadow_blur, fps, os.path.join(pdir, "intro.mp4"))]
    if any(p is not None for p in periods):
        avg = (gap_min + gap_max) / 2
        parts, big = plan_body_periodic(duration, intro, loop_len,
                                        [(e[1], p or avg) for e, p in zip(events, periods)], project_id)
    else:
        parts, big = plan_body(duration, intro, loop_len, [e[1] for e in events], gap_min, gap_max,
                               project_id)
    cache = {}
    for kind, val in parts:
        key = (kind, val)
        if key not in cache:
            out = os.path.join(pdir, f"{kind}_{str(val).replace('.', '_')}.mp4")
            if kind == "still":
                cache[key] = render_still_piece(image_path, val, base_chain, fps, out)
            elif kind == "loop":
                cache[key] = render_loop_piece(loop_path, val, base_chain, fps, out)
            else:
                ev, ln = events[val]
                if val in masks:
                    cache[key] = render_masked_event_piece(ev, masks[val], image_path, loop_path, ln,
                                                           base_chain, fps, out)
                else:
                    cache[key] = render_event_piece(ev, image_path, loop_path, ln, base_chain, fps, out)
        pieces.append(cache[key])

    list_path = os.path.join(pdir, "list.txt")
    with open(list_path, "w") as f:
        for p in pieces:
            f.write(f"file '{os.path.abspath(p)}'\n")
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", list_path, "-i", audio_path,
                "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", audio_chain,
                "-c:a", "aac", "-b:a", "384k", "-t", str(duration),
                "-movflags", "+faststart", output_path])
    print(f"[video] кусков: {len(pieces)}, разных: {len(cache) + 1}")
    return output_path


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
        try:
            grade_image(image_path, data)
        except Exception as grade_error:  # фильтр — украшение, сборку не роняем
            print(f"[grade] не удалось: {grade_error}")
        fade_in_seconds = float(data.get("fadeInSeconds", 1.5))
        fade_out_seconds = float(data.get("fadeOutSeconds", 3))
        gap_seconds = float(data.get("gapSeconds", 0))
        loop_count_raw = data.get("loopCount")
        loop_count = int(loop_count_raw) if loop_count_raw not in (None, "") else None
        compressor_threshold_db = float(data.get("compressorThresholdDb", -20))
        compressor_ratio = float(data.get("compressorRatio", 2))
        compressor_attack_sec = float(data.get("compressorAttackSec", 0.02))
        compressor_release_sec = float(data.get("compressorReleaseSec", 0.25))
        limiter_ceiling = float(data.get("limiterCeiling", 0.89))
        limiter_attack_ms = float(data.get("limiterAttackMs", 5))
        limiter_release_ms = float(data.get("limiterReleaseMs", 50))
        denoise_amount = float(data.get("denoiseAmount", 0))
        try:
            highs_db = -abs(float(data.get("highsDb", 0) or 0))      # всегда вниз: «на сколько тише верха»
        except (TypeError, ValueError):
            highs_db = 0.0
        try:
            highs_hz = float(data.get("highsHz", 7000) or 7000)
        except (TypeError, ValueError):
            highs_hz = 7000.0
        loudness_report = []
        audio_path, duration = build_audio_track(
            audio_zip_url, work_dir, loudness_report=loudness_report,
            target_lufs=target_lufs,
            fade_in_seconds=fade_in_seconds,
            fade_out_seconds=fade_out_seconds,
            gap_seconds=gap_seconds,
            loop_count=loop_count,
            compressor_threshold_db=compressor_threshold_db,
            compressor_ratio=compressor_ratio,
            compressor_attack_sec=compressor_attack_sec,
            compressor_release_sec=compressor_release_sec,
            limiter_ceiling=limiter_ceiling,
            limiter_attack_ms=limiter_attack_ms,
            limiter_release_ms=limiter_release_ms,
            denoise_amount=denoise_amount,
            highs_db=highs_db, highs_hz=highs_hz,
        )

        # НОВОЕ: проверка громкости готового файла — не блокирует сборку,
        # просто пишет в лог сервера, если что-то разъехалось с целью.
        check_loudness(audio_path, target_lufs)
        if loudness_report:
            report_text = format_loudness_report(loudness_report, target_lufs)
            print(report_text)
            try:
                os.makedirs(THUMBNAIL_DIR, exist_ok=True)
                with open(os.path.join(THUMBNAIL_DIR, f"{project_id}_loudness.txt"), "w", encoding="utf-8") as fh:
                    fh.write(report_text + "\n")
            except Exception as report_error:
                print(f"[громкость] отчёт не записан: {report_error}")

        fps = 5
        duration_frames = int(duration * fps)

        video_filters = collect_fx_filters(data, EFFECT_VIDEO_REGISTRY, duration_frames)
        if not video_filters:
            video_filters.append(f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}")

        # НОВОЕ (24.09): эффекты из таблицы — пусто или 0 = выключено.
        def _num(key):
            try:
                return float(data.get(key) or 0)
            except (TypeError, ValueError):
                return 0.0
        pixel_shift = int(_num("pixelShift"))
        old_film = _num("oldFilm")
        if pixel_shift > 0:
            video_filters.extend(pixel_shift_filters(pixel_shift))
            print(f"[effects] сдвиг пикселей ±{pixel_shift}")
        if old_film > 0:
            video_filters.extend(old_film_filters(old_film))
            print(f"[effects] старая плёнка, сила {old_film:g}")

        overlay_margin = int(data.get("overlayMargin", 60))

        font_name = data.get("overlayFont")
        font_path = FONT_MAP.get(font_name, DEFAULT_FONT_PATH)
        font_size = data.get("overlaySize", "44")
        font_color = data.get("overlayColor", "#FFFFFF").lstrip("#")

        # НОВОЕ: было только "if(lt(t,15),1,if(lt(t,18),(18-t)/3,0))" — то есть
        # мгновенное появление, потом 3 секунды угасания. Добавлено
        # симметричное появление: первые 3 секунды текст плавно проявляется,
        # с 3 по 15 держится на полной видимости, с 15 по 18 гаснет.
        # НОВОЕ (27.09): длительность появления и угасания — из таблицы
        # (🎬tmpl_OverlayFadeInSeconds / 🎬tmpl_OverlayFadeOutSeconds). При 5
        # кадрах в секунду короткое угасание видно ступеньками — чем дольше
        # фейд, тем мельче каждая ступенька. Полная видимость по-прежнему до
        # 15-й секунды; без значений в таблице — прежние 3 и 3 секунды.
        def _fade(key, default):
            try:
                v = float(data.get(key) or default)
                return v if v > 0 else default
            except (TypeError, ValueError):
                return default
        overlay_fade_in = _fade("overlayFadeInSeconds", 3.0)
        overlay_fade_out = _fade("overlayFadeOutSeconds", 3.0)
        overlay_hold_until = max(15.0, overlay_fade_in)
        overlay_visible_until = overlay_hold_until + overlay_fade_out
        overlay_alpha = (
            f"if(lt(t,{overlay_fade_in:g}),t/{overlay_fade_in:g},"
            f"if(lt(t,{overlay_hold_until:g}),1,"
            f"if(lt(t,{overlay_visible_until:g}),({overlay_visible_until:g}-t)/{overlay_fade_out:g},0)))"
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
        try:
            overlay_line_spacing = float(data.get("overlayLineSpacing") or 0.875)
        except (TypeError, ValueError):
            overlay_line_spacing = 0.875
        shadow_layers, main_layers = build_overlay_drawtext(
            overlay_text, overlay_position, font_path, font_size,
            font_color, shadow_color, shadow_opacity, overlay_alpha,
            margin=overlay_margin, line_spacing=overlay_line_spacing,
            visible_until=f"{overlay_visible_until:g}",
        )

        # ОТКАЧЕНО (20.09): 19.09 ночью сюда добавили фейд ВСЕГО видео целиком
        # (вход из чёрного/выход в чёрный), синхронизировав его с
        # tmpl_FadeInSeconds/tmpl_FadeOutSeconds — предыдущая версия этой
        # правки решила, что раз эти значения используются для звука, то
        # должны так же плавно затемнять и картинку. Автор это не заказывала:
        # fade-in/out у неё всегда были только про звук, картинка должна
        # быть видна с первого кадра без затемнения. Картинка больше не
        # фейдится — только звук (см. audio_fade ниже).
        if shadow_layers:
            # Собираем отдельный граф: [0:v] -> база со scale/эффектами;
            # прозрачный слой того же размера -> текст тенью (одна или две
            # строки, см. build_overlay_drawtext) -> размытие -> наложение
            # под базу -> резкий текст поверх.
            shadow_chain = ";".join(
                f"[{'shadowbg' if i == 0 else f'sh{i}'}]{f}[sh{i + 1}]"
                for i, f in enumerate(shadow_layers)
            )
            main_chain = ";".join(
                f"[{'with_shadow' if i == 0 else f'm{i}'}]{f}[{f'm{i + 1}' if i + 1 < len(main_layers) else 'v'}]"
                for i, f in enumerate(main_layers)
            )
            video_chain_graph = (
                f"[0:v]{base_chain}[base];"
                f"color=c=black@0.0:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:r={fps}:d={duration}[shadowbg];"
                f"{shadow_chain};"
                f"[sh{len(shadow_layers)}]gblur=sigma={shadow_blur}[shadow_blurred];"
                f"[base][shadow_blurred]overlay=0:0[with_shadow];"
                f"{main_chain}"
            )
        else:
            video_chain_graph = f"[0:v]{base_chain}[v]"

        audio_filters = collect_fx_filters(data, EFFECT_AUDIO_REGISTRY)
        # Та же логика fade, но для звука — тихий, плавный вход/выход у всей
        # аудиодорожки целиком, той же длиной и той же формой кривой (tri),
        # что и межтрековые фейды — см. комментарий у per-track фейда выше.
        audio_fade = (
            f"afade=t=in:st=0:d={fade_in_seconds}:curve=tri,"
            f"afade=t=out:st={duration-fade_out_seconds}:d={fade_out_seconds}:curve=tri"
        )
        audio_chain = ",".join(audio_filters + [audio_fade]) if audio_filters else audio_fade

        output_path = os.path.join(work_dir, f"{project_id}.mp4")
        # НОВОЕ (25.09): картинка подаётся сразу с частотой fps (5 кадров/с),
        # а не 25 по умолчанию. Раньше -r 5 на выходе лишь выбрасывал кадры
        # В КОНЦЕ, а все фильтры (масштаб, размытая тень надписи, сдвиг
        # пикселей, плёнка) честно считали все 25 кадров в секунду на весь
        # час видео — 4 из 5 кадров впустую. Картинка статична, результат
        # тот же; слой тени (color=...:r=fps) — с той же частотой.
        # Зум и сдвиг пикселей меняются на протяжении всего видео — для них
        # прежняя сборка одним проходом; во всех остальных случаях — кусками.
        if not data.get("fx_ZoomEnabled") and pixel_shift <= 0:
            build_video_from_pieces(
                data, work_dir, image_path, audio_path, duration, base_chain,
                shadow_layers, main_layers, shadow_blur, overlay_visible_until,
                audio_chain, output_path, project_id)
        else:
            run_ffmpeg([
                "-loop", "1", "-framerate", str(fps), "-i", image_path,
                "-i", audio_path,
                "-filter_complex",
                f"{video_chain_graph};[1:a]{audio_chain}[a]",
                "-map", "[v]", "-map", "[a]",
                "-t", str(duration),
                "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "384k",
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
            run_ffmpeg(["-ss", f"{(overlay_fade_in + overlay_hold_until) / 2:g}", "-i", output_path, "-frames:v", "1", thumbnail_path])
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


# НОВОЕ (02.10): отчёт о громкости последней сборки выпуска (текст).
@app.route("/loudness/<project_id>", methods=["GET"])
def get_loudness_report(project_id):
    report_path = os.path.join(THUMBNAIL_DIR, f"{project_id}_loudness.txt")
    if not os.path.exists(report_path):
        return "отчёта нет: выпуск ещё не собирался этой версией сборщика\n", 404
    return send_file(report_path, mimetype="text/plain; charset=utf-8")


@app.route("/clean_start", methods=["POST"])
def clean_start_route():
    try:
        return jsonify(clean_start(request.json or {}))
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 200


@app.route("/clean_status", methods=["POST"])
def clean_status_route():
    try:
        return jsonify(clean_status(request.json or {}))
    except Exception as e:
        return jsonify({"state": "unknown", "message": str(e)}), 200



# ПРЕВЬЮ ОЖИВЛЕНИЯ (04.10). /fx_grid — картинка выпуска с сеткой процентов: её видит
# тот, кто предлагает места оживления, и читает координаты с сетки, а не на глаз.
# /fx_preview — картинка для автора: дымок/пар/пузыри нарисованы как в ролике, полёт
# каждого листа — его положениями через доли секунды, край — пунктиром.
def _fx_image(url, work_dir):
    import sys as _sys
    if "/app/pylibs" not in _sys.path:
        _sys.path.insert(0, "/app/pylibs")
    return download_file(url, os.path.join(work_dir, "image.jpg"))


def draw_percent_grid(image_path, out_path):
    from PIL import Image, ImageDraw
    im = Image.open(image_path).convert("RGB")
    W, H = im.size
    over = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    lw = max(1, H // 600)
    for p in range(5, 100, 5):
        x, y = W * p / 100, H * p / 100
        strong = p % 10 == 0
        col = (20, 40, 160, 150 if strong else 80)
        d.line([(x, 0), (x, H)], fill=col, width=lw)
        col = (170, 20, 20, 150 if strong else 80)
        d.line([(0, y), (W, y)], fill=col, width=lw)
    fs = max(10, H // 45)
    for p in range(10, 100, 10):
        x, y = W * p / 100, H * p / 100
        for (tx, ty, txt, c) in ((x + 3, 2, str(p), (20, 40, 160)), (x + 3, H - fs - 4, str(p), (20, 40, 160)),
                                 (3, y + 2, str(p), (170, 20, 20)), (W - 2.2 * fs, y + 2, str(p), (170, 20, 20))):
            d.rectangle([tx - 2, ty - 1, tx + len(txt) * fs * 0.62 + 2, ty + fs + 2], fill=(255, 255, 255, 190))
            d.text((tx, ty), txt, fill=c + (255,))
    Image.alpha_composite(im.convert("RGBA"), over).convert("RGB").save(out_path, quality=88)
    return out_path


# ── ЛУПА (05.10): увеличенные кусочки вокруг точек эффектов — чтобы Аниматор уточнил их ──
# Для каждой точки строки оживления (верх трубы, пламя, глаз, поверхность, углы стекла)
# вырезается квадрат вокруг неё, увеличивается в 3 раза и размечается сеткой через 1 %
# с подписями в процентах ВСЕГО кадра. Текущая точка — голубой кружок.
ZOOM_POINTS = {
    "smoke": ["верх трубы"], "steam": ["поверхность напитка или воды"], "bubbles": ["рот рыбки"],
    "blink": ["глаз птицы"], "candle": ["середина пламени свечи"],
    "rain": ["левый верхний угол стекла", "правый нижний угол стекла"],
}


def zoom_points(image_path, fx_text, half_pct=10.0, scale=3):
    import base64, io
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(image_path).convert("RGB")
    W, H = im.size
    try:
        font = ImageFont.load_default(size=max(12, int(13 * scale / 3 * 1.2)))
    except TypeError:
        font = ImageFont.load_default()
    out = []
    for li, line in enumerate(str(fx_text or "").splitlines()):
        m = re.match(r"\s*([^\d:,\-]+?)\s*[:\-]?\s*(-?[\d.].*)$", line)
        if not m or line.strip().lower().startswith(EVENT_EFFECT_WORDS):
            continue
        kind = EFFECT_NAMES.get(m.group(1).strip().lower())
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", m.group(2))]
        for pi, label in enumerate(ZOOM_POINTS.get(kind, [])):
            if len(nums) < 2 * pi + 2:
                continue
            x, y = nums[2 * pi], nums[2 * pi + 1]
            hp = half_pct / 100 * W
            cx, cy = x / 100 * W, y / 100 * H
            x0, y0 = int(max(0, min(W - 2 * hp, cx - hp))), int(max(0, min(H - 2 * hp, cy - hp)))
            x1, y1 = int(min(W, x0 + 2 * hp)), int(min(H, y0 + 2 * hp))
            crop = im.crop((x0, y0, x1, y1)).resize(((x1 - x0) * scale, (y1 - y0) * scale), Image.LANCZOS)
            d = ImageDraw.Draw(crop, "RGBA")
            for k in range(int(x0 / W * 100), int(x1 / W * 100) + 2):
                px = (k / 100 * W - x0) * scale
                if 0 <= px < crop.width:
                    d.line([(px, 0), (px, crop.height)], fill=(20, 40, 160, 150 if k % 5 == 0 else 70), width=1)
                    d.rectangle([px + 1, 1, px + 30, 17], fill=(255, 255, 255, 200))
                    d.text((px + 3, 2), str(k), fill=(20, 40, 160, 255), font=font)
            for k in range(int(y0 / H * 100), int(y1 / H * 100) + 2):
                py = (k / 100 * H - y0) * scale
                if 0 <= py < crop.height:
                    d.line([(0, py), (crop.width, py)], fill=(170, 20, 20, 150 if k % 5 == 0 else 70), width=1)
                    d.rectangle([1, py + 1, 30, py + 17], fill=(255, 255, 255, 200))
                    d.text((3, py + 2), str(k), fill=(170, 20, 20, 255), font=font)
            mx, my = (cx - x0) * scale, (cy - y0) * scale
            d.ellipse([mx - 9, my - 9, mx + 9, my + 9], outline=(0, 190, 220, 255), width=2)
            buf = io.BytesIO()
            crop.save(buf, format="JPEG", quality=88)
            out.append({"id": f"{li}:{pi}", "line": li, "pair": pi, "kind": kind, "label": label,
                        "x": x, "y": y, "dataUrl": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()})
    return out


def draw_fx_preview(image_path, fx_text, data, out_path):
    import numpy as np
    from PIL import Image, ImageDraw
    effects = parse_effects(fx_text)
    if effects:
        frame = render_effects_loop(image_path, effects, data, 24, out_path + ".mp4", still_at=2.0)
    else:
        frame = np.asarray(Image.open(image_path).convert("RGB"), np.float32)
    H, W = frame.shape[:2]
    k = H / 864.0
    leaves, edge = parse_leaves(fx_text, data)
    for j, leaf in enumerate(leaves):
        seed = 1.3 + 2.9 * j
        rng = np.random.default_rng(int(seed * 1000) + 7)
        color = np.array(LEAF_COLORS["оранж"], np.float32)   # на превью — всегда оранжевый, не красный
        P = lambda xy: (xy[0] / 100 * W, xy[1] / 100 * H)
        (x0, y0), (x1, y1) = P(leaf["frm"]), P(leaf["to"])
        L0 = leaf["size"] * k
        via = [P(q) for q in leaf["via"]] if leaf.get("via") else None
        path = leaf_path(x0, y0, x1, y1, leaf["fall"], 24, seed, L0 * 1.1, via=via)
        ex = [e[0] / 100 * W for e in edge] if (leaf["behind"] and edge) else None
        ey = [e[1] / 100 * H for e in edge] if ex else None
        step = 8   # положение через треть секунды
        # тонкая линия пути — чтобы маленький лист было видно на превью
        trail = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8))
        dtr = ImageDraw.Draw(trail)
        pts = [(q[0], q[1]) for q in path]
        if ex:
            pts = [(x, y) for x, y in pts if y < float(np.interp(x, ex, ey))]
        for i in range(0, len(pts) - 1, 2):
            dtr.line([pts[i], pts[i + 1]], fill=(200, 90, 30), width=max(1, int(1.5 * k)))
        frame = np.asarray(trail, np.float32).copy()
        for i in range(0, len(path), step):
            x, y, ang, flip = path[i]
            L = L0 * (1 + (leaf["shrink"] - 1) * i / max(1, len(path) - 1))
            spr = leaf_sprite(leaf["shape"], color, ang, flip, L)
            al = spr[..., 3] / 255 * (0.55 + 0.45 * i / max(1, len(path) - 1))
            h, w = al.shape
            lx0, ly0 = int(x - w / 2), int(y - h / 2)
            if ex:
                fy = np.interp(np.arange(w) + lx0, ex, ey)
                al = al * ((np.arange(h) + ly0)[:, None] < fy[None, :])
            ya, yb, xa, xb = max(0, ly0), min(H, ly0 + h), max(0, lx0), min(W, lx0 + w)
            if ya < yb and xa < xb:
                a = al[ya - ly0:yb - ly0, xa - lx0:xb - lx0][..., None]
                frame[ya:yb, xa:xb] = frame[ya:yb, xa:xb] * (1 - a) + spr[ya - ly0:yb - ly0, xa - lx0:xb - lx0, :3] * a
    im = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8))
    if edge:
        d = ImageDraw.Draw(im)
        pts = [(e[0] / 100 * W, e[1] / 100 * H) for e in edge]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            n = max(1, int(((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5 / (12 * k)))
            for i in range(0, n, 2):   # пунктир
                t0, t1 = i / n, min(1, (i + 1) / n)
                d.line([(ax + (bx - ax) * t0, ay + (by - ay) * t0), (ax + (bx - ax) * t1, ay + (by - ay) * t1)],
                       fill=(30, 110, 200), width=max(2, int(2 * k)))
    im.save(out_path, quality=90)
    return out_path


@app.route("/fx_zoom", methods=["POST"])
def fx_zoom():
    data = request.json or {}
    work_dir = tempfile.mkdtemp(prefix="fxzoom_")
    try:
        img = _fx_image(data["imageUrl"], work_dir)
        return jsonify({"ok": True, "points": zoom_points(img, data.get("fx_Effects", ""))})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "points": []}), 200
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


@app.route("/fx_grid", methods=["POST"])
def fx_grid():
    import base64
    data = request.json or {}
    work_dir = tempfile.mkdtemp(prefix="fxgrid_")
    try:
        img = _fx_image(data["imageUrl"], work_dir)
        out = draw_percent_grid(img, os.path.join(work_dir, "grid.jpg"))
        b64 = base64.b64encode(open(out, "rb").read()).decode()
        return jsonify({"ok": True, "dataUrl": "data:image/jpeg;base64," + b64})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


@app.route("/fx_preview", methods=["POST"])
def fx_preview():
    data = request.json or {}
    work_dir = tempfile.mkdtemp(prefix="fxprev_")

    @after_this_request
    def cleanup(response):
        shutil.rmtree(work_dir, ignore_errors=True)
        return response
    img = _fx_image(data["imageUrl"], work_dir)
    out = draw_fx_preview(img, data.get("fx_Effects") or "", data, os.path.join(work_dir, "preview.jpg"))
    return send_file(out, mimetype="image/jpeg")



# РАЗМЕТКА АВТОРА (04.10): автор рисует красным маркером поверх превью или картинки —
# откуда идёт дымок и докуда, откуда срывается лист и куда падает. /fx_marks сравнивает её
# картинку с исходной и возвращает каждый штрих: верхний и нижний конец, путь, толщину —
# в процентах кадра. Штрихи — слева направо.
def find_red_marks(orig_path, marked_path):
    import numpy as np
    from PIL import Image
    orig = Image.open(orig_path).convert("RGB")
    W, H = orig.size
    marked = Image.open(marked_path).convert("RGB")
    marked_size = marked.size
    marked = marked.resize((W, H), Image.LANCZOS)
    S = 2                                           # ищем на уменьшенной картинке — быстро и без шума
    w, h = W // S, H // S
    # красное ищем на полном размере (тонкий штрих при уменьшении бледнеет и рвётся),
    # потом клетка S×S красная, если в ней есть хоть один красный пиксель
    a = np.asarray(marked, np.float32)
    b = np.asarray(orig, np.float32)
    r, g, bl = a[..., 0], a[..., 1], a[..., 2]
    # красный маркер: ярко-красный (оранжевые листики самого превью сюда не попадают)
    red_full = (r > 140) & (g < 100) & (bl < 100) & (r - g > 90) & (np.abs(a - b).max(axis=2) > 50)
    red = red_full[:h * S, :w * S].reshape(h, S, w, S).any(axis=(1, 3))
    # без склейки соседей: близкие штрихи (дымок и лист рядом) остаются раздельными
    m = red
    seen = np.zeros_like(m)
    marks = []
    for y0 in range(h):
        for x0 in range(w):
            if not m[y0, x0] or seen[y0, x0]:
                continue
            comp, stack = [], [(y0, x0)]
            seen[y0, x0] = True
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    if 0 <= ny < h and 0 <= nx < w and m[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            if len(comp) < 12:
                continue
            pts = np.array(comp)
            # концы: самая дальняя от центра точка и самая дальняя от неё
            c = pts.mean(axis=0)
            A = pts[np.argmax(((pts - c) ** 2).sum(1))]
            B = pts[np.argmax(((pts - A) ** 2).sum(1))]
            # путь от A к B внутри штриха (поиск в ширину)
            idx = {tuple(p): i for i, p in enumerate(pts)}
            prev = {tuple(A): None}
            q = [tuple(A)]
            for cur in q:
                if cur == tuple(B):
                    break
                for d in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                    nb = (cur[0] + d[0], cur[1] + d[1])
                    if nb in idx and nb not in prev:
                        prev[nb] = cur
                        q.append(nb)
            path, cur = [], tuple(B)
            while cur is not None:
                path.append(cur); cur = prev.get(cur)
            path = path[::-1]
            length = max(1.0, sum(((path[i][0] - path[i + 1][0]) ** 2 + (path[i][1] - path[i + 1][1]) ** 2) ** 0.5
                                  for i in range(len(path) - 1)))
            step = max(1, len(path) // 8)
            poly = [path[i] for i in range(0, len(path), step)] + [path[-1]]
            P = lambda yx: [round(yx[1] * S / W * 100, 1), round(yx[0] * S / H * 100, 1)]
            poly_pct = [P(p) for p in poly]
            top, bottom = (poly_pct[0], poly_pct[-1]) if poly_pct[0][1] <= poly_pct[-1][1] else (poly_pct[-1], poly_pct[0])
            # толщина — по красным пикселям полного размера внутри клеток штриха
            cells = np.zeros((h, w), bool); cells[pts[:, 0], pts[:, 1]] = True
            full = np.repeat(np.repeat(cells, S, 0), S, 1) & red_full[:h * S, :w * S]
            width_px = int(full.sum()) / (length * S)
            box = [round(float(pts[:, 1].min()) * S / W * 100, 1), round(float(pts[:, 0].min()) * S / H * 100, 1),
                   round(float(pts[:, 1].max() + 1) * S / W * 100, 1), round(float(pts[:, 0].max() + 1) * S / H * 100, 1)]
            marks.append({"top": top, "bottom": bottom, "box": box,
                          "path": poly_pct if poly_pct[0][1] <= poly_pct[-1][1] else poly_pct[::-1],
                          "width_pct": round(width_px / H * 100, 2), "left": float(pts[:, 1].min())})
    marks.sort(key=lambda m_: m_["left"])
    for m_ in marks:
        m_.pop("left")
    if not marks:   # объясняем, почему пусто: размеры и сколько красного вообще нашлось
        rr = (r > 140) & (g < 100) & (bl < 100) & (r - g > 90)
        raise ValueError(f"штрихов нет: картинка {W}x{H}, разметка {marked_size[0]}x{marked_size[1]}, "
                         f"красных пикселей {int(rr.sum())}, из них отличных от исходной {int(red_full.sum())}")
    return marks


# ── Маска для правки картинки по обводке автора ──
# Автор обводит красным маркером, что поправить. Внутри обводки (и сам штрих) — можно
# рисовать заново, снаружи — картинка остаётся как была. Маска — PNG размера исходной
# картинки: прозрачное = можно менять, непрозрачное = сохранить.
def make_edit_mask(orig_path, marked_path, out_path, margin_pct=2.0):
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter
    orig = Image.open(orig_path).convert("RGB")
    W, H = orig.size
    marked = Image.open(marked_path).convert("RGB").resize((W, H), Image.LANCZOS)
    a = np.asarray(marked, np.float32)
    b = np.asarray(orig, np.float32)
    r, g, bl = a[..., 0], a[..., 1], a[..., 2]
    red = (r > 140) & (g < 100) & (bl < 100) & (r - g > 90) & (np.abs(a - b).max(axis=2) > 50)
    if int(red.sum()) < 30:
        raise ValueError("красной обводки не нашлось")
    # считаем на уменьшенной копии: заливаем то, что внутри замкнутой обводки
    S = max(1, W // 512)
    w, h = W // S, H // S
    small = Image.fromarray((red * 255).astype(np.uint8)).resize((w, h), Image.BOX).point(lambda v: 255 if v > 0 else 0)
    small = small.filter(ImageFilter.MaxFilter(5))          # закрываем мелкие разрывы штриха
    canvas = Image.new("L", (w + 2, h + 2), 0)
    canvas.paste(small, (1, 1))
    ImageDraw.floodfill(canvas, (0, 0), 128)                 # всё, до чего можно дойти снаружи
    c = np.asarray(canvas)[1:-1, 1:-1]
    area = (c != 128)                                        # штрих + то, что внутри него
    m = Image.fromarray((area * 255).astype(np.uint8))
    pad = max(1, int(round(margin_pct / 100.0 * h)))
    m = m.filter(ImageFilter.MaxFilter(2 * pad + 1)).resize((W, H), Image.BILINEAR)
    edit = np.asarray(m) > 127
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., 3] = np.where(edit, 0, 255)
    Image.fromarray(rgba, "RGBA").save(out_path)
    return float(edit.mean())


@app.route("/edit_mask", methods=["POST"])
def edit_mask():
    import base64
    data = request.json or {}
    work_dir = tempfile.mkdtemp(prefix="editmask_")
    try:
        orig = _fx_image(data["imageUrl"], work_dir)
        marked = os.path.join(work_dir, "marked.jpg")
        open(marked, "wb").write(base64.b64decode(str(data.get("markedDataUrl") or "").split(",", 1)[-1]))
        out = os.path.join(work_dir, "mask.png")
        share = make_edit_mask(orig, marked, out, float(data.get("marginPct") or 2.0))
        if share > 0.6:
            raise ValueError("обведено больше половины картинки — это уже не правка, а новый рисунок")
        resp = send_file(out, mimetype="image/png")
        return resp
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 422
    finally:
        @after_this_request
        def _cleanup(response):
            shutil.rmtree(work_dir, ignore_errors=True)
            return response


@app.route("/fx_marks", methods=["POST"])
def fx_marks():
    import base64
    data = request.json or {}
    work_dir = tempfile.mkdtemp(prefix="fxmarks_")
    try:
        orig = _fx_image(data["imageUrl"], work_dir)
        raw = str(data.get("markedDataUrl") or "")
        marked = os.path.join(work_dir, "marked.jpg")
        open(marked, "wb").write(base64.b64decode(raw.split(",", 1)[-1]))
        marks = find_red_marks(orig, marked)
        if len(marks) > 12:
            # обводки «где оживить» и подписи словами: штрихов много и они мелкие — пересказывать их
            # нет смысла; этап читает разметку по самому фото, точные места доводят лупа и примагничивание
            return jsonify({"ok": True, "marks": marks[:0], "zones": True,
                            "text": f"На фото обводки и подписи автора (мелких штрихов: {len(marks)}). Читай разметку по самому фото: "
                                    "что обведено и что подписано. Места называй по центру обводки — точные точки "
                                    "(пламя, глаз, стекло) дальше доведут лупа и сборщик."})
        lines = []
        for i, m_ in enumerate(marks, 1):
            lines.append(f"{i}) верхний конец {m_['top'][0]}, {m_['top'][1]}; нижний конец {m_['bottom'][0]}, "
                         f"{m_['bottom'][1]}; путь сверху вниз: " + " → ".join(f"{p[0]}, {p[1]}" for p in m_["path"]) +
                         f"; толщина штриха {m_['width_pct']} % высоты кадра"
                         f"; рамка штриха: левый верх {m_['box'][0]}, {m_['box'][1]} — правый низ {m_['box'][2]}, {m_['box'][3]}")
        return jsonify({"ok": True, "marks": marks, "text": "\n".join(lines)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "marks": [], "text": ""}), 200
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


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
