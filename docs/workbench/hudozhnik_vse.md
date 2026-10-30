# Художник — всё, что он получает, в одном месте

Скопировано из таблицы Templates 17.10, в таблице ничего не менялось.

**Как это доходит до художника (по коду workflow 12):**
- образцы (картинки) — всегда, как изображения;
- правила — приклеиваются перед твоим брифом к каждой новой картинке (к правкам — нет);
- места 📍 — только блок, чьё слово есть в брифе (с картинкой места);
- модель — из листа «Этапы» (gpt-image-2); tmpl_ImageModel — запасная;
- **паспорт персонажа (🖋_tmpl_CharacterPassport) художнику НЕ идёт** — на нём только значок ручки.

## 🎨_tmpl_ReferenceImages  (ячейка H2, 142 знаков)
Образцы (ссылки на картинки).
```text
https://drive.google.com/file/d/1UIGLQhSptHVOrvRK_wsujWYJcPGjTe84/view

https://drive.google.com/file/d/1bhkS6ALdSgd7krau333bEWtwXLKpWmdN/view
```

## 🎨_tmpl_ArtistRules  (ячейка I2, 1842 знаков)
Правила — идут текстом перед брифом.
```text
Это рисованная книжная иллюстрация в манере, палитре и фактуре референсов.

Это книжная иллюстрация для взрослого читателя, не детская: в ней уместны тонкий юмор, намёки и аллюзии, которые считывает взрослый, без пошлости.

Пингви — взрослый, но ростом примерно с пятилетнего ребёнка. Он живёт в обычном человеческом мире, который ему великоват, но вещи вокруг для него привычны, а неловкости из-за роста он принимает с юмором и лёгкой самоиронией. Пингви ходит босиком. Питомцы в сцене — те, что названы в задании.

Глаза у Пингви всегда закрыты, на щеках лёгкий румянец. Он в моменте: обращён к тому, что делает или что его радует, голова и клюв повёрнуты туда; закрытые глаза — это его способ быть в моменте.

На картинке он не главный и не нарисован крупно: он естественная, небольшая часть иллюстрации — маленький и хрупкий в большом мире. Пингви небольшой: до четверти высоты изображения, по вертикали, по короткой стороне; сидя и лёжа он такой же величины, как стоя. Обычно он в левой или правой половине картинки, не в центре. Это подчёркивает его рост и скромный, обаятельный характер.

Рисунок доходит до самых краёв.

Людей лучше не рисовать; если они всё же есть — только вдали и силуэтом.

Названия кафе, магазинов и марок на надписях и вывесках — фантазийные. Все надписи на картинке — по-английски: вывески, таблички, подписи ингредиентов и шагов. Если при рисовании надписей остаётся много пустого места, буквы можно чуть увеличить или закрыть это место орнаментом по духу выпуска и сезону.

Мотивационные надписи и таблички — только как небольшие юмористические вставки, с юмором, и не злоупотреблять ими. На картинке достаточно одной шутливой надписи.

Картинка слоистая: помимо главного сюжета в ней есть несколько мелких деталей, которые по очереди цепляют взгляд. Их немного, в меру: это общее пожелание, а не требование.
```

## 🎨📍_tmpl_LocationImages  (ячейка J2, 1531 знаков)
Места — блок «НАЗВАНИЕ: слова-триггеры», ссылка на картинку, подпись.
```text
SUBWAY: метро, поезд, subway
https://drive.google.com/file/d/1IIMKOYjHimRH_XFgbzflA4psSeoRGoBt/view
the subway: the place and how Pengui sits there

KITCHEN: плит, варит, суп, гайд, рецепт, stove
https://drive.google.com/file/d/1yVQBy-qWsvOacoxQrFK2Dlr2adYxMbjR/view
Pengui's kitchen as it is: the stove, the sink under the window, the shelves and the fridge, and how big Pengui is among them; the things on the stove and the worktop change with the story

KITCHEN NOOK: кухн, уголок, kitchen
The place — the cosy eating corner of Pengui's kitchen, seen from the front, from just above the height of the table top. Along the back wall, under a window with brownstones and trees outside in the colours of the season, a short, straight, soft blue sofa-bench; the window has a deep, wide windowsill where the birdcage stands. The corner is closed on the left by the side of a soft mustard-yellow retro fridge and on the right by a small bookshelf, where the round fishbowl lives. Right in front of Pengui, a roomy round kitchen table where he eats, reads and writes his letters — big enough for a plate, a cup, books and postcards, even the birdcage when he brings it over. The furniture is human-sized, a little too big for Pengui.
https://drive.google.com/file/d/1UeM-5742WN6UUB7lBWFJ6lNNi0Bpe8Lu/view
Pengui's kitchen nook as it is: the fridge, the window with its wide windowsill, the blue bench, the round table and the bookshelf, and how big Pengui is among them; the things on the table and the windowsill change with the story
```

## 🎨_tmpl_DalleExamples  (ячейка K2, 0 знаков)

```text
(пусто)
```

## tmpl_ImageModel  (ячейка B2, 11 знаков)
Запасная модель (основная — в листе «Этапы»).
```text
gpt-image-2
```


---
# Чего у художника нет, но есть у писателя (для сравнения)

## 🖋_tmpl_CharacterPassport  (ячейка N2, 1961 знаков)
Паспорт персонажа — сейчас только у писателя.
```text
Pengui is a small, independent adult penguin living his own quiet life in New York. He works at the library and loves books and reading, music, walks in the parks and discovering interesting little corners of the city, and fishing — sitting with his rod on a little bridge over a pond is one of his happiest places. He's serious about ordinary things: his red knitted scarf; his headphones when he's out and about — on the subway, walking, in transit — while at home the music comes from his record player or the radio, or he simply hums to himself; his love of herring (yes, even for breakfast 🙂); his yellow canary and his little red fish; his grandmother, whom he visits now and then. He rides the subway and sometimes falls asleep on it.

He is shy and honest, notices small things and enjoys them, and does small kind things. He is tender-hearted and a little vulnerable, yet brave: he thinks things over, has his doubts, and still goes ahead — calmly, without drama.

He is good-natured and usually in good spirits. He likes to cook, often from his grandmother's recipes. He is a good neighbour: friendly to the people and animals around him, ready to share a slice of pie or lend a hand. His grandmother lives off-page: she appears in his memories, recipes, letters and visits.

The world around him is human-sized, a little too big for him. He has adapted to it the way short people do: most things he reaches on tiptoe or with a little hop, and here and there at home a step stool or a small ladder stands where he needs it. He has fitted his small imperfections into the world and meets little troubles with self-irony. When the world gets inconvenient, he can smile at himself about it. If other people appear in a scene, they stay soft and distant in the background — quiet shapes; the picture is about Pengui.

Height: about 110 cm — a short adult, not a child. Standing, his head is at about the chest of an adult; he sees over a table top easily.
```

## 🖋_tmpl_LocationPassports  (ячейка O2, 2337 знаков)
Паспорта мест (описания комнат) — сейчас только у писателя; у художника места — в 🎨📍 выше.
```text
LIVING ROOM — Fixed: a velvet armchair, a window with a steady city view, a wood bookshelf. Everything else — lamp, rug, small objects — is free to change with the mood. 
KITCHEN — Pengui's small New York kitchen, seen from the front and a little from above, the way you look in from the doorway, so you can see what is in a cup on the table. Everything here is human-sized, a little too big for Pengui. On the left, under a window with brownstones outside, a deep sink in a wooden worktop with a dish rack beside it; the worktop runs along the back wall over sage-green lower cabinets, with open wooden shelves above it: a few pots, cups on hooks, some jars. Against the back wall, a rounded mustard-yellow retro fridge with postcards on its door. Next to the worktop, a stove with a moka pot. On the right, by a second window, the cosy nook where Pengui eats, reads and writes: a blue bench along the wall and a small table in front of it; his birdcage stands on that windowsill. How each thing looks and the small details are free. 
KITCHEN NOOK — the cosy eating corner of Pengui's kitchen, seen from the front, from just above the height of the table top. Along the back wall, under a window with brownstones and trees outside in the colours of the season, a short, straight, soft blue sofa-bench; the window has a deep, wide windowsill where the birdcage stands. The corner is closed on the left by the side of a soft mustard-yellow retro fridge and on the right by a small bookshelf, where the round fishbowl lives. Right in front of Pengui, a roomy round kitchen table where he eats, reads and writes his letters — big enough for a plate, a cup, books and postcards, even the birdcage when he brings it over. The furniture is human-sized, a little too big for Pengui. 
BEDROOM — Fixed: a bed with one small blue pillow, a round fish bowl nearby. Everything else is free. 
BATHROOM — Fixed: a clawfoot bathtub with a shower head mounted above it, a shower curtain with a herring print (this curtain always belongs only to the tub, never to the window); a sink, a mirror, a small step-stool; a window with blinds (not curtains, to avoid confusion with the tub's shower curtain). Everything else — plants, candles, small objects — is free. 
BALCONY — Fixed: a narrow balcony with a railing, a folding chair. Everything else is free.
```
