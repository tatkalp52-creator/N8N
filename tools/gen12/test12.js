// Сценарии движка этапов: схема «напрямую», «одно окно», «завод».
// Код один и тот же — меняются только строки листа «Этапы».
const assert = require('assert');
const { run } = require('./harness12');

const TMPL = {
  tmpl_Channel: 'demo',
  tmpl_ImageModel: 'gpt-image-2',
  tmpl_ImageQuality: 'high',
  tmpl_ImageSize: '1536x864',
  tmpl_LightModel: 'gpt-5-mini',
  tmpl_LightEffort: 'minimal',
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
  '🌐_tmpl_TranslationRules': 'Пингви in English is always Pengui (he).',
};
const ITEMS = [
  { 'Канал': 'demo', '№': '1', 'Пункт': 'Оверлей', 'Колонки': 'ai_OverlayText | ai_OverlayPosition', 'Подсказка': 'текст | позиция', 'Можно пусто': 'да' },
  { 'Канал': 'demo', '№': '2', 'Пункт': 'Название', 'Колонки': 'ai_Title', 'Подсказка': '' },
  { 'Канал': 'demo', '№': '3', 'Пункт': 'Описание', 'Колонки': 'ai_DescriptionDraft, ai_DescriptionEN, ai_Description', 'Подсказка': 'история' },
  { 'Канал': 'demo', '№': '4', 'Пункт': 'Подвал', 'Колонки': 'ai_Description', 'Подсказка': 'с [Timecodes]' },
];
const st = (icon, who, talks, approve, does) => ({ 'Канал': 'demo', 'Значок': icon, 'Кто': who, 'С кем говорит': talks, 'Согласование': approve, 'Делает': does, 'Модель': /картин/.test(does) ? '' : 'gpt-5' });
const DIRECT = [st('🎨', 'Художник', 'автор', 'да', 'картинка'), st('✍️', 'Писатель', 'автор', 'да', '3'), st('🏷️', 'Технический писатель', 'автор', 'да', '1, 2, 4')];
const WINDOW = [st('🖋', 'Редактор', 'автор', 'да', '1, 2, 4'), st('🎨', 'Художник', 'Редактор', 'авто', 'картинка'), st('✍️', 'Писатель', 'Редактор', 'авто', '3')];
const FACTORY = [st('🎨', 'Художник', '', 'авто', 'картинка'), st('✍️', 'Писатель', '', 'авто', '3'), st('🏷️', 'Технический писатель', '', 'авто', '1, 2, 4')];

const call = (name, args) => ({ output: [{ type: 'function_call', name, call_id: 'c_' + name, arguments: JSON.stringify(args) }] });
// (28.10) ответ этапа «двумя кармашками»: разговор + тексты пунктов
const kar = obj => ({ output: [{ type: 'message', content: [{ type: 'output_text', text: JSON.stringify({ message: '', items: [], agreed: [], reopen: [], ...obj }) }] }] });

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
const TR = { 'Pengui baked a pie.': 'Пингви испёк пирог.', 'светлее': 'brighter', 'убрать кота': 'remove the cat' };
async function turn(stages, row, inc, response, subResponse) {
  // ответ модели не задан — простой текстовый ответ (пустой ответ теперь — падение «Работы»)
  response = response || { output: [{ type: 'message', content: [{ type: 'output_text', text: 'ок' }] }] };
  const ctx = await context(stages, row, inc);
  const nodes = { 'Контекст проекта': ctx };
  nodes['Кто отвечает'] = (await run('Кто отвечает', { nodes }))[0];
  let req = null;
  if (nodes['Кто отвечает'].mode === 'model') {
    req = (await run('Готовим запрос этапу', { nodes }))[0];
    nodes['Готовим запрос этапу'] = req;
    nodes['Разбираем ответ этапа'] = (await run('Разбираем ответ этапа', { nodes, input: [response] }))[0];
    if (nodes['Разбираем ответ этапа'].action === 'delegate') {
      nodes['Готовим поручение'] = (await run('Готовим поручение', { nodes }))[0];
      nodes['OpenAI: поручение'] = subResponse;
    }
  }
  nodes['Итог хода: черновик'] = (await run('Итог хода: черновик', { nodes }))[0];
  const pv = (await run('Перевод для автора: что', { nodes }))[0];
  nodes['Перевод для автора: что'] = pv;
  if (pv.need) {
    // переводчик видит только готовый текст пункта; здесь — словарь TR, иначе «RU: текст»
    assert.ok(pv.requestBody.input[0].content.includes('JSON'), 'слово JSON — в самом запросе');
    const src = JSON.parse(pv.requestBody.input[0].content.replace(/^[^\n]*\n/, ''));
    const outMap = {};
    for (const k of Object.keys(src)) outMap[k] = TR[src[k]] || 'RU: ' + src[k];
    nodes['OpenAI: перевод для автора'] = turn.trFail ? { error: { message: 'timeout' } }
      : { output: [{ type: 'message', content: [{ type: 'output_text', text: JSON.stringify(outMap) }] }] };
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
  assert.ok(t.r.dallePrompt.endsWith('RU: Пингви на кухне печёт пирог'), 'художнику — перевод задания');
  assert.ok(t.r.chunks.join('').includes('По-английски:'), 'автор видит английское задание');
  assert.ok(t.nodes['Перевод для автора: что'].requestBody.instructions.includes('Пингви in English is always Pengui'), 'переводчик брифа знает имя (🌐)');
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
  assert.equal(t.next, 'edit'); assert.equal(t.r.revisionTargetImageUrl, 'U1'); assert.ok(t.r.revisionInstruction.startsWith('Рисованная иллюстрация.'), 'правка держит правила'); assert.ok(t.r.revisionInstruction.endsWith('Change only what is asked here: brighter'), 'художнику — по-английски');
  t = await turn(DIRECT, { ai_ImageVariants: V, ai_ImageUrl: 'U2' }, { text: 'правка 2: убрать кота' });
  assert.equal(t.next, 'edit'); assert.equal(t.r.revisionTargetImageUrl, 'U2'); assert.ok(t.r.revisionInstruction.startsWith('Рисованная иллюстрация.'), 'правка держит правила'); assert.ok(t.r.revisionInstruction.endsWith('Change only what is asked here: remove the cat'));
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
    // (28.10) один запрос художнику: все картинки по порядку (основа правки первой) и маска — в JSON
    const { wf } = require('./harness12.js');
    assert.ok(!wf.nodes.some(n => n.name.startsWith('gpt-image-2')), '24 узла ушли');
    const IT = { 'Итог хода': { imageModel: 'gpt-image-2', imageQuality: 'medium', imageSize: '1536x864', editRoles: 'R: ', drawRoles: 'D: ' } };
    const withMask = { ...o, hasMask: true, revisionInstruction: 'шторка', __binary: { image_2: { mimeType: 'image/png' }, image_0: { mimeType: 'image/jpeg' }, image_1: {}, mask: { mimeType: 'image/png' } } };
    const q = (await run('Запрос художнику: правка', { nodes: { ...IT, 'Что дальше?': { next: 'edit' } }, input: [withMask] }))[0];
    assert.equal(q.body.images.length, 3); assert.ok(q.body.images[0].image_url.startsWith('data:image/jpeg;base64,'), 'основа правки — первой');
    assert.ok(q.body.mask && q.body.prompt.startsWith('Edit the first image only inside the transparent area') && q.body.prompt.endsWith('R: шторка'));
    assert.equal(q.body.quality, 'medium'); assert.equal(q.body.size, '1536x864');
    const d = (await run('Запрос художнику: рисуем', { nodes: { ...IT, 'Что дальше?': { next: 'draw' } }, input: [{ dallePrompt: 'кухня', __binary: { image_0: {}, image_1: {} } }] }))[0];
    assert.equal(d.body.images.length, 2); assert.equal(d.body.prompt, 'D: кухня'); assert.ok(!d.body.mask);
    assert.equal(wf.connections['Это правка?'].main[0][0].node, 'Извлекаем картинку (C)');
    assert.equal(wf.connections['Это правка?'].main[1][0].node, 'Извлекаем картинку (B)');
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
    kar({ items: [{ n: 3, text: 'Pengui baked a pie.' }], message: 'Вот история.' }));
  assert.equal(t.plan.stageName, 'Писатель');
  assert.equal(t.req.requestBody.text.format.name, 'otvet', 'ответ — всегда два кармашка');
  assert.equal(t.req.requestBody.tool_choice, 'auto', 'код не заставляет и не разбирает её слов');
  assert.ok(!t.req.requestBody.tools.some(x => x.type === 'web_search'), 'интернета нет, пока его нет в «Справочник»');
  const ins = t.req.requestBody.instructions;
  assert.ok(ins.includes('Пиши просто.') && ins.includes('маленький взрослый') && ins.includes('Автор не любит сироп.'));
  assert.ok(!ins.includes('Название коротко.'), 'колонка 🏷️ Писателю не идёт');
  assert.ok(!ins.includes('только редактору') && !ins.includes('служебное') && !ins.includes('Рисованная'), 'чужие и служебные колонки не идут');
  assert.ok(ins.includes('3. Описание — история'));
  assert.ok(!t.req.requestBody.conversation, 'разговор у OpenAI не хранится');
  assert.ok(t.req.requestBody.input[0].content.some(c => c.image_url === 'U2'), 'писатель видит согласованную картинку');
  assert.ok(t.req.requestBody.input[0].content[0].text.includes('Картинка согласована (вариант 2)'));
  const toolNames = t.req.requestBody.tools.map(x => x.name).filter(Boolean);
  assert.deepEqual(toolNames, ['save_note'], 'кнопки «записать пункты» больше нет — пункты во втором кармашке');
  assert.ok(t.r.chunks[0].startsWith('✍️ <b>Писатель</b>: Вот история.'));
  assert.ok(t.r.chunks[0].includes('<b>3. Описание</b>\nPengui baked a pie.\n\n— Перевод для автора —\nПингви испёк пирог.') || t.r.chunks[0].includes('Pengui baked a pie. (Пингви испёк пирог.)'));
  assert.ok(!JSON.stringify(t.req.requestBody.tools).includes('"ru"'), 'этап больше не пишет перевод сам');
  assert.equal(t.next, 'none');
  let state = JSON.parse(t.r.editorState);
  assert.equal(state.items[3].ruOf, 'Pengui baked a pie.', 'перевод привязан к тексту, с которого сделан');
  assert.ok(!state.stages['✍'].conv && !state.stages['✍'].pending, 'ни разговора, ни висящего вызова');
  assert.equal(state.stages['✍'].log.length, 2, 'этап помнит: служебный старт и свой ответ');
  console.log('3 писатель: только ✍️-колонки, свой разговор, картинка OK');

  // ── 4. Автор согласовала описание → этап завершён → Технический писатель ──
  t = await turn(DIRECT, { ...APPROVED, sys_EditorState: t.r.editorState }, { text: 'отлично, согласовано' },
    kar({ agreed: [3], message: 'Спасибо!' }));
  assert.equal(t.plan.stageName, 'Писатель');
  assert.ok(!t.req.requestBody.conversation);
  assert.equal(t.req.requestBody.input[1].role, 'assistant', 'этап помнит свой прошлый ответ');
  assert.ok(t.req.requestBody.input[1].content[0].text.includes('Вот история.') && t.req.requestBody.input[1].content[0].text.includes('propose_items: пункты 3'));
  assert.equal(t.req.requestBody.input[t.req.requestBody.input.length - 1].role, 'user', 'последним — то, что автор написала сейчас');
  assert.ok(t.req.requestBody.input.slice(-1)[0].content.some(c => c.image_url === 'U2'), 'картинка видна и на этом ходу (истории у OpenAI нет)');
  assert.equal(t.next, 'next'); assert.equal(t.r.nextIcon, '🏷️');
  state = JSON.parse(t.r.editorState);
  console.log('4 описание согласовано → переход к следующему этапу OK');

  // памятка писателя → колонка со значком ✍️ и 📝
  let tn = await turn(DIRECT, { ...APPROVED, sys_EditorState: t.r.editorState }, { text: 'Писателю: запомни — без крошечных стаканчиков' },
    call('save_note', { notes: 'Автор не любит сироп. Стакан у щедрого фермера полный.', message: 'Запомнил.' }));
  assert.equal(tn.plan.stageName, 'Писатель');
  assert.equal(tn.r.note.key, '✍️📝_tmpl_WriterNotes');
  const pm = (await run('Памятка', { nodes: { 'Итог хода': tn.r } }))[0];
  assert.equal(pm['✍️📝_tmpl_WriterNotes'], 'Автор не любит сироп. Стакан у щедрого фермера полный.', 'модель прислала прежнее + новое — так и остаётся');
  // (22.10) памятка дописывается: прежние записи остаются
  {
    const ctxW = { ...tn.ctx, tmpl: { ...tn.ctx.tmpl, '✍️📝_tmpl_WriterNotes': '15.10 · P0 — paws, не hands' } };
    const nw = { ...tn.nodes, 'Контекст проекта': ctxW };
    const rw = (await run('Разбираем ответ этапа', { nodes: nw, input: [call('save_note', { notes: 'без крошечных стаканчиков', message: 'Запомнил.' })] }))[0];
    assert.ok(rw.note.text.startsWith('15.10 · P0 — paws, не hands\n') && rw.note.text.endsWith('\nбез крошечных стаканчиков'), 'старое + новое, ровно её словами, без даты');
    const rw2 = (await run('Разбираем ответ этапа', { nodes: nw, input: [call('save_note', { notes: 'paws, не hands', message: 'Ок.' })] }))[0];
    assert.equal(rw2.note.text, '15.10 · P0 — paws, не hands', 'повтор не дописывается');
  }
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
      { 'Семейство': 'Пар и дым', 'Эффект': 'дым', 'Механика': 'smoke', 'Строка для сборщика': 'дымок: x, y', 'Как размечать': 'кружок', 'Ручки': 'густота', 'Статус': 'готов', demo: 'густота 4', other: '', 'Слово': 'дымок', 'Значит': 'smoke' },
      { 'Семейство': 'Осадки', 'Эффект': 'снег', 'Механика': 'snow', 'Строка для сборщика': 'снег: область', 'Как размечать': 'заливка', 'Ручки': 'густота', 'Статус': 'пока не умеет', demo: '' },
      { 'Семейство': 'КАК ЧИТАТЬ ЛИСТ', 'Эффект': '', 'Механика': '', 'Слово': 'густота', 'Значит': 'density' }];
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
    n['Сервер: сетка'] = { ok: true, dataUrl: 'data:image/jpeg;base64,GRID' };
    const req = (await run('Готовим запрос этапу', { nodes: n }))[0];
    const imgs = req.requestBody.input[0].content.filter(c => c.type === 'input_image').map(c => c.image_url);
    assert.deepEqual(imgs, ['data:image/jpeg;base64,GRID'], 'аниматор видит картинку с сеткой');
    assert.equal(req.requestBody.text.format.name, 'otvet', 'пункт с превью — во втором кармашке, тогда придёт видео');
    assert.ok(!('seen' in req), 'картинки не «помнятся» — показываются каждый ход');
    assert.ok(req.requestBody.instructions.includes('КАТАЛОГ ЭФФЕКТОВ') && req.requestBody.instructions.includes('строка «дымок: x, y»')
      && req.requestBody.instructions.includes('на этом канале: густота 4') && req.requestBody.instructions.includes('на этом канале: не используется'),
      'аниматор видит каталог эффектов со столбцом своего канала');
    n['Готовим запрос этапу'] = req;
    n['Разбираем ответ этапа'] = (await run('Разбираем ответ этапа', { nodes: n, input: [call('propose_items', { items: [{ n: 9, text: 'дымок: 44, 37' }], message: 'Вот.' })] }))[0];
    // (28.10) без разговора у OpenAI: следующий ход видит картинку снова и помнит прошлый ответ; ошибка OpenAI — падение «Работы»
    {
      const nr = { ...n, 'Контекст проекта': { ...ctxA, row: { ...ctxA.row, sys_EditorState: n['Разбираем ответ этапа'].editorState } } };
      delete nr['Готовим запрос этапу']; delete nr['Разбираем ответ этапа'];
      const r1 = (await run('Готовим запрос этапу', { nodes: nr }))[0];
      const last = r1.requestBody.input[r1.requestBody.input.length - 1];
      assert.ok(last.content.some(c => c.type === 'input_image' && c.image_url === 'data:image/jpeg;base64,GRID'), 'картинка с сеткой — снова');
      assert.ok(r1.requestBody.input.some(i => i.role === 'assistant' && i.content[0].text.includes('Вот.')), 'помнит свой ответ');
      nr['Готовим запрос этапу'] = r1;
      let thrown = '';
      try { await run('Разбираем ответ этапа', { nodes: nr, input: [{ error: { message: 'Bad request - please check your parameters', description: 'Invalid image' } }] }); }
      catch (e) { thrown = String(e.message); }
      assert.ok(thrown.includes('Invalid image'), 'ошибка не превращается в «напишите ещё раз» — «Работа» падает, очередь разберётся');
      const many = { ...nr, 'Контекст проекта': { ...ctxA, row: { ...ctxA.row, ai_ImageVariants: JSON.stringify([1, 2, 3, 4].map(k => ({ n: k, url: 'V' + k }))) } } };
      delete many['Готовим запрос этапу'];
      const r2 = (await run('Готовим запрос этапу', { nodes: many }))[0];
      const urls = r2.requestBody.input.slice(-1)[0].content.filter(c => c.type === 'input_image').map(c => c.image_url);
      assert.ok(!urls.includes('V1') && !urls.includes('V2'), 'старые варианты не показываются (каждый ход одной цены)');
      let log = JSON.parse(n['Разбираем ответ этапа'].editorState);
      for (let k = 0; k < 8; k++) {
        const nk = { ...nr, 'Контекст проекта': { ...ctxA, row: { ...ctxA.row, sys_EditorState: JSON.stringify(log) } } };
        nk['Готовим запрос этапу'] = (await run('Готовим запрос этапу', { nodes: nk }))[0];
        log = JSON.parse((await run('Разбираем ответ этапа', { nodes: nk, input: [call('propose_items', { items: [{ n: 9, text: 'дымок: 44, 37' }], message: 'ход ' + k })] }))[0].editorState);
      }
      assert.ok(Object.values(log.stages).every(x => x.log.length <= 10), 'память этапа — не больше 10 реплик');
    }
    console.log('18 разговор без OpenAI: память 10, картинки каждый ход, ошибка — падение OK');
    // (22.10) готовый текст пункта от автора — пишет код, модель не зовём, превью нет, согласовано
    {
      const ctxM = { ...ctxA, kind: 'message', text: 'Пункт 9, добавь к тому, что уже есть (остальное не трогай):\nобложка Б: кадр 1 2 — 51 52, оверлей справа',
        row: { ...ctxA.row, fx_Effects: 'пар: 28, 50\nобложка Б: кадр 0 0 — 50 50, оверлей слева' } };
      const nd = { 'Контекст проекта': ctxM };
      nd['Кто отвечает'] = (await run('Кто отвечает', { nodes: nd }))[0];
      assert.equal(nd['Кто отвечает'].mode, 'direct', 'модель не нужна');
      assert.equal(nd['Кто отвечает'].directText, 'пар: 28, 50\nобложка Б: кадр 1 2 — 51 52, оверлей справа');
      const it = (await run('Итог хода: черновик', { nodes: nd }))[0];
      const stD = JSON.parse(it.editorState);
      assert.equal(stD.items[9].text, 'пар: 28, 50\nобложка Б: кадр 1 2 — 51 52, оверлей справа');
      assert.equal(stD.agreed[9], true, 'её строки — сразу согласовано');
      assert.equal(it.previewBody, null, 'превью не нужно');
      assert.equal(it.agreedFields.fx_Effects, 'пар: 28, 50\nобложка Б: кадр 1 2 — 51 52, оверлей справа', 'в колонку выпуска');
      const ex = { 'Контекст проекта': { ...ctxM, text: 'Пункт 9, запиши ровно так, без изменений:\nпар: 28, 50\nобложка Б: кадр 0 0 — 50 50, оверлей слева\nпузыри: 1, 2, 3' } };
      ex['Кто отвечает'] = (await run('Кто отвечает', { nodes: ex }))[0];
      assert.equal(ex['Кто отвечает'].mode, 'direct'); assert.equal(ex['Кто отвечает'].directText, 'пар: 28, 50\nобложка Б: кадр 0 0 — 50 50, оверлей слева\nпузыри: 1, 2, 3', 'всё старое на месте — пишем');
      // «запиши ровно так» без старых строк — не стирает молча, спрашивает
      const wipe = { 'Контекст проекта': { ...ctxM, text: 'Пункт 9, запиши ровно так, без изменений:\nобложка Б: кадр 3 3 — 50 50, оверлей справа' } };
      const pw = (await run('Кто отвечает', { nodes: wipe }))[0];
      assert.equal(pw.mode, 'say', 'пар пропал бы — не пишем');
      assert.ok(pw.sayText.includes('пар: 28, 50') && pw.sayText.includes('добавь'));
      const force = { 'Контекст проекта': { ...ctxM, text: 'Пункт 9, перепиши целиком:\nобложка Б: кадр 3 3 — 50 50, оверлей справа' } };
      const pf = (await run('Кто отвечает', { nodes: force }))[0];
      assert.equal(pf.mode, 'direct'); assert.equal(pf.directText, 'обложка Б: кадр 3 3 — 50 50, оверлей справа');
      const ch = { 'Контекст проекта': { ...ctxM, text: 'сделай пар погуще' } };
      assert.equal((await run('Кто отвечает', { nodes: ch }))[0].mode, 'model', 'обычная просьба — по-прежнему этапу');
    }
    console.log('20 готовый пункт — без модели OK');
    // (28.10) лупы нет: точки ставит автор на страничке разметки
    const r = (await run('Итог хода', { nodes: n }))[0];
    assert.equal(r.previewBody.fx_Effects, 'дымок: 44, 37'); assert.equal(r.previewBody.imageUrl, 'U2');
    assert.equal(r.previewBody.targetLUFS, '-14', 'вид эффектов — колонки 🎬');
    assert.deepEqual(r.previewBody.fxTable, [{ mech: 'smoke', knobs: 'густота 4' }], 'ручки эффектов канала — из листа «Эффекты»');
    assert.deepEqual(r.previewBody.fxWords, [{ word: 'дымок', means: 'smoke' }, { word: 'густота', means: 'density' }], 'словарик — колонки «Слово» / «Значит» листа «Эффекты»');
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
    assert.equal(rq.requestBody.text.format.name, 'otvet', 'по разметке — ответ кармашками');
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
    assert.equal(t9.req.requestBody.text.format.name, 'otvet');
    assert.ok(t9.r.previewBody && t9.r.previewBody.fx_Effects === 'свеча: 61, 41.9', 'без изменений — превью всё равно');
  }
  console.log('9e те же строки → превью OK');

  // ── 9g. Строки со страницы разметки: модель сама отметила «согласовано» — пункт не согласуется,
  // приходит превью, следующий этап не начинается; «ок» после превью — согласовано и в таблице ──
  {
    const ANIM2 = [DIRECT[0], { ...st('🎞️', 'Аниматор', 'автор', 'да', '9') }, DIRECT[1], DIRECT[2]];
    const IT9 = [...ITEMS, { 'Канал': 'demo', '№': '9', 'Пункт': 'Оживление', 'Колонки': 'fx_Effects', 'Можно пусто': 'да', 'Превью': 'оживление' }];
    const ROW = { ...APPROVED, sys_EditorState: JSON.stringify({ v: 2, items: { 9: { text: 'свеча: 61, 41.9' } }, agreed: { 9: false }, stages: {} }) };
    const t = await turn(ANIM2, ROW, { text: 'Пункт 9, запиши ровно так, без изменений:\nсвеча: 58, 83; раскачка 12', __items: IT9 },
      call('propose_items', { items: [{ n: 9, text: 'свеча: 58, 83; раскачка 12' }], agreed: [9], message: 'Записал.' }));
    // (22.10, её решение) строки со странички она уже видела в движении — пишет код, без модели и превью
    assert.equal(t.plan.mode, 'direct');
    assert.equal(JSON.parse(t.r.editorState).agreed[9], true, 'её строки — согласовано сразу');
    assert.equal(t.r.previewBody, null, 'превью не нужно');
    assert.equal(t.r.agreedFields.fx_Effects, 'свеча: 58, 83; раскачка 12', 'и сразу в таблице');
    assert.notEqual(t.r.transition, 'none', 'дальше — следующий этап');
  }
  console.log('9g строки со странички — записаны без модели OK');

  // ── 9f. Слово «пересобери» реплаем на выпуск = сборка без новой чистки ──
  {
    const mk = text => ({ message: { chat: { id: 1 }, from: { id: 1 }, text, reply_to_message: { text: 'ID: 20261006_142515_pengui' } } });
    for (const w of ['пересобери', 'Пересобери!', 'собери', 'Собрать', 'пересобрать', '🎬 Собрать с этими треками', 'Собрать с этими треками', 'собери с теми же треками', 'пересобери видео', '🎬️ собрать с чистыми треками!']) {
      const r = (await run('Разбираем входящее', { nodes: { 'Telegram Trigger': mk(w) } }))[0];
      assert.equal(r.kind, 'build', w); assert.equal(r.projectId, '20261006_142515_pengui');
    }
    for (const w of ['собери мне пожалуйста картинку по-другому', 'пересобери текст 3', 'привет', 'собрать с этими треками нельзя, сначала поправь пар']) {
      const r = (await run('Разбираем входящее', { nodes: { 'Telegram Trigger': mk(w) } }))[0];
      assert.equal(r.kind, 'message', w);
    }
    const l = (await run('Разбираем входящее', { nodes: { 'Telegram Trigger': mk('https://drive.google.com/file/d/1CQQwEcSM1TUOIzI1XyskHVK_-kiuBVeI/view') } }))[0];
    assert.equal(l.kind, 'tracks');
  }
  console.log('9f «пересобери» → build, обычные реплики и ссылка не задеты OK');

  // ── 9g. Ответ (reply) на сообщение этапа — адрес; «заново» — сброс этапа и следующих ──
  {
    const APP = { ai_ImageVariants: V, ai_ApprovedImageUrl: 'U2', sys_Status: 'Картинка согласована', ai_UserBrief: 'Пингви на кухне',
      ai_Description: 'old', ai_Title: 'old title' };
    const STATE = JSON.stringify({ v: 2,
      items: { 3: { text: 'Story', ru: 'История' }, 2: { text: 'Title', ru: '' } },
      agreed: { 3: false, 2: false },
      stages: { '✍': { conv: 'conv_w', pending: '', seen: [] }, '🏷': { conv: 'conv_t', pending: '', seen: [] } } });
    const row = { ...APP, sys_EditorState: STATE };
    // «согласовано» в ответ на сообщение художника — это не одобрение истории Писателя
    let r1 = await turn(DIRECT, row, { text: 'согласовано', replyText: '🎨 Художник: рисую 🎨\n\nID: P1' }, call('propose_items', { message: 'ok' }));
    assert.equal(r1.plan.stageName, 'Художник'); assert.deepEqual(r1.plan.approveNums || [], []);
    // «ок» в ответ на сообщение Писателя — одобряет его пункт
    r1 = await turn(DIRECT, row, { text: 'ок', replyText: '✍️ Писатель: вот история\n\nID: P1' }, call('propose_items', { message: 'ok' }));
    assert.equal(r1.plan.stageName, 'Писатель'); assert.deepEqual(r1.plan.approveNums, [3]);
    // картинка «Вариант N» — к этапу-художнику
    r1 = await turn(DIRECT, row, { text: 'светлее', replyVariant: 1, replyText: 'Вариант 1\nID: P1' });
    assert.equal(r1.plan.stageName, 'Художник');
    // «заново» без адреса и без ответа — вопрос, ничего не стираем
    r1 = await turn(DIRECT, row, { text: 'заново' });
    assert.equal(r1.plan.mode, 'say'); assert.ok(r1.r.chunks[0].includes('С какого этапа'));
    assert.equal(JSON.parse(r1.r.editorState).items[3].text, 'Story');
    // «заново» ответом на Писателя: Писатель и все следующие стёрты, согласование снято, колонки очищены, переход к старту
    r1 = await turn(DIRECT, row, { text: 'Заново!', replyText: '✍️ Писатель: вот история\n\nID: P1' });
    assert.equal(r1.plan.mode, 'reset'); assert.equal(r1.r.action, 'reset');
    let st = JSON.parse(r1.r.editorState);
    assert.deepEqual(Object.keys(st.items), []); assert.deepEqual(st.stages, {}); assert.equal(r1.r.transition, 'next');
    assert.equal(r1.r.clearApproved, false); assert.equal(r1.r.approvedUrl, '');
    assert.ok(r1.r.chunks[0].includes('✍️ <b>Писатель</b>: начинаем заново'));
    assert.equal(r1.r.agreedFields.ai_Title, ''); assert.equal(r1.r.agreedFields.ai_Description, '');
    assert.equal(r1.next, 'next');
    // то же словом-адресом
    r1 = await turn(DIRECT, row, { text: '✍️ с нуля' });
    assert.equal(r1.plan.mode, 'reset');
    // «заново» у художника: картинка-варианты остаются, согласование и задание сброшены, остальные этапы стёрты
    r1 = await turn(DIRECT, row, { text: 'Художник: заново' });
    assert.equal(r1.r.action, 'reset'); assert.equal(r1.r.clearApproved, true); assert.equal(r1.r.userBrief, '');
    assert.equal(r1.r.statusAfter, 'Картинка в работе'); assert.equal(r1.r.transition, 'next');
    assert.deepEqual(Object.keys(JSON.parse(r1.r.editorState).items), []);
    // опубликованный выпуск не трогаем
    r1 = await turn(DIRECT, { ...row, sys_Status: 'Опубликовано' }, { text: '✍️ заново' });
    assert.ok(r1.r.chunks[0].includes('опубликован')); assert.equal(JSON.parse(r1.r.editorState).items[3].text, 'Story');
    // обычные слова с «заново» внутри — не сброс
    r1 = await turn(DIRECT, row, { text: 'перепиши заново, но короче', replyText: '✍️ Писатель: вот история\n\nID: P1' }, call('propose_items', { message: 'ok' }));
    assert.equal(r1.plan.mode, 'model');
    // женский род и «я»: «Я согласовала» — чистое одобрение; длинная реплика с «согласовано» — нет
    for (const w of ['согласованно', 'Согласованно!', 'Я согласовала', 'согласовала', 'ну вот, согласовано', 'Одобряю', 'это ок']) {
      r1 = await turn(DIRECT, row, { text: w, replyText: '✍️ Писатель: вот история\n\nID: P1' }, call('propose_items', { message: 'ok' }));
      assert.deepEqual(r1.plan.approveNums, [3], w);
    }
    r1 = await turn(DIRECT, row, { text: 'согласовано, но убери последнюю фразу', replyText: '✍️ Писатель: вот история\n\nID: P1' }, call('propose_items', { message: 'ok' }));
    assert.deepEqual(r1.plan.approveNums, []);
    console.log('9g reply = адрес этапа, «заново» = сброс этапа и следующих OK');
  }

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

  // ── 12. Перевод для автора — только от переводчика и только с того текста, что ляжет в таблицу ──
  {
    const A = { ai_ImageVariants: V, ai_ApprovedImageUrl: 'U2', sys_Status: 'Картинка согласована', ai_UserBrief: 'Пингви на кухне' };
    // этап «переводит» пометки автора, а английский оставил прежним — автор видит честный перевод английского
    let u = await turn(DIRECT, A, { kind: 'stageStart', event: 'Картинка согласована (вариант 2).' },
      call('propose_items', { items: [{ n: 3, text: 'Old line with a cart.', ru: 'Новая строка без тележки.' }], message: 'Внёс правки.' }));
    assert.ok(u.r.chunks[0].includes('RU: Old line with a cart.') && !u.r.chunks[0].includes('без тележки'));
    // следующий ход, текст тот же — второй раз не переводим, перевод на месте
    const row2 = { ...A, sys_EditorState: u.r.editorState };
    let u2 = await turn(DIRECT, row2, { text: 'хорошо' }, call('propose_items', { items: [], message: 'Ок.' }));
    assert.equal(u2.nodes['Перевод для автора: что'].need, false);
    assert.equal(JSON.parse(u2.r.editorState).items[3].ru, 'RU: Old line with a cart.');
    // переводчик не ответил — так и пишем, старый перевод не показываем
    turn.trFail = true;
    let u3 = await turn(DIRECT, row2, { text: 'поправь' }, call('propose_items', { items: [{ n: 3, text: 'New line.' }], message: 'Готово.' }));
    turn.trFail = false;
    assert.ok(u3.r.chunks[0].includes('New line. (перевод не получен)'), u3.r.chunks[0]);
    assert.ok(u3.r.chunks[0].includes('⚠️ Перевод для автора: переводчик не ответил: timeout'));
    assert.ok(!u3.r.chunks[0].includes('Old line'));
  }
  console.log('12 перевод для автора — переводчиком, с текста для таблицы OK');

  // ── 14. Новый проект: одно сообщение, по кнопке на канал (подпись — колонка «Кнопка» Catalog) ──
  {
    const k = (await run('Кнопка на каждый канал', { nodes: { 'Разбираем входящее': { chatId: 7 } },
      input: [{ Channel: 'one', 'Кнопка': 'One' }, { Channel: 'two' }, { Channel: '' }] }));
    assert.equal(k.length, 1, 'одно сообщение');
    assert.deepEqual(k[0].body.reply_markup.inline_keyboard, [[{ text: 'One', callback_data: 'one' }], [{ text: 'two', callback_data: 'two' }]]);
  }
  console.log('14 новый проект: одно сообщение со всеми каналами OK');

  // ── 15. Чистка и пересборка раздельно (14.10) ──
  {
    const ctx = { chatId: 7, projectId: '20261012_092708_pengui', items: [] };
    const row = { sys_ProjectID: ctx.projectId, sys_Status: 'Утверждено', sys_AudioZipUrl: 'https://drive.google.com/uc?export=download&id=1wun3Im-LhqCR_Z_3R53fKis4aRd4brs5' };
    const b1 = (await run('Стена: проверяем таблицу', { nodes: { 'Контекст проекта': ctx }, input: [{ ...row, sys_CleanState: 'идёт' }] }))[0];
    assert.equal(b1.ok, false, 'пока чистка идёт — не собираем');
    assert.ok(b1.problemsText.startsWith('Чистка звука ещё идёт'));
    const b2 = (await run('Стена: проверяем таблицу', { nodes: { 'Контекст проекта': ctx }, input: [{ ...row, sys_CleanState: 'готово' }] }))[0];
    assert.ok(!/Сначала чистка/.test(b2.okText), 'нет ложного «сначала чистка»');
    const b3 = (await run('Стена: проверяем таблицу', { nodes: { 'Контекст проекта': ctx }, input: [{ ...row, ai_ApprovedImageUrl: 'U1', sys_Status: 'Опубликовано', sys_CleanState: 'готово' }] }))[0];
    assert.equal(b3.ok, true, '«пересобери» вышедшего выпуска — стена пропускает (статус вернётся в «Утверждено»)');
    const b4 = (await run('Стена: проверяем таблицу', { nodes: { 'Контекст проекта': ctx }, input: [{ ...row, ai_ApprovedImageUrl: 'U1', sys_Status: 'Картинка согласована', sys_CleanState: 'готово' }] }))[0];
    assert.equal(b4.ok, false, 'несогласованный — нет');
    const tmpl = { '🎬tmpl_CleanMode': 'duo', '🎬tmpl_CleanAlarmHours': '4' };
    const c1 = (await run('Чистка: нужна?', { nodes: { 'Контекст проекта': { ...ctx, tmpl, row: { ...row, sys_CleanState: 'готово' },
      tracksUrl: 'https://drive.google.com/uc?export=download&id=1wun3Im-LhqCR_Z_3R53fKis4aRd4brs5' } } }))[0];
    assert.equal(c1.need, false, 'ссылка на уже очищенный архив — без чистки');
    const c2 = (await run('Чистка: нужна?', { nodes: { 'Контекст проекта': { ...ctx, tmpl, row: { ...row, sys_CleanState: 'готово' },
      tracksUrl: 'https://drive.google.com/uc?export=download&id=1NEWzzzzzzzzzzzzzzzzzzzzzzzzzzz' } } }))[0];
    assert.equal(c2.need, true, 'новая ссылка — чистим');
    const c3 = (await run('Чистка: нужна?', { nodes: { 'Контекст проекта': { ...ctx, tmpl, row: { ...row, sys_CleanState: 'идёт',
      sys_CleanSource: 'https://drive.google.com/uc?export=download&id=1TteXvQ3jTt9uetKgKExw5GNceijPYBss' },
      tracksUrl: 'https://drive.google.com/uc?export=download&id=1TteXvQ3jTt9uetKgKExw5GNceijPYBss' } } }))[0];
    assert.equal(c3.need, false, 'та же ссылка уже чистится — второй чистки нет');
    const z = (await run('Чистка: запущена?', { nodes: { 'Контекст проекта': { ...ctx, row: { ...row, sys_CleanState: 'идёт', sys_CleanTag: 'T1', sys_CleanStarted: 'S1', sys_CleanSource: 'U1' } },
      'Чистка: нужна?': { mode: 'duo', alarmHours: 4, body: { tracksUrl: 'U2', cleanNotebook: 'NB' } } }, input: [{ ok: false, busy: true, error: 'Блокнот занят' }] }))[0];
    assert.equal(z.tag, 'T1'); assert.equal(z.state, 'идёт'); assert.equal(z.source, 'U1');
  }
  console.log('15 чистка и пересборка раздельно, без ложного «сначала чистка» OK');

  // ── 16. Метка выпуска и вход из календаря (14.10) ──
  {
    const st = (await run('Разбираем входящее', { nodes: { 'Из календаря': { body: { action: 'start', channel: 'pengui', calId: 'a1',
      title: 'Кот в книжном', about: 'Всемирный день кошек.', release: '2026-10-16' } } } }))[0];
    assert.equal(st.kind, 'channelPick'); assert.equal(st.channelKey, 'pengui'); assert.equal(st.chatId, 285577543); assert.equal(st.cal.id, 'a1');
    const pid = (await run('Генерируем ProjectID', { nodes: { 'Разбираем входящее': st }, input: [{ SheetName: 'S', 'Значок': '🐧' }] }))[0];
    assert.equal(pid.calId, 'a1');
    assert.ok(pid.createdText.startsWith('<b>🐧 16.10 · Кот в книжном</b>'), pid.createdText);
    assert.ok(pid.createdText.includes('Повод: Всемирный день кошек.') && pid.createdText.includes('ID: ' + pid.projectId));
    assert.ok(!/reply/.test(pid.createdText), 'без напоминания про реплай');
    const tr = (await run('Разбираем входящее', { nodes: { 'Из календаря': { body: { action: 'tracks', projectId: '20261012_092708_pengui',
      url: 'https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWxYz/view?usp=sharing' } } } }))[0];
    assert.equal(tr.kind, 'tracks'); assert.equal(tr.tracksUrl, 'https://drive.google.com/uc?export=download&id=1AbCdEfGhIjKlMnOpQrStUvWxYz');
    const bad = (await run('Разбираем входящее', { nodes: { 'Из календаря': { body: { action: 'tracks', projectId: 'x', url: 'y' } } } }))[0];
    assert.equal(bad.kind, 'unknown');
    // метка в контексте: из календаря, иначе значок и дата создания
    const base = { 'Разбираем входящее': { kind: 'message', projectId: '20261012_092708_pengui', channelKey: 'pengui', chatId: 7 },
      'Находим лист канала': { SheetName: 'S', 'Значок': '🐧' }, 'Читаем строку проекта': { sys_ProjectID: '20261012_092708_pengui' },
      'Читаем шаблоны канала': {}, 'Читаем этапы': [], 'Читаем пункты': [], 'Читаем эффекты': [] };
    const k1 = (await run('Контекст проекта', { nodes: { ...base, 'Читаем календарь (метка)': [{ project: '20261012_092708_pengui', release: '2026-10-16', title: 'Global Cat Day', title_ru: 'Кот в книжном' }] } }))[0];
    assert.equal(k1.label, '🐧 16.10 · Кот в книжном'); assert.equal(k1.labelLine, '<b>🐧 16.10 · Кот в книжном</b>\n');
    const k2 = (await run('Контекст проекта', { nodes: { ...base, 'Читаем календарь (метка)': [{}] } }))[0];
    assert.equal(k2.label, '🐧 выпуск от 12.10');
  }
  console.log('16 метка выпуска и вход из календаря OK');

  // ── 17. (28.10) Приёмная: конверт для очереди (повторы и порядок решает очередь на сервере) ──
  {
    const env = async (nodes) => (await run('Приёмная: конверт', { nodes }))[0];
    const cb = (id, mid) => ({ update_id: id, callback_query: { id: 'q' + id, data: 'final|20261012_092708_pengui', from: { id: 7 }, message: { message_id: mid, chat: { id: 7 } } } });
    const e1 = await env({ 'Telegram Trigger': cb(1, 55) }), e2 = await env({ 'Telegram Trigger': cb(2, 56) });
    assert.equal(e1.key, e2.key, 'та же кнопка — один ключ (второе нажатие — повтор)');
    assert.equal(e1.project, '20261012_092708_pengui'); assert.equal(e1.callbackId, 'q1'); assert.equal(e1.keep, 600);
    const m = await env({ 'Telegram Trigger': { update_id: 9, message: { message_id: 3, chat: { id: 7 }, text: 'светлее', reply_to_message: { text: 'Вариант 1\nID: 20261012_092708_pengui' } } } });
    assert.equal(m.key, 'upd:9'); assert.equal(m.project, '20261012_092708_pengui', 'выпуск — из сообщения, на которое ответила');
    assert.equal(m.messageId, 3, 'на сообщение автора — 👀');
    const inner = await env({ 'Вызов изнутри': { kind: 'stageStart', projectId: 'P7', chatId: 7 } });
    assert.equal(inner.source, 'inner'); assert.equal(inner.project, 'P7'); assert.ok(inner.key.startsWith('inner:P7:'));
    const cal = await env({ 'Из календаря': { body: { action: 'start', channel: 'pengui' } } });
    assert.equal(cal.source, 'cal'); assert.equal(cal.project, '');
    const dec = async (e, r) => (await run('Очередь: решение', { nodes: { 'Приёмная: конверт': e }, input: [r] }))[0].route;
    assert.equal(await dec(m, { run: true }), 'run');
    assert.equal(await dec(m, { dup: true }), 'quiet', 'повтор сообщения — молча');
    assert.equal(await dec(e1, { dup: true }), 'dupButton', 'повтор кнопки — «уже принято»');
    assert.equal(await dec(m, { queued: true }), 'quiet', 'выпуск занят — ждёт своей очереди, автор ничего не пишет заново');
    assert.equal(await dec(e1, { queued: true }), 'queuedButton');
    assert.equal(await dec(m, { error: { message: 'ECONNREFUSED' } }), 'run', 'сервер молчит — лучше лишний запуск, чем потерянное');
    const job = (await run('В работу', { nodes: { 'Очередь: решение': { ...m, route: 'run' } } }))[0];
    assert.equal(job.key, 'upd:9'); assert.equal(job.chatId, 7); assert.equal(job.quote, '«светлее»');
    // повтор и «следующее» приходят из очереди в том виде, в каком положены: { body: { source, body } } —
    // «Работа» должна получить то же, что и в первый раз (28.10: повтор принимал обёртку за календарь и молчал)
    const fromQueue = async (e) => (await run('В работу', { nodes: { 'Изнутри: что это?': { resume: { key: e.key, body: { source: e.source, body: e.body }, chatId: e.chatId, tries: 2 } } } }))[0];
    for (const e of [m, inner, cal, e1]) {
      const fresh = (await run('В работу', { nodes: { 'Очередь: решение': { ...e, route: 'run' } } }))[0];
      const again = await fromQueue(e);
      assert.equal(again.source, fresh.source, 'повтор — тот же источник: ' + e.source);
      assert.deepEqual(again.body, fresh.body, 'повтор — то же содержимое: ' + e.source);
      assert.equal(again.tries, 2);
      const z1 = (await run('Задание для работы', { nodes: { 'В работу': fresh } }))[0];
      const z2 = (await run('Задание для работы', { nodes: { 'В работу': again } }))[0];
      const k1 = (await run('Разбираем входящее', { nodes: { 'Вызов изнутри': z1 } }))[0];
      const k2 = (await run('Разбираем входящее', { nodes: { 'Вызов изнутри': z2 } }))[0];
      assert.equal(k2.kind, k1.kind, 'работа разбирает повтор так же, как первый раз: ' + k1.kind);
      assert.notEqual(k1.kind, 'unknown', 'и это не «непонятно»: ' + e.source);
    }
    assert.equal((await fromQueue(m)).quote, '«светлее»', 'в повторе видно, о чём сообщение');
  }
  console.log('17 приёмная: конверт, решение очереди OK');

  // ── 19. «Пункт 9, добавь / убери» (22.10) — к тому, что уже лежит в пункте, без переписывания ──
  {
    const lib = new Function(require('fs').readFileSync(require('path').join(__dirname, 'js', 'lib12.js'), 'utf8') + '; return { itMergeCommand };')();
    const items = [{ n: 9, cols: 'fx_Effects' }];
    const row = { fx_Effects: 'пар: 28, 50; густота 5\nпузыри: 74, 17, 14\nобложка Б: кадр 1 2 — 51 52, оверлей слева' };
    const st = { items: {} };
    const r1 = lib.itMergeCommand('Пункт 9, добавь к тому, что уже есть (остальное не трогай):\nобложка Б: кадр 3 4 — 53 54, оверлей справа\nобложка В: кадр 0 0 — 60 60, оверлей слева\nпар: 60, 40\nпузыри: 74, 17, 14', items, row, st);
    assert.equal(r1.text, 'пар: 28, 50; густота 5\nпузыри: 74, 17, 14\nобложка Б: кадр 3 4 — 53 54, оверлей справа\nобложка В: кадр 0 0 — 60 60, оверлей слева\nпар: 60, 40',
      'обложка Б заменилась, В и второй пар добавились, повтор пузырей не задвоился');
    const r2 = lib.itMergeCommand('Пункт 9, убери: пар', items, row, st);
    assert.equal(r2.text, 'пузыри: 74, 17, 14\nобложка Б: кадр 1 2 — 51 52, оверлей слева');
    assert.equal(lib.itMergeCommand('Пункт 9, запиши ровно так, без изменений:\nпар: 1, 2', items, row, st), null, 'полная запись — как раньше');
    const r3 = lib.itMergeCommand('пункт 9 добавь\nморгание: 86, 13', items, {}, { items: { 9: { text: 'пар: 1, 2' } } });
    assert.equal(r3.text, 'пар: 1, 2\nморгание: 86, 13', 'пусто в таблице — берём из состояния');
  }
  console.log('19 пункт: добавь / убери OK');

  // 21. (28.10) сбой «Работы»: что повторять молча, что сказать сразу
  {
    const job = { key: 'upd:9', chatId: 7, quote: '«светлее»' };
    const f = async err => (await run('Разбираем сбой', { nodes: { 'В работу': job }, input: [{ error: { message: err } }] }))[0];
    assert.equal((await f('ETIMEDOUT')).fatal, false, 'сеть — повторить');
    assert.equal((await f('429 Too Many Requests')).fatal, false);
    assert.equal((await f('insufficient_quota')).fatal, true, 'деньги — сразу');
    assert.equal((await f('invalid_grant: token has been expired')).fatal, true);
    const say = async (r, err) => (await run('Сбой: что сказать', { nodes: { 'Разбираем сбой': await f(err) }, input: [r] }))[0];
    assert.equal((await say({ notify: 'none' }, 'ETIMEDOUT')).say, false, 'первый сбой — молча');
    const s2 = await say({ notify: 'slow' }, 'ETIMEDOUT');
    assert.ok(s2.say && s2.text.includes('Повторю сама') && s2.text.includes('«светлее»'));
    const s3 = await say({ notify: 'fatal' }, 'insufficient_quota');
    assert.ok(s3.text.includes('OpenAI') && s3.text.includes('Billing'));
    const s4 = await say({ notify: 'final', next: { key: 'upd:10' } }, 'ETIMEDOUT');
    assert.ok(s4.text.includes('за 15 минут') && s4.next.key === 'upd:10', 'после «насовсем» очередь выпуска идёт дальше');
    const pv = await run('Повторы: список', { nodes: {}, input: [{ run: [{ key: 'a', body: {} }], final: [{ key: 'b', chatId: 7, body: { source: 'tg', body: { message: { text: 'x' } } }, error: 'timeout' }] }] });
    assert.equal(pv.length, 2); assert.ok(pv[0].resume); assert.ok(pv[1].text.includes('за 15 минут'));
  }
  {
    // бриф обогнал запуск этапа — художник не просит задание ещё раз
    let t = await turn(DIRECT, { ai_UserBrief: 'вечерний город' }, { kind: 'stageStart', event: 'Новый выпуск.' });
    assert.equal(t.plan.mode, 'none');
    t = await turn(DIRECT, {}, { kind: 'stageStart', event: 'Новый выпуск.' });
    assert.equal(t.plan.mode, 'say');
    // «Модель: нет» — без OpenAI, «добавь» пишет код
    const NOM = [st('🎨', 'Художник', 'автор', 'да', 'картинка'), { ...st('✍️', 'Писатель', 'автор', 'да', '3'), 'Модель': 'нет' }];
    const AP = { ai_UserBrief: 'сад', ai_ApprovedImageUrl: 'U1', ai_ImageVariants: '[{"n":1,"url":"U1"}]', sys_Status: 'Картинка согласована' };
    t = await turn(NOM, AP, { kind: 'stageStart', event: 'Картинка согласована.' });
    assert.equal(t.plan.mode, 'say'); assert.ok(/жду пункт 3/.test(t.plan.sayText), t.plan.sayText);
    t = await turn(NOM, AP, { kind: 'message', text: 'напиши историю' });
    assert.equal(t.plan.mode, 'say'); assert.equal(t.req, null, 'модель не звали');
    t = await turn(NOM, AP, { kind: 'message', text: 'Пункт 3, добавь: Pengui baked a pie.' });
    assert.equal(t.plan.mode, 'direct');
  }
  console.log('21 сбои: тихо, «сама повторю», сразу; тихий старт; этап без модели OK');

  // 22. (23.10) Пункт без этапа (оживление): автор пишет сама со странички в любой момент
  {
    const IT9 = [...ITEMS, { 'Канал': 'demo', '№': '9', 'Пункт': 'Оживление', 'Колонки': 'fx_Effects', 'Подсказка': '', 'Можно пусто': 'да' }];
    const TWO = [st('🎨', 'Художник', 'автор', 'да', 'картинка'), st('✍️', 'Писатель', 'автор', 'да', '1–4')];
    const AP = { ai_UserBrief: 'сад', ai_ApprovedImageUrl: 'U1', ai_ImageVariants: '[{"n":1,"url":"U1"}]', sys_Status: 'Картинка согласована' };
    const CMD = 'Пункт 9, добавь к тому, что уже есть (остальное не трогай):\nпар: 40, 50';
    let t = await turn(TWO, AP, { kind: 'message', text: CMD, __items: IT9 });
    assert.equal(t.plan.mode, 'direct', 'пока работает Писатель'); assert.equal(t.req, null);
    assert.equal(t.r.transition, 'none', 'Писатель ещё работает — сводки нет');
    assert.ok(/пар: 40, 50/.test(t.r.message || JSON.stringify(t.r)), 'записано');
    t = await turn(TWO, { ai_UserBrief: 'сад' }, { kind: 'message', text: CMD, __items: IT9 });
    assert.equal(t.plan.mode, 'direct', 'даже пока рисуется картинка — не уходит художнику');
    const DONE = { ...AP, sys_EditorState: JSON.stringify({ v: 2, items: { 1: { text: 'a' }, 2: { text: 'b' }, 3: { text: 'c' }, 4: { text: 'd' } }, agreed: { 1: true, 2: true, 3: true, 4: true } }) };
    t = await turn(TWO, DONE, { kind: 'message', text: CMD, __items: IT9 });
    assert.equal(t.plan.mode, 'direct', 'все этапы прошли');
    assert.equal(t.r.transition, 'summary', '(24.10) всё готово — сразу сводка с ✅');
    t = await turn(TWO, { ...DONE, sys_Status: 'Утверждено' }, { kind: 'message', text: CMD, __items: IT9 });
    assert.equal(t.r.transition, 'summary', 'утверждённый выпуск изменён — согласовать заново');
    t = await turn(TWO, AP, { kind: 'message', text: 'светлее', __items: IT9 });
    assert.notEqual(t.plan.mode, 'direct', 'обычная реплика — как раньше');
  }
  console.log('22 пункт автора без этапа OK');

  // 23. (23.10) Обводка без подписи: не рисуем, ждём слова; следующее сообщение — правка по этой обводке
  {
    const V = JSON.stringify([{ n: 1, url: 'U1' }, { n: 2, url: 'U2' }]);
    let t = await turn(DIRECT, { ai_ImageVariants: V, ai_ImageUrl: 'U2' }, { text: '', replyVariant: 1, photo: [{ file_id: 'S' }, { file_id: 'BIG' }] });
    assert.equal(t.plan.mode, 'say'); assert.ok(/вижу обводку/.test(t.plan.sayText)); assert.equal(t.next === 'edit', false, 'вслепую не рисуем');
    const st = JSON.parse(t.r.editorState);
    assert.equal(st.stages['🎨'].marks.photo[1].file_id, 'BIG');
    t = await turn(DIRECT, { ai_ImageVariants: V, ai_ImageUrl: 'U2', sys_EditorState: t.r.editorState }, { text: 'радио на подоконнике' });
    assert.equal(t.plan.mode, 'edit'); assert.equal(t.plan.needMask, true); assert.equal(t.plan.maskPhoto[1].file_id, 'BIG');
    assert.equal(t.r.revisionTargetImageUrl, 'U1', 'правится та картинка, на которую была обводка');
    assert.ok(!JSON.parse(t.r.editorState).stages['🎨'].marks, 'обводка использована');
    // через 30 минут обводка забыта — обычное задание
    const old = JSON.parse(t.r.editorState); old.stages['🎨'] = { marks: { photo: [{ file_id: 'X' }], variant: 1, at: Date.now() - 31 * 60 * 1000 } };
    t = await turn(DIRECT, { ai_ImageVariants: V, ai_ImageUrl: 'U2', sys_EditorState: JSON.stringify(old) }, { text: 'осенний сад' });
    assert.equal(t.plan.mode, 'draw');
  }
  console.log('23 обводка без подписи OK');

  // 24. (24.10) Тот же бриф второй раз не переводится
  {
    const TR2 = Object.assign(TR, { 'осенний сад': 'autumn garden' });
    let t = await turn(DIRECT, {}, { kind: 'message', text: 'осенний сад' });
    assert.ok(t.r.dallePrompt.endsWith('autumn garden'), 'первый раз — перевод');
    const st = JSON.parse(t.r.editorState);
    assert.equal(st.stages['🎨'].briefEn.en, 'autumn garden');
    t = await turn(DIRECT, { sys_EditorState: t.r.editorState }, { kind: 'message', text: 'осенний сад' });
    assert.equal(t.nodes['Перевод для автора: что'].need, false, 'модель не зовём');
    assert.ok(t.r.dallePrompt.endsWith('autumn garden'), 'готовый перевод');
    t = await turn(DIRECT, { sys_EditorState: t.r.editorState }, { kind: 'message', text: 'зимний сад' });
    assert.equal(t.nodes['Перевод для автора: что'].need, true, 'новый бриф — переводим');
  }
  console.log('24 перевод брифа не повторяется OK');

  // 25. (24.10) «предложи ещё» до пунктов — свободный ответ; таймкоды переводятся
  {
    const TWO = [st('🎨', 'Художник', 'автор', 'да', 'картинка'), st('✍️', 'Писатель', 'автор', 'да', '1–4')];
    const AP = { ai_UserBrief: 'сад', ai_ApprovedImageUrl: 'U1', ai_ImageVariants: '[{"n":1,"url":"U1"}]', sys_Status: 'Картинка согласована' };
    const txt = { output: [{ type: 'message', content: [{ type: 'output_text', text: 'Ещё зёрна' }] }] };
    // (28.10) какие бы слова она ни написала — форма ответа одна: разговор + тексты пунктов, без принуждения
    for (const [row, words] of [[AP, 'Предложи ещё'], [AP, 'Берём первое'], [AP, 'всё ужасно, переделай полностью']]) {
      const tt = await turn(TWO, row, { kind: 'message', text: words }, txt);
      assert.equal(tt.req.requestBody.tool_choice, 'auto', words);
      assert.equal(tt.req.requestBody.text.format.name, 'otvet', words);
      assert.ok(!tt.req.requestBody.input.slice(-1)[0].content.toString().includes('[Система: отвечай'), 'код ничего не дописывает от себя');
    }
    // зёрна — только разговор: в таблицу ничего не пишется
    let t = await turn(TWO, AP, { kind: 'message', text: 'Предложи ещё' }, kar({ message: 'Вот три новых зерна: …' }));
    assert.equal(t.r.action, 'chat'); assert.ok(t.r.chunks[0].includes('Вот три новых зерна'));
    assert.deepEqual(JSON.parse(t.r.editorState).items, {});
    // текст — во втором кармашке: пишется в таблицу (ждёт согласования) и идёт на перевод
    t = await turn(TWO, AP, { kind: 'message', text: 'Берём первое' }, kar({ message: 'Вот текст.', items: [{ n: 3, text: 'A quiet story.' }] }));
    assert.equal(JSON.parse(t.r.editorState).items[3].text, 'A quiet story.');
    assert.equal(t.nodes['Перевод для автора: что'].need, true, 'текст пункта — на перевод');
    // не-JSON (сбой формы) — показываем как разговор, ничего не теряем
    t = await turn(TWO, AP, { kind: 'message', text: 'Привет' }, txt);
    assert.ok(t.r.chunks[0].includes('Ещё зёрна'));
    const ST4 = { ...AP, sys_EditorState: JSON.stringify({ v: 2, items: { 4: { text: 'Bat Air Traffic' } }, agreed: {} }) };
    t = await turn(TWO, ST4, { kind: 'message', text: 'Пункт 4, добавь: x' });
    const pv = t.nodes['Перевод для автора: что'];
    assert.ok(pv.need && pv.requestBody.instructions.includes('Пингви in English is always Pengui'), 'переводчику — правила 🌐 из таблицы');
    assert.equal(pv.requestBody.reasoning.effort, 'minimal', 'усилие переводчика — tmpl_LightEffort из таблицы');
    assert.ok(!/music pieces|characters/.test(pv.requestBody.instructions), 'своих правил про имена и названия в коде нет (28.10: спорили с таблицей)');
  }
  console.log('25 «предложи ещё» и перевод таймкодов OK');

  // 26. (24.10) одновременные запуски: «блокнот занят» не трогает строку; затёртая чистка всё равно забирается; замок
  {
    const { wf } = require('./harness12.js');
    const ctxC = { projectId: 'P1', chatId: 1, kind: 'tracks', row: { sys_CleanState: '', sys_CleanTag: '' }, tmpl: {} };
    const prep = { body: { cleanNotebook: 'https://www.kaggle.com/code/u/n', tracksUrl: 'U' }, mode: 'duo', alarmHours: 3 };
    let z = (await run('Чистка: запущена?', { nodes: { 'Контекст проекта': ctxC, 'Чистка: нужна?': prep }, input: [{ ok: true, tag: 'P1-1' }] }))[0];
    assert.equal(z.write, true, 'запустилась — пишем');
    z = (await run('Чистка: запущена?', { nodes: { 'Контекст проекта': ctxC, 'Чистка: нужна?': prep }, input: [{ ok: false, busy: true, error: 'Блокнот занят' }] }))[0];
    assert.equal(z.write, false, 'вторая ссылка вплотную: «занят» — строку не трогаем (снимок мог устареть)');
    z = (await run('Чистка: запущена?', { nodes: { 'Контекст проекта': ctxC, 'Чистка: нужна?': prep }, input: [{ ok: false, error: 'нет ключа' }] }))[0];
    assert.equal(z.write, true, 'настоящая ошибка — записать, чтобы было видно');
    const start = { tag: 'P1-1', notebookUrl: 'N' };
    const dal = async fresh => (await run('Чистка: что дальше', { nodes: { 'Чистка: запущена?': start, 'Перечитываем строку (чистка)': fresh, 'Ждём стук Kaggle': { body: { tag: 'P1-1', ok: true } } } }))[0].action;
    assert.equal(await dal({ sys_CleanTag: 'P1-1', sys_CleanState: 'идёт' }), 'ask');
    assert.equal(await dal({ sys_CleanTag: '', sys_CleanState: 'ошибка: Блокнот занят' }), 'ask', 'строку затёрли — чистка всё равно наша, забираем');
    assert.equal(await dal({ sys_CleanTag: 'P1-2', sys_CleanState: 'идёт' }), 'stop', 'идёт новая чистка — старая молчит');
    assert.equal(await dal({ sys_CleanTag: 'P1-1', sys_CleanState: 'готово' }), 'stop', 'уже забрано');
    // (28.10) Приёмная: у «Работы» один конец — удалось → «сделано» (+ следующее выпуска), упало → разбор сбоя
    const cn = wf.connections;
    assert.equal(cn['Работа'].main[0][0].node, 'Очередь: сделано');
    assert.equal(cn['Работа'].main[1][0].node, 'Разбираем сбой');
    assert.equal(wf.nodes.find(n => n.name === 'Работа').alwaysOutputData, true, 'пустой конец «Работы» — всё равно «сделано»');
    assert.equal(cn['Telegram Trigger'].main[0][0].node, 'Это владелец бота?');
    assert.equal(cn['Это владелец бота?'].main[0][0].node, 'Приёмная: конверт');
    assert.ok(!wf.nodes.some(n => /Вахтёр|Замок|разговор/.test(n.name)), 'ни Вахтёра, ни Замка, ни узлов разговора');
    assert.ok(!wf.settings.errorWorkflow && wf.settings.saveDataSuccessExecution === 'none');
    assert.equal(cn['Очередь: отпускаем (Kaggle)'].main[0][0].node, 'Ждём стук Kaggle', 'долгое ожидание Kaggle — очередь отпущена до него');
    assert.ok(wf.nodes.filter(n => n.type === 'n8n-nodes-base.code').every(n => n.retryOnFail), 'код-узлы повторяются (без этого сбой исполнителя роняет запуск)');
  }
  console.log('26 одновременные запуски: чистка; приёмная; повторы OK');

  // 27. (28.10) ответ на сообщение этапа: первая строка — название выпуска, значок этапа — ниже
  {
    const lib = new Function(require('fs').readFileSync(require('path').join(__dirname, 'js', 'lib12.js'), 'utf8') + '\nreturn { stByReply };')();
    const SS = [{ icon: '🎨', name: 'Художник', picture: true }, { icon: '✍️', name: 'Писатель' }];
    assert.equal((lib.stByReply(SS, 'Сен-Санс · Пляска смерти\n✍️ Писатель: вот зёрна', null) || {}).name, 'Писатель');
    assert.equal((lib.stByReply(SS, '✍️ Писатель: текст', null) || {}).name, 'Писатель');
    assert.equal(lib.stByReply(SS, 'просто текст', null), null);
  }
  console.log('27 ответ на сообщение этапа под названием выпуска OK');
  // 28. (29.10) приложение «Оживление»: кнопка по слову, каталог из листа, файл, строки обратно в пункт оживления
  {
    const IT9 = [...ITEMS, { 'Канал': 'demo', '№': '9', 'Пункт': 'Оживление', 'Колонки': 'fx_Effects', 'Можно пусто': 'да', 'Превью': 'оживление' }];
    // слово «оживление» реплаем на выпуск → kind fxApp
    const tgm = { update_id: 77, message: { message_id: 5, chat: { id: 1 }, from: { id: 1 }, text: 'оживление',
      reply_to_message: { text: 'выпуск 20261004_120000_demo' } } };
    const rz = (await run('Разбираем входящее', { nodes: { 'Вызов изнутри': { work: { source: 'tg', body: tgm } } } }))[0];
    assert.equal(rz.kind, 'fxApp'); assert.equal(rz.projectId, '20261004_120000_demo');
    const ctxA = await context(DIRECT, { ...APPROVED, ai_ApprovedImageUrl: 'https://drive.google.com/file/d/IMG1/view' }, { kind: 'fxApp' });
    const kb = (await run('Оживление: кнопка', { nodes: { 'Контекст проекта': ctxA } }))[0].body;
    const url = kb.reply_markup.inline_keyboard[0][0].web_app.url;
    assert.ok(url.startsWith('https://n8n.example/webhook/ozh12-') && url.includes('f=ozhivlenie.html') && url.includes('p=P1'), url);
    assert.ok(decodeURIComponent(url).includes('img=https://lh3.googleusercontent.com/d/IMG1=s2000'), 'картинка — прямой ссылкой');
    assert.ok(decodeURIComponent(url).includes('submit=https://n8n.example/webhook/cal12-'), 'строки — во вход календаря');
    const noImg = await context(DIRECT, { sys_Status: 'Картинка в работе' }, { kind: 'fxApp' });
    assert.ok(!(await run('Оживление: кнопка', { nodes: { 'Контекст проекта': noImg } }))[0].body.reply_markup, 'без картинки — без кнопки');
    // каталог — из листа «Эффекты»
    const FXR = [{ 'Раздел': 'Анимация', 'Эффект': 'пар над кружкой', 'Механика': 'steam_cup', 'Строка для сборщика': 'пар: x, y', 'Ручки': 'густота — гуще', 'Статус': 'готов', demo: 'густота 5', 'Слово': 'пар', 'Значит': 'steam' },
                 { 'Раздел': '', 'Эффект': 'Ручки — любое число', 'Механика': '', 'Слово': 'овал*', 'Значит': 'oval' }];
    const kat = (await run('Оживление: каталог', { nodes: { 'Оживление: вход': { query: { catalog: '1', ch: 'demo' } } }, input: FXR }))[0];
    assert.equal(kat.effects.length, 1); assert.equal(kat.effects[0].value, 'густота 5'); assert.equal(kat.words.length, 2);
    // файл — только из /pages, без выхода наверх
    assert.equal((await run('Оживление: какой файл', { input: [{ query: {} }] }))[0].f, 'ozhivlenie.html');
    await assert.rejects(run('Оживление: какой файл', { input: [{ query: { f: '../app.py' } }] }));
    // строки из приложения → «пункт 9, перепиши целиком» → записано, превью придёт
    const cal = { source: 'cal', body: { body: { action: 'fx', projectId: '20261004_120000_demo', chatId: 1, mode: 'replace', lines: 'пар: 30, 60; овал 20 × 8' } } };
    const rf = (await run('Разбираем входящее', { nodes: { 'Вызов изнутри': { work: cal } } }))[0];
    assert.equal(rf.kind, 'message'); assert.equal(rf.fxApp.lines, 'пар: 30, 60; овал 20 × 8');
    const ANIM2 = [DIRECT[0], DIRECT[1]];
    const t = await turn(ANIM2, { ...APPROVED, sys_EditorState: JSON.stringify({ v: 2, items: { 9: { text: 'свеча: 1, 1' } }, agreed: {} }) },
      { kind: 'message', text: '', fxApp: rf.fxApp, __items: IT9 });
    assert.equal(t.plan.mode, 'direct'); assert.equal(t.plan.directN, 9);
    assert.equal(JSON.parse(t.r.editorState).items[9].text, 'пар: 30, 60; овал 20 × 8', 'перепиши целиком');
    assert.ok(t.r.previewBody && t.r.previewBody.fx_Effects === 'пар: 30, 60; овал 20 × 8', 'из приложения — превью приходит');
  }
  console.log('28 приложение «Оживление» OK');
  console.log('ALL OK');
})().catch(e => { console.error('FAIL', e); process.exit(1); });
