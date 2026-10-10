// Ответ сервера на «запусти чистку».
const ctx = $('Контекст проекта').first().json;
const prep = $('Чистка: нужна?').first().json;
const r = $input.first().json || {};
const ok = !!r.ok && !!r.tag;
const err = r.error || (r.message) || 'сервер не ответил';
return [{
  json: {
    ok,
    tag: ok ? r.tag : '',
    notebookUrl: r.notebookUrl || prep.body.cleanNotebook,
    state: ok ? 'идёт' : `ошибка: ${err}`,
    started: ok ? new Date().toISOString() : '',
    source: prep.body.tracksUrl,
    chatId: ctx.chatId,
    projectId: ctx.projectId,
    text: ok
      ? `🧼 Чистка звука запущена (${prep.mode}). Это несколько часов — напишу, когда закончится.\n` +
        `Если за ${prep.alarmHours} ч новостей не будет, проверю сама. Спросить в любой момент: «как чистка?».\n\nID: ${ctx.projectId}`
      : (r.busy
        ? `⏳ ${escapeHtml(err)}\n\nID: ${ctx.projectId}`
        : `❌ Не смогла запустить чистку: ${escapeHtml(err)}\nМожно прислать ссылку ещё раз.\n\nID: ${ctx.projectId}`),
  }
}];
