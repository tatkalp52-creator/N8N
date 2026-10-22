// Строка на канал → лист «Разбор: каналы» (средние по разобранным роликам).
const prev = $('Ролики: запрос данных').all();
return $input.all().map((it, i) => {
  const src = prev[i].json, ch = src.channel || {}, sn = ch.snippet || {}, st = ch.statistics || {};
  const vids = (it.json || {}).items || [];
  const views = vids.map(v => +((v.statistics || {}).viewCount) || 0);
  const mins = vids.map(v => isoMin((v.contentDetails || {}).duration));
  const dates = vids.map(v => Date.parse((v.snippet || {}).publishedAt)).filter(Boolean).sort((a, b) => a - b);
  const gaps = dates.slice(1).map((d, k) => Math.round((d - dates[k]) / 86400000 * 10) / 10);
  const tagsN = vids.map(v => ((v.snippet || {}).tags || []).length);
  const withHash = vids.filter(v => hashtags((v.snippet || {}).description).length).length;
  const avg = a => a.length ? Math.round(a.reduce((x, y) => x + y, 0) / a.length * 10) / 10 : '';
  return { json: {
    'Группа': src.group, 'Канал': sn.title || '', 'Ссылка на канал': chLink(ch),
    'Подписчики': st.hiddenSubscriberCount ? 'скрыто' : (+st.subscriberCount || 0), 'Роликов всего': +st.videoCount || 0,
    'Просмотров всего': +st.viewCount || 0, 'Создан': String(sn.publishedAt || '').slice(0, 10), 'Страна': sn.country || '',
    'Описание канала': String(sn.description || '').slice(0, 3000),
    'Ключевые слова канала': String(((ch.brandingSettings || {}).channel || {}).keywords || '').slice(0, 1000),
    'Разобрано роликов': vids.length, 'Просмотры: медиана': median(views), 'Просмотры: среднее': avg(views),
    'Дней между роликами (медиана)': median(gaps) === '' ? '' : median(gaps), 'Минут: среднее': avg(mins),
    'Тегов: среднее': avg(tagsN), 'Роликов с хэштегами': vids.length ? Math.round(withHash / vids.length * 100) + '%' : '',
    'Самый ранний из разобранных': dates.length ? new Date(dates[0]).toISOString().slice(0, 10) : '', 'Разобрано': today(),
  } };
});
