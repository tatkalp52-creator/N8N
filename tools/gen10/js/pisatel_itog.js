// Итог хода: ответ Редактора + (если заказан) текст Писателя в пункте 3.
// Все дальнейшие узлы читают именно этот узел.
// «Художнику: …» приходит сюда в обход Редактора — уже готовым итогом хода.
if ($input.first().json.direct) return [{ json: $input.first().json }];
const base = $('Разбираем ответ редактора').first().json;
if (!base.storyBrief) return [{ json: base }];

const textOf = r => ((r && r.output) || [])
  .filter(i => i.type === 'message')
  .flatMap(i => (i.content || []).filter(c => c.type === 'output_text').map(c => c.text))
  .join('\n\n')
  .trim();
const story = textOf($('OpenAI: Писатель').first().json);
const storyRu = textOf($input.first().json);

if (!story) {
  const note = '⚠️ Писатель не прислал описание — попросите ещё раз.';
  return [{ json: { ...base, messageToUser: base.messageToUser ? base.messageToUser + '\n\n' + note : note } }];
}

const state = tbParseState(base.editorState);
state.items.description = story;
state.set[3] = true;
state.agreed[3] = false;
// Писатель пишет оригинал, который и уйдёт на YouTube; автору — перевод рядом.
state.descriptionEN = story;
state.descriptionENFor = story;
state.ru = state.ru || {};
if (storyRu) state.ru.description = storyRu; else delete state.ru.description;

const changedItems = base.changedItems.includes(3) ? base.changedItems : [...base.changedItems, 3];
let statusAfter = base.statusAfter;
let statusReverted = base.statusReverted;
if (statusAfter === 'Утверждено') { statusAfter = 'Картинка согласована'; statusReverted = true; }

return [{
  json: {
    ...base,
    editorState: JSON.stringify(state),
    changedItems,
    textBlockTouched: true,
    allAgreed: false,
    statusAfter,
    statusReverted,
    storyWritten: true,
  },
}];
