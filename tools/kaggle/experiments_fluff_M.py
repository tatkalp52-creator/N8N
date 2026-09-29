# M: всё мелодическое — как в L (двойной aggressive); щётки — вычистить до стерильности (UVR),
# потом «распушить»: добавить мягкий шорох (отфильтрованный шум) ТОЛЬКО там, где идут удары щёток,
# по огибающей ударов из исходной дорожки щёток. Ковра между ударами нет — есть «пух» на ударах.
import os, re, numpy as np, soundfile as sf
from scipy.signal import stft, istft, butter, sosfiltfilt
from audio_separator.separator import Separator
S='/tmp/claude-0/-home-user-N8N/994c923d-89bd-532f-b598-03f041c8a163/scratchpad'; R=f'{S}/res'; M=f'{S}/sep/models'
sr=44100
lab=lambda o:(re.findall(r'\(([^)]+)\)',os.path.basename(o)) or [''])[-1].lower()
def run(model, path, d):
    os.makedirs(d, exist_ok=True)
    s=Separator(output_dir=d, output_format='WAV', model_file_dir=M); s.load_model(model_filename=model)
    return [os.path.join(d, os.path.basename(o)) for o in s.separate(path)]
stems={lab(p):os.path.join(f'{R}/stems_G',p) for p in os.listdir(f'{R}/stems_G')}
# мелодические — берём готовые двойные чистки из L
parts=[]
for name,p in stems.items():
    if name=='drums': continue
    x,_=sf.read(p)
    if np.sqrt(np.mean(x**2))<1e-4: continue
    d2=f'{R}/L_{name}2'
    y=[os.path.join(d2,f) for f in os.listdir(d2) if lab(f)=='dry'][0]
    parts.append(sf.read(y)[0][:len(x)])
# щётки: стерильная чистка
d,_=sf.read(stems['drums'])
outs=run('UVR-DeNoise.pth', stems['drums'], f'{R}/M_drums')
clean=[o for o in outs if lab(o) in ('no noise',)][0]
dc,_=sf.read(clean); dc=dc[:len(d)]
# огибающая ударов из ИСХОДНЫХ щёток (верха 4–12 кГц), только выше «ковра»
sos=butter(4,[4000,12000],btype='band',fs=sr,output='sos')
hf=sosfiltfilt(sos,d.mean(axis=1))
env=np.abs(hf); w=int(0.01*sr); env=np.convolve(env,np.ones(w)/w,mode='same')
carpet=np.percentile(env,40); strokes=np.clip(env-carpet*1.2,0,None)
# «пух»: мягкий шум (розоватый, 3–10 кГц), дышит по огибающей ударов
rng=np.random.default_rng(1)
noise=rng.standard_normal((len(d),2))
sos2=butter(2,[3000,10000],btype='band',fs=sr,output='sos')
noise=sosfiltfilt(sos2,noise,axis=0)
noise/= (np.sqrt(np.mean(noise**2))+1e-9)
fluff=noise*strokes[:,None]
# громкость пуха: подгоняем к энергии ударов в исходнике (минус ковёр)
target=np.sqrt(np.mean(strokes**2)); fl=np.sqrt(np.mean(fluff**2))+1e-9
fluff*= target/fl*0.8
drums=dc+fluff
parts.append(drums)
n=min(len(p) for p in parts); tot=sum(p[:n] for p in parts)
ref,_=sf.read(f'{R}/G2.wav'); tot*=min(1.0,np.max(np.abs(ref))/(np.max(np.abs(tot))+1e-9))
sf.write(f'{R}/M.wav',tot,sr); print('M done')
