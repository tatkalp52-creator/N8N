// Летопись жизни героя: после утверждения выпуска дописываем в неё несколько
// строк — так Писатель и Редактор помнят, что с героем уже случилось.
const ctx = $('Контекст проекта').first().json;
const tmpl = ctx.tmpl || {};
const key = Object.keys(tmpl).find(k => k.includes('tmpl_Chronicle')) || '';
const chronicle = key ? String(tmpl[key] || '').trim() : '';
const state = tbParseState((ctx.row || {}).sys_EditorState);
const story = (state.ru && state.ru.description) || state.items.description || '';
const date = String(ctx.projectId || '').slice(0, 8).replace(/(\d{4})(\d{2})(\d{2})/, '$3.$2.$1');
return [{
  json: {
    chronicleKey: key,
    chronicle,
    date,
    requestBody: {
      model: 'gpt-5',
      input: [
        { role: 'system', content: 'Ты ведёшь летопись жизни героя канала. Ниже — летопись и утверждённое описание нового выпуска. Напиши для летописи 2–5 коротких строк об этом выпуске: что случилось, кто появился (с приметами), что герой понял или решил, детали и шутки, которые могут вернуться в будущих историях. Только факты этой истории, без оценок и пересказа стиля. Ответь только этими строками, без заголовка.' },
        { role: 'user', content: `ЛЕТОПИСЬ:\n${chronicle || '(пока пусто)'}\n\nНОВЫЙ ВЫПУСК (${date}):\n${story}` },
      ],
    },
  },
}];
