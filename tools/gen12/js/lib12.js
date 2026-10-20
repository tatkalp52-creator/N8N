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
      // «Картинка: с сеткой» — этап видит картинку с сеткой процентов (чтобы точно называть места)
      grid: /сетк/i.test(cell(r, 'Картинка')),
      // «Справочник: Эффекты» — этап видит каталог эффектов (лист «Эффекты», столбец своего канала)
      ref: cell(r, 'Справочник'),
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

// ── Эффекты ──
// Лист «Эффекты»: Семейство | Эффект | Механика | Строка для сборщика | Как размечать | Ручки | Статус |
// столбец на канал (заголовок — ключ канала). Строки без «Механики» — пояснения для человека.
function fxRows(rows, channelKey) {
  return (rows || []).map(r => ({
    family: cell(r, 'Семейство'), name: cell(r, 'Эффект'), mech: cell(r, 'Механика'),
    line: cell(r, 'Строка для сборщика'), marks: cell(r, 'Как размечать'), knobs: cell(r, 'Ручки'),
    status: cell(r, 'Статус'), value: String((r || {})[channelKey] == null ? '' : r[channelKey]).trim(),
  })).filter(e => e.mech && e.name);
}
// для сборщика: механика → ручки канала (пустая клетка — эффект каналу не нужен)
function fxTableFor(effects) {
  return (effects || []).filter(e => e.value).map(e => ({ mech: e.mech, knobs: e.value }));
}
function fxCatalogText(effects) {
  return (effects || []).map(e => `- ${e.family} · ${e.name}: строка «${e.line}»; разметка: ${e.marks}; ручки: ${e.knobs}; ` +
    `статус: ${e.status}; на этом канале: ${e.value || 'не используется'}`).join('\n');
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
    // «Превью: оживление» — после изменения пункта автору приходит картинка-превью от сборщика
    preview: cell(r, 'Превью').toLowerCase(),
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

// Диспетчер согласования: короткое одобрение автора («ок», «9 ок», «всё ок», «👍») отмечает
// пункты этапа согласованными сам — не дожидаясь, вызовет ли модель инструмент.
// Возвращает номера, которые одобрены (пусто — это не чистое одобрение).
const ST_OK_WORDS = ['ок', 'окей', 'ok', 'okay', 'oк', 'согласна', 'согласен', 'согласовано', 'согласован', 'согласованы',
  'согласовала', 'согласовал', 'согласовали', 'одобряю', 'одобрено', 'одобрила', 'принимаю', 'утверждено', 'утвердила',
  'утверждаю', 'принято', 'отлично', 'супер', 'хорошо', 'годится', 'подходит'];
const ST_FILL_WORDS = ['всё', 'все', 'пункт', 'пункты', 'пункта', 'и', 'тоже', 'так', 'я', 'это', 'вот', 'уже', 'тогда', 'ну'];
function stApproval(text, scopeItems, state) {
  // «согласованно» (две «н») — частая опечатка: двойные «н» сливаем, слова-согласия сравниваем без них
  const t = String(text || '').toLowerCase().replace(/ё/g, 'е').replace(/нн/g, 'н');
  if (!t.trim() || t.length > 60) return [];
  const nums = (t.match(/\d+/g) || []).map(Number);
  const hasEmoji = /[👍✅👌]/u.test(t);
  const words = t.replace(/[👍✅👌]/gu, ' ').replace(/\d+/g, ' ').split(/[^a-zа-я]+/i).filter(Boolean);
  const okWords = ST_OK_WORDS.map(w => w.replace(/ё/g, 'е').replace(/нн/g, 'н'));
  const fill = ST_FILL_WORDS.map(w => w.replace(/ё/g, 'е'));
  if (!words.every(w => okWords.includes(w) || fill.includes(w))) return [];
  if (!hasEmoji && !words.some(w => okWords.includes(w))) return [];
  const pending = scopeItems.filter(n => n in state.items && !state.agreed[n]);
  return nums.length ? pending.filter(n => nums.includes(n)) : pending;
}
function stApplyApproval(state, nums) {
  for (const n of nums || []) if (n in state.items) state.agreed[n] = true;
}

// Обращение по значку («✍️ …») или по имени («Писателю: …»).
// Сообщение начинается с номера пункта («9 предложи заново», «пункт 9: …») — отвечает этап, чей это
// пункт (по листам «Этапы»/«Пункты»), даже если сейчас работает другой. Все номера — одного этапа.
function stByItem(stages, text) {
  const m = String(text || '').match(/^\s*(?:пункт[а-яё]*\s*)?((?:\d+\s*(?:[,и]\s*)?)+)(?![\d.,]\d)/iu);
  if (!m) return null;
  const nums = (m[1].match(/\d+/g) || []).map(Number);
  const owners = [...new Set(nums.map(n => {
    const s = stages.find(s_ => s_.items.includes(n));
    if (!s) return null;
    return s.talks === 'boss' ? (stages.find(b => bareIcon(b.icon) === bareIcon(s.boss)) || s) : s;   // за подчинённого отвечает его начальник
  }))];
  return owners.length === 1 && owners[0] ? owners[0] : null;
}

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

// Ответ (reply) на сообщение этапа — это адрес: каждое сообщение этапа начинается со значка и имени
// («✍️ Писатель: …»); картинка этапа-художника подписана «Вариант N».
function stByReply(stages, replyText, replyVariant) {
  const t = bareIcon(String(replyText || '').trim());
  if (t) {
    const sorted = [...stages].sort((a, b) => bareIcon(b.icon).length - bareIcon(a.icon).length);
    for (const s of sorted) { const ic = bareIcon(s.icon); if (ic && t.startsWith(ic)) return s; }
  }
  if (replyVariant) return stages.find(s => s.picture) || null;
  return null;
}

// «заново» / «сначала» / «с нуля» — начать этап сначала (после обращения «✍️ …» или как reply на сообщение этапа).
function stIsReset(text) {
  return /^\s*(?:(?:давай|начни|начинай|начнём|начнем)\s+)?(?:заново|сначала|с\s+нуля|с\s+начала)\s*[.!]?\s*$/iu.test(String(text || ''));
}
// Сброс этапа: его разговор и черновики/согласование его пунктов — и всех следующих этапов (они строятся на нём).
// Варианты картинок не трогаем; у этапа-художника сбрасывается только согласование картинки.
function stResetState(stages, items, state, stage) {
  const idx = stages.findIndex(s => bareIcon(s.icon) === bareIcon(stage.icon));
  const later = stages.slice(idx < 0 ? 0 : idx);
  const names = [];
  let picture = false;
  for (const s of later) {
    delete state.stages[bareIcon(s.icon)];
    for (const n of s.items) { delete state.items[n]; delete state.agreed[n]; }
    if (s.picture) picture = true;
    if (s.talks !== 'boss') names.push(`${s.icon} ${s.name}`);
  }
  return { state, names, picture };
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
function itValue(state, n) { const v = state.items[n]; return v && typeof v === 'object' ? v : { text: '', ru: '', ruOf: '' }; }
// (11.10) Перевод для автора делает отдельный переводчик по готовому тексту пункта (узел «Перевод для
// автора»), а не сам этап: этап «переводил» свои намерения и пометки автора, а в таблицу шёл другой текст.
// Перевод действителен, только пока текст тот же, с которого он сделан (ruOf).
function itNeedsRu(text) {
  const t = String(text || '');
  return (t.match(/[a-zA-Z]/g) || []).length > (t.match(/[а-яёА-ЯЁ]/g) || []).length;
}
function itShow(state, item, forModel) {
  const v = itValue(state, item.n);
  if (!(item.n in state.items)) return '';
  if (!v.text) return '— пусто';
  if (forModel || !itNeedsRu(v.text)) return v.text;
  const long = v.text.includes('\n') || v.text.length > 200;
  if (!v.ru || v.ruOf !== v.text) return long ? `${v.text}\n\n— Перевод для автора не получен —` : `${v.text} (перевод не получен)`;
  return long ? `${v.text}\n\n— Перевод для автора —\n${v.ru}` : `${v.text} (${v.ru})`;
}
// Пункты, которым нужен свежий перевод: текст не по-русски, а перевода с этого текста ещё нет.
function itRuTodo(state) {
  return Object.keys(state.items || {}).map(n => ({ n: Number(n), v: itValue(state, n) }))
    .filter(x => x.v.text && itNeedsRu(x.v.text) && !(x.v.ru && x.v.ruOf === x.v.text))
    .map(x => ({ n: x.n, text: x.v.text }));
}
// Кладём в состояние ответ переводчика — только тем пунктам, чей текст не изменился с тех пор.
function itApplyRu(state) {
  let todo = [], resp = null;
  try { todo = $('Перевод для автора: что').first().json.todo || []; } catch (e) { return; }
  try { resp = $('OpenAI: перевод для автора').first().json || null; } catch (e) { return; }
  if (!todo.length) return;
  if (!resp || resp.error) {
    const er = resp && resp.error;
    return 'переводчик не ответил' + (er ? ': ' + String(er.message || (typeof er === 'string' ? er : JSON.stringify(er))).slice(0, 200) : '');
  }
  const out = (resp.output || []).filter(i => i.type === 'message')
    .flatMap(i => (i.content || []).filter(c => c.type === 'output_text').map(c => c.text)).join('').trim();
  let map = {};
  try { map = JSON.parse(out.replace(/^```(?:json)?\s*|\s*```$/g, '')); } catch (e) { return 'переводчик ответил не JSON'; }
  for (const t of todo) {
    const v = state.items[t.n];
    const ru = String(map[String(t.n)] == null ? '' : map[String(t.n)]).trim();
    if (v && typeof v === 'object' && v.text === t.text && ru) { v.ru = ru; v.ruOf = t.text; }
  }
}

// (20.10) Английский перевод задания художнику (второй проход «Итог хода»); пусто — рисуем по исходному.
function artEnBrief() {
  let pv = null, resp = null;
  try { pv = $('Перевод для автора: что').first().json; } catch (e) { return ''; }
  if (!pv || !pv.art) return '';
  try { resp = $('OpenAI: перевод для автора').first().json || null; } catch (e) { return ''; }
  if (!resp || resp.error) return '';
  const out = (resp.output || []).filter(i => i.type === 'message')
    .flatMap(i => (i.content || []).filter(c => c.type === 'output_text').map(c => c.text)).join('').trim();
  try { return String(JSON.parse(out.replace(/^```(?:json)?\s*|\s*```$/g, '')).brief || '').trim(); } catch (e) { return ''; }
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
  // (20.10) пересборка вышедшего выпуска: «Опубликовано» тоже годится — статус вернётся в «Утверждено» сразу после стены
  const okStatus = o.allowPublished ? ['Утверждено', 'Опубликовано'] : ['Утверждено'];
  if (o.needApproved && !okStatus.includes(val('sys_Status'))) problems.push(`статус «${val('sys_Status') || 'пусто'}», а не «Утверждено»`);
  if (o.needTracks && !val('sys_AudioZipUrl')) problems.push('sys_AudioZipUrl пустая (нет ссылки на треки)');
  return problems;
}

// Референсы художнику: картинки из колонок 🎨 — до 8 (в правке 7 + сама правляемая картинка = 8).
// Число связано с MAX_IMAGES в gen12.py: на каждое количество картинок свой узел запроса.
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
  const draw = fit(8);
  const edit = fit(7);
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
    const old = state.items[n];
    // перевод этапа не берём: перевод для автора делает отдельный переводчик по готовому тексту (itApplyRu)
    if (!old || old.text !== text) {
      state.agreed[n] = false; changed.push(n);
      state.items[n] = { text, ru: '', ruOf: '' };
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
    if (!(n in state.items) && it.canEmpty) state.items[n] = { text: '', ru: '', ruOf: '' };
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
