// Кто отвечает на это сообщение — решает таблица (лист «Этапы»), не код.
// Текущий этап — первый по порядку незавершённый (не подчинённый).
// Обращение «✍️ …» / «Писателю: …» — к названному этапу напрямую.
const ctx = $('Контекст проекта').first().json;
const row = ctx.row || {};
const stages = ctx.stages || [];
const items = ctx.items || [];
const state = stParseState(row.sys_EditorState);
const approvedUrl = String(row.ai_ApprovedImageUrl || '').trim();
const isStart = ctx.kind === 'stageStart';

const addressed = isStart ? null : stAddressed(stages, ctx.text);
const current = stCurrent(stages, items, state, approvedUrl);
// Всё готово, а автор пишет без обращения — отвечает последний этап, который говорит с автором
// словами (у кого есть пункты): художнику без обращения сообщение не уходит — он бы его нарисовал.
const lastAuthor = [...stages].reverse().find(s => s.talks === 'author' && s.items.length) || null;
// «9 …» — к этапу, чей пункт 9 (если это не текущий этап)
const byItem = isStart || addressed ? null : stByItem(stages, ctx.text);
// Ответ (reply) на сообщение этапа — адрес: «согласовано» на сообщение художника относится к художнику.
const replyStage = isStart || addressed || byItem ? null : stByReply(stages, ctx.replyText, ctx.replyVariant);
const stage = addressed ? addressed.stage : (byItem || replyStage || current || (isStart ? null : lastAuthor));
let userText = addressed ? addressed.rest : String(ctx.text || '');
const photo = ctx.photo && ctx.photo.length ? ctx.photo : null;
const ownWords = userText.trim();
if (!userText.trim()) userText = photo ? '(фото без подписи)' : '';
// (23.10) Обводка без подписи (с планшета подпись не всегда добавишь): не рисуем вслепую, а запоминаем
// обводку и ждём слова следующим сообщением — тогда это одна правка. Обводка живёт 30 минут.
const stKey = stage ? bareIcon(stage.icon) : '';
const pendingMarks = (() => {
  const m = stKey && state.stages[stKey] ? state.stages[stKey].marks : null;
  return m && m.photo && Date.now() - Number(m.at || 0) < 30 * 60 * 1000 ? m : null;
})();
let marksSave = null;
let marksClear = false;
let markPhoto = null;
let markVariant = null;

let mode = 'none';
let sayText = '';
let silent = false;
const resetAsked = !isStart && stIsReset(addressed ? addressed.rest : ctx.text);
const resetTarget = addressed ? addressed.stage : stByReply(stages, ctx.replyText, ctx.replyVariant);
if (ctx.setupProblem) {
  mode = 'say'; sayText = ctx.setupProblem;
} else if (resetAsked) {
  if (resetTarget) mode = 'reset';
  else { mode = 'say'; sayText = 'С какого этапа начать заново? Ответьте словом «заново» на сообщение нужного этапа или напишите, например, «✍️ заново».'; }
} else if (!stage) {
  mode = 'done'; // все этапы завершены — дальше сводка / запись
} else if (stage.picture && !stage.items.length) {
  // Художник: сообщение автора — это задание. Ответ на картинку или «правка …» — правка.
  if (isStart) {
    // (23.10) задание уже пришло (обогнало запуск этапа) — молчим, не просим его ещё раз
    if (stage.talks === 'author' && String(row.ai_UserBrief || '').trim()) {
      mode = 'none';
    } else if (stage.talks === 'author' || !String(row.ai_UserBrief || '').trim()) {
      mode = 'say';
      sayText = `${stage.icon} ${stage.name}: жду задание — опишите, что на картинке.`;
    } else {
      mode = 'draw'; userText = String(row.ai_UserBrief || ''); silent = true;
    }
  } else if (photo && !ownWords) {
    mode = 'say';
    sayText = `${stage.icon} ${stage.name}: вижу обводку. Что сделать в обведённых местах? Напишите следующим сообщением — поправлю по этой обводке.`;
    marksSave = { photo, variant: ctx.replyVariant || null, at: Date.now() };
  } else if (!userText.trim()) {
    mode = 'say'; sayText = `${stage.icon} ${stage.name}: напишите задание словами.`;
  } else if (!photo && pendingMarks) {
    // слова к обводке, присланной перед этим
    mode = 'edit';
    const e = userText.match(/^\s*правк[аиу](?![а-яё])(?:\s*по\s+разметке)?[\s:,.!—–-]*/iu);
    if (e) userText = userText.slice(e[0].length);
    markPhoto = pendingMarks.photo;
    markVariant = pendingMarks.variant;
    marksClear = true;
  } else {
    const e = userText.match(/^\s*правк[аиу](?![а-яё])(?:\s*(?:вариант[а]?|№)?\s*(\d+))?[\s:,.!—–-]*/iu);
    if (e || ctx.replyVariant) {
      mode = 'edit';
      if (e) userText = userText.slice(e[0].length);
    } else mode = 'draw';
  }
} else {
  mode = 'model';
  silent = stage.talks !== 'author' && !addressed;
}

// (22.10) «Пункт N, запиши ровно так / добавь / убери» — готовый текст автора: пишет код, модель не нужна
// (не тратит деньги и не ломается). Согласовано сразу — это её собственные строки.
// (23.10) Свою готовую строку («Пункт 9, добавь: …» со странички) автор шлёт в любой момент — и пока идёт
// любой этап, и когда все этапы уже прошли. Пункт без этапа в «Этапы» — пункт автора: только так и пишется.
// (29.10) строки из приложения «Оживление» — готовый текст автора для пункта с превью оживления
if (ctx.fxApp) {
  const fxItem = items.find(it => /оживл/.test(it.preview || ''));
  if (fxItem) userText = `Пункт ${fxItem.n}, ${ctx.fxApp.mode === 'add' ? 'добавь' : 'перепиши целиком'}:\n${ctx.fxApp.lines}`;
}
const directAllowed = !isStart && !photo && !ctx.setupProblem && !resetAsked && ['model', 'done', 'draw', 'edit'].includes(mode);
const direct = directAllowed ? itDirectCommand(userText, items, row, state) : null;
if (direct && direct.drops && direct.drops.length) {
  mode = 'say';
  sayText = `${stage ? stage.icon + ' ' + stage.name : '📋'}: ничего не записала — этот текст убрал бы из пункта ${direct.n} строки:\n`
    + direct.drops.join('\n')
    + `\n\nДописать новое к тому, что есть: «Пункт ${direct.n}, добавь: …». Убрать строку: «Пункт ${direct.n}, убери: пар». `
    + `Переписать пункт целиком, без этих строк: «Пункт ${direct.n}, перепиши целиком: …».`;
} else if (direct) { mode = 'direct'; silent = false; }
// (29.10) строки из приложения не теряются молча: не нашёлся пункт или не записались — автор видит почему и сами строки
if (ctx.fxApp && mode !== 'direct') {
  const fxItem = items.find(it => /оживл/.test(it.preview || ''));
  mode = 'say'; silent = false;
  sayText = '✨ Оживление не записано — ' + (fxItem ? `пункт ${fxItem.n} сейчас не принимает строки.` : 'Таблица: в листе «Пункты» нет пункта с «Превью: оживление».')
    + ' Строки целы — вот они, их можно переслать боту «Пункт N, перепиши целиком: …»:\n' + ctx.fxApp.lines;
}
// (23.10) этап без модели («Модель: нет» в листе «Этапы») — OpenAI не зовём, просим готовый текст
if (mode === 'model' && stage && stage.noModel) {
  const nums = stScope(stages, stage).items.join(', ');
  mode = 'say'; silent = false;
  sayText = isStart
    ? `${stage.icon} ${stage.name}: жду пункт ${nums} — пришлите готовый текст («Пункт ${nums}, добавь: …» со странички).`
    : `${stage.icon} ${stage.name}: я работаю без модели — пришлите готовый текст: «Пункт ${nums}, добавь: …», «убери: …» или «запиши ровно так: …».`;
}

const editVariant = (() => {
  const e = String(ctx.text || '').match(/правк[аиу]\s*(?:вариант[а]?|№)?\s*(\d+)/iu);
  return e ? Number(e[1]) : (markVariant || ctx.replyVariant || null);
})();

// диспетчер: чистое одобрение автора отмечаем сами (модель на этом ходу может выбрать другой инструмент)
const approveNums = mode === 'model' && !isStart && stage ? stApproval(userText, stScope(stages, stage).items, state) : [];

return [{
  json: {
    mode,
    approveNums,
    stageIcon: mode === 'reset' ? resetTarget.icon : (stage ? stage.icon : ''),
    stageName: mode === 'reset' ? resetTarget.name : (stage ? stage.name : ''),
    userText,
    photo: mode === 'model' ? photo : null,
    isStart,
    event: ctx.event || '',
    silent,
    sayText,
    editVariant,
    directN: direct ? direct.n : null,
    directText: direct ? direct.text : '',
    fromAuthor: !isStart,
    fxApp: !!ctx.fxApp,
    // фото этапу, чей пункт показывается превью «оживление», — это разметка: её читает сборщик
    needMarks: mode === 'model' && !!photo && !!approvedUrl && !!stage &&
      items.some(it => stScope(stages, stage).items.includes(it.n) && /оживл/.test(it.preview || '')),
    // правка картинки с фото автора: красная обводка на фото = где можно менять (маска сборщика)
    needMask: mode === 'edit' && !!(photo || markPhoto),
    maskPhoto: mode === 'edit' ? (photo || markPhoto) : null,
    marksSave,
    marksClear,
    needGrid: mode === 'model' && !!(stage && stage.grid) && !!approvedUrl,
  }
}];
