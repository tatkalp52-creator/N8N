// СТЕНА ПЕРЕД СБОРЩИКОМ: проверяем заново перечитанную строку. Если чего-то
// не хватает — до сообщения «приступаю к сборке» и до 04_Video цепочка не доходит.
const ctx = $('Контекст проекта').first().json;
const fresh = $input.first().json || {};
// Чистка: сюда доходят только когда она уже не нужна или закончилась. Если же она ещё идёт
// («пересобери» или ✅ посреди чистки) — не собираем на сырых треках: соберётся сам после чистки.
const cleanState = String(fresh.sys_CleanState || '').trim();
const cleaning = cleanState === 'идёт';
const cleanNote = /^ошибка/.test(cleanState) ? '⚠️ Последняя чистка не удалась — собираю на исходных треках.' : '';
const problems = validateRow(fresh, ctx.items || [], { needApproved: true, allowPublished: true, needTracks: true });
return [{ json: {
  ok: problems.length === 0 && !cleaning,
  chatId: ctx.chatId,
  projectId: ctx.projectId,
  okText: `Треки получены, приступаю к сборке 🎬\nВсе поля в таблице на месте — передаю сборщику видео.` + (cleanNote ? `\n${cleanNote}` : '') + `\n\nID: ${ctx.projectId}`,
  problemsText: (cleaning ? 'Чистка звука ещё идёт — соберу сам, как только она закончится. Сейчас ничего делать не нужно.' : '')
    + (cleaning && problems.length ? '\n\n' : '')
    + (problems.length ? 'Сборку НЕ запускаю — в таблице не хватает:\n• ' + problems.join('\n• ') : '') + `\n\nID: ${ctx.projectId}`,
} }];
