// Итог хода — все узлы ниже читают только его. Сюда приходят три пути:
// художник (задание автора), этап-модель (с поручением подчинённому или без),
// служебная реплика. Здесь же решаем переход к следующему этапу.
const ctx = $('Контекст проекта').first().json;
const plan = $('Кто отвечает').first().json;
const row = ctx.row || {};
const stages = ctx.stages || [];
const items = ctx.items || [];
const stage = stages.find(s => bareIcon(s.icon) === bareIcon(plan.stageIcon)) || null;
const before = stParseState(row.sys_EditorState);
let state = stParseState(row.sys_EditorState);
const approvedBefore = String(row.ai_ApprovedImageUrl || '').trim();

let action = 'chat';
let message = '';
let note = null;
let art = null;
let approveUrl = '';
let approveVariant = null;
let changed = [];
let speaker = stage;
// Картинку без согласования автора (этап «авто» или молчаливый) согласуем сами после рисунка.
let autoApprove = false;

if (plan.mode === 'say') {
  message = plan.sayText;
  speaker = null;
} else if (plan.mode === 'done') {
  action = 'done';
} else if (plan.mode === 'draw' || plan.mode === 'edit') {
  art = artBuild(ctx, stage, plan.userText, plan.mode === 'edit', plan.editVariant);
  autoApprove = !stage.approve || stage.talks === 'none';
  action = art.action;
  message = art.action === 'chat' ? art.messageToUser : (plan.mode === 'edit' ? 'поправляю 🎨' : 'рисую 🎨');
} else if (plan.mode === 'model') {
  const r = $('Разбираем ответ этапа').first().json;
  state = stParseState(r.editorState);
  action = r.action; message = r.message; note = r.note; changed = r.changed || [];
  approveUrl = r.approveUrl; approveVariant = r.approveVariant;
  if (r.art) { art = r.art; autoApprove = !stage.approve; }
  if (r.action === 'delegate') {
    // Подчинённый этап прислал свои пункты.
    const sub = stages.find(s => bareIcon(s.icon) === bareIcon(r.delegate.stageIcon));
    const boss = stage;
    let resp = {};
    try { resp = $('OpenAI: поручение').first().json || {}; } catch (e) {}
    const call = (resp.output || []).find(i => i.type === 'function_call');
    let a = {};
    try { a = JSON.parse((call && call.arguments) || '{}'); } catch (e) { a = {}; }
    const got = itApply(state, items, sub.items, a, !boss.approve);
    changed = [...new Set([...changed, ...got])];
    action = 'text_block';
    if (!call) message = [message, `⚠️ ${sub.icon} ${sub.name} не прислал работу — попросите ещё раз.`].filter(Boolean).join('\n\n');
  }
}

// ── Картинка согласована словами (через этап, который за неё отвечает) ──
const approvedUrl = approveUrl || approvedBefore;

// ── Статус в таблице: только механика для сборщика ──
const cur = ctx.status;
let statusAfter = cur || 'Картинка в работе';
let statusReverted = false;
if (cur !== 'Опубликовано') {
  if (action === 'approved' && !(cur === 'Утверждено' && approveUrl === approvedBefore)) statusAfter = 'Картинка согласована';
  if (cur === 'Утверждено' && changed.length) statusAfter = 'Картинка согласована';
  statusReverted = cur === 'Утверждено' && statusAfter !== 'Утверждено';
}

// ── Переход: этап только что завершился → следующий; всё готово → сводка или запись ──
let transition = 'none';
let event = '';
let nextIcon = '';
if (action === 'done') {
  transition = stages.some(s => s.approve) ? 'summary' : 'package';
} else if (stage && ['text_block', 'approved'].includes(action)) {
  const wasDone = stComplete(stages, items, before, approvedBefore, stage);
  const nowDone = stComplete(stages, items, state, approvedUrl, stage);
  if (nowDone && !wasDone) {
    const next = stCurrent(stages, items, state, approvedUrl);
    if (next) { transition = 'next'; nextIcon = next.icon; event = `Этап «${stage.name}» завершён.`; }
    else transition = stages.some(s => s.approve) ? 'summary' : 'package';
  }
}

// ── Что показать автору ──
const prefix = speaker ? `${speaker.icon} <b>${escapeHtml(speaker.name)}</b>: ` : '';
let text = prefix + escapeHtml(message || '');
// Разметка: автор видит, дошли ли её штрихи (иначе не понять, почему этап их не учёл)
if (plan.needMarks) {
  let mk = null;
  try { mk = $('Сервер: разметка').first().json || null; } catch (e) {}
  const n = mk && Array.isArray(mk.marks) ? mk.marks.length : 0;
  text += n ? `\n\n🖍 Разметка прочитана: штрихов — ${n}.`
    : `\n\n⚠️ Разметку прочитать не удалось${mk && mk.error ? ' (' + escapeHtml(String(mk.error)) + ')' : (mk ? ' — красных штрихов не нашлось' : ' — сборщик не ответил')}.`;
}
if (statusReverted) text += '\n\n⚠️ Статус «Утверждено» снят — после изменений пришлю новую сводку на ✅.';
if (action === 'text_block' && stage) {
  const sc = stScope(stages, stage);
  const mine = items.filter(it => sc.items.includes(it.n));
  const pending = mine.filter(it => !state.agreed[it.n]);
  const done = mine.filter(it => state.agreed[it.n]);
  if (pending.length) {
    text += `\n\n<b>Ждут согласования:</b> ${pending.map(it => it.n).join(', ')}`;
    for (const it of pending) {
      // пункт с превью автор проверяет глазами — строки для сборщика ей не показываем
      const body = it.preview && (state.items[it.n] || {}).text ? 'смотрите картинку-превью ниже' : itShow(state, it);
      text += `\n\n<b>${it.n}. ${escapeHtml(it.name)}</b>` + (body ? '\n' + escapeHtml(body) : ' — ещё не предложено');
    }
    text += '\n\nОтвечайте по номеру или по названию пункта.';
  }
  if (done.length) text += '\n\n✔️ Согласовано: ' + done.map(it => `${it.n} ${escapeHtml(it.name)}`).join(', ');
}
if (action === 'approved') text += `\n\n✅ Картинка согласована${approveVariant ? ' (вариант ' + approveVariant + ')' : ''}.`;
text += `\n\nID: ${ctx.projectId}`;
// Превью: изменился пункт, которому в листе «Пункты» положено превью, — сборщик нарисует картинку.
let previewBody = null;
const pvItem = items.find(it => it.preview && changed.includes(it.n) && (state.items[it.n] || {}).text);
if (pvItem && approvedBefore && /оживл/.test(pvItem.preview)) {
  const fx = {};
  for (const key of Object.keys(ctx.tmpl || {})) {        // вид эффектов — колонки 🎬 (как у сборки)
    if (!key.includes('🎬')) continue;
    const label = key.replace(/^[^a-zA-Z]+/, '').replace(/^tmpl_/, '');
    const v = String((ctx.tmpl || {})[key] == null ? '' : ctx.tmpl[key]).trim();
    if (label && v) fx[label.charAt(0).toLowerCase() + label.slice(1)] = v;
  }
  previewBody = { ...fx, imageUrl: approvedBefore, fx_Effects: state.items[pvItem.n].text, projectId: ctx.projectId };
}
const chunks = action === 'done' || (!message && action !== 'text_block') ? [] : splitForTelegram(text);

return [{ json: {
  action,
  chunks,
  silentTurn: !!plan.silent,
  note,
  editorState: JSON.stringify(state),
  statusAfter,
  statusReverted,
  approvedUrl: approveUrl,
  approveVariant,
  userBrief: String(row.ai_UserBrief || '').trim() || (plan.fromAuthor ? String(ctx.text || '').trim() : ''),
  transition,
  nextIcon,
  previewBody,
  previewCaption: previewBody ? `${stage ? stage.icon + ' ' : ''}Превью: так это будет выглядеть\n\nID: ${ctx.projectId}` : '',
  autoApprove,
  event,
  // для веток рисования (узлы перенесены из 01_Художник)
  dallePrompt: art ? art.dallePrompt : '',
  revisionInstruction: art ? art.revisionInstruction : '',
  revisionIsNewVariant: true,
  revisionTargetImageUrl: art ? art.revisionTargetImageUrl : '',
  revisionTargetVariantNumber: art ? art.revisionTargetVariantNumber : 1,
  drawRefUrls: art ? art.drawRefUrls : [],
  drawRoles: art ? art.drawRoles : '',
  editRefUrls: art ? art.editRefUrls : [],
  editRoles: art ? art.editRoles : '',
  imageModel: art ? art.imageModel : '',
  projectId: ctx.projectId,
  chatId: ctx.chatId,
  sheetName: ctx.sheetName,
  channelKey: ctx.channelKey,
  stageIcon: stage ? stage.icon : '',
} }];
