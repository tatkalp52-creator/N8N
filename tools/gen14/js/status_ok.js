// Отметка в «Каналы для разбора»: готово.
const prev = $('Ролики: запрос данных').all();
return $input.all().map((it, i) => {
  const src = prev[i].json, n = ((it.json || {}).items || []).length;
  return { json: { 'Ссылка': src.link, 'Статус': n ? `готово ${today()}: ${n} роликов` : 'роликов не нашлось' } };
});
