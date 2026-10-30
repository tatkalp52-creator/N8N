const ctx = $('Контекст проекта').first().json;
const chk = $('Проверяем таблицу (финал)').first().json;
// Утверждение НЕ запускает сборку само: если ссылка на треки уже есть,
// показываем её и кнопку «🎬 Собрать с этими треками» — решает автор.
const row = $('Перечитываем строку (финал)').first().json || {};
const url = String(row.sys_AudioZipUrl || '').trim();
const text = '✅ Утверждено. Всё записано в таблицу и перепроверено по каждому полю.' +
  (chk.hasTracks
    ? `\n\nВ таблице уже есть треки:\n${escapeHtml(url)}` +
      (url.includes('kaggle.com/code/') ? '\n(это блокнот Kaggle — возьму его последний готовый результат)' : '') +
      '\n\nСобрать с ними — кнопка ниже. Новые треки — пришлите ссылку ответом на это сообщение.'
    : '\n\nЖду ссылку на треки: пришлите её ответом на это сообщение.') +
  `\n\nID: ${ctx.projectId}`;
return [{ json: { chatId: ctx.chatId, text, hasTracks: chk.hasTracks, callbackData: `build|${ctx.projectId}`, buttonText: `👇 Собрать видео с этими треками?\n\nID: ${ctx.projectId}` } }];
