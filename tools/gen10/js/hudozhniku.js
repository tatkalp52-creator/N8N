// «Художнику: …» — задание автора уходит в рисование как есть, Редактор не вызывается.
// Выход — в том же виде, что у «Разбираем ответ редактора», чтобы дальше всё шло
// по обычным веткам рисования/правки. Разговор с Редактором не трогаем: его
// незакрытый вызов инструмента и состояние текста остаются как были.
const ctx = $('Контекст проекта').first().json;
const kb = $('Собираем знания канала').first().json;
const vhod = $('Вход редактора').first().json;
const row = ctx.row || {};
const d = vhod.directArt || {};

let variants = [];
try { variants = JSON.parse(row.ai_ImageVariants || '[]'); } catch (e) { variants = []; }
if (!Array.isArray(variants)) variants = [];
const last = variants.length ? variants[variants.length - 1] : null;

let action = d.edit ? 'revise_point' : 'ready_to_draw';
let messageToUser = d.edit ? 'Художник поправляет 🎨' : 'Художник рисует по твоему заданию 🎨';
let revisionTargetImageUrl = String(row.ai_ImageUrl || '');
let revisionTargetVariantNumber = last ? last.n : 1;

if (d.edit) {
  const target = d.variant ? variants.find(v => Number(v.n) === Number(d.variant)) : last;
  if (target && target.url) {
    revisionTargetImageUrl = target.url;
    revisionTargetVariantNumber = target.n;
  } else if (d.variant) {
    action = 'chat';
    messageToUser = `Не нашла вариант ${d.variant}. Есть: ${variants.map(v => v.n).join(', ') || 'пока ни одного'}.`;
  }
  if (action === 'revise_point' && !revisionTargetImageUrl) {
    action = 'chat';
    messageToUser = 'Править пока нечего — сначала нарисуем: «Художнику: …».';
  }
}
if (action !== 'chat' && !d.text) {
  action = 'chat';
  messageToUser = d.edit
    ? 'Напиши, что поправить: «Художнику правка: …» (или «Художнику правка 2: …» для варианта 2).'
    : 'Напиши задание после слова: «Художнику: …».';
}

return [{
  json: {
    direct: true,
    action,
    functionName: 'direct_artist',
    approvedNow: false,
    messageToUser,
    callId: String(row.sys_PendingToolCallId || '').trim() || null,
    conversationId: String(row.sys_ConversationId || '').trim(),
    editorState: String(row.sys_EditorState || ''),
    statusAfter: vhod.status || 'Картинка в работе',
    statusReverted: false,
    changedItems: [],
    textBlockTouched: false,
    allAgreed: false,
    communicationNotes: '',
    storyBrief: '',
    storyKeep: '',
    userBrief: String(row.ai_UserBrief || '').trim(),
    dallePrompt: action === 'ready_to_draw' ? d.text : '',
    revisionInstruction: action === 'revise_point' ? d.text : '',
    revisionIsNewVariant: true,
    revisionTargetImageUrl,
    revisionTargetVariantNumber,
    approveVariantNumber: null,
    approveTargetBrightness: null,
    resolvedApprovedImageUrl: '',
    styleGuideUrl: kb.styleGuideUrl,
    referenceUrls: kb.referenceUrls,
    fromButton: false,
    projectId: ctx.projectId,
    chatId: ctx.chatId,
    sheetName: ctx.sheetName,
    channelKey: ctx.channelKey,
  }
}];
