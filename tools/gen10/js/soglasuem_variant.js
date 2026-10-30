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
// Повторное нажатие на уже согласованный вариант ничего не запускает
// (кнопку легко нажать дважды — иначе Редактор начинает всё заново).
const already = !!(found && found.url && found.url === String(row.ai_ApprovedImageUrl || '') &&
  ['Картинка согласована', 'Утверждено', 'Опубликовано'].includes(cur));
let statusAfter = cur;
if (cur !== 'Опубликовано') {
  const same = found && found.url === String(row.ai_ApprovedImageUrl || '');
  if (!(cur === 'Утверждено' && same)) statusAfter = 'Картинка согласована';
}
const statusReverted = cur === 'Утверждено' && statusAfter !== 'Утверждено';

return [{
  json: {
    ok: !!(found && found.url) && !already,
    already,
    variantNumber: n,
    approvedUrl: found ? found.url : '',
    statusAfter,
    confirmText: `✅ Картинка согласована (вариант ${n}).` +
      (statusReverted ? '\n\n⚠️ Статус «Утверждено» снят — после смены картинки пришлю новую сводку на ✅.' : '') +
      `\n\nID: ${ctx.projectId}`,
    notFoundText: already
      ? `Вариант ${n} уже согласован — ничего не запускаю заново.\n\nID: ${ctx.projectId}`
      : `Не нашла вариант ${n} в этом проекте — ничего не меняла.\n\nID: ${ctx.projectId}`,
    syntheticText: `[Служебное сообщение, не слова автора] Автор нажала кнопку «✅» под вариантом ${n} — это её согласование этой картинки, в таблицу оно уже записано. Вызови approve_image с variantNumber ${n}. Дальше — как в правилах канала для этого момента (SystemPrompt, раздел КАРТИНКА).`,
  }
}];
