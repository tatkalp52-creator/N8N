// Кнопка "✅" под конкретным вариантом: номер варианта приходит в самой
// кнопке, поэтому гадать, какой вариант имелся в виду, не нужно.
const ctx = $('Контекст проекта').first().json;
const row = ctx.row || {};
const n = ctx.variantNumber;
let variants = [];
try { variants = JSON.parse(row.ai_ImageVariants || '[]'); } catch (e) { variants = []; }
if (!Array.isArray(variants)) variants = [];
const found = variants.find(v => Number(v.n) === Number(n));

const cur = ctx.status;
let statusAfter = cur;
if (cur !== 'Опубликовано') {
  const same = found && found.url === String(row.ai_ApprovedImageUrl || '');
  if (!(cur === 'Утверждено' && same)) statusAfter = 'Картинка согласована';
}
const statusReverted = cur === 'Утверждено' && statusAfter !== 'Утверждено';

return [{
  json: {
    ok: !!(found && found.url),
    variantNumber: n,
    approvedUrl: found ? found.url : '',
    statusAfter,
    confirmText: `✅ Картинка согласована (вариант ${n}).` +
      (statusReverted ? '\n\n⚠️ Статус «Утверждено» снят — после смены картинки пришлю новую сводку на ✅.' : '') +
      `\n\nID: ${ctx.projectId}`,
    notFoundText: `Не нашла вариант ${n} в этом проекте — ничего не меняла.\n\nID: ${ctx.projectId}`,
    syntheticText: `[Служебное сообщение, не слова автора] Автор нажала кнопку «✅» под вариантом ${n} — это её согласование этой картинки, в таблицу оно уже записано. Вызови approve_image с variantNumber ${n} и в том же вызове передай в items все пункты текстового блока, кроме описания, и в storyBrief — задание писателю на описание.`,
  }
}];
