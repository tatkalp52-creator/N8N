const response = $input.first().json;
const prep = $('Готовим запрос редактору').first().json;
const ctx = $('Контекст проекта').first().json;
const kb = $('Собираем знания канала').first().json;
const vhod = $('Вход редактора').first().json;
const row = ctx.row || {};
const output = response.output || [];

// Текст ответа (может быть несколько частей) и вызов инструмента — это
// отдельные элементы output, никакого разбора регулярками.
const plainText = output
  .filter(i => i.type === 'message')
  .flatMap(i => (i.content || []).filter(c => c.type === 'output_text').map(c => c.text))
  .join('\n\n')
  .trim();
const callItem = output.find(i => i.type === 'function_call');

let action = 'chat';
let messageToUser = plainText;
let callId = null;
let functionName = null;
let args = {};
if (callItem) {
  callId = callItem.call_id;
  functionName = callItem.name;
  try { args = JSON.parse(callItem.arguments || '{}'); } catch (e) { args = {}; }
  messageToUser = args.messageToUser || plainText || '';
}

const state = tbParseState(row.sys_EditorState);
state.seenImages = prep.newSeenImages || state.seenImages;

let variants = [];
try { variants = JSON.parse(row.ai_ImageVariants || '[]'); } catch (e) { variants = []; }
if (!Array.isArray(variants)) variants = [];
const lastVariant = variants.length ? variants[variants.length - 1] : null;

let dallePrompt = '';
let revisionInstruction = '';
let revisionIsNewVariant = false;
let revisionTargetImageUrl = String(row.ai_ImageUrl || '');
let revisionTargetVariantNumber = lastVariant ? lastVariant.n : 1;
let approveVariantNumber = null;
let approveTargetBrightness = null;
let resolvedApprovedImageUrl = '';
let communicationNotes = '';
const changedItems = [];
let textBlockTouched = false;

function applyTextBlock(args) {
  const items = args.items || {};
  const setVal = (key, n, value) => {
    const old = state.items[key];
    const same = Array.isArray(value) ? JSON.stringify(old) === JSON.stringify(value) : old === value;
    const wasSet = !!state.set[n];
    state.set[n] = true;
    if (!same || !wasSet) {
      state.items[key] = value;
      if (!changedItems.includes(n)) changedItems.push(n);
      state.agreed[n] = false;
    }
  };
  const str = v => (typeof v === 'string' ? v.trim() : '');
  // Пункт 1: текст и позиция живут вместе.
  if (str(items.overlayText)) setVal('overlayText', 1, str(items.overlayText) === '-' ? '' : str(items.overlayText));
  if (str(items.overlayPosition)) setVal('overlayPosition', 1, str(items.overlayPosition).toLowerCase());
  if (str(items.title)) setVal('title', 2, str(items.title));
  if (str(items.description)) setVal('description', 3, str(items.description));
  let tc = items.timecodes;
  if (typeof tc === 'string') tc = tc.split('\n');
  if (Array.isArray(tc)) {
    tc = tc.map(x => String(x || '').replace(/^\s*\d+[.)]\s*/, '').trim()).filter(Boolean);
    if (tc.length) setVal('timecodes', 4, tc);
  }
  if (str(items.footer)) setVal('footer', 5, str(items.footer));
  if (str(items.hashtags)) setVal('hashtags', 6, str(items.hashtags));
  if (str(items.tags)) setVal('tags', 7, str(items.tags));
  if (str(items.pinnedComment)) setVal('pinnedComment', 8, str(items.pinnedComment) === '-' ? '' : str(items.pinnedComment));

  // Русский перевод для автора: новый — сохраняем; если пункт изменился,
  // а перевода к нему не прислали — старый перевод убираем (он устарел).
  const ru = args.ruTranslations || {};
  state.ru = state.ru || {};
  for (const [key, n] of [['overlayText', 1], ['title', 2], ['pinnedComment', 8]]) {
    if (typeof ru[key] === 'string' && ru[key].trim()) state.ru[key] = ru[key].trim();
    else if (changedItems.includes(n)) delete state.ru[key];
  }
  if (Array.isArray(ru.timecodes) && ru.timecodes.length) state.ru.timecodes = ru.timecodes.map(x => String(x || '').replace(/^\s*\d+[.)]\s*/, '').trim());
  else if (changedItems.includes(4)) delete state.ru.timecodes;

  // Английский перевод относится к конкретному тексту описания.
  if (state.descriptionENFor !== state.items.description) {
    state.descriptionEN = '';
    state.descriptionENFor = '';
  }

  for (const n of (args.reopenItems || [])) {
    if (state.agreed[n]) { state.agreed[n] = false; if (!changedItems.includes(n)) changedItems.push(n); }
  }
  for (const raw of (args.agreedItems || [])) {
    const n = parseInt(raw, 10);
    if (!(n >= 1 && n <= 8)) continue;
    if (!state.set[n] && TB_CAN_BE_EMPTY.includes(n)) state.set[n] = true; // "оверлей/коммент не нужен"
    if (state.set[n]) state.agreed[n] = true;
  }
}

if (functionName === 'start_drawing') {
  action = 'ready_to_draw';
  dallePrompt = args.dallePrompt || '';
  if (!dallePrompt.trim()) action = 'chat';
} else if (functionName === 'request_revision') {
  action = 'revise_point';
  revisionInstruction = args.revisionInstruction || '';
  revisionIsNewVariant = !!args.isNewVariant;
  const target = args.variantNumber ? variants.find(v => Number(v.n) === Number(args.variantNumber)) : null;
  if (target && target.url) {
    revisionTargetImageUrl = target.url;
    revisionTargetVariantNumber = target.n;
  }
  if (!revisionTargetImageUrl) action = 'chat';
} else if (functionName === 'approve_image') {
  action = 'approved';
  approveVariantNumber = args.variantNumber || null;
  approveTargetBrightness = args.targetBrightness || null;
  const found = approveVariantNumber ? variants.find(v => Number(v.n) === Number(approveVariantNumber)) : null;
  resolvedApprovedImageUrl = (found && found.url) || (variants.length === 1 ? variants[0].url : '') || String(row.ai_ImageUrl || '');
  if (!resolvedApprovedImageUrl) action = 'chat';
  // Вместе с согласованием Редактор сразу присылает первый вариант текста.
  if (action === 'approved' && args.items && Object.keys(args.items).length) {
    textBlockTouched = true;
    applyTextBlock(args);
  }
} else if (functionName === 'update_communication_notes') {
  communicationNotes = args.notes || '';
} else if (functionName === 'update_text_block') {
  action = 'text_block';
  textBlockTouched = true;
  applyTextBlock(args);
}

// ── Статус в таблице ──
// Статус больше НЕ управляет разговором — он нужен только как стена перед
// сборщиком. Любая правка текста после "Утверждено" снимает утверждение.
const curStatus = vhod.status;
let statusAfter = curStatus || 'Картинка в работе';
let statusReverted = false;
if (curStatus !== 'Опубликовано') {
  if (action === 'approved') {
    const sameAsApproved = resolvedApprovedImageUrl && resolvedApprovedImageUrl === vhod.approvedUrl;
    if (!(curStatus === 'Утверждено' && sameAsApproved)) statusAfter = 'Картинка согласована';
  }
  if (curStatus === 'Утверждено' && action === 'text_block' && changedItems.length) {
    statusAfter = 'Картинка согласована';
  }
  statusReverted = curStatus === 'Утверждено' && statusAfter !== 'Утверждено';
}

return [{
  json: {
    action,
    functionName,
    approvedNow: action === 'approved',
    messageToUser,
    callId,
    conversationId: prep.conversationId,
    editorState: JSON.stringify(state),
    statusAfter,
    statusReverted,
    changedItems,
    textBlockTouched,
    allAgreed: tbAllAgreed(state),
    communicationNotes,
    userBrief: String(row.ai_UserBrief || '').trim() || (vhod.fromButton ? '' : vhod.userText),
    // для веток рисования (узлы перенесены из 01_Художник без изменений)
    dallePrompt,
    revisionInstruction,
    revisionIsNewVariant,
    revisionTargetImageUrl,
    revisionTargetVariantNumber,
    approveVariantNumber,
    approveTargetBrightness,
    resolvedApprovedImageUrl,
    styleGuideUrl: kb.styleGuideUrl,
    referenceUrls: kb.referenceUrls,
    fromButton: vhod.fromButton,
    projectId: ctx.projectId,
    chatId: ctx.chatId,
    sheetName: ctx.sheetName,
    channelKey: ctx.channelKey,
  }
}];
