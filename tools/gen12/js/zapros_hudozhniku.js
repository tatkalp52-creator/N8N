// (28.10) Один запрос художнику вместо 24 узлов: все картинки (референсы, основа правки, маска) — в одном
// JSON-запросе, сколько бы их ни было. Рисуем заново или правим — решает «Что дальше?».
const it = $('Итог хода').first().json;
const edit = $('Что дальше?').first().json.next === 'edit';
const item = $input.first();
const j = item.json || {};
const bin = item.binary || {};
const toUrl = async k => {
  const buf = await this.helpers.getBinaryDataBuffer(0, k);
  let mime = (bin[k] && bin[k].mimeType) || '';
  if (!mime || mime === 'application/octet-stream') mime = 'image/png';
  return `data:${mime};base64,${buf.toString('base64')}`;
};
const keys = Object.keys(bin).filter(k => /^image_\d+$/.test(k)).sort((a, b) => Number(a.slice(6)) - Number(b.slice(6)));
const images = [];
for (const k of keys) images.push({ image_url: await toUrl(k) });
if (!images.length) throw new Error('В запрос на рисунок не пришло ни одной картинки (референсы не скачались)');
// Первая картинка правки — сама правка, остальные только референсы (механика порядка картинок).
const prompt = !edit ? (it.drawRoles || '') + (j.dallePrompt || '')
  : (j.hasMask
    ? 'Edit the first image only inside the transparent area of the mask; everything outside the mask stays exactly as it is. The other images are references only.\n\n'
    : 'Edit the first image. The other images are references only.\n\n') + (it.editRoles || '') + (j.revisionInstruction || '');
const body = { model: it.imageModel, prompt, size: it.imageSize, quality: it.imageQuality, images };
if (edit && j.hasMask && bin.mask) body.mask = { image_url: await toUrl('mask') };
return [{ json: { body, edit } }];
