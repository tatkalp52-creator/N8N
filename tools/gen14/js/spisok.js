// Канал → его плейлист «все загрузки» → последние N роликов.
const prev = $('Есть канал?').all();
return $input.all().map((it, i) => {
  const src = prev[i].json, ch = ((it.json || {}).items || [])[0] || null;
  const uploads = ch && ch.contentDetails && ch.contentDetails.relatedPlaylists ? ch.contentDetails.relatedPlaylists.uploads : '';
  return { json: { ...src, channel: ch, error: ch ? '' : 'канал не открылся',
    plUrl: uploads ? `https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&maxResults=${src.limit}&playlistId=${uploads}` : '' } };
});
