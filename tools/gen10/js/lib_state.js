// ── Общий кусок (одинаковый в нескольких узлах этого канваса) ──────────────
// Текстовый блок: 8 пунктов с ЖЁСТКО закреплёнными номерами. Номер никогда
// не переприсваивается: 3 — это всегда "Описание".
const TB_ITEMS = [
  { n: 1, name: 'Оверлей', keys: ['overlayText', 'overlayPosition'] },
  { n: 2, name: 'Название', keys: ['title'] },
  { n: 3, name: 'Описание', keys: ['description'] },
  { n: 4, name: 'Тайм-коды', keys: ['timecodes'] },
  { n: 5, name: 'Подвал', keys: ['footer'] },
  { n: 6, name: 'Хэштеги', keys: ['hashtags'] },
  { n: 7, name: 'Теги', keys: ['tags'] },
  { n: 8, name: 'Закреплённый комментарий', keys: ['pinnedComment'] },
];
// Пункты, которые можно осознанно оставить пустыми (например, гайд без оверлея).
const TB_CAN_BE_EMPTY = [1, 8];

function tbEmptyState() {
  return {
    v: 1,
    items: { overlayText: '', overlayPosition: '', title: '', description: '', timecodes: [], footer: '', hashtags: '', tags: '', pinnedComment: '' },
    set: {},
    agreed: {},
    descriptionEN: '',
    descriptionENFor: '',
    seenImages: [],
    ru: {},
  };
}

function tbParseState(raw) {
  const s = tbEmptyState();
  if (!raw) return s;
  let p;
  try { p = typeof raw === 'string' ? JSON.parse(raw) : raw; } catch (e) { return s; }
  if (!p || typeof p !== 'object') return s;
  Object.assign(s.items, p.items || {});
  if (!Array.isArray(s.items.timecodes)) s.items.timecodes = [];
  s.set = p.set || {};
  s.agreed = p.agreed || {};
  s.descriptionEN = p.descriptionEN || '';
  s.descriptionENFor = p.descriptionENFor || '';
  s.seenImages = Array.isArray(p.seenImages) ? p.seenImages : [];
  s.ru = (p.ru && typeof p.ru === 'object') ? p.ru : {};
  return s;
}

function tbAllAgreed(s) {
  return TB_ITEMS.every(it => s.agreed[it.n] === true);
}

function tbPositionRu(p) {
  return { left: 'слева', right: 'справа', center: 'по центру' }[String(p || '').toLowerCase()] || (p || '');
}

// Текст одного пункта для показа автору (без номера и названия).
// Русский перевод (state.ru) показывается рядом в скобках — только автору;
// в таблицу и на YouTube уходит лишь сам текст пункта (state.items).
function tbItemText(s, n) {
  const it = s.items;
  const ru = s.ru || {};
  const tr = (v) => (v ? ` (${v})` : '');
  switch (n) {
    case 1:
      if (!s.set[1]) return '';
      return it.overlayText ? `${it.overlayText}${tr(ru.overlayText)} — ${tbPositionRu(it.overlayPosition) || 'позиция не указана'}` : '— без оверлея';
    case 2: return it.title ? it.title + tr(ru.title) : '';
    case 3: return (it.description || '') + (it.description && ru.description ? `\n\n— Перевод для автора —\n${ru.description}` : '');
    case 4: return (it.timecodes || []).map((t, i) => `${i + 1}. ${t}${tr((ru.timecodes || [])[i])}`).join('\n');
    case 5: return it.footer || '';
    case 6: return it.hashtags || '';
    case 7: return it.tags || '';
    case 8:
      if (!s.set[8]) return '';
      return it.pinnedComment ? it.pinnedComment + (ru.pinnedComment ? `\n(${ru.pinnedComment})` : '') : '— без закреплённого комментария';
  }
  return '';
}

function escapeHtml(t) {
  return String(t == null ? '' : t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// Режем длинный текст на куски под лимит Телеграма (4096), стараясь по переносу строки.
function splitForTelegram(text, limit) {
  const LIMIT = limit || 3800;
  const chunks = [];
  let rest = String(text || '');
  while (rest.length > LIMIT) {
    let cut = rest.lastIndexOf('\n', LIMIT);
    if (cut < LIMIT * 0.5) cut = LIMIT;
    chunks.push(rest.slice(0, cut));
    rest = rest.slice(cut).replace(/^\n+/, '');
  }
  if (rest.length) chunks.push(rest);
  if (!chunks.length) return [''];
  // ID проекта — в КАЖДОЙ части: автор может ответить (reply) на любую.
  const idm = String(text || '').match(/\n\nID: (\S+)\s*$/);
  if (idm && chunks.length > 1) {
    for (let i = 0; i < chunks.length - 1; i++) chunks[i] += `\n\n(продолжение ниже)\nID: ${idm[1]}`;
  }
  return chunks;
}

function findByLabel(row, label) {
  const key = Object.keys(row || {}).find(k => k.replace(/^[^a-zA-Z]+/, '') === label);
  return key ? row[key] : undefined;
}

// Барьер перед сборщиком: проверяем то, что РЕАЛЬНО лежит в таблице (строку
// перечитываем заново перед проверкой), а не то, что мы "вроде бы записали".
function validateForAssembler(row, tmpl, opts) {
  const o = opts || {};
  const problems = [];
  const val = k => String(row[k] == null ? '' : row[k]).trim();

  let required = ['overlayPosition', 'title', 'hashtags', 'tags', 'description'];
  const rawReq = findByLabel(tmpl, 'tmpl_RequiredTechFields');
  if (rawReq && String(rawReq).trim()) {
    required = String(rawReq).split(',').map(x => x.trim()).filter(Boolean);
  }
  const colFor = {
    overlayText: 'ai_OverlayText', overlayPosition: 'ai_OverlayPosition', title: 'ai_Title',
    hashtags: 'ai_Hashtags', tags: 'ai_Tags', description: 'ai_Description', pinnedComment: 'ai_PinnedComment',
  };
  for (const key of required) {
    const col = colFor[key] || key;
    if (!val(col)) problems.push(`${col} пустая`);
  }
  if (!val('ai_ApprovedImageUrl')) problems.push('ai_ApprovedImageUrl пустая (нет согласованной картинки)');
  if (!val('ai_DescriptionEN')) problems.push('ai_DescriptionEN пустая (нет английского описания)');
  if (val('ai_Description') && !/\[?Timecodes\]?/i.test(val('ai_Description'))) {
    problems.push('в ai_Description нет метки [Timecodes]');
  }
  if (o.needApproved && val('sys_Status') !== 'Утверждено') {
    problems.push(`статус «${val('sys_Status') || 'пусто'}», а не «Утверждено»`);
  }
  if (o.needTracks && !val('sys_AudioZipUrl')) problems.push('sys_AudioZipUrl пустая (нет ссылки на треки)');
  return problems;
}
// ── конец общего куска ─────────────────────────────────────────────────────

// Референсы художнику: общие из таблицы + картинки мест, чьи слова-триггеры
// встретились в задании («кухн» ловит «кухня», «на кухне»…). Модель берёт до 16
// картинок; в правке одно место занимает сама картинка. Не помещается — сокращаем
// общие с конца (style guide остаётся первым), места оставляем.
function tbPickRefs(kb, text) {
  const low = String(text || '').toLowerCase();
  const esc = w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const places = (kb.locations || []).filter(l =>
    (l.triggers || []).some(w => new RegExp('(^|[^\\p{L}\\p{N}])' + esc(w), 'u').test(low)));
  const base = kb.baseRefs || [];
  const loc = places.flatMap(p => p.refs || []);
  const fit = max => {
    const room = Math.max(1, max - loc.length);
    return [...base.slice(0, room), ...loc].slice(0, max);
  };
  const roles = (list, shift) => {
    const parts = list.map((r, i) => (r.role ? `Image ${i + 1 + shift} — ${r.role}.` : '')).filter(Boolean);
    return parts.length ? 'Reference images: ' + parts.join(' ') + '\n\n' : '';
  };
  const draw = fit(16);
  const edit = fit(15);
  return {
    places,
    drawRefUrls: draw.map(r => r.url),
    drawRoles: roles(draw, 0),
    editRefUrls: edit.map(r => r.url),
    editRoles: roles(edit, 1),
  };
}
