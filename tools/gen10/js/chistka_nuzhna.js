// Ссылка на треки сохранена. Нужна ли чистка в Kaggle? Да — если в таблице
// задан способ (🎬tmpl_CleanMode) и это не уже готовый результат Kaggle.
const ctx = $('Контекст проекта').first().json;
const tmpl = ctx.tmpl || {};
const val = l => String(findByLabel(tmpl, l) || '').trim();
const mode = val('tmpl_CleanMode');
const url = String(ctx.tracksUrl || '').trim();
// уже очищенный архив (та же ссылка, что лежит в строке после готовой чистки) — второй раз не чистим (13.10)
const row = ctx.row || {};
const fileId = u => { const s = String(u || '').trim(); const m = s.match(/(?:\/d\/|[?&]id=)([a-zA-Z0-9_-]{20,})/); return m ? m[1] : s; };
const alreadyClean = String(row.sys_CleanState || '').trim() === 'готово' && !!url && fileId(url) === fileId(row.sys_AudioZipUrl);
const need = !!mode && !!url && !url.includes('kaggle.com/code/') && !alreadyClean;
// адрес, по которому блокнот в конце «постучится» в ЭТО ожидание (у каждого запуска свой)
const callbackUrl = typeof $execution !== 'undefined' && $execution ? ($execution.resumeUrl || '') : '';
return [{
  json: {
    need,
    alreadyClean,
    projectId: ctx.projectId,
    body: {
      projectId: ctx.projectId, tracksUrl: url, cleanMode: mode,
      cleanNotebook: val('tmpl_CleanNotebook'),
      cleanBlend: val('tmpl_CleanBlend'), cleanBlendStems: val('tmpl_CleanBlendStems'),
      // все ручки чистки из таблицы: 🎬tmpl_CleanXxx → { Xxx: значение }
      cleanSettings: Object.fromEntries(Object.keys(tmpl)
        .map(k => [k, (String(k).match(/tmpl_Clean(\w+)$/) || [])[1]])
        .filter(([k, name]) => name && String(tmpl[k] ?? '').trim() !== '')
        .map(([k, name]) => [name, String(tmpl[k]).trim()])),
      callbackUrl,
    },
    mode,
    alarmHours: parseFloat(val('tmpl_CleanAlarmHours')) || 4,
  }
}];
