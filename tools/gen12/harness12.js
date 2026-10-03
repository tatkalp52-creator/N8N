const fs = require('fs');
const wf = JSON.parse(fs.readFileSync(__dirname + '/../../workflows/12_Этапы.json', 'utf8'));
const byName = Object.fromEntries(wf.nodes.map(n => [n.name, n]));
// ctx.nodes: имя узла → json (или массив json — для узлов с несколькими строками)
async function run(nodeName, ctx) {
  const code = byName[nodeName].parameters.jsCode;
  const $ = (n) => {
    if (!(n in ctx.nodes)) throw new Error(`Referenced node is unexecuted: ${n}`);
    const v = ctx.nodes[n];
    const arr = Array.isArray(v) ? v : [v];
    return { first: () => ({ json: arr[0] }), all: () => arr.map(j => ({ json: j })), item: { json: arr[0] } };
  };
  const input = (ctx.input || []).map(j => ({ json: j }));
  const $input = { first: () => input[0], all: () => input };
  const DateTime = { now: () => ({ toFormat: () => '20261004_120000' }) };
  const f = new Function('$', '$input', 'items', 'DateTime', `return (async () => {\n${code}\n})();`);
  const out = await f.call({ helpers: {} }, $, $input, input, DateTime);
  return out.map(o => o.json);
}
module.exports = { run, wf };
