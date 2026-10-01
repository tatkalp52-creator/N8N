import json, uuid, copy, os

REPO = '/home/user/N8N'
JS = os.path.join(os.path.dirname(__file__), 'js')
DOC = '1yEolX-8NV7NInu3OwCoxo2KSSNMny9dk-AVrpKdyNEs'
CRED_SHEETS = {'googleApi': {'id': '1uQkgKbOPhjKOB2l', 'name': 'Google Sheets account 2'}}
CRED_OPENAI = {'openAiApi': {'id': 'HvMLVgMnS8OU4ebj', 'name': 'OpenAi account'}}
# Тот же бот, что у старых воркфлоу (автор решила не заводить отдельный).
# Одновременно включён ТОЛЬКО один из двух: 00_Вход_и_диспетчер или этот.
CRED_TG = {'telegramApi': {'id': 'UW2MJh6bPIyVZeig', 'name': 'Telegram account 2'}}
VIDEO_WF_ID = 'Ajn6GuRmndcwqm16'

LIB = open(os.path.join(JS, 'lib_state.js')).read()

nodes = []
conns = {}
names = set()

def uid():
    return str(uuid.uuid4())

def add(node):
    assert node['name'] not in names, node['name']
    names.add(node['name'])
    node.setdefault('id', uid())
    nodes.append(node)
    return node['name']

def code(name, file, pos, lib=False):
    src = open(os.path.join(JS, file)).read()
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

CTX = "$('Контекст проекта').first().json"
P = "$('Парсим ответ редактора').first().json"
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
code('Разбираем входящее', 'razbor.js', [X + 440, Y])
switch_node('Что пришло?', '$json.kind', ['newStart', 'channelPick', 'unknown'], [X + 660, Y])
chain('Telegram Trigger', 'Это владелец бота?', 'Разбираем входящее', 'Что пришло?')

# ── новый заход: кнопки каналов
sheets_read('Читаем каталог каналов', 'Catalog', [], [X + 900, Y - 700], always=False)
code('Кнопка на каждый канал', 'kanaly.js', [X + 1120, Y - 700], lib=True)
tg_send('Предлагаем каналы', '={{ $json.chatId }}', '={{ $json.text }}', [X + 1340, Y - 700],
        button=('▶ Начать проект', '={{ $json.channel }}'))
link('Что пришло?', 'Читаем каталог каналов', 0)
chain('Читаем каталог каналов', 'Кнопка на каждый канал', 'Предлагаем каналы')

# ── выбран канал: создаём проект
tg_answer('Отвечаем на кнопку канала', [X + 900, Y - 450])
sheets_read('Ищем канал в каталоге', 'Catalog', [('Channel', "={{ $('Разбируем входящее').first().json.channelKey }}".replace('Разбируем', 'Разбираем'))], [X + 1120, Y - 450], always=False)
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
        "=Проект создан ✅\nID: {{ $('Генерируем ProjectID').first().json.projectId }}\n\nО чём сегодня думаем? Отвечайте на мои сообщения (reply) — так я понимаю, о каком проекте речь.",
        [X + 1780, Y - 450])
link('Что пришло?', 'Отвечаем на кнопку канала', 1)
chain('Отвечаем на кнопку канала', 'Ищем канал в каталоге', 'Генерируем ProjectID', 'Создаём проект', 'Проект создан')

# ── всё, что относится к существующему проекту
if_node('Это кнопка?', "!!$('Разбираем входящее').first().json.callbackQueryId", [X + 900, Y])
tg_answer('Отвечаем на кнопку', [X + 1120, Y - 150])
# Всплывающее «Принято» сразу после нажатия ✅ под картинкой — видно, что тап сработал
nodes[-1]['parameters']['additionalFields'] = {'text': "={{ $('Разбираем входящее').first().json.kind === 'imgApprove' ? '✅ Принято, вариант ' + $('Разбираем входящее').first().json.variantNumber : '' }}"}
sheets_read('Находим лист канала', 'Catalog', [('Channel', "={{ $('Разбираем входящее').first().json.channelKey }}")], [X + 1340, Y])
sheets_read('Читаем строку проекта', '={{ $json.SheetName }}', [('sys_ProjectID', "={{ $('Разбираем входящее').first().json.projectId }}")], [X + 1560, Y])
sheets_read('Читаем шаблоны канала', 'Templates', [('tmpl_Channel', "={{ $('Разбираем входящее').first().json.channelKey }}")], [X + 1780, Y])
code('Контекст проекта', 'kontekst.js', [X + 2000, Y])
if_node('Проект найден?', '$json.found', [X + 2220, Y])
tg_send('Проект не найден', '={{ $json.chatId }}', '=Не нашла проект {{ $json.projectId }} в таблице канала — ничего не делаю.', [X + 2440, Y + 200])
switch_node('Куда дальше?', '$json.kind', ['message', 'imgApprove', 'finalApprove', 'tracks', 'oldButton', 'build', 'cleanStatus'], [X + 2440, Y])
tg_send('Старая кнопка', '={{ $json.chatId }}', '=Эта кнопка из старой схемы — в новом канвасе она ничего не делает.\n\nID: {{ $json.projectId }}', [X + 2700, Y + 1500])
link('Что пришло?', 'Это кнопка?', 3)  # 2 = unknown → никуда
link('Это кнопка?', 'Отвечаем на кнопку', 0)
link('Это кнопка?', 'Находим лист канала', 1)
chain('Отвечаем на кнопку', 'Находим лист канала', 'Читаем строку проекта', 'Читаем шаблоны канала', 'Контекст проекта', 'Проект найден?')
link('Проект найден?', 'Куда дальше?', 0)
link('Проект найден?', 'Проект не найден', 1)
link('Куда дальше?', 'Старая кнопка', 4)

# ═════════════ КНОПКА ✅ ПОД ВАРИАНТОМ КАРТИНКИ ═════════════
BY = Y + 900
code('Согласуем вариант', 'soglasuem_variant.js', [X + 2700, BY])
if_node('Вариант нашёлся?', '$json.ok', [X + 2920, BY])
sheets_update('Записываем согласованную картинку', SHEET, {
    'sys_ProjectID': '={{ ' + CTX + '.projectId }}',
    'ai_ApprovedImageUrl': "={{ $('Согласуем вариант').first().json.approvedUrl }}",
    'sys_Status': "={{ $('Согласуем вариант').first().json.statusAfter }}",
}, [X + 3140, BY])
tg_send('Картинка согласована (кнопка)', '={{ ' + CTX + '.chatId }}', "={{ $('Согласуем вариант').first().json.confirmText }}", [X + 3360, BY])
tg_send('Вариант не найден', '={{ ' + CTX + '.chatId }}', '={{ $json.notFoundText }}', [X + 3140, BY + 200])
link('Куда дальше?', 'Согласуем вариант', 1)
link('Согласуем вариант', 'Вариант нашёлся?')
link('Вариант нашёлся?', 'Записываем согласованную картинку', 0)
link('Вариант нашёлся?', 'Вариант не найден', 1)
chain('Записываем согласованную картинку', 'Картинка согласована (кнопка)')

# ═════════════ РЕДАКТОР ═════════════
EY = Y - 1400
EX = X + 2700
code('Вход редактора', 'vhod_redaktora.js', [EX, EY])
code('Собираем знания канала', 'znaniya.js', [EX + 220, EY], lib=True)
if_node('Есть разговор?', "!!String(" + CTX + ".row.sys_ConversationId || '').trim()", [EX + 440, EY])
openai_http('OpenAI: создаём разговор', "={{ JSON.stringify({ metadata: { project: " + CTX + ".projectId } }) }}",
            'https://api.openai.com/v1/conversations', [EX + 660, EY + 180])
if_node('Есть фото?', "!!$('Вход редактора').first().json.photo", [EX + 880, EY])
add({'parameters': {'resource': 'file', 'operation': 'get', 'fileId': "={{ (function(){ const p = $('Вход редактора').first().json.photo; return p[p.length - 1].file_id; })() }}",
                    'download': True, 'additionalFields': {}},
     'name': 'Скачиваем фото', 'type': 'n8n-nodes-base.telegram', 'typeVersion': 1.2,
     'position': [EX + 1100, EY + 180], 'webhookId': uid(), 'credentials': copy.deepcopy(CRED_TG)})
code('Фото в base64', 'foto.js', [EX + 1320, EY + 180])
code('Готовим запрос редактору', 'zapros.js', [EX + 1540, EY], lib=True)
openai_http('OpenAI: Редактор', '={{ JSON.stringify($json.requestBody) }}', 'https://api.openai.com/v1/responses', [EX + 1760, EY])
code('Разбираем ответ редактора', 'parse.js', [EX + 1980, EY - 260], lib=True)
# ── Писатель: описание (пункт 3) пишет отдельный вызов, только по правилам ОПИСАНИЯ
if_node('Нужен писатель?', "!!$('Разбираем ответ редактора').first().json.storyBrief", [EX + 1980, EY + 180])
code('Готовим задание писателю', 'pisatel_zadanie.js', [EX + 1980, EY + 400], lib=True)
openai_http('OpenAI: Писатель', '={{ JSON.stringify($json.requestBody) }}', 'https://api.openai.com/v1/responses', [EX + 2200, EY + 400])
nodes[-1]['parameters']['options'] = {'timeout': 600000}
nodes[-1]['onError'] = 'continueRegularOutput'
code('Готовим перевод для автора', 'pisatel_perevod.js', [EX + 2420, EY + 400])
openai_http('OpenAI: перевод для автора', '={{ JSON.stringify($json.requestBody) }}', 'https://api.openai.com/v1/responses', [EX + 2640, EY + 400])
nodes[-1]['onError'] = 'continueRegularOutput'
code('Парсим ответ редактора', 'pisatel_itog.js', [EX + 1980, EY], lib=True)
sheets_update('Сохраняем ход разговора', '={{ ' + P + '.sheetName }}', {
    'sys_ProjectID': '={{ ' + P + '.projectId }}',
    'sys_ConversationId': '={{ ' + P + '.conversationId }}',
    'sys_PendingToolCallId': "={{ " + P + ".callId || '' }}",
    'sys_EditorState': '={{ ' + P + '.editorState }}',
    'sys_Status': '={{ ' + P + '.statusAfter }}',
    'ai_UserBrief': '={{ ' + P + '.userBrief }}',
}, [EX + 2200, EY])
if_node('Есть заметки?', "!!" + P + ".communicationNotes", [EX + 2420, EY])
sheets_update('Сохраняем заметки редактора', 'Templates', {
    'tmpl_Channel': '={{ ' + P + '.channelKey }}',
    '🖋_tmpl_EditorNotes': '={{ ' + P + '.communicationNotes }}',
}, [EX + 2640, EY + 180], match='tmpl_Channel')
switch_node('Что делает редактор?', P + '.action', ['chat', 'ready_to_draw', 'revise_point', 'approved', 'text_block'], [EX + 2860, EY])

link('Куда дальше?', 'Вход редактора', 0)
link('Картинка согласована (кнопка)', 'Вход редактора')
sheets_read('Читаем прошлые выпуски', SHEET, [], [EX + 220, EY - 260])
code('Прошлые главы', 'proshlye.js', [EX + 440, EY - 260])
# «Художнику: …» — сразу в рисование, без Редактора
if_node('Напрямую художнику?', "!!$('Вход редактора').first().json.directArt", [EX + 220, EY + 260])
code('Задание художнику напрямую', 'hudozhniku.js', [EX + 1760, EY + 260], lib=True)
chain('Вход редактора', 'Собираем знания канала', 'Напрямую художнику?')
link('Напрямую художнику?', 'Задание художнику напрямую', 0)
link('Напрямую художнику?', 'Читаем прошлые выпуски', 1)
link('Задание художнику напрямую', 'Парсим ответ редактора')
chain('Читаем прошлые выпуски', 'Прошлые главы', 'Есть разговор?')
link('Есть разговор?', 'Есть фото?', 0)
link('Есть разговор?', 'OpenAI: создаём разговор', 1)
link('OpenAI: создаём разговор', 'Есть фото?')
link('Есть фото?', 'Скачиваем фото', 0)
link('Есть фото?', 'Готовим запрос редактору', 1)
chain('Скачиваем фото', 'Фото в base64', 'Готовим запрос редактору')
chain('Готовим запрос редактору', 'OpenAI: Редактор', 'Разбираем ответ редактора', 'Нужен писатель?')
link('Нужен писатель?', 'Готовим задание писателю', 0)
link('Нужен писатель?', 'Парсим ответ редактора', 1)
chain('Готовим задание писателю', 'OpenAI: Писатель', 'Готовим перевод для автора', 'OpenAI: перевод для автора', 'Парсим ответ редактора')
chain('Парсим ответ редактора', 'Сохраняем ход разговора', 'Есть заметки?')
link('Есть заметки?', 'Сохраняем заметки редактора', 0)
link('Есть заметки?', 'Что делает редактор?', 1)
link('Сохраняем заметки редактора', 'Что делает редактор?')

AX = EX + 3120
# chat (и всё непонятное)
code('Готовим реплику', 'otvet_chat.js', [AX, EY - 700], lib=True)
tg_send('Отправляем реплику', '={{ $json.chatId }}', '={{ $json.text }}', [AX + 220, EY - 700])
link('Что делает редактор?', 'Готовим реплику', 0)
link('Что делает редактор?', 'Готовим реплику', 5)
link('Готовим реплику', 'Отправляем реплику')

# approved (картинка согласована через разговор)
sheets_update('Записываем согласование картинки', '={{ ' + P + '.sheetName }}', {
    'sys_ProjectID': '={{ ' + P + '.projectId }}',
    'ai_ApprovedImageUrl': '={{ ' + P + '.resolvedApprovedImageUrl }}',
    'ai_TargetBrightness': "={{ " + P + ".approveTargetBrightness || '' }}",
}, [AX, EY + 1300])
link('Что делает редактор?', 'Записываем согласование картинки', 3)
# после записи — тот же показ текстового блока, что и для update_text_block
link('Записываем согласование картинки', 'Собираем текстовый блок')

# text_block
code('Собираем текстовый блок', 'blok.js', [AX, EY + 1700], lib=True)
if_node('Все 8 согласованы?', "$('Собираем текстовый блок').first().json.allAgreed", [AX + 220, EY + 1700])
tg_send('Отправляем текстовый блок', '={{ $json.chatId }}', '={{ $json.text }}', [AX + 440, EY + 1900])
openai_http('OpenAI: перевод описания', "={{ JSON.stringify($('Собираем текстовый блок').first().json.translateBody) }}",
            'https://api.openai.com/v1/responses', [AX + 440, EY + 1700])
code('Сводка на утверждение', 'svodka.js', [AX + 660, EY + 1700], lib=True)
sheets_update('Сохраняем перевод', '={{ $json.sheetName }}', {
    'sys_ProjectID': '={{ $json.projectId }}',
    'sys_EditorState': '={{ $json.editorState }}',
}, [AX + 880, EY + 1700])
code('Режем сводку', 'svodka_kuski.js', [AX + 1100, EY + 1700])
tg_send('Отправляем сводку', '={{ $json.chatId }}', '={{ $json.text }}', [AX + 1320, EY + 1700])
code('Одно сообщение с кнопкой', 'svodka_knopka.js', [AX + 1540, EY + 1700], lib=True)
tg_send('Кнопка финального согласования', '={{ $json.chatId }}', '={{ $json.text }}', [AX + 1760, EY + 1700],
        button=('✅ Согласовано', '={{ $json.callbackData }}'))
link('Что делает редактор?', 'Собираем текстовый блок', 4)
link('Собираем текстовый блок', 'Все 8 согласованы?')
link('Все 8 согласованы?', 'OpenAI: перевод описания', 0)
link('Все 8 согласованы?', 'Отправляем текстовый блок', 1)
chain('OpenAI: перевод описания', 'Сводка на утверждение', 'Сохраняем перевод', 'Режем сводку', 'Отправляем сводку', 'Одно сообщение с кнопкой', 'Кнопка финального согласования')

# ═════════════ РИСОВАНИЕ (узлы перенесены из 01_Художник) ═════════════
art = json.load(open(os.path.join(REPO, 'workflows/01_Художник.json')))
art_nodes = {n['name']: n for n in art['nodes']}

def take(name, pos):
    n = copy.deepcopy(art_nodes[name])
    n['id'] = uid()
    n['position'] = pos
    n.pop('webhookId', None)
    return add(n)

DY = EY - 400
code('Реплика перед рисованием', 'otvet_korotkiy.js', [AX, DY], lib=True)
tg_send('Сообщаем: рисую', '={{ $json.chatId }}', '={{ $json.text }}', [AX + 220, DY])
B = ['Готовим список: style guide + референсы', 'Скачиваем референс (B)', 'Собираем референсы в один item (B)', 'Сколько картинок? (B)']
for i, nm in enumerate(B):
    take(nm, [AX + 440 + i * 220, DY])
nodes_by = lambda nm: [n for n in nodes if n['name'] == nm][0]
nodes_by(B[0])['parameters']['jsCode'] = open(os.path.join(JS, 'spisok_b.js')).read()
MAX_IMAGES = 16  # столько картинок модель принимает за один вызов

def image_switch(name, counts):
    """Переключатель по числу картинок: выход i — counts[i], последний — «всё остальное»."""
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
    """Вызов художника ровно с count картинками image_0..image_{count-1}."""
    n = copy.deepcopy(art_nodes[template])
    n['id'] = uid(); n['name'] = name; n['position'] = pos
    bp = [x for x in n['parameters']['bodyParameters']['parameters'] if x.get('parameterType') != 'formBinaryData']
    for x in bp:
        if x.get('name') == 'model':
            x['value'] = "={{ $('Собираем знания канала').first().json.imageModel }}"
        if x.get('name') == 'prompt':
            x['value'] = prompt
    if not any(x.get('name') == 'quality' for x in bp):
        bp.insert(3, {'name': 'quality', 'value': 'high'})
    bp += [{'parameterType': 'formBinaryData', 'name': 'image[]', 'inputDataFieldName': f'image_{k}'} for k in range(count)]
    n['parameters']['bodyParameters']['parameters'] = bp
    return add(n)

B_COUNTS = list(range(1, MAX_IMAGES + 1))
BG = [f'gpt-image-2: рисуем (B, {c} img)' for c in B_COUNTS]
for i, (nm, c) in enumerate(zip(BG, B_COUNTS)):
    # Роли референсов (и картинок места) — из «Парсим ответ редактора» (tbPickRefs)
    image_call('gpt-image-2: рисуем (B)', nm, c,
               "={{ $('Парсим ответ редактора').first().json.drawRoles || $('Собираем знания канала').first().json.referenceRolesDraw }}{{ $json.dallePrompt }}",
               [AX + 1320, DY - 1400 + i * 160])
image_switch('Сколько картинок? (B)', B_COUNTS)
B2 = ['Извлекаем картинку (B)', 'Загружаем на Диск (B)', 'Открываем доступ (B)', 'Собираем ссылку (B)', 'Сохраняем картинку и промпт (B)']
for i, nm in enumerate(B2):
    take(nm, [AX + 1540 + i * 220, DY])
tg_photo('Отправляем картинку (B)', "={{ $('Собираем ссылку (B)').first().json.chatId }}",
         "={{ $('Собираем ссылку (B)').first().json.ai_ImageUrl }}",
         "=Вариант {{ $('Собираем ссылку (B)').first().json.variantNumber }}\nID: {{ $('Собираем ссылку (B)').first().json.sys_ProjectID }}",
         "=✅ Согласовать вариант {{ $('Собираем ссылку (B)').first().json.variantNumber }}",
         "=img|{{ $('Собираем ссылку (B)').first().json.sys_ProjectID }}|{{ $('Собираем ссылку (B)').first().json.variantNumber }}",
         [AX + 2640, DY])
link('Что делает редактор?', 'Реплика перед рисованием', 1)
chain('Реплика перед рисованием', 'Сообщаем: рисую', *B)
for i, nm in enumerate(BG):
    link('Сколько картинок? (B)', nm, i)
    link(nm, 'Извлекаем картинку (B)')
chain(*B2, 'Отправляем картинку (B)')

CY = EY + 500
code('Реплика перед правкой', 'otvet_korotkiy.js', [AX, CY], lib=True)
tg_send('Сообщаем: поправляю', '={{ $json.chatId }}', '={{ $json.text }}', [AX + 220, CY])
C = ['Скачиваем текущую картинку (C)', 'Готовим список: доп. референсы (C)', 'Скачиваем референс (C)', 'Собираем доп. референсы в один item (C)', 'Собираем все референсы (C)', 'Сколько картинок? (C)']
for i, nm in enumerate(C):
    take(nm, [AX + 440 + i * 220, CY])
nodes_by('Готовим список: доп. референсы (C)')['parameters']['jsCode'] = open(os.path.join(JS, 'spisok_c.js')).read()
C_COUNTS = list(range(1, MAX_IMAGES + 1))
CG = [f'gpt-image-2: точечная правка (C, {c} img)' for c in C_COUNTS]
for i, (nm, c) in enumerate(zip(CG, C_COUNTS)):
    # Первая картинка — основа правки, остальные только референсы (иначе художник может править референс).
    # Правка — в том же качестве, что и рисование, иначе цвета уплывают в «пластик».
    image_call('gpt-image-2: точечная правка (C)', nm, c,
               "=Edit the first image. The other images are only references for the drawing style, the character and his places; do not bring their scenes into the picture.\n\n{{ $('Парсим ответ редактора').first().json.editRoles || $('Собираем знания канала').first().json.referenceRolesEdit }}{{ $json.revisionInstruction }}",
               [AX + 1760, CY - 1400 + i * 160])
image_switch('Сколько картинок? (C)', C_COUNTS)

C2 = ['Извлекаем картинку (C)', 'Загружаем на Диск (C)', 'Открываем доступ (C)', 'Собираем ссылку (C)', 'Сохраняем картинку (C)']
for i, nm in enumerate(C2):
    take(nm, [AX + 1980 + i * 220, CY])
tg_photo('Отправляем картинку (C)', "={{ $('Собираем ссылку (C)').first().json.chatId }}",
         "={{ $('Собираем ссылку (C)').first().json.ai_ImageUrl }}",
         "=Вариант {{ $('Собираем ссылку (C)').first().json.variantNumber }} (уточнено)\nID: {{ $('Собираем ссылку (C)').first().json.sys_ProjectID }}",
         "=✅ Согласовать вариант {{ $('Собираем ссылку (C)').first().json.variantNumber }}",
         "=img|{{ $('Собираем ссылку (C)').first().json.sys_ProjectID }}|{{ $('Собираем ссылку (C)').first().json.variantNumber }}",
         [AX + 3080, CY])
link('Что делает редактор?', 'Реплика перед правкой', 2)
chain('Реплика перед правкой', 'Сообщаем: поправляю', *C)
for i, nm in enumerate(CG):
    link('Сколько картинок? (C)', nm, i)
    link(nm, 'Извлекаем картинку (C)')
chain(*C2, 'Отправляем картинку (C)')

# ═════════════ ФИНАЛЬНАЯ КНОПКА ✅ ═════════════
FY = Y + 1300
code('Собираем пакет для таблицы', 'paket.js', [X + 2700, FY], lib=True)
if_node('Пакет собран?', '$json.ok', [X + 2920, FY])
fields = {k: "={{ $('Собираем пакет для таблицы').first().json.fields." + k + " }}" for k in
          ['sys_ProjectID', 'ai_OverlayText', 'ai_OverlayPosition', 'ai_Title', 'ai_DescriptionDraft', 'ai_DescriptionEN',
           'ai_Description', 'ai_Hashtags', 'ai_Tags', 'ai_PinnedComment', 'ai_TimecodeNames']}
sheets_update('Записываем пакет в таблицу', SHEET, fields, [X + 3140, FY])
sheets_read('Перечитываем строку (финал)', SHEET, [('sys_ProjectID', '={{ ' + CTX + '.projectId }}')], [X + 3360, FY])
code('Проверяем таблицу (финал)', 'proverka_final.js', [X + 3580, FY], lib=True)
if_node('Таблица в порядке?', '$json.ok', [X + 3800, FY])
sheets_update('Ставим статус Утверждено', SHEET, {
    'sys_ProjectID': '={{ ' + CTX + '.projectId }}', 'sys_Status': 'Утверждено'}, [X + 4020, FY])
# ── Летопись: после утверждения дописываем несколько строк о выпуске
code('Готовим запись в летопись', 'letopis_zapros.js', [X + 4020, FY + 260], lib=True)
openai_http('OpenAI: летопись', '={{ JSON.stringify($json.requestBody) }}', 'https://api.openai.com/v1/responses', [X + 4240, FY + 260])
nodes[-1]['onError'] = 'continueRegularOutput'
code('Дописываем летопись', 'letopis_itog.js', [X + 4460, FY + 260])
if_node('Летопись готова?', '$json.ok', [X + 4680, FY + 260])
sheets_update('Сохраняем летопись', 'Templates', {
    'tmpl_Channel': '={{ ' + CTX + '.channelKey }}',
    '🖋_tmpl_Chronicle': "={{ $('Дописываем летопись').first().json.chronicle }}",
}, [X + 4900, FY + 160], match='tmpl_Channel')
nodes[-1]['onError'] = 'continueRegularOutput'
code('Сообщение: утверждено', 'utverzhdeno.js', [X + 4240, FY], lib=True)
tg_send('Отправляем: утверждено', '={{ $json.chatId }}', '={{ $json.text }}', [X + 4460, FY])
tg_send('Кнопка: собрать с этими треками', "={{ $('Сообщение: утверждено').first().json.chatId }}",
        "={{ $('Сообщение: утверждено').first().json.buttonText }}", [X + 5560, FY - 120],
        button=('🎬 Собрать с этими треками', "={{ $('Сообщение: утверждено').first().json.callbackData }}"))
if_node('Треки уже есть?', "$('Сообщение: утверждено').first().json.hasTracks", [X + 5340, FY])
tg_send('Не могу утвердить', '={{ ' + CTX + '.chatId }}', '={{ $json.problemsText }}', [X + 3140, FY + 220])
link('Куда дальше?', 'Собираем пакет для таблицы', 2)
link('Собираем пакет для таблицы', 'Пакет собран?')
link('Пакет собран?', 'Записываем пакет в таблицу', 0)
link('Пакет собран?', 'Не могу утвердить', 1)
chain('Записываем пакет в таблицу', 'Перечитываем строку (финал)', 'Проверяем таблицу (финал)', 'Таблица в порядке?')
link('Таблица в порядке?', 'Ставим статус Утверждено', 0)
link('Таблица в порядке?', 'Не могу утвердить', 1)
chain('Ставим статус Утверждено', 'Готовим запись в летопись', 'OpenAI: летопись', 'Дописываем летопись', 'Летопись готова?')
link('Летопись готова?', 'Сохраняем летопись', 0)
link('Летопись готова?', 'Сообщение: утверждено', 1)
link('Сохраняем летопись', 'Сообщение: утверждено')
chain('Сообщение: утверждено', 'Отправляем: утверждено', 'Треки уже есть?')

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
                    'resumeAmount': "={{ $runIndex === 0 ? $('Чистка: нужна?').first().json.alarmHours : 1 }}",
                    'resumeUnit': 'hours', 'options': {}},
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
tg_send('Чистка ещё идёт', "={{ $('Чистка: итог').first().json.chatId }}", "={{ $('Чистка: итог').first().json.text }}", [X + 6440, KY + 150])

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
link('Чистка: итог куда?', 'Чистка ещё идёт', 2)
link('Чистка: итог куда?', 'Чистка ещё идёт', 3)
link('Записываем итог чистки', 'Сообщаем итог чистки')
link('Сообщаем итог чистки', 'Собирать после чистки?')
link('Собирать после чистки?', 'Перечитываем строку (стена)', 0)
# «ещё идёт» → снова ждём (будильник через час, стук по тому же адресу)

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
     'name': '04_Video', 'type': 'n8n-nodes-base.executeWorkflow', 'typeVersion': 1.2, 'position': [WX + 880, WY - 100]})
tg_send('Сборку не запускаю', '={{ $json.chatId }}', '={{ $json.problemsText }}', [WX + 660, WY + 150])
link('Треки уже есть?', 'Кнопка: собрать с этими треками', 0)
link('Куда дальше?', 'Перечитываем строку (стена)', 5)
link('Уже утверждено?', 'Перечитываем строку (стена)', 0)
link('Чистка ещё идёт', 'Ждём стук Kaggle')
chain('Перечитываем строку (стена)', 'Стена: проверяем таблицу', 'Всё на месте?')
link('Всё на месте?', 'Треки получены, приступаю к сборке', 0)
link('Всё на месте?', 'Сборку не запускаю', 1)
link('Треки получены, приступаю к сборке', '04_Video')


def sticky(text, pos, w, h, color=7):
    add({'parameters': {'content': text, 'height': h, 'width': w, 'color': color},
         'name': 'Заметка ' + str(len(nodes)), 'type': 'n8n-nodes-base.stickyNote', 'typeVersion': 1, 'position': pos})

sticky("## Вход\nВсё из Телеграма разбирается в одном месте («Разбираем входящее»). Никаких статусов и ключевых слов для выбора этапа.\n\nБот тот же, что у старых воркфлоу. Включён должен быть ТОЛЬКО один: 00_Вход_и_диспетчер или этот канвас (у бота один вебхук — кто включён последним, тот и забирает сообщения).", [X - 40, Y - 360], 620, 300, 4)
sticky("## Редактор — один на весь выпуск\nКаждый ход видит карточку состояния: варианты картинки, что согласовано, все 8 пунктов текстового блока. Вперёд/назад — по смыслу, без переключений.\n\nСтатус в таблице здесь НЕ решает, кто отвечает: он нужен только как стена перед сборщиком.", [EX - 40, EY - 420], 900, 300, 5)
sticky("## Рисование\nУзлы перенесены из 01_Художник без изменений (референсы, gpt-image-2, Диск). Под каждой картинкой своя кнопка «✅ Согласовать вариант N».", [AX - 40, DY - 560], 700, 200, 6)
sticky("## Текстовый блок\n8 пунктов, номера закреплены. Показываем только то, что ждёт согласования. Когда согласованы все 8 — перевод описания и сводка с ОДНОЙ кнопкой ✅.", [AX - 40, EY + 1560], 800, 200, 6)
sticky("## Финальная кнопка ✅\n1) пишем пакет в таблицу (без статуса)\n2) ПЕРЕЧИТЫВАЕМ строку\n3) проверяем каждое поле\n4) только потом ставим «Утверждено»", [X + 2660, FY - 260], 900, 220, 3)
sticky("## Стена перед сборщиком\n«Треки получены, приступаю к сборке» стоит ПОСЛЕ проверки заново перечитанной строки. Если в таблице чего-то нет — до этого сообщения и до 04_Video цепочка физически не доходит.", [WX - 40, WY - 360], 1100, 220, 3)

wf = {
    'name': '10_Единый_редактор',
    'nodes': nodes,
    'connections': conns,
    'active': False,
    'settings': {'executionOrder': 'v1', 'binaryMode': 'separate', 'errorWorkflow': 'FIjHQQSAlggtP8ij',
                 'callerPolicy': 'workflowsFromSameOwner'},
    'pinData': {},
    'tags': [],
}
out = os.path.join(REPO, 'workflows/10_Единый_редактор.json')
json.dump(wf, open(out, 'w'), ensure_ascii=False, indent=2)
print('nodes', len(nodes), '->', out)
