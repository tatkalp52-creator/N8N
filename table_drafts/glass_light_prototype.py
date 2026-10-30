import numpy as np, cv2, subprocess, imageio_ffmpeg
img=cv2.cvtColor(cv2.imread('cat.png'),cv2.COLOR_BGR2RGB).astype(np.float32)
H,W=img.shape[:2]; lum=img.mean(2)
lead=cv2.dilate((lum<38).astype(np.uint8),np.ones((2,2),np.uint8)).astype(bool)
n,lab=cv2.connectedComponents((~lead).astype(np.uint8),connectivity=4)
ys,xs=np.mgrid[0:H,0:W]
cl=np.zeros(n); cx=np.zeros(n); cy=np.zeros(n)
for i in range(1,n):
    m=lab==i; cl[i]=lum[m].mean(); cx[i]=xs[m].mean()/W; cy[i]=ys[m].mean()/H
rng=np.random.default_rng(5)
ph=rng.uniform(0,1,n); kk=rng.choice([1,2],n,p=[0.7,0.3])
amp=0.10+0.28*np.clip((cl-70)/150,0,1)
path=(cx>0.40)&(cx<0.56)&(cy>0.46)&(cy<0.92)&(cl>110)
sx,sy=0.496*W,0.356*H
R=np.hypot(xs-sx,ys-sy)
glow=np.exp(-(R/(0.26*W))**2); core=np.exp(-(R/(0.09*W))**2)
T=12.0; fps=24; N=int(T*fps)
# пылинки в луче
pr=np.random.default_rng(11); P=140
px=pr.normal(0.50,0.17,P)*W; py=pr.uniform(0.15,0.95,P)*H; pph=pr.uniform(0,1,P); psz=pr.uniform(1.0,2.6,P); pk=pr.choice([1,2],P)
sunlight=np.exp(-(np.hypot(px-sx,(py-sy)*0.7)/(0.35*W))**2)
lead3=lead[...,None].astype(np.float32)
out=[]
for f in range(N):
    u=f/N
    s=0.5+0.5*np.sin(2*np.pi*(kk*u+ph))
    fac=1-amp*s
    pf=1-0.40*(0.5+0.5*np.sin(2*np.pi*(u-1.5*cy)))
    fac=np.where(path,pf,fac); fac[0]=1
    frame=img*fac[lab][...,None]
    # дыхание солнца
    g=(0.55+0.45*np.sin(2*np.pi*u))
    frame=frame+(g*glow)[...,None]*np.array([120,75,18],np.float32)+(g*core)[...,None]*np.array([70,55,25],np.float32)
    # проход солнца слева направо, за кадром на старте и финише
    x0=(-0.3+1.6*u)*W
    band=np.exp(-((xs-(x0+0.22*ys))/(0.15*W))**2)
    frame=frame*(1+0.20*band[...,None])+band[...,None]*np.array([16,10,2],np.float32)
    # ореол на свинец
    bright=np.clip(frame-170,0,None)
    bloom=cv2.GaussianBlur(bright,(0,0),6)
    frame=frame+0.30*bloom*lead3+0.14*bloom
    # пылинки
    layer=np.zeros((H,W,3),np.float32)
    for i in range(P):
        v=(pk[i]*u+pph[i])%1.0
        a=np.sin(np.pi*v)**2*sunlight[i]
        x=px[i]+14*np.sin(2*np.pi*(v+pph[i])); y=py[i]-110*v
        if 0<=x<W and 0<=y<H:
            cv2.circle(layer,(int(x),int(y)),int(round(psz[i])),(255*a,235*a,190*a),-1,cv2.LINE_AA)
    frame=frame+cv2.GaussianBlur(layer,(0,0),1.1)*0.9
    frame[lead]=np.minimum(frame[lead],img[lead]*1.10+10)
    out.append(np.clip(frame,0,255).astype(np.uint8))
d=np.mean([np.abs(out[k].astype(int)-out[0].astype(int)).mean() for k in range(0,N,12)]); print('mean change vs frame0: %.1f'%d)
vw=cv2.VideoWriter('_t2.mp4',cv2.VideoWriter_fourcc(*'mp4v'),fps,(W,H))
for r in range(2):
    for fr in out: vw.write(cv2.cvtColor(fr,cv2.COLOR_RGB2BGR))
vw.release()
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-y','-i','_t2.mp4','-c:v','libx264','-pix_fmt','yuv420p','-crf','19','-movflags','+faststart','Витраж_свет_проба2.mp4'],check=True)
cv2.imwrite('g0.png',cv2.cvtColor(out[0],cv2.COLOR_RGB2BGR)); cv2.imwrite('g1.png',cv2.cvtColor(out[N//3],cv2.COLOR_RGB2BGR)); cv2.imwrite('g2.png',cv2.cvtColor(out[2*N//3],cv2.COLOR_RGB2BGR))
o=cv2.imread('cat.png'); cv2.imwrite('cmp2.png',np.hstack([cv2.imread(k)[130:470,260:760] for k in ('cat.png','g0.png','g1.png','g2.png')]))
