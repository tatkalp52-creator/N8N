// Лупа: подставляем уточнённые точки в строки пункта (меняются только числа этих точек).
const plan = $('Лупа: план').first().json;
const r = $('Разбираем ответ этапа').first().json;
const points = ($('Сервер: лупа').first().json || {}).points || [];
let resp = {};
try { resp = $('OpenAI: уточнение').first().json || {}; } catch (e) {}
const call = (resp.output || []).find(i => i.type === 'function_call');
let refined = [];
try { refined = JSON.parse((call && call.arguments) || '{}').points || []; } catch (e) { refined = []; }
const lines = String(plan.fx).split('\n');
let moved = 0;
for (const q of refined) {
  const p = points.find(pp => pp.id === String(q.id));
  const x = Number(q.x), y = Number(q.y);
  if (!p || !isFinite(x) || !isFinite(y) || x < 0 || x > 100 || y < 0 || y > 100) continue;
  if (Math.abs(x - p.x) > 11 || Math.abs(y - p.y) > 19) continue;   // дальше кусочка (±10 % ширины) — не верим
  const line = lines[p.line] || '';
  const head = line.indexOf(':') >= 0 ? line.indexOf(':') + 1 : 0;
  const re = /-?\d+(?:\.\d+)?/g;
  const nums = [];
  let m;
  while ((m = re.exec(line.slice(head)))) nums.push({ at: head + m.index, len: m[0].length });
  const a = nums[2 * p.pair], b = nums[2 * p.pair + 1];
  if (!a || !b) continue;
  const fmt = v => String(Math.round(v * 10) / 10);
  lines[p.line] = line.slice(0, a.at) + fmt(x) + line.slice(a.at + a.len, b.at) + fmt(y) + line.slice(b.at + b.len);
  if (Math.abs(x - p.x) >= 0.3 || Math.abs(y - p.y) >= 0.3) moved++;
}
const state = stParseState(r.editorState);
if (plan.n != null && state.items[plan.n]) state.items[plan.n].text = lines.join('\n');
return [{ json: { editorState: JSON.stringify(state), moved, refined: refined.length } }];
