// «Работа» упала. Повтор поможет (сеть, занятость) — очередь повторит сама через 5 / 15 / 30 минут.
// Не поможет (деньги, ключ, вход) — сказать сразу.
const job = $('В работу').first().json;
const e = $input.first().json || {};
const raw = [e.error && (e.error.message || e.error), e.message, e.error && e.error.description].filter(Boolean).join(' — ') || JSON.stringify(e).slice(0, 300);
const h = failHuman(raw);
return [{ json: { op: 'fail', key: job.key, fatal: h.fatal, error: h.raw, chatId: job.chatId, quote: job.quote, human: h } }];
