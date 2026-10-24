#!/usr/bin/env python3
"""Сборка исходников в самостоятельные страницы (build/*.html).

  build/atlas.html   — Атлас: shell.html + data.js + тексты + карточки
  build/rules.html   — Свод правил с вшитыми данными атласа
  build/sheet.html   — Лист путника
  build/stats.html   — Тест характеристик
  build/skills.html  — Тест навыков

Эти страницы рабочие сами по себе (так же выглядят артефакты в Claude).
Склейку в одну страницу для сайта делает tools/bundle.mjs.
"""
import json, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src')
OUT = os.path.join(ROOT, 'build')
os.makedirs(OUT, exist_ok=True)


def rd(*p):
    with open(os.path.join(*p), encoding='utf-8') as f:
        return f.read()


def wr(name, text):
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        f.write(text)


# 1. карточки существ: src/atlas/npc.txt -> build/npc.json (с проверками)
r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'npc_parse.py')], capture_output=True, text=True)
print(r.stdout.strip())
if r.returncode:
    print(r.stderr, file=sys.stderr)
    sys.exit('npc_parse: есть ошибки в карточках')

npc = rd(OUT, 'npc.json')
paras = rd(SRC, 'texts', 'paras.json')
clean = rd(SRC, 'texts', 'paras_clean.json')
data_js = rd(SRC, 'atlas', 'data.js')
img_dir = os.path.join(SRC, 'atlas', 'img')
imgs = sorted(f[:-5] for f in os.listdir(img_dir) if f.endswith('.webp'))

# 2. Атлас
# карта Артёма: map/spots.txt — кликабельные места (id | x0 y0 x1 y1 | подпись)
node_ids = set(json.loads(subprocess.check_output(['node', '-e',
    'eval(require("fs").readFileSync(process.argv[1],"utf8").replace(/const /g,"global."));'
    'console.log(JSON.stringify(NODES.map(n=>n[0])))', os.path.join(SRC, 'atlas', 'data.js')])))
mp = {'img': 'map/karta.webp', 'w': 0, 'h': 0, 'spots': []}
bad = []
for ln in rd(SRC, 'atlas', 'map', 'spots.txt').splitlines():
    ln = ln.strip()
    if not ln or ln.startswith('#'):
        continue
    if ln.startswith('@img '):
        mp['img'] = ln[5:].strip(); continue
    if ln.startswith('@size '):
        mp['w'], mp['h'] = map(int, ln[6:].split()); continue
    parts = [x.strip() for x in ln.split('|')]
    x0, y0, x1, y1 = map(int, parts[1].split())
    if parts[0] not in node_ids or not (0 <= x0 < x1 <= mp['w'] and 0 <= y0 < y1 <= mp['h']):
        bad.append(ln)
    mp['spots'].append([parts[0], x0, y0, x1, y1] + ([parts[2]] if len(parts) > 2 and parts[2] else []))
if bad:
    sys.exit('spots.txt: неизвестный id или рамка вне карты:\n' + '\n'.join(bad))
shell = rd(SRC, 'atlas', 'shell.html')
assert '/*DATA*/' in shell
data = (data_js + '\n// Расшифровка, по абзацу на эпизод\nconst PARAS=' + paras + ';\nconst IMGS=' + json.dumps(imgs)
        + ';\nconst CLEAN=' + clean + ';\nconst NPC=' + npc + ';\nconst MAP=' + json.dumps(mp, ensure_ascii=False) + ';\n')
wr('atlas.html', shell.replace('/*DATA*/', data))

# 3. Свод правил (данные атласа для всплывающих карточек)
nodes_edges = json.loads(subprocess.check_output(['node', '-e',
    'eval(require("fs").readFileSync(process.argv[1],"utf8").replace(/const /g,"global."));'
    'console.log(JSON.stringify({n:NODES,e:EDGES}))', os.path.join(SRC, 'atlas', 'data.js')]))
nodes = [{"id": n[0], "name": n[1], "type": n[2], "desc": n[3], "alias": n[4] if len(n) > 4 else ""} for n in nodes_edges['n']]
atlas_data = {"nodes": nodes, "edges": nodes_edges['e'], "npc": json.loads(npc), "paras": json.loads(clean), "imgs": imgs}
js = ('const ATLAS_DATA=(()=>{const d=' + json.dumps(atlas_data, ensure_ascii=False).replace('</', '<\\/')
      + ';d.byId=Object.fromEntries(d.nodes.map(n=>[n.id,n]));d.imgs=new Set(d.imgs);return d})();')
rules = rd(SRC, 'rules', 'rules.html')
assert '/*ATLASDATA*/' in rules
wr('rules.html', rules.replace('/*ATLASDATA*/', js))

# 3б. Кампания — тот же движок, что у свода правил, со своими статьями и предупреждением на входе
camp = rules
def swap(text, start, end, new, what):
    i = text.index(start)
    j = text.index(end, i) + len(end)
    return text[:i] + new + text[j:]
cjs = rd(SRC, 'campaign', 'campaign.js')
# статьи должны разбираться как JS и не содержать дыр в массиве
chk = subprocess.run(['node', '-e', 'const s=require("fs").readFileSync(process.argv[1],"utf8");'
    'const [S,A]=new Function(s+";return [SECTIONS,A]")();const ids=new Set(S.map(x=>x[0]));'
    'if(A.some(a=>!a)||A.length!==Object.keys(A).length)throw "пустой элемент в A (лишняя запятая?)";'
    'for(const a of A)if(!a.id||!a.t||!ids.has(a.sec))throw "статья без id/t или с неизвестным разделом: "+JSON.stringify(a.id);',
    os.path.join(SRC, 'campaign', 'campaign.js')], capture_output=True, text=True)
if chk.returncode:
    sys.exit('campaign.js: ' + (chk.stderr.strip().splitlines() or ['ошибка'])[-1])
c_sec = cjs[cjs.index('const SECTIONS=['):cjs.index('];', cjs.index('const SECTIONS=[')) + 2]
c_art = cjs[cjs.index('const A=['):cjs.index('\n];\n', cjs.index('const A=[')) + 3]
c_print = cjs[cjs.index('/*PRINT*/'):cjs.index('/*/PRINT*/')] if '/*PRINT*/' in cjs else ''
camp = swap(camp, 'const SECTIONS=[', '];', c_sec, 'SECTIONS')
# ((id)) без текста — подставляем название статьи свода
rules_titles = dict(re.findall(r'\{id:"([a-z0-9-]+)",sec:"[a-z]+",st:"[a-z]+",t:"([^"]+)"', rules))
c_art = re.sub(r'\(\(([a-z0-9-]+)\)\)', lambda m: '((%s|%s))' % (m.group(1), rules_titles.get(m.group(1), m.group(1))), c_art)
camp = swap(camp, 'const A=[', '\n];', c_art.rstrip(), 'A')
for a, b in [('<title>Свод правил Зазеркалья</title>', '<title>Кампания: поиск «пацаноида»</title>'),
             ('<h1>Свод правил<span>Я</span></h1>', '<h1>Кампания<span>Я</span></h1>'),
             ('placeholder="Найти правило: подготовка, лицо, отдых…"', 'placeholder="Найти в кампании: друг, куб, улики…"'),
             ('aria-label="Поиск по своду"', 'aria-label="Поиск по кампании"'),
             ('show(byId[start]?start:"worlds",false);', 'show(byId[start]?start:order[0].id,false);'),
             ('<header>', rd(SRC, 'campaign', 'gate.html') + '\n<header>'),
             ('&family=Yeseva+One&display=swap', '&family=Yeseva+One&family=Neucha&display=swap'),
             ('/*CAMP_EXTRA*/', c_print + '\nif(typeof CAMP_PR!=="undefined")Object.assign(PR,CAMP_PR);')]:
    assert camp.count(a) == 1, a
    camp = camp.replace(a, b)
assert camp.count('zz-rules-last') == 2
camp = camp.replace('zz-rules-last', 'zz-camp-last')
# ссылки кампании на статьи кампании и свода должны вести на существующие статьи
rules_ids = set(re.findall(r'\{id:"([a-z0-9-]+)"', rules))
camp_ids = set(re.findall(r'\{id:"([a-z0-9-]+)"', c_art))
bad = sorted({m for m in re.findall(r'\[\[([a-z0-9-]+)', c_art) if m not in camp_ids}
             | {m for m in re.findall(r'\(\(([a-z0-9-]+)\|', c_art) if m not in rules_ids}
             | {m for m in re.findall(r'\{\{([a-z_0-9]+)\|', c_art) if m not in {n['id'] for n in nodes} and not re.fullmatch(r'p\d+', m)})
if bad:
    sys.exit('campaign.js: ссылки на несуществующее: ' + ', '.join(bad))
assert '/*ATLASDATA*/' in camp
wr('campaign.html', camp.replace('/*ATLASDATA*/', js))

# 4. Лист и тесты — как есть
shutil.copyfile(os.path.join(SRC, 'sheet', 'list.html'), os.path.join(OUT, 'sheet.html'))
shutil.copyfile(os.path.join(SRC, 'tests', 'stats.html'), os.path.join(OUT, 'stats.html'))
shutil.copyfile(os.path.join(SRC, 'tests', 'skills.html'), os.path.join(OUT, 'skills.html'))

# 5. картинки рядом со страницами (для локального просмотра build/)
for sub in ('img', 'map'):
    dst = os.path.join(OUT, sub)
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(os.path.join(SRC, 'atlas', sub), dst, ignore=shutil.ignore_patterns('*.txt'))

print('build: ok —', len(nodes), 'узлов,', len(imgs), 'картинок,', len(mp['spots']), 'мест на карте')
