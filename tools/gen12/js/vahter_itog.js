// Вахтёр ответил: первый раз — дальше как обычно; повтор кнопки — «уже принято»; повтор сообщения — тихо стоп.
// Сервер не ответил — пропускаем (лучше лишний запуск, чем потерянное сообщение).
const r = $('Разбираем входящее').first().json;
const g = $input.first().json || {};
if (g.first !== false) return [{ json: r }];
return [{ json: { ...r, kind: r.callbackQueryId ? 'dupButton' : 'duplicate' } }];
