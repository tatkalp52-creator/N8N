// СТЕНА ПЕРЕД СБОРЩИКОМ. Сообщение "Треки получены, приступаю к сборке"
// стоит в канвасе ТОЛЬКО после этой проверки — если в таблице (строка
// перечитана заново прямо перед проверкой) чего-то не хватает, до этого
// сообщения и до вызова сборщика цепочка физически не доходит.
const ctx = $('Контекст проекта').first().json;
const fresh = $input.first().json || {};
const problems = validateForAssembler(fresh, ctx.tmpl || {}, { needApproved: true, needTracks: true });
return [{
  json: {
    ok: problems.length === 0,
    chatId: ctx.chatId,
    projectId: ctx.projectId,
    okText: `Треки получены, приступаю к сборке 🎬\nВсе поля в таблице на месте — передаю сборщику видео.\n\nID: ${ctx.projectId}`,
    problemsText: 'Сборку НЕ запускаю — в таблице не хватает:\n• ' + problems.join('\n• ') + `\n\nID: ${ctx.projectId}`,
  }
}];
