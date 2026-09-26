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
const urlLine = /^https?:\/\/\S+$/;
for (const key of Object.keys(tmpl)) {
  if (key.includes('tmpl_SystemPrompt')) continue;
  if (!key.includes('🖋') && !key.includes('🎨')) continue;
  const value = String(tmpl[key] || '');
  const lines = value.split('\n');
  const keep = [];
  for (const line of lines) {
    const t = line.trim();
    if (urlLine.test(t)) {
      if (key.includes('🎨')) imageUrls.push(toDirectImageUrl(t));
    } else {
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

const vectorStoreId = String(findByLabel(tmpl, 'tmpl_ChannelVectorStoreId') || '').trim();
const characterPassport = String(findByLabel(tmpl, 'tmpl_CharacterPassport') || '').trim();

return [{
  json: {
    knowledgeText,
    styleGuideUrl: imageUrls[0] || null,
    referenceUrls: imageUrls.slice(1),
    timecodeCount,
    vectorStoreId,
    characterPassport,
    translationRules,
  }
}];
