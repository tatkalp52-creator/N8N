// Перевод для автора (11.10): пункты не по-русски переводит отдельный переводчик. Он видит только
// готовый текст пункта — то, что ляжет в таблицу, — без разговора и без пометок автора. Поэтому
// русский, который читает автор, — всегда перевод того английского, который она согласует.
// Модель — этапа, который сейчас говорил (лист «Этапы»).
const draft = $('Итог хода: черновик').first().json;
const ctx = $('Контекст проекта').first().json;
const state = stParseState(draft.editorState);
const todo = itRuTodo(state);
if (!todo.length) return [{ json: { need: false, todo: [] } }];
const stages = ctx.stages || [];
const stage = stages.find(s => bareIcon(s.icon) === bareIcon(draft.stageIcon)) || stages.find(s => s.model) || {};
const model = stage.model || 'gpt-5';
const src = {};
for (const t of todo) src[String(t.n)] = t.text;
const requestBody = {
  model,
  instructions: 'Translate each text into Russian exactly as it is written. Do not add, drop, improve or explain anything; '
    + 'keep line breaks, numbers, timestamps, hashtags and names as they are. '
    + 'Answer with JSON only: {"<key>": "<Russian translation>"} with the same keys.',
  input: [{ role: 'user', content: JSON.stringify(src) }],
  text: { format: { type: 'json_object' } },
  store: false,
};
if (/^(gpt-5|o\d)/.test(model)) requestBody.reasoning = { effort: 'low' };
return [{ json: { need: true, todo, requestBody } }];
