const ctx = $('Контекст проекта').first().json;
const published = ctx.status === 'Опубликовано';
const approved = ctx.status === 'Утверждено';
return [{
  json: {
    published,
    approved,
    tracksUrl: ctx.tracksUrl,
    publishedText: `Этот проект уже опубликован — ссылку не сохраняю и сборку не запускаю.\n\nID: ${ctx.projectId}`,
    waitText: `Ссылку на треки сохранила ✅. Сборка начнётся сама, как только будет нажата финальная ✅ под сводкой текстового блока.\n\nID: ${ctx.projectId}`,
  }
}];
