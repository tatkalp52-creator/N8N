// (29.10) Какой файл приложения отдать (страница или картинка-образец листа). Только файлы из /pages сборщика.
const q = ($input.first().json || {}).query || {};
const f = String(q.f || 'ozhivlenie.html');
if (!/^[a-z0-9_]+(\/[a-z0-9_]+)*\.(html|png|jpg|js|css)$/i.test(f)) throw new Error('нет такого файла: ' + f.slice(0, 80));
return [{ json: { f } }];
