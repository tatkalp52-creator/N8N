// Обычная реплика Редактора → одно или несколько сообщений (лимит Телеграма 4096).
const p = $('Парсим ответ редактора').first().json;
const body = escapeHtml(p.messageToUser || '…') + `\n\nID: ${p.projectId}`;
return splitForTelegram(body).map(text => ({ json: { chatId: p.chatId, text } }));
