// Следующее ждущее этого выпуска — отдельным запуском, через ту же «В работу».
let next = null;
try { next = $('Очередь: сделано').first().json.next; } catch (e) {}
if (!next) { try { next = $('Сбой: что сказать').first().json.next; } catch (e) {} }
return next ? [{ json: { resume: next } }] : [];
