// Передаём выпуск следующему этапу: канвас вызывает сам себя (новый запуск
// читает таблицу заново — никакой путаницы с устаревшими данными).
let r = null;
try { r = $('Итог хода').first().json; } catch (e) {}
let ctx = null;
try { ctx = $('Контекст проекта').first().json; } catch (e) {}
let event = r && r.event ? r.event : '';
try { const a = $('Согласуем вариант').first().json; if (a && a.ok) event = `Картинка согласована (вариант ${a.variantNumber}).`; } catch (e) {}
try { const a = $('Авто: согласуем картинку').first().json; if (a && a.ok) event = 'Картинка готова.'; } catch (e) {}
if (!ctx) {
  // новый выпуск: контекста ещё нет — берём из создания проекта
  const p = $('Генерируем ProjectID').first().json;
  return [{ json: { kind: 'stageStart', projectId: p.projectId, channelKey: p.channelKey, chatId: p.chatId, event: 'Новый выпуск.' } }];
}
return [{ json: { kind: 'stageStart', projectId: ctx.projectId, channelKey: ctx.channelKey, chatId: ctx.chatId, event } }];
