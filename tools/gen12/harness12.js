const fs = require('fs');
const wf = JSON.parse(fs.readFileSync(__dirname + '/../../workflows/12_Этапы.json', 'utf8'));
const byName = Object.fromEntries(wf.nodes.map(n => [n.name, n]));
// ctx.nodes: имя узла → json (или массив json — для узлов с несколькими строками)
async function run(nodeName, ctx) {
  const code = byName[nodeName].parameters.jsCode;
  // (28.10) «Разбираем входящее» получает всё из «Работы»: { work: { source, body } } — старые тесты дают сырой вход
  if (nodeName === 'Разбираем входящее' && ctx.nodes && !(ctx.nodes['Вызов изнутри'] || {}).work) {
    const n = ctx.nodes;
    const work = n['Telegram Trigger'] ? { source: 'tg', body: n['Telegram Trigger'] }
      : n['Из календаря'] ? { source: 'cal', body: n['Из календаря'] } : { source: 'inner', body: n['Вызов изнутри'] || {} };
    ctx = { ...ctx, nodes: { ...n, 'Вызов изнутри': { work } } };
  }
  const $ = (n) => {
    if (!(n in ctx.nodes)) throw new Error(`Referenced node is unexecuted: ${n}`);
    const v = ctx.nodes[n];
    const arr = Array.isArray(v) ? v : [v];
    const it = j => ({ json: j, binary: j && j.__binary });
    return { first: () => it(arr[0]), all: () => arr.map(it), item: it(arr[0]) };
  };
  const input = (ctx.input || []).map(j => ({ json: j, binary: j && j.__binary }));
  const $input = { first: () => input[0], all: () => input };
  const DateTime = { now: () => ({ toFormat: () => '20261004_120000' }) };
  // статические данные workflow — только если тест их передал (ctx.staticData)
  const sdFn = ctx.staticData ? () => ctx.staticData : undefined;
  const f = new Function('$', '$input', 'items', 'DateTime', '$getWorkflowStaticData', '$execution', '$env', `return (async () => {\n${code}\n})();`);
  const out = await f.call({ helpers: { getBinaryDataBuffer: async (i, k) => Buffer.from(String(((input[i] || {}).binary || {})[k] || '')) } }, $, $input, input, DateTime, sdFn, { id: 'E1' }, ctx.env || { WEBHOOK_URL: 'https://n8n.example/' });
  return out.map(o => (o.binary ? { ...o.json, __binary: o.binary } : o.json));
}
module.exports = { run, wf };
