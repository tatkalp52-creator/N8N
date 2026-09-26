const ctx = $('Контекст проекта').first().json;
const chk = $('Проверяем таблицу (финал)').first().json;
const text = '✅ Утверждено. Всё записано в таблицу и перепроверено по каждому полю.' +
  (chk.hasTracks ? '\n\nСсылка на треки уже есть — передаю сборщику.' : '\n\nЖду ссылку на треки: пришлите её ответом на это сообщение.') +
  `\n\nID: ${ctx.projectId}`;
return [{ json: { chatId: ctx.chatId, text, hasTracks: chk.hasTracks } }];
