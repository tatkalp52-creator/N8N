# Снимок разбора строк оживления: python3 tools/effects/fx_parse_dump.py <app-dir> <out.json> [vocab.json]
import sys, json, os
sys.path.insert(0, sys.argv[1])
import app as A
corpus = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fx_corpus.json')))
data = {'leafSize': '30', 'leafFallSeconds': '6'}
if len(sys.argv) > 3:
    data['fxWords'] = json.load(open(sys.argv[3]))
if hasattr(A, 'set_vocab'):
    A.set_vocab(data)
def fx(x):
    return [[k, list(n), dict(n.knobs), n.area, n.cloud, n.cuts, n.spill, n.exact, n.radius] for k, n in x]
out = []
for t in corpus:
    lv, edge = A.parse_leaves(t, data)
    out.append({'effects': fx(A.parse_effects(t)), 'leaves': [{k: v for k, v in l.items() if k != '_named'} for l in lv],
                'edge': edge, 'occ': A.parse_occluders(t), 'covers': A.parse_cover_lines(t)})
json.dump(out, open(sys.argv[2], 'w'), ensure_ascii=False, default=list)
print('dumped', len(out))
