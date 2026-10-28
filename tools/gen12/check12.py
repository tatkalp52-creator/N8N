import json, re, subprocess, os, glob
HERE = os.path.dirname(os.path.abspath(__file__))
wf = json.load(open(os.path.join(HERE, '..', '..', 'workflows', '12_Этапы.json')))
import tempfile
TMP = os.path.join(tempfile.gettempdir(), '_c12.js')
names = {n['name'] for n in wf['nodes']}
bad = 0
# 1. syntax
for n in wf['nodes']:
    if n['type'] == 'n8n-nodes-base.code':
        open(TMP, 'w').write('async function __f(){\n' + n['parameters']['jsCode'] + '\n}')
        r = subprocess.run(['node', '--check', TMP], capture_output=True, text=True)
        if r.returncode: print('SYNTAX', n['name'], r.stderr[:500]); bad += 1
# 2. references
blob = json.dumps(wf, ensure_ascii=False)
for ref in set(re.findall(r"\$\('([^']+)'\)", blob)):
    if ref not in names: print('MISSING REF', ref); bad += 1
# 3. connections valid + fan-out
for src, c in wf['connections'].items():
    if src not in names: print('BAD SRC', src); bad += 1
    for i, outs in enumerate(c['main']):
        for o in outs:
            if o['node'] not in names: print('BAD DST', src, o['node']); bad += 1
        if len(outs) > 1: print('FAN-OUT', src, i, [o['node'] for o in outs]); bad += 1
# 4. orphans
targets = {o['node'] for c in wf['connections'].values() for outs in c['main'] for o in outs}
for n in wf['nodes']:
    if n['name'] not in targets and n['type'] not in ('n8n-nodes-base.telegramTrigger', 'n8n-nodes-base.executeWorkflowTrigger', 'n8n-nodes-base.webhook', 'n8n-nodes-base.stickyNote', 'n8n-nodes-base.scheduleTrigger'):
        print('ORPHAN', n['name']); bad += 1
# 5. credentials
for n in wf['nodes']:
    t = n['type']
    if t in ('n8n-nodes-base.telegram', 'n8n-nodes-base.telegramTrigger', 'n8n-nodes-base.googleSheets', 'n8n-nodes-base.googleDrive') and not n.get('credentials'):
        print('NO CREDS', n['name']); bad += 1
    if t == 'n8n-nodes-base.httpRequest' and 'openai' in json.dumps(n['parameters']) and not n.get('credentials'):
        print('NO CREDS', n['name']); bad += 1
# 6. СТОРОЖ: код не читает колонки с содержанием по имени и не знает ролей.
# Разрешены только служебные колонки (кнопки механики) и колонки листа выпусков (интерфейс 04_Video).
SERVICE = {'tmpl_Channel', 'tmpl_ImageModel', 'tmpl_ImageQuality', 'tmpl_LightModel', 'tmpl_LightEffort', 'tmpl_ImageSize', 'tmpl_ChannelVectorStoreId', 'tmpl_CleanMode', 'tmpl_CleanNotebook',
           'tmpl_CleanAlarmHours', 'tmpl_CleanRecheckTimes', 'tmpl_CleanBlend', 'tmpl_CleanBlendStems', 'tmpl_Clean'}
ROLE_WORDS = re.compile(r'Редактор|Писател|Художник|Технический|Pengui|Пингви', re.I)
for n in wf['nodes']:
    if n['type'] != 'n8n-nodes-base.code':
        continue
    src = re.sub(r'//.*', '', n['parameters']['jsCode'])
    for m in set(re.findall(r'tmpl_[A-Za-z]+', src)):
        if m not in SERVICE:
            print('GUARD: колонка по имени', n['name'], m); bad += 1
    body = src
    for m in set(ROLE_WORDS.findall(body)):
        print('GUARD: роль/канал в коде', n['name'], m); bad += 1
for n in wf['nodes']:
    if n['type'] == 'n8n-nodes-base.googleSheets':
        for k in (n['parameters'].get('columns', {}).get('value') or {}):
            if k.startswith('tmpl_') and k not in SERVICE or re.match(r'^\W', k):
                print('GUARD: запись в колонку по имени', n['name'], k); bad += 1
# Листы, где строк много (Этапы, Пункты, Эффекты), читаются целиком: без returnAllMatches узел отдаёт одну строку
# (05.10: так пропал пункт 9 — Аниматор остался без своего пункта)
for n in wf['nodes']:
    if n['type'] == 'n8n-nodes-base.googleSheets' and n['parameters'].get('sheetName', {}).get('value') in ('Этапы', 'Пункты', 'Эффекты'):
        if n['parameters'].get('options', {}).get('returnAllMatches') != 'returnAllMatches':
            print('GUARD: лист читается одной строкой', n['name']); bad += 1
# (24.10) ПРАВИЛО ПОВТОРОВ: повторять можно только безопасное (чтение, запись в строку по ключу, запросы без памяти).
# Отправка в Телеграм, добавление строки, запуск чистки — без повторов (повтор = дубль). (28.10) Запросы к OpenAI
# теперь без памяти у OpenAI — повтор безвреден; очередь /inbox повторяема (тот же запуск — тот же ответ).
for n in wf['nodes']:
    t = n['type']; op = n['parameters'].get('operation', '')
    body = str(n['parameters'].get('jsonBody', ''))
    unsafe = (t == 'n8n-nodes-base.telegram'
              or (t == 'n8n-nodes-base.googleSheets' and op in ('append', 'appendOrUpdate'))
              or (t == 'n8n-nodes-base.httpRequest' and ('requestBody' in body or '/clean_start' in n['parameters'].get('url', '') or '/gate' in n['parameters'].get('url', ''))
                  and n['name'] in ('Сервер: запусти чистку',) + tuple(x['name'] for x in wf['nodes'] if '/gate' in x['parameters'].get('url', ''))))
    if unsafe and n.get('retryOnFail'):
        print('GUARD: повтор там, где повтор = дубль', n['name']); bad += 1
# (24.10) НИ ОДНОГО ТУПИКА БЕЗ СЛОВА: у развилки (Switch) каждый выход куда-то ведёт, кроме перечисленных —
# там молчание задумано (повтор сообщения, «ничего не нужно», чистку уже обработали).
QUIET = {('Что пришло?', 2), ('Очередь: куда?', 3), ('Куда дальше?', 9), ('Куда после хода?', 5),
         ('Чистка: куда?', 2), ('Чистка: куда?', 3), ('Чистка: итог куда?', 4)}
for n in wf['nodes']:
    if n['type'] != 'n8n-nodes-base.switch':
        continue
    rules = len(n['parameters'].get('rules', {}).get('values', []))
    total = rules + (1 if n['parameters'].get('options', {}).get('fallbackOutput') == 'extra' else 0)
    outs = wf['connections'].get(n['name'], {}).get('main', [])
    for i in range(total):
        if (i >= len(outs) or not outs[i]) and (n['name'], i) not in QUIET:
            print('GUARD: развилка молча обрывается', n['name'], 'выход', i); bad += 1
print('problems:', bad)
