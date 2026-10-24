import sys,json,re
import os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S=os.path.join(ROOT,'src','texts')+'/'
A=int(sys.argv[1]);B=A+1
P=json.load(open(S+'paras.json',encoding='utf-8'));P[A-1],P[B-1]=P[B-1],P[A-1]
json.dump(P,open(S+'paras.json','w',encoding='utf-8'),ensure_ascii=False)
C=json.load(open(S+'paras_clean.json',encoding='utf-8'));C[A-1],C[B-1]=C[B-1],C[A-1];json.dump(C,open(S+'paras_clean.json','w',encoding='utf-8'),ensure_ascii=False)
open(S+'paras_num.txt','w',encoding='utf-8').write(''.join(f'{k+1}. {x}\n' for k,x in enumerate(P)))
sw=lambda n:B if n==A else A if n==B else n
q=os.path.join(ROOT,'src','atlas','npc.txt');s=open(q,encoding='utf-8').read()
s=re.sub(r'^Q: ([\d, ]+) \|',lambda m:'Q: '+', '.join(str(sw(int(x))) for x in re.findall(r'\d+',m.group(1)))+' |',s,flags=re.M);open(q,'w',encoding='utf-8').write(s)
r=os.path.join(ROOT,'src','rules','rules.html');h=open(r,encoding='utf-8').read()
h=re.sub(r'\{id:"odd-[^"]+".*?`\},',lambda m:re.sub(r'<td>([\d, ]+)</td></tr>',lambda mm:'<td>'+', '.join(str(sw(int(x))) for x in re.findall(r'\d+',mm.group(1)))+'</td></tr>',m.group(0)),h,flags=re.S)
open(r,'w',encoding='utf-8').write(h)
print(A,P[A-1][:50]);print(B,P[B-1][:50])
