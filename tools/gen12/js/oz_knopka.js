// (29.10) «оживление» реплаем на выпуск → кнопка, которая открывает приложение разметки прямо в Телеграме.
// Приложение отдаёт сам n8n (https), строки возвращаются тем же входом, что и календарь.
const ctx = $('Контекст проекта').first().json;
const base = String($env.WEBHOOK_URL || '').replace(/\/+$/, '');
const img = String((ctx.row || {}).ai_ApprovedImageUrl || '').trim();
let text, markup = null;
if (!base) {
  text = '⚙️ На сервере n8n не задан WEBHOOK_URL — приложению не на что открыться.';
} else if (!img) {
  text = 'Картинка выпуска ещё не согласована — оживлять пока нечего.';
} else {
  const q = new URLSearchParams({ f: 'ozhivlenie.html', p: ctx.projectId, ch: ctx.channelKey,
    img: toDirectImageUrl(img), submit: base + '/webhook/' + CAL_HOOK });
  text = ctx.labelLine + 'Разметка оживления — откройте и отметьте, что оживить. Готовые строки придут в пункт оживления выпуска.';
  markup = { inline_keyboard: [[{ text: '✨ Оживление', web_app: { url: base + '/webhook/' + OZH_HOOK + '?' + q.toString() } }]] };
}
return [{ json: { body: { chat_id: ctx.chatId, text, parse_mode: 'HTML', ...(markup ? { reply_markup: markup } : {}) } } }];
