// Всё, что знаем о проекте, в одном месте: что пришло, лист канала, строка
// проекта, шаблон канала, этапы и пункты канала. Все узлы ниже берут данные отсюда.
const inc = $('Разбираем входящее').first().json;
let catalog = {};
try { catalog = $('Находим лист канала').first().json || {}; } catch (e) {}
let row = {};
try { row = $('Читаем строку проекта').first().json || {}; } catch (e) {}
let tmpl = {};
try { tmpl = $('Читаем шаблоны канала').first().json || {}; } catch (e) {}
let stageRows = [];
try { stageRows = $('Читаем этапы').all().map(i => i.json || {}); } catch (e) {}
let itemRows = [];
try { itemRows = $('Читаем пункты').all().map(i => i.json || {}); } catch (e) {}

const found = !!row.sys_ProjectID && String(row.sys_ProjectID).trim() === inc.projectId;
const stages = stParseStages(stageRows);
const items = itParseItems(itemRows);

return [{
  json: {
    ...inc,
    sheetName: String(catalog.SheetName || '').trim(),
    found,
    row: found ? row : {},
    tmpl,
    stages,
    items,
    setupProblem: !stages.length ? 'В листе «Этапы» нет строк для этого канала — не знаю, кто работает.' : '',
    status: found ? String(row.sys_Status || '').trim() : '',
  }
}];
