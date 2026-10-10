import os, re, numpy as np, soundfile as sf
from scipy.signal import stft, istft, butter, sosfilt
from audio_separator.separator import Separator
S='/tmp/claude-0/-home-user-N8N/994c923d-89bd-532f-b598-03f041c8a163/scratchpad'; R=f'{S}/res'; M=f'{S}/sep/models'
AGGR='denoise_mel_band_roformer_aufr33_aggr_sdr_27.9768.ckpt'
sr=44100
def run(model, path, d):
    os.makedirs(d, exist_ok=True)
    s=Separator(output_dir=d, output_format='WAV', model_file_dir=M); s.load_model(model_filename=model)
    return [os.path.join(d, os.path.basename(o)) for o in s.separate(path)]
lab=lambda o:(re.findall(r'\(([^)]+)\)',os.path.basename(o)) or [''])[-1].lower()
def denoise(path, d):
    if os.path.isdir(d):
        have=[os.path.join(d,f) for f in os.listdir(d) if lab(f)=='dry']
        if have: return have[0]
    outs=run(AGGR, path, d); return [o for o in outs if lab(o)=='dry'][0]
# стемы исходника (уже есть от прошлого шага)
stems={lab(p):os.path.join(f'{R}/stems_G',p) for p in os.listdir(f'{R}/stems_G')}
print(stems.keys())
parts=[]
for name,p in stems.items():
    x,_=sf.read(p)
    if np.sqrt(np.mean(x**2))<1e-4: continue
    if name=='drums':
        continue
    y,_=sf.read(denoise(denoise(p,f'{R}/L_{name}1'),f'{R}/L_{name}2'))
    parts.append(y[:len(x)])
# ЩЁТКИ: «причесать» без нейросети
d,_=sf.read(stems['drums'])
def brush_comb(x, hf=6000, floor_db=-9.0, soft_db=-2.0):
    out=np.zeros_like(x)
    for ch in range(x.shape[1]):
        f,t,Z=stft(x[:,ch],fs=sr,nperseg=2048)
        hfm=f>=hf
        e=np.abs(Z[hfm]).mean(axis=0)                       # энергия верхов по времени
        base=np.percentile(e,40)                            # «ковёр» между ударами
        # мягкий экспандер: где энергия близка к ковру — приглушаем до floor_db, на ударах — не трогаем
        ratio=np.clip((e/base-1.0)/2.0,0,1)                 # 0 — ковёр, 1 — явный удар
        g=10**((floor_db*(1-ratio))/20)
        g=np.convolve(g,np.ones(5)/5,mode='same')          # сгладить, без щелчков
        G=np.ones_like(np.abs(Z)); G[hfm]=g[None,:]
        # лёгкое смягчение самого верха (>11 кГц)
        G[f>=11000]*=10**(soft_db/20)
        _,y=istft(Z*G,fs=sr,nperseg=2048); out[:,ch]=y[:len(x)]
    return out
parts.append(brush_comb(d))
n=min(len(p) for p in parts); tot=sum(p[:n] for p in parts)
ref,_=sf.read(f'{R}/G2.wav'); tot*=min(1.0,np.max(np.abs(ref))/(np.max(np.abs(tot))+1e-9))
sf.write(f'{R}/L.wav',tot,sr); print('L done')
