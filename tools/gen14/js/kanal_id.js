// Из ответа YouTube — id канала (по видео, по имени, по поиску).
const prev = $('Что разбираем').all();
return $input.all().map((it, i) => {
  const src = prev[i].json, r = it.json || {}, x = (r.items || [])[0];
  const channelId = !x ? '' : (src.kind === 'video' || src.kind === 'custom') ? ((x.snippet || {}).channelId || '') : (x.id || '');
  const error = src.kind === 'bad' ? 'не понимаю ссылку' : r.error ? 'YouTube: ' + String((r.error.message || r.error)).slice(0, 150) : channelId ? '' : 'канал не найден';
  return { json: { ...src, channelId, error,
    chUrl: channelId ? `https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics,contentDetails,brandingSettings&id=${channelId}` : '' } };
});
