const prep = $('Готовим запись в летопись').first().json;
const r = $input.first().json || {};
const lines = (r.output || [])
  .filter(i => i.type === 'message')
  .flatMap(i => (i.content || []).filter(c => c.type === 'output_text').map(c => c.text))
  .join('\n')
  .trim();
const entry = lines ? `${prep.date}\n${lines}` : '';
return [{
  json: {
    ok: !!(entry && prep.chronicleKey),
    chronicleKey: prep.chronicleKey,
    chronicle: entry ? [prep.chronicle, entry].filter(Boolean).join('\n\n') : prep.chronicle,
  },
}];
