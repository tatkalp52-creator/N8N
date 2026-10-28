// Запрос к этапу (любому: писатель, технический, редактор…). Кто он, что знает
// и что делает — из таблицы: лист «Этапы», лист «Пункты», колонки Templates с его значком.
const ctx = $('Контекст проекта').first().json;
const plan = $('Кто отвечает').first().json;
const row = ctx.row || {};
const stages = ctx.stages || [];
const items = ctx.items || [];
const stage = stages.find(s => bareIcon(s.icon) === bareIcon(plan.stageIcon));
if (!stage) throw new Error('Этап ' + plan.stageIcon + ' не найден в листе «Этапы»');
if (!stage.model) throw new Error('Таблица: у этапа ' + stage.name + ' не указана модель (лист «Этапы»)');
const state = stParseState(row.sys_EditorState);
stApplyApproval(state, plan.approveNums);   // карточка уже показывает согласование автора
const sc = stScope(stages, stage);
const st = stStage(state, stage.icon);
const approvedUrl = String(row.ai_ApprovedImageUrl || '').trim();
const brief = String(row.ai_UserBrief || '').trim();

// (28.10) Разговор этапа — без хранилища у OpenAI: каждый ход этап получает карточку выпуска, свои знания
// и последние реплики разговора (log, до 10). Ломаться нечему, и ход всегда одного размера.
const history = plan.silent ? [] : (st.log || []).slice(-10);

let userImageUrl = '';
try { userImageUrl = $('Фото в base64').first().json.userImageUrl || ''; } catch (e) {}

const kb = kbForStage(ctx.tmpl, stage.icon, [plan.userText, brief].join(' '));

// ── Картинки: каждый ход — согласованная и последние 2 варианта (истории у OpenAI нет) ──
let variants = [];
try { variants = JSON.parse(row.ai_ImageVariants || '[]'); } catch (e) { variants = []; }
if (!Array.isArray(variants)) variants = [];
const images = [];
const addImage = (url, label) => { if (url && !images.some(i => i.url === url)) images.push({ url, label }); };
let gridUrl = '';
try { gridUrl = ($('Сервер: сетка').first().json || {}).dataUrl || ''; } catch (e) {}
if (gridUrl && approvedUrl) addImage(gridUrl, 'согласованная картинка выпуска с сеткой процентов: синие подписи — проценты слева направо, красные — сверху вниз');
else if (approvedUrl) addImage(approvedUrl, 'согласованная картинка выпуска');
if (sc.picture) variants.slice(-2).forEach(v => addImage(v.url, 'вариант ' + v.n + ' этого выпуска'));

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
// (28.10) два кармашка: этап с пунктами, который говорит с автором, отвечает всегда одной формой —
// разговор (message) + тексты пунктов (items). Кнопки «записать», которую можно забыть, нет; код не разбирает её слов.
const pockets = myItems.length > 0 && !plan.silent;
const itemsSpec = myItems.map(it => `  ${it.n}. ${it.name}${it.hint ? ' — ' + it.hint : ''}${it.canEmpty ? ' (можно оставить пустым: "-")' : ''}`).join('\n');
const subs = sc.subs;
const talk = plan.silent
  ? 'Ты работаешь молча, по заданию: сразу вызови propose_items со своими пунктами.'
  : 'Ты говоришь с автором напрямую.';

// интернет — только этапу, у которого в листе «Этапы» в «Справочник» написано «интернет»
const tools = /интернет/i.test(stage.ref || '') ? [{ type: 'web_search' }] : [];
const toolLines = [];
if (myItems.length && plan.silent) {
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
  toolLines.push('- propose_items — твои пункты.');
}
const POCKETS = {
  type: 'json_schema', name: 'otvet', strict: true,
  schema: { type: 'object', additionalProperties: false, required: ['message', 'items', 'agreed', 'reopen'], properties: {
    message: { type: 'string', description: 'Что ты говоришь автору' },
    items: { type: 'array', description: 'Тексты твоих пунктов, которые ты в этом ответе пишешь или меняешь, — ровно то, что уйдёт в таблицу; "-" если пункт не нужен. Пусто, если текстов пунктов в этом ответе нет.',
      items: { type: 'object', additionalProperties: false, required: ['n', 'text'], properties: {
        n: { type: 'integer', description: 'Номер пункта' }, text: { type: 'string', description: 'Текст пункта' } } } },
    agreed: { type: 'array', items: { type: 'integer' }, description: 'Номера пунктов, которые автор явно одобрила' },
    reopen: { type: 'array', items: { type: 'integer' }, description: 'Номера согласованных пунктов, которые автор решила пересмотреть' },
  } },
};
if (kb.notesKey && !plan.silent) {
  tools.push({
    type: 'function', name: 'save_note',
    description: 'Дописать в твою памятку (колонка таблицы). Прежние записи система сохраняет сама.',
    parameters: { type: 'object', properties: {
      notes: { type: 'string', description: 'Что дописать' },
      message: { type: 'string', description: 'Реплика автору' },
    }, required: ['notes', 'message'] },
  });
  toolLines.push('- save_note — дописать в памятку. Когда это делать — только по твоим правилам из таблицы.');
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

${pockets ? `ОТВЕТ — всегда два кармашка: message — что ты говоришь автору; items — тексты пунктов, когда ты их пишешь или меняешь
(система запишет их в таблицу и покажет автору с переводом; в message их не повторяй); agreed / reopen — номера пунктов,
которые автор явно одобрила / решила пересмотреть. Изменённый пункт снова ждёт согласования.
` : ''}${toolLines.length ? `ИНСТРУМЕНТЫ. За один ответ — не больше одного.
${toolLines.join('\n')}
` : ''}Когда все твои пункты согласованы, твой этап завершён — система сама передаст выпуск дальше.

ТВОИ ЗНАНИЯ ИЗ ТАБЛИЦЫ КАНАЛА:
${kb.text || '(пусто — в Templates нет колонок с твоим значком)'}
${/эффект/i.test(stage.ref || '') && (ctx.effects || []).length ? `
КАТАЛОГ ЭФФЕКТОВ (лист «Эффекты» таблицы):
${fxCatalogText(ctx.effects)}
` : ''}
КАРТОЧКА ВЫПУСКА (актуальна на этот ход; если расходится с тем, что ты помнишь, — верь карточке):
${card}`;

// ── Сообщение ──
const text = plan.isStart
  ? `[Служебное сообщение] ${plan.event || 'Предыдущий этап завершён.'} Сейчас твой этап — начни по своим правилам.`
  : (plan.userText || '(пустое сообщение)') + ((plan.approveNums || []).length
    ? `\n\n[Система: пункты ${plan.approveNums.join(', ')} уже отмечены согласованными. Если все твои пункты согласованы, этап завершён и выпуск идёт дальше.]`
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
const input = history.map(h => h.r === 'a'
  ? { role: 'assistant', content: [{ type: 'output_text', text: String(h.t || '') }] }
  : { role: 'user', content: String(h.t || '') });
input.push({ role: 'user', content: content.length > 1 ? content : text });

const requestBody = {
  model: stage.model,
  instructions,
  input,
  tools,
  // молчаливый этап работает только пунктами; с автором — свободно (пункты — во втором кармашке)
  tool_choice: plan.silent && myItems.length ? { type: 'function', name: 'propose_items' } : 'auto',
  parallel_tool_calls: false,
  truncation: 'auto',
};
if (pockets) requestBody.text = { format: POCKETS };
if (['low', 'medium', 'high'].includes(stage.effort)) requestBody.reasoning = { effort: stage.effort };

return [{ json: { requestBody, pockets, stageIcon: stage.icon, logUser: plan.isStart ? '[служебно] ' + (plan.event || 'этап начат') : String(plan.userText || '') } }];
