import json, re, uuid, copy, os

REPO = '/home/user/N8N'
JS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'js')
JS10 = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'gen10', 'js')
DOC = '1yEolX-8NV7NInu3OwCoxo2KSSNMny9dk-AVrpKdyNEs'
CRED_SHEETS = {'googleApi': {'id': '1uQkgKbOPhjKOB2l', 'name': 'Google Sheets account 2'}}
CRED_OPENAI = {'openAiApi': {'id': 'HvMLVgMnS8OU4ebj', 'name': 'OpenAi account'}}
# Тот же бот, что у старых воркфлоу (автор решила не заводить отдельный).
# Одновременно включён ТОЛЬКО один из двух: 00_Вход_и_диспетчер или этот.
CRED_TG = {'telegramApi': {'id': 'UW2MJh6bPIyVZeig', 'name': 'Telegram account 2'}}
VIDEO_WF_ID = 'Ajn6GuRmndcwqm16'

LIB = open(os.path.join(JS, 'lib12.js')).read()

nodes = []
conns = {}
names = set()

def uid():
    return str(uuid.uuid4())

# секретный адрес входа из календаря; тот же — в странице календаря (tools/patch11_plan.py)
CAL_HOOK = 'cal12-pDjXqAmp9bfKxK9RRByEPOci'

def add(node):
    assert node['name'] not in names, node['name']
    names.add(node['name'])
    node.setdefault('id', uid())
    nodes.append(node)
    return node['name']

def code(name, file, pos, lib=False):
    # движок — gen12/js; механика (треки, чистка, каналы…) — та же, что в gen10/js
    path = os.path.join(JS, file)
    if not os.path.exists(path):
        path = os.path.join(JS10, file)
    src = open(path).read()
    if lib:
        src = LIB + '\n' + src
    return add({'parameters': {'jsCode': src}, 'name': name, 'type': 'n8n-nodes-base.code', 'typeVersion': 2, 'position': pos})

def link(src, dst, out=0):
    c = conns.setdefault(src, {'main': []})['main']
    while len(c) <= out:
        c.append([])
    c[out].append({'node': dst, 'type': 'main', 'index': 0})

def chain(*ns):
    for a, b in zip(ns, ns[1:]):
        link(a, b)

def if_node(name, expr, pos):
    return add({
        'parameters': {'conditions': {
            'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'loose'},
            'conditions': [{'id': uid(), 'leftValue': '={{ ' + expr + ' }}', 'rightValue': True,
                            'operator': {'type': 'boolean', 'operation': 'true', 'singleValue': True}}],
            'combinator': 'and'}, 'options': {}},
        'name': name, 'type': 'n8n-nodes-base.if', 'typeVersion': 2, 'position': pos})

def switch_node(name, expr, values, pos):
    rules = []
    for v in values:
        rules.append({'conditions': {
            'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'loose'},
            'conditions': [{'leftValue': '={{ ' + expr + ' }}', 'rightValue': v,
                            'operator': {'type': 'string', 'operation': 'equals'}}],
            'combinator': 'and'}})
    return add({'parameters': {'rules': {'values': rules}, 'options': {'fallbackOutput': 'extra'}},
                'name': name, 'type': 'n8n-nodes-base.switch', 'typeVersion': 3, 'position': pos})

def sheets_read(name, sheet_expr, filters, pos, always=True):
    n = {'parameters': {'authentication': 'serviceAccount',
                        'documentId': {'__rl': True, 'value': DOC, 'mode': 'id'},
                        'sheetName': {'__rl': True, 'value': sheet_expr, 'mode': 'name'},
                        'filtersUI': {'values': [{'lookupColumn': c, 'lookupValue': v} for c, v in filters]},
                        'options': {}},
         'name': name, 'type': 'n8n-nodes-base.googleSheets', 'typeVersion': 4, 'position': pos,
         'credentials': copy.deepcopy(CRED_SHEETS)}
    if always:
        n['alwaysOutputData'] = True
    return add(n)

def sheets_update(name, sheet_expr, values, pos, match='sys_ProjectID'):
    return add({'parameters': {'authentication': 'serviceAccount', 'operation': 'update',
                               'documentId': {'__rl': True, 'value': DOC, 'mode': 'id'},
                               'sheetName': {'__rl': True, 'value': sheet_expr, 'mode': 'name'},
                               'columns': {'mappingMode': 'defineBelow', 'matchingColumns': [match], 'value': values},
                               'options': {}},
                'name': name, 'type': 'n8n-nodes-base.googleSheets', 'typeVersion': 4, 'position': pos,
                'credentials': copy.deepcopy(CRED_SHEETS)})

def tg_send(name, chat_expr, text_expr, pos, button=None):
    p = {'resource': 'message', 'operation': 'sendMessage', 'chatId': chat_expr, 'text': text_expr,
         'additionalFields': {'appendAttribution': False, 'parse_mode': 'HTML'}}
    if button:
        btn_text, cb_expr = button
        p['replyMarkup'] = 'inlineKeyboard'
        p['inlineKeyboard'] = {'rows': [{'row': {'buttons': [
            {'text': btn_text, 'additionalFields': {'callback_data': cb_expr}}]}}]}
    return add({'parameters': p, 'name': name, 'type': 'n8n-nodes-base.telegram', 'typeVersion': 1.2,
                'position': pos, 'webhookId': uid(), 'credentials': copy.deepcopy(CRED_TG)})

def tg_photo(name, chat_expr, url_expr, caption_expr, btn_text_expr, cb_expr, pos):
    p = {'resource': 'message', 'operation': 'sendPhoto', 'chatId': chat_expr, 'file': url_expr,
         'replyMarkup': 'inlineKeyboard',
         'inlineKeyboard': {'rows': [{'row': {'buttons': [
             {'text': btn_text_expr, 'additionalFields': {'callback_data': cb_expr}}]}}]},
         'additionalFields': {'caption': caption_expr}}
    return add({'parameters': p, 'name': name, 'type': 'n8n-nodes-base.telegram', 'typeVersion': 1.2,
                'position': pos, 'webhookId': uid(), 'credentials': copy.deepcopy(CRED_TG),
                # Ссылка на свежий файл Диска открывается не сразу — Телеграм может не скачать её с первого раза
                'retryOnFail': True, 'maxTries': 3, 'waitBetweenTries': 5000})

def tg_answer(name, pos):
    return add({'parameters': {'resource': 'callback', 'operation': 'answerQuery', 'queryId': "={{ $('Разбираем входящее').first().json.callbackQueryId }}",
                               'additionalFields': {}},
                'name': name, 'type': 'n8n-nodes-base.telegram', 'typeVersion': 1.2, 'position': pos,
                'webhookId': uid(), 'credentials': copy.deepcopy(CRED_TG), 'onError': 'continueRegularOutput'})

def openai_http(name, body_expr, url, pos):
    return add({'parameters': {'method': 'POST', 'url': url, 'authentication': 'predefinedCredentialType',
                               'nodeCredentialType': 'openAiApi', 'sendBody': True, 'specifyBody': 'json',
                               'jsonBody': body_expr, 'options': {}},
                'name': name, 'type': 'n8n-nodes-base.httpRequest', 'typeVersion': 4.2, 'position': pos,
                'credentials': copy.deepcopy(CRED_OPENAI)})

def sheets_automap(name, sheet_expr, pos, match):
    """Запись с колонками из входных данных: имена колонок решает таблица, а не код."""
    return add({'parameters': {'authentication': 'serviceAccount', 'operation': 'update',
                               'documentId': {'__rl': True, 'value': DOC, 'mode': 'id'},
                               'sheetName': {'__rl': True, 'value': sheet_expr, 'mode': 'name'},
                               'columns': {'mappingMode': 'autoMapInputData', 'value': {}, 'matchingColumns': [match], 'schema': []},
                               'options': {}},
                'name': name, 'type': 'n8n-nodes-base.googleSheets', 'typeVersion': 4, 'position': pos,
                'credentials': copy.deepcopy(CRED_SHEETS)})

_w04e = json.load(open(os.path.join(REPO, 'workflows/04_Video.json')))
ASM = [n for n in _w04e['nodes'] if n['name'] == 'Собираем видео (POST)'][0]['parameters']['url'].rsplit('/', 1)[0]

CTX = "$('Контекст проекта').first().json"
R = "$('Итог хода').first().json"
SHEET = '={{ ' + CTX + '.sheetName }}'

# ═════════════ ВХОД ═════════════
X = 0; Y = 0
add({'parameters': {'updates': ['message', 'callback_query'], 'additionalFields': {}},
     'name': 'Telegram Trigger', 'type': 'n8n-nodes-base.telegramTrigger', 'typeVersion': 1.1,
     'position': [X, Y], 'webhookId': uid(), 'credentials': copy.deepcopy(CRED_TG)})
add({'parameters': {'conditions': {'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'loose'},
     'conditions': [{'leftValue': "={{ String($json.message?.from?.id || $json.callback_query?.from?.id || '') }}",
                     'rightValue': '285577543', 'operator': {'type': 'string', 'operation': 'equals'}}],
     'combinator': 'and'}, 'options': {}},
     'name': 'Это владелец бота?', 'type': 'n8n-nodes-base.if', 'typeVersion': 2, 'position': [X + 220, Y]})
# Канвас вызывает сам себя, когда выпуск переходит к следующему этапу
add({'parameters': {}, 'name': 'Вызов изнутри', 'type': 'n8n-nodes-base.executeWorkflowTrigger', 'typeVersion': 1,
     'position': [X, Y + 200]})
code('Разбираем входящее', 'razbor.js', [X + 440, Y])
switch_node('Что пришло?', '$json.kind', ['newStart', 'channelPick', 'unknown', 'dupButton'], [X + 660, Y])
chain('Telegram Trigger', 'Это владелец бота?', 'Разбираем входящее', 'Что пришло?')
link('Вызов изнутри', 'Разбираем входящее')
# Из календаря (страница контент-плана): «Старт» выпуска и ссылка на треки — тем же путём, что из Телеграма
add({'parameters': {'httpMethod': 'POST', 'path': CAL_HOOK, 'options': {}}, 'name': 'Из календаря',
     'type': 'n8n-nodes-base.webhook', 'typeVersion': 2, 'position': [X, Y + 400], 'webhookId': uid()})
link('Из календаря', 'Разбираем входящее')

sheets_read('Читаем каталог каналов', 'Catalog', [], [X + 900, Y - 700], always=False)
code('Кнопка на каждый канал', 'kanaly.js', [X + 1120, Y - 700], lib=True)
# одно сообщение со всеми кнопками каналов: у узла Telegram число кнопок фиксировано, поэтому — прямой вызов API
add({'parameters': {'method': 'POST', 'url': '=https://api.telegram.org/bot{{ $env.TELEGRAM_BOT_TOKEN }}/sendMessage',
                    'sendBody': True, 'specifyBody': 'json', 'jsonBody': '={{ JSON.stringify($json.body) }}', 'options': {}},
     'name': 'Предлагаем каналы', 'type': 'n8n-nodes-base.httpRequest', 'typeVersion': 4.2, 'position': [X + 1340, Y - 700]})
link('Что пришло?', 'Читаем каталог каналов', 0)
chain('Читаем каталог каналов', 'Кнопка на каждый канал', 'Предлагаем каналы')

tg_answer('Отвечаем на кнопку канала', [X + 900, Y - 450])
nodes[-1]['parameters']['additionalFields'] = {'text': '✅ Принято'}
# (22.10) второе нажатие той же кнопки (не видно, нажалось ли) — только ответ «уже принято», без второго действия
tg_answer('Отвечаем: уже нажато', [X + 900, Y - 650])
nodes[-1]['parameters']['additionalFields'] = {'text': '✅ Уже принято — делаю'}
link('Что пришло?', 'Отвечаем: уже нажато', 3)
sheets_read('Ищем канал в каталоге', 'Catalog', [('Channel', "={{ $('Разбираем входящее').first().json.channelKey }}")], [X + 1120, Y - 450], always=False)
code('Генерируем ProjectID', 'projectid.js', [X + 1340, Y - 450])
add({'parameters': {'authentication': 'serviceAccount', 'operation': 'append',
                    'documentId': {'__rl': True, 'value': DOC, 'mode': 'id'},
                    'sheetName': {'__rl': True, 'value': '={{ $json.sheetName }}', 'mode': 'name'},
                    'columns': {'mappingMode': 'defineBelow', 'value': {
                        'sys_ProjectID': '={{ $json.projectId }}', 'sys_Status': 'Картинка в работе'}},
                    'options': {}},
     'name': 'Создаём проект', 'type': 'n8n-nodes-base.googleSheets', 'typeVersion': 4,
     'position': [X + 1560, Y - 450], 'credentials': copy.deepcopy(CRED_SHEETS)})
tg_send('Проект создан', "={{ $('Генерируем ProjectID').first().json.chatId }}",
        "={{ $('Генерируем ProjectID').first().json.createdText }}", [X + 2220, Y - 450])
if_node('Из календаря?', "!!$('Генерируем ProjectID').first().json.calId", [X + 1780, Y - 450])
sheets_update('Привязываем к календарю', 'Календарь', {
    'id': "={{ $('Генерируем ProjectID').first().json.calId }}",
    'project': "={{ $('Генерируем ProjectID').first().json.projectId }}", 'status': 'В работе'}, [X + 2000, Y - 550], match='id')
nodes[-1]['onError'] = 'continueRegularOutput'
link('Что пришло?', 'Отвечаем на кнопку канала', 1)
chain('Отвечаем на кнопку канала', 'Ищем канал в каталоге', 'Генерируем ProjectID', 'Создаём проект', 'Из календаря?')
link('Из календаря?', 'Привязываем к календарю', 0)
link('Привязываем к календарю', 'Проект создан')
link('Из календаря?', 'Проект создан', 1)

if_node('Это кнопка?', "!!$('Разбираем входящее').first().json.callbackQueryId", [X + 900, Y])
tg_answer('Отвечаем на кнопку', [X + 1120, Y - 150])
nodes[-1]['parameters']['additionalFields'] = {'text': "={{ (function(){ const j = $('Разбираем входящее').first().json; return j.kind === 'imgApprove' ? '✅ Принято, вариант ' + j.variantNumber : j.kind === 'finalApprove' ? '✅ Принято — записываю' : j.kind === 'build' ? '🎬 Принято — собираю' : '✅ Принято'; })() }}"}
sheets_read('Находим лист канала', 'Catalog', [('Channel', "={{ $('Разбираем входящее').first().json.channelKey }}")], [X + 1340, Y])
sheets_read('Читаем строку проекта', '={{ $json.SheetName }}', [('sys_ProjectID', "={{ $('Разбираем входящее').first().json.projectId }}")], [X + 1560, Y])
sheets_read('Читаем шаблоны канала', 'Templates', [('tmpl_Channel', "={{ $('Разбираем входящее').first().json.channelKey }}")], [X + 1780, Y])
# Сценарий канала: кто работает и в каком порядке; какие пункты и куда они пишутся
sheets_read('Читаем этапы', 'Этапы', [('Канал', "={{ $('Разбираем входящее').first().json.channelKey }}")], [X + 2000, Y])
nodes[-1]['executeOnce'] = True
nodes[-1]['parameters']['options'] = {'returnAllMatches': 'returnAllMatches'}  # по умолчанию узел отдаёт только первую строку
sheets_read('Читаем пункты', 'Пункты', [('Канал', "={{ $('Разбираем входящее').first().json.channelKey }}")], [X + 2220, Y])
nodes[-1]['executeOnce'] = True
nodes[-1]['parameters']['options'] = {'returnAllMatches': 'returnAllMatches'}
sheets_read('Читаем эффекты', 'Эффекты', [], [X + 2220, Y + 200])   # каталог эффектов: весь лист, столбцы каналов
nodes[-1]['executeOnce'] = True
nodes[-1]['onError'] = 'continueRegularOutput'
nodes[-1]['parameters'].pop('filtersUI')           # без фильтра — весь лист
nodes[-1]['parameters']['options'] = {'returnAllMatches': 'returnAllMatches'}
sheets_read('Читаем календарь (метка)', 'Календарь', [('project', "={{ $('Разбираем входящее').first().json.projectId }}")], [X + 2330, Y + 200])
nodes[-1]['executeOnce'] = True
nodes[-1]['onError'] = 'continueRegularOutput'
code('Контекст проекта', 'kontekst.js', [X + 2440, Y], lib=True)
if_node('Проект найден?', '$json.found', [X + 2660, Y])
tg_send('Проект не найден', '={{ $json.chatId }}', '=Не нашла проект {{ $json.projectId }} в таблице канала — ничего не делаю.', [X + 2880, Y + 200])
switch_node('Куда дальше?', '$json.kind', ['message', 'imgApprove', 'finalApprove', 'tracks', 'oldButton', 'build', 'cleanStatus', 'stageStart'], [X + 2880, Y])
tg_send('Старая кнопка', '={{ $json.chatId }}', '=Эта кнопка из старой схемы — она ничего не делает.\n\nID: {{ $json.projectId }}', [X + 3140, Y + 1500])
link('Что пришло?', 'Это кнопка?', 4)
link('Это кнопка?', 'Отвечаем на кнопку', 0)
link('Это кнопка?', 'Находим лист канала', 1)
chain('Отвечаем на кнопку', 'Находим лист канала', 'Читаем строку проекта', 'Читаем шаблоны канала', 'Читаем этапы', 'Читаем пункты', 'Читаем эффекты', 'Читаем календарь (метка)', 'Контекст проекта', 'Проект найден?')
link('Проект найден?', 'Куда дальше?', 0)
link('Проект найден?', 'Проект не найден', 1)
link('Куда дальше?', 'Старая кнопка', 4)

# ═════════════ ДВИЖОК ЭТАПОВ ═════════════
EX = X + 3140; EY = Y - 1400
code('Кто отвечает', 'kto.js', [EX, EY], lib=True)
if_node('Это этап-модель?', "$('Кто отвечает').first().json.mode === 'model'", [EX + 220, EY])
if_node('Нужен разговор?', "$('Кто отвечает').first().json.needConv", [EX + 440, EY - 180])
openai_http('OpenAI: создаём разговор', "={{ JSON.stringify({ metadata: { project: " + CTX + ".projectId } }) }}",
            'https://api.openai.com/v1/conversations', [EX + 660, EY - 60])
if_node('Есть фото?', "!!$('Кто отвечает').first().json.photo", [EX + 880, EY - 180])
add({'parameters': {'resource': 'file', 'operation': 'get', 'fileId': "={{ (function(){ const p = $('Кто отвечает').first().json.photo; return p[p.length - 1].file_id; })() }}",
                    'download': True, 'additionalFields': {}},
     'name': 'Скачиваем фото', 'type': 'n8n-nodes-base.telegram', 'typeVersion': 1.2,
     'position': [EX + 1100, EY - 60], 'webhookId': uid(), 'credentials': copy.deepcopy(CRED_TG)})
code('Фото в base64', 'foto.js', [EX + 1320, EY - 60])
if_node('Нужна сетка?', "$('Кто отвечает').first().json.needGrid", [EX + 1430, EY - 300])
add({'parameters': {'method': 'POST', 'url': ASM + '/fx_grid', 'sendBody': True, 'specifyBody': 'json',
                    'jsonBody': "={{ JSON.stringify({ imageUrl: " + CTX + ".row.ai_ApprovedImageUrl }) }}", 'options': {'timeout': 120000}},
     'name': 'Сервер: сетка', 'type': 'n8n-nodes-base.httpRequest', 'typeVersion': 4.2, 'position': [EX + 1430, EY - 460],
     'onError': 'continueRegularOutput'})
code('Готовим запрос этапу', 'zapros.js', [EX + 1540, EY - 180], lib=True)
openai_http('OpenAI: этап', '={{ JSON.stringify($json.requestBody) }}', 'https://api.openai.com/v1/responses', [EX + 1760, EY - 180])
nodes[-1]['parameters']['options'] = {'timeout': 600000}
nodes[-1]['onError'] = 'continueRegularOutput'
code('Разбираем ответ этапа', 'parse.js', [EX + 1980, EY - 180], lib=True)
# ── ЛУПА: точки оживления уточняются по увеличенным кусочкам (сборщик режет, этап читает) ──
code('Лупа: план', 'lupa_plan.js', [EX + 1980, EY - 520], lib=True)
if_node('Нужна лупа?', "$('Лупа: план').first().json.need", [EX + 2090, EY - 680])
add({'parameters': {'method': 'POST', 'url': ASM + '/fx_zoom', 'sendBody': True, 'specifyBody': 'json',
                    'jsonBody': "={{ JSON.stringify({ imageUrl: $('Лупа: план').first().json.imageUrl, fx_Effects: $('Лупа: план').first().json.fx }) }}",
                    'options': {'timeout': 120000}},
     'name': 'Сервер: лупа', 'type': 'n8n-nodes-base.httpRequest', 'typeVersion': 4.2, 'position': [EX + 2200, EY - 840],
     'onError': 'continueRegularOutput'})
if_node('Есть точки?', "(($('Сервер: лупа').first().json || {}).points || []).length > 0", [EX + 2310, EY - 1000])
code('Готовим уточнение', 'lupa_zapros.js', [EX + 2420, EY - 1160], lib=True)
openai_http('OpenAI: уточнение', '={{ JSON.stringify($json.requestBody) }}', 'https://api.openai.com/v1/responses', [EX + 2530, EY - 1320])
nodes[-1]['parameters']['options'] = {'timeout': 300000}
nodes[-1]['onError'] = 'continueRegularOutput'
code('Лупа: итог', 'lupa_itog.js', [EX + 2640, EY - 1160], lib=True)
if_node('Поручение?', "$('Разбираем ответ этапа').first().json.action === 'delegate'", [EX + 2200, EY - 180])
code('Готовим поручение', 'podchinennyy.js', [EX + 2420, EY - 360], lib=True)
openai_http('OpenAI: поручение', '={{ JSON.stringify($json.requestBody) }}', 'https://api.openai.com/v1/responses', [EX + 2640, EY - 360])
nodes[-1]['parameters']['options'] = {'timeout': 600000}
nodes[-1]['onError'] = 'continueRegularOutput'
code('Итог хода: черновик', 'itog.js', [EX + 2640, EY + 200], lib=True)
# (11.10) перевод для автора — отдельным переводчиком по готовому тексту пункта; затем итог хода ещё раз, уже с ним
code('Перевод для автора: что', 'perevod_avtoru.js', [EX + 2750, EY + 380], lib=True)
if_node('Нужен перевод?', "$('Перевод для автора: что').first().json.need", [EX + 2750, EY + 200])
openai_http('OpenAI: перевод для автора', "={{ JSON.stringify($('Перевод для автора: что').first().json.requestBody) }}", 'https://api.openai.com/v1/responses', [EX + 2860, EY + 380])
nodes[-1]['parameters']['options'] = {'timeout': 180000}
nodes[-1]['onError'] = 'continueRegularOutput'
code('Итог хода', 'itog.js', [EX + 2860, EY], lib=True)
sheets_update('Сохраняем ход', '={{ ' + R + '.sheetName }}', {
    'sys_ProjectID': '={{ ' + R + '.projectId }}',
    'sys_EditorState': '={{ ' + R + '.editorState }}',
    'sys_Status': '={{ ' + R + '.statusAfter }}',
    'ai_UserBrief': '={{ ' + R + '.userBrief }}',
    'ai_ApprovedImageUrl': "={{ " + R + ".clearApproved ? '' : (" + R + ".approvedUrl || " + CTX + ".row.ai_ApprovedImageUrl || '') }}",
}, [EX + 3080, EY])
if_node('Согласованное есть?', '!!' + R + '.agreedFields', [EX + 3190, EY - 300])
code('Согласованное по колонкам', 'soglasovannoe.js', [EX + 3300, EY - 460])
sheets_automap('Записываем согласованное', SHEET, [EX + 3520, EY - 460], 'sys_ProjectID')
if_node('Есть памятка?', '!!' + R + '.note', [EX + 3300, EY])
code('Памятка', 'pamyatka.js', [EX + 3520, EY + 160])
sheets_automap('Сохраняем памятку', 'Templates', [EX + 3740, EY + 160], 'tmpl_Channel')
code('Сообщения хода', 'soobshcheniya.js', [EX + 3960, EY])
if_node('Есть что сказать?', '!$json.skip', [EX + 4180, EY])
tg_send('Отправляем ответ', '={{ $json.chatId }}', '={{ $json.text }}', [EX + 4400, EY - 120])
code('Что дальше?', 'chto_dalshe.js', [EX + 4620, EY])
if_node('Нужно превью?', "$('Что дальше?').first().json.preview", [EX + 4730, EY + 200])
# превью — видео (05.10): та же петля эффектов, что в ролике; картинка не показывала движения
add({'parameters': {'method': 'POST', 'url': ASM + '/fx_preview_video', 'sendBody': True, 'specifyBody': 'json',
                    'jsonBody': "={{ JSON.stringify(" + R + ".previewBody) }}",
                    'options': {'timeout': 300000, 'response': {'response': {'responseFormat': 'file', 'outputPropertyName': 'data'}}}},
     'name': 'Сервер: превью', 'type': 'n8n-nodes-base.httpRequest', 'typeVersion': 4.2, 'position': [EX + 4730, EY + 380],
     'onError': 'continueRegularOutput'})
add({'parameters': {'resource': 'message', 'operation': 'sendVideo', 'chatId': '={{ ' + R + '.chatId }}',
                    'binaryData': True, 'binaryPropertyName': 'data',
                    'additionalFields': {'caption': '={{ ' + R + '.previewCaption }}'}},
     'name': 'Отправляем превью', 'type': 'n8n-nodes-base.telegram', 'typeVersion': 1.2, 'position': [EX + 4950, EY + 380],
     'webhookId': uid(), 'credentials': copy.deepcopy(CRED_TG), 'onError': 'continueRegularOutput'})
switch_node('Куда после хода?', "$('Что дальше?').first().json.next", ['draw', 'edit', 'next', 'summary', 'package'], [EX + 4840, EY])

link('Куда дальше?', 'Кто отвечает', 0)
link('Куда дальше?', 'Кто отвечает', 7)
link('Кто отвечает', 'Это этап-модель?')
link('Это этап-модель?', 'Нужен разговор?', 0)
link('Это этап-модель?', 'Итог хода: черновик', 1)
link('Нужен разговор?', 'OpenAI: создаём разговор', 0)
link('Нужен разговор?', 'Есть фото?', 1)
link('OpenAI: создаём разговор', 'Есть фото?')
link('Есть фото?', 'Скачиваем фото', 0)
link('Есть фото?', 'Нужна сетка?', 1)
if_node('Нужна разметка?', "$('Кто отвечает').first().json.needMarks", [EX + 1320, EY - 300])
add({'parameters': {'method': 'POST', 'url': ASM + '/fx_marks', 'sendBody': True, 'specifyBody': 'json',
                    'jsonBody': "={{ JSON.stringify({ imageUrl: " + CTX + ".row.ai_ApprovedImageUrl, markedDataUrl: $('Фото в base64').first().json.userImageUrl }) }}",
                    'options': {'timeout': 120000}},
     'name': 'Сервер: разметка', 'type': 'n8n-nodes-base.httpRequest', 'typeVersion': 4.2, 'position': [EX + 1320, EY - 460],
     'onError': 'continueRegularOutput'})
chain('Скачиваем фото', 'Фото в base64', 'Нужна разметка?')
link('Нужна разметка?', 'Сервер: разметка', 0)
link('Нужна разметка?', 'Нужна сетка?', 1)
link('Сервер: разметка', 'Нужна сетка?')
link('Нужна сетка?', 'Сервер: сетка', 0)
link('Нужна сетка?', 'Готовим запрос этапу', 1)
link('Сервер: сетка', 'Готовим запрос этапу')
chain('Готовим запрос этапу', 'OpenAI: этап', 'Разбираем ответ этапа', 'Лупа: план', 'Нужна лупа?')
link('Нужна лупа?', 'Сервер: лупа', 0)
link('Нужна лупа?', 'Поручение?', 1)
chain('Сервер: лупа', 'Есть точки?')
link('Есть точки?', 'Готовим уточнение', 0)
link('Есть точки?', 'Поручение?', 1)
chain('Готовим уточнение', 'OpenAI: уточнение', 'Лупа: итог', 'Поручение?')
link('Поручение?', 'Готовим поручение', 0)
link('Поручение?', 'Итог хода: черновик', 1)
chain('Готовим поручение', 'OpenAI: поручение', 'Итог хода: черновик')
chain('Итог хода: черновик', 'Перевод для автора: что', 'Нужен перевод?', 'OpenAI: перевод для автора', 'Итог хода')
link('Нужен перевод?', 'Итог хода', 1)
chain('Итог хода', 'Сохраняем ход', 'Согласованное есть?')
link('Согласованное есть?', 'Согласованное по колонкам', 0)
link('Согласованное есть?', 'Есть памятка?', 1)
chain('Согласованное по колонкам', 'Записываем согласованное', 'Есть памятка?')
link('Есть памятка?', 'Памятка', 0)
link('Есть памятка?', 'Сообщения хода', 1)
chain('Памятка', 'Сохраняем памятку', 'Сообщения хода')
link('Сообщения хода', 'Есть что сказать?')
link('Есть что сказать?', 'Отправляем ответ', 0)
link('Есть что сказать?', 'Что дальше?', 1)
link('Отправляем ответ', 'Что дальше?')
link('Что дальше?', 'Нужно превью?')
link('Нужно превью?', 'Сервер: превью', 0)
link('Нужно превью?', 'Куда после хода?', 1)
chain('Сервер: превью', 'Отправляем превью', 'Куда после хода?')

# ── переход к следующему этапу: канвас вызывает сам себя ──
code('Передаём дальше', 'dalshe.js', [EX + 5100, EY + 300])
# workflowId в версии 1.1 — «указатель ресурса» (объект), а не строка: строку n8n не видит
add({'parameters': {'source': 'database', 'workflowId': {'__rl': True, 'value': '={{ $workflow.id }}', 'mode': 'id'},
                    'options': {'waitForSubWorkflow': False}},
     'name': 'Следующий этап', 'type': 'n8n-nodes-base.executeWorkflow', 'typeVersion': 1.1, 'position': [EX + 5320, EY + 300]})
link('Куда после хода?', 'Передаём дальше', 2)
link('Передаём дальше', 'Следующий этап')
link('Проект создан', 'Передаём дальше')

# ── сводка на ✅ ──
code('Сводка', 'svodka.js', [EX + 5100, EY + 600], lib=True)
tg_send('Отправляем сводку', '={{ $json.chatId }}', '={{ $json.text }}', [EX + 5320, EY + 600])
code('Одно сообщение с кнопкой', 'svodka_knopka.js', [EX + 5540, EY + 600], lib=True)
tg_send('Кнопка финального согласования', '={{ $json.chatId }}', '={{ $json.text }}', [EX + 5760, EY + 600],
        button=('✅ Согласовано', '={{ $json.callbackData }}'))
link('Куда после хода?', 'Сводка', 3)
chain('Сводка', 'Отправляем сводку', 'Одно сообщение с кнопкой', 'Кнопка финального согласования')

# ═════════════ РИСОВАНИЕ (узлы перенесены из 01_Художник) ═════════════
art = json.load(open(os.path.join(REPO, 'workflows/01_Художник.json')))
art_nodes = {n['name']: n for n in art['nodes']}

def retarget(n):
    s = json.dumps(n, ensure_ascii=False).replace("$('Парсим ответ редактора')", "$('Итог хода')")
    return json.loads(s)

def take(name, pos):
    n = retarget(copy.deepcopy(art_nodes[name]))
    n['id'] = uid()
    n['position'] = pos
    n.pop('webhookId', None)
    return add(n)

nodes_by = lambda nm: [n for n in nodes if n['name'] == nm][0]
# Максимум картинок в одном запросе художнику (основа правки считается): для каждого числа 1…MAX свой узел запроса,
# поэтому цифра прямо влияет на размер канваса. Меняется здесь и в lib12.js (artRefs) вместе.
MAX_IMAGES = 8
AX = EX + 5100

def image_switch(name, counts):
    sw = nodes_by(name)
    tmpl_rule = sw['parameters']['rules']['values'][0]
    rules = []
    for c in counts[:-1]:
        r = copy.deepcopy(tmpl_rule)
        r['conditions']['conditions'][0]['rightValue'] = c
        rules.append(r)
    sw['parameters']['rules']['values'] = rules
    sw['parameters']['options'] = {'fallbackOutput': 'extra'}

def image_call(template, name, count, prompt, pos):
    n = retarget(copy.deepcopy(art_nodes[template]))
    n['id'] = uid(); n['name'] = name; n['position'] = pos
    bp = [x for x in n['parameters']['bodyParameters']['parameters'] if x.get('parameterType') != 'formBinaryData']
    for x in bp:
        if x.get('name') == 'model':
            x['value'] = "={{ $('Итог хода').first().json.imageModel }}"
        if x.get('name') == 'prompt':
            x['value'] = prompt
    if not any(x.get('name') == 'quality' for x in bp):
        bp.insert(3, {'name': 'quality', 'value': 'high'})
    bp += [{'parameterType': 'formBinaryData', 'name': 'image[]', 'inputDataFieldName': f'image_{k}'} for k in range(count)]
    n['parameters']['bodyParameters']['parameters'] = bp
    return add(n)

DY = EY - 1200
B = ['Готовим список: style guide + референсы', 'Скачиваем референс (B)', 'Собираем референсы в один item (B)', 'Сколько картинок? (B)']
for i, nm in enumerate(B):
    take(nm, [AX + 440 + i * 220, DY])
nodes_by(B[0])['parameters']['jsCode'] = open(os.path.join(JS, 'spisok_b.js')).read()
B_COUNTS = list(range(1, MAX_IMAGES + 1))
BG = [f'gpt-image-2: рисуем (B, {c} img)' for c in B_COUNTS]
for i, (nm, c) in enumerate(zip(BG, B_COUNTS)):
    image_call('gpt-image-2: рисуем (B)', nm, c,
               "={{ $('Итог хода').first().json.drawRoles }}{{ $json.dallePrompt }}",
               [AX + 1320, DY - 1400 + i * 160])
image_switch('Сколько картинок? (B)', B_COUNTS)
B2 = ['Извлекаем картинку (B)', 'Загружаем на Диск (B)', 'Открываем доступ (B)', 'Собираем ссылку (B)', 'Сохраняем картинку и промпт (B)']
for i, nm in enumerate(B2):
    take(nm, [AX + 1540 + i * 220, DY])
tg_photo('Отправляем картинку (B)', "={{ $('Собираем ссылку (B)').first().json.chatId }}",
         "={{ $('Собираем ссылку (B)').first().json.ai_ImageUrl }}",
         "={{ $('Итог хода').first().json.stageIcon }} {{ $('Итог хода').first().json.stageName }}: Вариант {{ $('Собираем ссылку (B)').first().json.variantNumber }}\nID: {{ $('Собираем ссылку (B)').first().json.sys_ProjectID }}",
         "=✅ Согласовать вариант {{ $('Собираем ссылку (B)').first().json.variantNumber }}",
         "=img|{{ $('Собираем ссылку (B)').first().json.sys_ProjectID }}|{{ $('Собираем ссылку (B)').first().json.variantNumber }}",
         [AX + 2640, DY])
link('Куда после хода?', B[0], 0)
chain(*B)
for i, nm in enumerate(BG):
    link('Сколько картинок? (B)', nm, i)
    link(nm, 'Извлекаем картинку (B)')
chain(*B2, 'Отправляем картинку (B)')

CY = EY + 1100
C = ['Скачиваем текущую картинку (C)', 'Готовим список: доп. референсы (C)', 'Скачиваем референс (C)', 'Собираем доп. референсы в один item (C)', 'Собираем все референсы (C)', 'Сколько картинок? (C)']
for i, nm in enumerate(C):
    take(nm, [AX + 440 + i * 220, CY])
nodes_by('Готовим список: доп. референсы (C)')['parameters']['jsCode'] = open(os.path.join(JS, 'spisok_c.js')).read()
C_COUNTS = list(range(1, MAX_IMAGES + 1))
CG = [f'gpt-image-2: точечная правка (C, {c} img)' for c in C_COUNTS]
for i, (nm, c) in enumerate(zip(CG, C_COUNTS)):
    # Первая картинка — основа правки, остальные только референсы (механика порядка картинок).
    image_call('gpt-image-2: точечная правка (C)', nm, c,
               "=Edit the first image. The other images are references only.\n\n{{ $('Итог хода').first().json.editRoles }}{{ $json.revisionInstruction }}",
               [AX + 1760, CY - 1400 + i * 160])
image_switch('Сколько картинок? (C)', C_COUNTS)
C2 = ['Извлекаем картинку (C)', 'Загружаем на Диск (C)', 'Открываем доступ (C)', 'Собираем ссылку (C)', 'Сохраняем картинку (C)']
for i, nm in enumerate(C2):
    take(nm, [AX + 1980 + i * 220, CY])
tg_photo('Отправляем картинку (C)', "={{ $('Собираем ссылку (C)').first().json.chatId }}",
         "={{ $('Собираем ссылку (C)').first().json.ai_ImageUrl }}",
         "={{ $('Итог хода').first().json.stageIcon }} {{ $('Итог хода').first().json.stageName }}: Вариант {{ $('Собираем ссылку (C)').first().json.variantNumber }} (уточнено{{ $('Собираем все референсы (C)').first().json.hasMask ? ' по обводке' : ($('Кто отвечает').first().json.needMask ? '; обводка не прочиталась — правка всей картинки' : '') }})\nID: {{ $('Собираем ссылку (C)').first().json.sys_ProjectID }}",
         "=✅ Согласовать вариант {{ $('Собираем ссылку (C)').first().json.variantNumber }}",
         "=img|{{ $('Собираем ссылку (C)').first().json.sys_ProjectID }}|{{ $('Собираем ссылку (C)').first().json.variantNumber }}",
         [AX + 3080, CY])
# Правка по обводке: фото автора с красной обводкой → сборщик делает маску (прозрачное = можно менять).
if_node('Правка по обводке?', "$('Кто отвечает').first().json.needMask", [AX, CY + 300])
add({'parameters': {'resource': 'file', 'operation': 'get', 'fileId': "={{ (function(){ const p = $('Кто отвечает').first().json.maskPhoto; return p[p.length - 1].file_id; })() }}",
                    'download': True, 'additionalFields': {}},
     'name': 'Скачиваем фото обводки', 'type': 'n8n-nodes-base.telegram', 'typeVersion': 1.2,
     'position': [AX + 110, CY + 460], 'webhookId': uid(), 'credentials': copy.deepcopy(CRED_TG)})
code('Фото обводки в base64', 'foto.js', [AX + 220, CY + 620])
add({'parameters': {'method': 'POST', 'url': ASM + '/edit_mask', 'sendBody': True, 'specifyBody': 'json',
                    'jsonBody': "={{ JSON.stringify({ imageUrl: $('Итог хода').first().json.revisionTargetImageUrl, markedDataUrl: $('Фото обводки в base64').first().json.userImageUrl }) }}",
                    'options': {'timeout': 120000, 'response': {'response': {'responseFormat': 'file', 'outputPropertyName': 'mask'}}}},
     'name': 'Сервер: маска', 'type': 'n8n-nodes-base.httpRequest', 'typeVersion': 4.2, 'position': [AX + 330, CY + 460],
     'onError': 'continueRegularOutput'})
link('Куда после хода?', 'Правка по обводке?', 1)
link('Правка по обводке?', 'Скачиваем фото обводки', 0)
link('Правка по обводке?', C[0], 1)
chain('Скачиваем фото обводки', 'Фото обводки в base64', 'Сервер: маска', C[0])
nodes_by('Собираем все референсы (C)')['parameters']['jsCode'] = open(os.path.join(JS, 'sobiraem_c.js')).read()
chain(*C[:-1])
# с маской — те же узлы правки, плюс поле mask (маска относится к первой картинке)
if_node('С маской? (C)', "$json.hasMask", [AX + 1430, CY + 300])
sw = copy.deepcopy(nodes_by('Сколько картинок? (C)'))
sw['id'] = uid(); sw['name'] = 'Сколько картинок? (C, маска)'; sw['position'] = [AX + 1540, CY + 460]
add(sw)
CM = [f'gpt-image-2: правка по обводке (C, {c} img)' for c in C_COUNTS]
for i, (nm, c) in enumerate(zip(CM, C_COUNTS)):
    image_call('gpt-image-2: точечная правка (C)', nm, c,
                   "=Edit the first image only inside the transparent area of the mask; everything outside the mask stays exactly as it is. The other images are references only.\n\n{{ $('Итог хода').first().json.editRoles }}{{ $json.revisionInstruction }}",
                   [AX + 1760, CY + 1300 + i * 160])
    nodes_by(nm)['parameters']['bodyParameters']['parameters'].append({'parameterType': 'formBinaryData', 'name': 'mask', 'inputDataFieldName': 'mask'})
link(C[-2], 'С маской? (C)')
link('С маской? (C)', 'Сколько картинок? (C, маска)', 0)
link('С маской? (C)', C[-1], 1)
for i, nm in enumerate(CM):
    link('Сколько картинок? (C, маска)', nm, i)
    link(nm, 'Извлекаем картинку (C)')
for i, nm in enumerate(CG):
    link('Сколько картинок? (C)', nm, i)
    link(nm, 'Извлекаем картинку (C)')
chain(*C2, 'Отправляем картинку (C)')

# ── после рисунка: этап «авто» — согласуем сами и передаём дальше ──
code('Авто: согласуем картинку', 'avto_kartinka.js', [AX + 3300, DY + 300])
if_node('Согласовать самим?', "$('Авто: согласуем картинку').first().json.ok", [AX + 3520, DY + 300])
sheets_update('Записываем авто-картинку', "={{ $('Авто: согласуем картинку').first().json.sheetName }}", {
    'sys_ProjectID': "={{ $('Авто: согласуем картинку').first().json.projectId }}",
    'ai_ApprovedImageUrl': "={{ $('Авто: согласуем картинку').first().json.approvedUrl }}",
    'sys_Status': 'Картинка согласована',
}, [AX + 3740, DY + 300])
link('Отправляем картинку (B)', 'Авто: согласуем картинку')
link('Отправляем картинку (C)', 'Авто: согласуем картинку')
link('Авто: согласуем картинку', 'Согласовать самим?')
link('Согласовать самим?', 'Записываем авто-картинку', 0)
link('Записываем авто-картинку', 'Передаём дальше')

# ═════════════ КНОПКА ✅ ПОД ВАРИАНТОМ КАРТИНКИ ═════════════
BY = Y + 900
code('Согласуем вариант', 'soglasuem_variant.js', [X + 3140, BY])
if_node('Вариант нашёлся?', '$json.ok', [X + 3360, BY])
sheets_update('Записываем согласованную картинку', SHEET, {
    'sys_ProjectID': '={{ ' + CTX + '.projectId }}',
    'ai_ApprovedImageUrl': "={{ $('Согласуем вариант').first().json.approvedUrl }}",
    'sys_Status': "={{ $('Согласуем вариант').first().json.statusAfter }}",
}, [X + 3580, BY])
tg_send('Картинка согласована (кнопка)', '={{ ' + CTX + '.chatId }}', "={{ $('Согласуем вариант').first().json.confirmText }}", [X + 3800, BY])
tg_send('Вариант не найден', '={{ ' + CTX + '.chatId }}', '={{ $json.notFoundText }}', [X + 3580, BY + 200])
link('Куда дальше?', 'Согласуем вариант', 1)
link('Согласуем вариант', 'Вариант нашёлся?')
link('Вариант нашёлся?', 'Записываем согласованную картинку', 0)
link('Вариант нашёлся?', 'Вариант не найден', 1)
chain('Записываем согласованную картинку', 'Картинка согласована (кнопка)', 'Передаём дальше')

# ═════════════ ЗАПИСЬ В ТАБЛИЦУ (✅ под сводкой или этапы «авто») ═════════════
FY = Y + 1300
code('Собираем пакет для таблицы', 'paket.js', [X + 3140, FY], lib=True)
if_node('Пакет собран?', '$json.ok', [X + 3360, FY])
code('Пакет по колонкам', 'paket_zapis.js', [X + 3580, FY])
sheets_automap('Записываем пакет в таблицу', SHEET, [X + 3800, FY], 'sys_ProjectID')
sheets_read('Перечитываем строку (финал)', SHEET, [('sys_ProjectID', '={{ ' + CTX + '.projectId }}')], [X + 4020, FY])
code('Проверяем таблицу (финал)', 'proverka_final.js', [X + 4240, FY], lib=True)
if_node('Таблица в порядке?', '$json.ok', [X + 4460, FY])
sheets_update('Ставим статус Утверждено', SHEET, {
    'sys_ProjectID': '={{ ' + CTX + '.projectId }}', 'sys_Status': 'Утверждено'}, [X + 4680, FY])
code('Сообщение: утверждено', 'utverzhdeno.js', [X + 4900, FY], lib=True)
tg_send('Отправляем: утверждено', '={{ $json.chatId }}', '={{ $json.text }}', [X + 5120, FY])
tg_send('Кнопка: собрать с этими треками', "={{ $('Сообщение: утверждено').first().json.chatId }}",
        "={{ $('Сообщение: утверждено').first().json.buttonText }}", [X + 5560, FY - 120],
        button=('🎬 Собрать с этими треками', "={{ $('Сообщение: утверждено').first().json.callbackData }}"))
if_node('Треки уже есть?', "$('Сообщение: утверждено').first().json.hasTracks", [X + 5340, FY])
tg_send('Не могу утвердить', '={{ ' + CTX + '.chatId }}', '={{ $json.problemsText }}', [X + 3580, FY + 220])
link('Куда дальше?', 'Собираем пакет для таблицы', 2)
link('Куда после хода?', 'Собираем пакет для таблицы', 4)
link('Собираем пакет для таблицы', 'Пакет собран?')
link('Пакет собран?', 'Пакет по колонкам', 0)
link('Пакет собран?', 'Не могу утвердить', 1)
chain('Пакет по колонкам', 'Записываем пакет в таблицу', 'Перечитываем строку (финал)', 'Проверяем таблицу (финал)', 'Таблица в порядке?')
link('Таблица в порядке?', 'Ставим статус Утверждено', 0)
link('Таблица в порядке?', 'Не могу утвердить', 1)
chain('Ставим статус Утверждено', 'Сообщение: утверждено', 'Отправляем: утверждено', 'Треки уже есть?')
link('Треки уже есть?', 'Кнопка: собрать с этими треками', 0)
# ═════════════ ССЫЛКА НА ТРЕКИ ═════════════
TY = Y + 1900
code('Разбираем ссылку на треки', 'treki.js', [X + 2700, TY])
if_node('Уже опубликован?', '$json.published', [X + 2920, TY])
tg_send('Сообщаем: уже опубликован', '={{ ' + CTX + '.chatId }}', '={{ $json.publishedText }}', [X + 3140, TY - 200])
sheets_update('Сохраняем ссылку на треки', SHEET, {
    'sys_ProjectID': '={{ ' + CTX + '.projectId }}', 'sys_AudioZipUrl': '={{ ' + CTX + '.tracksUrl }}'}, [X + 3140, TY])
if_node('Уже утверждено?', "$('Разбираем ссылку на треки').first().json.approved", [X + 3360, TY])
tg_send('Ссылка сохранена, ждём ✅', '={{ ' + CTX + '.chatId }}', "={{ $('Разбираем ссылку на треки').first().json.waitText }}", [X + 3580, TY + 200])
link('Куда дальше?', 'Разбираем ссылку на треки', 3)
link('Разбираем ссылку на треки', 'Уже опубликован?')
link('Уже опубликован?', 'Сообщаем: уже опубликован', 0)
link('Уже опубликован?', 'Сохраняем ссылку на треки', 1)
link('Уже утверждено?', 'Ссылка сохранена, ждём ✅', 1)

# ═════════════ ЧИСТКА ЗВУКА В KAGGLE «ПО СОБЫТИЮ» ═════════════
# Ссылка сохранена → (если в таблице задан способ чистки) сервер запускает
# блокнот и сразу отвечает → ждём: блокнот сам «постучится» в это ожидание,
# а если нет — через N ч сработает будильник. Состояние — в строке выпуска.
_w04 = json.load(open(os.path.join(REPO, 'workflows/04_Video.json')))
ASSEMBLER = [n for n in _w04['nodes'] if n['name'] == 'Собираем видео (POST)'][0]['parameters']['url'].rsplit('/', 1)[0]

def http_post(name, url, body_expr, pos):
    return add({'parameters': {'method': 'POST', 'url': url, 'sendBody': True, 'specifyBody': 'json',
                               'jsonBody': body_expr, 'options': {'timeout': 600000}},
                'name': name, 'type': 'n8n-nodes-base.httpRequest', 'typeVersion': 4.2, 'position': pos,
                'onError': 'continueRegularOutput'})

KY = TY + 600
code('Чистка: нужна?', 'chistka_nuzhna.js', [X + 3360, KY], lib=True)
if_node('Нужна чистка?', "$('Чистка: нужна?').first().json.need", [X + 3580, KY])
http_post('Сервер: запусти чистку', ASSEMBLER + '/clean_start', "={{ JSON.stringify($('Чистка: нужна?').first().json.body) }}", [X + 3800, KY])
code('Чистка: запущена?', 'chistka_zapushena.js', [X + 4020, KY], lib=True)
sheets_update('Записываем чистку', SHEET, {
    'sys_ProjectID': '={{ ' + CTX + '.projectId }}',
    'sys_CleanTag': "={{ $('Чистка: запущена?').first().json.tag }}",
    'sys_CleanState': "={{ $('Чистка: запущена?').first().json.state }}",
    'sys_CleanStarted': "={{ $('Чистка: запущена?').first().json.started }}",
    'sys_CleanSource': "={{ $('Чистка: запущена?').first().json.source }}",
}, [X + 4240, KY])
tg_send('Сообщаем о чистке', "={{ $('Чистка: запущена?').first().json.chatId }}", "={{ $('Чистка: запущена?').first().json.text }}", [X + 4460, KY])
if_node('Чистка пошла?', "$('Чистка: запущена?').first().json.ok", [X + 4680, KY])
add({'parameters': {'resume': 'webhook', 'httpMethod': 'POST', 'limitWaitTime': True,
                    'limitType': 'afterTimeInterval',
                    'resumeAmount': "={{ $runIndex === 0 ? Math.round($('Чистка: нужна?').first().json.alarmHours * 60) : 15 }}",
                    'resumeUnit': 'minutes', 'options': {}},
     'name': 'Ждём стук Kaggle', 'type': 'n8n-nodes-base.wait', 'typeVersion': 1.1,
     'position': [X + 4900, KY], 'webhookId': uid()})
sheets_read('Перечитываем строку (чистка)', SHEET, [('sys_ProjectID', '={{ ' + CTX + '.projectId }}')], [X + 5120, KY])
code('Чистка: что дальше', 'chistka_dalshe.js', [X + 5340, KY])
switch_node('Чистка: куда?', "$('Чистка: что дальше').first().json.action", ['ask', 'failed', 'stop'], [X + 5560, KY])
http_post('Сервер: как чистка', ASSEMBLER + '/clean_status', "={{ JSON.stringify($('Чистка: что дальше').first().json.statusBody) }}", [X + 5780, KY - 100])
code('Чистка: итог', 'chistka_itog.js', [X + 6000, KY], lib=True)
switch_node('Чистка: итог куда?', "$('Чистка: итог').first().json.action", ['done', 'failed', 'wait_more', 'gave_up'], [X + 6220, KY])
sheets_update('Записываем итог чистки', SHEET, {
    'sys_ProjectID': '={{ ' + CTX + '.projectId }}',
    'sys_CleanState': "={{ $('Чистка: итог').first().json.state }}",
    'sys_AudioZipUrl': "={{ $('Чистка: итог').first().json.audioUrl || $('Перечитываем строку (чистка)').first().json.sys_AudioZipUrl }}",
}, [X + 6440, KY - 100])
tg_send('Сообщаем итог чистки', "={{ $('Чистка: итог').first().json.chatId }}", "={{ $('Чистка: итог').first().json.text }}", [X + 6660, KY - 100])
if_node('Собирать после чистки?', "$('Чистка: итог').first().json.action === 'done' && $('Чистка: итог').first().json.approved", [X + 6880, KY - 100])
if_node('Сказать, что ещё идёт?', "!$('Чистка: итог').first().json.quiet", [X + 6440, KY + 150])
tg_send('Чистка ещё идёт', "={{ $('Чистка: итог').first().json.chatId }}", "={{ $('Чистка: итог').first().json.text }}", [X + 6660, KY + 150])
# (20.10) «слишком долго» — сказать и закончить: раньше цепочка снова уходила в ожидание и повторяла это раз в час
tg_send('Чистка: перестала проверять', "={{ $('Чистка: итог').first().json.chatId }}", "={{ $('Чистка: итог').first().json.text }}", [X + 6440, KY + 350])

link('Сохраняем ссылку на треки', 'Чистка: нужна?')
link('Чистка: нужна?', 'Нужна чистка?')
link('Нужна чистка?', 'Сервер: запусти чистку', 0)
link('Нужна чистка?', 'Уже утверждено?', 1)
chain('Сервер: запусти чистку', 'Чистка: запущена?', 'Записываем чистку', 'Сообщаем о чистке', 'Чистка пошла?')
link('Чистка пошла?', 'Ждём стук Kaggle', 0)
chain('Ждём стук Kaggle', 'Перечитываем строку (чистка)', 'Чистка: что дальше', 'Чистка: куда?')
link('Чистка: куда?', 'Сервер: как чистка', 0)
link('Чистка: куда?', 'Чистка: итог', 1)
link('Сервер: как чистка', 'Чистка: итог')
link('Чистка: итог', 'Чистка: итог куда?')
link('Чистка: итог куда?', 'Записываем итог чистки', 0)
link('Чистка: итог куда?', 'Записываем итог чистки', 1)
link('Чистка: итог куда?', 'Сказать, что ещё идёт?', 2)
link('Чистка: итог куда?', 'Чистка: перестала проверять', 3)
link('Сказать, что ещё идёт?', 'Чистка ещё идёт', 0)
link('Сказать, что ещё идёт?', 'Ждём стук Kaggle', 1)
link('Записываем итог чистки', 'Сообщаем итог чистки')
link('Сообщаем итог чистки', 'Собирать после чистки?')
link('Собирать после чистки?', 'Перечитываем строку (стена)', 0)
# «ещё идёт» → снова ждём (20.10: будильник через 15 мин, стук по тому же адресу)

# ═════════════ «как чистка?» / «статус» ═════════════
SY = KY + 700
code('Статус чистки', 'status_chistki.js', [X + 2700, SY], lib=True)
if_node('Спросить сервер?', '$json.ask', [X + 2920, SY])
http_post('Сервер: как чистка (статус)', ASSEMBLER + '/clean_status', '={{ JSON.stringify($json.statusBody) }}', [X + 3140, SY - 100])
code('Статус чистки: ответ', 'status_chistki.js', [X + 3360, SY - 100], lib=True)
if_node('Обновить строку (статус)?', '$json.update', [X + 3580, SY])
sheets_update('Записываем статус чистки', SHEET, {
    'sys_ProjectID': '={{ ' + CTX + '.projectId }}',
    'sys_CleanState': '={{ $json.state }}',
    'sys_AudioZipUrl': "={{ $json.audioUrl || " + CTX + ".row.sys_AudioZipUrl }}",
}, [X + 3800, SY - 100])
code('Статус чистки: текст', 'status_tekst.js', [X + 4020, SY])
if_node('С кнопкой?', '$json.button', [X + 4240, SY])
tg_send('Статус с кнопкой', '={{ $json.chatId }}', '={{ $json.text }}', [X + 4460, SY - 100],
        button=('🎬 Собрать с этими треками', '={{ $json.callbackData }}'))
tg_send('Статус без кнопки', '={{ $json.chatId }}', '={{ $json.text }}', [X + 4460, SY + 100])
link('Куда дальше?', 'Статус чистки', 6)
link('Статус чистки', 'Спросить сервер?')
link('Спросить сервер?', 'Сервер: как чистка (статус)', 0)
link('Спросить сервер?', 'Обновить строку (статус)?', 1)
chain('Сервер: как чистка (статус)', 'Статус чистки: ответ', 'Обновить строку (статус)?')
link('Обновить строку (статус)?', 'Записываем статус чистки', 0)
link('Обновить строку (статус)?', 'Статус чистки: текст', 1)
link('Записываем статус чистки', 'Статус чистки: текст')
link('Статус чистки: текст', 'С кнопкой?')
link('С кнопкой?', 'Статус с кнопкой', 0)
link('С кнопкой?', 'Статус без кнопки', 1)

# ═════════════ СТЕНА ПЕРЕД СБОРЩИКОМ ═════════════
WX = X + 4900; WY = Y + 1600
sheets_read('Перечитываем строку (стена)', SHEET, [('sys_ProjectID', '={{ ' + CTX + '.projectId }}')], [WX, WY])
code('Стена: проверяем таблицу', 'barier.js', [WX + 220, WY], lib=True)
if_node('Всё на месте?', '$json.ok', [WX + 440, WY])
tg_send('Треки получены, приступаю к сборке', '={{ $json.chatId }}', '={{ $json.okText }}', [WX + 660, WY - 100])
add({'parameters': {'workflowId': {'__rl': True, 'value': VIDEO_WF_ID, 'mode': 'list',
                                   'cachedResultUrl': '/workflow/' + VIDEO_WF_ID, 'cachedResultName': '04_Video'},
                    'workflowInputs': {'mappingMode': 'defineBelow',
                                       'value': {'message': "={{ { text: '/render ' + $('Стена: проверяем таблицу').first().json.projectId, chat: { id: $('Стена: проверяем таблицу').first().json.chatId } } }}"},
                                       'matchingColumns': [], 'schema': [], 'attemptToConvertTypes': False, 'convertFieldsToString': False},
                    'options': {'waitForSubWorkflow': False}},
     'name': '04_Video', 'type': 'n8n-nodes-base.executeWorkflow', 'typeVersion': 1.2, 'position': [WX + 1000, WY - 100]})
tg_send('Сборку не запускаю', '={{ $json.chatId }}', '={{ $json.problemsText }}', [WX + 660, WY + 150])
link('Куда дальше?', 'Перечитываем строку (стена)', 5)
link('Уже утверждено?', 'Перечитываем строку (стена)', 0)
link('Чистка ещё идёт', 'Ждём стук Kaggle')
chain('Перечитываем строку (стена)', 'Стена: проверяем таблицу', 'Всё на месте?')
# Пересборка уже выпущенного проекта: 04 отказывает при статусе «Опубликовано», поэтому перед сборкой статус возвращается
sheets_update('Статус: снова утверждено', SHEET, {'sys_ProjectID': "={{ $('Стена: проверяем таблицу').first().json.projectId }}",
                                                 'sys_Status': 'Утверждено'}, [WX + 770, WY - 100])
link('Всё на месте?', 'Треки получены, приступаю к сборке', 0)
link('Всё на месте?', 'Сборку не запускаю', 1)
link('Треки получены, приступаю к сборке', 'Статус: снова утверждено')
link('Статус: снова утверждено', '04_Video')



def sticky(text, pos, w, h, color=7):
    add({'parameters': {'content': text, 'height': h, 'width': w, 'color': color},
         'name': 'Заметка ' + str(len(nodes)), 'type': 'n8n-nodes-base.stickyNote', 'typeVersion': 1, 'position': pos})

sticky("## Вход\nТелеграм и «Вызов изнутри» (переход к следующему этапу) разбираются в одном месте.\n\nБот тот же, что у 10_Единый_редактор. Включён должен быть ТОЛЬКО один канвас.", [X - 40, Y - 360], 620, 260, 4)
sticky("## Движок этапов\nКод не знает ролей, пунктов и колонок с содержанием. Кто работает, в каком порядке, с кем говорит и нужно ли согласование — лист «Этапы». Пункты и куда они пишутся — лист «Пункты». Что знает этап — колонки Templates с его значком (📍 — по словам задания, 📝 — памятка этапа).", [EX - 40, EY - 520], 1000, 260, 5)
sticky("## Запись в таблицу\nПункты раскладываются по колонкам из листа «Пункты». Строка перечитывается и проверяется, только потом «Утверждено».", [X + 3100, FY - 260], 900, 200, 3)

# МЕТКА ВЫПУСКА (14.10, автор): каждое сообщение по проекту начинается с «🐧 16.10 · Кот в книжном» —
# при двух-трёх выпусках сразу видно, на какое отвечать. Метку считает «Контекст проекта» (календарь + Catalog).
NO_LABEL = {'Проект создан', 'Предлагаем каналы'}
LBL = "$('Контекст проекта').first().json"
for n_ in nodes:
    if n_.get('type') != 'n8n-nodes-base.telegram' or n_['name'] in NO_LABEL:
        continue
    p_ = n_['parameters']
    if p_.get('operation') not in ('sendMessage', 'sendPhoto', 'sendVideo'):
        continue
    html = (p_.get('additionalFields') or {}).get('parse_mode') == 'HTML'
    field = LBL + ('.labelLine' if html else '.labelPlain')
    holder, key = (p_, 'text') if p_.get('operation') == 'sendMessage' else (p_['additionalFields'], 'caption')
    t_ = holder.get(key, '')
    m_ = re.fullmatch(r'=\{\{(.*)\}\}', t_, re.S)
    holder[key] = ('={{ ' + field + ' + (' + m_.group(1).strip() + ') }}') if m_ and '{{' not in m_.group(1) else ('={{ ' + field + ' }}' + t_[1:])

# Повтор при сбое Code-узлов (08.10): n8n иногда не успевает передать задачу исполнителю («Task request timed out
# after 60 seconds»), особенно при нескольких запусках сразу. 3 попытки с паузой 25 с — сбой не доходит до автора.
for n_ in nodes:
    if n_.get('type') == 'n8n-nodes-base.code':
        n_['retryOnFail'] = True
        n_['maxTries'] = 3
        n_['waitBetweenTries'] = 25000

wf = {
    'name': '12_Этапы',
    'nodes': nodes,
    'connections': conns,
    'active': False,
    'settings': {'executionOrder': 'v1', 'binaryMode': 'separate', 'errorWorkflow': 'A6x2zK1xfuhc5I3E',
                 'callerPolicy': 'workflowsFromSameOwner'},
    'pinData': {},
    'tags': [],
}
out = os.path.join(REPO, 'workflows/12_Этапы.json')
json.dump(wf, open(out, 'w'), ensure_ascii=False, indent=2)
print('nodes', len(nodes), '->', out)
