"""Добавляет в workflows/04_Video.json переводы названия и описания (локализации YouTube).

Ветка от успешной загрузки: Готовим переводы → OpenAI: переводы → Собираем локализации
→ Переводы готовы? → Ставим переводы на YouTube → Итог переводов → Сообщаем: переводы.
Какие языки — служебная колонка tmpl_Languages в Templates («es, de, fr»; пусто — ветка
молча кончается). Как переводить — колонки со значком 🌐. Повторный запуск ничего не дублирует.

    python3 tools/patch04_translations.py
"""
import json, os, uuid

PATH = os.path.join(os.path.dirname(__file__), "..", "workflows", "04_Video.json")

PREP = r"""// Переводы названия и описания — локализации YouTube: зритель из Испании видит
// ролик по-испански. Какие языки — служебная колонка tmpl_Languages в Templates
// («es, de, fr»); пусто — переводов нет, ветка молча кончается. Как переводить
// (что оставить как есть, тон) — колонки со значком 🌐: здесь только механика.
const tmpl = $('Читаем стиль оверлея').first().json;
const data = $('Готовим данные для сборки').first().json;
const key = Object.keys(tmpl).find(k => k.replace(/^[^a-zA-Z]+/, '') === 'tmpl_Languages');
const langs = [...new Set(String(key ? tmpl[key] || '' : '')
  .split(/[\s,;]+/).map(s => s.trim().toLowerCase())
  .filter(s => /^[a-z]{2,3}(-[a-z0-9]{2,4})?$/.test(s) && s !== 'en'))];
if (!langs.length) return [];
const rules = Object.keys(tmpl)
  .filter(k => k.includes('🌐') && String(tmpl[k] || '').trim())
  .map(k => String(tmpl[k]).trim()).join('\n\n');
const systemPrompt = 'Translate the title and the description of a YouTube video from English into these languages (codes): '
  + langs.join(', ') + '.\n'
  + 'Answer with JSON only: {"<code>": {"title": "...", "description": "..."}} — one entry for every code.\n'
  + 'Keep line breaks, the timestamps at the start of lines (0:00, 12:34, 1:02:03), links and hashtags exactly as they are. '
  + 'The title must stay under 100 characters. Never use the characters < and >.'
  + (rules ? '\n\n' + rules : '');
return [{ json: { langs, systemPrompt, userPrompt: JSON.stringify({ title: data.title, description: data.description }) } }];"""

BUILD = r"""// Ответ переводчика → тело videos.update. Этот вызов переписывает snippet целиком,
// поэтому кладём в него ровно то, что ушло при загрузке (название, описание, теги,
// категорию) — иначе YouTube стёр бы описание и теги. defaultLanguage обязателен,
// без него YouTube не принимает локализации.
if ($json.error) return [{ json: { error: 'переводчик не ответил: ' + JSON.stringify($json.error).slice(0, 200) } }];
const data = $('Готовим данные для сборки').first().json;
const up = $('Загружаем на YouTube').first().json;
const prep = $('Готовим переводы').first().json;
let parsed;
try { parsed = JSON.parse($json.choices[0].message.content); }
catch (e) { return [{ json: { error: 'переводчик ответил не JSON' } }]; }
const clean = s => String(s || '').replace(/[<>]/g, '').trim();
const localizations = {};
for (const l of prep.langs) {
  const t = parsed[l] || {};
  const title = clean(t.title);
  if (!title) continue;
  let description = clean(t.description);
  while (Buffer.byteLength(description, 'utf8') > 5000) description = description.slice(0, -50);
  localizations[l] = { title: title.slice(0, 100), description };
}
if (!Object.keys(localizations).length) return [{ json: { error: 'в ответе нет ни одного перевода' } }];
// те же теги, что при загрузке (тот же отбор под лимит 500 символов)
const seen = new Set(); const tags = []; let used = 0;
for (const raw of String(data.tags || '').split(',')) {
  const t = raw.trim(); const k = t.toLowerCase();
  if (!t || seen.has(k)) continue;
  const cost = t.length + (t.includes(' ') ? 2 : 0) + (tags.length ? 1 : 0);
  if (used + cost > 480) break;
  seen.add(k); tags.push(t); used += cost;
}
return [{ json: {
  error: '',
  langs: Object.keys(localizations),
  body: {
    id: up.uploadId,
    snippet: { title: data.title, description: data.description, categoryId: '10', tags, defaultLanguage: 'en' },
    localizations,
  },
} }];"""

RESULT = r"""// Итог для автора: какие языки встали, или почему не встали (ролик при этом уже на YouTube).
const built = $('Собираем локализации').first().json;
const err = built.error || ($json.error ? JSON.stringify($json.error).slice(0, 300) : '');
const text = err
  ? '🌐 Переводы названия и описания не встали: ' + err + '\nРолик загружен; переводы можно добавить в YouTube Studio → Субтитры.'
  : '🌐 Переводы названия и описания: ' + built.langs.join(', ');
return [{ json: { chatId: $('Готовим данные для сборки').first().json.chatId, text } }];"""


def main():
    wf = json.load(open(PATH, encoding="utf-8"))
    nodes = {n["name"]: n for n in wf["nodes"]}
    conns = wf["connections"]
    up = nodes["Загружаем на YouTube"]
    yt_cred = up["credentials"]
    ai_cred = nodes["OpenAI: названия треков"]["credentials"]
    x, y = up["position"]
    y += 400

    def put(node):
        node.setdefault("id", str(uuid.uuid4()))
        if node["name"] in nodes:
            old = nodes[node["name"]]
            node["id"] = old["id"]
            wf["nodes"][wf["nodes"].index(old)] = node
        else:
            wf["nodes"].append(node)
        nodes[node["name"]] = node

    put({"parameters": {"jsCode": PREP}, "name": "Готовим переводы", "type": "n8n-nodes-base.code",
         "typeVersion": 2, "position": [x + 224, y]})
    put({"parameters": {
            "method": "POST", "url": "https://api.openai.com/v1/chat/completions",
            "authentication": "predefinedCredentialType", "nodeCredentialType": "openAiApi",
            "sendBody": True, "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({ model: 'gpt-4o', response_format: { type: 'json_object' }, messages: [ { role: 'system', content: $json.systemPrompt }, { role: 'user', content: $json.userPrompt } ] }) }}",
            "options": {"timeout": 180000}},
         "name": "OpenAI: переводы", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.4,
         "position": [x + 448, y], "credentials": ai_cred, "continueOnFail": True})
    put({"parameters": {"jsCode": BUILD}, "name": "Собираем локализации", "type": "n8n-nodes-base.code",
         "typeVersion": 2, "position": [x + 672, y]})
    put({"parameters": {
            "conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
                           "conditions": [{"leftValue": "={{ $json.error }}", "rightValue": "",
                                           "operator": {"type": "string", "operation": "equals"}}],
                           "combinator": "and"},
            "options": {}},
         "name": "Переводы готовы?", "type": "n8n-nodes-base.if", "typeVersion": 2,
         "position": [x + 896, y]})
    put({"parameters": {
            "method": "PUT", "url": "https://www.googleapis.com/youtube/v3/videos?part=snippet,localizations",
            "authentication": "predefinedCredentialType", "nodeCredentialType": "youTubeOAuth2Api",
            "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.body) }}",
            "options": {}},
         "name": "Ставим переводы на YouTube", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.4,
         "position": [x + 1120, y - 96], "credentials": yt_cred, "continueOnFail": True})
    put({"parameters": {"jsCode": RESULT}, "name": "Итог переводов", "type": "n8n-nodes-base.code",
         "typeVersion": 2, "position": [x + 1344, y]})
    put({"parameters": {
            "method": "POST", "url": "=https://api.telegram.org/bot{{ $env.TELEGRAM_BOT_TOKEN }}/sendMessage",
            "sendBody": True, "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({ chat_id: $json.chatId, text: $json.text }) }}",
            "options": {}},
         "name": "Сообщаем: переводы", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.4,
         "position": [x + 1568, y], "continueOnFail": True})

    link = lambda a, b, out=0: {"node": b, "type": "main", "index": 0}
    ok = conns["Загружаем на YouTube"]["main"][0]
    if not any(t["node"] == "Готовим переводы" for t in ok):
        ok.append(link(None, "Готовим переводы"))
    conns["Готовим переводы"] = {"main": [[link(None, "OpenAI: переводы")]]}
    conns["OpenAI: переводы"] = {"main": [[link(None, "Собираем локализации")]]}
    conns["Собираем локализации"] = {"main": [[link(None, "Переводы готовы?")]]}
    conns["Переводы готовы?"] = {"main": [[link(None, "Ставим переводы на YouTube")], [link(None, "Итог переводов")]]}
    conns["Ставим переводы на YouTube"] = {"main": [[link(None, "Итог переводов")]]}
    conns["Итог переводов"] = {"main": [[link(None, "Сообщаем: переводы")]]}

    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(wf, f, ensure_ascii=False, indent=2)
    print("ok: переводы в 04")


if __name__ == "__main__":
    main()
