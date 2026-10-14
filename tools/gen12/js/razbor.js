// Единая точка разбора всего, что пришло: из Телеграма или изнутри (переход
// к следующему этапу — канвас вызывает сам себя). Дальше никто не лезет в
// сырое сообщение — все берут готовые поля отсюда.
// kind:
//   newStart     — сообщение без ID проекта → предлагаем выбрать канал
//   channelPick  — нажата кнопка выбора канала → создаём проект
//   imgApprove   — кнопка "✅" под вариантом картинки (img|ID|N)
//   finalApprove — финальная кнопка "✅ Согласовано" под сводкой (final|ID)
//   build        — кнопка "🎬 Собрать с этими треками" (build|ID) или слово «собери / пересобери» реплаем на выпуск
//                  (собирает на уже почищенных треках, без новой чистки)
//   oldButton    — кнопка из старой схемы (approve|ID)
//   tracks       — ссылка на треки
//   cleanStatus  — «как чистка?» / «статус»
//   stageStart   — изнутри: этап завершён, начинает следующий
//   message      — обычная реплика по проекту → этапу
const OWNER_CHAT = 285577543;   // владелец бота (тот же, что в «Это владелец бота?»)
let t = null;
try { t = $('Telegram Trigger').first().json; } catch (e) { t = null; }
// Из календаря (страница-контент-план): «Старт» выпуска или ссылка на треки
let cal = null;
if (!t) { try { cal = $('Из календаря').first().json; } catch (e) { cal = null; } }
if (cal) {
  const b = cal.body || {};
  const chatId = Number(b.chatId) || OWNER_CHAT;
  const none = { chatId, text: '', photo: null, callbackQueryId: '', variantNumber: null, tracksUrl: '', replyVariant: null, event: '', projectId: '', channelKey: '' };
  if (b.action === 'start' && /^[a-z0-9]+$/i.test(String(b.channel || ''))) {
    return [{ json: { ...none, kind: 'channelPick', channelKey: String(b.channel).toLowerCase(),
      cal: { id: String(b.calId || ''), title: String(b.title || '').slice(0, 120), about: String(b.about || '').slice(0, 600),
             release: String(b.release || ''), icon: String(b.icon || '') } } }];
  }
  const cm = String(b.projectId || '').match(/^(\d{8})_(\d{6})_([A-Za-z0-9]+)$/);
  let url = String(b.url || '').trim();
  if (b.action === 'tracks' && cm && /^https?:\/\//.test(url)) {
    const dm = url.match(/\/d\/([a-zA-Z0-9_-]+)/) || url.match(/[?&]id=([a-zA-Z0-9_-]+)/);
    if (dm) url = 'https://drive.google.com/uc?export=download&id=' + dm[1];
    return [{ json: { ...none, kind: 'tracks', projectId: cm[0], channelKey: cm[3], tracksUrl: url } }];
  }
  return [{ json: { ...none, kind: 'unknown' } }];
}
if (!t) {
  const inner = $('Вызов изнутри').first().json || {};
  return [{ json: {
    kind: 'stageStart', chatId: inner.chatId, projectId: inner.projectId, channelKey: inner.channelKey,
    event: inner.event || '', text: '', photo: null, callbackQueryId: '', variantNumber: null, tracksUrl: '', replyVariant: null,
  } }];
}
// Телеграм присылает то же сообщение повторно, если бот долго отвечал (13.10 — вторая чистка).
// Уже виденное update_id — молча пропускаем.
if (t.update_id != null && typeof $getWorkflowStaticData === 'function') {
  const sd = $getWorkflowStaticData('global');
  const seen = Array.isArray(sd.seenUpdates) ? sd.seenUpdates : [];
  if (seen.includes(t.update_id)) return [{ json: { kind: 'unknown', duplicate: true, chatId: null, text: '', photo: null, projectId: '', channelKey: '', callbackQueryId: '', variantNumber: null, tracksUrl: '', replyVariant: null, event: '' } }];
  seen.push(t.update_id);
  sd.seenUpdates = seen.slice(-300);
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

const msg = { ...(t.message || {}) };
// Новый формат Telegram (rich_message): текст и фото лежат в блоках — разворачиваем в обычные поля
if (msg.rich_message && Array.isArray(msg.rich_message.blocks)) {
  const blocks = msg.rich_message.blocks;
  const txt = blocks.filter(b => b && typeof b.text === 'string').map(b => b.text).join('\n\n').trim();
  const ph = blocks.find(b => b && Array.isArray(b.photo) && b.photo.length);
  if (!msg.text && !msg.caption && txt) msg.caption = txt;
  if (!msg.photo && ph) msg.photo = ph.photo;
}
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

// Сборка на уже почищенных треках: слово «пересобери / собери» или текст кнопки,
// набранный руками («🎬 Собрать с этими треками», «собери видео»). Иначе фраза уходила
// этапу как реплика, и сборка молча не начиналась (10.10).
const BUILD_RE = /^\s*(?:🎬\uFE0F?\s*)?(?:пересобер|собер|пересобра|собра)[а-яё]*(?:\s+(?:(?:с\s+)?(?:эти(?:ми)?|те(?:ми)?\s+же|чисты(?:ми)?)\s+трек[а-яё]*|видео|выпуск|ролик|заново))?\s*[.!]*\s*$/iu;

return [{
  json: {
    kind: tracksUrl ? 'tracks' : (/^\s*(как\s+(там\s+)?чистка|статус)(?![а-яё])/iu.test(userText) ? 'cleanStatus'
      : (BUILD_RE.test(userText) ? 'build' : 'message')),
    chatId,
    ...fromId(m),
    text: userText,
    // картинка, отправленная файлом (без сжатия), — тоже картинка
    photo: msg.photo || (msg.document && /^image\//.test(msg.document.mime_type || '') ? [{ file_id: msg.document.file_id }] : null),
    callbackQueryId: '',
    variantNumber: null,
    // ответ на картинку «Вариант N» — какой вариант имеется в виду
    replyVariant: (() => { const r = msg.reply_to_message; const mm = r && String(r.caption || r.text || '').match(/Вариант\s+(\d+)/); return mm ? Number(mm[1]) : null; })(),
    tracksUrl,
    // начало сообщения, на которое автор ответила (reply): по значку и имени в начале понятно, к какому этапу оно относится
    replyText: msg.reply_to_message ? String(msg.reply_to_message.text || msg.reply_to_message.caption || '').slice(0, 300) : '',
    event: '',
  }
}];
