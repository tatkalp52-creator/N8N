// Сценарии движка этапов: схема «напрямую», «одно окно», «завод».
// Код один и тот же — меняются только строки листа «Этапы».
const assert = require('assert');
const { run } = require('./harness12');

const TMPL = {
  tmpl_Channel: 'demo',
  tmpl_ImageModel: 'gpt-image-2',
  '🎨_tmpl_ReferenceImages': 'https://drive.google.com/file/d/STYLE/view\n\nhttps://drive.google.com/file/d/SHEET/view\nлист героя',
  '🎨_tmpl_ArtistRules': 'Рисованная иллюстрация.',
  '🎨📍_tmpl_LocationImages': 'KITCHEN: кухн, kitchen\nУютная кухня с окном.\nhttps://drive.google.com/file/d/K1/view\nкухня как есть\n\nSUBWAY: метро\nhttps://drive.google.com/file/d/S1/view',
  '🖋✍️_tmpl_CharacterPassport': 'Герой — маленький взрослый.',
  '✍️_tmpl_WriterRules': 'Пиши просто.',
  '✍️📝_tmpl_WriterNotes': 'Автор не любит сироп.',
  '🏷️_tmpl_PackagingRules': 'Название коротко.',
  '🏷️📝_tmpl_TechNotes': '',
  '🖋_tmpl_EditorOnly': 'только редактору',
  '⚙️_tmpl_Secret': 'служебное',
  '🎬tmpl_TargetLUFS': '-14',
};
const ITEMS = [
  { 'Канал': 'demo', '№': '1', 'Пункт': 'Оверлей', 'Колонки': 'ai_OverlayText | ai_OverlayPosition', 'Подсказка': 'текст | позиция', 'Можно пусто': 'да' },
  { 'Канал': 'demo', '№': '2', 'Пункт': 'Название', 'Колонки': 'ai_Title', 'Подсказка': '' },
  { 'Канал': 'demo', '№': '3', 'Пункт': 'Описание', 'Колонки': 'ai_DescriptionDraft, ai_DescriptionEN, ai_Description', 'Подсказка': 'история' },
  { 'Канал': 'demo', '№': '4', 'Пункт': 'Подвал', 'Колонки': 'ai_Description', 'Подсказка': 'с [Timecodes]' },
];
const st = (icon, who, talks, approve, does) => ({ 'Канал': 'demo', 'Значок': icon, 'Кто': who, 'С кем говорит': talks, 'Согласование': approve, 'Делает': does });
const DIRECT = [st('🎨', 'Художник', 'автор', 'да', 'картинка'), st('✍️', 'Писатель', 'автор', 'да', '3'), st('🏷️', 'Технический писатель', 'автор', 'да', '1, 2, 4')];
const WINDOW = [st('🖋', 'Редактор', 'автор', 'да', '1, 2, 4'), st('🎨', 'Художник', 'Редактор', 'авто', 'картинка'), st('✍️', 'Писатель', 'Редактор', 'авто', '3')];
const FACTORY = [st('🎨', 'Художник', '', 'авто', 'картинка'), st('✍️', 'Писатель', '', 'авто', '3'), st('🏷️', 'Технический писатель', '', 'авто', '1, 2, 4')];

const call = (name, args) => ({ output: [{ type: 'function_call', name, call_id: 'c_' + name, arguments: JSON.stringify(args) }] });

async function context(stages, row, inc) {
  const nodes = {
    'Разбираем входящее': { kind: 'message', chatId: 1, projectId: 'P1', channelKey: 'demo', text: '', photo: null, replyVariant: null, event: '', ...inc },
    'Находим лист канала': { SheetName: 'demo' },
    'Читаем строку проекта': { sys_ProjectID: 'P1', sys_Status: 'Картинка в работе', ai_ImageVariants: '[]', ...row },
    'Читаем шаблоны канала': TMPL,
    'Читаем этапы': stages,
    'Читаем пункты': inc.__items || ITEMS,
  };
  return (await run('Контекст проекта', { nodes }))[0];
}

// Один ход: Кто отвечает → (модель: запрос → ответ → разбор → поручение) → Итог хода
async function turn(stages, row, inc, response, subResponse) {
  const ctx = await context(stages, row, inc);
  const nodes = { 'Контекст проекта': ctx };
  nodes['Кто отвечает'] = (await run('Кто отвечает', { nodes }))[0];
  let req = null;
  if (nodes['Кто отвечает'].mode === 'model') {
    if (nodes['Кто отвечает'].needConv) nodes['OpenAI: создаём разговор'] = { id: 'conv_new' };
    req = (await run('Готовим запрос этапу', { nodes }))[0];
    nodes['Готовим запрос этапу'] = req;
    nodes['Разбираем ответ этапа'] = (await run('Разбираем ответ этапа', { nodes, input: [response] }))[0];
    if (nodes['Разбираем ответ этапа'].action === 'delegate') {
      nodes['Готовим поручение'] = (await run('Готовим поручение', { nodes }))[0];
      nodes['OpenAI: поручение'] = subResponse;
    }
  }
  const r = (await run('Итог хода', { nodes }))[0];
  nodes['Итог хода'] = r;
  const next = (await run('Что дальше?', { nodes }))[0].next;
  return { ctx, plan: nodes['Кто отвечает'], req, r, next, nodes };
}

(async () => {
  // ── 1. Напрямую: новый выпуск → художник ждёт задание ──
  let t = await turn(DIRECT, {}, { kind: 'stageStart', event: 'Новый выпуск.' });
  assert.equal(t.plan.mode, 'say');
  assert.ok(t.r.chunks[0].includes('🎨 Художник: жду задание'));
  console.log('1 новый выпуск → художник ждёт задание OK');

  // ── 2. Сообщение автора — задание художнику (без префикса): знания 🎨 + место по слову ──
  t = await turn(DIRECT, {}, { text: 'Пингви на кухне печёт пирог' });
  assert.equal(t.next, 'draw');
  assert.ok(t.r.dallePrompt.includes('Рисованная иллюстрация.'));
  assert.ok(t.r.dallePrompt.includes('Уютная кухня с окном.'), 'место по слову «кухне»');
  assert.ok(!t.r.dallePrompt.includes('KITCHEN:'), 'строка с триггерами — механика, художнику не идёт');
  assert.ok(!t.r.dallePrompt.includes('маленький взрослый'), 'паспорт без 🎨 художнику не идёт');
  assert.ok(t.r.dallePrompt.endsWith('Пингви на кухне печёт пирог'));
  assert.deepEqual(t.r.drawRefUrls, ['https://lh3.googleusercontent.com/d/STYLE=s2000', 'https://lh3.googleusercontent.com/d/SHEET=s2000', 'https://lh3.googleusercontent.com/d/K1=s2000']);
  assert.ok(t.r.drawRoles.includes('Image 2 — лист героя.') && t.r.drawRoles.includes('Image 3 — кухня как есть.'));
  assert.ok(!t.r.drawRefUrls.some(u => u.includes('S1')), 'метро не названо — его картинки нет');
  assert.equal(t.r.imageModel, 'gpt-image-2');
  // ответ на картинку «Вариант 1» — правка
  const V = JSON.stringify([{ n: 1, url: 'U1' }, { n: 2, url: 'U2' }]);
  t = await turn(DIRECT, { ai_ImageVariants: V, ai_ImageUrl: 'U2' }, { text: 'светлее', replyVariant: 1 });
  assert.equal(t.next, 'edit'); assert.equal(t.r.revisionTargetImageUrl, 'U1'); assert.equal(t.r.revisionInstruction, 'светлее');
  t = await turn(DIRECT, { ai_ImageVariants: V, ai_ImageUrl: 'U2' }, { text: 'правка 2: убрать кота' });
  assert.equal(t.next, 'edit'); assert.equal(t.r.revisionTargetImageUrl, 'U2'); assert.equal(t.r.revisionInstruction, 'убрать кота');
  // правка с фото-обводкой: план просит маску; маска — к первой картинке; подпись честно говорит, сработала ли
  t = await turn(DIRECT, { ai_ImageVariants: V, ai_ImageUrl: 'U2' }, { text: 'шторка на штанге', replyVariant: 2, photo: [{ file_id: 'S' }, { file_id: 'B' }] });
  assert.equal(t.plan.mode, 'edit'); assert.equal(t.plan.needMask, true); assert.equal(t.plan.maskPhoto[1].file_id, 'B');
  {
    const base = { 'Скачиваем текущую картинку (C)': { __binary: { image_0: 'IMG' } } };
    const extra = { revisionInstruction: 'шторка', extraCount: 2, __binary: { image_1: 'R1', image_2: 'R2' } };
    let o = (await run('Собираем все референсы (C)', { nodes: { ...base, 'Сервер: маска': { __binary: { mask: 'M' } } }, input: [extra] }))[0];
    assert.equal(o.hasMask, true); assert.equal(o.__binary.mask, 'M'); assert.equal(o.imageCount, 3); assert.equal(o.__binary.image_0, 'IMG');
    o = (await run('Собираем все референсы (C)', { nodes: { ...base, 'Сервер: маска': { ok: false, error: 'нет обводки' } }, input: [extra] }))[0];
    assert.equal(o.hasMask, false); assert.ok(!o.__binary.mask);
    o = (await run('Собираем все референсы (C)', { nodes: base, input: [extra] }))[0];
    assert.equal(o.hasMask, false, 'без фото — обычная правка');
    const { wf } = require('./harness12.js');
    const masked = wf.nodes.filter(n => n.name.startsWith('gpt-image-2: правка по обводке'));
    assert.equal(masked.length, 8);
    assert.ok(masked.every(n => n.parameters.bodyParameters.parameters.some(p => p.name === 'mask' && p.inputDataFieldName === 'mask')));
    assert.ok(wf.connections['С маской? (C)'].main[0][0].node === 'Сколько картинок? (C, маска)');
  }
  t = await turn(DIRECT, { ai_ImageVariants: V, ai_ImageUrl: 'U2' }, { text: 'правка 2: убрать кота' });
  assert.equal(t.plan.needMask, false);
  {
    const tg = { message: { chat: { id: 1 }, from: { id: 1 }, caption: 'шторка', document: { file_id: 'D', mime_type: 'image/jpeg' },
      reply_to_message: { caption: 'Вариант 2\nID: 20261004_192748_pengui' } } };
    const r = (await run('Разбираем входящее', { nodes: { 'Telegram Trigger': tg } }))[0];
    assert.deepEqual(r.photo, [{ file_id: 'D' }], 'картинка файлом — тоже картинка');
    assert.equal(r.replyVariant, 2);
    // новый формат Telegram: rich_message с блоками «абзац» и «фото»
    const tg2 = { message: { chat: { id: 1 }, from: { id: 1 }, reply_to_message: { caption: 'Вариант 14\nID: 20261004_192748_pengui' },
      rich_message: { blocks: [{ type: 'paragraph', text: '1) смеситель' }, { type: 'photo', photo: [{ file_id: 'small' }, { file_id: 'big' }] }] } } };
    const r2 = (await run('Разбираем входящее', { nodes: { 'Telegram Trigger': tg2 } }))[0];
    assert.equal(r2.text, '1) смеситель'); assert.equal(r2.photo[1].file_id, 'big'); assert.equal(r2.replyVariant, 14);
  }
  console.log('2 художник: задание, место по слову, правка, правка по обводке OK');

  // ── 3. Картинка согласована → следующий этап: Писатель, чистая голова ──
  const APPROVED = { ai_ImageVariants: V, ai_ApprovedImageUrl: 'U2', sys_Status: 'Картинка согласована', ai_UserBrief: 'Пингви на кухне' };
  t = await turn(DIRECT, APPROVED, { kind: 'stageStart', event: 'Картинка согласована (вариант 2).' },
    call('propose_items', { items: [{ n: 3, text: 'Pengui baked a pie.', ru: 'Пингви испёк пирог.' }], message: 'Вот история.' }));
  assert.equal(t.plan.stageName, 'Писатель');
  const ins = t.req.requestBody.instructions;
  assert.ok(ins.includes('Пиши просто.') && ins.includes('маленький взрослый') && ins.includes('Автор не любит сироп.'));
  assert.ok(!ins.includes('Название коротко.'), 'колонка 🏷️ Писателю не идёт');
  assert.ok(!ins.includes('только редактору') && !ins.includes('служебное') && !ins.includes('Рисованная'), 'чужие и служебные колонки не идут');
  assert.ok(ins.includes('3. Описание — история'));
  assert.equal(t.req.requestBody.conversation, 'conv_new');
  assert.ok(t.req.requestBody.input[0].content.some(c => c.image_url === 'U2'), 'писатель видит согласованную картинку');
  assert.ok(t.req.requestBody.input[0].content[0].text.includes('Картинка согласована (вариант 2)'));
  const toolNames = t.req.requestBody.tools.map(x => x.name).filter(Boolean);
  assert.deepEqual(toolNames, ['propose_items', 'save_note']);
  assert.ok(t.r.chunks[0].startsWith('✍️ <b>Писатель</b>: Вот история.'));
  assert.ok(t.r.chunks[0].includes('<b>3. Описание</b>\nPengui baked a pie.\n\n— Перевод для автора —\nПингви испёк пирог.') || t.r.chunks[0].includes('Pengui baked a pie. (Пингви испёк пирог.)'));
  assert.equal(t.next, 'none');
  let state = JSON.parse(t.r.editorState);
  assert.equal(state.stages['✍'].conv, 'conv_new'); assert.equal(state.stages['✍'].pending, 'c_propose_items');
  console.log('3 писатель: только ✍️-колонки, свой разговор, картинка OK');

  // ── 4. Автор согласовала описание → этап завершён → Технический писатель ──
  t = await turn(DIRECT, { ...APPROVED, sys_EditorState: t.r.editorState }, { text: 'отлично, согласовано' },
    call('propose_items', { agreed: [3], message: 'Спасибо!' }));
  assert.equal(t.plan.stageName, 'Писатель');
  assert.equal(t.req.requestBody.conversation, 'conv_new', 'тот же разговор писателя');
  assert.equal(t.req.requestBody.input[0].type, 'function_call_output');
  assert.equal(t.next, 'next'); assert.equal(t.r.nextIcon, '🏷️');
  state = JSON.parse(t.r.editorState);
  console.log('4 описание согласовано → переход к следующему этапу OK');

  // памятка писателя → колонка со значком ✍️ и 📝
  let tn = await turn(DIRECT, { ...APPROVED, sys_EditorState: t.r.editorState }, { text: 'Писателю: запомни — без крошечных стаканчиков' },
    call('save_note', { notes: 'Автор не любит сироп. Стакан у щедрого фермера полный.', message: 'Запомнил.' }));
  assert.equal(tn.plan.stageName, 'Писатель');
  assert.equal(tn.r.note.key, '✍️📝_tmpl_WriterNotes');
  const pm = (await run('Памятка', { nodes: { 'Итог хода': tn.r } }))[0];
  assert.deepEqual(pm, { tmpl_Channel: 'demo', '✍️📝_tmpl_WriterNotes': 'Автор не любит сироп. Стакан у щедрого фермера полный.' });
  console.log('4b памятка — в колонку со значком этапа и 📝 OK');

  // ── 5. Технический: видит описание, предлагает свои пункты; «-» для оверлея ──
  t = await turn(DIRECT, { ...APPROVED, sys_EditorState: t.r.editorState }, { kind: 'stageStart', event: 'Этап «Писатель» завершён.' },
    call('propose_items', { items: [{ n: 1, text: 'Just Apples | right', ru: 'Просто яблоки' }, { n: 2, text: 'Apple Day' }, { n: 4, text: '[Timecodes]\n──\nfooter' }], message: 'Варианты.' }));
  assert.equal(t.plan.stageName, 'Технический писатель');
  assert.ok(t.req.requestBody.instructions.includes('Название коротко.'));
  assert.ok(!t.req.requestBody.instructions.includes('Пиши просто.'));
  assert.ok(t.req.requestBody.instructions.includes('Pengui baked a pie.'), 'карточка показывает согласованное описание');
  assert.ok(t.r.chunks[0].includes('Ждут согласования:</b> 1, 2, 4'));
  t = await turn(DIRECT, { ...APPROVED, sys_EditorState: t.r.editorState }, { text: 'всё ок' }, call('propose_items', { agreed: [1, 2, 4], message: 'Готово.' }));
  assert.equal(t.next, 'summary');
  console.log('5 технический → всё согласовано → сводка OK');

  // ── 6. Сводка и запись по листу «Пункты» ──
  const ctx6 = await context(DIRECT, { ...APPROVED, sys_EditorState: t.r.editorState }, { kind: 'finalApprove' });
  const sv = await run('Сводка', { nodes: { 'Контекст проекта': ctx6, 'Итог хода': t.r } });
  assert.ok(sv[0].text.includes('<b>3. Описание</b>') && sv[0].text.includes('Apple Day'));
  const pk = (await run('Собираем пакет для таблицы', { nodes: { 'Контекст проекта': ctx6 } }))[0];
  assert.ok(pk.ok, pk.problemsText);
  assert.equal(pk.fields.ai_OverlayText, 'Just Apples'); assert.equal(pk.fields.ai_OverlayPosition, 'right');
  assert.equal(pk.fields.ai_DescriptionEN, 'Pengui baked a pie.');
  assert.equal(pk.fields.ai_Description, 'Pengui baked a pie.\n\n[Timecodes]\n──\nfooter');
  assert.equal(pk.fields.ai_Title, 'Apple Day');
  const fresh = { ...pk.fields, ai_ApprovedImageUrl: 'U2' };
  const chk = (await run('Проверяем таблицу (финал)', { nodes: { 'Контекст проекта': ctx6 }, input: [fresh] }))[0];
  assert.ok(chk.ok, chk.problemsText);
  const chk2 = (await run('Проверяем таблицу (финал)', { nodes: { 'Контекст проекта': ctx6 }, input: [{ ...fresh, ai_Title: '' }] }))[0];
  assert.ok(!chk2.ok && chk2.problemsText.includes('ai_Title пустая'));
  console.log('6 сводка, запись по «Пунктам», проверка OK');

  // ── 7. Обращение к прошлому этапу: «Художнику: …» на этапе писателя ──
  t = await turn(DIRECT, APPROVED, { text: 'Художнику: добавь кота' });
  assert.equal(t.next, 'draw'); assert.ok(t.r.dallePrompt.endsWith('добавь кота'));
  t = await turn(DIRECT, APPROVED, { text: '🏷️ какое название?' }, { output: [{ type: 'message', content: [{ type: 'output_text', text: 'Подумаю.' }] }] });
  assert.equal(t.plan.stageName, 'Технический писатель'); assert.equal(t.plan.userText, 'какое название?');
  console.log('7 обращение к любому этапу по имени или значку OK');

  // ── 8. Одно окно: Редактор говорит с автором и поручает Писателю ──
  t = await turn(WINDOW, { ...APPROVED }, { text: 'давай историю про пирог' },
    call('delegate', { stage: 'Писатель', task: 'История про пирог', message: 'Поручил писателю.' }),
    call('propose_items', { items: [{ n: 3, text: 'Pie story.', ru: 'Про пирог.' }] }));
  assert.equal(t.plan.stageName, 'Редактор');
  const edTools = t.req.requestBody.tools.map(x => x.name).filter(Boolean);
  assert.ok(edTools.includes('delegate') && edTools.includes('approve_image'));
  const sub = t.nodes['Готовим поручение'].requestBody;
  assert.ok(sub.instructions.includes('Пиши просто.') && !sub.instructions.includes('только редактору'));
  assert.deepEqual(sub.tool_choice, { type: 'function', name: 'propose_items' });
  state = JSON.parse(t.r.editorState);
  assert.equal(state.items[3].text, 'Pie story.'); assert.ok(!state.agreed[3], 'описание согласует автор — через Редактора');
  assert.ok(t.r.chunks[0].startsWith('🖋 <b>Редактор</b>') && t.r.chunks[0].includes('Pie story.'));
  // Редактор поручает художнику
  t = await turn(WINDOW, {}, { text: 'нарисуй кухню' }, call('delegate', { stage: 'Художник', task: 'Пингви на кухне', message: 'Рисуем.' }));
  assert.equal(t.next, 'draw'); assert.ok(t.r.dallePrompt.includes('Уютная кухня') && t.r.dallePrompt.endsWith('Пингви на кухне'));
  assert.equal(t.r.autoApprove, false, 'художник «авто», но начальник согласует сам — картинку согласует автор через Редактора');
  console.log('8 одно окно: Редактор поручает писателю и художнику OK');

  // ── 9. Завод: всё «авто», с автором никто не говорит ──
  t = await turn(FACTORY, { ai_UserBrief: 'осенний сад' }, { kind: 'stageStart', event: 'Новый выпуск.' });
  assert.equal(t.next, 'draw'); assert.ok(t.r.dallePrompt.endsWith('осенний сад')); assert.equal(t.r.autoApprove, true);
  t = await turn(FACTORY, { ai_UserBrief: 'осенний сад', ai_ApprovedImageUrl: 'U1', ai_ImageVariants: '[{"n":1,"url":"U1"}]' }, { kind: 'stageStart', event: 'Картинка готова.' },
    call('propose_items', { items: [{ n: 3, text: 'Garden story.' }] }));
  assert.equal(t.plan.stageName, 'Писатель'); assert.ok(t.plan.silent);
  assert.deepEqual(t.req.requestBody.tool_choice, { type: 'function', name: 'propose_items' });
  assert.ok(!t.req.requestBody.conversation, 'молчаливый этап — без разговора');
  assert.equal(t.next, 'next', 'пункты согласованы сами → дальше');
  t = await turn(FACTORY, { ai_UserBrief: 'осенний сад', ai_ApprovedImageUrl: 'U1', sys_EditorState: t.r.editorState }, { kind: 'stageStart' },
    call('propose_items', { items: [{ n: 1, text: '-' }, { n: 2, text: 'Garden' }, { n: 4, text: '[Timecodes]' }] }));
  assert.equal(t.next, 'package', 'никто не согласует — сразу запись в таблицу');
  console.log('9 завод: бриф → картинка → тексты → запись, без согласований OK');

  // ── 9b. Всё готово, автор пишет без обращения — отвечает последний пишущий, не художник ──
  {
    const all = JSON.stringify({ v: 2, items: { 1: { text: 'a' }, 2: { text: 'b' }, 3: { text: 'c' }, 4: { text: 'd' } }, agreed: { 1: true, 2: true, 3: true, 4: true }, stages: {} });
    t = await turn(DIRECT, { ...APPROVED, sys_EditorState: all }, { text: 'Привет' }, { output: [{ type: 'message', content: [{ type: 'output_text', text: 'Привет!' }] }] });
    assert.equal(t.plan.stageName, 'Технический писатель');
    t = await turn([DIRECT[0]], APPROVED, { text: 'Привет' });
    assert.notEqual(t.next, 'draw', 'художник без обращения не рисует «Привет»');
  }
  console.log('9b всё готово → отвечает пишущий этап, художник не рисует приветствие OK');

  // ── 9c. Аниматор: видит картинку с сеткой (метка в памяти, не данные), его пункт — с превью ──
  {
    const ANIM = [DIRECT[0], { ...st('🎞️', 'Аниматор', 'автор', 'да', '9'), 'Картинка': 'с сеткой', 'Справочник': 'Эффекты' }];
    const FX = [
      { 'Семейство': 'Пар и дым', 'Эффект': 'дым', 'Механика': 'smoke', 'Строка для сборщика': 'дымок: x, y', 'Как размечать': 'кружок', 'Ручки': 'густота', 'Статус': 'готов', demo: 'густота 4', other: '' },
      { 'Семейство': 'Осадки', 'Эффект': 'снег', 'Механика': 'snow', 'Строка для сборщика': 'снег: область', 'Как размечать': 'заливка', 'Ручки': 'густота', 'Статус': 'пока не умеет', demo: '' },
      { 'Семейство': 'КАК ЧИТАТЬ ЛИСТ', 'Эффект': '', 'Механика': '' }];
    const IT9 = [...ITEMS, { 'Канал': 'demo', '№': '9', 'Пункт': 'Оживление', 'Колонки': 'fx_Effects', 'Можно пусто': 'да', 'Превью': 'оживление' }];
    const ctxA = await (async () => {
      const nodes = { 'Разбираем входящее': { kind: 'stageStart', chatId: 1, projectId: 'P1', channelKey: 'demo', text: '', event: 'Картинка согласована.' },
        'Находим лист канала': { SheetName: 'demo' }, 'Читаем строку проекта': { sys_ProjectID: 'P1', ai_ApprovedImageUrl: 'U2', ai_ImageVariants: V },
        'Читаем шаблоны канала': { ...TMPL, '🎞️_tmpl_AnimatorRules': 'дымок: x, y' }, 'Читаем этапы': ANIM, 'Читаем пункты': IT9, 'Читаем эффекты': FX };
      return (await run('Контекст проекта', { nodes }))[0];
    })();
    const n = { 'Контекст проекта': ctxA };
    n['Кто отвечает'] = (await run('Кто отвечает', { nodes: n }))[0];
    assert.equal(n['Кто отвечает'].stageName, 'Аниматор'); assert.equal(n['Кто отвечает'].needGrid, true);
    n['OpenAI: создаём разговор'] = { id: 'cA' };
    n['Сервер: сетка'] = { ok: true, dataUrl: 'data:image/jpeg;base64,GRID' };
    const req = (await run('Готовим запрос этапу', { nodes: n }))[0];
    const imgs = req.requestBody.input[0].content.filter(c => c.type === 'input_image').map(c => c.image_url);
    assert.deepEqual(imgs, ['data:image/jpeg;base64,GRID'], 'аниматор видит картинку с сеткой');
    assert.deepEqual(req.requestBody.tool_choice, { type: 'function', name: 'propose_items' }, 'пункт с превью — всегда строками, тогда придёт видео');
    assert.ok(req.seen.includes('grid:U2') && !req.seen.some(x => x.startsWith('data:')), 'в памяти — метка, не данные');
    assert.ok(req.requestBody.instructions.includes('КАТАЛОГ ЭФФЕКТОВ') && req.requestBody.instructions.includes('строка «дымок: x, y»')
      && req.requestBody.instructions.includes('на этом канале: густота 4') && req.requestBody.instructions.includes('на этом канале: не используется'),
      'аниматор видит каталог эффектов со столбцом своего канала');
    n['Готовим запрос этапу'] = req;
    n['Разбираем ответ этапа'] = (await run('Разбираем ответ этапа', { nodes: n, input: [call('propose_items', { items: [{ n: 9, text: 'дымок: 44, 37' }], message: 'Вот.' })] }))[0];
    // лупа: точки уточняются по увеличенным кусочкам, меняются только числа этих точек
    {
      const ln = { ...n, 'Разбираем ответ этапа': (await run('Разбираем ответ этапа', { nodes: n, input: [call('propose_items', { items: [{ n: 9, text: 'свеча: 62, 49\nдождь: 56, 44, 71, 60\nлистья: 46, 14 → 47, 88; раз в 2 мин' }], message: 'Вот.' })] }))[0] };
      const lp = (await run('Лупа: план', { nodes: ln }))[0];
      assert.equal(lp.need, true); assert.equal(lp.n, 9); assert.equal(lp.imageUrl, 'U2');
      ln['Лупа: план'] = lp;
      ln['Сервер: лупа'] = { ok: true, points: [
        { id: '0:0', line: 0, pair: 0, label: 'середина пламени свечи', x: 62, y: 49, dataUrl: 'data:A' },
        { id: '1:0', line: 1, pair: 0, label: 'левый верхний угол стекла', x: 56, y: 44, dataUrl: 'data:B' },
        { id: '1:1', line: 1, pair: 1, label: 'правый нижний угол стекла', x: 71, y: 60, dataUrl: 'data:C' }] };
      const lz = (await run('Готовим уточнение', { nodes: ln }))[0];
      assert.equal(lz.requestBody.input[0].content.filter(c => c.type === 'input_image').length, 3);
      assert.deepEqual(lz.requestBody.tool_choice, { type: 'function', name: 'refine_points' });
      ln['OpenAI: уточнение'] = { output: [{ type: 'function_call', name: 'refine_points', arguments: JSON.stringify({ points: [
        { id: '0:0', x: 60.6, y: 42.3 }, { id: '1:0', x: 53, y: 37 }, { id: '1:1', x: 65, y: 43 }, { id: '9:9', x: 1, y: 1 }] }) }] };
      const li = (await run('Лупа: итог', { nodes: ln }))[0];
      const txt = JSON.parse(li.editorState).items[9].text;
      assert.equal(txt, 'свеча: 60.6, 42.3\nдождь: 53, 37, 65, 43\nлистья: 46, 14 → 47, 88; раз в 2 мин');
      assert.equal(li.moved, 3);
      ln['Лупа: итог'] = li;
      const rr = (await run('Итог хода', { nodes: ln }))[0];
      assert.equal(rr.previewBody.fx_Effects, txt, 'превью — уже по уточнённым точкам');
      assert.ok(rr.chunks[0].includes('Лупа уточнила точек: 3'));
      // слишком далёкий «уточнённый» ответ не принимаем
      ln['OpenAI: уточнение'] = { output: [{ type: 'function_call', name: 'refine_points', arguments: JSON.stringify({ points: [{ id: '0:0', x: 20, y: 10 }] }) }] };
      assert.ok(JSON.parse((await run('Лупа: итог', { nodes: ln }))[0].editorState).items[9].text.startsWith('свеча: 62, 49'));
      // без пункта оживления лупа не нужна
      const nn = { ...n, 'Разбираем ответ этапа': { ...ln['Разбираем ответ этапа'], changed: [] } };
      assert.equal((await run('Лупа: план', { nodes: nn }))[0].need, false);
    }
    const r = (await run('Итог хода', { nodes: n }))[0];
    assert.equal(r.previewBody.fx_Effects, 'дымок: 44, 37'); assert.equal(r.previewBody.imageUrl, 'U2');
    assert.equal(r.previewBody.targetLUFS, '-14', 'вид эффектов — колонки 🎬');
    assert.deepEqual(r.previewBody.fxTable, [{ mech: 'smoke', knobs: 'густота 4' }], 'ручки эффектов канала — из листа «Эффекты»');
    assert.ok(r.previewCaption.includes('ID: P1'));
    const nx = (await run('Что дальше?', { nodes: { 'Итог хода': r } }))[0];
    assert.equal(nx.preview, true);
    // автор прислала фото с красной разметкой — сборщик прочитал, Аниматор получил точные числа
    const ctxM = { ...ctxA, kind: 'message', text: 'вот так', photo: [{ file_id: 'F' }] };
    const nm = { 'Контекст проекта': ctxM };
    nm['Кто отвечает'] = (await run('Кто отвечает', { nodes: nm }))[0];
    assert.equal(nm['Кто отвечает'].needMarks, true);
    nm['Фото в base64'] = { userImageUrl: 'data:image/jpeg;base64,MARKED' };
    nm['Сервер: разметка'] = { ok: true, text: '1) верхний конец 47, 19; нижний конец 44, 37' };
    nm['OpenAI: создаём разговор'] = { id: 'cM' };
    const rq = (await run('Готовим запрос этапу', { nodes: nm }))[0];
    assert.ok(rq.requestBody.input[0].content[0].text.includes('Разметка автора') && rq.requestBody.input[0].content[0].text.includes('нижний конец 44, 37'));
    assert.deepEqual(rq.requestBody.tool_choice, { type: 'function', name: 'propose_items' }, 'по разметке — всегда новый пункт, значит и новое превью');
    // автор видит, дошла ли разметка; строки для сборщика ей не показываем
    nm['Сервер: разметка'] = { ok: true, marks: [{}, {}], text: '…' };
    nm['Готовим запрос этапу'] = rq;
    nm['Разбираем ответ этапа'] = (await run('Разбираем ответ этапа', { nodes: nm, input: [call('propose_items', { items: [{ n: 9, text: 'дымок: 44, 37 → 46, 20' }], message: 'Поправил.' })] }))[0];
    const rm = (await run('Итог хода', { nodes: nm }))[0];
    assert.ok(rm.chunks[0].includes('Разметка прочитана: штрихов — 2'));
    assert.ok(rm.chunks[0].includes('смотрите картинку-превью') && !rm.chunks[0].includes('46, 20'));
    assert.equal(rm.previewBody.fx_Effects, 'дымок: 44, 37 → 46, 20');
    nm['Сервер: разметка'] = { ok: true, zones: true, marks: [], text: 'обводки' };
    assert.ok((await run('Итог хода', { nodes: nm }))[0].chunks[0].includes('обводки и подписи'));
    nm['Сервер: разметка'] = { ok: false, error: 'boom', marks: [], text: '' };
    const rf = (await run('Итог хода', { nodes: nm }))[0];
    assert.ok(rf.chunks[0].includes('Разметку прочитать не удалось (boom)'));
    // диспетчер: автор пишет «9 ок», а модель вместо отметки сохраняет памятку — пункт всё равно согласован,
    // этап завершён, выпуск идёт дальше, согласованное сразу в колонках таблицы
    const st9 = JSON.stringify({ v: 2, items: { 9: { text: 'дымок: 44, 37', ru: '' } }, agreed: { 9: false }, stages: { '🎞': { conv: 'cA', pending: '', seen: ['grid:U2'] } } });
    const ctxO = { ...ctxA, kind: 'message', text: '9 ок', row: { ...ctxA.row, sys_EditorState: st9 }, tmpl: { ...ctxA.tmpl, '🎞️📝_tmpl_AnimatorNotes': 'старое' } };
    const no = { 'Контекст проекта': ctxO };
    no['Кто отвечает'] = (await run('Кто отвечает', { nodes: no }))[0];
    assert.deepEqual(no['Кто отвечает'].approveNums, [9]);
    no['Готовим запрос этапу'] = (await run('Готовим запрос этапу', { nodes: no }))[0];
    assert.ok(no['Готовим запрос этапу'].requestBody.instructions.includes('9. Оживление [СОГЛАСОВАНО'));
    no['Разбираем ответ этапа'] = (await run('Разбираем ответ этапа', { nodes: no, input: [call('save_note', { notes: 'дымок из трубы', message: 'Запомнил.' })] }))[0];
    const ro = (await run('Итог хода', { nodes: no }))[0];
    assert.equal(JSON.parse(ro.editorState).agreed[9], true);
    assert.ok(ro.note, 'памятка тоже сохраняется');
    assert.notEqual(ro.transition, 'none', 'этап завершён — выпуск идёт дальше');
    assert.equal(ro.agreedFields.fx_Effects, 'дымок: 44, 37');
    // не чистое одобрение — решает модель
    for (const t of ['9 ок, но дым правее', 'да', 'это ещё один лист?']) {
      const c = { ...ctxO, text: t };
      assert.deepEqual((await run('Кто отвечает', { nodes: { 'Контекст проекта': c } }))[0].approveNums, [], t);
    }
    for (const t of ['ок', 'Всё ок!', '👍', 'согласовано', '9 и 3 ок']) {
      const c = { ...ctxO, text: t };
      assert.deepEqual((await run('Кто отвечает', { nodes: { 'Контекст проекта': c } }))[0].approveNums, [9], t);
    }
  }
  console.log('9c аниматор: сетка для него, превью для автора OK');

  // ── 9d. «9 предложи заново» — к этапу, чей пункт, даже если сейчас работает другой ──
  {
    const who = async (stages, text) => (await run('Кто отвечает', { nodes: { 'Контекст проекта': await context(stages, APPROVED, { text }) } }))[0];
    assert.equal((await who(DIRECT, 'перепиши концовку')).stageName, 'Писатель', 'без номера — текущий этап');
    assert.equal((await who(DIRECT, '1 предложи заново')).stageName, 'Технический писатель', 'номер чужого пункта — его этапу');
    assert.equal((await who(DIRECT, 'пункт 2: короче')).stageName, 'Технический писатель');
    assert.equal((await who(DIRECT, '3 ок')).stageName, 'Писатель');
    assert.equal((await who(DIRECT, '1, 3 ок')).stageName, 'Писатель', 'номера разных этапов — текущий этап');
    assert.equal((await who(WINDOW, '3 перепиши')).stageName, 'Редактор', 'за подчинённого — его начальник');
    assert.equal((await who(DIRECT, '✍️ 1 тоже глянь')).stageName, 'Писатель', 'обращение важнее номера');
  }
  console.log('9d номер пункта — к его этапу OK');

  // ── 9e. Аниматор прислал те же строки — видео-превью всё равно приходит ──
  {
    const ANIM2 = [DIRECT[0], { ...st('🎞️', 'Аниматор', 'автор', 'да', '9') }, DIRECT[1], DIRECT[2]];
    const IT9 = [...ITEMS, { 'Канал': 'demo', '№': '9', 'Пункт': 'Оживление', 'Колонки': 'fx_Effects', 'Можно пусто': 'да', 'Превью': 'оживление' }];
    const ROW = { ...APPROVED, sys_EditorState: JSON.stringify({ v: 2, items: { 9: { text: 'свеча: 61, 41.9' } }, agreed: { 9: false }, stages: {} }) };
    const t9 = await turn(ANIM2, ROW, { text: '9 предложи заново', __items: IT9 }, call('propose_items', { items: [{ n: 9, text: 'свеча: 61, 41.9' }], message: 'Те же строки.' }));
    assert.equal(t9.plan.stageName, 'Аниматор');
    assert.deepEqual(t9.req.requestBody.tool_choice, { type: 'function', name: 'propose_items' });
    assert.ok(t9.r.previewBody && t9.r.previewBody.fx_Effects === 'свеча: 61, 41.9', 'без изменений — превью всё равно');
  }
  console.log('9e те же строки → превью OK');

  // ── 9f. Слово «пересобери» реплаем на выпуск = сборка без новой чистки ──
  {
    const mk = text => ({ message: { chat: { id: 1 }, from: { id: 1 }, text, reply_to_message: { text: 'ID: 20261006_142515_pengui' } } });
    for (const w of ['пересобери', 'Пересобери!', 'собери', 'Собрать', 'пересобрать']) {
      const r = (await run('Разбираем входящее', { nodes: { 'Telegram Trigger': mk(w) } }))[0];
      assert.equal(r.kind, 'build', w); assert.equal(r.projectId, '20261006_142515_pengui');
    }
    for (const w of ['собери мне пожалуйста картинку по-другому', 'пересобери текст 3', 'привет']) {
      const r = (await run('Разбираем входящее', { nodes: { 'Telegram Trigger': mk(w) } }))[0];
      assert.equal(r.kind, 'message', w);
    }
    const l = (await run('Разбираем входящее', { nodes: { 'Telegram Trigger': mk('https://drive.google.com/file/d/1CQQwEcSM1TUOIzI1XyskHVK_-kiuBVeI/view') } }))[0];
    assert.equal(l.kind, 'tracks');
  }
  console.log('9f «пересобери» → build, обычные реплики и ссылка не задеты OK');

  // ── 10. Нет строк в «Этапах» — честно говорим ──
  t = await turn([], {}, { text: 'привет' });
  assert.ok(t.r.chunks[0].includes('В листе «Этапы» нет строк'));
  console.log('10 пустой лист «Этапы» → понятное сообщение OK');

  // ── 11. Переход: внутренний вызов несёт выпуск и событие ──
  const ctxN = await context(DIRECT, APPROVED, {});
  const d = (await run('Передаём дальше', { nodes: { 'Контекст проекта': ctxN, 'Итог хода': { event: 'Этап «Писатель» завершён.' } } }))[0];
  assert.deepEqual(d, { kind: 'stageStart', projectId: 'P1', channelKey: 'demo', chatId: 1, event: 'Этап «Писатель» завершён.' });
  const inner = (await run('Разбираем входящее', { nodes: { 'Вызов изнутри': d } }))[0];
  assert.equal(inner.kind, 'stageStart'); assert.equal(inner.event, 'Этап «Писатель» завершён.');
  console.log('11 переход к следующему этапу через внутренний вызов OK');

  console.log('ALL OK');
})().catch(e => { console.error('FAIL', e); process.exit(1); });
