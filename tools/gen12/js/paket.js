// Запись в таблицу: значения пунктов раскладываются по колонкам листа выпусков
// так, как написано в листе «Пункты» (колонка «Колонки»). Статус здесь ещё НЕ ставим.
const ctx = $('Контекст проекта').first().json;
const row = ctx.row || {};
let raw = row.sys_EditorState;
try { raw = $('Итог хода').first().json.editorState; } catch (e) {}
const state = stParseState(raw);
const items = ctx.items || [];
const problems = [];
const notAgreed = items.filter(it => !state.agreed[it.n]);
if (notAgreed.length) problems.push('не согласованы пункты: ' + notAgreed.map(it => `${it.n} ${it.name}`).join(', '));
if (!String(row.ai_ApprovedImageUrl || '').trim()) problems.push('картинка не согласована');
if (!items.length) problems.push('лист «Пункты» пуст для этого канала');
const fields = { sys_ProjectID: ctx.projectId, sys_EditorState: JSON.stringify(state), ...itFields(items, state) };
return [{ json: {
  ok: problems.length === 0, problems, fields,
  problemsText: 'Не могу утвердить:\n• ' + problems.join('\n• ') + `\n\nID: ${ctx.projectId}`,
} }];
