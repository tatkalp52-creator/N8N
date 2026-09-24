// Вся логика календаря в одном месте. На входе — строки листа «Календарь»
// и событие (сообщение / кнопка из Телеграма или еженедельный будильник).
// На выходе один пакет: какие строки записать в таблицу (upserts) и какие
// сообщения отправить/поправить (messages). Нейросети тут нет: разбор дат,
// склейка повторов и статусы — обычный код.
const OWNER = 285577543;
const MON_GEN = ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
const MON_NOM = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];
const MON_KEYS = [['янв','jan'],['фев','feb'],['мар','mar'],['апр','apr'],['мая','май','may'],['июн','jun'],['июл','jul'],['авг','aug'],['сен','sep'],['окт','oct'],['ноя','nov'],['дек','dec']];
const STATUS = { i: 'Идея', p: 'Выбран', w: 'В работе', d: 'Вышел', s: 'Отклонён' };
const MARK = { 'Идея': '', 'Выбран': ' ⭐', 'В работе': ' 🛠', 'Вышел': ' ✓', 'Отклонён': ' ✖' };
const CH = { pengui: '🔴 Pengui', tapestry: '🟡 Гобелены' };
const COLS = ['id','year','month','day','title','channel','status','project','note','sources','createdAt','updatedAt'];

const store = $getWorkflowStaticData('global');
store.pending = store.pending || {};
const nowIso = new Date().toISOString();
for (const k of Object.keys(store.pending)) {
  if (Date.now() - (store.pending[k].t || 0) > 3 * 86400000) delete store.pending[k];
}

const esc = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const chName = c => CH[c] || ('⚪ ' + c);
const srcList = r => String(r.sources || '').split(';').map(s => s.trim()).filter(Boolean);
const newId = () => 'o' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

const rows = $('Читаем календарь').all().map(i => i.json)
  .filter(r => r && String(r.id || '').trim())
  .map(r => ({ ...r, id: String(r.id).trim(), month: Number(r.month), day: Number(r.day),
    year: r.year ? Number(r.year) : null, status: r.status || 'Идея', channel: r.channel || 'pengui' }));

const upserts = [];
const messages = [];
function toSheet(r) {
  const o = {};
  for (const c of COLS) o[c] = r[c] === null || r[c] === undefined ? '' : String(r[c]);
  return o;
}
function put(r) { r.updatedAt = nowIso; upserts.push(toSheet(r)); }

// ---------- даты ----------
const today = new Date(); today.setHours(0, 0, 0, 0);
function nextDate(r, from) {
  for (const y of [from.getFullYear(), from.getFullYear() + 1]) {
    if (r.year && r.year !== y) continue;
    const d = new Date(y, r.month - 1, r.day);
    if (d >= from) return d;
  }
  return null;
}
const short = d => d.getDate() + ' ' + MON_GEN[d.getMonth()].slice(0, 3);

// ---------- разбор списка ----------
function monthFromWord(w) { w = w.toLowerCase(); for (let i = 0; i < 12; i++) if (MON_KEYS[i].some(k => w.startsWith(k))) return i + 1; return 0; }
function parseLine(raw) {
  let line = raw.replace(/^[\s\-–—•*·>\d]*[.)]\s+/, '').replace(/^[\s\-–—•*·>]+/, '').replace(/\*\*/g, '').trim();
  if (!line) return null;
  let m, mo = 0, d = 0, y = null, matched = '';
  if ((m = line.match(/(\d{4})-(\d{1,2})-(\d{1,2})/))) { y = +m[1]; mo = +m[2]; d = +m[3]; matched = m[0]; }
  else if ((m = line.match(/(\d{1,2})(?:\s*[–-]\s*\d{1,2})?\s+([А-Яа-яЁёA-Za-z]{3,})\.?(?:\s+(\d{4}))?/)) && monthFromWord(m[2])) { d = +m[1]; mo = monthFromWord(m[2]); y = m[3] ? +m[3] : null; matched = m[0]; }
  else if ((m = line.match(/\b([A-Za-z]{3,})\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?/)) && monthFromWord(m[1])) { mo = monthFromWord(m[1]); d = +m[2]; y = m[3] ? +m[3] : null; matched = m[0]; }
  else if ((m = line.match(/\b(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?\b/))) { d = +m[1]; mo = +m[2]; y = m[3] ? (m[3].length === 2 ? 2000 + +m[3] : +m[3]) : null; matched = m[0]; }
  let title = matched ? line.replace(matched, ' ') : line;
  title = title.replace(/^[\s\-–—:|,.()]+|[\s\-–—:|,(]+$/g, '').replace(/\s{2,}/g, ' ').trim();
  const ok = mo >= 1 && mo <= 12 && d >= 1 && d <= 31;
  return { title: title || line, month: ok ? mo : 0, day: ok ? d : 0, year: y, ok, raw: line };
}
const STOP = new Set(['день','дня','всемирный','всемирного','международный','международного','национальный','day','world','international','national','the','of','and','для','рождения','birthday','born']);
function words(s) { return new Set(String(s).toLowerCase().replace(/[^a-zа-яё0-9 ]/gi, ' ').split(/\s+/).filter(w => w.length > 2 && !STOP.has(w)).map(w => w.slice(0, 6))); }
function similar(a, b) { const A = words(a), B = words(b); if (!A.size || !B.size) return a.trim().toLowerCase() === b.trim().toLowerCase(); let k = 0; for (const w of A) if (B.has(w)) k++; return k / Math.min(A.size, B.size) >= 0.5; }
function classify(p) {
  // для текущего канала: новый / уже есть (какая строка) / повтор внутри списка / нет даты
  const ch = p.channel;
  const out = { fresh: [], dup: [], bad: [] };
  const batch = [];
  for (const it of p.lines) {
    if (!it.ok) { out.bad.push(it); continue; }
    const hit = rows.find(r => r.channel === ch && r.month === it.month && r.day === it.day && similar(r.title, it.title));
    if (hit) { out.dup.push({ it, hit }); continue; }
    if (batch.some(b => b.month === it.month && b.day === it.day && similar(b.title, it.title))) continue;
    batch.push(it); out.fresh.push(it);
  }
  return out;
}
const dstr = it => it.day + ' ' + MON_GEN[it.month - 1].slice(0, 3) + (it.year ? ' ' + it.year : '');
function previewText(p) {
  const c = classify(p);
  const L = [];
  L.push(`<b>Список поводов</b>: строк ${p.lines.length}`);
  L.push(`🆕 новых: ${c.fresh.length}   🔁 уже есть: ${c.dup.length}${c.bad.length ? `   ⚠️ без даты: ${c.bad.length}` : ''}`);
  L.push(`Канал: <b>${esc(chName(p.channel))}</b>`);
  if (c.fresh.length) { L.push('', '<b>Новые</b>'); c.fresh.slice(0, 30).forEach(it => L.push(`• ${dstr(it)} — ${esc(it.title)}`)); if (c.fresh.length > 30) L.push(`…и ещё ${c.fresh.length - 30}`); }
  if (c.dup.length) { L.push('', '<b>Уже в календаре</b> (станут ×' + '2+)'); c.dup.slice(0, 15).forEach(({ it, hit }) => L.push(`• ${dstr(it)} — ${esc(hit.title)} ×${srcList(hit).length + 1}`)); if (c.dup.length > 15) L.push(`…и ещё ${c.dup.length - 15}`); }
  if (c.bad.length) { L.push('', '<b>Не поняла дату</b>'); c.bad.slice(0, 10).forEach(it => L.push(`• ${esc(it.raw.slice(0, 80))}`)); }
  L.push('', 'Выбери канал и нажми «✅ Добавить».');
  return L.join('\n').slice(0, 4000);
}
function cardText(r) {
  const d = nextDate(r, today) || new Date(r.year || today.getFullYear(), r.month - 1, r.day);
  const n = srcList(r).length;
  const L = [`<b>${short(d)}</b> · ${esc(chName(r.channel))}`, `<b>${esc(r.title)}</b>${n > 1 ? ' ×' + n : ''}`, `Статус: <b>${esc(r.status)}</b>${MARK[r.status] || ''}`];
  if (r.project) L.push(`Проект: <code>${esc(r.project)}</code>`);
  if (r.note) L.push('', `<i>${esc(String(r.note).slice(0, 1500))}</i>`);
  if (n) L.push('', `Откуда: ${esc(srcList(r).join(', '))}`);
  L.push(`<code>id:${esc(r.id)}</code>`);
  return L.join('\n');
}
function summary(from, days, title) {
  const end = new Date(from); end.setDate(end.getDate() + days);
  const list = [];
  for (const r of rows) { if (r.status === 'Отклонён') continue; const d = nextDate(r, from); if (d && d <= end) list.push([d, r]); }
  list.sort((a, b) => a[0] - b[0]);
  if (!list.length) return `${title}\n\nПоводов нет.`;
  const L = [title, ''];
  let last = '';
  for (const [d, r] of list) {
    const k = short(d);
    const n = srcList(r).length;
    L.push(`${k === last ? '       ' : '<b>' + k + '</b>'} ${r.channel === 'tapestry' ? '🟡' : r.channel === 'pengui' ? '🔴' : '⚪'} ${esc(r.title)}${n > 1 ? ' ×' + n : ''}${MARK[r.status] || ''}`);
    last = k;
  }
  return L.join('\n').slice(0, 4000);
}
const HELP = [
  '<b>Studio Calendar</b>',
  '',
  '• Вставь список поводов от любой нейросети — одна строка, один повод. Даты: «20 января», «20.01», «January 20». Я покажу, что нового, а что уже есть.',
  '• <b>ближайшие</b> — поводы на 30 дней вперёд.',
  '• <b>октябрь</b> (или любой месяц) — поводы месяца списком.',
  '• Кнопка <b>«Календарь»</b> внизу слева — красивый календарь по месяцам: там выбираешь поводы и пишешь заметки.',
  '• <b>выбранные</b> — что ты выбрала на 3 месяца вперёд.',
  '• Ответь на карточку повода любым текстом — он добавится в заметки.',
  '',
  '⭐ выбран · 🛠 в работе · ✓ вышел · ×3 — предложили три источника.',
].join('\n');

// ---------- событие ----------
let tg = null;
if ($('Telegram Trigger').isExecuted) tg = $('Telegram Trigger').first().json;

if (!tg) {
  // еженедельный будильник
  const picked = rows.filter(r => ['Выбран', 'В работе'].includes(r.status));
  let text = summary(today, 14, '<b>Поводы на две недели</b>');
  if (!picked.length) text += '\n\nВыбранных пока нет — пришли «октябрь» или нужный месяц, чтобы выбрать.';
  messages.push({ type: 'send', chatId: OWNER, text });
} else if (tg.callback_query) {
  const cb = tg.callback_query;
  const chatId = cb.message.chat.id, messageId = cb.message.message_id, queryId = cb.id;
  const parts = String(cb.data || '').split('|');
  if (parts[0] === 'imp') {
    const p = store.pending[parts[1]];
    if (!p) {
      messages.push({ type: 'edit', chatId, messageId, text: 'Этот список уже обработан или устарел. Пришли его ещё раз.' });
      messages.push({ type: 'answer', queryId, text: 'Список устарел' });
    } else if (parts[2] === 'ch') {
      p.channel = parts[3];
      messages.push({ type: 'editImport', chatId, messageId, importId: parts[1], text: previewText(p) });
      messages.push({ type: 'answer', queryId, text: 'Канал: ' + chName(p.channel) });
    } else if (parts[2] === 'src') {
      p.source = parts[3];
      messages.push({ type: 'editImport', chatId, messageId, importId: parts[1], text: previewText(p) });
      messages.push({ type: 'answer', queryId, text: 'Источник: ' + p.source });
    } else if (parts[2] === 'no') {
      delete store.pending[parts[1]];
      messages.push({ type: 'edit', chatId, messageId, text: 'Отменила, ничего не добавлено.' });
      messages.push({ type: 'answer', queryId, text: 'Отменено' });
    } else if (parts[2] === 'go') {
      const c = classify(p);
      const d0 = new Date(p.t); const src = 'список ' + String(d0.getDate()).padStart(2, '0') + '.' + String(d0.getMonth() + 1).padStart(2, '0') + ' ' + parts[1].slice(-4);
      for (const it of c.fresh) {
        const r = { id: newId(), year: it.year || '', month: it.month, day: it.day, title: it.title, channel: p.channel, status: 'Идея', project: '', note: '', sources: src, createdAt: nowIso };
        put(r);
      }
      let merged = 0;
      const touched = new Set();
      for (const { hit } of c.dup) {
        if (touched.has(hit.id)) continue;
        touched.add(hit.id);
        const s = srcList(hit);
        if (!s.includes(src)) { s.push(src); hit.sources = s.join('; '); put(hit); merged++; }
      }
      delete store.pending[parts[1]];
      messages.push({ type: 'edit', chatId, messageId, text: `✅ Готово · ${chName(p.channel)}\nНовых поводов: ${c.fresh.length}\nСовпадений (стали ×N+1): ${merged}${c.bad.length ? `\nБез даты, пропущено: ${c.bad.length}` : ''}\n\nКалендарь — кнопка «Календарь» внизу слева.` });
      messages.push({ type: 'answer', queryId, text: 'Добавлено' });
    }
  } else if (parts[0] === 'st') {
    const r = rows.find(x => x.id === parts[1]);
    const st = STATUS[parts[2]];
    if (!r || !st) {
      messages.push({ type: 'answer', queryId, text: 'Не нашла этот повод в таблице' });
    } else {
      r.status = st; put(r);
      messages.push({ type: 'editCard', chatId, messageId, rowId: r.id, text: cardText(r) });
      messages.push({ type: 'answer', queryId, text: 'Статус: ' + st });
    }
  } else {
    messages.push({ type: 'answer', queryId, text: '' });
  }
} else if (tg.message) {
  const msg = tg.message;
  const chatId = msg.chat.id;
  const text = String(msg.text || msg.caption || '').trim();
  const low = text.toLowerCase().replace(/^\//, '');
  const replyTo = msg.reply_to_message ? String(msg.reply_to_message.text || '') : '';
  const idInReply = replyTo.match(/id:([A-Za-z0-9_-]+)/);
  const monM = low.match(/^(январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|октябр|ноябр|декабр)[а-я]*\s*(\d{4})?$/);

  if (idInReply && text) {
    const r = rows.find(x => x.id === idInReply[1]);
    if (!r) messages.push({ type: 'send', chatId, text: 'Не нашла этот повод в таблице.' });
    else {
      r.note = (r.note ? String(r.note) + '\n\n' : '') + text;
      put(r);
      messages.push({ type: 'send', chatId, text: `📝 Добавила в заметки: <b>${esc(r.title)}</b>` });
    }
  } else if (!text || ['start', 'help', 'помощь', 'меню'].includes(low)) {
    messages.push({ type: 'send', chatId, text: HELP });
  } else if (['ближайшие', 'soon', 'скоро'].includes(low)) {
    messages.push({ type: 'send', chatId, text: summary(today, 30, '<b>Ближайшие 30 дней</b>') });
  } else if (['выбранные', 'план'].includes(low)) {
    const end = new Date(today); end.setDate(end.getDate() + 92);
    const list = rows.filter(r => ['Выбран', 'В работе'].includes(r.status)).map(r => [nextDate(r, today), r]).filter(([d]) => d && d <= end).sort((a, b) => a[0] - b[0]);
    messages.push({ type: 'send', chatId, text: list.length ? '<b>Выбранные на 3 месяца</b>\n\n' + list.map(([d, r]) => `<b>${short(d)}</b> ${r.channel === 'tapestry' ? '🟡' : '🔴'} ${esc(r.title)}${MARK[r.status]}`).join('\n') : 'Выбранных поводов на 3 месяца пока нет.' });
  } else if (monM) {
    const mi = MON_KEYS.findIndex(k => k.some(x => monM[1].startsWith(x.slice(0, 3)))) ;
    const mIdx = mi >= 0 ? mi : 0;
    let y = monM[2] ? +monM[2] : today.getFullYear();
    if (!monM[2] && mIdx < today.getMonth()) y++;
    const from = new Date(y, mIdx, 1);
    const days = new Date(y, mIdx + 1, 0).getDate() - 1;
    messages.push({ type: 'send', chatId, text: summary(from, days, `<b>${MON_NOM[mIdx]} ${y}</b>`) + '\n\n⭐ выбран · 🛠 в работе · ✓ вышел. Выбирать — в «Календаре» (кнопка внизу слева).' });
  } else {
    const lines = text.split(/\n+/).map(parseLine).filter(Boolean);
    if (!lines.some(l => l.ok)) {
      messages.push({ type: 'send', chatId, text: 'Не нашла в сообщении ни одной даты.\n\n' + HELP });
    } else {
      const importId = Date.now().toString(36).slice(-6) + Math.random().toString(36).slice(2, 4);
      store.pending[importId] = { t: Date.now(), channel: 'pengui', source: '', lines };
      messages.push({ type: 'sendImport', chatId, importId, text: previewText(store.pending[importId]) });
    }
  }
}

return [{ json: { upserts, messages } }];
