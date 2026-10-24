# merge.py N — присоединяет абзац N+1 к абзацу N, сдвигает ссылки
import sys,json,re
import os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S=os.path.join(ROOT,'src','texts')+'/'
N=int(sys.argv[1]);fix=sys.argv[2] if len(sys.argv)>2 else None
P=json.load(open(S+'paras.json',encoding='utf-8'))
P[N-1:N+1]=[P[N-1].rstrip()+' '+(fix or P[N]).strip()]
json.dump(P,open(S+'paras.json','w',encoding='utf-8'),ensure_ascii=False)
C=json.load(open(S+'paras_clean.json',encoding='utf-8'));fixc=sys.argv[3] if len(sys.argv)>3 else None
C[N-1:N+1]=[C[N-1].rstrip()+' '+(fixc or C[N]).strip()];json.dump(C,open(S+'paras_clean.json','w',encoding='utf-8'),ensure_ascii=False)
open(S+'paras_num.txt','w',encoding='utf-8').write(''.join(f'{k+1}. {x}\n' for k,x in enumerate(P)))
sh=lambda n:n if n<=N else n-1
q=os.path.join(ROOT,'src','atlas','npc.txt');s=open(q,encoding='utf-8').read()
s=re.sub(r'^Q: ([\d, ]+) \|',lambda m:'Q: '+', '.join(str(sh(int(x))) for x in re.findall(r'\d+',m.group(1)))+' |',s,flags=re.M)
open(q,'w',encoding='utf-8').write(s)
r=os.path.join(ROOT,'src','rules','rules.html');h=open(r,encoding='utf-8').read()
h=re.sub(r'\{id:"odd-[^"]+".*?`\},',lambda m:re.sub(r'<td>([\d, ]+)</td></tr>',lambda mm:'<td>'+', '.join(str(sh(int(x))) for x in re.findall(r'\d+',mm.group(1)))+'</td></tr>',m.group(0)),h,flags=re.S)
h=re.sub(r'(абзацев )(\d+)( и )(\d+)',lambda m:m.group(1)+str(sh(int(m.group(2))))+m.group(3)+str(sh(int(m.group(4)))),h)
open(r,'w',encoding='utf-8').write(h)
print('merged',N,'total',len(P));print(P[N-1][-120:])
