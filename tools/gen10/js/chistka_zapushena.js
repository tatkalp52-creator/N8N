// Ответ сервера на «запусти чистку».
const ctx = $('Контекст проекта').first().json;
const prep = $('Чистка: нужна?').first().json;
const r = $input.first().json || {};
const ok = !!r.ok && !!r.tag;
const err = r.error || (r.message) || 'сервер не ответил';
// Не запустилась, а в строке уже идёт чистка (повторное нажатие, «блокнот занят») — строку НЕ трогаем:
// иначе идущая чистка теряет свою метку и её результат не забирается (14.10, кот).
const row = ctx.row || {};
const keep = !ok && String(row.sys_CleanState || '').trim() === 'идёт';
return [{
  json: {
    ok,
    // (24.10) «блокнот занят» — строку выпуска не трогаем вовсе (снимок строки мог устареть: идущая чистка
    // могла начаться секунды назад и ещё не видна здесь)
    write: ok || !r.busy,
    tag: ok ? r.tag : (keep ? String(row.sys_CleanTag || '') : ''),
    notebookUrl: r.notebookUrl || prep.body.cleanNotebook,
    state: ok ? 'идёт' : (keep ? 'идёт' : `ошибка: ${err}`),
    started: ok ? new Date().toISOString() : (keep ? String(row.sys_CleanStarted || '') : ''),
    source: ok || !keep ? prep.body.tracksUrl : String(row.sys_CleanSource || prep.body.tracksUrl),
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
