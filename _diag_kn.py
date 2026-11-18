# -*- coding: utf-8 -*-
import json
from pathlib import Path
p = Path(r'D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\daily_consolidated\math\g8\math_g8_first_20261109_book.json')
d = json.loads(p.read_text(encoding='utf-8'))
for k in d['knowledge'][:14]:
    print({x: k.get(x) for x in ('node_type', 'name', 'parent', 'order_index')})
print('chapters:', [c['name'] for c in d['chapters']][:8])
q = d['chapters'][0]['questions'][0]
print('q keys:', list(q.keys()), 'kp=', q.get('knowledge_point'))
print('chapter0 name:', d['chapters'][0]['name'])
