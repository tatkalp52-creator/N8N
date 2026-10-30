// Новый заход без ID проекта: ОДНО сообщение, в нём по кнопке на каждый канал из листа Catalog
// (11.10, автор: «сразу кнопка Пингви, кнопка Luminous…», без строчки «Новый проект в канале …» на каждый).
// Подпись кнопки — колонка «Кнопка» листа Catalog (пусто — ключ канала); нажатие отдаёт ключ канала.
const chatId = $('Разбираем входящее').first().json.chatId;
const rows = items
  .map(i => ({ key: String(i.json.Channel || '').trim(), label: String(i.json['Кнопка'] || '').trim() }))
  .filter(r => r.key);
const body = rows.length
  ? { chat_id: chatId, text: 'Новый проект — какой канал?', reply_markup: { inline_keyboard: rows.map(r => [{ text: r.label || r.key, callback_data: r.key }]) } }
  : { chat_id: chatId, text: 'В листе Catalog нет ни одного канала.' };
return [{ json: { chatId, body } }];
