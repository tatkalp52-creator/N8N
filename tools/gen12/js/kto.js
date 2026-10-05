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
const stage = addressed ? addressed.stage : (byItem || current || (isStart ? null : lastAuthor));
let userText = addressed ? addressed.rest : String(ctx.text || '');
const photo = ctx.photo && ctx.photo.length ? ctx.photo : null;
if (!userText.trim()) userText = photo ? '(фото без подписи)' : '';

let mode = 'none';
let sayText = '';
let silent = false;
if (ctx.setupProblem) {
  mode = 'say'; sayText = ctx.setupProblem;
} else if (!stage) {
  mode = 'done'; // все этапы завершены — дальше сводка / запись
} else if (stage.picture && !stage.items.length) {
  // Художник: сообщение автора — это задание. Ответ на картинку или «правка …» — правка.
  if (isStart) {
    if (stage.talks === 'author' || !String(row.ai_UserBrief || '').trim()) {
      mode = 'say';
      sayText = `${stage.icon} ${stage.name}: жду задание — опишите, что на картинке.`;
    } else {
      mode = 'draw'; userText = String(row.ai_UserBrief || ''); silent = true;
    }
  } else if (!userText.trim()) {
    mode = 'say'; sayText = `${stage.icon} ${stage.name}: напишите задание словами.`;
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

const editVariant = (() => {
  const e = String(ctx.text || '').match(/правк[аиу]\s*(?:вариант[а]?|№)?\s*(\d+)/iu);
  return e ? Number(e[1]) : (ctx.replyVariant || null);
})();

// диспетчер: чистое одобрение автора отмечаем сами (модель на этом ходу может выбрать другой инструмент)
const approveNums = mode === 'model' && !isStart && stage ? stApproval(userText, stScope(stages, stage).items, state) : [];

return [{
  json: {
    mode,
    approveNums,
    stageIcon: stage ? stage.icon : '',
    stageName: stage ? stage.name : '',
    userText,
    photo: mode === 'model' ? photo : null,
    isStart,
    event: ctx.event || '',
    silent,
    sayText,
    editVariant,
    fromAuthor: !isStart,
    // фото этапу, чей пункт показывается превью «оживление», — это разметка: её читает сборщик
    needMarks: mode === 'model' && !!photo && !!approvedUrl && !!stage &&
      items.some(it => stScope(stages, stage).items.includes(it.n) && /оживл/.test(it.preview || '')),
    // правка картинки с фото автора: красная обводка на фото = где можно менять (маска сборщика)
    needMask: mode === 'edit' && !!photo,
    maskPhoto: mode === 'edit' ? photo : null,
    needGrid: mode === 'model' && !!(stage && stage.grid) && !!approvedUrl,
    needConv: mode === 'model' && !silent && !String((state.stages[bareIcon(stage ? stage.icon : '')] || {}).conv || '').trim(),
  }
}];
