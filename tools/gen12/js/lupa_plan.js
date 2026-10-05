// Лупа: этап только что предложил пункт с превью «оживление» — его точки уточним по увеличенным кусочкам.
const ctx = $('Контекст проекта').first().json;
const r = $('Разбираем ответ этапа').first().json;
const items = ctx.items || [];
const state = stParseState(r.editorState);
const imageUrl = String((ctx.row || {}).ai_ApprovedImageUrl || '').trim();
const it = items.find(i => /оживл/.test(i.preview || '') && (r.changed || []).includes(i.n) && ((state.items[i.n] || {}).text || '').trim());
return [{ json: { need: !!(it && imageUrl), n: it ? it.n : null, fx: it ? state.items[it.n].text : '', imageUrl } }];
