// Разбираем ответ этапа: текст и (не больше одного) вызов инструмента.
const response = $input.first().json || {};
const prep = $('Готовим запрос этапу').first().json;
const ctx = $('Контекст проекта').first().json;
const plan = $('Кто отвечает').first().json;
const row = ctx.row || {};
const stages = ctx.stages || [];
const items = ctx.items || [];
const stage = stages.find(s => bareIcon(s.icon) === bareIcon(prep.stageIcon));
const sc = stScope(stages, stage);
const output = response.output || [];

const plainText = output.filter(i => i.type === 'message')
  .flatMap(i => (i.content || []).filter(c => c.type === 'output_text').map(c => c.text)).join('\n\n').trim();
const callItem = output.find(i => i.type === 'function_call');
let functionName = null, callId = null, args = {};
if (callItem) {
  functionName = callItem.name; callId = callItem.call_id;
  try { args = JSON.parse(callItem.arguments || '{}'); } catch (e) { args = {}; }
}
let message = (args.message || plainText || '').trim();
if (response.error || (!callItem && !plainText)) {
  message = `⚠️ ${stage.name} не ответил${response.error ? ': ' + (response.error.message || response.error) : ''}. Напишите ещё раз.`;
}

const state = stParseState(row.sys_EditorState);
stApplyApproval(state, plan.approveNums);   // согласование автора — до и независимо от инструмента модели
const st = stStage(state, stage.icon);
if (!plan.silent) {
  st.conv = prep.conversationId || st.conv;
  st.pending = callId || '';
  st.seen = prep.seen || st.seen;
}

let action = 'chat';
let changed = [];
let proposed = [];
let note = null;
let delegate = null;
let art = null;
let approveUrl = '';
let approveVariant = null;

if (functionName === 'propose_items') {
  changed = itApply(state, items, sc.items, args, plan.silent || !stage.approve);
  // что этап прислал на этом ходу, даже без изменений (превью покажем и тогда)
  proposed = (Array.isArray(args.items) ? args.items : []).map(p => parseInt(p && p.n, 10)).filter(n => sc.items.includes(n));
  action = 'text_block';
} else if (functionName === 'save_note') {
  const kb = kbForStage(ctx.tmpl, stage.icon, '');
  if (kb.notesKey) note = { key: kb.notesKey, text: String(args.notes || '') };
} else if (functionName === 'delegate') {
  const sub = sc.subs.find(s => s.name === args.stage);
  if (sub && sub.picture && !sub.items.length) {
    art = artBuild(ctx, sub, String(args.task || ''), !!args.edit || !!args.variant, args.variant || null);
    action = art.action;
    if (action === 'chat') message = [message, art.messageToUser].filter(Boolean).join('\n\n');
  } else if (sub) {
    delegate = { stageIcon: sub.icon, stageName: sub.name, task: String(args.task || '') };
    action = 'delegate';
  }
} else if (functionName === 'approve_image') {
  let variants = [];
  try { variants = JSON.parse(row.ai_ImageVariants || '[]'); } catch (e) { variants = []; }
  if (!Array.isArray(variants)) variants = [];
  const found = args.variant ? variants.find(v => Number(v.n) === Number(args.variant)) : (variants.length === 1 ? variants[0] : null);
  if (found && found.url) { approveUrl = found.url; approveVariant = found.n; action = 'approved'; }
  else message += `\n\n(Не поняла, какой вариант согласован${variants.length ? ': есть ' + variants.map(v => v.n).join(', ') : ''}.)`;
}

return [{ json: {
  action, functionName, callId, message, changed, proposed, note, delegate, art,
  approveUrl, approveVariant,
  editorState: JSON.stringify(state),
  stageIcon: stage.icon, stageName: stage.name,
} }];
