# Авточистка через Kaggle — проект (код НЕ написан, ждёт обкатки)

Цель: бот/04 без изменений; сборщик сам гоняет блокнот suno-clean, ждёт, забирает чистый zip и собирает видео.

## Поток
1. 04 → `/assemble` как сейчас (audioZipUrl = ссылка на zip на Диске). Колонки 🎬 уже передаются автоматически.
2. Если `cleanMode` (🎬tmpl_CleanMode) не пуст и ссылка не kaggle.com/code/ → сборщик:
   - берёт код чистки из `/app/suno_clean_kaggle.py` (обновляется wget, как app.py);
   - подставляет в строки настроек `TRACKS_LINK`, `MODE`, `BLEND`, `BLEND_STEMS` (как в wan_loop: замена `^ИМЯ = ...`; не нашёл строку → ошибка, а не молчаливый запуск);
   - заворачивает в .ipynb с одной ячейкой и шлёт SaveKernel;
   - ждёт статус; COMPLETE → скачивает output (уже есть `download_kaggle_output_zip`) → сборка как обычно.
3. Пусто → всё как раньше (ручной путь со ссылкой на блокнот тоже остаётся).

## API (сверено по официальному клиенту kaggle 2.2.4 / kagglesdk 0.1.37)
База `https://api.kaggle.com/v1/`, `Authorization: Bearer <token>`, тело JSON в camelCase.
- `kernels.KernelsApiService/SaveKernel`:
  `{slug:"td1976/suno-clean", text:<ipynb json строкой>, language:"python", kernelType:"notebook", isPrivate:true, enableGpu:true, enableInternet:true, machineShape:"NvidiaTeslaT4"}`
  → `{versionNumber, url, error, ...}`. `error` не пуст → стоп с текстом ошибки.
  machineShape варианты: NvidiaTeslaT4 (это и есть «T4 x2»), NvidiaTeslaP100, Tpu1VmV38.
  Сохранение = новая версия + запуск (как Save & Run All). Код блокнота в Kaggle заменяется версией с сервера.
- `kernels.KernelsApiService/GetKernelSessionStatus` `{userName, kernelSlug}` → `{status, failureMessage}`.
  status: QUEUED, RUNNING, COMPLETE, ERROR, CANCEL_REQUESTED, CANCEL_ACKNOWLEDGED, NEW_SCRIPT
  (строка может прийти с префиксом KERNEL_WORKER_STATUS_ — сравнивать по окончанию).
- `kernels.KernelsApiService/ListKernelSessionOutput` — уже работает в сборщике.

## Риски и защита
1. Сбой сети/сервера при опросе → не ошибка: пропускаем, пробуем на следующем опросе; ошибка только после ~5 неудач подряд. Поэтому частота опроса на надёжность не влияет, только на задержку.
2. Частота опроса — ячейка `🎬tmpl_CleanPollMinutes`, по умолчанию 15 (решение автора). Цена: до 15 мин лишнего ожидания.
3. Старый output: сразу после запуска новой версии список файлов ещё от прошлой → качать только после COMPLETE и проверять, что имя zip = «<имя входного архива> (clean).zip».
4. Очередь GPU / зависание → общий предел ожидания (ячейка, по умолч. 4 ч; у 04 таймаут 6 ч). Превышен → понятная ошибка в отчёт.
5. ERROR в Kaggle (кончилась квота 30 ч/нед, битая ссылка на Диск, ошибка кода) → в отчёт failureMessage. Собирать ли тогда без чистки — решение автора (ячейка `🎬tmpl_CleanFallback`: пусто = стоп).
6. Два выпуска одновременно → оба пишут в один блокнот и перебьют друг друга → в сборщике замок: одна чистка за раз, второй ждёт.
7. Перезапуск сборщика во время ожидания → ожидание теряется, но Kaggle доработает; тогда ручной путь: ссылку на блокнот боту.
8. Ключ: 401/403 → «ключ Kaggle не принят (истёк/удалён?)».
9. Ссылка на Диск должна быть «всем, у кого есть ссылка» — иначе gdown в Kaggle упадёт (п.5).
10. Код чистки на сервере и в репо — один файл tools/kaggle/suno_clean_kaggle.py; меняем способ → wget на сервер.

## Время
~1 ч чистка (21 трек, T4) + ~33 мин сборка ≈ 1,5 ч без участия автора.
