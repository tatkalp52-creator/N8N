// Что сказать автору о сбое: первый раз — ничего; второй — «сама повторю»; всё — коротко и что делать.
const f = $('Разбираем сбой').first().json;
const r = $input.first().json || {};
const h = f.human || {};
const q = f.quote ? ' ' + f.quote : '';
let text = '';
if (r.notify === 'fatal') text = `${h.what}${q}\n${h.todo ? 'Что делать: ' + h.todo + '\n' : ''}Как починится — пришли это сообщение ещё раз.\n(${h.raw})`;
else if (r.notify === 'slow') text = `⏳ ${h.what.replace(/^\S+\s/, '')} Повторю сама${q}, ничего не пиши.`;
else if (r.notify === 'final') text = `⚠️ Не получилось за 15 минут${q}: ${h.what}\nКак починится — пришли его ещё раз.\n(${h.raw})`;
return [{ json: { say: !!text && !!f.chatId, chatId: f.chatId, text, next: r.next || null } }];
