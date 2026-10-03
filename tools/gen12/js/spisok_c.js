// Правка: первая картинка — сама правка (image_0), за ней референсы — до 15.
const parsed = $('Итог хода').first().json;
const urls = (parsed.editRefUrls || []).filter(Boolean).slice(0, 15);
return urls.map((url, i) => ({ json: {
  refUrl: url, refIndex: i + 1, revisionInstruction: parsed.revisionInstruction,
  projectId: parsed.projectId, chatId: parsed.chatId, sheetName: parsed.sheetName,
} }));
