// Текущая картинка (image_0) скачана раньше; здесь подмешиваем к ней референсы
// (image_1, image_2, ...) и, если автор прислала обводку, маску правки (mask).
// Маска относится к первой картинке: прозрачное — можно менять, остальное — как было.
const curItem = $('Скачиваем текущую картинку (C)').first();
const extra = $input.first();

const binary = { image_0: curItem.binary.image_0 };
Object.assign(binary, extra.binary || {});

let hasMask = false;
try {
  const m = $('Сервер: маска').first();
  if (m && m.binary && m.binary.mask) { binary.mask = m.binary.mask; hasMask = true; }
} catch (e) {}

const imageCount = 1 + (extra.json.extraCount || 0);

return [{
  json: {
    revisionInstruction: extra.json.revisionInstruction,
    projectId: extra.json.projectId,
    chatId: extra.json.chatId,
    sheetName: extra.json.sheetName,
    imageCount,
    hasMask,
  },
  binary
}];
