const inc = $('Разбираем входящее').first().json;
const sheetInfo = $input.first().json || {};
const sheetName = String(sheetInfo.SheetName || '').trim();
if (!sheetName) throw new Error('Канал ' + inc.channelKey + ' не найден в Catalog');
const projectId = DateTime.now().toFormat('yyyyLLdd_HHmmss') + '_' + inc.channelKey;
return [{ json: { chatId: inc.chatId, channelKey: inc.channelKey, sheetName, projectId } }];
