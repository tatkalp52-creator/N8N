// (29.10) Каталог для приложения «Оживление»: эффекты листа «Эффекты» (раздел, механика, строка, как размечать,
// ручки, статус, значения канала) и словарик «Слово» → «Значит». Всё содержание — из таблицы.
const ch = String((($('Оживление: вход').first().json || {}).query || {}).ch || '').trim();
const rows = $input.all().map(i => i.json || {});
const t = v => String(v == null ? '' : v).trim();
const effects = rows.filter(r => t(r['Механика'])).map(r => ({
  section: t(r['Раздел']), name: t(r['Эффект']), mech: t(r['Механика']), template: t(r['Строка для сборщика']),
  marks: t(r['Как размечать']), knobs: t(r['Ручки']), status: t(r['Статус']), value: ch ? t(r[ch]) : '' }));
const words = rows.map(r => ({ word: t(r['Слово']), means: t(r['Значит']) })).filter(w => w.word && w.means);
return [{ json: { effects, words } }];
