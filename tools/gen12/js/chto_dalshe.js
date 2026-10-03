// Что делать после хода — ровно одно действие (сколько бы кусков сообщения ни ушло).
const r = $('Итог хода').first().json;
let next = 'none';
if (r.action === 'ready_to_draw') next = 'draw';
else if (r.action === 'revise_point') next = 'edit';
else if (r.transition && r.transition !== 'none') next = r.transition;
return [{ json: { next } }];
