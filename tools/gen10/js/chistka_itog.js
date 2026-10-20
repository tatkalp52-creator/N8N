// Итог: готово / ошибка / ещё идёт (подождать ещё) / слишком долго.
const ctx = $('Контекст проекта').first().json;
const d = $('Чистка: что дальше').first().json;
let r = {};
try { r = $('Сервер: как чистка').first().json || {}; } catch (e) {}
const round = typeof $runIndex === 'number' ? $runIndex : 0;
const recheck = parseInt(findByLabel(ctx.tmpl || {}, 'tmpl_CleanRecheckTimes'), 10) || 3;
let action, text;
if (d.action === 'failed' || r.state === 'error') {
  action = 'failed';
  text = `❌ Чистка не удалась: ${escapeHtml(d.failure || r.message || 'без подробностей')}\nМожно прислать ссылку на треки ещё раз.`;
} else if (r.state === 'complete') {
  action = 'done';
  text = '✅ Треки почищены.';
} else if (round < recheck) {
  action = 'wait_more';
  text = `🧼 Чистка ещё идёт — проверяю сама, напишу, как будет готово.`;
} else {
  action = 'gave_up';
  text = `🧼 Чистка идёт дольше обычного. Я перестала проверять сама — спросите «как чистка?» позже.`;
}
const approved = String(($('Перечитываем строку (чистка)').first().json || {}).sys_Status || '') === 'Утверждено';
if (action === 'done') text += approved ? ' Собираю видео 🎬' : ' Сборка начнётся после финальной ✅ (или кнопкой «🎬 Собрать»).';
return [{ json: {
  action, approved, chatId: ctx.chatId, projectId: ctx.projectId,
  // (20.10) «ещё идёт» сообщаем один раз — дальше проверяем молча
  quiet: action === 'wait_more' && round > 0,
  state: action === 'done' ? 'готово' : action === 'failed' ? `ошибка: ${d.failure || r.message || ''}`.trim() : 'идёт',
  audioUrl: action === 'done' ? `${d.notebookUrl}#run=${d.tag}` : '',
  text: `${text}\n\nID: ${ctx.projectId}`,
} }];
