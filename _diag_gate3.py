# -*- coding: utf-8 -*-
"""只读：验证「题挂载 section 被多个章共用」能否作为 P3 第三道门的判据。"""
import json
from pathlib import Path
from collections import defaultdict

DIR = Path(r'D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\daily_consolidated')
for f in sorted(DIR.rglob('*_book.json')):
    d = json.loads(f.read_text(encoding='utf-8'))
    parent = {k['name']: k.get('parent') for k in d.get('knowledge') or [] if k.get('node_type') == 'point'}
    secnames = {k['name'] for k in d.get('knowledge') or [] if k.get('node_type') == 'section'}
    owner = defaultdict(set)
    undecided = 0
    for c in d.get('chapters') or []:
        for q in c.get('questions') or []:
            kp = q.get('knowledge_point')
            sec = parent.get(kp) or (kp if kp in secnames else None)
            if sec is None:
                undecided += 1
                continue
            owner[sec].add(c.get('name'))
    shared_q = 0
    for c in d.get('chapters') or []:
        for q in c.get('questions') or []:
            kp = q.get('knowledge_point')
            sec = parent.get(kp) or (kp if kp in secnames else None)
            if sec and len(owner[sec]) > 1:
                shared_q += 1
    tag = 'GOOD' if f.parent.name in ('g1', 'g8') else 'new '
    print(f'{tag} {f.parent.parent.name}/{f.parent.name}: sharedSections='
          f'{sum(1 for v in owner.values() if len(v)>1)} sharedQ={shared_q} unresolvedKP={undecided}')
