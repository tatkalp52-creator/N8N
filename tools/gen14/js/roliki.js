const prev = $('Ролики: запрос списка').all();
return $input.all().map((it, i) => {
  const src = prev[i].json;
  const ids = ((it.json || {}).items || []).map(x => (x.contentDetails || {}).videoId).filter(Boolean);
  return { json: { ...src, videoIds: ids,
    vUrl: ids.length ? `https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,contentDetails&id=${ids.join(',')}` : '' } };
});
