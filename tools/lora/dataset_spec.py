# Набор для обучения LoRA Пингви — ТОЛЬКО картинки из папки Visual reference (решение автора).
# (id файла на Диске, рамка x0,y0,x1,y1 в пикселях оригинала, подпись).
# В подписи всё, что меняется от картинки к картинке (наушники, поза, место), — чтобы модель
# не прилипла к этому и это можно было просить или не просить.
T = "pengui, a small penguin with a red knitted scarf, eyes closed, rosy cheeks, soft colored pencil storybook illustration"
CHALLAH = "1613T_hq9nk9YyiPWJDjzKyd8jBjwZPrs"
BIBLE = "1yy52ryUeE8qr1YdXcQK856U6eSz3XyZe"
STRETCH = "1bhkS6ALdSgd7krau333bEWtwXLKpWmdN"
GUIDE = "1UIGLQhSptHVOrvRK_wsujWYJcPGjTe84"
BEACH = "1h7M_lKxgLIThWqwlbwO2mLPlaohBCdK8"
METRO = "1IIMKOYjHimRH_XFgbzflA4psSeoRGoBt"
HERRING = "14HDl8xuGTDIC89xYp262qABqQD-tJ0jx"
ITEMS = [
    (CHALLAH, (770, 230, 960, 420), f"{T}, stirring a bowl with a wooden spoon, no headphones, beige paper"),
    (CHALLAH, (1000, 230, 1190, 420), f"{T}, mixing dough in a bowl, a bag of flour, no headphones, beige paper"),
    (CHALLAH, (1230, 230, 1420, 420), f"{T}, kneading dough on a floured table, no headphones, beige paper"),
    (CHALLAH, (1440, 230, 1630, 420), f"{T}, covering a bowl with a checked towel, no headphones, beige paper"),
    (CHALLAH, (740, 672, 960, 892), f"{T}, shaping a spiral of dough, no headphones, beige paper"),
    (CHALLAH, (980, 668, 1200, 888), f"{T}, brushing a round loaf with egg wash, no headphones, beige paper"),
    (CHALLAH, (1220, 655, 1475, 910), f"{T}, taking a baked round bread out with oven mitts, a window with the city, no headphones, beige paper"),
    (BIBLE, (15, 645, 168, 822), f"{T}, standing, front view, no headphones, light paper"),
    (BIBLE, (190, 645, 338, 822), f"{T}, standing, side view, no headphones, light paper"),
    (BIBLE, (348, 645, 495, 822), f"{T}, standing, back view, no headphones, light paper"),
    (BIBLE, (535, 700, 870, 940), f"{T}, tiny in a snowy city street among tall people, carrying a paper bag, no headphones"),
    (BIBLE, (900, 700, 1055, 940), f"{T}, sitting at a cafe table with a cup, no headphones"),
    (BIBLE, (1055, 700, 1210, 940), f"{T}, reading a book among library shelves, no headphones"),
    (STRETCH, (440, 80, 700, 430), f"{T}, wearing headphones, standing, tilting his head, beige paper"),
    (STRETCH, (760, 80, 1110, 430), f"{T}, wearing headphones, stretching his wings wide, beige paper"),
    (STRETCH, (1100, 80, 1370, 430), f"{T}, wearing headphones, bending to the side, beige paper"),
    (STRETCH, (90, 600, 360, 828), f"{T}, wearing headphones, curled forward on the floor, beige paper"),
    (STRETCH, (410, 510, 690, 850), f"{T}, wearing headphones, sitting on the floor, twisting, beige paper"),
    (STRETCH, (780, 580, 1090, 840), f"{T}, wearing headphones, lying on his back holding his feet, beige paper"),
    (STRETCH, (1100, 508, 1370, 838), f"{T}, wearing headphones, standing tall, beige paper"),
    (GUIDE, (430, 150, 1060, 780), f"{T}, wearing headphones, dozing on a subway seat, a newspaper, the city in the window"),
    (BEACH, (450, 180, 1134, 864), f"{T}, wearing headphones, lounging on a striped beach chair under a beach umbrella, a tin of sardines, an old suitcase, sand and sea"),
    (METRO, (560, 180, 1220, 840), f"{T}, wearing headphones, sitting on a subway seat, a newspaper slipping down"),
    (HERRING, (230, 220, 750, 740), f"{T}, hurrying along a snowy street at night with a paper bag of herring and bread, scarf flying, warm shop window light"),
]
