// Раз в 5 минут: очередь отдаёт, что пора повторить (упало или зависло), и что не получилось за час.
const r = $input.first().json || {};
const out = [];
for (const it of r.run || []) out.push({ json: { resume: it } });
for (const it of r.final || []) {
  if (!it.chatId) continue;
  out.push({ json: { final: true, chatId: it.chatId, text: `⚠️ Не получилось за час ${inboxQuote(it)}: ${failHuman(it.error).what}\nКак починится — пришли его ещё раз.` } });
}
return out;
