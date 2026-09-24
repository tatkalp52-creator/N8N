// строка, которую прислала страница: берём только известные колонки
const COLS = ['id','year','month','day','title','channel','status','project','note','sources','createdAt','updatedAt'];
const STATUSES = ['Идея','Выбран','В работе','Вышел','Отклонён'];
const r = ($('Сохранение со страницы').first().json.body || {}).row || {};
const id = String(r.id || '').trim();
if (!/^[A-Za-z0-9_-]{2,40}$/.test(id)) throw new Error('bad id');
const m = Number(r.month), d = Number(r.day);
if (!(m >= 1 && m <= 12 && d >= 1 && d <= 31)) throw new Error('bad date');
const now = new Date().toISOString();
const out = {};
for (const c of COLS) out[c] = r[c] === null || r[c] === undefined ? '' : String(r[c]).slice(0, 20000);
out.id = id; out.month = String(m); out.day = String(d);
if (!STATUSES.includes(out.status)) out.status = 'Идея';
out.channel = (out.channel || 'pengui').toLowerCase();
out.updatedAt = now;
if (!out.createdAt) out.createdAt = now;
return [{ json: out }];
