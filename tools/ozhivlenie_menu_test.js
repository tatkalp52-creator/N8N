const { chromium } = require('playwright'); const fs = require('fs'), path = require('path'); const D = process.argv[2];
(async () => {
  const b = await chromium.launch(); const pg = await b.newPage({ viewport: { width: 390, height: 780 } });
  const errors = []; pg.on('pageerror', e => errors.push(String(e)));
  await pg.route('**/*', async r => {
    const u = new URL(r.request().url());
    if (u.hostname === 'telegram.org') return r.fulfill({ body: 'window.Telegram={WebApp:{ready(){},expand(){},close(){},initDataUnsafe:{user:{id:1}},MainButton:{setText(){},show(){},hide(){},onClick(){}},showPopup(){}}}', contentType: 'application/javascript' });
    if (u.searchParams.get('episodes')) return r.fulfill({ body: JSON.stringify({ episodes: [{ p: '20261031_100000_pengui', ch: 'pengui', img: 'https://n8n.test/pic.jpg', title: 'Danse Macabre', status: 'Картинка согласована' }] }), contentType: 'application/json' });
    if (u.searchParams.get('catalog')) return r.fulfill({ body: fs.readFileSync(path.join(D, 'catalog.json')), contentType: 'application/json' });
    if (u.pathname.endsWith('pic.jpg')) return r.fulfill({ body: fs.readFileSync(path.join(D, 'pic.jpg')), contentType: 'image/jpeg' });
    if (u.pathname.endsWith('/app')) return r.fulfill({ body: fs.readFileSync(path.join(D, 'ozhivlenie.html')), contentType: 'text/html' });
    return r.fulfill({ status: 404, body: '' });
  });
  await pg.goto('https://n8n.test/app?f=ozhivlenie.html&submit=https://n8n.test/submit'); await pg.waitForTimeout(600);
  console.log('список:', await pg.$$eval('#panel button', bs => bs.map(x => x.textContent)));
  await pg.click('#panel button'); await pg.waitForTimeout(700);
  console.log('эффектов:', (await pg.$$('#tools button')).length, 'картинка:', await pg.$eval('#pic', i => i.naturalWidth));
  console.log('ошибки:', errors.length ? errors : 'нет'); await b.close();
})();
