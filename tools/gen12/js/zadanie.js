// Задание «Работе»: тот же канвас, вызванный сам собой, получает только это (см. «Разбираем входящее»).
const j = $('В работу').first().json;
return [{ json: { work: { source: j.source, body: j.body, key: j.key } } }];
