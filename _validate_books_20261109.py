# -*- coding: utf-8 -*-
"""校验 20261109 整册归集文件（*_book.json），覆盖 g7/g9 全学科。"""
import subprocess
from pathlib import Path

ROOT = Path(r'D:\ai\prj\trae\HuaWei\AiLearning')
PY = ROOT / 'backend' / '.venv' / 'Scripts' / 'python.exe'
VAL = ROOT / 'docs' / 'content-templates' / '_validate_daily.py'
BASE = ROOT / 'docs' / 'content-templates'
MANIFEST = BASE / '_import-manifest.json'
OUTLINE = {
    'math': BASE / 'baseline' / '_outline_math_first_latest.md',
    'math_g9': BASE / 'baseline' / '_outline_math_g9_first_latest.md',
    'chinese': BASE / 'baseline' / '_outline_chinese_first_latest.md',
    'english': BASE / 'baseline' / '_outline_english_first_latest.md',
    'politics': BASE / 'baseline' / '_outline_politics_first_latest.md',
    'biology': BASE / 'baseline' / '_outline_biology_first_latest.md',
    'geography': BASE / 'baseline' / '_outline_geography_first_latest.md',
    'history': BASE / 'baseline' / '_outline_history_first_latest.md',
    'physics': BASE / 'baseline' / '_outline_physics_first_latest.md',
    'chemistry': BASE / 'baseline' / '_outline_chemistry_first_latest.md',
}
VERSION = {'math': '北师大版', 'chinese': '人教版', 'english': '牛津深圳版', 'politics': '部编版',
           'biology': '人教版', 'geography': '湘教版', 'history': '部编版',
           'physics': '人教版', 'chemistry': '人教版'}
CONS = BASE / 'daily_consolidated'
SUBJECTS = ['math', 'chinese', 'english', 'politics',
            'biology', 'geography', 'history', 'physics', 'chemistry']
GRADES = [7, 9]


def outline_for(subj, g):
    if subj == 'math' and g == 9:
        return OUTLINE['math_g9']
    return OUTLINE[subj]


total_ok = total_fail = 0
fail_details = []
for subj in SUBJECTS:
    for g in GRADES:
        f = CONS / subj / f'g{g}' / f'{subj}_g{g}_first_20261109_book.json'
        if not f.is_file():
            continue
        argv = [str(PY), str(VAL), str(f),
                '--expect-subject', subj, '--expect-grade', str(g),
                '--expect-version', VERSION[subj], '--expect-semester', 'first',
                '--outline', str(outline_for(subj, g)), '--manifest', str(MANIFEST)]
        res = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding='utf-8', errors='replace')
        out = res.stdout
        n_err = 0
        cur_errs = []
        for line in out.splitlines():
            if '处错误' in line:
                n = int(line.split('处错误')[0].strip())
                if n > 0:
                    n_err = n
                    cur_errs.append(line.strip())
        if n_err:
            total_fail += 1
            fail_details.append((subj, g, cur_errs))
            print(f'  {subj} g{g}: FAIL ({n_err} err)')
        else:
            total_ok += 1
            print(f'  {subj} g{g}: OK')

print('=' * 60)
print(f'BOOKS SUMMARY: ok={total_ok} fail={total_fail}')
for subj, g, errs in fail_details:
    print(f'  FAIL {subj} g{g}:')
    for e in errs:
        print(f'    {e}')
