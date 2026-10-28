// Приёмная: всё, что пришло (Телеграм, календарь, переход этапа), — в один конверт для очереди.
let source = 'inner', body = null;
try { body = $('Telegram Trigger').first().json; source = 'tg'; } catch (e) {}
if (source !== 'tg') { try { body = $('Из календаря').first().json; source = 'cal'; } catch (e) {} }
if (source === 'inner') body = $('Вызов изнутри').first().json;
return [{ json: { ...inboxEnvelope(source, body), exec: $execution.id } }];
