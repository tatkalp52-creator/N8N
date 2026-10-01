import sys, json, time
sys.path.insert(0, '/home/user/N8N/assembler'); import app as A
A.CLEAN_CODE_PATH = 'code.py'; A.CLEAN_LOCK_PATH = 'lock'
calls = []
statuses = iter([Exception('сеть упала'), {'status': 'RUNNING'}, {'status': 'KERNEL_WORKER_STATUS_COMPLETE'}])
def fake(method, body, timeout=60):
    calls.append((method, body))
    if method == 'SaveKernel': return {'versionNumber': 7}
    x = next(statuses)
    if isinstance(x, Exception): raise x
    return x
A.kaggle_call = fake
A.time.sleep = lambda s: None
data = {'cleanNotebook': 'https://www.kaggle.com/code/td1976/suno-clean', 'cleanMode': 'knobs', 'cleanPollMinutes': '15'}
url, tag = A.run_kaggle_clean('https://drive.google.com/file/d/ABC/view', data, 'P1')
nb = json.loads(calls[0][1]['text'])['cells'][0]['source']
assert "TRACKS_LINK = 'https://drive.google.com/file/d/ABC/view'" in nb
assert "MODE = 'knobs'" in nb and f"RUN_TAG = '{tag}'" in nb
assert calls[0][1]['slug'] == 'td1976/suno-clean' and calls[0][1]['machineShape'] == 'NvidiaTeslaT4'
assert url == 'https://www.kaggle.com/code/td1976/suno-clean' and tag.startswith('P1-')
print('ok run', tag)
# ошибка в Kaggle
statuses = iter([{'status': 'ERROR', 'failureMessage': 'quota'}])
try: A.run_kaggle_clean('u', data, 'P1'); print('FAIL')
except RuntimeError as e: print('ok error:', e)
# пять сбоев подряд
statuses = iter([Exception('x')] * 5)
try: A.run_kaggle_clean('u', data, 'P1'); print('FAIL')
except RuntimeError as e: print('ok fails:', str(e)[:40])
# выбор архива по метке
files = [{'fileName': 'Bach (clean) [OTHER-1].zip', 'url': 'u1'}, {'fileName': f'Bach (clean) [{tag}].zip', 'url': 'u2'}]
class R:
    def __init__(s, j=None): s.j = j
    def raise_for_status(s): pass
    def json(s): return s.j
    def __enter__(s): return s
    def __exit__(s, *a): pass
    def iter_content(s, chunk_size): yield b'zip'
got = []
A.requests.post = lambda *a, **k: R({'files': files})
A.requests.get = lambda u, **k: got.append(u) or R()
A.kaggle_token = lambda: 'T'
A.download_file(f'https://www.kaggle.com/code/td1976/suno-clean#run={tag}', 'out.zip')
assert got == ['u2'], got; print('ok tag pick')
try: A.download_file('https://www.kaggle.com/code/td1976/suno-clean#run=NOPE', 'out.zip'); print('FAIL')
except RuntimeError as e: print('ok foreign:', str(e)[:50])
