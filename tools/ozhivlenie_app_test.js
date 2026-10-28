// Проверка приложения «Оживление» в браузере (Playwright): node tools/ozhivlenie_app_test.js <папка с ozhivlenie.html, catalog.json, pic.jpg>
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const D = process.argv[2];
(async () => {
  const b = await chromium.launch(); const pg = await b.newPage({ viewport: { width: 390, height: 780 }, hasTouch: false });
  const errors = []; pg.on('pageerror', e => errors.push(String(e))); pg.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  let posted = null;
  await pg.route('**/*', async r => {
    const u = new URL(r.request().url());
    if (u.hostname === 'telegram.org') return r.fulfill({ body: `window.Telegram={WebApp:{ready(){},expand(){},close(){window.__closed=1},initDataUnsafe:{user:{id:285577543}},
      MainButton:{setText(t){window.__mb=t},show(){window.__mbShown=1},hide(){window.__mbShown=0},onClick(f){window.__mbClick=f}},
      showPopup(o,cb){window.__popup=o;cb('replace')}}}`, contentType: 'application/javascript' });
    if (u.searchParams.get('catalog')) return r.fulfill({ body: fs.readFileSync(path.join(D, 'catalog.json')), contentType: 'application/json' });
    if (u.pathname.endsWith('pic.jpg')) return r.fulfill({ body: fs.readFileSync(path.join(D, 'pic.jpg')), contentType: 'image/jpeg' });
    if (u.pathname.endsWith('/submit')) { posted = JSON.parse(r.request().postData()); return r.fulfill({ body: '{}', contentType: 'application/json' }); }
    if (u.pathname.endsWith('/app')) return r.fulfill({ body: fs.readFileSync(path.join(D, 'ozhivlenie.html')), contentType: 'text/html' });
    return r.fulfill({ status: 404, body: '' });
  });
  await pg.goto('https://n8n.test/app?f=ozhivlenie.html&p=20261004_120000_pengui&ch=pengui&img=https://n8n.test/pic.jpg&submit=https://n8n.test/submit');
  await pg.waitForTimeout(800);
  const tools = await pg.$$eval('#tools button', bs => bs.map(b => b.textContent));
  console.log('эффекты:', tools.join(' | '));
  const box = await (await pg.$('#pic')).boundingBox();
  const P = (x, y) => [box.x + box.width * x / 100, box.y + box.height * y / 100];
  const tool = async n => { await pg.click(`#tools button:text-is("${n}")`); };
  // пар над кружкой: касание → овал, потянуть ручку ширины
  await tool('пар над кружкой'); await pg.mouse.click(...P(30, 60));
  const h = await pg.$('circle[data-h="a"]'); const hb = await h.boundingBox();
  await pg.mouse.move(hb.x + hb.width / 2, hb.y + hb.height / 2); await pg.mouse.down(); await pg.mouse.move(hb.x + 60, hb.y + 3, { steps: 6 }); await pg.mouse.up();
  await pg.fill('.mk label:has-text("скорость") input', '-5');
  await pg.fill('.mk label:has-text("ширина") input', '0,75');
  // моргание: касание (круг) → радиус
  await tool('моргание'); await pg.mouse.click(...P(50, 30));
  // звёзды: обвести пальцем
  await tool('звёзды'); console.log('до звёзд', await pg.$$eval('.mk', x => x.length), await pg.textContent('#hint'), JSON.stringify(P(10,5)), JSON.stringify(box)); await pg.mouse.move(...P(10, 5)); await pg.mouse.down();
  for (const [x, y] of [[30, 5], [30, 20], [10, 20], [10, 6]]) await pg.mouse.move(...P(x, y), { steps: 5 });
  await pg.mouse.up(); console.log('после звёзд', await pg.$$eval('.mk', x => x.length));
  // гирлянда: три касания и «Готово»
  await tool('гирлянда'); for (const x of [60, 65, 70]) await pg.mouse.click(...P(x, 10)); await pg.click('#bDone');
  // листья: провести путь
  await tool('листья'); await pg.mouse.move(...P(40, 5)); await pg.mouse.down(); await pg.mouse.move(...P(42, 60), { steps: 12 }); await pg.mouse.up();
  await pg.fill('.mk input[type=text]', 'клён; раз в 2 мин');
  // обложка: касание → рамка, сторона слева
  await tool('обложка'); await pg.mouse.click(...P(50, 50)); await pg.click('.mk:last-child button:text-is("слева")');
  const lines = await pg.$$eval('.mk code', cs => cs.map(c => c.textContent));
  console.log(lines.join('\n'));
  console.log('кнопка:', await pg.evaluate(() => window.__mb));
  await pg.evaluate(() => window.__mbClick());
  await pg.waitForTimeout(400);
  console.log('ушло:', JSON.stringify(posted));
  console.log('закрылось:', await pg.evaluate(() => window.__closed));
  await pg.screenshot({ path: path.join(D, 'shot.png') });
  console.log('ошибки:', errors.length ? errors : 'нет');
  await b.close();
})();
