// Итог хода: ответ Редактора + (если заказан) текст Писателя в пункте 3.
// Все дальнейшие узлы читают именно этот узел.
const base = $('Разбираем ответ редактора').first().json;
if (!base.storyBrief) return [{ json: base }];

const resp = $input.first().json || {};
const story = (resp.output || [])
  .filter(i => i.type === 'message')
  .flatMap(i => (i.content || []).filter(c => c.type === 'output_text').map(c => c.text))
  .join('\n\n')
  .trim();

if (!story) {
  const note = '⚠️ Писатель не прислал описание — попросите ещё раз.';
  return [{ json: { ...base, messageToUser: base.messageToUser ? base.messageToUser + '\n\n' + note : note } }];
}

const state = tbParseState(base.editorState);
state.items.description = story;
state.set[3] = true;
state.agreed[3] = false;
if (state.descriptionENFor !== story) { state.descriptionEN = ''; state.descriptionENFor = ''; }

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
