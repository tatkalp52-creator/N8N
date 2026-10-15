# Нарезка листа образцов (листья на бумаге) на отдельные PNG с прозрачным фоном.
# Фон = бумага, до которой можно дойти от края картинки, не переходя тёмный контур листа.
# Светлые пятна внутри листа не связаны с краем — остаются листом; карманы между лопастями — фон.
import cv2, numpy as np, os, sys
src, out = sys.argv[1], sys.argv[2]
T = float(sys.argv[3]) if len(sys.argv) > 3 else 14
img = cv2.imread(src); H, W = img.shape[:2]
lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
# цвет бумаги — по краям картинки (там листьев нет); местная медиана рядом с листом темнеет и ломает фон
edge_px = np.concatenate([lab[:20].reshape(-1, 3), lab[-20:].reshape(-1, 3), lab[:, :20].reshape(-1, 3), lab[:, -20:].reshape(-1, 3)])
bg = np.median(edge_px, 0)[None, None, :]
d = cv2.GaussianBlur(np.sqrt(((lab - bg) ** 2).sum(2)), (0, 0), 1.0)
paper = (d < T).astype(np.uint8)
paper = cv2.morphologyEx(paper, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
pad = np.pad(paper, 1, constant_values=1)
n, lb = cv2.connectedComponents(pad, connectivity=4)
outside = (lb == lb[0, 0])[1:-1, 1:-1]
leaf = (~outside).astype(np.uint8) * 255
# закрытые карманы бумаги внутри (между листочками ясеня, дырки рваного листа) — тоже прозрачные
n2, l2, s2, _ = cv2.connectedComponentsWithStats(pad, connectivity=4)
for j in range(1, n2):
    if j != lb[0, 0] and s2[j, 4] > 150:
        leaf[(l2 == j)[1:-1, 1:-1]] = 0
leaf = cv2.erode(leaf, np.ones((3, 3), np.uint8))   # без светлой каймы бумаги по краю
leaf = cv2.morphologyEx(leaf, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
n, lb, st, cen = cv2.connectedComponentsWithStats(leaf)
order = sorted([i for i in range(1, n) if st[i, 4] > 5000], key=lambda i: (round(cen[i][1] / 300), cen[i][0]))
os.makedirs(out, exist_ok=True)
for k, i in enumerate(order, 1):
    x, y, w, h, a = st[i]
    p = 4; x0, y0, x1, y1 = max(0, x - p), max(0, y - p), min(W, x + w + p), min(H, y + h + p)
    alpha = cv2.GaussianBlur((lb[y0:y1, x0:x1] == i).astype(np.uint8) * 255, (0, 0), 0.7)
    cv2.imwrite(f'{out}/list_{k:02d}.png', np.dstack([img[y0:y1, x0:x1], alpha]))
print('листьев', len(order))
