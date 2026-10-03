// Задание Писателю: только то, что нужно для истории. Правила описания
// (раздел ОПИСАНИЕ) и колонки со значком ✍️ — из таблицы; бланка на 8 пунктов,
// прошлых глав и прежнего черновика здесь нет.
const b = $('Разбираем ответ редактора').first().json;
const ctx = $('Контекст проекта').first().json;
const kb = $('Собираем знания канала').first().json;
const row = ctx.row || {};
const state = tbParseState(b.editorState);
const approvedUrl = b.resolvedApprovedImageUrl || String(row.ai_ApprovedImageUrl || '').trim();

const instructions = [
  `Ты — писатель канала "${ctx.sheetName}". Ты пишешь описание выпуска — историю к согласованной картинке. Правила, голос и мир героя — ниже, из таблицы канала. Ответь только текстом истории, без заголовка и пояснений.`,
  kb.writerRules ? 'ПРАВИЛА ОПИСАНИЯ:\n' + kb.writerRules : '',
  kb.writerWorld || '',
].filter(Boolean).join('\n\n');

let task = 'ЗАДАНИЕ ОТ РЕДАКТОРА:\n' + b.storyBrief;
if (row.ai_UserBrief) task += '\n\nИзначальный бриф автора: ' + row.ai_UserBrief;
if (b.storyKeep && state.items.description) {
  task += '\n\nИз прежнего текста автор похвалила: ' + b.storyKeep +
    '\n\nПрежний текст — только чтобы взять похваленное, остальное пиши заново:\n' + state.items.description;
}
const content = [{ type: 'input_text', text: task }];
if (approvedUrl) {
  content.push({ type: 'input_text', text: '(Согласованная картинка выпуска:)' });
  content.push({ type: 'input_image', image_url: approvedUrl });
}

return [{
  json: {
    requestBody: {
      model: 'gpt-5',
      reasoning: { effort: 'high' },
      instructions,
      input: [{ role: 'user', content }],
    },
  },
}];
