const fs = require('fs');
const wf = JSON.parse(fs.readFileSync('/home/user/N8N/workflows/10_Единый_редактор.json', 'utf8'));
const byName = Object.fromEntries(wf.nodes.map(n => [n.name, n]));
async function run(nodeName, ctx) {
  const code = byName[nodeName].parameters.jsCode;
  const $ = (n) => {
    if (!(n in ctx.nodes)) throw new Error(`Referenced node is unexecuted: ${n}`);
    const v = ctx.nodes[n];
    return { first: () => ({ json: v }), item: { json: v } };
  };
  const input = (ctx.input || []).map(j => ({ json: j }));
  const $input = { first: () => input[0], all: () => input };
  const DateTime = { now: () => ({ toFormat: () => '20260924_120000' }) };
  const f = new Function('$', '$input', 'items', 'DateTime', `return (async () => {\n${code}\n})();`);
  const out = await f.call({ helpers: {} }, $, $input, input, DateTime);
  return out.map(o => o.json);
}
module.exports = { run };
