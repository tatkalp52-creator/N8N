// Перевод для автора (11.10): пункты не по-русски переводит отдельный переводчик. Он видит только
// готовый текст пункта — то, что ляжет в таблицу, — без разговора и без пометок автора. Поэтому
// русский, который читает автор, — всегда перевод того английского, который она согласует.
// Модель — служебная колонка Templates tmpl_LightModel (22.10: переводу не нужна большая модель); пусто — как раньше, модель этапа.
const draft = $('Итог хода: черновик').first().json;
const ctx = $('Контекст проекта').first().json;
const state = stParseState(draft.editorState);
const todo = itRuTodo(state);
const stages = ctx.stages || [];
const textModel = s => s && s.model && !/image|dall/i.test(s.model) ? s.model : '';
const lightModel = String(findByLabel(ctx.tmpl || {}, 'tmpl_LightModel') || '').trim();
// (28.10) усилие — тоже из таблицы: tmpl_LightEffort для лёгкой модели, иначе «Усилие» этапа; пусто — не задаём
const EFFORTS = ['minimal', 'low', 'medium', 'high'];
const lightEffort = String(findByLabel(ctx.tmpl || {}, 'tmpl_LightEffort') || '').trim().toLowerCase();
// (23.10) правила перевода канала — колонки со значком 🌐 (их получатель — переводчик): имена героев и т. п.
// (28.10) что переводить, а что оставить (имена, названия) — только там: правило в коде спорило с таблицей
const trRules = Object.keys(ctx.tmpl || {}).filter(k => k.includes('🌐')).map(k => String(ctx.tmpl[k] == null ? '' : ctx.tmpl[k]).trim()).filter(Boolean).join('\n');
const withRules = t => t + (trRules ? '\n\nThe channel\'s translation rules (follow them, e.g. for names):\n' + trRules : '');
// (20.10) Задание художнику — наоборот, на английский: по-русски модель картинок дорисовывает
// «русский дух» (сани, гобелен с тройкой). Переводится только смысл задания, ничего не добавляется.
const plan = $('Кто отвечает').first().json;
const artTask = ['ready_to_draw', 'revise_point'].includes(draft.action) ? String(plan.userText || '').trim() : '';
// (24.10) тот же бриф уже переводили — берём готовый перевод, модель не зовём
const artKey = bareIcon(plan.stageIcon || '');
const cached = artTask && state.stages[artKey] && state.stages[artKey].briefEn;
if (artTask && cached && cached.ru === artTask && cached.en) {
  return [{ json: { need: false, todo: [], art: true, artTask, cachedEn: cached.en } }];
}
if (artTask && /[а-яё]/i.test(artTask)) {
  const model = lightModel || stages.map(textModel).find(Boolean);
  if (!model) throw new Error('Таблица: нет модели для перевода (Templates tmpl_LightModel)');
  const requestBody = {
    model,
    instructions: withRules('Translate the author\'s picture brief into clear, natural English for an image model. '
      + 'Keep its meaning exactly: add no objects, details, styles or cultural elements and drop none. '
      + 'Answer with JSON only: {"brief": "<English brief>"}.'),
    input: [{ role: 'user', content: 'Brief to translate (JSON):\n' + JSON.stringify({ brief: artTask }) }],
    text: { format: { type: 'json_object' } },
    store: false,
  };
  const eff = lightModel ? lightEffort : String((stages.find(s => s.model === model) || {}).effort || '');
  if (EFFORTS.includes(eff)) requestBody.reasoning = { effort: eff };
  return [{ json: { need: true, todo: [], art: true, artTask, requestBody } }];
}
if (!todo.length) return [{ json: { need: false, todo: [] } }];
const stage = stages.find(s => bareIcon(s.icon) === bareIcon(draft.stageIcon)) || stages.find(s => s.model) || {};
const model = lightModel || stage.model;
if (!model) throw new Error('Таблица: нет модели для перевода (Templates tmpl_LightModel)');
const src = {};
for (const t of todo) src[String(t.n)] = t.text;
const requestBody = {
  model,
  instructions: withRules('Translate each text into Russian exactly as it is written. Do not add, drop, improve or explain anything; '
    + 'keep line breaks, numbers, timestamps and hashtags as they are. '
    + 'Answer with JSON only: {"<key>": "<Russian translation>"} with the same keys.'),
  // слово JSON обязано стоять в самом запросе — иначе OpenAI отказывает в формате json_object
  input: [{ role: 'user', content: 'Texts to translate (JSON):\n' + JSON.stringify(src) }],
  text: { format: { type: 'json_object' } },
  store: false,
};
const eff = lightModel ? lightEffort : String(stage.effort || '');
if (EFFORTS.includes(eff)) requestBody.reasoning = { effort: eff };
return [{ json: { need: true, todo, requestBody } }];
