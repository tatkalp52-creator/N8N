# N: мелодические слои почищены (N1 — 1 проход aggressive, N2 — 2 прохода), каждый возвращён к своей исходной громкости;
# ударные — ИСХОДНЫЕ, без чистки и без обработки.
import os, re, numpy as np, soundfile as sf
S='/tmp/claude-0/-home-user-N8N/994c923d-89bd-532f-b598-03f041c8a163/scratchpad'; R=f'{S}/res'; sr=44100
lab=lambda o:(re.findall(r'\(([^)]+)\)',os.path.basename(o)) or [''])[-1].lower()
stems={lab(p):os.path.join(f'{R}/stems_G',p) for p in os.listdir(f'{R}/stems_G')}
rms=lambda a: np.sqrt(np.mean(a**2))+1e-9
ref,_=sf.read(f'{R}/G2.wav')
for tag,k in (('N1','1'),('N2','2')):
    parts=[]
    for name,p in stems.items():
        x,_=sf.read(p)
        if rms(x)<1e-4: continue
        if name=='drums':
            parts.append(x); continue
        dd=f'{R}/L_{name}{k}'
        y=sf.read([os.path.join(dd,f) for f in os.listdir(dd) if lab(f)=='dry'][0])[0][:len(x)]
        parts.append(y*min(rms(x)/rms(y),10**(3/20)))   # вернуть громкость слоя, не больше +3 дБ
    n=min(len(p) for p in parts); tot=sum(p[:n] for p in parts)
    tot*=min(1.0,np.max(np.abs(ref))/(np.max(np.abs(tot))+1e-9))
    sf.write(f'{R}/{tag}.wav',tot,sr); print(tag,'done')
