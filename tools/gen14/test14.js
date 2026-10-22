// Тесты узлов 14: $('Узел').all() / $input.all() — массивы.
const assert = require('assert'), fs = require('fs');
const wf = JSON.parse(fs.readFileSync(__dirname + '/../../workflows/14_Разбор_каналов.json', 'utf8'));
const by = Object.fromEntries(wf.nodes.map(n => [n.name, n]));
async function run(name, nodes, input) {
  const $ = n => { if (!(n in nodes)) throw new Error('unexecuted ' + n); const a = nodes[n].map(j => ({ json: j })); return { all: () => a, first: () => a[0] }; };
  const inp = (input || []).map(j => ({ json: j }));
  const f = new Function('$', '$input', `return (async () => {\n${by[name].parameters.jsCode}\n})();`);
  return (await f($, { all: () => inp, first: () => inp[0] })).map(o => o.json);
}
(async () => {
  const rows = [
    { 'Ссылка': 'https://www.youtube.com/@BaroqueRoom/videos', 'Группа': 'классика', 'Сколько роликов': '' },
    { 'Ссылка': 'https://youtu.be/dQw4w9WgXcQ', 'Группа': '"классика"' },
    { 'Ссылка': 'https://www.youtube.com/channel/UCabcdefghijklmnopqrstuv', 'Группа': 'джаз', 'Сколько роликов': '10' },
    { 'Ссылка': 'https://www.youtube.com/c/LofiGirl', 'Группа': 'лофи' },
    { 'Ссылка': 'чепуха ссылка', 'Группа': 'x' },
    { 'Ссылка': 'https://www.youtube.com/@done', 'Статус': 'готово 22.10.2026: 50 роликов' },
  ];
  const p = await run('Что разбираем', {}, rows);
  assert.equal(p.length, 5, 'с готовым статусом — не трогаем');
  assert.deepEqual(p.map(x => x.kind), ['handle', 'video', 'id', 'custom', 'bad']);
  assert.ok(p[0].step1Url.includes('forHandle=%40BaroqueRoom')); assert.equal(p[0].limit, 50); assert.equal(p[2].limit, 10);
  const r1 = [{ items: [{ id: 'UC1' }] }, { items: [{ snippet: { channelId: 'UC2' } }] }, { items: [{ id: 'UCabcdefghijklmnopqrstuv' }] }, { items: [{ snippet: { channelId: 'UC4' } }] }, { error: { message: 'Bad Request' } }];
  const k = await run('Канал найден?', { 'Что разбираем': p }, r1);
  assert.deepEqual(k.map(x => x.channelId), ['UC1', 'UC2', 'UCabcdefghijklmnopqrstuv', 'UC4', '']);
  assert.equal(k[4].error, 'не понимаю ссылку');
  const ok = k.slice(0, 1);
  const ch = { id: 'UC1', snippet: { title: 'Baroque Room', customUrl: '@baroqueroom', publishedAt: '2018-01-02T00:00:00Z', description: 'Baroque music', country: 'DE' },
    statistics: { subscriberCount: '950', videoCount: '40', viewCount: '120000' }, contentDetails: { relatedPlaylists: { uploads: 'UU1' } }, brandingSettings: { channel: { keywords: 'baroque bach' } } };
  const s = await run('Ролики: запрос списка', { 'Есть канал?': ok }, [{ items: [ch] }]);
  assert.ok(s[0].plUrl.includes('playlistId=UU1') && s[0].plUrl.includes('maxResults=50'));
  const d = await run('Ролики: запрос данных', { 'Ролики: запрос списка': s }, [{ items: [{ contentDetails: { videoId: 'v1' } }, { contentDetails: { videoId: 'v2' } }] }]);
  assert.ok(d[0].vUrl.endsWith('id=v1,v2'));
  const vids = { items: [
    { id: 'v1', snippet: { title: 'Bach · Cello Suite | Study', publishedAt: '2026-10-01T10:00:00Z', description: 'Line one\n\nLine two\n#baroque #bach #baroque', tags: ['bach', 'baroque'], thumbnails: { high: { url: 'https://i.ytimg.com/vi/v1/hq.jpg' } } }, statistics: { viewCount: '1000', likeCount: '50', commentCount: '3' }, contentDetails: { duration: 'PT1H2M30S' } },
    { id: 'v2', snippet: { title: 'Vivaldi', publishedAt: '2026-10-05T10:00:00Z', description: 'no tags' }, statistics: { viewCount: '3000' }, contentDetails: { duration: 'PT45M' } }] };
  const sr = await run('Строки роликов', { 'Ролики: запрос данных': d }, [vids]);
  assert.equal(sr.length, 2); assert.equal(sr[0]['Минут'], 62.5); assert.equal(sr[0]['Хэштеги'], '#baroque #bach');
  assert.equal(sr[0]['Начало описания'], 'Line one / Line two'); assert.equal(sr[0]['Тегов'], 2); assert.equal(sr[0]['Ссылка на канал'], 'https://www.youtube.com/@baroqueroom');
  const sk = await run('Сводка каналов', { 'Ролики: запрос данных': d }, [vids]);
  assert.equal(sk[0]['Подписчики'], 950); assert.equal(sk[0]['Просмотры: медиана'], 2000); assert.equal(sk[0]['Дней между роликами (медиана)'], 4);
  assert.equal(sk[0]['Роликов с хэштегами'], '50%'); assert.equal(sk[0]['Ключевые слова канала'], 'baroque bach');
  const st = await run('Статус: готово', { 'Ролики: запрос данных': d }, [vids]);
  assert.ok(st[0]['Статус'].startsWith('готово ') && st[0]['Статус'].endsWith(': 2 роликов')); assert.equal(st[0]['Ссылка'], p[0].link);
  const se = await run('Статус: ошибка', {}, [k[4]]);
  assert.equal(se[0]['Статус'], 'ошибка: не понимаю ссылку');
  console.log('14 ALL OK');
})().catch(e => { console.error('FAIL', e); process.exit(1); });
