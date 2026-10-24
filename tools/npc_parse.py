import re,json,subprocess,sys
import os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H=os.path.join(ROOT,'src','atlas')
ids=json.loads(subprocess.check_output(['node','-e','eval(require("fs").readFileSync("'+os.path.join(H,"data.js").replace("\\","/")+'","utf8").replace(/const /g,"global."));console.log(JSON.stringify(Object.fromEntries(NODES.map(n=>[n[0],n[2]]))))']))
paras=json.load(open(os.path.join(ROOT,'src','texts','paras.json'),encoding='utf-8'))
SK=["Коканье","Колупание","Механика","Кукичество","Сыворотка общества","Шепоток","Лицедейство","Хождение в копытах","Знахарство","Варево","Бобылеведение","Трубоведение","Летопись","Чак-чак","Сноходчество","Щекотка"]
ST={"Разварен","Колосится","Неуклюж","Кислый","Красные уши","Влажный","Заполиплен","Опутан","Опрокинут","Ошарашен","Напуган","В петле","Пуча","Простуда","Ангина ламантинов","Икота","Подготовлен","Воодушевлён","Раскрепощён","Гуттаперчив","Вывернут","В раковине","Парит","Свой","Светится","С двойником"}
RANKS={"мелочь","обычный","сильный","легендарный","—"}
err=[];out={}
def chk(t,cid):
    for m in re.finditer(r'\[\[([^|\]]+)',t):
        if m.group(1) not in ids: err.append(f'{cid}: bad link {m.group(1)}')
    for m in re.finditer(r'\{([^|}]+)',t):
        if m.group(1) not in ST: err.append(f'{cid}: bad state {m.group(1)}')
    return t
cur=None
for ln in open(H+'/npc.txt',encoding='utf-8'):
    ln=ln.rstrip('\n')
    if not ln.strip() or ln.startswith('#'): continue
    if ln.startswith('@'):
        f=ln[1:].split('|')
        cid=f[0]
        if cid not in ids: err.append('unknown id '+cid)
        if f[3] not in RANKS: err.append(cid+' rank '+f[3])
        cur=out[cid]={'k':f[1],'g':f[2],'rank':f[3],'face':int(f[4]),
          'fr':None if f[5]=='-' else int(f[5]),'rz':None if f[6]=='-' else int(f[6]),
          'talk':None if f[7]=='-' else int(f[7]),'tn':f[8] if len(f)>8 else '',
          'props':[],'moves':[],'skills':[]}
        continue
    key,_,val=ln.partition(': ');val=val.strip()
    c=cur;cid=[k for k,v in out.items() if v is c][0]
    if key=='S':
        if val=='-': c['stats']=None
        else:
            v=[int(x) for x in val.split()]
            if len(v)!=6 or not all(1<=x<=9 for x in v): err.append(cid+' stats')
            c['stats']=v
    elif key=='K':
        for p in val.split(','):
            p=p.strip();n,l=p.rsplit(' ',1)
            if n not in SK: err.append(cid+' skill '+n)
            c['skills'].append([n,int(l)])
    elif key=='P': c['props'].append(chk(val,cid))
    elif key=='M':
        if val!='—':
            t,_,x=val.partition(' = ');c['moves'].append([t,chk(x,cid)])
    elif key in ('L','B'):
        toks=[t.strip() for t in val.split(',')] if not val.startswith('[[') or ', ' in val else [val]
        for t in toks:
            if re.fullmatch(r'[a-z_0-9]+',t) and t not in ids: err.append(cid+' place '+t)
            chk(t,cid)
        c['lives' if key=='L' else 'bel']=toks
    elif key=='I':
        i,_,cap=val.partition('|');c['img']=[i,cap]
    elif key in '+-T$D':
        c[{'+':'likes','-':'fears','T':'teach','$':'trade','D':'loot'}[key]]=chk(val,cid)
    elif key=='Q':
        p,_,q=val.partition(' | ');p=p.strip()
        c['q']=[p,q]
        nums=[int(x) for x in re.findall(r'\d+',p)]
        src=' '.join(paras[n-1] for n in nums).lower().replace('ё','е')
        w=[x for x in re.findall(r'\w{4,}',q.lower().replace('ё','е'))]
        hit=sum(1 for x in w if x[:5] in src)
        if w and hit/len(w)<.6: err.append(f'{cid}: quote mismatch {hit}/{len(w)} par {p}')
    elif key=='X': c['x']=val
    elif key=='H':
        BR={'трусливый':0,'нормальный':1,'храбрый':2}
        if val not in BR: err.append(cid+' brave '+val)
        c['br']=BR.get(val)
    else: err.append(cid+' key '+key)
for cid,c in out.items():
    if 'x' in c: continue
    for k in ('stats','q','likes','fears','teach','trade','loot'):
        if k not in c: err.append(cid+' missing '+k)
    if c['rank']!='—' and 'br' not in c: err.append(cid+' missing brave')
print('\n'.join(err) or 'ok', len(out))
if err: sys.exit(1)
tp={}
for k in out: tp[ids[k]]=tp.get(ids[k],0)+1
print(tp)
missing=[k for k,t in ids.items() if t in('person','kind') and k not in out]
print('без карточки (person/kind):',missing)
os.makedirs(os.path.join(ROOT,'build'),exist_ok=True)
json.dump(out,open(os.path.join(ROOT,'build','npc.json'),'w',encoding='utf-8'),ensure_ascii=False)
