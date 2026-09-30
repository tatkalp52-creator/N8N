# T: мелодические слои — aggressive 1 проход (громкость слоя вернуть к исходной);
# барабаны разложены DrumSep: бочка, малый, томы, райд, крэш — ИСХОДНЫЕ; чистится только хэт (там весь песок и щётки).
# T1 — хэт почищен 1 раз; T2 — 2 раза; T3 — 1 раз и на 3 дБ тише.
import os, re, glob, numpy as np, soundfile as sf
S='/tmp/claude-0/-home-user-N8N/994c923d-89bd-532f-b598-03f041c8a163/scratchpad'; R=f'{S}/res'; sr=44100
lab=lambda o:(re.findall(r'\(([^)]+)\)',os.path.basename(o)) or [''])[-1].lower()
rms=lambda a: np.sqrt(np.mean(a**2))+1e-9
stems={lab(p):os.path.join(f'{R}/stems_G',p) for p in os.listdir(f'{R}/stems_G')}
mel=[]
for name,p in stems.items():
    if name=='drums': continue
    x,_=sf.read(p)
    if rms(x)<1e-4: continue
    dd=f'{R}/L_{name}1'
    y=sf.read([os.path.join(dd,f) for f in os.listdir(dd) if lab(f)=='dry'][0])[0][:len(x)]
    mel.append(y*min(rms(x)/rms(y),10**(3/20)))
kit={}
for f in glob.glob(f'{R}/drumsep/*.wav'):
    kit[re.findall(r'\((\w+)\)_MDX',f)[0]]=sf.read(f)[0]
hh0=kit['hh']
dry=lambda d:[os.path.join(d,f) for f in os.listdir(d) if lab(f)=='dry'][0]
hh1=sf.read(dry(f'{R}/hh1'))[0][:len(hh0)]; hh2=sf.read(dry(f'{R}/hh2'))[0][:len(hh0)]
hh1*=min(rms(hh0)/rms(hh1),10**(2/20)); hh2*=min(rms(hh0)/rms(hh2),10**(2/20))
rest=[kit[k] for k in ('kick','snare','toms','ride','crash')]
ref,_=sf.read(f'{R}/G2.wav')
for tag,hh in (('T1',hh1),('T2',hh2),('T3',hh1*10**(-3/20))):
    ps=mel+rest+[hh]; n=min(len(p) for p in ps); tot=sum(p[:n] for p in ps)
    tot*=min(1.0,np.max(np.abs(ref))/(np.max(np.abs(tot))+1e-9))
    sf.write(f'{R}/{tag}.wav',tot,sr); print(tag,'done')
