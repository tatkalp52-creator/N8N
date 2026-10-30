// Правка: первая картинка — сама правка (image_0), за ней style guide, референсы
// и картинки места — до 15, чтобы вместе с правкой было не больше 16.
const parsed = $('Парсим ответ редактора').first().json;
const urls = (parsed.editRefUrls || [parsed.styleGuideUrl, ...(parsed.referenceUrls || [])]).filter(Boolean).slice(0, 15);

return urls.map((url, i) => ({
  json: {
    refUrl: url,
    refIndex: i + 1,
    revisionInstruction: parsed.revisionInstruction,
    projectId: parsed.projectId,
    chatId: parsed.chatId,
    sheetName: parsed.sheetName,
  }
}));
