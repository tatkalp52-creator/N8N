const s = $('Сводка на утверждение').first().json;
return s.chunks.map(text => ({ json: { chatId: s.chatId, text } }));
