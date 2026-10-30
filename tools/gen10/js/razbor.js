// Единая точка разбора всего, что пришло из Телеграма. Дальше по канвасу
// никто не лезет в сырое сообщение — все берут готовые поля отсюда.
// kind:
//   newStart     — сообщение без ID проекта → предлагаем выбрать канал
//   channelPick  — нажата кнопка выбора канала → создаём проект
//   imgApprove   — кнопка "✅" под конкретным вариантом картинки (img|ID|N)
//   finalApprove — финальная кнопка "✅ Согласовано" под сводкой (final|ID)
//   build        — кнопка "🎬 Собрать с этими треками" (build|ID)
//   oldButton    — кнопка из старой схемы (approve|ID)
//   tracks       — сообщение по проекту со ссылкой (ссылка на треки)
//   message      — обычная реплика по проекту → Редактору
const t = $('Telegram Trigger').first().json;
const ID_RE = /(\d{8})_?(\d{6})_?([A-Za-z0-9]+)/;

function fromId(m) {
  return { projectId: m[1] + '_' + m[2] + '_' + m[3], channelKey: m[3] };
}

if (t.callback_query) {
  const cb = t.callback_query;
  const data = String(cb.data || '').trim();
  const base = {
    chatId: cb.message && cb.message.chat ? cb.message.chat.id : (cb.from ? cb.from.id : null),
    callbackQueryId: cb.id,
    text: '',
    photo: null,
    projectId: '',
    channelKey: '',
    variantNumber: null,
    tracksUrl: '',
  };
  const parts = data.split('|');
  const idMatch = parts[1] ? parts[1].match(ID_RE) : null;

  if (parts[0] === 'img' && idMatch) {
    return [{ json: { ...base, ...fromId(idMatch), kind: 'imgApprove', variantNumber: parseInt(parts[2], 10) || null } }];
  }
  if (parts[0] === 'final' && idMatch) {
    return [{ json: { ...base, ...fromId(idMatch), kind: 'finalApprove' } }];
  }
  if (parts[0] === 'build' && idMatch) {
    return [{ json: { ...base, ...fromId(idMatch), kind: 'build' } }];
  }
  if (parts[0] === 'approve' && idMatch) {
    return [{ json: { ...base, ...fromId(idMatch), kind: 'oldButton' } }];
  }
  if (!data.includes('|') && data) {
    return [{ json: { ...base, kind: 'channelPick', channelKey: data } }];
  }
  return [{ json: { ...base, kind: 'unknown' } }];
}

const msg = t.message || {};
const ownText = msg.text || msg.caption || '';
let search = ownText;
if (msg.reply_to_message) {
  search += ' ' + (msg.reply_to_message.text || msg.reply_to_message.caption || '');
}
const m = search.match(ID_RE);
const chatId = msg.chat ? msg.chat.id : null;

if (!m) {
  return [{ json: { kind: 'newStart', chatId, text: ownText, photo: null, projectId: '', channelKey: '', callbackQueryId: '', variantNumber: null, tracksUrl: '' } }];
}

let userText = ownText;
if (userText.includes(m[0])) {
  userText = userText.replace(m[0], '').replace(/ID\s*:?/gi, '').trim();
}

// Любая ссылка в сообщении по проекту — это ссылка на треки (так было и в
// старой схеме). Картинки для Редактора присылаются фотографией, не ссылкой.
// Задание художнику может содержать ссылку — это не треки.
const toArtist = /^\s*художнику(?![а-яё])/iu.test(userText);
const urlMatch = toArtist ? null : userText.match(/https?:\/\/\S+/);
let tracksUrl = '';
if (urlMatch) {
  tracksUrl = urlMatch[0];
  // Тот же перевод ссылки Google Drive в прямую, что делает 04_Video.
  const driveMatch = tracksUrl.match(/\/d\/([a-zA-Z0-9_-]+)/) || tracksUrl.match(/[?&]id=([a-zA-Z0-9_-]+)/);
  if (driveMatch) {
    tracksUrl = 'https://drive.google.com/uc?export=download&id=' + driveMatch[1];
  }
}

return [{
  json: {
    // «как чистка?» / «статус» — вопрос о чистке звука этого выпуска
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
  }
}];
