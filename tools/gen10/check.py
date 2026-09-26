import json, re, subprocess, os, sys
wf = json.load(open('/home/user/N8N/workflows/10_Единый_редактор.json'))
names = {n['name'] for n in wf['nodes']}
bad = 0
# 1. syntax
for n in wf['nodes']:
    if n['type'] == 'n8n-nodes-base.code':
        src = 'async function __f(){\n' + n['parameters']['jsCode'] + '\n}'
        open('/tmp/claude-0/-home-user-N8N/994c923d-89bd-532f-b598-03f041c8a163/scratchpad/_c.js', 'w').write(src)
        r = subprocess.run(['node', '--check', '/tmp/claude-0/-home-user-N8N/994c923d-89bd-532f-b598-03f041c8a163/scratchpad/_c.js'], capture_output=True, text=True)
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
    if n['name'] not in targets and n['type'] not in ('n8n-nodes-base.telegramTrigger','n8n-nodes-base.stickyNote'): print('ORPHAN', n['name']); bad += 1
# 5. nodes w/ creds
for n in wf['nodes']:
    t = n['type']
    if t in ('n8n-nodes-base.telegram','n8n-nodes-base.telegramTrigger','n8n-nodes-base.googleSheets','n8n-nodes-base.googleDrive') and not n.get('credentials'):
        print('NO CREDS', n['name']); bad += 1
    if t == 'n8n-nodes-base.httpRequest' and 'openai' in json.dumps(n['parameters']) and not n.get('credentials'):
        print('NO CREDS', n['name']); bad += 1
    if t == 'n8n-nodes-base.httpRequest' and 'TELEGRAM_BOT_TOKEN' in json.dumps(n['parameters']):
        print('OLD BOT TOKEN', n['name']); bad += 1
print('problems:', bad)
