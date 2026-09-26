// Проверяем то, что РЕАЛЬНО оказалось в таблице после записи (строку только
// что перечитали), а не то, что собирались записать.
const ctx = $('Контекст проекта').first().json;
const fresh = $input.first().json || {};
const problems = validateForAssembler(fresh, ctx.tmpl || {}, {});
return [{
  json: {
    ok: problems.length === 0,
    problems,
    problemsText: 'Записала пакет, но в таблице не хватает:\n• ' + problems.join('\n• ') + '\n\nСтатус «Утверждено» НЕ поставлен.' + `\n\nID: ${ctx.projectId}`,
    hasTracks: !!String(fresh.sys_AudioZipUrl || '').trim(),
  }
}];
