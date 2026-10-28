// В работу: одно входящее — один запуск «Работы». Сюда приходят новое из Приёмной и повтор / следующее из очереди.
let it = null;
try { it = $('Изнутри: что это?').first().json.resume; } catch (e) {}
if (!it) it = $('Очередь: решение').first().json;
const job = inboxJob(it);
const b = job.body || {};
const chatId = it.chatId || (b.message && b.message.chat ? b.message.chat.id : null);
return [{ json: { key: it.key, source: job.source, body: b, chatId, tries: it.tries || 1, quote: inboxQuote(it) } }];
