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

