// Проверяем то, что РЕАЛЬНО оказалось в таблице после записи (строку только что перечитали).
const ctx = $('Контекст проекта').first().json;
const fresh = $input.first().json || {};
const problems = validateRow(fresh, ctx.items || [], {});
return [{ json: {
  ok: problems.length === 0,
  problems,
  problemsText: 'Записала пакет, но в таблице не хватает:\n• ' + problems.join('\n• ') + '\n\nСтатус «Утверждено» НЕ поставлен.' + `\n\nID: ${ctx.projectId}`,
  hasTracks: !!String(fresh.sys_AudioZipUrl || '').trim(),
} }];
