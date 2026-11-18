# -*- coding: utf-8 -*-
"""检查 g7/g9 各 skeleton 章节名是否落在对应大纲允许名内。"""
import sys, json
from pathlib import Path

ROOT = Path(r'D:\ai\prj\trae\HuaWei\AiLearning')
CT = ROOT / 'docs' / 'content-templates'
BASE = CT / 'baseline'
sys.path.insert(0, str(CT))
from _validate_daily import load_outline

SKEL = BASE / '_skeleton_first'
SCOPE = {
    'biology': [7], 'geography': [7], 'history': [7, 9], 'physics': [9], 'chemistry': [9],
    'math': [7, 9], 'chinese': [7, 9], 'english': [7, 9], 'politics': [7, 9],
}

problems = 0
for subj, grades in SCOPE.items():
    for g in grades:
        outline_path = BASE / (f'_outline_{subj}_g9_first_latest.md' if (subj == 'math' and g == 9)
                                else f'_outline_{subj}_first_latest.md')
        subject, grade_map, pair_map = load_outline(outline_path)
        allowed = grade_map.get(g, set())
        skel = SKEL / f'chapters_{subj}_g{g}_first_20261107.json'
        data = json.loads(skel.read_text(encoding='utf-8'))
        names = [c['name'] for c in data['chapters']]
        missing = [n for n in names if n not in allowed]
        if missing:
            problems += len(missing)
            print(f'[缺] {subj} g{g}: 允许名 {len(allowed)}；缺失章节 -> {missing}')
            print(f'     允许名样例: {sorted(allowed)[:8]}')
        else:
            print(f'[OK] {subj} g{g}: {len(names)} 章全部命中大纲（允许名 {len(allowed)}）')
print('=' * 50)
print(f'PROBLEMS={problems}')
