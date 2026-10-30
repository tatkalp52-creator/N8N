"""Календарь (11) читает из листа выпусков только нужные колонки (24.10).

Раньше страница календаря на каждое открытие читала лист выпусков целиком — с промтами всех вариантов
картинок, текстами и состоянием бота: мегабайты, и всё больше с каждым выпуском. Теперь:
  заголовок листа (строки 1–2) → номера нужных колонок по ИМЕНАМ из таблицы → читаем только их
  → проверка (имя прочитанной колонки совпало, у строк есть номера) → «Собираем данные».
Если проверка не прошла (переставили колонки, лист пустой, Google ответил ошибкой) — старый путь:
весь лист, как раньше. Календарь не может перестать открываться из-за этой правки.
Повторный запуск ничего не дублирует.

    python3 tools/patch11_lite.py
"""
import json, os, uuid

ROOT = os.path.join(os.path.dirname(__file__), "..")
PATH = os.path.join(ROOT, "workflows", "11_Календарь.json")
DOC = {"__rl": True, "value": "1yEolX-8NV7NInu3OwCoxo2KSSNMny9dk-AVrpKdyNEs", "mode": "id"}
GS = {"googleApi": {"id": "1uQkgKbOPhjKOB2l", "name": "Google Sheets account 2"}}

# какие колонки нужны странице — те же имена, что читает «Собираем данные»
KOLONKI = """// Номера нужных колонок — по их именам в первой строке листа выпусков (имена задаёт таблица)
const NEED = ['sys_ProjectID', 'sys_Status', 'sys_AudioZipUrl', 'ai_Title'];
const cat = $('Читаем каталог (страница)').all();
const letter = i => { let s = ''; i++; while (i > 0) { const m = (i - 1) % 26; s = String.fromCharCode(65 + m) + s; i = Math.floor((i - 1) / 26); } return s; };
const pIdx = it => { const p = it.pairedItem; return Array.isArray(p) ? (p[0] || {}).item || 0 : (p && p.item) || 0; };
const out = [];
for (const it of $input.all()) {
  const j = it.json || {};
  const sheet = String(((cat[pIdx(it)] || {}).json || {}).SheetName || '').trim();
  const keys = Object.keys(j).filter(k => k !== 'row_number');
  if (!sheet || j.error || !keys.includes('sys_ProjectID')) continue;
  for (const name of NEED) {
    const i = keys.indexOf(name);
    if (i >= 0) out.push({ json: { sheet, name, range: letter(i) + '1:' + letter(i) + '5000' } });
  }
}
return out.length ? out : [{ json: { sheet: '', name: '', range: '', skip: true } }];
"""

PROVERKA = """// Склеиваем прочитанные колонки по номеру строки. Любое сомнение — ok: false, и календарь читает лист целиком.
const reqs = $('Выпуски: какие колонки').all().map(i => i.json);
const pIdx = it => { const p = it.pairedItem; return Array.isArray(p) ? (p[0] || {}).item || 0 : (p && p.item) || 0; };
let ok = reqs.length > 0 && !reqs[0].skip;
const bySheet = {};
for (const it of $input.all()) {
  const j = it.json || {};
  const keys = Object.keys(j).filter(k => k !== 'row_number');
  if (!keys.length) continue;                    // пустая колонка — нечего склеивать
  const rq = reqs[pIdx(it)];
  if (j.error || !rq || keys[0] !== rq.name || j.row_number == null) { ok = false; break; }
  const s = bySheet[rq.sheet] = bySheet[rq.sheet] || {};
  const r = s[j.row_number] = s[j.row_number] || {};
  r[rq.name] = j[rq.name];
}
const rows = ok ? Object.values(bySheet).flatMap(s => Object.values(s)) : [];
if (!rows.some(r => String(r.sys_ProjectID || '').trim())) ok = false;
return [{ json: { ok, rows: ok ? rows : [] } }];
"""

KATALOG = """// Запасной путь: каналы ещё раз — по ним старый узел читает листы выпусков целиком
return $('Читаем каталог (страница)').all();
"""

OLD_RAW = "let raw = [];\ntry { raw = $('Читаем выпуски (страница)').all().map(i => i.json); } catch (e) {}"
NEW_RAW = ("let raw = [];\n"
           "// (24.10) обычно — только нужные колонки; если быстрый путь не прошёл проверку — весь лист, как раньше\n"
           "try { const v = $('Выпуски: проверка').first().json; if (v.ok) raw = v.rows; } catch (e) {}\n"
           "if (!raw.length) { try { raw = $('Читаем выпуски (страница)').all().map(i => i.json); } catch (e) {} }")


def sheets_read(name, sheet_expr, rng, pos):
    return {"parameters": {"authentication": "serviceAccount", "documentId": DOC,
                           "sheetName": {"__rl": True, "value": sheet_expr, "mode": "name"},
                           "filtersUI": {"values": []},
                           "options": {"dataLocationOnSheet": {"values": {"rangeDefinition": "specifyRangeA1", "range": rng}}}},
            "id": str(uuid.uuid4()), "name": name, "type": "n8n-nodes-base.googleSheets", "typeVersion": 4,
            "position": pos, "credentials": GS, "alwaysOutputData": True, "onError": "continueRegularOutput"}


def code(name, js, pos):
    return {"parameters": {"jsCode": js}, "id": str(uuid.uuid4()), "name": name,
            "type": "n8n-nodes-base.code", "typeVersion": 2, "position": pos, "alwaysOutputData": True}


def main():
    w = json.load(open(PATH))
    names = {n["name"] for n in w["nodes"]}
    if "Выпуски: проверка" in names:
        print("уже стоит")
        return
    full = next(n for n in w["nodes"] if n["name"] == "Читаем выпуски (страница)")
    x, y = full["position"]
    # старый узел читает лист по SheetName входящего элемента — теперь элементы ему даёт «Каталог заново»
    full["position"] = [x + 880, y + 220]
    w["nodes"] += [
        sheets_read("Выпуски: заголовок", "={{ $json.SheetName }}", "A1:ZZ2", [x, y]),
        code("Выпуски: какие колонки", KOLONKI, [x + 220, y]),
        sheets_read("Выпуски: нужные колонки", "={{ $json.sheet }}", "={{ $json.range }}", [x + 440, y]),
        code("Выпуски: проверка", PROVERKA, [x + 660, y]),
        {"parameters": {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
                                       "conditions": [{"id": str(uuid.uuid4()), "leftValue": "={{ $json.ok }}", "rightValue": True,
                                                       "operator": {"type": "boolean", "operation": "true", "singleValue": True}}],
                                       "combinator": "and"}, "options": {}},
         "id": str(uuid.uuid4()), "name": "Колонки прочитаны?", "type": "n8n-nodes-base.if", "typeVersion": 2,
         "position": [x + 880, y]},
        code("Каталог заново", KATALOG, [x + 880, y + 440]),
    ]
    sob = next(n for n in w["nodes"] if n["name"] == "Собираем данные")
    assert OLD_RAW in sob["parameters"]["jsCode"]
    sob["parameters"]["jsCode"] = sob["parameters"]["jsCode"].replace(OLD_RAW, NEW_RAW)
    c = w["connections"]
    m = lambda *targets: {"main": [[{"node": t, "type": "main", "index": 0}] if t else [] for t in targets]}
    c["Читаем каталог (страница)"] = m("Выпуски: заголовок")
    c["Выпуски: заголовок"] = m("Выпуски: какие колонки")
    c["Выпуски: какие колонки"] = m("Выпуски: нужные колонки")
    c["Выпуски: нужные колонки"] = m("Выпуски: проверка")
    c["Выпуски: проверка"] = m("Колонки прочитаны?")
    c["Колонки прочитаны?"] = m("Собираем данные", "Каталог заново")
    c["Каталог заново"] = m("Читаем выпуски (страница)")
    c["Читаем выпуски (страница)"] = m("Собираем данные")
    json.dump(w, open(PATH, "w"), ensure_ascii=False, indent=2)
    print("готово")


if __name__ == "__main__":
    main()
