// общее для строк разбора
function isoMin(d) { const m = String(d || '').match(/P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/); if (!m) return 0; return Math.round(((+m[1] || 0) * 1440 + (+m[2] || 0) * 60 + (+m[3] || 0) + (+m[4] || 0) / 60) * 10) / 10; }
function hashtags(t) { return [...new Set(String(t || '').match(/#[\p{L}\p{N}_]+/gu) || [])]; }
function median(a) { const s = a.filter(x => x != null && !isNaN(x)).sort((x, y) => x - y); if (!s.length) return ''; const k = Math.floor(s.length / 2); return s.length % 2 ? s[k] : Math.round((s[k - 1] + s[k]) / 2); }
function today() { const d = new Date(); return String(d.getUTCDate()).padStart(2, '0') + '.' + String(d.getUTCMonth() + 1).padStart(2, '0') + '.' + d.getUTCFullYear(); }
function chLink(ch) { const h = ((ch || {}).snippet || {}).customUrl; return h ? 'https://www.youtube.com/' + (h.startsWith('@') ? h : '@' + h) : 'https://www.youtube.com/channel/' + ((ch || {}).id || ''); }
