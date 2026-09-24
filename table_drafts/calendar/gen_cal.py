import json, uuid, sys
D='/tmp/claude-0/-home-user-N8N/994c923d-89bd-532f-b598-03f041c8a163/scratchpad/cal/'
CRED_ID = sys.argv[1] if len(sys.argv)>1 else 'SET_ME'
TG = {"telegramApi": {"id": CRED_ID, "name": "Telegram Studio Calendar"}}
GS = {"googleApi": {"id": "1uQkgKbOPhjKOB2l", "name": "Google Sheets account 2"}}
DOC = {"__rl": True, "value": "1yEolX-8NV7NInu3OwCoxo2KSSNMny9dk-AVrpKdyNEs", "mode": "id"}
SHEET = {"__rl": True, "value": "Календарь", "mode": "name"}
COLS = ['id','year','month','day','title','channel','status','project','note','sources','createdAt','updatedAt']
nodes=[]; conns={}
def node(name,type_,ver,params,pos,cred=None,**kw):
    n={"parameters":params,"id":str(uuid.uuid4()),"name":name,"type":type_,"typeVersion":ver,"position":pos}
    if cred: n["credentials"]=cred
    n.update(kw); nodes.append(n); return name
def link(a,b,out=0):
    c=conns.setdefault(a,{"main":[]})
    while len(c["main"])<=out: c["main"].append([])
    c["main"][out].append({"node":b,"type":"main","index":0})
TXT = {"appendAttribution": False, "parse_mode": "HTML", "disable_web_page_preview": True}
TXT_EDIT = {"parse_mode": "HTML", "disable_web_page_preview": True}
def btn(text, data): return {"text": text, "additionalFields": {"callback_data": data}}
IMP = {"rows": [
  {"row": {"buttons": [btn("🔴 Pengui", "=imp|{{ $json.importId }}|ch|pengui"), btn("🟡 Гобелены", "=imp|{{ $json.importId }}|ch|tapestry")]}},
  {"row": {"buttons": [btn("NotebookLM", "=imp|{{ $json.importId }}|src|NotebookLM"), btn("GPT", "=imp|{{ $json.importId }}|src|GPT"), btn("Gemini", "=imp|{{ $json.importId }}|src|Gemini"), btn("Claude", "=imp|{{ $json.importId }}|src|Claude")]}},
  {"row": {"buttons": [btn("✅ Добавить", "=imp|{{ $json.importId }}|go"), btn("✖ Отмена", "=imp|{{ $json.importId }}|no")]}}]}
CARD = {"rows": [
  {"row": {"buttons": [btn("⭐ Выбрать", "=st|{{ $json.rowId }}|p"), btn("🛠 В работе", "=st|{{ $json.rowId }}|w")]}},
  {"row": {"buttons": [btn("✓ Вышел", "=st|{{ $json.rowId }}|d"), btn("💡 Идея", "=st|{{ $json.rowId }}|i"), btn("✖ Отклонить", "=st|{{ $json.rowId }}|s")]}}]}

node("Telegram Trigger","n8n-nodes-base.telegramTrigger",1.1,{"updates":["message","callback_query"],"additionalFields":{}},[0,0],TG,webhookId=str(uuid.uuid4()))
node("Каждый понедельник","n8n-nodes-base.scheduleTrigger",1.2,{"rule":{"interval":[{"field":"cronExpression","expression":"0 9 * * 1"}]}},[0,260])
node("Это владелец?","n8n-nodes-base.if",2,{"conditions":{"options":{"caseSensitive":True,"leftValue":"","typeValidation":"loose"},"conditions":[{"leftValue":"={{ String($json.message?.from?.id || $json.callback_query?.from?.id || '') }}","rightValue":"285577543","operator":{"type":"string","operation":"equals"}}],"combinator":"and"},"options":{}},[220,0])
node("Читаем календарь","n8n-nodes-base.googleSheets",4,{"authentication":"serviceAccount","documentId":DOC,"sheetName":SHEET,"filtersUI":{"values":[]},"options":{}},[440,120],GS,alwaysOutputData=True)
node("Логика","n8n-nodes-base.code",2,{"jsCode":open(D+'logika.js').read()},[660,120])
node("Есть что записать?","n8n-nodes-base.if",2,{"conditions":{"options":{"caseSensitive":True,"leftValue":"","typeValidation":"loose"},"conditions":[{"leftValue":"={{ $json.upserts.length }}","rightValue":0,"operator":{"type":"number","operation":"gt"}}],"combinator":"and"},"options":{}},[880,120])
node("Строки для записи","n8n-nodes-base.code",2,{"jsCode":"// каждая строка — отдельный элемент для записи в лист\nreturn $('Логика').first().json.upserts.map(r => ({ json: r }));"},[1100,40])
node("Записываем в календарь","n8n-nodes-base.googleSheets",4,{"authentication":"serviceAccount","operation":"appendOrUpdate","documentId":DOC,"sheetName":SHEET,
  "columns":{"mappingMode":"defineBelow","matchingColumns":["id"],"value":{c:"={{ $json."+c+" }}" for c in COLS}},"options":{}},[1320,40],GS)
node("Сообщения","n8n-nodes-base.code",2,{"jsCode":"// что отправить в Телеграм — по одному элементу на сообщение\nreturn $('Логика').first().json.messages.map(m => ({ json: m }));"},[1540,120])
types=['send','sendImport','editImport','edit','card','editCard','answer']
node("Что отправить?","n8n-nodes-base.switch",3,{"rules":{"values":[{"conditions":{"options":{"caseSensitive":True,"leftValue":"","typeValidation":"loose"},"conditions":[{"leftValue":"={{ $json.type }}","rightValue":t,"operator":{"type":"string","operation":"equals"}}],"combinator":"and"}} for t in types]},"options":{}},[1760,120])
y=-240
def tgnode(name,params,y):
    return node(name,"n8n-nodes-base.telegram",1.2,params,[2000,y],TG,onError="continueRegularOutput")
tgnode("Отправляем текст",{"chatId":"={{ $json.chatId }}","text":"={{ $json.text }}","additionalFields":TXT},-240)
tgnode("Отправляем список на проверку",{"chatId":"={{ $json.chatId }}","text":"={{ $json.text }}","replyMarkup":"inlineKeyboard","inlineKeyboard":IMP,"additionalFields":TXT},-80)
tgnode("Обновляем проверку списка",{"operation":"editMessageText","messageType":"message","chatId":"={{ $json.chatId }}","messageId":"={{ $json.messageId }}","text":"={{ $json.text }}","replyMarkup":"inlineKeyboard","inlineKeyboard":IMP,"additionalFields":TXT_EDIT},80)
tgnode("Правим сообщение",{"operation":"editMessageText","messageType":"message","chatId":"={{ $json.chatId }}","messageId":"={{ $json.messageId }}","text":"={{ $json.text }}","additionalFields":TXT_EDIT},240)
tgnode("Отправляем карточку",{"chatId":"={{ $json.chatId }}","text":"={{ $json.text }}","replyMarkup":"inlineKeyboard","inlineKeyboard":CARD,"additionalFields":TXT},400)
tgnode("Обновляем карточку",{"operation":"editMessageText","messageType":"message","chatId":"={{ $json.chatId }}","messageId":"={{ $json.messageId }}","text":"={{ $json.text }}","replyMarkup":"inlineKeyboard","inlineKeyboard":CARD,"additionalFields":TXT_EDIT},560)
tgnode("Закрываем часики на кнопке",{"resource":"callback","operation":"answerQuery","queryId":"={{ $json.queryId }}","additionalFields":{"text":"={{ $json.text }}"}},720)
node("Заметка","n8n-nodes-base.stickyNote",1,{"content":"## Studio Calendar\nОтдельный бот (@studio_calendar_1976_bot), с Редактором не пересекается.\n\nВсё решает узел «Логика»: разбор списков, склейка повторов, статусы. Нейросети нет.\nДанные — лист «Календарь» в основной таблице (колонки: "+", ".join(COLS)+").\nНезавершённые списки (до кнопки «Добавить») хранятся в памяти воркфлоу 3 дня.\n\nПо понедельникам в 9:00 бот сам присылает поводы на две недели.","height":320,"width":520,"color":4},[0,-420])

link("Telegram Trigger","Это владелец?")
link("Это владелец?","Читаем календарь",0)
link("Каждый понедельник","Читаем календарь")
link("Читаем календарь","Логика")
link("Логика","Есть что записать?")
link("Есть что записать?","Строки для записи",0)
link("Есть что записать?","Сообщения",1)
link("Строки для записи","Записываем в календарь")
link("Записываем в календарь","Сообщения")
link("Сообщения","Что отправить?")
for i,n in enumerate(["Отправляем текст","Отправляем список на проверку","Обновляем проверку списка","Правим сообщение","Отправляем карточку","Обновляем карточку","Закрываем часики на кнопке"]):
    link("Что отправить?",n,i)
wf={"name":"11_Календарь","nodes":nodes,"connections":conns,"active":False,"settings":{"executionOrder":"v1","callerPolicy":"workflowsFromSameOwner"},"pinData":{},"tags":[]}
json.dump(wf,open('/home/user/N8N/workflows/11_Календарь.json','w'),ensure_ascii=False,indent=2)
print('nodes',len(nodes))
