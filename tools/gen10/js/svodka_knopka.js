// Одно сообщение с единственной финальной кнопкой — после всех кусков сводки.
const s = $('Сводка на утверждение').first().json;
return [{ json: { chatId: s.chatId, text: escapeHtml(s.buttonText), callbackData: 'final|' + s.projectId } }];
