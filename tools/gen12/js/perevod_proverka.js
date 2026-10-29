// (29.10) Проверка перевода для автора: пункты, чей перевод не по-русски (или его нет), — переводчику ещё раз,
// только они. Итог хода берёт лучшее из двух ответов; не получилось и со второго раза — автор видит это прямо.
const pv = $('Перевод для автора: что').first().json;
if (pv.art || !(pv.todo || []).length) return [{ json: { retry: false } }];
let resp = null;
try { resp = $('OpenAI: перевод для автора').first().json || null; } catch (e) { resp = null; }
const map = ruRead(resp).map;
const bad = pv.todo.filter(t => !ruGood(map[String(t.n)]));
if (!bad.length) return [{ json: { retry: false } }];
const src = {};
for (const t of bad) src[String(t.n)] = t.text;
const requestBody = { ...pv.requestBody,
  instructions: pv.requestBody.instructions + '\n\nThese texts came back untranslated last time. Translate every one of them into Russian.',
  input: [{ role: 'user', content: 'Texts to translate (JSON):\n' + JSON.stringify(src) }] };
return [{ json: { retry: true, todo: bad, requestBody } }];
