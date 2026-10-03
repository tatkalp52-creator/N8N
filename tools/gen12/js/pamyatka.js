// Памятка этапа — колонка Templates с его значком и 📝 (имя колонки берётся из таблицы).
const r = $('Итог хода').first().json;
return [{ json: { tmpl_Channel: r.channelKey, [r.note.key]: r.note.text } }];
