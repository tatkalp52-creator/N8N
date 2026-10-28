// (29.10) Приложение открыто кнопкой меню бота — выпуска ещё не знает: список выпусков, которые можно оживить
// (картинка согласована, ещё не опубликован), по всем каналам листа Catalog.
const rows = $input.all().map(i => i.json || {});
const t = v => String(v == null ? '' : v).trim();
const list = rows.filter(r => t(r.sys_ProjectID) && t(r.ai_ApprovedImageUrl) && t(r.sys_Status) !== 'Опубликовано')
  .map(r => {
    const id = t(r.sys_ProjectID), m = id.match(/^\d{8}_\d{6}_([A-Za-z0-9]+)$/);
    return { p: id, ch: m ? m[1] : '', img: toDirectImageUrl(t(r.ai_ApprovedImageUrl)),
      title: t(r.ai_Title) || t(r.ai_UserBrief).slice(0, 80) || id, status: t(r.sys_Status) };
  })
  .sort((a, b) => (a.p < b.p ? 1 : -1));
return [{ json: { episodes: list } }];
