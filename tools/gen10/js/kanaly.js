// Новый заход без ID проекта: по сообщению с кнопкой на каждый канал из каталога.
const chatId = $('Разбираем входящее').first().json.chatId;
return items
  .map(i => String(i.json.Channel || '').trim())
  .filter(Boolean)
  .map(channel => ({ json: { chatId, channel, text: `Новый проект в канале <b>${escapeHtml(channel)}</b>?` } }));
