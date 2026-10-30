// Поручение этапу, который работает по заданию другого (например, Редактор → Писатель).
// Он получает только задание, свои знания из таблицы и картинку — молча, без разговора.
const ctx = $('Контекст проекта').first().json;
const r = $('Разбираем ответ этапа').first().json;
const row = ctx.row || {};
const stages = ctx.stages || [];
const items = ctx.items || [];
const sub = stages.find(s => bareIcon(s.icon) === bareIcon(r.delegate.stageIcon));
if (!sub.model) throw new Error('Таблица: у этапа ' + sub.name + ' не указана модель (лист «Этапы»)');
const state = stParseState(r.editorState);
const kb = kbForStage(ctx.tmpl, sub.icon, r.delegate.task + ' ' + String(row.ai_UserBrief || ''));
const myItems = items.filter(it => sub.items.includes(it.n));
const approvedUrl = String(row.ai_ApprovedImageUrl || '').trim();
const current = myItems.map(it => { const t = itShow(state, it, true); return t ? `${it.n}. ${it.name}:\n${t}` : ''; }).filter(Boolean).join('\n\n');

const instructions = `Ты — ${sub.icon} ${sub.name} канала "${ctx.sheetName}". Ты работаешь по заданию: сразу вызови propose_items со своими пунктами.

ТВОИ ПУНКТЫ
${myItems.map(it => `  ${it.n}. ${it.name}${it.hint ? ' — ' + it.hint : ''}`).join('\n')}

ТВОИ ЗНАНИЯ ИЗ ТАБЛИЦЫ КАНАЛА:
${kb.text || '(пусто)'}`;

const content = [{ type: 'input_text', text: 'ЗАДАНИЕ:\n' + r.delegate.task + (current ? '\n\nСейчас в твоих пунктах (для сведения):\n' + current : '') }];
if (approvedUrl) {
  content.push({ type: 'input_text', text: '(Согласованная картинка выпуска:)' });
  content.push({ type: 'input_image', image_url: approvedUrl });
}
const tools = [{
  type: 'function', name: 'propose_items', description: 'Твои пункты.',
  parameters: { type: 'object', properties: {
    items: { type: 'array', items: { type: 'object', properties: {
      n: { type: 'integer' }, text: { type: 'string' },
    }, required: ['n', 'text'] } },
    message: { type: 'string' },
  }, required: ['items'] },
}];
const requestBody = {
  model: sub.model, instructions, input: [{ role: 'user', content }], tools,
  tool_choice: { type: 'function', name: 'propose_items' },
};
if (['low', 'medium', 'high'].includes(sub.effort)) requestBody.reasoning = { effort: sub.effort };
return [{ json: { requestBody } }];
