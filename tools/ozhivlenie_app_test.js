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

  const all = () => pg.evaluate(() => window.__lines());
  const stX = () => pg.evaluate(() => [Konva.stages[0].x(), Konva.stages[0].y()]);
  const knob = (k, b) => pg.click(`.knob:has(.kn:text-is("${k}")) button:text-is("${b}")`);

  // 1. пар: выбрать в полоске, растянуть овал
  await tool('пар над кружкой');
  await dragPath([P(30, 60), P(36, 63)]); await pg.waitForTimeout(150);
  let L = await all();
  ok(/^пар: (29\.\d|30(\.\d)?), (59\.\d|60(\.\d)?); овал \d/.test(L[0] || ''), 'овал движением: ' + L[0]);
  const G2 = await geo();
  ok(Math.abs(G2.x - G.x) < 1 && Math.abs(G2.y - G.y) < 1 && Math.abs(G2.w - G.w) < 1, 'картинка на месте после отметки');
  const anchor = await handleAt('middle-right');
  const a0 = (L[0].match(/овал ([\d.]+)/) || [])[1];
  await dragPath([anchor, [anchor[0] + 40, anchor[1]]]);
  L = await all(); const a1 = (L[0].match(/овал ([\d.]+)/) || [])[1];
  ok(Number(a1) > Number(a0), 'ручка растягивает овал: ' + a0 + ' → ' + a1);
  const rot = await handleAt('rotater');
  await dragPath([rot, [rot[0] + 60, rot[1] + 25]]);
  L = await all();
  ok(/наклон -?\d+/.test(L[0]), 'поворот даёт наклон: ' + L[0]);
  const ec = await pg.evaluate(() => { const s = Konva.stages[0], e = s.findOne('Ellipse'), p = e.getAbsolutePosition(), r = s.container().getBoundingClientRect(); return [r.left + p.x, r.top + p.y]; });
  const before = L[0].match(/^пар: ([\d.]+), ([\d.]+)/);
  await dragPath([ec, [ec[0] + G.w * 0.1, ec[1]]]);
  L = await all(); const after = L[0].match(/^пар: ([\d.]+), ([\d.]+)/);
  ok(after && Math.abs(after[1] - before[1] - 10) < 0.6 && L.length === 1, 'овал переносится на 10%: ' + before[1] + ' → ' + (after && after[1]) + ', отметок ' + L.length);
  // ручки: каждая своей строкой; − и + и ползунок
  ok((await pg.$$('.knob')).length >= 3, 'ручки отдельными строками: ' + (await pg.$$('.knob')).length);
  await knob('скорость', '−'); await knob('густота', '+');
  L = await all();
  ok(/скорость 4\.5/.test(L[0]) && /густота 5\.5/.test(L[0]), 'ручки −/+: ' + L[0].split('; ').slice(-2).join('; '));
  const rg = await pg.$('.knob:has(.kn:text-is("завитки")) input[type=range]');
  if (rg) { const bb = await rg.boundingBox(); await tapAt([bb.x + bb.width * 0.9, bb.y + bb.height / 2]); L = await all(); ok(/завитки (8\.\d|9(\.\d)?)/.test(L[0]), 'ползунок: ' + (L[0].match(/завитки [\d.]+/) || [''])[0]); }
  // 2. Готово → щелчок по картинке ничего не ставит, протяжка двигает картинку
  await pg.click('#bDone');
  await tapAt(P(32, 61)); await tapAt(P(70, 30));
  ok((await all()).length === 1 && (await pg.$$('.mk.sel')).length === 0, 'после «Готово» щелчок по картинке нового пара не ставит');
  // увеличить кнопкой ＋ и потащить картинку
  await pg.click('#zoom button:text-is("＋")'); await pg.click('#zoom button:text-is("＋")'); await pg.waitForTimeout(80);
  const Gz = await geo(); ok(Gz.s > G.s * 1.8, 'кнопка ＋ увеличивает: ×' + (Gz.s / G.s).toFixed(2));
  let s0 = await stX(); const c0 = [G.x + 0, 0];
  const mid = [Gz.x + Gz.w / 2, Gz.y + Gz.h / 2], box = await pg.$eval('#stage', e => { const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; });
  await dragPath([box, [box[0] - 120, box[1] - 60]]);
  let s1 = await stX();
  ok(Math.abs(s1[0] - s0[0] + 120) < 3 && (await all()).length === 1, 'протяжка двигает картинку (' + Math.round(s1[0] - s0[0]) + '), отметок не прибавилось');
  // полоса прокрутки снизу двигает картинку
  const th = await pg.$eval('#sbX i', e => { const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; });
  s0 = await stX(); await dragPath([th, [th[0] + 60, th[1]]]); s1 = await stX();
  ok(s1[0] < s0[0] - 20, 'полоса прокрутки двигает картинку: ' + Math.round(s1[0] - s0[0]));
  const thy = await pg.$eval('#sbY i', e => { const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; });
  s0 = await stX(); await dragPath([thy, [thy[0], thy[1] - 50]]); s1 = await stX();
  ok(s1[1] > s0[1] + 10, 'полоса справа двигает картинку: ' + Math.round(s1[1] - s0[1]));
  // назад к целому виду
  for (let i = 0; i < 4; i++) await pg.click('#zoom button:text-is("−")');
  G = await geo(); ok(Math.abs(G.s - G2.s) < 0.01, 'кнопка − возвращает к целой картинке и не мельче');
  // 3. гирлянда: три лампочки, «↶» убирает одну, а не всю
  await tool('гирлянда'); for (const x of [60, 65, 70]) await tapAt(P(x, 10));
  L = await all(); ok(L.length === 2 && (L[1].match(/;/g) || []).length === 2, 'гирлянда из трёх: ' + L[1]);
  await pg.click('#bUndo');
  L = await all(); ok(L.length === 2 && (L[1].match(/;/g) || []).length === 1, '«↶» убрал одну лампочку: ' + L[1]);
  await tapAt(P(72, 12));
  L = await all(); ok((L[1].match(/;/g) || []).length === 2, 'лампочка поставлена снова: ' + L[1]);
  await pg.click('#bDone');
  const vis = await pg.evaluate(() => Konva.stages[0].find('.dot').filter(d => d.isVisible()).length);
  ok(vis === 0, 'после «Готово» меток гирлянды не видно: ' + vis);
  await tapAt(P(50, 50)); ok((await all()).length === 2, 'щелчок после гирлянды ничего не ставит');
  // открыть гирлянду снова — кнопкой внизу — и добавить лампочку
  await pg.click('#panel .list button:has-text("гирлянда")'); await tapAt(P(75, 12)); await pg.click('#bDone');
  L = await all(); ok((L[1].match(/;/g) || []).length === 3, 'гирлянда открыта снова и дополнена: ' + L[1]);
  // 4. область, листья, обложка
  await tool('звёзды');
  await dragPath([P(10, 5), P(30, 5), P(30, 20), P(10, 20), P(10, 6)]);
  L = await all(); ok(/^звёзды: область /.test(L[2] || ''), 'область обводкой');
  await tool('листья'); await dragPath([P(40, 5), P(41, 30), P(42, 60)]);
  L = await all(); ok(/^листья: [\d.]+, [\d.]+ → /.test(L[3] || ''), 'листья путём');
  // панель листа: плитки, размер, как часто, цвет; превью рисует лист
  await pg.click('.tile:has(span:text-is("3"))'); await pg.click('.tile:has(span:text-is("5"))');
  await pg.click('.lrow button:text-is("крупный")'); await pg.selectOption('.lrow select', '40');
  await pg.click('.lrow label:has-text("как нарисован") input');
  await pg.click('.lrow label:has-text("вглубь") input');
  L = await all(); ok(/^листья: .*; образ\S* 3, 5; цвет 6; крупн\S*; вглубь; раз в 40$/.test(L[3] || ''), 'панель листа: ' + L[3]);
  await pg.click('#bUndo'); L = await all(); ok(!/вглубь/.test(L[3]) && /раз в 40/.test(L[3]), '«↶» снимает одну галочку листа');
  await tool('обложка'); await tapAt(P(75, 60)); await pg.click('.mk.sel button:text-is("слева")');
  L = await all(); ok(/^обложка Б: кадр [\d. ]+ — [\d. ]+, слева$/.test(L[4] || ''), 'обложка: ' + L[4]);
  await pg.click('#bDone');
  // 5. масштаб колесом/двумя пальцами, точка после масштаба — на своём месте
  if (!prof.touch) { await pg.mouse.move(...P(50, 50)); await pg.mouse.wheel(0, -400); }
  else {
    const c = P(50, 50), q = d => [{ x: c[0] - d, y: c[1], id: 1 }, { x: c[0] + d, y: c[1], id: 2 }];
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: q(40) });
    for (const d of [50, 60, 70, 80]) await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: q(d) });
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  }
  await pg.waitForTimeout(100);
  const G3 = await geo(); ok(G3.s > G.s * 1.2, 'масштаб ×' + (G3.s / G.s).toFixed(2));
  G = G3; await tool('дым'); await tapAt(P(55, 40));
  L = await all(); ok(/^дым(ок)?: (54\.\d|55(\.\d)?), (39\.\d|40(\.\d)?)$/.test(L[5] || ''), 'точка после масштаба на своём месте: ' + L[5]);
  // полоска эффектов крутится колесом мыши
  if (!prof.touch) {
    const wide = await pg.$eval('#tools', e => e.scrollWidth > e.clientWidth);
    if (wide) { await pg.mouse.move(...(await pg.$eval('#tools', e => { const r = e.getBoundingClientRect(); return [r.left + 50, r.top + r.height / 2]; }))); await pg.mouse.wheel(0, 300); }
    ok(!wide || await pg.$eval('#tools', e => e.scrollLeft > 0), 'полоска эффектов колесом' + (wide ? '' : ' (влезает целиком)'));
  }
  // 6. «Готово» ничего не отправляет; отправка — своей кнопкой
  await pg.click('#bDone'); await pg.waitForTimeout(100);
  ok(!posted && (await pg.$$('.mk.sel')).length === 0, '«Готово» — эффект закончен, ничего не ушло');
  await pg.click('#bSend'); await pg.waitForTimeout(300);
  ok(posted && posted.action === 'fx' && posted.lines.split('\n').length === 6, 'ушло в бот: ' + (posted ? posted.lines.split('\n').length + ' строк' : 'нет'));
  // 7. окошко строк — те же строки, что ушли
  await pg.click('#bLines'); const lbox = await pg.$eval('#linesText', e => e.value);
  ok(posted && lbox === posted.lines, 'окошко «Строки» — те же строки, что ушли в бот');
  await pg.click('#bLinesClose');
  // 8. закрыли и открыли снова — разметка на месте
  await pg.waitForTimeout(900);
  await pg.reload(); await pg.waitForTimeout(1200);
  const back = await all();
  ok(posted && back.join('\n') === posted.lines, 'после повторного открытия разметка на месте: ' + back.length + ' отметок');
  ok((await pg.$$eval('#panel .hn', h => h.filter(x => /Выберите эффект/.test(x.textContent)).length)) === 0, 'подсказка «выберите эффект» не дублируется внизу');
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
