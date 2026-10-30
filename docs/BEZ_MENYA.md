# Сделать самой, без меня (после выкладки «Вечера»)

Каждый шаг отдельный. Сделала — следующий. Ни один не трогает выпуски.

## 1. Поставить 04 с повторами
n8n → 04_Video → **Unpublish** → ⋯ → **Import from file** → `workflows/04_Video.json` → **Publish**.

## 2. Сторож не засоряет Executions
n8n → 13 Сторож → ⋯ → **Settings** → **Save successful production executions** → **Do not save** → **Save**.

## 3. Удалить старые запуски Сторожа
n8n → **Executions** → фильтр (воронка) → Workflow: **13 Сторож** → галочка «выбрать все» вверху списка → **Delete**.
Если их тысячи и n8n задумался — подождать, не нажимать второй раз.

## 4. Доделать уборку (файлы запусков старше 3 дней)
Сервер (root@vultr), когда ничего не собирается:
```
find /var/lib/docker/volumes/v1kvoquehala9zkdm1m8m7sp_n8n-data/_data/binary_data -type f -mtime +3 -delete; du -sh /var/lib/docker/volumes/v1kvoquehala9zkdm1m8m7sp_n8n-data/_data/binary_data
```
Было 5,4 ГБ — должно стать заметно меньше. То же самое ты делала 13.10.

## 5. Завтра: ушли ли ошибки «timed out»
Сервер (root@vultr), после того как пару раз написала боту:
```
docker logs --since 24h $(docker ps -qf name=n8n-v1kvoquehala9zkdm1m8m7sp) 2>&1 | grep -cE "timed out|Offer expired"
```
**0** — причина снята. Больше нуля — оставь до вторника, разберём.

## Если сборка снова висит
Признак: колёсико в 04 больше часа, а видео не выходит.
Сервер (root@vultr):
```
docker top $(docker ps -qf name=sgteo3bx0oyq9tipeiy0qou6)
```
Есть строка ffmpeg, а сборка висит дольше часа → номер из колонки PID: `kill НОМЕР` → в n8n Executions → 04 → **Stop** → в боте `пересобери`.
