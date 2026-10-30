// Style guide первым, затем референсы и (если в задании названо место) картинки
// места — список уже собран и уложен в 16 картинок в «Разбираем ответ редактора»
// / «Задание художнику напрямую» (tbPickRefs). Сколько ссылок — столько картинок.
const j = $('Парсим ответ редактора').first().json;
const urls = (j.drawRefUrls || [j.styleGuideUrl, ...(j.referenceUrls || [])]).filter(Boolean).slice(0, 16);

return urls.map((url, i) => ({
  json: { ...j, refUrl: url, refIndex: i }
}));
