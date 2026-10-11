"""Добавляет в workflows/11_Календарь.json АВТОСБОР поводов (11.10).

Сам — 1-го числа в 9:00 на следующий месяц; по команде в боте календаря: «собери» (следующий
месяц) или «собери ноябрь». ИИ с поиском в интернете находит поводы месяца для всех каналов
сразу; что искать для каждого канала — лист «Автосбор» (Канал | Что искать | Модель), не код.
Формат один: дата, название как в оригинале + русское, каналы, строка идеи. Повторы с листом
«Календарь» не добавляются. Новые ложатся «Идеей», итог приходит сообщением.

Остальной календарь (узел «Логика» и страница) не трогается. Повторный запуск не дублирует.

    python3 tools/patch11_avtosbor.py
"""
import json, os, uuid

PATH = os.path.join(os.path.dirname(__file__), "..", "workflows", "11_Календарь.json")
DOC = {"__rl": True, "value": "1yEolX-8NV7NInu3OwCoxo2KSSNMny9dk-AVrpKdyNEs", "mode": "id"}
GS = {"googleApi": {"id": "1uQkgKbOPhjKOB2l", "name": "Google Sheets account 2"}}
AI = {"openAiApi": {"id": "HvMLVgMnS8OU4ebj", "name": "OpenAi account"}}
COLS = ['id', 'year', 'month', 'day', 'title', 'channel', 'status', 'project', 'note', 'sources', 'createdAt', 'updatedAt', 'title_ru']

ZADANIE = r"""// Автосбор: какой месяц и что искать. Месяц — из команды («собери ноябрь»), иначе следующий.
// Что искать для каждого канала — лист «Автосбор» (Канал | Что искать | Модель): здесь только механика.
const MON = [['янв','jan'],['фев','feb'],['мар','mar'],['апр','apr'],['мая','май','may'],['июн','jun'],['июл','jul'],['авг','aug'],['сен','sep'],['окт','oct'],['ноя','nov'],['дек','dec']];
const MON_EN = ['January','February','March','April','May','June','July','August','September','October','November','December'];
const MON_RU = ['январь','февраль','март','апрель','май','июнь','июль','август','сентябрь','октябрь','ноябрь','декабрь'];
let msg = null;
try { msg = $('Telegram Trigger').first().json.message || null; } catch (e) {}
const text = String((msg && msg.text) || '').toLowerCase();
const now = new Date();
let y = now.getFullYear(), m = now.getMonth() + 2;            // следующий месяц, 1..13
const w = (text.match(/собер\S*\s+(\S+)/) || [])[1] || '';
const mi = MON.findIndex(ks => ks.some(k => w.startsWith(k)));
if (mi >= 0) { m = mi + 1; if (m < now.getMonth() + 1) y++; }
if (m > 12) { m -= 12; y++; }
const hints = $('Читаем, что искать').all().map(i => i.json)
  .map(r => ({ key: String(r['Канал'] || '').trim(), what: String(r['Что искать'] || '').trim(), model: String(r['Модель'] || '').trim() }))
  .filter(r => r.key && r.what);
const model = (hints.find(h => h.model) || {}).model || 'gpt-5';
const chatId = msg ? msg.chat.id : 285577543;
if (!hints.length) return [{ json: { need: false, chatId, text: 'Лист «Автосбор» пуст: не знаю, что искать.' } }];
const instructions = 'You collect occasions for a YouTube content plan. Find holidays, observances, "national/world ... days", '
  + 'seasonal and astronomical events that fall in ' + MON_EN[m - 1] + ' ' + y + '. Use web search to check the dates for this year. '
  + 'What is useful for each channel (key: description):\n' + hints.map(h => '- ' + h.key + ': ' + h.what).join('\n') + '\n\n'
  + 'Answer with JSON only, no other text: {"items": [{"date": "YYYY-MM-DD", "title": "the original name, as it is known (usually English)", '
  + '"title_ru": "Russian translation of the name", "channels": ["channel keys it fits"], "idea_ru": "one short line in Russian: how it could fit", '
  + '"source": "site name"}]}. Only occasions that fit at least one channel. Never invent a date; skip an occasion you cannot date for '
  + y + '. Up to 60 items, sorted by date.';
const requestBody = { model, instructions, tools: [{ type: 'web_search' }],
  input: [{ role: 'user', content: 'Collect the occasions for ' + MON_EN[m - 1] + ' ' + y + ' as JSON.' }] };
if (/^(gpt-5|o\d)/.test(model)) requestBody.reasoning = { effort: 'low' };
return [{ json: { need: true, chatId, y, m, monthRu: MON_RU[m - 1], keys: hints.map(h => h.key), requestBody,
  text: '🔎 Ищу поводы на ' + MON_RU[m - 1] + ' ' + y + '. Это займёт несколько минут.' } }];"""

RAZBOR = r"""// Ответ ИИ → строки листа «Календарь». Повторы (тот же день и то же название) с листом и внутри
// ответа не добавляются. Новые — статус «Идея», источник «автосбор dd.mm».
const z = $('Автосбор: задание').first().json;
const resp = $json || {};
const MON_GEN = ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const out = (resp.output || []).filter(i => i.type === 'message')
  .flatMap(i => (i.content || []).filter(c => c.type === 'output_text').map(c => c.text)).join('\n');
let items = [];
try {
  const a = out.indexOf('{'), b = out.lastIndexOf('}');
  items = (JSON.parse(out.slice(a, b + 1)).items) || [];
} catch (e) { items = null; }
if (resp.error || !Array.isArray(items)) {
  const why = resp.error ? (resp.error.message || JSON.stringify(resp.error)).slice(0, 200) : 'ответ не разобрался';
  return [{ json: { rows: [], text: '⚠️ Автосбор на ' + z.monthRu + ' не получился: ' + esc(why) } }];
}
const norm = s => String(s || '').toLowerCase().replace(/[^a-zа-яё0-9]+/gi, ' ').trim();
const seen = new Set();
for (const r of $('Читаем календарь (автосбор)').all().map(i => i.json)) {
  if (!r || !r.id) continue;
  seen.add(Number(r.month) + '-' + Number(r.day) + '|' + norm(r.title));
}
const now = new Date().toISOString();
const stamp = new Date().toISOString().slice(8, 10) + '.' + new Date().toISOString().slice(5, 7);
const rows = []; let found = 0;
for (const it of items) {
  const md = String(it.date || '').match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!md || Number(md[1]) !== z.y || Number(md[2]) !== z.m) continue;
  const title = String(it.title || '').trim();
  if (!title) continue;
  found++;
  const k = z.m + '-' + Number(md[3]) + '|' + norm(title);
  if (seen.has(k)) continue;
  seen.add(k);
  const ch = (Array.isArray(it.channels) ? it.channels : [it.channels]).map(c => String(c || '').trim()).filter(c => z.keys.includes(c));
  rows.push({ id: 'a' + Date.now().toString(36) + rows.length.toString(36) + Math.random().toString(36).slice(2, 5),
    year: String(z.y), month: String(z.m), day: String(Number(md[3])), title, channel: (ch.length ? ch : [z.keys[0]]).join(', '),
    status: 'Идея', project: '', note: String(it.idea_ru || '').trim(), sources: 'автосбор ' + stamp + (it.source ? '; ' + String(it.source).trim() : ''),
    createdAt: now, updatedAt: now, title_ru: String(it.title_ru || '').trim() });
}
rows.sort((a, b) => Number(a.day) - Number(b.day));
let text = '🗓 Автосбор на ' + z.monthRu + ' ' + z.y + ': найдено ' + found + ', новых ' + rows.length + '.';
for (const r of rows) {
  const line = '\n' + r.day + ' ' + MON_GEN[z.m - 1].slice(0, 3) + ' — <b>' + esc(r.title) + '</b>' + (r.title_ru ? ' — ' + esc(r.title_ru) : '') + ' · ' + esc(r.channel);
  if ((text + line).length > 3900) { text += '\n…и ещё, всё — в листе «Календарь».'; break; }
  text += line;
}
return [{ json: { rows, text } }];"""


def main():
    wf = json.load(open(PATH, encoding="utf-8"))
    nodes = {n["name"]: n for n in wf["nodes"]}
    conns = wf["connections"]
    tg = nodes["Отправляем текст"]["credentials"]

    def put(node):
        node.setdefault("id", str(uuid.uuid4()))
        if node["name"] in nodes:
            old = nodes[node["name"]]
            node["id"] = old["id"]
            wf["nodes"][wf["nodes"].index(old)] = node
        else:
            wf["nodes"].append(node)
        nodes[node["name"]] = node

    def iff(name, expr, pos):
        return {"parameters": {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
                "conditions": [{"leftValue": "={{ " + expr + " }}", "rightValue": True,
                                "operator": {"type": "boolean", "operation": "true", "singleValue": True}}], "combinator": "and"}, "options": {}},
                "name": name, "type": "n8n-nodes-base.if", "typeVersion": 2, "position": pos}

    def send(name, pos):
        return {"parameters": {"chatId": "={{ $json.chatId }}", "text": "={{ $json.text }}",
                "additionalFields": {"appendAttribution": False, "parse_mode": "HTML", "disable_web_page_preview": True}},
                "name": name, "type": "n8n-nodes-base.telegram", "typeVersion": 1.2, "position": pos,
                "credentials": tg, "onError": "continueRegularOutput"}

    X, Y = 440, 1900
    put(iff("Это автосбор?", "/^\\s*собер/i.test(String($json.message?.text || ''))", [330, -160]))
    put({"parameters": {"rule": {"interval": [{"field": "cronExpression", "expression": "0 9 1 * *"}]}},
         "name": "Первого числа", "type": "n8n-nodes-base.scheduleTrigger", "typeVersion": 1.2, "position": [X - 220, Y]})
    put({"parameters": {"authentication": "serviceAccount", "documentId": DOC,
         "sheetName": {"__rl": True, "value": "Автосбор", "mode": "name"}, "filtersUI": {"values": []}, "options": {}},
         "name": "Читаем, что искать", "type": "n8n-nodes-base.googleSheets", "typeVersion": 4, "position": [X, Y],
         "credentials": GS, "alwaysOutputData": True})
    put({"parameters": {"jsCode": ZADANIE}, "name": "Автосбор: задание", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [X + 220, Y]})
    put(send("Автосбор: начали", [X + 440, Y - 160]))
    put(iff("Есть что искать?", "$('Автосбор: задание').first().json.need", [X + 440, Y]))
    put({"parameters": {"method": "POST", "url": "https://api.openai.com/v1/responses", "authentication": "predefinedCredentialType",
         "nodeCredentialType": "openAiApi", "sendBody": True, "specifyBody": "json",
         "jsonBody": "={{ JSON.stringify($('Автосбор: задание').first().json.requestBody) }}", "options": {"timeout": 600000}},
         "name": "OpenAI: ищем поводы", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": [X + 660, Y],
         "credentials": AI, "onError": "continueRegularOutput"})
    put({"parameters": {"authentication": "serviceAccount", "documentId": DOC,
         "sheetName": {"__rl": True, "value": "Календарь", "mode": "name"}, "filtersUI": {"values": []}, "options": {}},
         "name": "Читаем календарь (автосбор)", "type": "n8n-nodes-base.googleSheets", "typeVersion": 4, "position": [X + 880, Y],
         "credentials": GS, "alwaysOutputData": True, "executeOnce": True})
    put({"parameters": {"jsCode": RAZBOR}, "name": "Автосбор: разбор", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [X + 1100, Y],
         "notes": "вход — ответ OpenAI (через чтение календаря он не проходит: читаем $('OpenAI: ищем поводы'))"})
    # разбор читает ответ ИИ по имени узла, а не $json (вход — строки календаря)
    nodes["Автосбор: разбор"]["parameters"]["jsCode"] = RAZBOR.replace("const resp = $json || {};", "const resp = $('OpenAI: ищем поводы').first().json || {};")
    put({"parameters": {"jsCode": "// по строке на элемент — для записи в лист\nreturn $('Автосбор: разбор').first().json.rows.map(r => ({ json: r }));"},
         "name": "Автосбор: строки", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [X + 1320, Y - 160]})
    put({"parameters": {"authentication": "serviceAccount", "operation": "append", "documentId": DOC,
         "sheetName": {"__rl": True, "value": "Календарь", "mode": "name"},
         "columns": {"mappingMode": "defineBelow", "value": {c: "={{ $json." + c + " }}" for c in COLS}}, "options": {}},
         "name": "Автосбор: записываем", "type": "n8n-nodes-base.googleSheets", "typeVersion": 4, "position": [X + 1540, Y - 160], "credentials": GS})
    put({"parameters": {"jsCode": "const z = $('Автосбор: задание').first().json;\nreturn [{ json: { chatId: z.chatId, text: $('Автосбор: разбор').first().json.text } }];"},
         "name": "Автосбор: итог", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [X + 1320, Y + 100]})
    put(send("Автосбор: сообщаем", [X + 1540, Y + 100]))
    put(send("Автосбор: нечего искать", [X + 660, Y + 200]))

    L = lambda b: {"node": b, "type": "main", "index": 0}
    conns["Это владелец?"] = {"main": [[L("Это автосбор?")]]}
    conns["Это автосбор?"] = {"main": [[L("Читаем, что искать")], [L("Читаем календарь")]]}
    conns["Первого числа"] = {"main": [[L("Читаем, что искать")]]}
    conns["Читаем, что искать"] = {"main": [[L("Автосбор: задание")]]}
    conns["Автосбор: задание"] = {"main": [[L("Есть что искать?")]]}
    conns["Есть что искать?"] = {"main": [[L("Автосбор: начали"), L("OpenAI: ищем поводы")], [L("Автосбор: нечего искать")]]}
    conns["OpenAI: ищем поводы"] = {"main": [[L("Читаем календарь (автосбор)")]]}
    conns["Читаем календарь (автосбор)"] = {"main": [[L("Автосбор: разбор")]]}
    conns["Автосбор: разбор"] = {"main": [[L("Автосбор: строки"), L("Автосбор: итог")]]}
    conns["Автосбор: строки"] = {"main": [[L("Автосбор: записываем")]]}
    conns["Автосбор: итог"] = {"main": [[L("Автосбор: сообщаем")]]}

    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(wf, f, ensure_ascii=False, indent=2)
    print("ok: автосбор в 11")


if __name__ == "__main__":
    main()
