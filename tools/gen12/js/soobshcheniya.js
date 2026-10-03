// Сообщения хода — по одному на кусок (лимит Телеграма); если сказать нечего — один пропуск.
const r = $('Итог хода').first().json;
if (!r.chunks || !r.chunks.length) return [{ json: { skip: true } }];
return r.chunks.map(text => ({ json: { skip: false, chatId: r.chatId, text } }));
