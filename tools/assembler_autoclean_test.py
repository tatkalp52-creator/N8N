import sys, json, os, shutil
sys.path.insert(0, '/home/user/N8N/assembler'); import app as A
A.CLEAN_CODE_PATH = 'code.py'; A.CLEAN_CACHE_DIR = 'cache'; shutil.rmtree('cache', ignore_errors=True)
calls = []; state = {'st': 'COMPLETE'}
def fake(method, body, timeout=60):
    calls.append((method, body))
    if method == 'SaveKernel': return {'versionNumber': 9}
    if method == 'GetKernelSessionStatus': return {'status': state['st'], 'failureMessage': 'quota exceeded' if state['st']=='ERROR' else ''}
A.kaggle_call = fake
NB = 'https://www.kaggle.com/code/td1976/suno-clean'
d = {'projectId': 'P1', 'tracksUrl': 'https://drive.google.com/file/d/Z/view', 'cleanMode': 'knobs', 'cleanNotebook': NB, 'callbackUrl': 'https://n8n.x/webhook-waiting/77'}
state['st'] = 'RUNNING'; r = A.clean_start(d); assert r['busy'] and not r['ok']; print('ok busy')
state['st'] = 'COMPLETE'; r = A.clean_start(d); assert r['ok'], r; tag = r['tag']
src = json.loads([c for c in calls if c[0]=='SaveKernel'][0][1]['text'])['cells'][0]['source']
assert "CALLBACK_URL = 'https://n8n.x/webhook-waiting/77'" in src and f"RUN_TAG = '{tag}'" in src and "MODE = 'knobs'" in src
compile(src, 'nb', 'exec'); print('ok start', tag)
state['st'] = 'RUNNING'; assert A.clean_status({'cleanNotebook': NB, 'tag': tag})['state'] == 'running'; print('ok running')
state['st'] = 'ERROR'; r = A.clean_status({'cleanNotebook': NB, 'tag': tag}); assert r['state'] == 'error' and 'quota' in r['message']; print('ok error')
state['st'] = 'COMPLETE'
A.download_kaggle_output_file = lambda url, dest, ext='.zip', prefer=None, must_contain=None: open(dest, 'w').write('zip-' + must_contain) and dest
r = A.clean_status({'cleanNotebook': NB, 'tag': tag}); assert r == {'state': 'complete', 'cached': True}, r
assert os.path.exists(A.clean_cache_path(tag)); print('ok cached')
# сборка берёт из кэша, не из Kaggle
A.download_kaggle_output_file = lambda *a, **k: (_ for _ in ()).throw(AssertionError('не должен ходить в Kaggle'))
A.download_file(f'{NB}#run={tag}', 'got.zip'); assert open('got.zip').read() == 'zip-' + tag; print('ok build from cache')
# архив затёрт другим запуском
A.download_kaggle_output_file = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('нет архива с меткой'))
r = A.clean_status({'cleanNotebook': NB, 'tag': 'OTHER-1'}); assert r['state'] == 'error'; print('ok overwritten ->', r['message'][:45])
