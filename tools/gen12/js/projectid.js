// Новый проект: ID и первое сообщение. Из календаря — с меткой выпуска и сутью повода.
const inc = $('Разбираем входящее').first().json;
const sheetInfo = $input.first().json || {};
const sheetName = String(sheetInfo.SheetName || '').trim();
if (!sheetName) throw new Error('Канал ' + inc.channelKey + ' не найден в Catalog');
const projectId = DateTime.now().toFormat('yyyyLLdd_HHmmss') + '_' + inc.channelKey;
const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const cal = inc.cal || null;
const icon = String(sheetInfo['Значок'] || '').trim();
const rel = cal ? String(cal.release || '').match(/^\d{4}-(\d{2})-(\d{2})$/) : null;
const label = [icon, rel ? rel[2] + '.' + rel[1] : '', cal && cal.title ? '· ' + cal.title : ''].filter(Boolean).join(' ').trim();
const lines = [];
if (label) lines.push('<b>' + esc(label) + '</b>');
lines.push('Проект создан ✅' + (cal ? ' Поехали!' : ''));
if (cal && cal.about) lines.push('', 'Повод: ' + esc(cal.about));
lines.push('', 'ID: ' + projectId);
return [{ json: { chatId: inc.chatId, channelKey: inc.channelKey, sheetName, projectId, calId: cal ? cal.id : '', createdText: lines.join('\n') } }];
