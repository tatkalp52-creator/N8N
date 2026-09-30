# M4/M5: «распушённые» щётки на основе M3 (UVR + 10% живых щёток):
#  глуше (срез верхов), медленнее атака (смягчение удара), длиннее хвост (пух с медленным затуханием + короткий «зал»).
#  M4 — умеренно, M5 — сильнее.
import os, re, numpy as np, soundfile as sf
from scipy.signal import butter, sosfiltfilt, sosfilt, fftconvolve
S='/tmp/claude-0/-home-user-N8N/994c923d-89bd-532f-b598-03f041c8a163/scratchpad'; R=f'{S}/res'; sr=44100
lab=lambda o:(re.findall(r'\(([^)]+)\)',os.path.basename(o)) or [''])[-1].lower()
stems={lab(p):os.path.join(f'{R}/stems_G',p) for p in os.listdir(f'{R}/stems_G')}
parts=[]
for name,p in stems.items():
    if name=='drums': continue
    x,_=sf.read(p)
    if np.sqrt(np.mean(x**2))<1e-4: continue
    d2=f'{R}/L_{name}2'
    parts.append(sf.read([os.path.join(d2,f) for f in os.listdir(d2) if lab(f)=='dry'][0])[0][:len(x)])
d,_=sf.read(stems['drums'])
dc,_=sf.read([os.path.join(f'{R}/M_drums',f) for f in os.listdir(f'{R}/M_drums') if lab(f)=='no noise'][0]); dc=dc[:len(d)]
base=dc+0.10*d

def follow(x, att, rel):  # огибающая с раздельными атакой/затуханием
    a=np.exp(-1/(att*sr)); r=np.exp(-1/(rel*sr)); e=np.zeros_like(x); v=0.0
    for i,s in enumerate(x):
        c=a if s>v else r; v=c*v+(1-c)*s; e[i]=v
    return e
mono=np.abs(sosfiltfilt(butter(4,[4000,12000],btype='band',fs=sr,output='sos'),d.mean(axis=1)))
# огибающие считаем на прореженном сигнале (быстрее), потом растягиваем
step=32; m=mono[::step]
def fol(att,rel):
    a=np.exp(-1/(att*sr/step)); r=np.exp(-1/(rel*sr/step)); e=np.zeros_like(m); v=0.0
    for i,s in enumerate(m):
        c=a if s>v else r; v=c*v+(1-c)*s; e[i]=v
    return np.repeat(e,step)[:len(mono)]+1e-6
fast=fol(0.001,0.08); slow=fol(0.030,0.08)
ref,_=sf.read(f'{R}/G2.wav')
for tag,(soft,lp,tail_ms,room) in {'M6':(0.5,7500,250,0.20),'M7':(0.8,6000,400,0.30)}.items():
    g=np.clip((slow/fast)**soft,0.25,1.0)            # удар тише в самом начале → атака медленнее
    hp=sosfiltfilt(butter(2,2000,btype='high',fs=sr,output='sos'),base,axis=0)
    y=(base-hp)+hp*g[:,None]
    y=sosfiltfilt(butter(2,lp,btype='low',fs=sr,output='sos'),y,axis=0)*0.6+y*0.4  # глуше, но не мёртво
    # пух с длинным хвостом: шум 1.5–6 кГц по огибающей с медленным затуханием
    env=fol(0.015,tail_ms/1000)
    env=np.clip(env-np.percentile(env,40)*1.2,0,None)
    nz=sosfiltfilt(butter(2,[1500,6000],btype='band',fs=sr,output='sos'),np.random.default_rng(2).standard_normal((len(y),2)),axis=0)
    nz/=np.sqrt(np.mean(nz**2))+1e-9
    fl=nz*env[:,None]; fl*=np.sqrt(np.mean(y**2))/(np.sqrt(np.mean(fl**2))+1e-9)*0.6
    # короткий тёмный «зал» для хвоста
    t=np.arange(int(0.35*sr))/sr
    ir=np.random.default_rng(3).standard_normal((len(t),2))*np.exp(-t/0.12)[:,None]
    ir=sosfiltfilt(butter(2,5000,btype='low',fs=sr,output='sos'),ir,axis=0); ir/=np.sqrt(np.sum(ir**2,axis=0))
    wet=np.stack([fftconvolve(y[:,c],ir[:,c])[:len(y)] for c in range(2)],axis=1)
    drums=y+fl+room*wet
    drums*=np.sqrt(np.mean(base**2))/(np.sqrt(np.mean(drums**2))+1e-9)   # громкость щёток как в M3
    ps=parts+[drums]; n=min(len(p) for p in ps); tot=sum(p[:n] for p in ps)
    tot*=min(1.0,np.max(np.abs(ref))/(np.max(np.abs(tot))+1e-9))
    sf.write(f'{R}/{tag}.wav',tot,sr); print(tag,'done')
