// Сюда приходят два пути: обычная реплика автора и нажатие "✅" под
// вариантом картинки (тогда Редактору уходит служебная фраза о кнопке).
const ctx = $('Контекст проекта').first().json;
let synthetic = '';
let btn = null;
try { btn = $('Согласуем вариант').first().json; synthetic = btn.syntheticText || ''; } catch (e) {}
// После кнопки строка проекта, прочитанная в начале, уже устарела: статус и
// согласованная картинка только что записаны — берём свежие значения.
const status = btn && btn.ok ? btn.statusAfter : ctx.status;
const approvedUrl = btn && btn.ok ? btn.approvedUrl : String((ctx.row || {}).ai_ApprovedImageUrl || '').trim();

const photo = synthetic ? null : (ctx.photo && ctx.photo.length ? ctx.photo : null);
let userText = synthetic || ctx.text || '';
if (!userText.trim()) userText = photo ? '(фото без подписи)' : '(пустое сообщение)';

// «Художнику: …» — задание уходит художнику напрямую, без Редактора.
// «Художнику правка: …» / «Художнику правка 3: …» — правка последнего / 3-го варианта.
let directArt = null;
const SEP = '[\\s:,.!—–-]*';
const m = synthetic ? null : String(ctx.text || '').match(new RegExp('^\\s*художнику(?![а-яё])' + SEP, 'iu'));
if (m) {
  let rest = String(ctx.text).slice(m[0].length);
  const e = rest.match(new RegExp('^правк[аиу](?![а-яё])(?:\\s*(?:вариант[а]?|№)?\\s*(\\d+))?' + SEP, 'iu'));
  let edit = false, variant = null;
  if (e) { edit = true; variant = e[1] ? Number(e[1]) : null; rest = rest.slice(e[0].length); }
  directArt = { edit, variant, text: rest.trim() };
}

return [{
  json: {
    projectId: ctx.projectId,
    chatId: ctx.chatId,
    sheetName: ctx.sheetName,
    channelKey: ctx.channelKey,
    userText,
    photo,
    fromButton: !!synthetic,
    status,
    approvedUrl,
    directArt,
  }
}];
