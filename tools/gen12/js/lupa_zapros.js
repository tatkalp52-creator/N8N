// Лупа: просим этап уточнить каждую точку по увеличенному кусочку картинки с мелкой сеткой.
const ctx = $('Контекст проекта').first().json;
const plan = $('Лупа: план').first().json;
const stageIcon = $('Разбираем ответ этапа').first().json.stageIcon;
const stage = (ctx.stages || []).find(s => bareIcon(s.icon) === bareIcon(stageIcon)) || {};
const points = ($('Сервер: лупа').first().json || {}).points || [];
const content = [{ type: 'input_text', text:
  'Строки оживления:\n' + plan.fx + '\n\nНиже — увеличенные кусочки картинки вокруг каждой точки этих строк.' }];
for (const p of points) {
  content.push({ type: 'input_text', text: `Точка ${p.id} — ${p.label}; сейчас ${p.x}, ${p.y}.` });
  content.push({ type: 'input_image', image_url: p.dataUrl });
}
const requestBody = {
  model: stage.model || 'gpt-5',
  instructions: 'Ты уточняешь точки оживления по увеличенным кусочкам картинки. На каждом кусочке — сетка через 1 % ' +
    'с подписями в процентах ВСЕГО кадра: синие числа сверху — слева направо, красные слева — сверху вниз. ' +
    'Голубой кружок — где точка стоит сейчас. Найди на кусочке то, на что точка должна указывать (написано рядом с ней), ' +
    'и прочитай его координаты по сетке с точностью до десятых. Если этого на кусочке нет — верни прежние числа. ' +
    'Ответь только вызовом refine_points.',
  input: [{ role: 'user', content }],
  tools: [{ type: 'function', name: 'refine_points', description: 'Уточнённые координаты точек',
    parameters: { type: 'object', properties: { points: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, x: { type: 'number' }, y: { type: 'number' } }, required: ['id', 'x', 'y'] } } }, required: ['points'] } }],
  tool_choice: { type: 'function', name: 'refine_points' },
  reasoning: { effort: 'medium' },
};
return [{ json: { requestBody } }];
