// ── Общий кусок движка этапов (одинаковый в нескольких узлах) ─────────────
// Движок не знает ни ролей, ни пунктов, ни имён колонок с содержанием.
// Сценарий — лист «Этапы», пункты — лист «Пункты», знания — колонки Templates
// со значком этапа. Служебные колонки (⚙️ или без значка) — механика.

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

// Служебная колонка по имени (только для ⚙️ / колонок без значка — это кнопки механики).
function findByLabel(row, label) {
  const key = Object.keys(row || {}).find(k => k.replace(/^[^a-zA-Z]+/, '') === label);
  return key ? row[key] : undefined;
}

// Значение строки служебного листа по заголовку (заголовки листов «Этапы»/«Пункты»).
function cell(row, ...names) {
  const norm = s => String(s).toLowerCase().replace(/[^a-zа-яё0-9№]+/giu, '');
  for (const nm of names) {
    const key = Object.keys(row || {}).find(k => norm(k) === norm(nm));
    if (key !== undefined && row[key] != null && String(row[key]).trim() !== '') return String(row[key]).trim();
  }
  return '';
}

// «1, 2, 4-8» / «1,2,4–8» → [1,2,4,5,6,7,8]
function parseNumbers(text) {
  const out = [];
  for (const part of String(text || '').split(/[,;\s]+/)) {
    const m = part.match(/^(\d+)\s*[-–—]\s*(\d+)$/);
    if (m) { for (let i = +m[1]; i <= +m[2]; i++) out.push(i); continue; }
    if (/^\d+$/.test(part)) out.push(+part);
  }
  return [...new Set(out)];
}

function isEmojiStart(s) { return /^\p{Extended_Pictographic}/u.test(String(s || '').trim()); }
// Значок для сравнения — без вариационного селектора (✍️ и ✍ — один значок).
function bareIcon(s) { return String(s || '').replace(/️/g, '').trim(); }

// ── Этапы ──
// Строка листа «Этапы»: Значок | Кто | С кем говорит | Согласование | Делает | Модель | Усилие
function stParseStages(rows) {
  const list = (rows || []).map(r => {
    const does = cell(r, 'Делает');
    const talksRaw = cell(r, 'С кем говорит').toLowerCase();
    return {
      icon: cell(r, 'Значок'),
      name: cell(r, 'Кто'),
      talksRaw,
      approve: !/авто/i.test(cell(r, 'Согласование')),
      picture: /картин/i.test(does),
      items: parseNumbers(does.replace(/картин\S*/gi, '')),
      model: cell(r, 'Модель'),
      effort: cell(r, 'Усилие').toLowerCase(),
    };
  }).filter(s => s.icon && s.name);
  for (const s of list) {
    if (/^автор/.test(s.talksRaw)) s.talks = 'author';
    else if (!s.talksRaw || /^[-—–]$/.test(s.talksRaw) || /^(никто|сам)/.test(s.talksRaw)) s.talks = 'none';
    else {
      const boss = list.find(b => b !== s && (b.name.toLowerCase() === s.talksRaw || bareIcon(b.icon) === bareIcon(s.talksRaw)));
      s.talks = boss ? 'boss' : 'none';
      s.boss = boss ? boss.icon : '';
    }
  }
  return list;
}

function stSubordinates(stages, stage) {
  return stages.filter(s => s.talks === 'boss' && bareIcon(s.boss) === bareIcon(stage.icon));
}

// Что этап отвечает: свои пункты + пункты подчинённых; картинка — своя или подчинённого.
function stScope(stages, stage) {
  const subs = stSubordinates(stages, stage);
  const items = [...new Set([...stage.items, ...subs.flatMap(s => s.items)])].sort((a, b) => a - b);
  return { items, picture: stage.picture || subs.some(s => s.picture), subs };
}

// ── Пункты ──
// Строка листа «Пункты»: № | Пункт | Колонки | Подсказка | Можно пусто
function itParseItems(rows) {
  return (rows || []).map(r => ({
    n: parseInt(cell(r, '№', 'Номер'), 10),
    name: cell(r, 'Пункт'),
    cols: cell(r, 'Колонки'),
    hint: cell(r, 'Подсказка'),
    canEmpty: /^да/i.test(cell(r, 'Можно пусто')),
  })).filter(i => i.n > 0 && i.name).sort((a, b) => a.n - b.n);
}

// ── Состояние выпуска (sys_EditorState) ──
function stEmptyState() {
  return { v: 2, items: {}, agreed: {}, stages: {} };
}
function stParseState(raw) {
  let p = null;
  try { p = typeof raw === 'string' ? JSON.parse(raw) : raw; } catch (e) { p = null; }
  if (!p || typeof p !== 'object' || p.v !== 2) return stEmptyState();
  const s = stEmptyState();
  s.items = p.items && typeof p.items === 'object' ? p.items : {};
  s.agreed = p.agreed && typeof p.agreed === 'object' ? p.agreed : {};
  s.stages = p.stages && typeof p.stages === 'object' ? p.stages : {};
  return s;
}
function stStage(state, icon) {
  const k = bareIcon(icon);
  state.stages[k] = state.stages[k] || { conv: '', pending: '', seen: [] };
  if (!Array.isArray(state.stages[k].seen)) state.stages[k].seen = [];
  return state.stages[k];
}

function stItemDone(state, item) {
  return state.agreed[item.n] === true;
}

// Этап готов: картинка согласована (если он за неё отвечает) и все его пункты согласованы.
function stComplete(stages, items, state, approvedUrl, stage) {
  const sc = stScope(stages, stage);
  if (sc.picture && !approvedUrl) return false;
  return sc.items.every(n => { const it = items.find(i => i.n === n); return !it || stItemDone(state, it); });
}

// Текущий этап: первый по порядку незавершённый, который сам ведёт работу (не подчинённый).
function stCurrent(stages, items, state, approvedUrl) {
  return stages.find(s => s.talks !== 'boss' && !stComplete(stages, items, state, approvedUrl, s)) || null;
}

// Обращение по значку («✍️ …») или по имени («Писателю: …»).
function stAddressed(stages, text) {
  const t = String(text || '').trim();
  for (const s of stages) {
    const ic = bareIcon(s.icon);
    if (ic && bareIcon(t).startsWith(ic)) return { stage: s, rest: bareIcon(t).slice(ic.length).replace(/^[\s:,.!—–-]+/, '') };
  }
  const first = (t.match(/^[\p{L}-]+/u) || [''])[0].toLowerCase();
  if (first.length >= 4) {
    // сначала по первому слову имени («Писателю»), потом по любому («Техническому»)
    for (const pass of [0, 1]) {
      for (const s of stages) {
        const words = s.name.toLowerCase().split(/\s+/);
        for (const word of pass === 0 ? words.slice(0, 1) : words.slice(1)) {
          if (word.length < 5) continue;
          const stem = word.slice(0, word.length - 2);
          if (first.startsWith(stem) && first.length <= word.length + 2) {
            // остальные слова имени («Техническому писателю: …») тоже убираем
            let rest = t.slice(first.length).replace(/^[\s:,.!—–-]+/, '');
            for (const w of words.slice(words.indexOf(word) + 1)) {
              const next = (rest.match(/^[\p{L}-]+/u) || [''])[0];
              if (w.length >= 5 && next.toLowerCase().startsWith(w.slice(0, w.length - 2))) rest = rest.slice(next.length).replace(/^[\s:,.!—–-]+/, '');
            }
            return { stage: s, rest };
          }
        }
      }
    }
  }
  return null;
}

// ── Знания этапа из Templates: все колонки со значком этапа ──
// 📍 в заголовке: колонка из блоков «НАЗВАНИЕ: слово, слово» (через пустую строку);
// блок берётся, только если одно из слов встретилось в задании (ловится по началу слова).
// Строка-ссылка — картинка; строка сразу под ссылкой — её роль.
function kbIsService(key) { return !isEmojiStart(key) || key.includes('⚙'); }
function kbLabel(key) { return key.replace(/^[^a-zA-Z]+/, '').replace(/^tmpl_/, ''); }
const URL_LINE = /^https?:\/\/\S+$/;
function toDirectImageUrl(url) {
  const m = url.match(/\/d\/([a-zA-Z0-9_-]+)/) || url.match(/[?&]id=([a-zA-Z0-9_-]+)/);
  return m ? 'https://lh3.googleusercontent.com/d/' + m[1] + '=s2000' : url;
}
function triggered(words, text) {
  const low = String(text || '').toLowerCase();
  const esc = w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return words.some(w => w && new RegExp('(^|[^\\p{L}\\p{N}])' + esc(w), 'u').test(low));
}
// Текст и картинки одного куска колонки.
function kbSplit(text) {
  const lines = String(text || '').split('\n');
  const keep = [];
  const images = [];
  let last = null;
  for (const line of lines) {
    const t = line.trim();
    if (URL_LINE.test(t)) { last = { url: toDirectImageUrl(t), role: '' }; images.push(last); continue; }
    if (t && last && !last.role) { last.role = t; continue; }
    if (t) last = null;
    keep.push(line);
  }
  return { text: keep.join('\n').trim(), images };
}
function kbForStage(tmpl, icon, taskText, opts) {
  const o = opts || {};
  const ic = bareIcon(icon);
  const parts = [];
  const images = [];
  const notesKey = Object.keys(tmpl || {}).find(k => !kbIsService(k) && bareIcon(k).includes(ic) && k.includes('📝')) || '';
  for (const key of Object.keys(tmpl || {})) {
    if (kbIsService(key)) continue;
    if (!bareIcon(key.match(/^[^a-zA-Z]*/)[0]).includes(ic)) continue;
    const raw = String(tmpl[key] == null ? '' : tmpl[key]);
    if (!raw.trim()) continue;
    let chunks = [raw];
    if (key.includes('📍')) {
      chunks = raw.split(/\n\s*\n/).filter(b => {
        const head = b.trim().split('\n')[0] || '';
        const i = head.indexOf(':');
        const words = i > 0 ? [head.slice(0, i), ...head.slice(i + 1).split(',')].map(w => w.trim().toLowerCase()) : [];
        return words.length && triggered(words, taskText);
      });
    }
    const texts = [];
    for (let c of chunks) {
      // у 📍-блока первая строка — название и слова-триггеры, это механика, не знание
      if (key.includes('📍')) c = c.trim().split('\n').slice(1).join('\n');
      const sp = kbSplit(c);
      if (sp.text) texts.push(sp.text);
      images.push(...sp.images.map(i => ({ ...i, place: key.includes('📍') })));
    }
    if (texts.length) parts.push((o.labels === false ? '' : kbLabel(key) + ':\n') + texts.join('\n\n'));
  }
  return { text: parts.join('\n\n'), images, notesKey, notes: notesKey ? String(tmpl[notesKey] || '') : '' };
}

// ── Пункты: показ и запись в таблицу ──
function itValue(state, n) { const v = state.items[n]; return v && typeof v === 'object' ? v : { text: '', ru: '' }; }
function itShow(state, item) {
  const v = itValue(state, item.n);
  if (!(item.n in state.items)) return '';
  if (!v.text) return '— пусто';
  if (!v.ru) return v.text;
  return v.text.includes('\n') || v.text.length > 200 ? `${v.text}\n\n— Перевод для автора —\n${v.ru}` : `${v.text} (${v.ru})`;
}

// Колонки пункта: «a, b» — одно значение в обе; «a | b» — значение делится по «|»;
// одна колонка у нескольких пунктов — значения склеиваются через пустую строку по порядку.
function itFields(items, state) {
  const acc = {};
  const order = [];
  const put = (col, val) => { if (!(col in acc)) { acc[col] = []; order.push(col); } if (val) acc[col].push(val); };
  for (const it of items) {
    const text = itValue(state, it.n).text || '';
    if (it.cols.includes('|')) {
      const cols = it.cols.split('|').map(c => c.trim()).filter(Boolean);
      const vals = text.split('|').map(v => v.trim());
      cols.forEach((c, i) => put(c, vals[i] || ''));
    } else {
      for (const c of it.cols.split(',').map(c => c.trim()).filter(Boolean)) put(c, text);
    }
  }
  const out = {};
  for (const c of order) out[c] = acc[c].join('\n\n');
  return out;
}

// Стена перед сборщиком: проверяем то, что РЕАЛЬНО лежит в таблице.
// Обязательны колонки пунктов, которые нельзя оставить пустыми.
function validateRow(row, items, opts) {
  const o = opts || {};
  const problems = [];
  const val = k => String(row[k] == null ? '' : row[k]).trim();
  for (const it of items) {
    if (it.canEmpty) continue;
    for (const c of it.cols.split(/[|,]/).map(c => c.trim()).filter(Boolean)) {
      if (!val(c) && !problems.includes(`${c} пустая`)) problems.push(`${c} пустая (пункт ${it.n}. ${it.name})`);
    }
  }
  if (!val('ai_ApprovedImageUrl')) problems.push('ai_ApprovedImageUrl пустая (нет согласованной картинки)');
  // Метка [Timecodes] — место, куда сборщик вставит тайм-коды (механика 04_Video).
  if (val('ai_TimecodeNames') && val('ai_Description') && !/\[?Timecodes\]?/i.test(val('ai_Description'))) {
    problems.push('в ai_Description нет метки [Timecodes]');
  }
  if (o.needApproved && val('sys_Status') !== 'Утверждено') problems.push(`статус «${val('sys_Status') || 'пусто'}», а не «Утверждено»`);
  if (o.needTracks && !val('sys_AudioZipUrl')) problems.push('sys_AudioZipUrl пустая (нет ссылки на треки)');
  return problems;
}

// Референсы художнику: картинки из колонок 🎨 — до 16 (в правке 15).
// Картинки 📍-мест (названных в задании) остаются, общие сокращаются с конца.
function artRefs(kbImages, placeImages) {
  const fit = max => {
    const room = Math.max(1, max - placeImages.length);
    return [...kbImages.slice(0, room), ...placeImages].slice(0, max);
  };
  const roles = (list, shift) => {
    const parts = list.map((r, i) => (r.role ? `Image ${i + 1 + shift} — ${r.role}.` : '')).filter(Boolean);
    return parts.length ? 'Reference images: ' + parts.join(' ') + '\n\n' : '';
  };
  const draw = fit(16);
  const edit = fit(15);
  return { drawRefUrls: draw.map(r => r.url), drawRoles: roles(draw, 0), editRefUrls: edit.map(r => r.url), editRoles: roles(edit, 1) };
}
// Применяем предложения этапа к пунктам — только в пределах его пунктов (scope).
// Изменённый пункт снова ждёт согласования. Возвращает номера изменённых пунктов.
function itApply(state, items, scope, args, autoAgree) {
  const changed = [];
  const inScope = n => scope.includes(n) && items.some(i => i.n === n);
  for (const p of (Array.isArray(args.items) ? args.items : [])) {
    const n = parseInt(p && p.n, 10);
    if (!inScope(n)) continue;
    let text = String(p.text == null ? '' : p.text).trim();
    if (text === '-') text = '';
    const ru = String(p.ru == null ? '' : p.ru).trim();
    const old = state.items[n];
    if (!old || old.text !== text || (ru && old.ru !== ru)) {
      if (!old || old.text !== text) { state.agreed[n] = false; changed.push(n); }
      state.items[n] = { text, ru: ru || (old && old.text === text ? old.ru || '' : '') };
    }
    if (autoAgree) state.agreed[n] = true;
  }
  for (const raw of (args.reopen || [])) {
    const n = parseInt(raw, 10);
    if (inScope(n) && state.agreed[n]) { state.agreed[n] = false; if (!changed.includes(n)) changed.push(n); }
  }
  for (const raw of (args.agreed || [])) {
    const n = parseInt(raw, 10);
    if (!inScope(n)) continue;
    const it = items.find(i => i.n === n);
    if (!(n in state.items) && it.canEmpty) state.items[n] = { text: '', ru: '' };
    if (n in state.items) state.agreed[n] = true;
  }
  return changed;
}

// Задание художнику: знания колонок его значка (без подписей) + слова задания.
// Новая картинка — правила и описание мест + сцена; правка — только слова правки.
function artBuild(ctx, stage, task, edit, variantNumber) {
  const row = ctx.row || {};
  const tmpl = ctx.tmpl || {};
  let variants = [];
  try { variants = JSON.parse(row.ai_ImageVariants || '[]'); } catch (e) { variants = []; }
  if (!Array.isArray(variants)) variants = [];
  const last = variants.length ? variants[variants.length - 1] : null;
  const kb = kbForStage(tmpl, stage.icon, task, { labels: false });
  const refs = artRefs(kb.images.filter(i => !i.place), kb.images.filter(i => i.place));
  const r = {
    action: edit ? 'revise_point' : 'ready_to_draw',
    messageToUser: '',
    dallePrompt: '', revisionInstruction: '', revisionIsNewVariant: true,
    revisionTargetImageUrl: String(row.ai_ImageUrl || ''), revisionTargetVariantNumber: last ? last.n : 1,
    imageModel: stage.model || String(findByLabel(tmpl, 'tmpl_ImageModel') || '').trim() || 'gpt-image-2',
    ...refs,
  };
  if (edit) {
    const target = variantNumber ? variants.find(v => Number(v.n) === Number(variantNumber)) : last;
    if (target && target.url) { r.revisionTargetImageUrl = target.url; r.revisionTargetVariantNumber = target.n; }
    else { r.action = 'chat'; r.messageToUser = variantNumber ? `Не нашла вариант ${variantNumber}. Есть: ${variants.map(v => v.n).join(', ') || 'пока ни одного'}.` : 'Править пока нечего — сначала нужна картинка.'; }
    r.revisionInstruction = task;
  } else {
    r.dallePrompt = [kb.text, task].filter(Boolean).join('\n\n');
  }
  if (r.action !== 'chat' && !String(task || '').trim()) { r.action = 'chat'; r.messageToUser = 'Напишите задание словами.'; }
  return r;
}
// ── конец общего куска ─────────────────────────────────────────────────────
