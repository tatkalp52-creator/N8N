// База канала из таблицы Templates: все колонки со значками 🖋 и 🎨.
// Новая колонка с тем же значком попадёт сюда сама, без правки кода.
const ctx = $('Контекст проекта').first().json;
const tmpl = ctx.tmpl || {};
if (!tmpl || !Object.keys(tmpl).length) {
  throw new Error('Шаблон для канала ' + ctx.channelKey + ' не найден в Templates');
}

function stripLabel(key) { return key.replace(/^[^a-zA-Z]+/, ''); }

function extractSection(text, tag) {
  if (!text) return '';
  const re = new RegExp('###' + tag + '###([\\s\\S]*?)###/' + tag + '###');
  const m = text.match(re);
  return m ? m[1].trim() : '';
}

// Google Drive отдаёт HTML-страницу на обычной ссылке — приводим к прямой.
function toDirectImageUrl(url) {
  const match = url.match(/\/d\/([a-zA-Z0-9_-]+)/) || url.match(/[?&]id=([a-zA-Z0-9_-]+)/);
  return match ? 'https://lh3.googleusercontent.com/d/' + match[1] + '=s2000' : url;
}

const textParts = [];
const imageUrls = [];
// Роль картинки — строка, написанная в ячейке сразу под её ссылкой (например,
// «манера и размер героя в кадре»). Художнику уходит «Image N — роль».
const imageRoles = [];
const urlLine = /^https?:\/\/\S+$/;
for (const key of Object.keys(tmpl)) {
  if (key.includes('tmpl_SystemPrompt')) continue;
  // Картинки локаций уходят художнику только по словам задания (см. ниже), не всегда.
  if (key.includes('tmpl_LocationImages')) continue;
  if (!key.includes('🖋') && !key.includes('🎨')) continue;
  const value = String(tmpl[key] || '');
  const lines = value.split('\n');
  const keep = [];
  let lastImage = -1;
  for (const line of lines) {
    const t = line.trim();
    if (urlLine.test(t)) {
      if (key.includes('🎨')) { imageUrls.push(toDirectImageUrl(t)); imageRoles.push(''); lastImage = imageUrls.length - 1; }
    } else {
      if (t && lastImage >= 0 && !imageRoles[lastImage]) imageRoles[lastImage] = t;
      else if (t) lastImage = -1;
      keep.push(line);
    }
  }
  const text = keep.join('\n').trim();
  if (text) textParts.push(stripLabel(key) + ':\n' + text);
}

// Все три раздела SystemPrompt — теперь это один Редактор на все этапы.
const spKey = Object.keys(tmpl).find(k => k.includes('tmpl_SystemPrompt'));
const sp = spKey ? String(tmpl[spKey] || '') : '';
const sections = [
  ['КАРТИНКА', 'этап картинки'],
  ['ОПИСАНИЕ', 'описание'],
  ['ТЕХНИЧЕСКОЕ', 'техническая часть: оверлей, название, подвал, хэштеги, теги'],
].map(([tag, label]) => {
  const body = extractSection(sp, tag);
  return body ? `SystemPrompt (${label}):\n${body}` : '';
}).filter(Boolean);

const knowledgeText = [...sections, ...textParts].join('\n\n');

// Правила перевода описания — тоже из таблицы (раздел ###ПЕРЕВОД### в SystemPrompt).
const translationRules = extractSection(sp, 'ПЕРЕВОД');

let timecodeCount = parseInt(findByLabel(tmpl, 'tmpl_TimecodeCount'), 10);
if (!timecodeCount || timecodeCount < 1) timecodeCount = 25;

// Роли референсов для художника. Рисование: Image 1.. = референсы по порядку.
// Правка: Image 1 = текущая картинка, референсы сдвигаются на один.
const MAX_REFS = 16;
function rolesText(shift) {
  const parts = imageRoles.slice(0, MAX_REFS - shift)
    .map((r, i) => (r ? `Image ${i + 1 + shift} — ${r}.` : ''))
    .filter(Boolean);
  return parts.length ? 'Reference images: ' + parts.join(' ') + '\n\n' : '';
}
const referenceRolesDraw = rolesText(0);
const referenceRolesEdit = rolesText(1);
// Модель художника — из таблицы (колонка tmpl_ImageModel); пусто — прежняя.
const imageModel = String(findByLabel(tmpl, 'tmpl_ImageModel') || '').trim() || 'gpt-image-2';
// Постоянные правила для прямых заданий «Художнику: …» — из таблицы (колонка tmpl_ArtistRules); пусто — без них.
const artistRules = String(findByLabel(tmpl, 'tmpl_ArtistRules') || '').trim();

// Локации: колонка tmpl_LocationImages, по блоку на место.
//   KITCHEN: кухн, kitchen        ← название и слова-триггеры (ловятся по началу слова)
//   https://…                     ← картинки места
//   роль картинки                 ← строка сразу под ссылкой
// Текст места — строки паспортов локаций (tmpl_LocationPassports), начинающиеся с названия.
const locPassportLines = String(findByLabel(tmpl, 'tmpl_LocationPassports') || '').split('\n').map(l => l.trim()).filter(Boolean);
const locations = [];
{
  let cur = null;
  let lastRef = null;
  let afterBlank = true;
  for (const raw of String(findByLabel(tmpl, 'tmpl_LocationImages') || '').split('\n')) {
    const t = raw.trim();
    if (!t) { afterBlank = true; lastRef = null; continue; }
    if (urlLine.test(t)) {
      if (cur) { lastRef = { url: toDirectImageUrl(t), role: '' }; cur.refs.push(lastRef); }
    } else if (lastRef && !lastRef.role) {
      lastRef.role = t;
    } else if ((afterBlank || !cur) && t.includes(':')) {
      const name = t.slice(0, t.indexOf(':')).trim();
      const triggers = [name, ...t.slice(t.indexOf(':') + 1).split(',')].map(w => w.trim().toLowerCase()).filter(Boolean);
      const passport = locPassportLines.filter(l => l.toUpperCase().startsWith(name.toUpperCase())).join('\n');
      cur = { name, triggers, refs: [], passport };
      locations.push(cur);
      lastRef = null;
    }
    afterBlank = false;
  }
}
const baseRefs = imageUrls.map((url, i) => ({ url, role: imageRoles[i] || '' }));

const vectorStoreId = String(findByLabel(tmpl, 'tmpl_ChannelVectorStoreId') || '').trim();
const characterPassport = String(findByLabel(tmpl, 'tmpl_CharacterPassport') || '').trim();
// Правила описания для Писателя — раздел ОПИСАНИЕ в SystemPrompt.
const writerRules = extractSection(sp, 'ОПИСАНИЕ');
// Писателю — колонки со значком ✍️ (значок = получатель), в порядке таблицы.
const writerWorld = Object.keys(tmpl)
  .filter(k => k.includes('✍'))
  .map(k => {
    const v = String(tmpl[k] || '').trim();
    return v ? stripLabel(k) + ':\n' + v : '';
  }).filter(Boolean).join('\n\n');

return [{
  json: {
    knowledgeText,
    artistRules,
    styleGuideUrl: imageUrls[0] || null,
    referenceUrls: imageUrls.slice(1),
    baseRefs,
    locations,
    timecodeCount,
    vectorStoreId,
    characterPassport,
    writerRules,
    referenceRolesDraw,
    referenceRolesEdit,
    imageModel,
    writerWorld,
    translationRules,
  }
}];
