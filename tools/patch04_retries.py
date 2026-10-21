# (22.10) Тихие повторы в 04: временный сбой Google / OpenAI / Телеграма (429, «занят», обрыв связи)
# повторяется сам — 3 попытки с паузой 5 с, — и до Сторожа с пугающим сообщением не доходит.
# Сборка видео (POST) не повторяется: она идёт часами, её загрузки повторяет сам сборщик.
# Повторный запуск скрипта ничего не меняет.
import json, os
P = os.path.join(os.path.dirname(__file__), '..', 'workflows', '04_Video.json')
w = json.load(open(P, encoding='utf-8'))
SKIP = {'Собираем видео (POST)', 'Загружаем на YouTube'}
n_set = 0
for n in w['nodes']:
    if n['name'] in SKIP or n.get('retryOnFail'):
        continue
    if n['type'] in ('n8n-nodes-base.httpRequest', 'n8n-nodes-base.googleSheets'):
        n['retryOnFail'] = True
        n['maxTries'] = 3
        n['waitBetweenTries'] = 5000
        n_set += 1
json.dump(w, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('повторы добавлены узлам:', n_set)
