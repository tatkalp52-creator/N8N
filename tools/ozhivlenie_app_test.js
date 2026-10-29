// Проверка приложения «Оживление» в браузере (Playwright) на трёх устройствах: телефон и планшет (палец), компьютер (мышь).
// node tools/ozhivlenie_app_test.js <папка с ozhivlenie.html, catalog.json, pic.jpg, konva.min.js>
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const D = process.argv[2];
const PROFILES = [
  { name: 'компьютер (мышь)', viewport: { width: 1280, height: 800 }, touch: false },
  { name: 'планшет (палец/стилус)', viewport: { width: 820, height: 1180 }, touch: true },
  { name: 'телефон (палец)', viewport: { width: 390, height: 780 }, touch: true },
];
let fails = 0;
const ok = (c, msg) => { console.log((c ? '  ✓ ' : '  ✗ ') + msg); if (!c) fails++; };

async function runProfile(b, prof) {
  console.log('— ' + prof.name);
  const ctx = await b.newContext({ viewport: prof.viewport, hasTouch: prof.touch, isMobile: prof.touch });
  const pg = await ctx.newPage();
  const errors = []; pg.on('pageerror', e => errors.push(String(e)));
  let posted = null;
  await pg.route('**/*', async r => {
    const u = new URL(r.request().url());
    if (u.hostname === 'telegram.org') return r.fulfill({ body: `window.Telegram={WebApp:{ready(){},expand(){},close(){window.__closed=1},initDataUnsafe:{user:{id:285577543}},
      MainButton:{setText(t){window.__mb=t},show(){},hide(){},onClick(f){window.__mbClick=f}},showPopup(o,cb){cb('replace')}}}`, contentType: 'application/javascript' });
    if (u.searchParams.get('f') === 'konva.min.js') return r.fulfill({ body: fs.readFileSync(path.join(D, 'konva.min.js')), contentType: 'application/javascript' });
    if (u.searchParams.get('catalog')) return r.fulfill({ body: fs.readFileSync(path.join(D, 'catalog.json')), contentType: 'application/json' });
    if (u.pathname.endsWith('pic.jpg')) return r.fulfill({ body: fs.readFileSync(path.join(D, 'pic.jpg')), contentType: 'image/jpeg' });
    if (u.pathname.endsWith('/submit')) { posted = JSON.parse(r.request().postData()); return r.fulfill({ body: '{}', contentType: 'application/json' }); }
    if (u.pathname.endsWith('/app')) return r.fulfill({ body: fs.readFileSync(path.join(D, 'ozhivlenie.html')), contentType: 'text/html' });
    return r.fulfill({ status: 404, body: '' });
  });
  await pg.goto('https://n8n.test/app?f=ozhivlenie.html&p=20261028_173312_pengui&ch=pengui&img=https://n8n.test/pic.jpg&submit=https://n8n.test/submit');
  await pg.waitForTimeout(900);
  const cdp = prof.touch ? await ctx.newCDPSession(pg) : null;
  const tools = await pg.$$eval('#tools button', bs => bs.map(x => x.textContent));
  ok(tools.length >= 10, 'эффекты в полоске: ' + tools.length);
  // где картинка на экране: из сцены Konva
  const geo = () => pg.evaluate(() => { const s = Konva.stages[0], img = s.findOne('Image'), r = s.container().getBoundingClientRect();
    return { x: r.left + s.x(), y: r.top + s.y(), w: img.width() * s.scaleX(), h: img.height() * s.scaleY(), s: s.scaleX(), cw: r.width, ch: r.height }; });
  let G = await geo();
  ok(G.w > 100 && G.h > 50, 'картинка видна ' + Math.round(G.w) + '×' + Math.round(G.h));
  const P = (x, y) => [G.x + G.w * x / 100, G.y + G.h * y / 100];
  const tool = n => pg.click(`#tools button:text-is("${n}")`);
  const lines = () => pg.$$eval('.mk code', cs => cs.map(c => c.textContent));
  // жесты: мышь или палец (CDP)
  async function dragPath(pts) {
    if (!prof.touch) { await pg.mouse.move(...pts[0]); await pg.mouse.down(); for (const q of pts.slice(1)) await pg.mouse.move(...q, { steps: 10 }); await pg.mouse.up(); return; }
    const t = q => [{ x: q[0], y: q[1], id: 1 }];
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: t(pts[0]) });
    for (let i = 1; i < pts.length; i++) for (let k = 1; k <= 10; k++) {
      const a = pts[i - 1], c = pts[i], q = [a[0] + (c[0] - a[0]) * k / 10, a[1] + (c[1] - a[1]) * k / 10];
      await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: t(q) });
    }
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  }
  // где ручка рамки на экране: ищем её на холсте (Konva рисует ручки с отступом от своей точки)
  const handleAt = name => pg.evaluate(nm => { const s = Konva.stages[0], a = s.findOne('.' + nm), p = a.getAbsolutePosition(), r = s.container().getBoundingClientRect();
    let sx = 0, sy = 0, n = 0;
    for (let dx = -30; dx <= 30; dx += 2) for (let dy = -30; dy <= 30; dy += 2) { const h = s.getIntersection({ x: p.x + dx, y: p.y + dy }); if (h && h.name().indexOf(nm) === 0) { sx += dx; sy += dy; n++; } }
    return n ? [r.left + p.x + sx / n, r.top + p.y + sy / n] : [r.left + p.x, r.top + p.y]; }, name);
  async function tapAt(q) { if (prof.touch) await pg.touchscreen.tap(...q); else await pg.mouse.click(...q); await pg.waitForTimeout(60); }

  // 1. овал одним движением
  await tool('пар над кружкой');
  await dragPath([P(30, 60), P(36, 63)]); await pg.waitForTimeout(150);
  let L = await lines();
  ok(/^пар: (29\.\d|30(\.\d)?), (59\.\d|60(\.\d)?); овал \d/.test(L[0] || ''), 'овал движением: ' + L[0]);
  // картинка не сдвинулась и не сжалась, когда появилась отметка
  const G2 = await geo();
  ok(Math.abs(G2.x - G.x) < 1 && Math.abs(G2.y - G.y) < 1 && Math.abs(G2.w - G.w) < 1, 'картинка на месте после отметки');
  // растянуть за правую среднюю ручку рамки
  const anchor = await handleAt('middle-right');
  const a0 = (L[0].match(/овал ([\d.]+)/) || [])[1];
  await dragPath([anchor, [anchor[0] + 40, anchor[1]]]);
  L = await lines(); const a1 = (L[0].match(/овал ([\d.]+)/) || [])[1];
  ok(Number(a1) > Number(a0), 'ручка растягивает овал: ' + a0 + ' → ' + a1);
  // повернуть
  const rot = await handleAt('rotater');
  await dragPath([rot, [rot[0] + 60, rot[1] + 25]]);
  L = await lines();
  ok(/наклон -?\d+/.test(L[0]), 'поворот даёт наклон: ' + L[0]);
  // передвинуть овал за середину (центр — там, где он сейчас)
  const ec = await pg.evaluate(() => { const s = Konva.stages[0], e = s.findOne('Ellipse'), p = e.getAbsolutePosition(), r = s.container().getBoundingClientRect(); return [r.left + p.x, r.top + p.y]; });
  const before = L[0].match(/^пар: ([\d.]+), ([\d.]+)/);
  await dragPath([ec, [ec[0] + G.w * 0.1, ec[1]]]);
  L = await lines(); const after = L[0].match(/^пар: ([\d.]+), ([\d.]+)/);
  ok(after && Math.abs(after[1] - before[1] - 10) < 0.6 && Math.abs(after[2] - before[2]) < 0.6 && L.length === 1, 'овал переносится на 10%: ' + before[1] + ' → ' + (after && after[1]) + ', отметок ' + L.length);
  // касание — кружок-заготовка без размера
  await tapAt(P(70, 40));
  L = await lines();
  ok(/^пар: (69\.\d|70(\.\d)?), (39\.\d|40(\.\d)?)$/.test(L[1] || ''), 'касание — точка без овала: ' + L[1]);
  // ручки − +
  await pg.click('.mk:nth-child(1) label:has-text("скорость") button:text-is("−")');
  await pg.click('.mk:nth-child(1) label:has-text("густота") button:text-is("+")');
  L = await lines();
  ok(/скорость 4/.test(L[0]) && /густота 6/.test(L[0]), 'ручки −/+: ' + L[0].split('; ').slice(-2).join('; '));
  // 2. обвести область
  await tool('звёзды');
  await dragPath([P(10, 5), P(30, 5), P(30, 20), P(10, 20), P(10, 6)]);
  L = await lines();
  ok(/^звёзды: область /.test(L[2] || ''), 'область обводкой');
  // 3. гирлянда: три касания + Готово
  await tool('гирлянда'); for (const x of [60, 65, 70]) await tapAt(P(x, 10)); await pg.click('#bDone');
  L = await lines(); ok(/^гирлянда: [\d.]+, [\d.]+; [\d.]+, [\d.]+; [\d.]+, [\d.]+$/.test(L[3] || ''), 'гирлянда: ' + L[3]);
  // 4. листья: путь
  await tool('листья'); await dragPath([P(40, 5), P(41, 30), P(42, 60)]);
  L = await lines(); ok(/^листья: [\d.]+, [\d.]+ → /.test(L[4] || ''), 'листья путём');
  // 5. обложка: касание → рамка; сторона
  await tool('обложка'); await tapAt(P(50, 50)); await pg.click('.mk:last-child button:text-is("слева")');
  L = await lines(); ok(/^обложка Б: кадр [\d. ]+ — [\d. ]+, слева$/.test(L[5] || ''), 'обложка: ' + L[5]);
  // 6. масштаб: колесо (мышь) или два пальца, и после него отметка — в правильном месте картинки
  if (!prof.touch) { await pg.mouse.move(...P(50, 50)); await pg.mouse.wheel(0, -400); }
  else {
    const c = P(50, 50), q = d => [{ x: c[0] - d, y: c[1], id: 1 }, { x: c[0] + d, y: c[1], id: 2 }];
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: q(40) });
    for (const d of [50, 60, 70, 80]) await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: q(d) });
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  }
  await pg.waitForTimeout(100);
  const G3 = await geo(); ok(G3.s > G.s * 1.2, 'масштаб ×' + (G3.s / G.s).toFixed(2));
  G = G3; await tool('дым'); await tapAt(P(75, 28));
  L = await lines(); ok(/^дым(ок)?: (74\.\d|75(\.\d)?), (27\.\d|28(\.\d)?)$/.test(L[6] || ''), 'точка после масштаба на своём месте: ' + L[6]);
  // 7. отправка
  await pg.evaluate(() => window.__mbClick()); await pg.waitForTimeout(300);
  ok(posted && posted.action === 'fx' && posted.lines.split('\n').length === 7, 'ушло в бот: ' + (posted ? posted.lines.split('\n').length + ' строк' : 'нет'));
  ok(!errors.length, 'ошибок на странице нет' + (errors.length ? ': ' + errors.join('; ') : ''));
  await pg.screenshot({ path: path.join(D, 'shot_' + prof.viewport.width + '.png') });
  await ctx.close();
}

(async () => {
  const b = await chromium.launch();
  for (const p of PROFILES) await runProfile(b, p);
  await b.close();
  console.log(fails ? 'ПРОВАЛОВ: ' + fails : 'ВСЁ ПРОШЛО');
  process.exit(fails ? 1 : 0);
})();
