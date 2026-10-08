// Лупа: этап только что предложил пункт с превью «оживление» — его точки уточним по увеличенным кусочкам.
const ctx = $('Контекст проекта').first().json;
const r = $('Разбираем ответ этапа').first().json;
const items = ctx.items || [];
const state = stParseState(r.editorState);
const imageUrl = String((ctx.row || {}).ai_ApprovedImageUrl || '').trim();
// Служебный выключатель канала (Templates, колонка без значка): tmpl_Lupa = нет — лупа не нужна, точки автора верные
// (автор размечает сама на страничке, лупа сдвигала их). Пусто или «да» — как раньше.
const lupaSwitch = String(findByLabel(ctx.tmpl || {}, 'tmpl_Lupa') || '').trim().toLowerCase();
const lupaOff = ['нет', 'выкл', 'off', 'no', '0'].includes(lupaSwitch);
const it = items.find(i => /оживл/.test(i.preview || '') && (r.changed || []).includes(i.n) && ((state.items[i.n] || {}).text || '').trim());
return [{ json: { need: !!(it && imageUrl) && !lupaOff, n: it ? it.n : null, fx: it ? state.items[it.n].text : '', imageUrl } }];
