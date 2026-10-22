// (23.10) Вахтёр: одно и то же из Телеграма — только один раз, даже если запуски идут одновременно.
// Телеграм присылает сообщение повторно, когда n8n отвечает медленно; кнопки жмутся дважды или под
// разными сообщениями с одинаковым действием. Ключ: сообщение — по update_id (1 ч), кнопка — по её
// действию (10 мин; кнопка выбора канала — ещё и по сообщению). Изнутри и из календаря — без ключа.
let t = null;
try { t = $('Telegram Trigger').first().json; } catch (e) { t = null; }
let key = '', ttl = 0;
if (t && t.callback_query) {
  const cb = t.callback_query, data = String(cb.data || '');
  key = data.includes('|') ? 'btn:' + data : 'btn:' + (cb.message ? cb.message.message_id : '') + ':' + data;
  ttl = 600;
} else if (t && t.update_id != null) {
  key = 'upd:' + t.update_id; ttl = 3600;
}
return [{ json: { key, ttl } }];
