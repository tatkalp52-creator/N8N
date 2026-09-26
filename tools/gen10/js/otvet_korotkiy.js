// Короткая реплика перед рисованием/правкой — ровно ОДНО сообщение, чтобы
// следующая ветка (рисование) запустилась ровно один раз.
const p = $('Парсим ответ редактора').first().json;
const msg = String(p.messageToUser || 'Рисую!').slice(0, 3500);
return [{ json: { chatId: p.chatId, text: escapeHtml(msg) + `\n\nID: ${p.projectId}` } }];
