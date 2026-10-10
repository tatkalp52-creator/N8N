// Ссылка на треки сохранена. Нужна ли чистка в Kaggle? Да — если в таблице
// задан способ (🎬tmpl_CleanMode) и это не уже готовый результат Kaggle.
const ctx = $('Контекст проекта').first().json;
const tmpl = ctx.tmpl || {};
const val = l => String(findByLabel(tmpl, l) || '').trim();
const mode = val('tmpl_CleanMode');
const url = String(ctx.tracksUrl || '').trim();
const need = !!mode && !!url && !url.includes('kaggle.com/code/');
// адрес, по которому блокнот в конце «постучится» в ЭТО ожидание (у каждого запуска свой)
const callbackUrl = typeof $execution !== 'undefined' && $execution ? ($execution.resumeUrl || '') : '';
return [{
  json: {
    need,
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
