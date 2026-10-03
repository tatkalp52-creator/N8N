// Референсы художнику — список уже собран и уложен в 16 картинок в «Итог хода».
const j = $('Итог хода').first().json;
const urls = (j.drawRefUrls || []).filter(Boolean).slice(0, 16);
return urls.map((url, i) => ({ json: { ...j, refUrl: url, refIndex: i } }));
