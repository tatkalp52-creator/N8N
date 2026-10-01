// Проснулись: либо постучал блокнот, либо сработал будильник.
// Сначала сверяемся с таблицей: это всё ещё наша чистка?
const start = $('Чистка: запущена?').first().json;
const fresh = $('Перечитываем строку (чистка)').first().json || {};
const w = $('Ждём стук Kaggle').first().json || {};
const knock = w.body && typeof w.body === 'object' && w.body.tag ? w.body : null;
const ours = String(fresh.sys_CleanTag || '') === start.tag && String(fresh.sys_CleanState || '') === 'идёт';
let action = 'ask';
let failure = '';
if (!ours) action = 'stop';           // уже обработано (статусом) или запущена новая чистка
else if (knock && knock.tag === start.tag && knock.ok === false) { action = 'failed'; failure = knock.error || 'ошибка в блокноте'; }
return [{ json: { action, failure, knocked: !!knock, tag: start.tag, notebookUrl: start.notebookUrl,
                  statusBody: { cleanNotebook: start.notebookUrl, tag: start.tag } } }];
