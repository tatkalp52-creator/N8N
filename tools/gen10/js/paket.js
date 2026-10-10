// Финальная кнопка: собираем из согласованного текстового блока значения
// колонок, которые читает сборщик видео (04_Video). Статус здесь ещё НЕ ставим.
const ctx = $('Контекст проекта').first().json;
const row = ctx.row || {};
const state = tbParseState(row.sys_EditorState);
const it = state.items;
const problems = [];

const notAgreed = TB_ITEMS.filter(x => !state.agreed[x.n]);
if (notAgreed.length) problems.push('не согласованы пункты: ' + notAgreed.map(x => `${x.n} ${x.name}`).join(', '));
if (!state.descriptionEN || state.descriptionENFor !== it.description) {
  problems.push('английский перевод описания устарел — попросите Редактора показать сводку заново');
}
if (!String(row.ai_ApprovedImageUrl || '').trim()) problems.push('картинка не согласована');
if (!/\[?Timecodes\]?/i.test(it.footer || '')) problems.push('в подвале (5) нет метки [Timecodes]');

const fields = {
  sys_ProjectID: ctx.projectId,
  ai_OverlayText: it.overlayText || '',
  ai_OverlayPosition: it.overlayPosition || 'center',
  ai_Title: it.title || '',
  ai_DescriptionDraft: it.description || '',
  ai_DescriptionEN: state.descriptionEN || '',
  ai_Description: (state.descriptionEN || '') + '\n\n' + (it.footer || ''),
  ai_Hashtags: it.hashtags || '',
  ai_Tags: it.tags || '',
  ai_PinnedComment: it.pinnedComment || '',
  // Согласованные названия тайм-кодов — по одному на строку; 04_Video берёт их по порядку.
  ai_TimecodeNames: (it.timecodes || []).join('\n'),
};

return [{
  json: {
    ok: problems.length === 0,
    problems,
    fields,
    problemsText: 'Не могу утвердить:\n• ' + problems.join('\n• ') + `\n\nID: ${ctx.projectId}`,
  }
}];
