"""Собирает workflows/13_Сторож.json (14.10): страховка от падений.

1) «Ошибки»: n8n Error Trigger. Назначить этот workflow как Error workflow в настройках 04, 11, 12
   (Settings → Error workflow). Любое падение → сообщение в Телеграм простыми словами: где, что, что делать.
2) «Сторож»: раз в час спрашивает сборщик /health (жив ли, сколько места на диске, висят ли старые
   временные папки). Плохо → сообщение. Одно и то же — не чаще раза в 6 часов.

    python3 tools/gen13/gen13.py
"""
import json, os, uuid

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
OUT = os.path.join(ROOT, 'workflows', '13_Сторож.json')
W04 = json.load(open(os.path.join(ROOT, 'workflows', '04_Video.json'), encoding='utf-8'))
ASM = [n for n in W04['nodes'] if n['name'] == 'Собираем видео (POST)'][0]['parameters']['url'].rsplit('/', 1)[0]
TG = {'telegramApi': {'id': 'UW2MJh6bPIyVZeig', 'name': 'Telegram account 2'}}
OWNER = '285577543'

RAZBOR = r"""// Ошибка любого workflow → понятное сообщение: где упало, причина простыми словами, что делать.
const j = $json || {};
const ex = j.execution || {};
const err = ex.error || (j.trigger && j.trigger.error) || {};
const raw = String(err.message || err.description || '') + ' ' + String(err.description || '') + ' ' + String((err.cause && err.cause.message) || '');
const wf = (j.workflow && j.workflow.name) || 'workflow';
const node = ex.lastNodeExecuted || (err.node && err.node.name) || '';
const id = (raw.match(/\d{8}_\d{6}_[a-z0-9]+/i) || [])[0] || '';
const RULES = [
  [/No space left|ENOSPC/i, '💾 На сервере кончилось место на диске.', 'Почистить: старые /tmp/assemble_* и n8n binary_data (как 13.10). Сборщик новой версии чистит старые папки сам.'],
  [/insufficient_quota|exceeded your current quota|billing/i, '💳 OpenAI: закончились деньги или лимит.', 'platform.openai.com → Billing: пополнить баланс.'],
  [/invalid_api_key|Incorrect API key/i, '🔑 OpenAI не принял ключ.', 'n8n → Credentials → OpenAI: проверить ключ.'],
  [/rate.?limit|Too Many Requests|\b429\b/i, '⏳ Сервис ответил «слишком много запросов».', 'Подождать 10–15 минут и повторить.'],
  [/invalid_grant|token has been expired|expired or revoked|reconnect/i, '🔑 Истёк вход в Google или YouTube.', 'n8n → Credentials → YouTube / Google → Reconnect.'],
  [/uploadLimitExceeded|quotaExceeded|dailyLimitExceeded/i, '📺 YouTube: исчерпан дневной лимит.', 'Подождать до завтра (лимит сбрасывается раз в сутки) и повторить.'],
  [/PERMISSION_DENIED|forbidden|\b403\b|insufficient permission/i, '🔒 Google отказал в доступе.', 'Проверить, что у сервисного аккаунта есть доступ к таблице и папке Диска.'],
  [/\b401\b|unauthori[sz]ed/i, '🔑 Сервис не принял вход (401).', 'n8n → Credentials: переподключить тот сервис, на котором упало (см. шаг).'],
  [/kaggle/i, '🧹 Ошибка чистки в Kaggle.', 'kaggle.com → Code: открыть последний запуск; квота GPU — в профиле.'],
  [/ECONNREFUSED|ENOTFOUND|EAI_AGAIN|socket hang up|ECONNRESET/i, '🛠 Сервис не отвечает (сборщик или сеть).', 'Coolify → сборщик: открыть Terminal, проверить wget -qO- http://localhost:8100/health; если молчит — Restart.'],
  [/timeout|timed out|ETIMEDOUT|\b50[234]\b|Bad Gateway|Service Unavailable/i, '⌛ Сервис не успел ответить.', 'Чаще всего сборщик занят или завис: Coolify → сборщик → логи; если завис — Restart, потом «пересобери».'],
];
const hit = RULES.find(([re]) => re.test(raw));
const lines = ['⚠️ Сбой в «' + wf + '»' + (id ? ' · ' + id : '')];
if (node) lines.push('Шаг: ' + node);
lines.push(hit ? hit[1] : '❓ Незнакомая ошибка.');
lines.push(hit ? 'Что делать: ' + hit[2] : 'Пришли этот текст Клоду.');
lines.push('Текст ошибки: ' + raw.trim().slice(0, 300));
if (ex.url) lines.push(ex.url);
return [{ json: { chatId: '""" + OWNER + r"""', text: lines.join('\n') } }];"""

STOROZH = r"""// Сторож: сборщик жив? места хватает? Одно и то же — не чаще раза в 6 часов.
const h = $json || {};
const problems = [];
if (h.error || h.status !== 'ok') problems.push(['down', '🛠 Сборщик не ответил за 20 секунд. Если сейчас идёт сборка — это бывает, подожди. Если нет: Coolify → сборщик: Terminal → wget -qO- http://localhost:8100/health; если молчит — Restart.']);
if (typeof h.diskFreeGb === 'number' && h.diskFreeGb < 15) problems.push(['disk', '💾 На сервере осталось ' + h.diskFreeGb + ' ГБ (сборке нужно ~15). Почистить n8n binary_data и docker (как 13.10).']);
if (h.oldTempDirs > 0) problems.push(['tmp', '🧹 На сервере ' + h.oldTempDirs + ' старых временных папок сборки — видимо, сборка зависла. Сборщик удалит их сам перед следующей сборкой.']);
const sd = typeof $getWorkflowStaticData === 'function' ? $getWorkflowStaticData('global') : {};
const last = sd.alerted || {};
const now = Date.now();
const fresh = problems.filter(([k]) => !last[k] || now - last[k] > 6 * 3600 * 1000);
for (const [k] of fresh) last[k] = now;
for (const k of Object.keys(last)) if (!problems.some(([p]) => p === k)) delete last[k];   // починилось — забываем
sd.alerted = last;
if (!fresh.length) return [];
return [{ json: { chatId: '""" + OWNER + r"""', text: '👀 Сторож:\n' + fresh.map(([, t]) => t).join('\n') } }];"""


def node(name, typ, ver, pos, params, **kw):
    n = {'parameters': params, 'id': str(uuid.uuid4()), 'name': name, 'type': typ, 'typeVersion': ver, 'position': pos}
    n.update(kw)
    return n


def tg(name, pos):
    return node(name, 'n8n-nodes-base.telegram', 1.2, pos,
                {'chatId': '={{ $json.chatId }}', 'text': '={{ $json.text }}',
                 'additionalFields': {'appendAttribution': False, 'disable_web_page_preview': True}},
                credentials=TG, onError='continueRegularOutput')


nodes = [
    node('Ошибка в workflow', 'n8n-nodes-base.errorTrigger', 1, [0, 0], {}),
    node('Разбираем ошибку', 'n8n-nodes-base.code', 2, [240, 0], {'jsCode': RAZBOR}),
    tg('Сообщаем об ошибке', [480, 0]),
    node('Каждый час', 'n8n-nodes-base.scheduleTrigger', 1.2, [0, 260],
         {'rule': {'interval': [{'field': 'hours', 'hoursInterval': 1}]}}),
    node('Сборщик: здоровье', 'n8n-nodes-base.httpRequest', 4.2, [240, 260],
         {'url': ASM + '/health', 'options': {'timeout': 20000}}, onError='continueRegularOutput', alwaysOutputData=True),
    node('Сторож: итог', 'n8n-nodes-base.code', 2, [480, 260], {'jsCode': STOROZH}),
    tg('Сторож: сообщаем', [720, 260]),
    node('Заметка', 'n8n-nodes-base.stickyNote', 1, [0, -260], {'width': 720, 'height': 220, 'content':
         '## Сторож и ошибки\n1) Этот workflow назначить **Error workflow** в Settings у 04, 11 и 12 — тогда любое падение приходит в Телеграм простыми словами.\n'
         '2) Раз в час проверяет сборщик: жив ли, сколько места на диске, нет ли зависших временных папок.\n'
         'Если упадёт весь сервер, этот workflow тоже молчит — для этого внешний пинг (UptimeRobot) на /health.'}),
]
L = lambda b: {'node': b, 'type': 'main', 'index': 0}
conns = {
    'Ошибка в workflow': {'main': [[L('Разбираем ошибку')]]},
    'Разбираем ошибку': {'main': [[L('Сообщаем об ошибке')]]},
    'Каждый час': {'main': [[L('Сборщик: здоровье')]]},
    'Сборщик: здоровье': {'main': [[L('Сторож: итог')]]},
    'Сторож: итог': {'main': [[L('Сторож: сообщаем')]]},
}
wf = {'name': '13 Сторож', 'nodes': nodes, 'connections': conns, 'active': False,
      'settings': {'executionOrder': 'v1', 'saveDataSuccessExecution': 'none'}, 'pinData': {}}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)
print('ok:', OUT)
