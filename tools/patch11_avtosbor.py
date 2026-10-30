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
COLS = ['id', 'year', 'month', 'day', 'title', 'channel', 'status', 'project', 'note', 'sources', 'createdAt', 'updatedAt', 'title_ru', 'tag']

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
const srows = $('Читаем, что искать').all().map(i => i.json || {});
// что искать — общий текст листа «Автосбор» (без каналов); страны — для официальных праздников
const what = srows.map(r => String(r['Что искать'] || '').trim()).filter(Boolean).join('\n');
const model = srows.map(r => String(r['Модель'] || '').trim()).find(Boolean) || 'gpt-5';
const countries = [...new Set((srows.map(r => String(r['Страны'] || '')).join(',').toUpperCase().match(/\b[A-Z]{2}\b/g) || []))];
const chatId = msg ? msg.chat.id : 285577543;
if (!what) return [{ json: { need: false, chatId, text: 'Лист «Автосбор» пуст: не знаю, что искать.' } }];
const last = new Date(y, m, 0).getDate();
const ranges = [[1, 10], [11, 20], [21, last]];   // три запроса по ~10 дней — ответы не гигантские
return [{ json: { need: true, chatId, y, m, monthRu: MON_RU[m - 1], monthEn: MON_EN[m - 1], what, model, countries, ranges,
  text: '🔎 Ищу поводы на ' + MON_RU[m - 1] + ' ' + y + ' — три части по десять дней, это 5–15 минут.' } }];"""

RAZBOR = r"""// Ответы ИИ (три части месяца) → строки листа «Календарь». Повторы (тот же день и то же название) с листом
// и между частями не добавляются. Новые — «Идея», без канала, суть — в note, значок — в tag.
const z = $('Автосбор: задание').first().json;
const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const parts = $('OpenAI: ищем поводы').all().map(i => i.json || {});
let items = []; const bad = [];
parts.forEach((resp, n) => {
  const out = (resp.output || []).filter(i => i.type === 'message')
    .flatMap(i => (i.content || []).filter(c => c.type === 'output_text').map(c => c.text)).join('\n');
  try {
    const a = out.indexOf('{'), b = out.lastIndexOf('}');
    const arr = JSON.parse(out.slice(a, b + 1)).items;
    if (!Array.isArray(arr)) throw new Error('no items');
    items = items.concat(arr);
  } catch (e) {
    bad.push('часть ' + (n + 1) + ': ' + (resp.error ? String(resp.error.message || JSON.stringify(resp.error)).slice(0, 150) : 'ответ не разобрался'));
  }
});
if (!items.length) return [{ json: { rows: [], text: '⚠️ Автосбор на ' + z.monthRu + ' не получился: ' + esc(bad.join('; ') || 'пусто') } }];
const norm = s => String(s || '').toLowerCase().replace(/[^a-zа-яё0-9]+/gi, ' ').trim();
const seen = new Set();
for (const r of $('Читаем календарь (автосбор)').all().map(i => i.json)) {
  if (!r || !r.id) continue;
  seen.add(Number(r.month) + '-' + Number(r.day) + '|' + norm(r.title));
}
const now = new Date().toISOString();
const stamp = now.slice(8, 10) + '.' + now.slice(5, 7);
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
  rows.push({ id: 'a' + Date.now().toString(36) + rows.length.toString(36) + Math.random().toString(36).slice(2, 5),
    year: String(z.y), month: String(z.m), day: String(Number(md[3])), title, channel: '',
    status: 'Идея', project: '', note: String(it.about_ru || '').trim().slice(0, 1200),
    sources: 'автосбор ' + stamp + (it.source ? '; ' + String(it.source).trim() : ''),
    createdAt: now, updatedAt: now, title_ru: String(it.title_ru || '').trim(), tag: String(it.tag || '').trim().slice(0, 8) });
}
rows.sort((a, b) => Number(a.day) - Number(b.day));
let text = '🗓 Автосбор на ' + z.monthRu + ' ' + z.y + ': найдено ' + found + ', новых ' + rows.length + '. Всё — в календаре, у каждого повода суть.';
if (bad.length) text += '\n⚠️ Не получилось: ' + esc(bad.join('; ')) + '. Можно повторить: «собери ' + z.monthRu + '».';
return [{ json: { rows, text } }];"""



STRANY = r"""// по элементу на страну — официальные праздники из бесплатного календаря (date.nager.at)
const z = $('Автосбор: задание').first().json;
const list = (z.countries && z.countries.length) ? z.countries : ['US'];
return list.map(cc => ({ json: { cc, y: z.y } }));"""

CHASTI = r"""// три запроса к ИИ (дни 1–10, 11–20, 21–конец); в каждый — официальные праздники стран этих дней
const z = $('Автосбор: задание').first().json;
const pad = n => String(n).padStart(2, '0');
const pref = z.y + '-' + pad(z.m) + '-';
const hol = {};
for (const it of $input.all()) {
  const h = it.json || {};
  const d = String(h.date || '');
  const name = String(h.name || h.localName || '').trim();
  if (!d.startsWith(pref) || !name) continue;
  const key = d + '|' + name.toLowerCase();
  (hol[key] = hol[key] || { date: d, name, local: String(h.localName || '').trim(), cc: [] }).cc.push(String(h.countryCode || ''));
}
const hl = Object.values(hol);
const FORMAT = 'Answer with JSON only, no other text: {"items": [{"date": "YYYY-MM-DD", "title": "the original name as it is known (English if it has one)", '
  + '"title_ru": "Russian name", "about_ru": "2-3 sentences in Russian: what this day is, where it comes from, how it is marked", '
  + '"tag": "one emoji: the country flag for a national or local occasion, 🌍 for international or world days, 🕯 for religious, 🌙 for seasonal or astronomical, 🎗 for memorial", '
  + '"source": "site name"}]}. Never invent a date; skip what you cannot date for ' + z.y + '. Do not assign channels and do not suggest episode ideas.';
return z.ranges.map(([a, b]) => {
  const inR = hl.filter(h => { const d = Number(h.date.slice(8, 10)); return d >= a && d <= b; });
  const off = inR.length ? '\n\nOfficial public holidays in this period (include every one, each as its own item; name the countries in about_ru):\n'
    + inR.map(h => '- ' + h.date + ' ' + h.name + (h.local && h.local !== h.name ? ' (' + h.local + ')' : '') + ' — ' + [...new Set(h.cc)].join(', ')).join('\n') : '';
  const instructions = 'You collect occasions for a content calendar. Period: ' + z.monthEn + ' ' + a + '-' + b + ', ' + z.y
    + '. Use web search to check the dates for this year.\nWhat to collect:\n' + z.what + off + '\n\n' + FORMAT + ' Up to 120 items, sorted by date.';
  const requestBody = { model: z.model, instructions, tools: [{ type: 'web_search' }],
    input: [{ role: 'user', content: 'Collect the occasions for ' + z.monthEn + ' ' + a + '-' + b + ', ' + z.y + ' as JSON.' }] };
  if (/^(gpt-5|o\d)/.test(z.model)) requestBody.reasoning = { effort: 'low' };
  return { json: { a, b, requestBody } };
});"""


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
    put(send("Автосбор: начали", [X + 440, Y - 520]))
    put(iff("Есть что искать?", "$('Автосбор: задание').first().json.need", [X + 440, Y]))
    put({"parameters": {"jsCode": STRANY}, "name": "Автосбор: страны", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [X + 660, Y - 320]})
    put({"parameters": {"url": "={{ 'https://date.nager.at/api/v3/PublicHolidays/' + $json.y + '/' + $json.cc }}", "options": {"timeout": 30000}},
         "name": "Праздники стран", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": [X + 880, Y - 320],
         "onError": "continueRegularOutput", "alwaysOutputData": True})
    put({"parameters": {"jsCode": CHASTI}, "name": "Автосбор: части", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [X + 1100, Y - 320]})
    put({"parameters": {"method": "POST", "url": "https://api.openai.com/v1/responses", "authentication": "predefinedCredentialType",
         "nodeCredentialType": "openAiApi", "sendBody": True, "specifyBody": "json",
         "jsonBody": "={{ JSON.stringify($json.requestBody) }}", "options": {"timeout": 600000}},
         "name": "OpenAI: ищем поводы", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": [X + 660, Y],
         "credentials": AI, "onError": "continueRegularOutput"})
    put({"parameters": {"authentication": "serviceAccount", "documentId": DOC,
         "sheetName": {"__rl": True, "value": "Календарь", "mode": "name"}, "filtersUI": {"values": []}, "options": {}},
         "name": "Читаем календарь (автосбор)", "type": "n8n-nodes-base.googleSheets", "typeVersion": 4, "position": [X + 880, Y],
         "credentials": GS, "alwaysOutputData": True, "executeOnce": True})
    put({"parameters": {"jsCode": RAZBOR}, "name": "Автосбор: разбор", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [X + 1100, Y],
         "notes": "вход — ответ OpenAI (через чтение календаря он не проходит: читаем $('OpenAI: ищем поводы'))"})
    # разбор читает ответ ИИ по имени узла, а не $json (вход — строки календаря)
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
    conns["Есть что искать?"] = {"main": [[L("Автосбор: начали"), L("Автосбор: страны")], [L("Автосбор: нечего искать")]]}
    conns["Автосбор: страны"] = {"main": [[L("Праздники стран")]]}
    conns["Праздники стран"] = {"main": [[L("Автосбор: части")]]}
    conns["Автосбор: части"] = {"main": [[L("OpenAI: ищем поводы")]]}
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
