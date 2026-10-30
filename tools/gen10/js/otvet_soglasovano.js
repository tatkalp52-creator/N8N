const p = $('Парсим ответ редактора').first().json;
let text = escapeHtml(p.messageToUser || '');
// Если автор нажала кнопку — подтверждение "✅" уже ушло, не дублируем.
if (!p.fromButton) {
  text += `\n\n✅ Картинка согласована${p.approveVariantNumber ? ' (вариант ' + p.approveVariantNumber + ')' : ''}.`;
}
if (p.statusReverted) text += '\n\n⚠️ Статус «Утверждено» снят — после изменений пришлю новую сводку на ✅.';
text += `\n\nID: ${p.projectId}`;
return splitForTelegram(text).map(t => ({ json: { chatId: p.chatId, text: t } }));
