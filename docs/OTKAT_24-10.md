# Вернуть всё, как было утром 24.10

Делать ПОСЛЕ того, как «Вечер» появится на YouTube (перезапуск n8n оборвёт сборку).
Каждый шаг отдельно. Сделала — следующий.

## 1. Coolify → n8n → Environment Variables
Удалить эти строки (корзина справа):
- `EXECUTIONS_DATA_PRUNE`
- `EXECUTIONS_DATA_MAX_AGE`
- `EXECUTIONS_DATA_PRUNE_MAX_COUNT`
- `DB_SQLITE_VACUUM_ON_STARTUP` (если есть)

`N8N_RUNNERS_AUTO_SHUTDOWN_TIMEOUT` — поставить обратно `15`.

## 2. Coolify → n8n → Docker Compose
Стереть всё и вставить одну строку из файла `compose_backup/n8n_compose_MORNING_one_line.json`
(это утренний файл: исполнитель кода отдельным контейнером, как было). Save.

## 3. Coolify → n8n → Deploy
Подождать, пока статус станет Running (healthy), 1–2 минуты.

## 4. n8n → 12_Этапы
Unpublish → ⋯ → Import from file → `workflows/12_Этапы_утро_24-10.json` → Publish.
(12, каким он был утром: без замка, с повторами.)

## 5. n8n → 04_Video
Unpublish → ⋯ → Import from file → `workflows/04_Video.json` → Publish.
(04 с повторами везде, как вчера.)

## Уже сделано сегодня
- ffmpeg в сборщике возвращён на сборку от 22.10 (та, что работала). Сборщик — только Restart, не Deploy: Deploy скачает новый ffmpeg.
- Потолок процессора у сборщика снят.

## Остаётся из сегодняшнего (безвредно, само слетит при Restart сборщика)
- приоритет n8n над сборщиком (`--cpu-shares 128`).
