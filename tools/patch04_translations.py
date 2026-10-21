# (22.10) Переводы на языки YouTube и названия треков — дешевле и без повторов.
# 1) Пересборка не переводит заново: готовые переводы лежат в строке выпуска (sys_Translations)
#    вместе с отпечатком текста; совпал — берём их, меняются только тайм-коды.
# 2) Модель — служебная колонка Templates tmpl_LightModel (по умолчанию gpt-5-mini), не gpt-4o.
# Повторный запуск скрипта ничего не меняет.
import json, os, uuid
P = os.path.join(os.path.dirname(__file__), '..', 'workflows', '04_Video.json')
w = json.load(open(P, encoding='utf-8'))
N = {n['name']: n for n in w['nodes']}
c = w['connections']

BODY = ("={{ JSON.stringify(Object.assign({ model: $json.model || 'gpt-5-mini', response_format: { type: 'json_object' }, "
        "messages: [ { role: 'system', content: $json.systemPrompt }, { role: 'user', content: $json.userPrompt } ] }, "
        "/^gpt-5/.test($json.model || 'gpt-5-mini') ? { reasoning_effort: 'minimal' } : {})) }}")
for nm in ('OpenAI: названия треков', 'OpenAI: переводы'):
    N[nm]['parameters']['jsonBody'] = BODY

LIGHT = """// (22.10) лёгкая модель для служебных текстов — служебная колонка Templates tmpl_LightModel
const lightModel = String((Object.entries(%s).find(([k]) => k.replace(/^[^a-zA-Z]+/, '') === 'tmpl_LightModel') || [])[1] || '').trim() || 'gpt-5-mini';
"""
code = N['Готовим запрос на названия треков']['parameters']['jsCode']
if 'lightModel' not in code:
    code = code.replace("const channelRow = $json;\n", "const channelRow = $json;\n" + LIGHT % 'channelRow', 1)
    code = code.replace("return [{ json: { skipGpt: false, prewritten, systemPrompt,", "return [{ json: { skipGpt: false, model: lightModel, prewritten, systemPrompt,", 1)
    assert 'model: lightModel' in code
    N['Готовим запрос на названия треков']['parameters']['jsCode'] = code

code = N['Готовим переводы']['parameters']['jsCode']
if 'sys_Translations' not in code:
    old = "return [{ json: { langs, systemPrompt, userPrompt: JSON.stringify({ title: data.title, description: data.description }) } }];"
    assert old in code
    code = code.replace("const data = $('Готовим данные для сборки').first().json;\n",
                        "const data = $('Готовим данные для сборки').first().json;\n" + LIGHT % 'tmpl', 1)
    code = code.replace(old, """// (22.10) пересборка: тот же текст — те же переводы, OpenAI не зовём. Отпечаток — без тайм-кодов,
// они при новой сборке могут сдвинуться; в готовые переводы подставляем новые по порядку.
const TS = /\\b\\d{1,2}:\\d{2}(?::\\d{2})?\\b/g;
const fp = s => { let h = 5381; for (const ch of s) h = ((h * 33) ^ ch.codePointAt(0)) >>> 0; return h.toString(36); };
const print = fp(JSON.stringify([langs, data.title, String(data.description || '').replace(TS, '#')]));
let cache = null;
try { cache = JSON.parse(String($('Читаем проект').first().json.sys_Translations || '') || 'null'); } catch (e) { cache = null; }
const newTs = String(data.description || '').match(TS) || [];
if (cache && cache.print === print && cache.loc) {
  const loc = {};
  let ok = true;
  for (const [l, v] of Object.entries(cache.loc)) {
    const old = String(v.description || '').match(TS) || [];
    if (old.length !== newTs.length) { ok = false; break; }
    let i = 0;
    loc[l] = { title: v.title, description: String(v.description || '').replace(TS, () => newTs[i++]) };
  }
  if (ok) return [{ json: { langs, cached: true, cachedLoc: loc, print } }];
}
return [{ json: { langs, cached: false, print, model: lightModel, systemPrompt, userPrompt: JSON.stringify({ title: data.title, description: data.description }) } }];""", 1)
    N['Готовим переводы']['parameters']['jsCode'] = code

code = N['Собираем локализации']['parameters']['jsCode']
if 'cachedLoc' not in code:
    old = """if ($json.error) return [{ json: { error: 'переводчик не ответил: ' + JSON.stringify($json.error).slice(0, 200) } }];
const data = $('Готовим данные для сборки').first().json;
const up = $('Загружаем на YouTube').first().json;
const prep = $('Готовим переводы').first().json;
let parsed;
try { parsed = JSON.parse($json.choices[0].message.content); }
catch (e) { return [{ json: { error: 'переводчик ответил не JSON' } }]; }"""
    assert old in code
    code = code.replace(old, """const data = $('Готовим данные для сборки').first().json;
const up = $('Загружаем на YouTube').first().json;
const prep = $('Готовим переводы').first().json;
let parsed;
if (prep.cached) parsed = prep.cachedLoc;          // (22.10) пересборка — готовые переводы
else {
  if ($json.error) return [{ json: { error: 'переводчик не ответил: ' + JSON.stringify($json.error).slice(0, 200) } }];
  try { parsed = JSON.parse($json.choices[0].message.content); }
  catch (e) { return [{ json: { error: 'переводчик ответил не JSON' } }]; }
}""", 1)
    old2 = "return [{ json: {\n  error: '',\n  langs: Object.keys(localizations),"
    assert old2 in code
    code = code.replace(old2, "return [{ json: {\n  error: '',\n  cached: !!prep.cached,\n  // в строку выпуска: следующая пересборка возьмёт отсюда\n  cacheJson: JSON.stringify({ print: prep.print, loc: localizations }),\n  langs: Object.keys(localizations),", 1)
    N['Собираем локализации']['parameters']['jsCode'] = code

RETRY = {'retryOnFail': True, 'maxTries': 3, 'waitBetweenTries': 5000}
names = set(N)
if 'Переводы уже есть?' not in names:
    w['nodes'].append({'parameters': {'conditions': {'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'loose'},
        'conditions': [{'id': str(uuid.uuid5(uuid.NAMESPACE_URL, '04-tr-if')), 'leftValue': '={{ !!$json.cached }}', 'rightValue': True,
                        'operator': {'type': 'boolean', 'operation': 'true', 'singleValue': True}}], 'combinator': 'and'}, 'options': {}},
        'name': 'Переводы уже есть?', 'type': 'n8n-nodes-base.if', 'typeVersion': 2, 'position': [7920, 1860],
        'id': str(uuid.uuid5(uuid.NAMESPACE_URL, 'n8n-04-Переводы уже есть?'))})
    c['Готовим переводы'] = {'main': [[{'node': 'Переводы уже есть?', 'type': 'main', 'index': 0}]]}
    c['Переводы уже есть?'] = {'main': [[{'node': 'Собираем локализации', 'type': 'main', 'index': 0}],
                                         [{'node': 'OpenAI: переводы', 'type': 'main', 'index': 0}]]}
if 'Запоминаем переводы' not in names:
    sheet = json.loads(json.dumps(N['Ставим статус Опубликовано']))
    sheet['name'] = 'Запоминаем переводы'
    sheet['id'] = str(uuid.uuid5(uuid.NAMESPACE_URL, 'n8n-04-Запоминаем переводы'))
    sheet['position'] = [8480, 1860]
    sheet['parameters']['columns']['value'] = {'sys_ProjectID': "={{ $('Читаем проект').first().json.sys_ProjectID }}",
                                               'sys_Translations': "={{ $('Собираем локализации').first().json.cacheJson }}"}
    sheet['continueOnFail'] = True
    w['nodes'].append(sheet)
    outs = c['Переводы готовы?']['main'][0]
    if not any(t['node'] == 'Запоминаем переводы' for t in outs):
        outs.append({'node': 'Запоминаем переводы', 'type': 'main', 'index': 0})
json.dump(w, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('ok')
