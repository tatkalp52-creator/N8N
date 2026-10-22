// Строка на ролик → лист «Разбор: ролики».
const prev = $('Ролики: запрос данных').all();
const out = [];
$input.all().forEach((it, i) => {
  const src = prev[i].json, ch = src.channel || {};
  for (const v of ((it.json || {}).items || [])) {
    const sn = v.snippet || {}, st = v.statistics || {}, cd = v.contentDetails || {};
    const desc = String(sn.description || '');
    const tags = sn.tags || [];
    const th = sn.thumbnails || {};
    out.push({ json: {
      'Группа': src.group, 'Канал': (ch.snippet || {}).title || '', 'Ссылка на канал': chLink(ch),
      'Ролик': 'https://www.youtube.com/watch?v=' + v.id, 'Название': sn.title || '', 'Длина названия': String(sn.title || '').length,
      'Дата': String(sn.publishedAt || '').slice(0, 10), 'Минут': isoMin(cd.duration),
      'Просмотры': +st.viewCount || 0, 'Лайки': +st.likeCount || 0, 'Комментарии': +st.commentCount || 0,
      'Тегов': tags.length, 'Теги': tags.join(', '), 'Хэштеги': hashtags(desc).join(' '),
      'Начало описания': desc.split('\n').filter(l => l.trim()).slice(0, 2).join(' / ').slice(0, 300),
      'Длина описания': desc.length, 'Описание': desc.slice(0, 5000),
      'Язык': sn.defaultAudioLanguage || sn.defaultLanguage || '', 'Категория': sn.categoryId || '',
      'Обложка': (th.maxres || th.high || th.medium || th.default || {}).url || '', 'Разобрано': today(),
    } });
  }
});
return out;
