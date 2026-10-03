// Единая точка разбора всего, что пришло: из Телеграма или изнутри (переход
// к следующему этапу — канвас вызывает сам себя). Дальше никто не лезет в
// сырое сообщение — все берут готовые поля отсюда.
// kind:
//   newStart     — сообщение без ID проекта → предлагаем выбрать канал
//   channelPick  — нажата кнопка выбора канала → создаём проект
//   imgApprove   — кнопка "✅" под вариантом картинки (img|ID|N)
//   finalApprove — финальная кнопка "✅ Согласовано" под сводкой (final|ID)
//   build        — кнопка "🎬 Собрать с этими треками" (build|ID)
//   oldButton    — кнопка из старой схемы (approve|ID)
//   tracks       — ссылка на треки
//   cleanStatus  — «как чистка?» / «статус»
//   stageStart   — изнутри: этап завершён, начинает следующий
//   message      — обычная реплика по проекту → этапу
let t = null;
try { t = $('Telegram Trigger').first().json; } catch (e) { t = null; }
if (!t) {
  const inner = $('Вызов изнутри').first().json || {};
  return [{ json: {
    kind: 'stageStart', chatId: inner.chatId, projectId: inner.projectId, channelKey: inner.channelKey,
    event: inner.event || '', text: '', photo: null, callbackQueryId: '', variantNumber: null, tracksUrl: '', replyVariant: null,
  } }];
}
const ID_RE = /(\d{8})_?(\d{6})_?([A-Za-z0-9]+)/;
const fromId = m => ({ projectId: m[1] + '_' + m[2] + '_' + m[3], channelKey: m[3] });

if (t.callback_query) {
  const cb = t.callback_query;
  const data = String(cb.data || '').trim();
  const base = {
    chatId: cb.message && cb.message.chat ? cb.message.chat.id : (cb.from ? cb.from.id : null),
    callbackQueryId: cb.id, text: '', photo: null, projectId: '', channelKey: '',
    variantNumber: null, tracksUrl: '', replyVariant: null, event: '',
  };
  const parts = data.split('|');
  const idMatch = parts[1] ? parts[1].match(ID_RE) : null;
  if (parts[0] === 'img' && idMatch) return [{ json: { ...base, ...fromId(idMatch), kind: 'imgApprove', variantNumber: parseInt(parts[2], 10) || null } }];
  if (parts[0] === 'final' && idMatch) return [{ json: { ...base, ...fromId(idMatch), kind: 'finalApprove' } }];
  if (parts[0] === 'build' && idMatch) return [{ json: { ...base, ...fromId(idMatch), kind: 'build' } }];
  if (parts[0] === 'approve' && idMatch) return [{ json: { ...base, ...fromId(idMatch), kind: 'oldButton' } }];
  if (!data.includes('|') && data) return [{ json: { ...base, kind: 'channelPick', channelKey: data } }];
  return [{ json: { ...base, kind: 'unknown' } }];
}

const msg = t.message || {};
const ownText = msg.text || msg.caption || '';
let search = ownText;
if (msg.reply_to_message) search += ' ' + (msg.reply_to_message.text || msg.reply_to_message.caption || '');
const m = search.match(ID_RE);
const chatId = msg.chat ? msg.chat.id : null;
if (!m) {
  return [{ json: { kind: 'newStart', chatId, text: ownText, photo: null, projectId: '', channelKey: '', callbackQueryId: '', variantNumber: null, tracksUrl: '', replyVariant: null, event: '' } }];
}

let userText = ownText;
if (userText.includes(m[0])) userText = userText.replace(m[0], '').replace(/ID\s*:?/gi, '').trim();

// Ссылка на треки — сообщение, где кроме ссылки почти ничего нет.
// Задание с ссылкой внутри («нарисуй как здесь https://…») — не треки.
const urlMatch = userText.match(/https?:\/\/\S+/);
let tracksUrl = '';
if (urlMatch && userText.replace(urlMatch[0], '').trim().split(/\s+/).filter(Boolean).length <= 3) {
  tracksUrl = urlMatch[0];
  const driveMatch = tracksUrl.match(/\/d\/([a-zA-Z0-9_-]+)/) || tracksUrl.match(/[?&]id=([a-zA-Z0-9_-]+)/);
  if (driveMatch) tracksUrl = 'https://drive.google.com/uc?export=download&id=' + driveMatch[1];
}

return [{
  json: {
    kind: tracksUrl ? 'tracks' : (/^\s*(как\s+(там\s+)?чистка|статус)(?![а-яё])/iu.test(userText) ? 'cleanStatus' : 'message'),
    chatId,
    ...fromId(m),
    text: userText,
    photo: msg.photo || null,
    callbackQueryId: '',
    variantNumber: null,
    // ответ на картинку «Вариант N» — какой вариант имеется в виду
    replyVariant: (() => { const r = msg.reply_to_message; const mm = r && String(r.caption || r.text || '').match(/Вариант\s+(\d+)/); return mm ? Number(mm[1]) : null; })(),
    tracksUrl,
    event: '',
  }
}];
