// Разбор каналов YouTube (23.10): лист «Каналы для разбора» — Ссылка | Группа | Сколько роликов | Статус.
// Берём строки без статуса. Ссылка — канал (@имя, /channel/UC…, /user/…, /c/…) или любой ролик канала.
// Группа — любая метка автора («классика», «джаз», «кулинария»): по ней потом разбор, коду она не важна.
const API = 'https://www.googleapis.com/youtube/v3/';
const MAX_PER_RUN = 10;
function parse(raw) {
  const s = String(raw || '').trim();
  if (!s) return null;
  let m;
  if ((m = s.match(/(?:v=|youtu\.be\/|\/shorts\/|\/live\/|\/embed\/)([A-Za-z0-9_-]{11})/))) return { kind: 'video', value: m[1] };
  if ((m = s.match(/\/channel\/(UC[A-Za-z0-9_-]{22})/)) || (m = s.match(/^(UC[A-Za-z0-9_-]{22})$/))) return { kind: 'id', value: m[1] };
  if ((m = s.match(/(?:^|\/)@([^/?#\s]+)/))) return { kind: 'handle', value: '@' + decodeURIComponent(m[1]) };
  if ((m = s.match(/\/user\/([^/?#\s]+)/))) return { kind: 'user', value: m[1] };
  if ((m = s.match(/\/c\/([^/?#\s]+)/))) return { kind: 'custom', value: decodeURIComponent(m[1]) };
  if (/^[\w.-]+$/.test(s)) return { kind: 'handle', value: '@' + s };
  return null;
}
const url = p => p.kind === 'video' ? `${API}videos?part=snippet&id=${p.value}`
  : p.kind === 'id' ? `${API}channels?part=id&id=${p.value}`
  : p.kind === 'handle' ? `${API}channels?part=id&forHandle=${encodeURIComponent(p.value)}`
  : p.kind === 'user' ? `${API}channels?part=id&forUsername=${encodeURIComponent(p.value)}`
  : `${API}search?part=snippet&type=channel&maxResults=1&q=${encodeURIComponent(p.value)}`;
const out = [];
for (const it of $input.all()) {
  const r = it.json || {};
  const link = String(r['Ссылка'] || '').trim();
  if (!link || String(r['Статус'] || '').trim()) continue;
  const limit = Math.max(1, Math.min(50, parseInt(r['Сколько роликов'], 10) || 50));
  const p = parse(link);
  out.push({ json: { link, group: String(r['Группа'] || '').trim(), limit, kind: p ? p.kind : 'bad', step1Url: p ? url(p) : '' } });
  if (out.length >= MAX_PER_RUN) break;
}
return out;
