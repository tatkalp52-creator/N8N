import cv2, numpy as np, sys, os, json
U = '/root/.claude/uploads/863834ac-b5c9-5ddb-833b-0b250e3046ee/'
SRC = {'lavka': '../font/cat.img', 'rynok1': U + '27a2d3c0-image.jpg', 'rynok2': U + '2fa350ae-image.jpg', 'rynok3': U + '42320360-image.jpg',
       'rynok4': U + '6907533d-image.jpg', 'rynok5': U + '9e7d5ba3-image.jpg', 'sup': U + '68b08fe6-image.jpg'}
os.makedirs('cand', exist_ok=True)
cands = []
for name, path in SRC.items():
    img = cv2.imread(path); H, W = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0].astype(int), hsv[..., 1].astype(int), hsv[..., 2].astype(int)
    warm = (((h <= 30) | (h >= 170)) & (s > 90) & (v > 90))
    m = cv2.morphologyEx(warm.astype(np.uint8) * 255, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(m)
    for i in range(1, n):
        x, y, w, hh, a = st[i]
        if a < 120 or a > 6000 or w < 12 or hh < 12 or max(w, hh) > 4 * min(w, hh):
            continue
        comp = (lab[y:y + hh, x:x + w] == i).astype(np.uint8)
        cnts, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        hull = cv2.convexHull(cnts[0]); sol = a / max(1, cv2.contourArea(hull))
        if sol < 0.45:   # слишком рваное — скорее куча
            continue
        # тыквы и прочее круглое и крупное не берём: лист — с вырезами (solidity < 0.92) или вытянутый
        if sol > 0.93 and max(w, hh) < 1.6 * min(w, hh):
            continue
        pad = 3
        x0, y0, x1, y1 = max(0, x - pad), max(0, y - pad), min(W, x + w + pad), min(H, y + hh + pad)
        alpha = cv2.dilate((lab[y0:y1, x0:x1] == i).astype(np.uint8) * 255, np.ones((3, 3), np.uint8))
        alpha = cv2.GaussianBlur(alpha, (0, 0), 0.8)
        rgba = np.dstack([img[y0:y1, x0:x1], alpha])
        fn = f'cand/{name}_{i:04d}.png'; cv2.imwrite(fn, rgba)
        cands.append({'file': fn, 'src': name, 'box': [int(x0), int(y0), int(x1), int(y1)], 'area': int(a), 'sol': round(float(sol), 2)})
json.dump(cands, open('cands.json', 'w'), ensure_ascii=False, indent=0)
print(len(cands), {k: sum(c['src'] == k for c in cands) for k in SRC})
