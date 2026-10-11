// Запрос к этапу (любому: писатель, технический, редактор…). Кто он, что знает
// и что делает — из таблицы: лист «Этапы», лист «Пункты», колонки Templates с его значком.
const ctx = $('Контекст проекта').first().json;
const plan = $('Кто отвечает').first().json;
const row = ctx.row || {};
const stages = ctx.stages || [];
const items = ctx.items || [];
const stage = stages.find(s => bareIcon(s.icon) === bareIcon(plan.stageIcon));
if (!stage) throw new Error('Этап ' + plan.stageIcon + ' не найден в листе «Этапы»');
const state = stParseState(row.sys_EditorState);
stApplyApproval(state, plan.approveNums);   // карточка уже показывает согласование автора
const sc = stScope(stages, stage);
const st = stStage(state, stage.icon);
const approvedUrl = String(row.ai_ApprovedImageUrl || '').trim();
const brief = String(row.ai_UserBrief || '').trim();

// Разговор этапа: свой у каждого этапа (чистая голова). Молчаливый этап — без разговора.
let conversationId = '';
let isNew = false;
if (!plan.silent) {
  conversationId = String(st.conv || '').trim();
  if (!conversationId) {
    try { conversationId = $('OpenAI: создаём разговор').first().json.id; isNew = true; } catch (e) {}
  }
  if (!conversationId) throw new Error('Нет разговора для этапа ' + stage.name);
}
const pendingCallId = plan.silent || isNew ? '' : String(st.pending || '').trim();

let userImageUrl = '';
try { userImageUrl = $('Фото в base64').first().json.userImageUrl || ''; } catch (e) {}

const kb = kbForStage(ctx.tmpl, stage.icon, [plan.userText, brief].join(' '));

// ── Картинки: каждая показывается этапу один раз и дальше живёт в истории разговора ──
let variants = [];
try { variants = JSON.parse(row.ai_ImageVariants || '[]'); } catch (e) { variants = []; }
if (!Array.isArray(variants)) variants = [];
const seen = new Set(plan.silent ? [] : st.seen);
const images = [];
// key — что помнить в состоянии (картинку с сеткой помним по метке, а не по её огромным данным)
const addImage = (url, label, key) => { const k = key || url; if (url && !seen.has(k)) { images.push({ url, label }); seen.add(k); } };
let gridUrl = '';
try { gridUrl = ($('Сервер: сетка').first().json || {}).dataUrl || ''; } catch (e) {}
if (gridUrl && approvedUrl) addImage(gridUrl, 'согласованная картинка выпуска с сеткой процентов: синие подписи — проценты слева направо, красные — сверху вниз', 'grid:' + approvedUrl);
else if (approvedUrl) addImage(approvedUrl, 'согласованная картинка выпуска');
if (sc.picture) variants.forEach(v => addImage(v.url, 'вариант ' + v.n + ' этого выпуска'));

// ── Карточка выпуска ──
const who = n => { const s = stages.find(x => x.items.includes(n)); return s ? s.name : '—'; };
const itemLines = items.map(it => {
  const status = state.agreed[it.n] ? 'СОГЛАСОВАНО' : (it.n in state.items ? 'предложено, ждёт согласования' : 'ещё не предлагалось');
  const mine = sc.items.includes(it.n) ? 'твой пункт' : 'делает ' + who(it.n);
  const text = itShow(state, it, true);
  return `  ${it.n}. ${it.name} [${status}; ${mine}]` + (text ? '\n' + text.split('\n').map(l => '     ' + l).join('\n') : '');
}).join('\n');
const stageLines = stages.map(s => `  ${s.icon} ${s.name}: ${stComplete(stages, items, state, approvedUrl, s) ? 'готово' : 'в работе'}`).join('\n');
const card = [
  `Выпуск ${ctx.projectId}.`,
  brief ? `Бриф автора: ${brief}` : '',
  `Картинка: ${approvedUrl ? 'согласована' : 'ещё не согласована'}${variants.length ? `; вариантов: ${variants.length}` : ''}.`,
  'Этапы:', stageLines,
  'Пункты:', itemLines || '  (лист «Пункты» пуст)',
].filter(Boolean).join('\n');

const myItems = items.filter(it => sc.items.includes(it.n));
const previewStage = myItems.some(it => it.preview);
const itemsSpec = myItems.map(it => `  ${it.n}. ${it.name}${it.hint ? ' — ' + it.hint : ''}${it.canEmpty ? ' (можно оставить пустым: "-")' : ''}`).join('\n');
const subs = sc.subs;
const talk = plan.silent
  ? 'Ты работаешь молча, по заданию: сразу вызови propose_items со своими пунктами.'
  : 'Ты говоришь с автором напрямую.';

const tools = [{ type: 'web_search' }];
const toolLines = [];
if (myItems.length) {
  tools.push({
    type: 'function', name: 'propose_items',
    description: 'Предложить или изменить свои пункты и/или отметить пункты, которые автор явно согласовала.',
    parameters: { type: 'object', properties: {
      items: { type: 'array', description: 'Только пункты, которые предлагаешь или меняешь сейчас', items: { type: 'object', properties: {
        n: { type: 'integer', description: 'Номер пункта' },
        text: { type: 'string', description: 'Текст пункта — ровно то, что уйдёт в таблицу; "-" если пункт не нужен' },
      }, required: ['n', 'text'] } },
      agreed: { type: 'array', items: { type: 'integer' }, description: 'Номера пунктов, которые автор ЯВНО одобрила' },
      reopen: { type: 'array', items: { type: 'integer' }, description: 'Номера согласованных пунктов, которые автор решила пересмотреть' },
      message: { type: 'string', description: 'Реплика автору (пункты система покажет сама)' },
    }, required: ['message'] },
  });
  toolLines.push('- propose_items — предложить/изменить свои пункты и отметить согласованные автором (agreed — только то, что она явно одобрила; «всё ок» — все показанные). Система сама покажет автору пункты, ждущие согласования; в message их не переписывай. Изменённый пункт снова ждёт согласования.');
}
if (kb.notesKey && !plan.silent) {
  tools.push({
    type: 'function', name: 'save_note',
    description: 'Сохранить твою памятку (колонка таблицы, её видишь только ты и в следующих выпусках).',
    parameters: { type: 'object', properties: {
      notes: { type: 'string', description: 'ПОЛНЫЙ текст памятки: прежняя + новое' },
      message: { type: 'string', description: 'Реплика автору' },
    }, required: ['notes', 'message'] },
  });
  toolLines.push('- save_note — записать в твою памятку то, что стоит помнить в следующих выпусках (замечания автора, её вкус). Передавай полный текст.');
}
if (subs.length && !plan.silent) {
  tools.push({
    type: 'function', name: 'delegate',
    description: 'Поручить работу этапу, который работает по твоему заданию.',
    parameters: { type: 'object', properties: {
      stage: { type: 'string', enum: subs.map(s => s.name), description: 'Кому поручаешь' },
      task: { type: 'string', description: 'Задание: что сделать' },
      variant: { type: 'integer', description: 'Для правки картинки: номер варианта, который правим' },
      edit: { type: 'boolean', description: 'Для картинки: true — правка уже нарисованного варианта' },
      message: { type: 'string', description: 'Реплика автору' },
    }, required: ['stage', 'task', 'message'] },
  });
  toolLines.push('- delegate — поручить работу: ' + subs.map(s => `${s.icon} ${s.name} (${s.picture ? 'картинка' : 'пункты ' + s.items.join(', ')})`).join('; ') + '. Он получает только твоё задание и свои знания из таблицы.');
}
if (sc.picture && !stage.picture && !plan.silent) {
  tools.push({
    type: 'function', name: 'approve_image',
    description: 'Автор согласовала картинку словами.',
    parameters: { type: 'object', properties: {
      variant: { type: 'integer', description: 'Номер согласованного варианта' },
      message: { type: 'string', description: 'Реплика автору' },
    }, required: ['message'] },
  });
  toolLines.push('- approve_image — автор согласовала картинку словами (номер варианта, если их несколько).');
}

const instructions = `Ты — ${stage.icon} ${stage.name} канала "${ctx.sheetName}". ${talk}
Кто ты, как говоришь и что делаешь — в твоих знаниях из таблицы канала ниже. Здесь — только то, как устроена система.

ТВОИ ПУНКТЫ В ЭТОМ ВЫПУСКЕ
${itemsSpec || '  (своих пунктов нет)'}

ИНСТРУМЕНТЫ. За один ответ — не больше одного; если ничего не нужно — просто отвечай текстом.
${toolLines.join('\n')}
Когда все твои пункты согласованы, твой этап завершён — система сама передаст выпуск дальше.
Если по смыслу твоих слов что-то предложено, согласовано или изменено, а инструмент не вызван — вызови его в этом же ответе.

ТВОИ ЗНАНИЯ ИЗ ТАБЛИЦЫ КАНАЛА:
${kb.text || '(пусто — в Templates нет колонок с твоим значком)'}
${/эффект/i.test(stage.ref || '') && (ctx.effects || []).length ? `
КАТАЛОГ ЭФФЕКТОВ (лист «Эффекты» таблицы). Предлагай только эффекты со статусом «готов» (или «в работе», предупредив автора), которые используются на этом канале. Ручки — шкала 1–10: 5 — как обычно на канале, 1 — вдвое слабее, 10 — вдвое сильнее. Обычные значения канала сборщик возьмёт сам; в строку выпуска дописывай ручку, только если автор попросила иначе для этого выпуска: «пар: область …; густота 7».
${fxCatalogText(ctx.effects)}
` : ''}
КАРТОЧКА ВЫПУСКА (актуальна на этот ход; если расходится с тем, что ты помнишь, — верь карточке):
${card}`;

// ── Сообщение ──
const text = plan.isStart
  ? `[Служебное сообщение] ${plan.event || 'Предыдущий этап завершён.'} Сейчас твой этап — начни по своим правилам.`
  : (plan.userText || '(пустое сообщение)') + ((plan.approveNums || []).length
    ? `\n\n[Система: пункты ${plan.approveNums.join(', ')} уже отмечены согласованными. Если все твои пункты согласованы, этап завершён и выпуск идёт дальше — просто коротко попрощайся или сохрани памятку.]`
    : '');
let marksText = '';
try { marksText = ($('Сервер: разметка').first().json || {}).text || ''; } catch (e) {}
const content = [{ type: 'input_text', text: text + (marksText
  ? '\n\n[Разметка автора — красные штрихи на её картинке, слева направо; числа — проценты кадра, прочитаны точно]\n' + marksText
  : '') }];
if (userImageUrl) {
  content.push({ type: 'input_text', text: '(Фото, которое автор прислала в этом сообщении:)' });
  content.push({ type: 'input_image', image_url: userImageUrl });
}
for (const img of images) {
  content.push({ type: 'input_text', text: `(Служебно: ${img.label})` });
  content.push({ type: 'input_image', image_url: img.url });
}
const input = [];
if (pendingCallId) input.push({ type: 'function_call_output', call_id: pendingCallId, output: 'Выполнено. Актуальный результат — в карточке выпуска.' });
input.push({ role: 'user', content: content.length > 1 ? content : text });

const requestBody = {
  model: stage.model || 'gpt-5',
  instructions,
  input,
  tools,
  // молчаливый этап и разметка автора — это всегда работа над пунктами: ответ инструментом, тогда придёт и превью
  // пункт с превью (оживление): автор проверяет его глазами — на любое не-одобрение отвечаем строками, тогда придёт видео
  tool_choice: (plan.silent || marksText || (previewStage && !(plan.approveNums || []).length)) && myItems.length
    ? { type: 'function', name: 'propose_items' } : 'auto',
  parallel_tool_calls: false,
  truncation: 'auto',
};
if (conversationId) requestBody.conversation = conversationId;
if (['low', 'medium', 'high'].includes(stage.effort)) requestBody.reasoning = { effort: stage.effort };

return [{ json: { requestBody, conversationId, seen: Array.from(seen), stageIcon: stage.icon } }];
