// В работу: одно входящее — один запуск «Работы». Сюда приходят новое из Приёмной и повтор из очереди.
let it = null;
try { it = $('Изнутри: что это?').first().json.resume; } catch (e) {}
if (!it) it = $('Очередь: решение').first().json;
const b = it.body || {};
const chatId = it.chatId || (b.message && b.message.chat ? b.message.chat.id : null);
return [{ json: { key: it.key, source: it.source || (b.update_id != null ? 'tg' : (b.body ? 'cal' : 'inner')), body: b, chatId,
  tries: it.tries || 1, quote: inboxQuote(it) } }];
