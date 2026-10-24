# split.py N "начало нового абзаца" — делит абзац N, сдвигает ссылки на абзацы в карточках и своде правил
import sys,json,re
import os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S=os.path.join(ROOT,'src','texts')+'/'
N=int(sys.argv[1]);mk=sys.argv[2]
P=json.load(open(S+'paras.json',encoding='utf-8'));t=P[N-1];i=t.find(mk);assert i>0,('marker not found',t)
a,b=t[:i].rstrip(),t[i:].strip();b=b[0].upper()+b[1:]
P[N-1:N]=[a,b];json.dump(P,open(S+'paras.json','w',encoding='utf-8'),ensure_ascii=False)
C=json.load(open(S+'paras_clean.json',encoding='utf-8'));ct=C[N-1];mk2=sys.argv[3] if len(sys.argv)>3 else mk
j=ct.lower().replace('ё','е').find(mk2.lower().replace('ё','е'))
if j<=0: print('!!! В выправленном тексте маркер не найден — передай третий аргумент'); sys.exit(1)
ca,cb=ct[:j].rstrip(),ct[j:].strip();cb=cb[0].upper()+cb[1:];C[N-1:N]=[ca,cb];json.dump(C,open(S+'paras_clean.json','w',encoding='utf-8'),ensure_ascii=False)
open(S+'paras_num.txt','w',encoding='utf-8').write(''.join(f'{k+1}. {x}\n' for k,x in enumerate(P)))
norm=lambda x:re.sub(r'[^а-яa-z]','',x.lower().replace('ё','е'))
def shift(n,quote=None):
    if n<N:return n
    if n>N:return n+1
    if quote is None:return n
    w=re.findall(r'\w{4,}',quote.lower().replace('ё','е'));sa=sum(x[:5] in a.lower().replace('ё','е') for x in w);sb=sum(x[:5] in b.lower().replace('ё','е') for x in w);return N+1 if sb>sa else N
q=os.path.join(ROOT,'src','atlas','npc.txt');s=open(q,encoding='utf-8').read()
def qrep(m):
    nums=[shift(int(x),m.group(2)) for x in re.findall(r'\d+',m.group(1))]
    return 'Q: '+', '.join(map(str,nums))+' | '+m.group(2)
s=re.sub(r'^Q: ([\d, ]+) \| (.*)$',qrep,s,flags=re.M);open(q,'w',encoding='utf-8').write(s)
r=os.path.join(ROOT,'src','rules','rules.html');h=open(r,encoding='utf-8').read()
amb=[]
def art(m):
    body=m.group(0)
    def td(mm):
        nums=[int(x) for x in re.findall(r'\d+',mm.group(1))]
        if N in nums: amb.append(mm.string[max(0,mm.start()-200):mm.start()])
        return '<td>'+', '.join(str(shift(x)) for x in nums)+'</td></tr>'
    return re.sub(r'<td>([\d, ]+)</td></tr>',td,body)
h=re.sub(r'\{id:"odd-[^"]+".*?`\},',art,h,flags=re.S)
h=re.sub(r'(абзацев )(\d+)( и )(\d+)',lambda m:m.group(1)+str(shift(int(m.group(2))))+m.group(3)+str(shift(int(m.group(4)))),h)
open(r,'w',encoding='utf-8').write(h)
print('split',N,'→',N,'/',N+1,'| total',len(P));print('A:',a[-60:]);print('B:',b[:60])
for x in amb:print('RULES ref ==N, проверь вручную:',re.sub(r'<[^>]+>',' ',x)[-120:])
