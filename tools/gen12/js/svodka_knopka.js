// Одно сообщение с единственной финальной кнопкой — после всех кусков сводки.
const s = $('Сводка').first().json;
return [{ json: { chatId: s.chatId, text: s.buttonText, callbackData: s.callbackData } }];
