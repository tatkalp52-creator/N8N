const { run } = require('./harness');
const assert = require('assert');
const writerOut = t => ({ output: [{ type: 'message', content: [{ type: 'output_text', text: t }] }] });
// Ход редактора целиком: разбор ответа → (писатель, если заказан) → итог хода.
async function parseEd(c, story) {
  const b = (await run('Разбираем ответ редактора', c))[0];
  const nodes2 = { ...c.nodes, 'Разбираем ответ редактора': b, 'OpenAI: Писатель': story === undefined ? writerOut('STORY') : story };
  const inp = b.storyBrief ? [writerOut('ПЕРЕВОД')] : [b];
  return run('Парсим ответ редактора', { nodes: nodes2, input: inp });
}
(async () => {
  // ── 1. Разбор входящего
  let r = await run('Разбираем входящее', { nodes: { 'Telegram Trigger': { message: { chat: { id: 1 }, text: 'давай к описанию, картинка ок', reply_to_message: { text: 'Вариант 2\nID: 20260924_101010_pengui' } } } } });
  assert.equal(r[0].kind, 'message'); assert.equal(r[0].projectId, '20260924_101010_pengui');
  r = await run('Разбираем входящее', { nodes: { 'Telegram Trigger': { message: { chat: { id: 1 }, text: 'https://drive.google.com/file/d/ABC_1/view', reply_to_message: { text: 'ID: 20260924_101010_pengui' } } } } });
  assert.equal(r[0].kind, 'tracks'); assert.equal(r[0].tracksUrl, 'https://drive.google.com/uc?export=download&id=ABC_1');
  r = await run('Разбираем входящее', { nodes: { 'Telegram Trigger': { callback_query: { id: 'q', data: 'img|20260924_101010_pengui|3', message: { chat: { id: 1 } } } } } });
  assert.equal(r[0].kind, 'imgApprove'); assert.equal(r[0].variantNumber, 3);
  r = await run('Разбираем входящее', { nodes: { 'Telegram Trigger': { callback_query: { id: 'q', data: 'final|20260924_101010_pengui', message: { chat: { id: 1 } } } } } });
  assert.equal(r[0].kind, 'finalApprove');
  r = await run('Разбираем входящее', { nodes: { 'Telegram Trigger': { callback_query: { id: 'q', data: 'pengui', message: { chat: { id: 1 } } } } } });
  assert.equal(r[0].kind, 'channelPick');
  r = await run('Разбираем входящее', { nodes: { 'Telegram Trigger': { message: { chat: { id: 1 }, text: 'привет' } } } });
  assert.equal(r[0].kind, 'newStart');
  console.log('1 разбор OK');

  // ── 2. Ход редактора: предлагает все 8 пунктов
  const tmpl = { tmpl_Channel: 'pengui', '🖋_tmpl_SystemPrompt': '###КАРТИНКА###рисуй мило###/КАРТИНКА### ###ОПИСАНИЕ###тепло###/ОПИСАНИЕ###', '🎨_tmpl_StyleRefs': 'https://drive.google.com/file/d/STYLE/view\nhttps://drive.google.com/file/d/REF1/view\nпастель', '🖋🎨_tmpl_CharacterPassport': 'Pengui — пингвин', tmpl_TimecodeCount: '20' };
  const variants = [{ n: 1, url: 'U1', dallePrompt: 'p1' }, { n: 2, url: 'U2', dallePrompt: 'p2' }];
  let row = { sys_ProjectID: 'P', sys_Status: 'Картинка согласована', sys_ConversationId: 'conv_1', sys_PendingToolCallId: 'call_0', ai_ImageVariants: JSON.stringify(variants), ai_ApprovedImageUrl: 'U2', ai_ImageUrl: 'U2', sys_EditorState: '' };
  const ctx = { kind: 'message', projectId: 'P', chatId: 1, sheetName: 'Pengui', channelKey: 'pengui', row, tmpl, status: row.sys_Status, text: 'давай текст', photo: null };
  const vhod = (await run('Вход редактора', { nodes: { 'Контекст проекта': ctx } }))[0];
  assert.equal(vhod.status, 'Картинка согласована'); assert.equal(vhod.approvedUrl, 'U2');
  const kb = (await run('Собираем знания канала', { nodes: { 'Контекст проекта': ctx } }))[0];
  assert.equal(kb.timecodeCount, 20); assert.equal(kb.styleGuideUrl, 'https://lh3.googleusercontent.com/d/STYLE=s2000');
  assert.ok(kb.knowledgeText.includes('SystemPrompt (описание):\nтепло'));
  assert.ok(!kb.knowledgeText.includes('drive.google.com'));
  // роль референса — строка под его ссылкой; художнику уходит «Image N — роль»
  assert.equal(kb.referenceRolesDraw, 'Reference images: Image 2 — пастель.\n\n');
  assert.equal(kb.referenceRolesEdit, 'Reference images: Image 3 — пастель.\n\n', 'в правке первая картинка — сама правка');
  assert.equal(kb.imageModel, 'gpt-image-2', 'без колонки — прежняя модель');
  const kb2 = (await run('Собираем знания канала', { nodes: { 'Контекст проекта': { ...ctx, tmpl: { ...tmpl, tmpl_ImageModel: 'gpt-image-2.5-sunburst' } } } }))[0];
  assert.equal(kb2.imageModel, 'gpt-image-2.5-sunburst');
  const nodes = { 'Контекст проекта': ctx, 'Вход редактора': vhod, 'Собираем знания канала': kb };
  let prep = (await run('Готовим запрос редактору', { nodes }))[0];
  const body = prep.requestBody;
  assert.equal(body.conversation, 'conv_1');
  assert.equal(body.input[0].type, 'function_call_output');
  assert.ok(body.instructions.includes('Картинка: согласована (вариант 2)'));
  assert.ok(body.instructions.includes('Нужное число тайм-кодов (из таблицы): 20'));
  const imgs = body.input[1].content.filter(c => c.type === 'input_image').map(c => c.image_url);
  assert.deepEqual(imgs, ['https://lh3.googleusercontent.com/d/STYLE=s2000', 'https://lh3.googleusercontent.com/d/REF1=s2000', 'U1', 'U2']);
  nodes['Готовим запрос редактору'] = prep;
  const tc = Array.from({ length: 20 }, (_, i) => 'Name ' + (i + 1));
  const call = (name, args) => ({ output: [{ type: 'function_call', call_id: 'call_1', name, arguments: JSON.stringify(args) }] });
  let p = (await parseEd({ nodes, input: [call('update_text_block', { items: { overlayText: 'Just Love', overlayPosition: 'Right', title: 'Pengui writes a love note', description: 'Пингви пишет записку…', timecodes: tc, footer: 'Music by X\n\n[Timecodes]\n\nSubscribe!', hashtags: '#lofi', tags: 'lofi, jazz', pinnedComment: '-' }, messageToUser: 'Вот первый вариант!' })] }))[0];
  assert.equal(p.action, 'text_block'); assert.equal(p.allAgreed, false); assert.deepEqual(p.changedItems, [1, 2, 4, 5, 6, 7, 8], 'описание Редактор не пишет');
  assert.equal(JSON.parse(p.editorState).items.description, '');
  assert.equal(p.statusAfter, 'Картинка согласована');
  let st = JSON.parse(p.editorState);
  assert.equal(st.items.overlayPosition, 'right'); assert.equal(st.items.pinnedComment, ''); assert.equal(st.set[8], true);
  assert.equal(st.seenImages.length, 4);
  nodes['Парсим ответ редактора'] = p;
  let blk = await run('Собираем текстовый блок', { nodes });
  const txt = blk.map(b => b.text).join('');
  assert.ok(txt.includes('ждут согласования: 1, 2, 3, 4, 5, 6, 7, 8'));
  assert.ok(txt.includes('<b>8. Закреплённый комментарий</b>\n— без закреплённого комментария'));
  assert.ok(txt.includes('Just Love — справа'));
  console.log('2 первое предложение OK');

  // ── 3. Следующий ход: автор согласовала 1,2,4,5,8; правка описания
  row = { ...row, sys_EditorState: p.editorState, sys_PendingToolCallId: 'call_1' };
  ctx.row = row;
  prep = (await run('Готовим запрос редактору', { nodes: { ...nodes, 'Контекст проекта': ctx } }))[0];
  assert.equal(prep.requestBody.input[1].content, 'давай текст', 'картинки повторно не прикладываются');
  nodes['Готовим запрос редактору'] = prep;
  p = (await parseEd({ nodes, input: [call('update_text_block', { items: { title: '' }, agreedItems: [1, 2, 4, 5, 8], messageToUser: 'Ок' })] }))[0];
  row = { ...row, sys_EditorState: p.editorState, sys_PendingToolCallId: 'call_1' };
  ctx.row = row;
  // Описание заказывается писателю: он получает только правила ОПИСАНИЯ, мир героя и задание
  const b3 = (await run('Разбираем ответ редактора', { nodes: { ...nodes, 'Контекст проекта': ctx }, input: [call('commission_story', { storyBrief: 'Пингви пишет записку соседу', messageToUser: 'Заказала писателю' })] }))[0];
  assert.equal(b3.action, 'text_block'); assert.equal(b3.storyBrief, 'Пингви пишет записку соседу');
  const wr = (await run('Готовим задание писателю', { nodes: { ...nodes, 'Контекст проекта': ctx, 'Разбираем ответ редактора': b3 } }))[0].requestBody;
  assert.equal(wr.reasoning.effort, 'high');
  assert.ok(wr.instructions.includes('ПРАВИЛА ОПИСАНИЯ:\nтепло'));
  assert.ok(wr.instructions.includes('Pengui — пингвин'));
  assert.ok(!wr.instructions.includes('рисуй мило'), 'правила картинки писателю не нужны');
  assert.ok(wr.input[0].content[0].text.includes('Пингви пишет записку соседу'));
  assert.ok(!wr.input[0].content[0].text.includes('Прежний текст'), 'без похвалы прежний текст писатель не видит');
  assert.equal(wr.input[0].content[2].image_url, 'U2', 'писатель видит согласованную картинку');
  p = (await parseEd({ nodes: { ...nodes, 'Контекст проекта': ctx }, input: [call('commission_story', { storyBrief: 'Пингви пишет записку соседу', messageToUser: 'Заказала писателю' })] }, writerOut('New story')))[0];
  st = JSON.parse(p.editorState);
  assert.equal(st.items.description, 'New story', 'оригинал писателя');
  assert.equal(st.ru.description, 'ПЕРЕВОД', 'автору — перевод рядом');
  assert.deepEqual(p.changedItems, [3]);
  // писатель не ответил — описание не трогаем, автору говорим
  const pf = (await parseEd({ nodes: { ...nodes, 'Контекст проекта': ctx }, input: [call('commission_story', { storyBrief: 'x', messageToUser: 'Заказала' })] }, { error: 'timeout' }))[0];
  assert.ok(pf.messageToUser.includes('Писатель не прислал описание'));
  assert.equal(JSON.parse(pf.editorState).items.description, '');
  assert.equal(st.items.title, 'Pengui writes a love note', 'пустая строка не стирает пункт');
  assert.deepEqual(Object.keys(st.agreed).filter(k => st.agreed[k]).map(Number), [1, 2, 4, 5, 8]);
  nodes['Парсим ответ редактора'] = p;
  blk = await run('Собираем текстовый блок', { nodes });
  const txt2 = blk.map(b => b.text).join('');
  assert.ok(txt2.includes('ждут согласования: 3, 6, 7'));
  assert.ok(txt2.includes('✔️ Согласовано: 1 Оверлей, 2 Название, 4 Тайм-коды, 5 Подвал, 8 Закреплённый комментарий'));
  assert.ok(!txt2.includes('Name 5'), 'согласованные тайм-коды не повторяем');
  console.log('3 частичное согласование OK');

  // ── 4. Всё согласовано → перевод → сводка
  row = { ...row, sys_EditorState: p.editorState };
  ctx.row = row;
  p = (await parseEd({ nodes: { ...nodes, 'Контекст проекта': ctx }, input: [call('update_text_block', { agreedItems: [3, 6, 7], messageToUser: 'Ура!' })] }))[0];
  assert.equal(p.allAgreed, true);
  nodes['Парсим ответ редактора'] = p;
  blk = await run('Собираем текстовый блок', { nodes });
  assert.equal(blk[0].allAgreed, true); assert.equal(blk[0].originalReady, true, 'оригинал уже есть — обратно не переводим');
  assert.ok(blk[0].translateBody.input[0].content.includes('на русский')); assert.equal(blk[0].translateBody.input[1].content, 'New story');
  nodes['Собираем текстовый блок'] = blk[0];
  const sv = (await run('Сводка на утверждение', { nodes, input: [{ output: [{ type: 'message', content: [{ type: 'output_text', text: 'Свежий перевод' }] }] }] }))[0];
  const svText = sv.chunks.join('\n');
  assert.ok(svText.includes('(так уйдёт на YouTube)</i>\nNew story'));
  assert.ok(svText.includes('— Перевод для автора —\nСвежий перевод'));
  const st4 = JSON.parse(sv.editorState);
  assert.equal(st4.descriptionEN, 'New story'); assert.equal(st4.descriptionENFor, 'New story');
  nodes['Сводка на утверждение'] = sv;
  const kn = (await run('Одно сообщение с кнопкой', { nodes }))[0];
  assert.equal(kn.callbackData, 'final|P');
  console.log('4 сводка OK');

  // ── 5. Финальная кнопка → пакет → проверка перечитанной строки
  const rowF = { ...row, sys_EditorState: sv.editorState };
  const ctxF = { ...ctx, kind: 'finalApprove', row: rowF };
  const pk = (await run('Собираем пакет для таблицы', { nodes: { 'Контекст проекта': ctxF } }))[0];
  assert.equal(pk.ok, true, pk.problemsText);
  assert.equal(pk.fields.ai_Description, 'New story\n\nMusic by X\n\n[Timecodes]\n\nSubscribe!');
  assert.equal(pk.fields.ai_PinnedComment, '');
  assert.equal(pk.fields.ai_TimecodeNames.split('\n').length, 20);
  const fresh = { ...rowF, ...pk.fields };
  let chk = (await run('Проверяем таблицу (финал)', { nodes: { 'Контекст проекта': ctxF }, input: [fresh] }))[0];
  assert.equal(chk.ok, true, chk.problemsText); assert.equal(chk.hasTracks, false);
  // пустой заголовок в таблице → не утверждаем
  chk = (await run('Проверяем таблицу (финал)', { nodes: { 'Контекст проекта': ctxF }, input: [{ ...fresh, ai_Title: '' }] }))[0];
  assert.equal(chk.ok, false); assert.ok(chk.problemsText.includes('ai_Title'));
  // описание изменили после сводки → перевод устарел
  const stale = JSON.parse(sv.editorState); stale.items.description = 'другое';
  const pk2 = (await run('Собираем пакет для таблицы', { nodes: { 'Контекст проекта': { ...ctxF, row: { ...rowF, sys_EditorState: JSON.stringify(stale) } } } }))[0];
  assert.equal(pk2.ok, false); assert.ok(pk2.problemsText.includes('перевод описания устарел'));
  // летопись: после утверждения дописываем строки о выпуске
  const ctxL = { ...ctxF, projectId: '20260926_175112_pengui', tmpl: { ...ctxF.tmpl, '🖋_tmpl_Chronicle': '12.09.2026\nПёк печенье с предсказаниями.' } };
  const lz = (await run('Готовим запись в летопись', { nodes: { 'Контекст проекта': ctxL } }))[0];
  assert.equal(lz.date, '26.09.2026'); assert.ok(lz.requestBody.input[1].content.includes('Пёк печенье'));
  const li = (await run('Дописываем летопись', { nodes: { 'Готовим запись в летопись': lz }, input: [writerOut('Отнёс печенье соседу в вязаной шапке.')] }))[0];
  assert.equal(li.ok, true);
  assert.equal(li.chronicle, '12.09.2026\nПёк печенье с предсказаниями.\n\n26.09.2026\nОтнёс печенье соседу в вязаной шапке.');
  const lf = (await run('Дописываем летопись', { nodes: { 'Готовим запись в летопись': lz }, input: [{ error: 'x' }] }))[0];
  assert.equal(lf.ok, false, 'сбой летописи не ломает утверждение');
  console.log('5 финальная кнопка OK');

  // ── 6. Стена перед сборщиком
  let w = (await run('Стена: проверяем таблицу', { nodes: { 'Контекст проекта': ctxF }, input: [{ ...fresh, sys_Status: 'Утверждено', sys_AudioZipUrl: 'https://x' }] }))[0];
  assert.equal(w.ok, true);
  w = (await run('Стена: проверяем таблицу', { nodes: { 'Контекст проекта': ctxF }, input: [{ ...fresh, sys_Status: 'Утверждено', sys_AudioZipUrl: '' }] }))[0];
  assert.equal(w.ok, false); assert.ok(w.problemsText.includes('sys_AudioZipUrl'));
  w = (await run('Стена: проверяем таблицу', { nodes: { 'Контекст проекта': ctxF }, input: [{ ...fresh, sys_Status: 'Картинка согласована', sys_AudioZipUrl: 'https://x' }] }))[0];
  assert.equal(w.ok, false);
  console.log('6 стена OK');

  // ── 7. Правка после Утверждено снимает статус; кнопка картинки
  const ctxU = { ...ctx, row: { ...rowF, sys_Status: 'Утверждено' }, status: 'Утверждено' };
  const vU = (await run('Вход редактора', { nodes: { 'Контекст проекта': ctxU } }))[0];
  const nU = { 'Контекст проекта': ctxU, 'Вход редактора': vU, 'Собираем знания канала': kb, 'Готовим запрос редактору': prep };
  p = (await parseEd({ nodes: nU, input: [call('update_text_block', { items: { tags: 'new, tags' }, messageToUser: 'ок' })] }))[0];
  assert.equal(p.statusAfter, 'Картинка согласована'); assert.equal(p.statusReverted, true);
  p = (await parseEd({ nodes: nU, input: [{ output: [{ type: 'message', content: [{ type: 'output_text', text: 'просто болтаем' }] }] }] }))[0];
  assert.equal(p.statusAfter, 'Утверждено'); assert.equal(p.action, 'chat');
  // кнопка "✅" под вариантом 1, когда было Утверждено с вариантом 2
  const ctxB = { ...ctxU, kind: 'imgApprove', variantNumber: 1 };
  const sb = (await run('Согласуем вариант', { nodes: { 'Контекст проекта': ctxB } }))[0];
  assert.equal(sb.ok, true); assert.equal(sb.approvedUrl, 'U1'); assert.equal(sb.statusAfter, 'Картинка согласована');
  const vB = (await run('Вход редактора', { nodes: { 'Контекст проекта': ctxB, 'Согласуем вариант': sb } }))[0];
  assert.equal(vB.status, 'Картинка согласована'); assert.equal(vB.approvedUrl, 'U1'); assert.equal(vB.fromButton, true);
  // редактор после кнопки просто ответил текстом — статус НЕ возвращается в Утверждено
  p = (await parseEd({ nodes: { ...nU, 'Контекст проекта': ctxB, 'Вход редактора': vB }, input: [{ output: [{ type: 'message', content: [{ type: 'output_text', text: 'ура' }] }] }] }))[0];
  assert.equal(p.statusAfter, 'Картинка согласована');
  // кнопка → Редактор согласует и СРАЗУ присылает все 8 пунктов
  const ctxB2 = { ...ctxB, row: { ...ctxB.row, sys_EditorState: '' } };
  p = (await parseEd({ nodes: { ...nU, 'Контекст проекта': ctxB2, 'Вход редактора': vB }, input: [call('approve_image', { variantNumber: 1, messageToUser: 'Ура, вот текст', items: { overlayText: 'Just Mail', overlayPosition: 'left', title: 'T', timecodes: ['a','b'], footer: '[Timecodes]\nF', hashtags: '#h', tags: 't', pinnedComment: '-' }, storyBrief: 'про почту' })] }))[0];
  assert.equal(JSON.parse(p.editorState).items.description, 'STORY', 'описание от писателя');
  assert.equal(p.action, 'approved'); assert.equal(p.resolvedApprovedImageUrl, 'U1'); assert.equal(p.textBlockTouched, true);
  assert.equal(JSON.parse(p.editorState).items.title, 'T');
  let bl = await run('Собираем текстовый блок', { nodes: { ...nodes, 'Парсим ответ редактора': p } });
  let bt = bl.map(x => x.text).join('');
  assert.ok(!bt.includes('✅ Картинка согласована'), 'после кнопки не дублируем ✅');
  assert.ok(bt.includes('ждут согласования: 1, 2, 3, 4, 5, 6, 7, 8'), 'блок пришёл сразу');
  // описание уже согласовано → новая картинка его не переписывает
  {
    const agreedSt = { items: { description: 'OLD' }, set: { 3: true }, agreed: { 3: true } };
    const ctxK = { ...ctxB, row: { ...ctxB.row, sys_EditorState: JSON.stringify(agreedSt) } };
    const pk = (await parseEd({ nodes: { ...nU, 'Контекст проекта': ctxK, 'Вход редактора': vB }, input: [call('approve_image', { variantNumber: 1, messageToUser: 'Ок', storyBrief: 'про новую картинку' })] }))[0];
    assert.equal(pk.storyBrief, '', 'писатель не вызывается');
    assert.equal(JSON.parse(pk.editorState).items.description, 'OLD', 'согласованное описание на месте');
    assert.ok(pk.messageToUser.includes('«3: перепиши»'));
  }
  // согласование словами → ✅ и блок одним сообщением
  p = (await parseEd({ nodes: { ...nU, 'Контекст проекта': { ...ctxU, row: { ...ctxU.row, sys_EditorState: '' } } }, input: [call('approve_image', { variantNumber: 2, messageToUser: 'Супер', items: { title: 'T2' } })] }))[0];
  bl = await run('Собираем текстовый блок', { nodes: { ...nodes, 'Парсим ответ редактора': p } });
  bt = bl.map(x => x.text).join('');
  assert.ok(bt.startsWith('✅ Картинка согласована (вариант 2).'), bt.slice(0, 80));
  assert.ok(bt.includes('<b>2. Название</b>\nT2'));
  // согласовал без пунктов — просто подтверждение, без пустого блока
  p = (await parseEd({ nodes: nU, input: [call('approve_image', { variantNumber: 2, messageToUser: 'Супер' })] }))[0];
  bl = await run('Собираем текстовый блок', { nodes: { ...nodes, 'Парсим ответ редактора': p } });
  assert.ok(!bl[0].text.includes('Текстовый блок'));
  console.log('7 статусы и кнопка картинки OK');

  // ── 8. Рисование / правка варианта
  p = (await parseEd({ nodes: nU, input: [call('request_revision', { variantNumber: 1, isNewVariant: false, revisionInstruction: 'add hat', preserveDetails: 'the mug', messageToUser: 'Поправляю' })] }))[0];
  assert.equal(p.action, 'revise_point'); assert.equal(p.revisionTargetImageUrl, 'U1'); assert.equal(p.revisionInstruction, 'add hat', 'художнику уходит ровно текст правки');
  assert.equal(p.revisionIsNewVariant, true, 'правка всегда сохраняется новым вариантом');
  p = (await parseEd({ nodes: nU, input: [call('start_drawing', { dallePrompt: 'scene', messageToUser: 'Рисую!' })] }))[0];
  assert.equal(p.action, 'ready_to_draw'); assert.equal(p.styleGuideUrl, kb.styleGuideUrl);
  console.log('8 рисование OK');
  // ── 9. Русский перевод: виден автору, но не уходит в таблицу/YouTube
  p = (await parseEd({ nodes: { ...nU, 'Контекст проекта': { ...ctxU, status: 'Картинка согласована', row: { ...ctxU.row, sys_Status: 'Картинка согласована', sys_EditorState: '' } }, 'Вход редактора': { ...vU, status: 'Картинка согласована' } }, input: [call('update_text_block', { items: { overlayText: 'Just Warm', overlayPosition: 'left', title: 'Lofi Jazz | Reimagining Elgar', timecodes: ['Tiptoe Reach', 'Steam and Ink'], pinnedComment: 'Write one line' }, ruTranslations: { overlayText: 'Просто тепло', title: 'Лоуфай-джаз | Элгар по-новому', timecodes: ['На цыпочках', 'Пар и чернила'], pinnedComment: 'Напишите одну строку' }, messageToUser: 'Вот' })] }))[0];
  let stR = JSON.parse(p.editorState);
  assert.equal(stR.items.title, 'Lofi Jazz | Reimagining Elgar', 'в самом пункте — только английский');
  nodes['Парсим ответ редактора'] = p;
  let bR = (await run('Собираем текстовый блок', { nodes })).map(x => x.text).join('');
  assert.ok(bR.includes('Just Warm (Просто тепло) — слева'), bR);
  assert.ok(bR.includes('Lofi Jazz | Reimagining Elgar (Лоуфай-джаз | Элгар по-новому)'));
  assert.ok(bR.includes('1. Tiptoe Reach (На цыпочках)'));
  assert.ok(bR.includes('Write one line\n(Напишите одну строку)'));
  // правка названия без перевода — старый перевод убирается
  const ctxR = { ...ctxU, status: 'Картинка согласована', row: { ...ctxU.row, sys_Status: 'Картинка согласована', sys_EditorState: p.editorState } };
  p = (await parseEd({ nodes: { ...nU, 'Контекст проекта': ctxR, 'Вход редактора': { ...vU, status: 'Картинка согласована' } }, input: [call('update_text_block', { items: { title: 'New Title' }, messageToUser: 'ок' })] }))[0];
  stR = JSON.parse(p.editorState);
  assert.equal(stR.ru.title, undefined); assert.equal(stR.ru.overlayText, 'Просто тепло');
  // финальный пакет — без переводов
  const allSt = JSON.parse(p.editorState); [1,2,3,4,5,6,7,8].forEach(n => { allSt.set[n] = true; allSt.agreed[n] = true; });
  allSt.items.description = 'Д'; allSt.items.footer = '[Timecodes]\nF'; allSt.descriptionEN = 'D'; allSt.descriptionENFor = 'Д';
  const pkR = (await run('Собираем пакет для таблицы', { nodes: { 'Контекст проекта': { ...ctxF, row: { ...rowF, sys_EditorState: JSON.stringify(allSt) } } } }))[0];
  assert.equal(pkR.fields.ai_OverlayText, 'Just Warm'); assert.equal(pkR.fields.ai_TimecodeNames, 'Tiptoe Reach\nSteam and Ink'); assert.equal(pkR.fields.ai_PinnedComment, 'Write one line');
  console.log('9 перевод для автора OK');
  // ── 10. «Художнику: …» — напрямую, без Редактора
  {
    const vs = [{ n: 1, url: 'U1' }, { n: 2, url: 'U2' }];
    const rowD = { sys_ProjectID: 'P', sys_Status: 'Картинка в работе', sys_ConversationId: 'conv_9', sys_PendingToolCallId: 'call_7', sys_EditorState: '{"x":1}', ai_ImageVariants: JSON.stringify(vs), ai_ImageUrl: 'U2', ai_UserBrief: 'бриф' };
    const tmplD = { tmpl_Channel: 'pengui', '🎨_tmpl_StyleRefs': 'https://drive.google.com/file/d/STYLE/view' };
    const mk = text => ({ kind: 'message', projectId: 'P', chatId: 1, sheetName: 'Pengui', channelKey: 'pengui', row: rowD, tmpl: tmplD, status: rowD.sys_Status, text, photo: null });
    const go = async text => {
      const c = mk(text);
      const v = (await run('Вход редактора', { nodes: { 'Контекст проекта': c } }))[0];
      if (!v.directArt) return { v };
      const k = (await run('Собираем знания канала', { nodes: { 'Контекст проекта': c } }))[0];
      const n = { 'Контекст проекта': c, 'Вход редактора': v, 'Собираем знания канала': k };
      const d = (await run('Задание художнику напрямую', { nodes: n }))[0];
      const f = (await run('Парсим ответ редактора', { nodes: n, input: [d] }))[0];
      return { v, d: f };
    };
    let x = await go('Художнику: Pengui reads under a lamp, matte colors');
    assert.deepEqual(x.v.directArt, { edit: false, variant: null, text: 'Pengui reads under a lamp, matte colors' });
    assert.equal(x.d.action, 'ready_to_draw'); assert.equal(x.d.dallePrompt, 'Pengui reads under a lamp, matte colors');
    assert.equal(x.d.callId, 'call_7', 'незакрытый вызов Редактора не теряем');
    assert.equal(x.d.conversationId, 'conv_9'); assert.equal(x.d.editorState, '{"x":1}'); assert.equal(x.d.userBrief, 'бриф');
    assert.equal(x.d.statusAfter, 'Картинка в работе'); assert.equal(x.d.styleGuideUrl, 'https://lh3.googleusercontent.com/d/STYLE=s2000');
    x = await go('художнику,  нарисуй кота'); assert.equal(x.d.dallePrompt, 'нарисуй кота');
    {
      const c = { ...mk('Художнику: кот в кафе'), tmpl: { ...tmplD, '🎨_tmpl_ArtistRules': 'Pengui is small. The scene:' } };
      const v = (await run('Вход редактора', { nodes: { 'Контекст проекта': c } }))[0];
      const k = (await run('Собираем знания канала', { nodes: { 'Контекст проекта': c } }))[0];
      assert.equal(k.artistRules, 'Pengui is small. The scene:');
      const n = { 'Контекст проекта': c, 'Вход редактора': v, 'Собираем знания канала': k };
      const dd = (await run('Задание художнику напрямую', { nodes: n }))[0];
      assert.equal(dd.dallePrompt, 'Pengui is small. The scene:\n\nкот в кафе', 'правила из таблицы + сцена');
      const c2 = { ...mk('Художнику правка: теплее'), tmpl: c.tmpl };
      const v2 = (await run('Вход редактора', { nodes: { 'Контекст проекта': c2 } }))[0];
      const d2 = (await run('Задание художнику напрямую', { nodes: { ...n, 'Контекст проекта': c2, 'Вход редактора': v2 } }))[0];
      assert.equal(d2.revisionInstruction, 'теплее', 'в правку правила не подклеиваем');
    }
    x = await go('ХУДОЖНИКУ — правка: warmer light');
    assert.equal(x.d.action, 'revise_point'); assert.equal(x.d.revisionInstruction, 'warmer light');
    assert.equal(x.d.revisionTargetImageUrl, 'U2'); assert.equal(x.d.revisionTargetVariantNumber, 2);
    x = await go('Художнику правка 1: less people');
    assert.equal(x.d.revisionTargetImageUrl, 'U1'); assert.equal(x.d.revisionTargetVariantNumber, 1); assert.equal(x.d.revisionInstruction, 'less people');
    {
      const c = mk('Художнику правка: brighter');
      const v = (await run('Вход редактора', { nodes: { 'Контекст проекта': c, 'Разбираем входящее': { replyVariant: 1 } } }))[0];
      assert.equal(v.directArt.variant, 1, 'ответ на «Вариант 1» — правим вариант 1');
      const v2 = (await run('Вход редактора', { nodes: { 'Контекст проекта': mk('Художнику правка 2: x'), 'Разбираем входящее': { replyVariant: 1 } } }))[0];
      assert.equal(v2.directArt.variant, 2, 'номер в тексте важнее');
      const rz = (await run('Разбираем входящее', { nodes: { 'Telegram Trigger': { message: { chat: { id: 1 }, text: 'Художнику правка: теплее', reply_to_message: { caption: 'Вариант 3\nID: 20260924_101010_pengui' } } } } }))[0];
      assert.equal(rz.kind, 'message'); assert.equal(rz.replyVariant, 3);
      const rz2 = (await run('Разбираем входящее', { nodes: { 'Telegram Trigger': { message: { chat: { id: 1 }, text: 'Художнику: как тут https://drive.google.com/file/d/X/view', reply_to_message: { text: 'ID: 20260924_101010_pengui' } } } } }))[0];
      assert.equal(rz2.kind, 'message', 'ссылка в задании художнику — не треки');
    }
    x = await go('Художнику правка 5: x'); assert.equal(x.d.action, 'chat'); assert.ok(x.d.messageToUser.includes('Не нашла вариант 5'));
    x = await go('Художнику:'); assert.equal(x.d.action, 'chat');
    x = await go('Художникутром поговорим'); assert.equal(x.v.directArt, null, 'похожее слово — не команда');
    x = await go('давай художнику скажем'); assert.equal(x.v.directArt, null, 'только в начале');
    x = await go('Художнику правкой займёмся потом'); assert.equal(x.d.action, 'ready_to_draw', '«правкой» — не команда правки');
  }
  console.log('10 художнику напрямую OK');
  // ── 11. Утвердить ≠ собрать: кнопка «🎬 Собрать с этими треками»
  {
    const rb = (await run('Разбираем входящее', { nodes: { 'Telegram Trigger': { callback_query: { id: 'q', data: 'build|20260924_101010_pengui', message: { chat: { id: 1 } } } } } }))[0];
    assert.equal(rb.kind, 'build'); assert.equal(rb.projectId, '20260924_101010_pengui');
    const ctxV = { projectId: 'P', chatId: 1 };
    const u = (await run('Сообщение: утверждено', { nodes: { 'Контекст проекта': ctxV, 'Проверяем таблицу (финал)': { hasTracks: true }, 'Перечитываем строку (финал)': { sys_AudioZipUrl: 'https://www.kaggle.com/code/td1976/suno-clean' } } }))[0];
    assert.ok(u.text.includes('Собрать с ними — кнопка ниже')); assert.ok(u.text.includes('последний готовый результат'));
    assert.ok(!u.text.includes('передаю сборщику'), 'утверждение само не собирает');
    assert.equal(u.callbackData, 'build|P'); assert.equal(u.hasTracks, true);
    const u2 = (await run('Сообщение: утверждено', { nodes: { 'Контекст проекта': ctxV, 'Проверяем таблицу (финал)': { hasTracks: false }, 'Перечитываем строку (финал)': {} } }))[0];
    assert.ok(u2.text.includes('Жду ссылку на треки'));
  }
  console.log('11 утвердить ≠ собрать OK');
  console.log('ALL OK');
})().catch(e => { console.error('FAIL', e); process.exit(1); });
