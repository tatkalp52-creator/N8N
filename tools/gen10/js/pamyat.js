// Карточка утверждённого выпуска → файл для векторной памяти канала.
// По ней Редактор потом сам находит прошлые истории (file_search).
const ctx = $('Контекст проекта').first().json;
const f = $('Собираем пакет для таблицы').first().json.fields || {};
const row = ctx.row || {};
const vsId = String(findByLabel(ctx.tmpl || {}, 'tmpl_ChannelVectorStoreId') || '').trim();
const m = String(ctx.projectId).match(/^(\d{4})(\d{2})(\d{2})/);
const date = m ? `${m[3]}.${m[2]}.${m[1]}` : '';
const theme = (String(f.ai_Description || '').split('\n').find(l => l.trim().startsWith('♪')) || '').trim();
const text = [
  `ВЫПУСК КАНАЛА «${ctx.sheetName}» · ${date} · ID ${ctx.projectId}`,
  `Название: ${f.ai_Title || ''}`,
  `Оверлей: ${f.ai_OverlayText || ''}`,
  theme ? `Музыкальная тема: ${theme}` : '',
  row.ai_UserBrief ? `Замысел автора: ${row.ai_UserBrief}` : '',
  '',
  'История (как её согласовала автор):',
  f.ai_DescriptionDraft || '',
  '',
  'Названия треков: ' + String(f.ai_TimecodeNames || '').split('\n').filter(Boolean).join(' · '),
].filter(x => x !== null).join('\n');
return [{
  json: { vsId, hasMemory: !!vsId },
  binary: { data: { data: Buffer.from(text, 'utf8').toString('base64'), mimeType: 'text/plain', fileName: `episode_${ctx.projectId}.txt` } },
}];
