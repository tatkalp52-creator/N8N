import json, re, subprocess, os, glob
HERE = os.path.dirname(os.path.abspath(__file__))
wf = json.load(open(os.path.join(HERE, '..', '..', 'workflows', '12_Этапы.json')))
TMP = '/tmp/claude-0/-home-user-N8N/994c923d-89bd-532f-b598-03f041c8a163/scratchpad/_c12.js'
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
    if n['name'] not in targets and n['type'] not in ('n8n-nodes-base.telegramTrigger', 'n8n-nodes-base.executeWorkflowTrigger', 'n8n-nodes-base.webhook', 'n8n-nodes-base.stickyNote'):
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
SERVICE = {'tmpl_Channel', 'tmpl_Lupa', 'tmpl_ImageModel', 'tmpl_ChannelVectorStoreId', 'tmpl_CleanMode', 'tmpl_CleanNotebook',
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
print('problems:', bad)
