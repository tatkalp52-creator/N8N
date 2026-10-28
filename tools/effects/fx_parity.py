# Сверка разбора строк оживления до и после переноса слов в таблицу (лист «Слова»).
# python3 tools/effects/fx_parity.py <before.json> <after.json>
import sys, json
K = {"густота": "density", "толщина": "thickness", "высота": "height", "скорость": "speed", "завитки": "curls",
     "прозрачность": "transparency", "ореол": "halo", "раскачка": "sway", "яркость": "brightness", "капли": "drops",
     "частота": "frequency", "размер": "size", "мерцание": "flicker", "отсвет": "glow", "пламя": "flame", "разлив": "reach"}
L = {"Б": "B", "В": "V", "Г": "G"}
a, b = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
bad = 0
for i, (x, y) in enumerate(zip(a, b)):
    for e in x["effects"]:
        e[2] = {K.get(k, k): v for k, v in e[2].items()}
    x["covers"] = [[L.get(c[0], c[0])] + c[1:] for c in x["covers"]]
    for key in x:
        if x[key] != y[key]:
            bad += 1
            print("РАЗНИЦА", i, key, "\n  было:", json.dumps(x[key], ensure_ascii=False)[:600], "\n  стало:", json.dumps(y[key], ensure_ascii=False)[:600])
print("строк:", len(a), "различий:", bad)
sys.exit(1 if bad or len(a) != len(b) else 0)
