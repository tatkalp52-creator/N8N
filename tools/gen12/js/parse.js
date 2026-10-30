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
// (28.10) два кармашка: ответ — JSON {message, items, agreed, reopen}; тексты пунктов — как будто propose_items
let pocketsUsed = false;
if (!callItem && prep.pockets && plainText) {
  let pk = null;
  try { pk = JSON.parse(plainText); } catch (e) { pk = null; }
  if (pk && typeof pk === 'object' && typeof pk.message === 'string') {
    args = pk; pocketsUsed = true;
    const has = k => Array.isArray(pk[k]) && pk[k].length;
    if (has('items') || has('agreed') || has('reopen')) functionName = 'propose_items';
  }
}
let message = (args.message || (pocketsUsed ? '' : plainText) || '').trim();
if (response.error || (!callItem && !plainText)) {
  // (28.10) не ответил — «Работа» падает, очередь повторит сама (автору не нужно писать ещё раз)
  const er = response.error, why = er ? [er.message || (typeof er === 'string' ? er : ''), er.description].filter(Boolean).join(' — ') : 'пустой ответ';
  throw new Error(`${stage.name} не ответил: ${String(why).slice(0, 400)}`);
}

const state = stParseState(row.sys_EditorState);
stApplyApproval(state, plan.approveNums);   // согласование автора — до и независимо от инструмента модели
const st = stStage(state, stage.icon);
// (28.10) память разговора этапа: реплика автора и ответ этапа (что он сделал — коротко), последние 10
if (!plan.silent) {
  const did = functionName ? ` [${functionName}${Array.isArray(args.items) && args.items.length ? ': пункты ' + args.items.map(i => i && i.n).filter(Boolean).join(', ') : ''}]` : '';
  const cut = t => { t = String(t || '').trim(); return t.length > 1200 ? t.slice(0, 1200) + '…' : t; };
  if (prep.logUser) st.log.push({ r: 'u', t: cut(prep.logUser) });
  st.log.push({ r: 'a', t: cut(message + did) });
  st.log = st.log.slice(-10);
  // ячейка таблицы держит 50 000 знаков: память этапов не должна её переполнить — старое уходит первым
  const logs = Object.values(state.stages).filter(x => Array.isArray(x.log));
  while (JSON.stringify(state).length > 40000) {
    const longest = logs.reduce((m, x) => (x.log.length > (m ? m.log.length : 0) ? x : m), null);
    if (!longest || longest.log.length <= 2) break;
    longest.log.shift();
  }
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
  // (22.10) памятка только дописывается: раньше модель присылала «полный текст», а писала одно новое —
  // и прежние выпуски стирались. Дата и выпуск — чтобы было видно, откуда запись.
  if (kb.notesKey) {
    const old = String((ctx.tmpl || {})[kb.notesKey] || '').trim();
    const add = String(args.notes || '').trim();
    // (28.10) пишем ровно то, что пришло, без даты и номера выпуска: памятка — не журнал выпусков
    const text = !add || old.includes(add) ? old : (add.startsWith(old) && old ? add : [old, add].filter(Boolean).join('\n'));
    note = { key: kb.notesKey, text };
  }
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
