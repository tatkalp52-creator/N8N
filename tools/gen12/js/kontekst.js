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

let effectRows = [];
try { effectRows = $('Читаем эффекты').all().map(i => i.json || {}); } catch (e) {}
const effects = fxRows(effectRows, inc.channelKey);

const found = !!row.sys_ProjectID && String(row.sys_ProjectID).trim() === inc.projectId;
// Метка выпуска для каждого сообщения: значок канала (Catalog) + дата выхода + имя из календаря.
// Без календаря — значок и дата создания проекта.
let calRow = {};
try { calRow = ($('Читаем календарь (метка)').all().map(i => i.json || {}).find(r => String(r.project || '').trim() === inc.projectId)) || {}; } catch (e) {}
const icon = String(catalog['Значок'] || '').trim();
const relM = String(calRow.release || '').match(/^\d{4}-(\d{2})-(\d{2})$/);
const idM = String(inc.projectId || '').match(/^\d{4}(\d{2})(\d{2})_/);
const calName = String(calRow.title_ru || calRow.title || '').trim().slice(0, 60);
const label = calName
  ? [icon, relM ? relM[2] + '.' + relM[1] : '', '· ' + calName].filter(Boolean).join(' ')
  : (idM ? [icon, 'выпуск от ' + idM[2] + '.' + idM[1]].filter(Boolean).join(' ') : icon);
const escH = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
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
    effects,
    setupProblem: !stages.length ? 'В листе «Этапы» нет строк для этого канала — не знаю, кто работает.' : '',
    status: found ? String(row.sys_Status || '').trim() : '',
    label,
    labelLine: label ? '<b>' + escH(label) + '</b>\n' : '',
    labelPlain: label ? label + '\n' : '',
  }
}];
