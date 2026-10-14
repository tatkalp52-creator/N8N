const { chromium } = require('/opt/node22/lib/node_modules/playwright');
(async () => { const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1280, height: 760 } });
 for (const v of ['a','b','c']) { await p.goto('file://' + __dirname + '/mock.html#' + v); await p.reload(); await p.waitForTimeout(200); await p.screenshot({ path: __dirname + '/variant_' + v + '.png' }); }
 await b.close(); })();
