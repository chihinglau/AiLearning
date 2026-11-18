# -*- coding: utf-8 -*-
"""只读：统计整册结构，用于标定 P3 验收门槛。"""
import json
from pathlib import Path

DIR = Path(r'D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\daily_consolidated')
GOOD_GRADES = {'g1', 'g8'}
CLICHE = ['更可取的学习做法', '可以先梳理', '结合实例分析比单纯背诵',
          '举一个生活中用到', '值得提倡的', '先理解概念再结合实例分析']

books = sorted(DIR.rglob('*_book.json'))
print('books =', len(books))
for f in books:
    d = json.loads(f.read_text(encoding='utf-8'))
    kn = d.get('knowledge') or []
    secs = [k['name'] for k in kn if k.get('node_type') == 'section']
    pts = [k['name'] for k in kn if k.get('node_type') == 'point']
    chaps = d.get('chapters') or []
    stems = []
    nq = 0
    cl = 0
    for c in chaps:
        for q in c.get('questions') or []:
            nq += 1
            stems.append((c.get('name'), q.get('q_type'), (q.get('stem') or '').strip()))
            if any(x in (q.get('stem') or '') for x in CLICHE):
                cl += 1
    # 跨章重复题种
    seen = {}
    dup = 0
    for ch, qt, st in stems:
        key = (qt, st)
        if key in seen and seen[key] != ch:
            dup += 1
        else:
            seen[key] = ch
    # 挂载点 parent
    parent = {k['name']: k.get('parent') for k in kn if k.get('node_type') == 'point'}
    mismatch = 0
    for c in chaps:
        for q in c.get('questions') or []:
            kp = q.get('knowledge_point')
            if kp in parent:
                if parent[kp] != c.get('name'):
                    mismatch += 1
    tag = 'GOOD' if f.parent.name in GOOD_GRADES else 'new '
    print(f'{tag} {f.parent.parent.name}/{f.parent.name}: ch={len(chaps):2d} sec={len(secs):2d} '
          f'pt={len(pts):3d} q={nq:4d} dupCross={dup:4d} mismatch={mismatch:3d} cliche={cl:4d}')
