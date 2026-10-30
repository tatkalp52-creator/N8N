# (22.10) Обложки Б/В в Телеграм: строки «обложка Б/В: кадр …» из пункта 9 сборщик превращает в картинки
# при сборке; после сообщения «видео на YouTube» 04 спрашивает у сборщика, какие обложки есть, и шлёт
# каждую файлом (без сжатия Телеграма) — для «Тест и сравнение» в Studio. Сбой здесь ничего не роняет.
# Повторный запуск скрипта ничего не меняет.
import json, os, uuid
P = os.path.join(os.path.dirname(__file__), '..', 'workflows', '04_Video.json')
w = json.load(open(P, encoding='utf-8'))
SERVER = 'http://sgteo3bx0oyq9tipeiy0qou6.45.76.43.137.sslip.io'
PID = "{{ $('Нормализуем вход').first().json.projectId }}"
RETRY = {'retryOnFail': True, 'maxTries': 3, 'waitBetweenTries': 5000}
names = {n['name'] for n in w['nodes']}
NEW = [
    {'name': 'Обложки Б/В: какие есть', 'type': 'n8n-nodes-base.httpRequest', 'typeVersion': 4.4, 'position': [8704, 2400],
     'parameters': {'url': '=' + SERVER + '/covers/' + PID, 'options': {}}, 'continueOnFail': True, **RETRY},
    {'name': 'Обложки Б/В: по одной', 'type': 'n8n-nodes-base.code', 'typeVersion': 2, 'position': [8928, 2400],
     'parameters': {'jsCode': "// Нет строк обложек в пункте 9 или сборщик не ответил — ничего не шлём, молча.\n"
                              "return $input.all().flatMap(i => ((i.json && i.json.covers) || []).filter(c => c && c.file).map(c => ({ json: c })));"}},
    {'name': 'Скачиваем обложку Б/В', 'type': 'n8n-nodes-base.httpRequest', 'typeVersion': 4.4, 'position': [9152, 2400],
     'parameters': {'url': '=' + SERVER + '/cover_file/' + PID + '/{{ $json.file }}',
                    'options': {'response': {'response': {'responseFormat': 'file'}}}}, 'continueOnFail': True, **RETRY},
    {'name': 'Шлём обложку Б/В', 'type': 'n8n-nodes-base.httpRequest', 'typeVersion': 4.4, 'position': [9376, 2400],
     'parameters': {'method': 'POST', 'url': '=https://api.telegram.org/bot{{ $env.TELEGRAM_BOT_TOKEN }}/sendDocument',
                    'sendBody': True, 'contentType': 'multipart-form-data',
                    'bodyParameters': {'parameters': [
                        {'name': 'chat_id', 'value': "={{ $('Готовим данные для сборки').first().json.chatId }}"},
                        {'name': 'caption', 'value': "=Обложка {{ $('Обложки Б/В: по одной').item.json.letter }} — для «Тест и сравнение» в YouTube Studio"},
                        {'parameterType': 'formBinaryData', 'name': 'document', 'inputDataFieldName': 'data'}]},
                    'options': {}}, 'continueOnFail': True, **RETRY},
]
added = 0
for n in NEW:
    if n['name'] in names:
        continue
    n['id'] = str(uuid.uuid5(uuid.NAMESPACE_URL, 'n8n-04-' + n['name']))
    w['nodes'].append(n)
    added += 1
c = w['connections']
def link(a, b):
    outs = c.setdefault(a, {'main': [[]]})['main']
    if not any(t['node'] == b for t in outs[0]):
        outs[0].append({'node': b, 'type': 'main', 'index': 0})
for src in ('Сообщаем: видео на YouTube', 'Сообщаем: видео без обложки'):
    link(src, NEW[0]['name'])
for a, b in zip(NEW, NEW[1:]):
    link(a['name'], b['name'])
json.dump(w, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('узлов обложек добавлено:', added)
