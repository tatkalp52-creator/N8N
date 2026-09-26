const ctx = $('Контекст проекта').first().json;
const vhod = $('Вход редактора').first().json;
const kb = $('Собираем знания канала').first().json;
let prevText = '';
try { prevText = $('Прошлые главы').first().json.text || ''; } catch (e) {}
const row = ctx.row || {};
const state = tbParseState(row.sys_EditorState);

// Разговор: либо уже есть у проекта, либо только что создан.
let conversationId = String(row.sys_ConversationId || '').trim();
let isNewConversation = false;
if (!conversationId) {
  try { conversationId = $('OpenAI: создаём разговор').first().json.id; isNewConversation = true; } catch (e) {}
}
if (!conversationId) throw new Error('Нет conversation_id для проекта ' + ctx.projectId);
const pendingCallId = isNewConversation ? '' : String(row.sys_PendingToolCallId || '').trim();

let userImageUrl = '';
try { userImageUrl = $('Фото в base64').first().json.userImageUrl || ''; } catch (e) {}

// ── Варианты картинки ──
let variants = [];
try { variants = JSON.parse(row.ai_ImageVariants || '[]'); } catch (e) { variants = []; }
if (!Array.isArray(variants)) variants = [];
const approvedUrl = vhod.approvedUrl;
const approvedVariant = variants.find(v => v.url === approvedUrl);

// ── Какие картинки показать модели в этом ходе ──
// Всё, что модель уже видела в этом разговоре, остаётся в его истории —
// повторно не прикладываем (иначе разговор разбухает от одних и тех же
// картинок). Прикладываем только новое: свежее фото автора, новые варианты,
// а на первом ходе — style guide и референсы канала.
const seen = new Set(state.seenImages || []);
const images = [];
function addImage(url, label) {
  if (!url || seen.has(url)) return;
  images.push({ url, label });
  seen.add(url);
}
if (kb.styleGuideUrl) addImage(kb.styleGuideUrl, 'style guide канала');
(kb.referenceUrls || []).forEach((u, i) => addImage(u, 'референс канала ' + (i + 1)));
variants.forEach(v => addImage(v.url, 'вариант ' + v.n + ' этого проекта'));
if (approvedUrl && !approvedVariant) addImage(approvedUrl, 'согласованная картинка этого проекта');

// ── Карточка состояния проекта: единственный источник правды ──
function line(s) { return s; }
const variantLines = variants.length
  ? variants.map(v => `  • Вариант ${v.n}${approvedVariant && approvedVariant.n === v.n ? ' — СОГЛАСОВАН' : ''}: ${(v.dallePrompt || '').slice(0, 300)}`).join('\n')
  : '  (ещё ни одного варианта)';
const tbLines = TB_ITEMS.map(it => {
  const status = state.agreed[it.n] ? 'СОГЛАСОВАНО' : (state.set[it.n] ? 'предложено, ждёт согласования' : 'ещё не предлагалось');
  const text = tbItemText(state, it.n);
  return `  ${it.n}. ${it.name} [${status}]` + (text ? `\n${text.split('\n').map(l => '     ' + l).join('\n')}` : '');
}).join('\n');

const stateCard = [
  `Проект ${ctx.projectId}, статус в таблице: «${vhod.status || 'пусто'}».`,
  `Картинка: ${approvedUrl ? 'согласована' + (approvedVariant ? ' (вариант ' + approvedVariant.n + ')' : '') : 'ещё НЕ согласована'}.`,
  'Варианты:',
  variantLines,
  '',
  'Текстовый блок:',
  tbLines,
  '',
  `Нужное число тайм-кодов (из таблицы): ${kb.timecodeCount}.`,
  `Ссылка на треки: ${String(row.sys_AudioZipUrl || '').trim() ? 'уже прислана' : 'ещё не прислана'}.`,
  row.ai_UserBrief ? `Изначальный бриф автора: ${row.ai_UserBrief}` : '',
].filter(x => x !== '').join('\n');

const instructions = `Ты — редактор канала "${ctx.sheetName}". Ты ведёшь весь выпуск в одном разговоре с автором: картинку и текстовый блок. Как говорить, что и как писать — всё это правила канала в базе ниже (SystemPrompt по этапам, паспорта, правила упаковки, заметки). Здесь — только то, как устроена сама система.

КАК УСТРОЕН ВЫПУСК
Картинка → текстовый блок из 8 пунктов → автор жмёт финальную кнопку "✅ Согласовано" под сводкой → всё записывается в таблицу → когда придёт ссылка на треки, видео собирается автоматически. Между этапами можно двигаться свободно в любую сторону, по смыслу слов автора — кодовых слов и переключений нет.

КАРТОЧКА СОСТОЯНИЯ (в самом конце) — источник правды о том, что нарисовано, согласовано и записано; обновляется перед каждым твоим ответом. Если она расходится с тем, что ты помнишь из разговора, — верь карточке.

ИНСТРУМЕНТЫ. За один ответ — не больше одного инструмента; если ничего не нужно — просто отвечай текстом.
- start_drawing — нарисовать НОВЫЙ пронумерованный вариант. Художник получает ровно твоё описание сцены и референсы канала из таблицы.
- request_revision — правка уже нарисованного варианта. isNewVariant: false — тот же вариант заменяется на месте; true — результат сохраняется следующим вариантом, прежний остаётся. Художник получает ровно твоё описание правки, текущую картинку и референсы канала. Если вариантов несколько и неясно, какой правим, — уточни номер.
- approve_image — автор согласовала картинку. В ЭТОМ ЖЕ вызове сразу передай в items все 8 пунктов текстового блока — автор получит подтверждение и первый вариант текста одним сообщением. Если вариантов несколько и номер не прозвучал — переспроси. Под каждой картинкой у автора своя кнопка "✅"; если она её нажала, придёт служебное сообщение — тогда вызови approve_image с этим номером и тоже сразу с items.
- update_text_block — предложить, изменить или отметить согласованными пункты текстового блока.
- update_communication_notes — сохранить заметки в базу канала (колонка EditorNotes). Передавай ПОЛНЫЙ обновлённый текст заметок: существующие + новое.
Если по смыслу твоих слов что-то согласовано, начато или изменено, а инструмент не вызван — вызови его в этом же ответе.
Если правила канала противоречат друг другу — скажи об этом автору, чтобы она поправила таблицу.

ТЕКСТОВЫЙ БЛОК: 8 ПУНКТОВ, НОМЕРА ЗАКРЕПЛЕНЫ
1. Оверлей (текст + позиция left/right/center). 2. Название. 3. Описание. 4. Тайм-коды. 5. Подвал. 6. Хэштеги. 7. Теги. 8. Закреплённый комментарий.
Содержание, язык и стиль каждого пункта — по правилам канала в базе ниже. Технические требования системы:
- Оверлей или закреплённый комментарий не нужны — передай "-".
- Тайм-кодов — ровно столько, сколько указано в карточке.
- Подвал обязательно содержит буквальную метку [Timecodes] — туда сборщик вставит тайм-коды.
- Описание автоматически переводится на английский в конце; перевод показывается автору в финальной сводке.
- К оверлею, названию, тайм-кодам и закреплённому комментарию передавай в ruTranslations русский перевод — система покажет его автору в скобках рядом; в таблицу и на YouTube он не идёт.
Как работать с блоком:
- После update_text_block система сама покажет автору пронумерованные пункты, ждущие согласования, — в messageToUser их не переписывай.
- В items — только пункты, которые предлагаешь или меняешь сейчас (пустая строка = без изменений). Изменённый пункт снова ждёт согласования.
- В agreedItems — ТОЛЬКО номера пунктов, которые автор явно одобрила (по номеру, названию или общим «всё ок» — тогда все показанные). Передумала насчёт согласованного — в reopenItems.
- Когда согласованы все 8, система сама пришлёт сводку с одной кнопкой "✅ Согласовано". Показать блок или сводку заново — update_text_block без изменений.
- Правка после "Утверждено" снимает этот статус; система предупредит автора.

КАРТИНКИ В ЭТОМ РАЗГОВОРЕ
Вместе с сообщениями тебе показываются настоящие картинки: фото автора (если прислала), style guide и референсы канала, новые варианты этого проекта. Каждая показывается один раз и дальше остаётся в истории разговора.

БАЗА КАНАЛА (персонаж, локации, стиль, правила упаковки, заметки — используй по смыслу подписи каждого блока):
${kb.knowledgeText}
${prevText ? `

ПРОШЛЫЕ ГЛАВЫ — последние выпуски канала, как их согласовала автор (для сквозных нитей и продолжения голоса; сюжеты не повторяй, но можешь опереться на них: то, что было раньше, продолжается). Старые выпуски можно найти поиском по памяти канала (file_search).
${prevText}` : ''}

КАРТОЧКА СОСТОЯНИЯ ПРОЕКТА (актуальна на этот ход):
${stateCard}`;

// ── Сообщение автора + новые картинки ──
const content = [{ type: 'input_text', text: vhod.userText }];
if (userImageUrl) {
  content.push({ type: 'input_text', text: '(Фото, которое автор прислала в этом сообщении:)' });
  content.push({ type: 'input_image', image_url: userImageUrl });
}
for (const img of images) {
  content.push({ type: 'input_text', text: `(Служебно: ${img.label})` });
  content.push({ type: 'input_image', image_url: img.url });
}

const input = [];
if (pendingCallId) {
  input.push({ type: 'function_call_output', call_id: pendingCallId, output: 'Выполнено. Актуальный результат — в карточке состояния проекта.' });
}
input.push({ role: 'user', content: content.length > 1 ? content : vhod.userText });

const TEXT_BLOCK_ITEMS = { type: 'object', description: 'Только пункты, которые предлагаешь или меняешь сейчас. Пустая строка или отсутствие поля — без изменений.', properties: {
        overlayText: { type: 'string', description: '1. Оверлей; "-" если не нужен' },
        overlayPosition: { type: 'string', description: '1. Позиция оверлея: left, right или center' },
        title: { type: 'string', description: '2. Название' },
        description: { type: 'string', description: '3. Описание' },
        timecodes: { type: 'array', items: { type: 'string' }, description: '4. Названия тайм-кодов, ровно столько, сколько в карточке' },
        footer: { type: 'string', description: '5. Подвал, обязательно с меткой [Timecodes]' },
        hashtags: { type: 'string', description: '6. Хэштеги' },
        tags: { type: 'string', description: '7. Теги через запятую' },
        pinnedComment: { type: 'string', description: '8. Закреплённый комментарий; "-" если не нужен' },
      } };

const RU_TRANSLATIONS = { type: 'object', description: 'Русский перевод для показа автору (в таблицу и на YouTube не идёт): для оверлея, названия, тайм-кодов и закреплённого комментария — к тем пунктам, что передаёшь сейчас.', properties: {
  overlayText: { type: 'string' },
  title: { type: 'string' },
  timecodes: { type: 'array', items: { type: 'string' }, description: 'Переводы в том же порядке, что и тайм-коды' },
  pinnedComment: { type: 'string' },
} };

const tools = [
  { type: 'web_search' },
  ...(kb.vectorStoreId ? [{ type: 'file_search', vector_store_ids: [kb.vectorStoreId] }] : []),
  {
    type: 'function', name: 'start_drawing',
    description: 'Нарисовать НОВЫЙ вариант сцены.',
    parameters: { type: 'object', properties: {
      dallePrompt: { type: 'string', description: 'Описание сцены для художника' },
      messageToUser: { type: 'string', description: 'Реплика автору' },
    }, required: ['dallePrompt', 'messageToUser'] },
  },
  {
    type: 'function', name: 'request_revision',
    description: 'Поправить уже нарисованный вариант. Если вариантов больше одного — обязательно укажи variantNumber.',
    parameters: { type: 'object', properties: {
      variantNumber: { type: 'integer', description: 'Номер варианта, который правишь' },
      isNewVariant: { type: 'boolean', description: 'false — точечная правка того же кадра (заменяет его на месте); true — структурное изменение, сохраняется следующим вариантом. Если сомневаешься — false.' },
      revisionInstruction: { type: 'string', description: 'Описание правки для художника' },
      messageToUser: { type: 'string', description: 'Реплика автору' },
    }, required: ['revisionInstruction', 'isNewVariant', 'messageToUser'] },
  },
  {
    type: 'function', name: 'approve_image',
    description: 'Автор согласовала картинку. Если вариантов больше одного — укажи variantNumber.',
    parameters: { type: 'object', properties: {
      variantNumber: { type: 'integer', description: 'Номер согласованного варианта' },
      targetBrightness: { type: 'integer', description: 'Необязательно: целевая яркость кадра 0-255.' },
      items: { ...TEXT_BLOCK_ITEMS, description: 'Все 8 пунктов текстового блока — первый вариант текста к этой картинке.' },
      ruTranslations: RU_TRANSLATIONS,
      messageToUser: { type: 'string', description: 'Реплика автору (блок система покажет отдельно)' },
    }, required: ['items', 'messageToUser'] },
  },
  {
    type: 'function', name: 'update_text_block',
    description: 'Предложить/изменить пункты текстового блока и/или отметить пункты, которые автор явно согласовала. Без изменений — чтобы заново показать блок или сводку.',
    parameters: { type: 'object', properties: {
      items: TEXT_BLOCK_ITEMS,
      ruTranslations: RU_TRANSLATIONS,
      agreedItems: { type: 'array', items: { type: 'integer' }, description: 'Номера пунктов (1-8), которые автор ЯВНО одобрила' },
      reopenItems: { type: 'array', items: { type: 'integer' }, description: 'Номера ранее согласованных пунктов, которые автор решила пересмотреть' },
      messageToUser: { type: 'string', description: 'Реплика автору (сам блок система покажет отдельно)' },
    }, required: ['messageToUser'] },
  },
  {
    type: 'function', name: 'update_communication_notes',
    description: 'Сохранить заметки в базу канала.',
    parameters: { type: 'object', properties: {
      notes: { type: 'string', description: 'Полный обновлённый текст заметок (существующие + новое)' },
      messageToUser: { type: 'string', description: 'Реплика автору' },
    }, required: ['notes', 'messageToUser'] },
  },
];

const requestBody = {
  model: 'gpt-5',
  conversation: conversationId,
  instructions,
  input,
  tools,
  tool_choice: 'auto',
  parallel_tool_calls: false,
  truncation: 'auto',
};

return [{
  json: {
    requestBody,
    conversationId,
    newSeenImages: Array.from(seen),
    projectId: ctx.projectId,
    chatId: ctx.chatId,
    sheetName: ctx.sheetName,
    channelKey: ctx.channelKey,
  }
}];
