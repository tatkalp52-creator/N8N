#!/usr/bin/env python3
"""Сторож правила автора: в коде только механика и обращения к категориям, всё остальное — в таблице.

Ищет в «восьмёрке» (12), 04 и сборщике то, чего в коде быть не должно:
  ЗАПАС   — запасное значение вместо пустой колонки (`|| 'gpt-5'`, `data.get("x", 64)`, `_float_or(v, 90)`);
  СЛОВАРЬ — слова о содержании в коде (списки, словари, шаблоны с русскими словами: «пар», «клён»…);
  МОДЕЛЬ  — имя модели в коде;
  КАНАЛ   — название канала в коде.

Разрешённое (техника: тайм-ауты, пределы YouTube и Telegram, команды автора системе) — только
по одному, с причиной, в allow.txt. Новое нарушение сторож не пропустит, даже если «очень надо».

    python3 tools/guard/guard.py          # итог: «нарушений: 0» — иначе работа не готова
"""
import ast
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
ALLOW = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'allow.txt')
CYR = re.compile(r'[а-яё]', re.I)
CHANNEL = re.compile(r'pengui|пингви|jazzt', re.I)
MODEL = re.compile(r'\b(gpt-[\w.-]+|dall-e[\w-]*|o\d-[\w-]+)\b', re.I)


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()[:160]


# ── JavaScript: Code-узлы 12 (gen12/js и механика из gen10/js) и 04 ──
def strip_js_comments(src):
    out = []
    for line in src.split('\n'):
        if line.strip().startswith('//'):
            out.append('')
            continue
        # хвостовой комментарий: « // …» вне строки (грубо, но кавычки с // у нас только в URL)
        m = re.search(r'(^|\s)//(?![^\'"`]*[\'"`]\s*[,);\]}])', line)
        out.append(line[:m.start()] if m and 'http' not in line[:m.start() + 3] else line)
    return '\n'.join(out)


JS_FALLBACK = re.compile(r"\|\|\s*('(?:[^'\\]|\\.)+'|\"(?:[^\"\\]|\\.)+\"|-?\d+(?:\.\d+)?)(?!\s*[:?])")
JS_REGEX = re.compile(r"(?<![\w)\]])/((?:[^/\\\n]|\\.)+)/[gimsuy]*")
JS_ARRAY_WORDS = re.compile(r"\[\s*(?:'[^'\n]*'\s*,\s*)*'[^'\n]*[а-яё][^'\n]*'(?:\s*,\s*'[^'\n]*')+\s*\]", re.I)


def scan_js(where, src):
    found = []
    code = strip_js_comments(src)
    for m in JS_FALLBACK.finditer(code):
        lit = m.group(1)
        if lit in ("''", '""', '0'):
            continue
        found.append(('ЗАПАС', where, norm(code[max(0, m.start() - 60):m.end()])))
    for m in JS_REGEX.finditer(code):
        if CYR.search(m.group(1)):
            found.append(('СЛОВАРЬ', where, norm(m.group(0))))
    for m in JS_ARRAY_WORDS.finditer(code):
        found.append(('СЛОВАРЬ', where, norm(m.group(0))))
    for m in MODEL.finditer(code):
        found.append(('МОДЕЛЬ', where, norm(code[max(0, m.start() - 40):m.end() + 10])))
    for m in CHANNEL.finditer(code):
        found.append(('КАНАЛ', where, norm(code[max(0, m.start() - 40):m.end() + 20])))
    return found


def js_sources():
    gen12 = os.path.join(ROOT, 'tools', 'gen12')
    g = open(os.path.join(gen12, 'gen12.py'), encoding='utf-8').read()
    used = set(re.findall(r"'([a-z0-9_]+\.js)'", g)) | {'lib12.js'}
    for name in sorted(used):
        for d in (os.path.join(gen12, 'js'), os.path.join(ROOT, 'tools', 'gen10', 'js')):
            p = os.path.join(d, name)
            if os.path.exists(p):
                yield 'gen12/' + name if d.endswith(os.path.join('gen12', 'js')) else 'gen10/' + name, open(p, encoding='utf-8').read()
                break
    wf = json.load(open(os.path.join(ROOT, 'workflows', '04_Video.json'), encoding='utf-8'))
    for n in wf['nodes']:
        p = n.get('parameters', {})
        for key in ('jsCode', 'jsonBody'):
            if isinstance(p.get(key), str) and p[key]:
                yield '04/' + n['name'], p[key]


# ── Python: сборщик ──
def const(node):
    return isinstance(node, ast.Constant) and node.value is not None and node.value != '' and not isinstance(node.value, bool)


def has_cyr_str(node):
    return any(isinstance(x, ast.Constant) and isinstance(x.value, str) and CYR.search(x.value) for x in ast.walk(node))


def scan_py(where, src):
    found = []
    lines = src.split('\n')
    tree = ast.parse(src)
    seen_coll = set()
    for node in ast.walk(tree):
        seg = lambda n: norm(lines[n.lineno - 1]) if hasattr(n, 'lineno') else ''
        if isinstance(node, ast.Call):
            f = node.func
            fname = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else '')
            # data.get("x", 64) — запасное значение
            if fname == 'get' and len(node.args) == 2 and const(node.args[1]):
                found.append(('ЗАПАС', where, seg(node)))
            # _float_or(v, 90) / _f("x", 24) / _num("x", 3) / _fade("x", 2)
            if fname in ('_float_or', '_f', '_num', '_fade') and len(node.args) == 2 and const(node.args[1]):
                found.append(('ЗАПАС', where, seg(node)))
            # re.search(r"листья…") — слова о содержании в шаблоне
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == 're' and node.args \
                    and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str) and CYR.search(node.args[0].value):
                found.append(('СЛОВАРЬ', where, seg(node)))
        # data.get("x") or 7000 — тоже запас
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and any(const(v) and not isinstance(v.value, str) or (const(v) and isinstance(v.value, str)) for v in node.values[1:]):
            if any(isinstance(v, ast.Call) for v in node.values[:1]):
                found.append(('ЗАПАС', where, seg(node)))
        # списки / словари / кортежи с русскими словами
        if isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.Dict)) and has_cyr_str(node):
            if node.lineno not in seen_coll:
                seen_coll.add(node.lineno)
                found.append(('СЛОВАРЬ', where, seg(node)))
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if MODEL.search(node.value):
                found.append(('МОДЕЛЬ', where, seg(node)))
            if CHANNEL.search(node.value):
                found.append(('КАНАЛ', where, seg(node)))
    return found


def load_allow():
    allow = {}
    if os.path.exists(ALLOW):
        for line in open(ALLOW, encoding='utf-8'):
            line = line.rstrip('\n')
            if not line.strip() or line.startswith('#'):
                continue
            parts = line.split(' | ')
            if len(parts) >= 4:
                allow[(parts[0].strip(), parts[1].strip(), parts[2].strip())] = parts[3].strip()
    return allow


def main():
    found = []
    for where, src in js_sources():
        found += scan_js(where, src)
    found += scan_py('assembler/app.py', open(os.path.join(ROOT, 'assembler', 'app.py'), encoding='utf-8').read())
    uniq = []
    for f in found:
        if f not in uniq:
            uniq.append(f)
    allow = load_allow()
    bad = [f for f in uniq if f not in allow]
    if '--dump' in sys.argv:
        for kind, where, snip in uniq:
            print(f'{kind} | {where} | {snip} | ')
        return
    for kind, where, snip in bad:
        print(f'{kind}: {where}: {snip}')
    stale = [k for k in allow if k not in uniq]
    for k in stale:
        print('лишнее в allow.txt (этого в коде уже нет):', ' | '.join(k))
    print('нарушений:', len(bad))
    sys.exit(1 if bad or stale else 0)


if __name__ == '__main__':
    main()
