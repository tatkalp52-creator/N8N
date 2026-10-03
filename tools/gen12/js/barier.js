// СТЕНА ПЕРЕД СБОРЩИКОМ: проверяем заново перечитанную строку. Если чего-то
// не хватает — до сообщения «приступаю к сборке» и до 04_Video цепочка не доходит.
const ctx = $('Контекст проекта').first().json;
const fresh = $input.first().json || {};
const cleanMode = String(findByLabel(ctx.tmpl || {}, 'tmpl_CleanMode') || '').trim();
const tracks = String(fresh.sys_AudioZipUrl || '');
const cleanNote = cleanMode && !tracks.includes('kaggle.com/code/')
  ? `Сначала чистка звука в Kaggle (${cleanMode}) — это несколько часов, потом сборка. Напишу, когда видео будет на канале.`
  : '';
const problems = validateRow(fresh, ctx.items || [], { needApproved: true, needTracks: true });
return [{ json: {
  ok: problems.length === 0,
  chatId: ctx.chatId,
  projectId: ctx.projectId,
  okText: `Треки получены, приступаю к сборке 🎬\nВсе поля в таблице на месте — передаю сборщику видео.` + (cleanNote ? `\n${cleanNote}` : '') + `\n\nID: ${ctx.projectId}`,
  problemsText: 'Сборку НЕ запускаю — в таблице не хватает:\n• ' + problems.join('\n• ') + `\n\nID: ${ctx.projectId}`,
} }];
