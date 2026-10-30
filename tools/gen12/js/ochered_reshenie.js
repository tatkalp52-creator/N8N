// Очередь ответила: в работу / повтор (молча) / выпуск занят — ждёт своей очереди.
// Сервер не ответил — в работу (лучше лишний запуск, чем потерянное сообщение).
const env = $('Приёмная: конверт').first().json;
const r = $input.first().json || {};
let route = 'run';
if (r.dup) route = env.callbackId ? 'dupButton' : 'quiet';
else if (r.queued) route = env.callbackId ? 'queuedButton' : 'quiet';
return [{ json: { ...env, route } }];
