// Все 8 пунктов согласованы: собираем финальную сводку с английским
// описанием (ровно то, что уйдёт на YouTube) и сохраняем перевод в состояние.
const p = $('Парсим ответ редактора').first().json;
const ctx = $('Контекст проекта').first().json;
const state = tbParseState(p.editorState);

const response = $input.first().json;
const out = response.output || [];
const translated = out
  .filter(i => i.type === 'message')
  .flatMap(i => (i.content || []).filter(c => c.type === 'output_text').map(c => c.text))
  .join('\n\n')
  .trim();
const originalReady = !!$('Собираем текстовый блок').first().json.originalReady;
let descriptionEN;
if (originalReady) {
  // Описание — английский оригинал Писателя; пришёл свежий русский перевод для автора.
  descriptionEN = state.items.description;
  state.ru = state.ru || {};
  if (translated) state.ru.description = translated;
} else {
  descriptionEN = translated;
  if (!descriptionEN) throw new Error('Перевод описания пришёл пустым — сводку не отправляю');
  state.descriptionEN = descriptionEN;
  state.descriptionENFor = state.items.description;
}

let text = escapeHtml(p.messageToUser || '');
if (p.statusReverted) text += '\n\n⚠️ Статус «Утверждено» снят — нужно заново нажать ✅ под этой сводкой.';
text += '\n\n<b>Финальная сводка</b> — все 8 пунктов согласованы.';
for (const it of TB_ITEMS) {
  if (it.n === 3) {
    text += originalReady
      ? `\n\n<b>${it.n}. ${it.name}</b> <i>(так уйдёт на YouTube)</i>\n` + escapeHtml(tbItemText(state, 3))
      : `\n\n<b>${it.n}. ${it.name}</b>\n` + escapeHtml(tbItemText(state, 3)) + '\n\n<i>EN — так уйдёт на YouTube:</i>\n' + escapeHtml(descriptionEN);
    continue;
  }
  text += `\n\n<b>${it.n}. ${it.name}</b>\n` + escapeHtml(tbItemText(state, it.n));
}
text += `\n\nID: ${p.projectId}`;

const warn = String((ctx.row || {}).ai_ApprovedImageUrl || '').trim() ? '' : '\n⚠️ Картинка ещё не согласована — сначала согласуйте её, иначе кнопка не сработает.';

return [{
  json: {
    chatId: p.chatId,
    projectId: p.projectId,
    sheetName: p.sheetName,
    chunks: splitForTelegram(text),
    editorState: JSON.stringify(state),
    buttonText: 'Всё верно? Нажмите ✅ — я запишу всё в таблицу и проверю каждое поле.' + warn + `\n\nID: ${p.projectId}`,
  }
}];
