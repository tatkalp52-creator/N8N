# M2/M3: мягче щётки. Мелодические как в M. Щётки UVR -> срезать резкость выше 8 кГц (-5 дБ),
# пух ниже и медленнее (2–7 кГц, огибающая 30 мс). M3 = M2 + 10% исходных щёток.
import os, re, numpy as np, soundfile as sf
from scipy.signal import butter, sosfiltfilt
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
hi=sosfiltfilt(butter(2,8000,btype='high',fs=sr,output='sos'),dc,axis=0)
dc=dc-hi*(1-10**(-5/20))
hf=sosfiltfilt(butter(4,[4000,12000],btype='band',fs=sr,output='sos'),d.mean(axis=1))
w=int(0.03*sr); env=np.convolve(np.abs(hf),np.ones(w)/w,mode='same')
strokes=np.clip(env-np.percentile(env,40)*1.2,0,None)
noise=sosfiltfilt(butter(2,[2000,7000],btype='band',fs=sr,output='sos'),np.random.default_rng(1).standard_normal((len(d),2)),axis=0)
noise/=np.sqrt(np.mean(noise**2))+1e-9
fluff=noise*strokes[:,None]; fluff*=np.sqrt(np.mean(strokes**2))/(np.sqrt(np.mean(fluff**2))+1e-9)*0.9
ref,_=sf.read(f'{R}/G2.wav')
for tag,extra in (('M2',0),('M3',0.10)):
    ps=parts+[dc+fluff+extra*d]
    n=min(len(p) for p in ps); tot=sum(p[:n] for p in ps)
    tot*=min(1.0,np.max(np.abs(ref))/(np.max(np.abs(tot))+1e-9))
    sf.write(f'{R}/{tag}.wav',tot,sr); print(tag,'done')
