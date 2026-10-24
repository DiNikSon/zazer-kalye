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
import json, os, shutil, subprocess, sys

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
shell = rd(SRC, 'atlas', 'shell.html')
assert '/*DATA*/' in shell
data = (data_js + '\n// Расшифровка, по абзацу на эпизод\nconst PARAS=' + paras + ';\nconst IMGS=' + json.dumps(imgs)
        + ';\nconst CLEAN=' + clean + ';\nconst NPC=' + npc + ';\n')
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

# 4. Лист и тесты — как есть
shutil.copyfile(os.path.join(SRC, 'sheet', 'list.html'), os.path.join(OUT, 'sheet.html'))
shutil.copyfile(os.path.join(SRC, 'tests', 'stats.html'), os.path.join(OUT, 'stats.html'))
shutil.copyfile(os.path.join(SRC, 'tests', 'skills.html'), os.path.join(OUT, 'skills.html'))

# 5. картинки рядом со страницами (для локального просмотра build/)
dst = os.path.join(OUT, 'img')
shutil.rmtree(dst, ignore_errors=True)
shutil.copytree(img_dir, dst)

print('build: ok —', len(nodes), 'узлов,', len(imgs), 'картинок')
