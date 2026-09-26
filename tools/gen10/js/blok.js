// Показываем текстовый блок. Номера пунктов закреплены: показываем только
// то, что ещё ждёт согласования, согласованное — одной строкой внизу.
const p = $('Парсим ответ редактора').first().json;
const ctx = $('Контекст проекта').first().json;
const kb = $('Собираем знания канала').first().json;
const state = tbParseState(p.editorState);
// Картинку согласовали словами — подтверждение идёт в начале этого же
// сообщения (после кнопки "✅" подтверждение уже отправлено отдельно).
const approvedLine = p.approvedNow && !p.fromButton
  ? `✅ Картинка согласована${p.approveVariantNumber ? ' (вариант ' + p.approveVariantNumber + ')' : ''}.\n\n`
  : '';

if (p.approvedNow && !p.textBlockTouched) {
  const t = approvedLine + escapeHtml(p.messageToUser || '') + `\n\nID: ${p.projectId}`;
  return splitForTelegram(t).map(x => ({ json: { allAgreed: false, chatId: p.chatId, text: x } }));
}

if (tbAllAgreed(state)) {
  // Все 8 согласованы → сначала переводим описание, потом шлём сводку.
  const passport = kb.characterPassport ? `\n\nПаспорт персонажа (имена пиши так, как здесь): ${kb.characterPassport.slice(0, 1500)}` : '';
  const rules = kb.translationRules ? `\n\nПравила перевода канала:\n${kb.translationRules}` : '';
  const translateBody = {
    model: 'gpt-5',
    input: [
      { role: 'system', content: 'Переведи этот текст на английский. Ответь только переводом.' + rules + passport },
      { role: 'user', content: state.items.description },
    ],
  };
  return [{ json: { allAgreed: true, translateBody, chatId: p.chatId, projectId: p.projectId } }];
}

const pending = TB_ITEMS.filter(it => !state.agreed[it.n]);
const done = TB_ITEMS.filter(it => state.agreed[it.n]);

let text = approvedLine + escapeHtml(p.messageToUser || '');
if (p.statusReverted) text += '\n\n⚠️ Статус «Утверждено» снят — после изменений пришлю новую сводку на ✅.';
text += `\n\n<b>Текстовый блок</b> — ждут согласования: ${pending.map(it => it.n).join(', ')}`;
for (const it of pending) {
  const body = tbItemText(state, it.n);
  text += `\n\n<b>${it.n}. ${it.name}</b>` + (body ? '\n' + escapeHtml(body) : ' — ещё не предложено');
}
if (done.length) {
  text += '\n\n✔️ Согласовано: ' + done.map(it => `${it.n} ${it.name}`).join(', ');
}
text += '\n\nОтвечайте по номеру или по названию пункта.';
text += `\n\nID: ${p.projectId}`;

return splitForTelegram(text).map(t => ({ json: { allAgreed: false, chatId: p.chatId, text: t } }));
