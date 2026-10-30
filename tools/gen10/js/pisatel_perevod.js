// Автор читает описание в переводе на русский; правила перевода — из таблицы (###ПЕРЕВОД###).
const kb = $('Собираем знания канала').first().json;
const r = $input.first().json || {};
const story = (r.output || [])
  .filter(i => i.type === 'message')
  .flatMap(i => (i.content || []).filter(c => c.type === 'output_text').map(c => c.text))
  .join('\n\n')
  .trim();
const rules = kb.translationRules ? '\n\nПравила перевода канала:\n' + kb.translationRules : '';
return [{
  json: {
    requestBody: {
      model: 'gpt-5',
      input: [
        { role: 'system', content: 'Переведи этот текст на русский для автора канала. Ответь только переводом.' + rules },
        { role: 'user', content: story || '(пусто)' },
      ],
    },
  },
}];
