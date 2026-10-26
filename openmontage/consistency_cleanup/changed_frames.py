import numpy as np,subprocess,json,sys
C,F,out=sys.argv[1:4]
raw=subprocess.check_output(['ffmpeg','-nostdin','-v','error','-i',C,'-fps_mode','passthrough','-vf','scale=36:64','-f','rawvideo','-pix_fmt','gray','-'])
CT=np.frombuffer(raw,np.uint8).reshape(-1,64*36).astype(np.float32)
FT=np.load(F)
n=min(len(CT),len(FT)); d=np.abs(CT[:n]-FT[:n]).max(1)
idx=np.where(d>12)[0]; R=[]
for i in idx:
    if R and i-R[-1][1]<15: R[-1][1]=int(i)+1
    else: R.append([int(i),int(i)+1])
R=[[max(0,a-3),min(n,b+3),'fix'] for a,b in R]
json.dump({'fixes':R},open(out,'w'))
print(len(R),'ranges',sum(b-a for a,b,_ in R),'frames of',n)
