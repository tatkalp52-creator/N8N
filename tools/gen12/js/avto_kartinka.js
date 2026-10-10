// После рисунка: если картинку согласовывать не нужно (этап «авто» в листе «Этапы»),
// согласуем её сами и передаём выпуск дальше.
const r = $('Итог хода').first().json;
let s = null;
try { s = $('Собираем ссылку (B)').first().json; } catch (e) {}
try { s = $('Собираем ссылку (C)').first().json; } catch (e) {}
const ok = !!(r.autoApprove && s && s.ai_ImageUrl);
return [{ json: { ok, approvedUrl: ok ? s.ai_ImageUrl : '', variantNumber: s ? s.variantNumber : null, projectId: r.projectId, sheetName: r.sheetName } }];
