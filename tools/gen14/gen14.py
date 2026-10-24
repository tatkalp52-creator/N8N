# Собирает workflows/14_Разбор_каналов.json из js/*.js (lib14.js — в начало узлов строк и статусов).
import json, os, uuid
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, '..', '..')
DOC = '1yEolX-8NV7NInu3OwCoxo2KSSNMny9dk-AVrpKdyNEs'
CRED_SH = {'googleApi': {'id': 'PGJ3stGcaGlz0z9i', 'name': 'Google Sheets account 2'}}
CRED_YT = {'youTubeOAuth2Api': {'id': 'qfSSe0BXXUuYCU11', 'name': 'YouTube account 3'}}
RETRY = {'retryOnFail': True, 'maxTries': 3, 'waitBetweenTries': 5000}
nodes, conns = [], {}
def uid(name): return str(uuid.uuid5(uuid.NAMESPACE_URL, 'n8n-14-' + name))
def js(f, lib=False):
    s = open(os.path.join(HERE, 'js', f), encoding='utf-8').read()
    return (open(os.path.join(HERE, 'js', 'lib14.js'), encoding='utf-8').read() + '\n' + s) if lib else s
def add(n): n.setdefault('id', uid(n['name'])); nodes.append(n); return n
def code(name, f, pos, lib=False):
    return add({'parameters': {'jsCode': js(f, lib)}, 'name': name, 'type': 'n8n-nodes-base.code', 'typeVersion': 2, 'position': pos})
def yt(name, expr, pos):
    return add({'parameters': {'url': '=' + expr, 'authentication': 'predefinedCredentialType', 'nodeCredentialType': 'youTubeOAuth2Api', 'options': {}},
                'name': name, 'type': 'n8n-nodes-base.httpRequest', 'typeVersion': 4.2, 'position': pos,
                'credentials': CRED_YT, 'continueOnFail': True, **RETRY})
def sheet(name, op, sheet_name, pos, extra):
    p = {'authentication': 'serviceAccount', 'documentId': {'__rl': True, 'value': DOC, 'mode': 'id'},
         'sheetName': {'__rl': True, 'value': sheet_name, 'mode': 'name'}, 'options': {}}
    if op: p['operation'] = op
    p.update(extra)
    # (24.10) правило повторов: добавление строк не повторяем (повтор = дубль строк)
    return add({'parameters': p, 'name': name, 'type': 'n8n-nodes-base.googleSheets', 'typeVersion': 4, 'position': pos,
                'credentials': CRED_SH, **({} if op in ('append', 'appendOrUpdate') else RETRY)})
def link(a, b, out=0):
    m = conns.setdefault(a, {'main': []})['main']
    while len(m) <= out: m.append([])
    m[out].append({'node': b, 'type': 'main', 'index': 0})

add({'parameters': {'rule': {'interval': [{'field': 'hours', 'hoursInterval': 1}]}}, 'name': 'Раз в час', 'type': 'n8n-nodes-base.scheduleTrigger', 'typeVersion': 1.2, 'position': [0, 0]})
add({'parameters': {}, 'name': 'Запустить вручную', 'type': 'n8n-nodes-base.manualTrigger', 'typeVersion': 1, 'position': [0, 200]})
sheet('Читаем ссылки', None, 'Каналы для разбора', [220, 100], {})
code('Что разбираем', 'chto.js', [440, 100])
yt('YouTube: находим канал', '{{ $json.step1Url }}', [660, 100])
code('Канал найден?', 'kanal_id.js', [880, 100])
add({'parameters': {'conditions': {'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'loose'},
     'conditions': [{'id': uid('c1'), 'leftValue': '={{ !!$json.channelId }}', 'rightValue': True,
                     'operator': {'type': 'boolean', 'operation': 'true', 'singleValue': True}}], 'combinator': 'and'}, 'options': {}},
     'name': 'Есть канал?', 'type': 'n8n-nodes-base.if', 'typeVersion': 2, 'position': [1100, 100]})
yt('YouTube: канал', '{{ $json.chUrl }}', [1320, 0])
code('Ролики: запрос списка', 'spisok.js', [1540, 0])
yt('YouTube: список роликов', "{{ $json.plUrl || 'https://www.googleapis.com/youtube/v3/videos?part=id&id=none' }}", [1760, 0])
code('Ролики: запрос данных', 'roliki.js', [1980, 0])
yt('YouTube: ролики', "{{ $json.vUrl || 'https://www.googleapis.com/youtube/v3/videos?part=id&id=none' }}", [2200, 0])
code('Строки роликов', 'stroki_rolikov.js', [2420, -200], lib=True)
code('Сводка каналов', 'svodka_kanalov.js', [2420, 0], lib=True)
code('Статус: готово', 'status_ok.js', [2420, 200], lib=True)
code('Статус: ошибка', 'status_err.js', [1320, 300])
APPEND = {'columns': {'mappingMode': 'autoMapInputData', 'value': {}}}
sheet('Пишем ролики', 'append', 'Разбор: ролики', [2640, -200], APPEND)
sheet('Пишем каналы', 'append', 'Разбор: каналы', [2640, 0], APPEND)
sheet('Отмечаем ссылку', 'update', 'Каналы для разбора', [2640, 300],
      {'columns': {'mappingMode': 'autoMapInputData', 'value': {}, 'matchingColumns': ['Ссылка']}})

link('Раз в час', 'Читаем ссылки'); link('Запустить вручную', 'Читаем ссылки')
for a, b in [('Читаем ссылки', 'Что разбираем'), ('Что разбираем', 'YouTube: находим канал'), ('YouTube: находим канал', 'Канал найден?'),
             ('Канал найден?', 'Есть канал?'), ('YouTube: канал', 'Ролики: запрос списка'), ('Ролики: запрос списка', 'YouTube: список роликов'),
             ('YouTube: список роликов', 'Ролики: запрос данных'), ('Ролики: запрос данных', 'YouTube: ролики'),
             ('YouTube: ролики', 'Строки роликов'), ('YouTube: ролики', 'Сводка каналов'), ('YouTube: ролики', 'Статус: готово'),
             ('Строки роликов', 'Пишем ролики'), ('Сводка каналов', 'Пишем каналы'), ('Статус: готово', 'Отмечаем ссылку'),
             ('Статус: ошибка', 'Отмечаем ссылку')]:
    link(a, b)
link('Есть канал?', 'YouTube: канал', 0); link('Есть канал?', 'Статус: ошибка', 1)
w = {'name': '14_Разбор_каналов', 'nodes': nodes, 'connections': conns, 'active': False,
     'settings': {'executionOrder': 'v1', 'errorWorkflow': 'A6x2zK1xfuhc5I3E'}, 'pinData': {}}
P = os.path.join(REPO, 'workflows', '14_Разбор_каналов.json')
json.dump(w, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('nodes', len(nodes), '->', P)
