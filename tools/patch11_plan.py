"""Ставит в workflows/11_Календарь.json новую страницу календаря — контент-план (11.10).

Страница (table_drafts/calendar/plan_page.html): слева месяц с выпусками по каналам, справа поводы
по дням; «В план» → день; шаги выпуска. Читает и пишет лист «Календарь» сразу (как прежняя страница:
/data и /save). Новые колонки листа: title_ru, release (дата выпуска), step (0–5). Каналы и подписи —
лист Catalog. Остальной календарь не трогается. Повторный запуск не дублирует.

    python3 tools/patch11_plan.py
"""
import json, os, uuid

ROOT = os.path.join(os.path.dirname(__file__), "..")
PATH = os.path.join(ROOT, "workflows", "11_Календарь.json")
PAGE = os.path.join(ROOT, "table_drafts", "calendar", "plan_page.html")
DOC = {"__rl": True, "value": "1yEolX-8NV7NInu3OwCoxo2KSSNMny9dk-AVrpKdyNEs", "mode": "id"}
GS = {"googleApi": {"id": "1uQkgKbOPhjKOB2l", "name": "Google Sheets account 2"}}
COLS = ['id', 'year', 'month', 'day', 'title', 'channel', 'status', 'project', 'note', 'sources', 'createdAt', 'updatedAt', 'title_ru', 'release', 'step', 'posted', 'tag']

SOBIRAEM = """// все строки листа, каналы (Catalog) и выпуски каналов (только шаг и треки) одним JSON для страницы
// только соседние месяцы (прошлый … +3 вперёд) — страница не тяжелеет с годами
const now = new Date(), base = now.getFullYear() * 12 + now.getMonth();
const ym = (y, m) => { y = Number(y) || 0; m = Number(m) || 0; if (!m) return -1; if (!y) { y = now.getFullYear(); if (y * 12 + m - 1 < base - 2) y++; } return y * 12 + m - 1; };
const near = k => k >= base - 1 && k <= base + 3;
const rows = $('Читаем календарь (страница)').all().map(i => i.json).filter(r => r && String(r.id || '').trim()).filter(r => {
  const rel = String(r.release || '').match(/^(\\d{4})-(\\d{2})/);
  return near(ym(r.year, r.month)) || (rel && near(ym(rel[1], rel[2])));
});
const channels = $('Читаем каталог (страница)').all().map(i => i.json).filter(c => c && String(c.Channel || '').trim());
let raw = [];
try { raw = $('Читаем выпуски (страница)').all().map(i => i.json); } catch (e) {}
const projects = raw.filter(p => p && /^\\d{8}_\\d{6}_[a-z0-9]+$/i.test(String(p.sys_ProjectID || '').trim())).map(p => {
  const id = String(p.sys_ProjectID).trim();
  return { id, ch: id.split('_').slice(2).join('_').toLowerCase(), status: String(p.sys_Status || '').trim(),
    tracks: !!String(p.sys_AudioZipUrl || '').trim(), title: String(p.ai_Title || '').slice(0, 160) };
});
return [{ json: { body: JSON.stringify({ rows, channels, projects }) } }];"""

STROKA = """// строка, которую прислала страница: берём только известные колонки
const COLS = %s;
const STATUSES = ['Идея','Выбран','В работе','Вышел','Отклонён'];
const r = ($('Сохранение со страницы').first().json.body || {}).row || {};
const id = String(r.id || '').trim();
if (!/^[A-Za-z0-9_-]{2,40}$/.test(id)) throw new Error('bad id');
const m = Number(r.month), d = Number(r.day);
if (!(m >= 1 && m <= 12 && d >= 1 && d <= 31)) throw new Error('bad date');
const now = new Date().toISOString();
const out = {};
for (const c of COLS) out[c] = r[c] === null || r[c] === undefined ? '' : String(r[c]).slice(0, 20000);
out.id = id; out.month = String(m); out.day = String(d);
if (!STATUSES.includes(out.status)) out.status = 'Идея';
if (out.release && !/^\\d{4}-\\d{2}-\\d{2}$/.test(out.release)) out.release = '';
if (out.step && !/^[0-5]$/.test(out.step)) out.step = '';
if (out.posted !== 'да') out.posted = '';
if (out.project && !/^\\d{8}_\\d{6}_[a-z0-9]+$/i.test(out.project)) out.project = '';
out.channel = out.channel.toLowerCase();   // пусто — повод общий, для любого канала
out.updatedAt = now;
if (!out.createdAt) out.createdAt = now;
return [{ json: out }];""" % json.dumps(COLS)


def main():
    wf = json.load(open(PATH, encoding="utf-8"))
    nodes = {n["name"]: n for n in wf["nodes"]}
    conns = wf["connections"]
    nodes["Отдаём страницу"]["parameters"]["responseBody"] = open(PAGE, encoding="utf-8").read()
    nodes["Собираем данные"]["parameters"]["jsCode"] = SOBIRAEM
    nodes["Строка со страницы"]["parameters"]["jsCode"] = STROKA
    nodes["Записываем со страницы"]["parameters"]["columns"]["value"] = {c: "={{ $json." + c + " }}" for c in COLS}
    if "Читаем каталог (страница)" not in nodes:
        x, y = nodes["Читаем календарь (страница)"]["position"]
        n = {"parameters": {"authentication": "serviceAccount", "documentId": DOC,
             "sheetName": {"__rl": True, "value": "Catalog", "mode": "name"}, "filtersUI": {"values": []}, "options": {}},
             "id": str(uuid.uuid4()), "name": "Читаем каталог (страница)", "type": "n8n-nodes-base.googleSheets", "typeVersion": 4,
             "position": [x + 110, y + 160], "credentials": GS, "alwaysOutputData": True, "executeOnce": True}
        wf["nodes"].append(n)
    if "Читаем выпуски (страница)" not in nodes:
        x, y = nodes["Читаем каталог (страница)"]["position"]
        n = {"parameters": {"authentication": "serviceAccount", "documentId": DOC,
             "sheetName": {"__rl": True, "value": "={{ $json.SheetName }}", "mode": "name"}, "filtersUI": {"values": []}, "options": {}},
             "id": str(uuid.uuid4()), "name": "Читаем выпуски (страница)", "type": "n8n-nodes-base.googleSheets", "typeVersion": 4,
             "position": [x + 110, y + 160], "credentials": GS, "alwaysOutputData": True, "onError": "continueRegularOutput"}
        wf["nodes"].append(n)
    L = lambda b: {"node": b, "type": "main", "index": 0}
    conns["Читаем календарь (страница)"] = {"main": [[L("Читаем каталог (страница)")]]}
    conns["Читаем каталог (страница)"] = {"main": [[L("Читаем выпуски (страница)")]]}
    conns["Читаем выпуски (страница)"] = {"main": [[L("Собираем данные")]]}
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(wf, f, ensure_ascii=False, indent=2)
    print("ok: контент-план в 11")


if __name__ == "__main__":
    main()
