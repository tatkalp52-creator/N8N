// «как чистка?» / «статус»: что с чисткой этого выпуска.
const ctx = $('Контекст проекта').first().json;
const row = ctx.row || {};
const state = String(row.sys_CleanState || '').trim();
const tag = String(row.sys_CleanTag || '').trim();
const nbKey = Object.keys(ctx.tmpl || {}).find(k => k.includes('tmpl_CleanNotebook'));
const notebook = nbKey ? String(ctx.tmpl[nbKey] || '').trim() : '';
let r = null;
try { r = $('Сервер: как чистка (статус)').first().json || null; } catch (e) {}
const ask = state === 'идёт' && !!tag;
const mins = row.sys_CleanStarted ? Math.round((Date.now() - Date.parse(row.sys_CleanStarted)) / 60000) : null;
let text, button = false, update = false, newState = state, audioUrl = '';
if (ask && !r) {
  // первый проход: сначала спросить сервер
  return [{ json: { ask: true, statusBody: { cleanNotebook: notebook, tag } } }];
}
if (!state) text = 'Чистка для этого выпуска не запускалась.';
else if (r && r.state === 'complete') { text = '✅ Чистка готова, треки забраны.'; button = true; update = true; newState = 'готово'; audioUrl = `${notebook}#run=${tag}`; }
else if (r && r.state === 'error') { text = `❌ Чистка не удалась: ${escapeHtml(r.message || '')}\nМожно прислать ссылку ещё раз.`; update = true; newState = `ошибка: ${r.message || ''}`.trim(); }
else if (state === 'идёт') text = `🧼 Чистка идёт${mins != null ? ` (${mins} мин)` : ''}.`;
else if (state === 'готово') { text = '✅ Чистка готова.'; button = true; }
else text = `Состояние чистки: ${escapeHtml(state)}`;
return [{ json: { ask: false, chatId: ctx.chatId, projectId: ctx.projectId, button, update, state: newState, audioUrl,
                  callbackData: `build|${ctx.projectId}`,
                  text: `${text}${button ? '\nСобрать видео — кнопка ниже.' : ''}\n\nID: ${ctx.projectId}` } }];
