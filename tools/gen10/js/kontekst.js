// Собираем в одном месте всё, что знаем о проекте: что пришло, лист канала,
// строка проекта и шаблон канала. Все узлы ниже берут данные отсюда.
const inc = $('Разбираем входящее').first().json;
let catalog = {};
try { catalog = $('Находим лист канала').first().json || {}; } catch (e) {}
let row = {};
try { row = $('Читаем строку проекта').first().json || {}; } catch (e) {}
let tmpl = {};
try { tmpl = $('Читаем шаблоны канала').first().json || {}; } catch (e) {}

const found = !!row.sys_ProjectID && String(row.sys_ProjectID).trim() === inc.projectId;

return [{
  json: {
    ...inc,
    sheetName: String(catalog.SheetName || '').trim(),
    found,
    row: found ? row : {},
    tmpl,
    status: found ? String(row.sys_Status || '').trim() : '',
  }
}];
