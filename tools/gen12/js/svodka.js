// Все этапы завершены: сводка всех пунктов — ровно то, что уйдёт в таблицу и на YouTube —
// и одна кнопка ✅. Состояние берём из этого хода, если он был, иначе из строки.
const ctx = $('Контекст проекта').first().json;
let raw = (ctx.row || {}).sys_EditorState;
try { raw = $('Итог хода').first().json.editorState; } catch (e) {}
const state = stParseState(raw);
const items = ctx.items || [];
let text = '<b>Финальная сводка</b> — все пункты согласованы.';
for (const it of items) text += `\n\n<b>${it.n}. ${escapeHtml(it.name)}</b>\n` + escapeHtml(itShow(state, it) || '— пусто');
text += `\n\nID: ${ctx.projectId}`;
const warn = String((ctx.row || {}).ai_ApprovedImageUrl || '').trim() ? '' : '\n⚠️ Картинка ещё не согласована — сначала согласуйте её, иначе кнопка не сработает.';
return splitForTelegram(text).map((t, i, all) => ({ json: {
  chatId: ctx.chatId, text: t, last: i === all.length - 1,
  buttonText: escapeHtml('Всё верно? Нажмите ✅ — я запишу всё в таблицу и проверю каждое поле.' + warn) + `\n\nID: ${ctx.projectId}`,
  callbackData: 'final|' + ctx.projectId,
} }));
