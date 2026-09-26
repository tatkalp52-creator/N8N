// Прошлые главы: 5 последних утверждённых выпусков этого канала (кроме
// текущего) — чтобы Редактор тянул сквозные нити и держал голос канала.
const ctx = $('Контекст проекта').first().json;
const rows = $('Читаем прошлые выпуски').all().map(i => i.json || {});
const done = rows.filter(r => {
  const id = String(r.sys_ProjectID || '').trim();
  const st = String(r.sys_Status || '').trim();
  return id && id !== ctx.projectId && (st === 'Утверждено' || st === 'Опубликовано') && String(r.ai_DescriptionDraft || r.ai_Description || '').trim();
});
done.sort((a, b) => String(b.sys_ProjectID).localeCompare(String(a.sys_ProjectID)));
const cut = (s, n) => { s = String(s || '').replace(/\s+/g, ' ').trim(); return s.length > n ? s.slice(0, n) + '…' : s; };
const dateOf = id => { const m = String(id).match(/^(\d{4})(\d{2})(\d{2})/); return m ? `${m[3]}.${m[2]}.${m[1]}` : ''; };
const text = done.slice(0, 5).map(r =>
  `— ${dateOf(r.sys_ProjectID)} · ${cut(r.ai_Title, 120)}\n${cut(r.ai_DescriptionDraft || r.ai_Description, 700)}`
).join('\n\n');
return [{ json: { text, count: Math.min(done.length, 5) } }];
