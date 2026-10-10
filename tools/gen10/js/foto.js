// Фото автора → data URL, чтобы Редактор увидел саму картинку.
const buffer = await this.helpers.getBinaryDataBuffer(0, 'data');
const item = $input.first();
let mimeType = (item.binary && item.binary.data && item.binary.data.mimeType) || '';
if (!mimeType || mimeType === 'application/octet-stream') mimeType = 'image/jpeg';
return [{ json: { userImageUrl: `data:${mimeType};base64,${buffer.toString('base64')}` } }];
