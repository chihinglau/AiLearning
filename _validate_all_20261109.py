# -*- coding: utf-8 -*-
"""批量校验 20261109 全册分片：按 (subject, grade) 分组调用 _validate_daily.py。"""
import subprocess
from pathlib import Path

ROOT = Path(r'D:\ai\prj\trae\HuaWei\AiLearning')
PY = ROOT / 'backend' / '.venv' / 'Scripts' / 'python.exe'
VAL = ROOT / 'docs' / 'content-templates' / '_validate_daily.py'
BASE = ROOT / 'docs' / 'content-templates'
MANIFEST = BASE / '_import-manifest.json'
DATE = '20261109'

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
DAILY = BASE / 'daily'
SUBJECTS = ['math', 'chinese', 'english', 'politics',
            'biology', 'geography', 'history', 'physics', 'chemistry']
GRADES = [7, 9]


def outline_for(subj, g):
    if subj == 'math' and g == 9:
        return OUTLINE['math_g9']
    return OUTLINE[subj]


total_ok = total_fail = total_warn = 0
fail_details = []
for subj in SUBJECTS:
    for g in GRADES:
        files = sorted((DAILY / subj / f'g{g}').glob(f'{subj}_g{g}_first_{DATE}*.json'))
        if not files:
            print(f'  [缺] {subj} g{g}: 无文件')
            continue
        argv = [str(PY), str(VAL), *[str(f) for f in files],
                '--expect-subject', subj, '--expect-grade', str(g),
                '--expect-version', VERSION[subj], '--expect-semester', 'first',
                '--outline', str(outline_for(subj, g)), '--manifest', str(MANIFEST)]
        res = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding='utf-8', errors='replace')
        out = res.stdout
        err_files = []
        cur = None
        for line in out.splitlines():
            if line.startswith('文件：'):
                cur = line[len('文件：'):]
            elif '处错误' in line:
                n = int(line.split('处错误')[0].strip())
                if n > 0:
                    err_files.append((cur, line.strip()))
        n_warn = out.count('[提醒]')
        ok = len(files) - len(err_files)
        total_ok += ok
        total_fail += len(err_files)
        total_warn += n_warn
        status = 'OK' if not err_files else 'FAIL'
        print(f'  {subj} g{g}: {len(files)} files, ok={ok}, warn={n_warn}, fail={len(err_files)} [{status}]')
        for fn, msg in err_files:
            fail_details.append((subj, g, fn, msg))
            print(f'      ✗ {fn}: {msg}')

print('=' * 60)
print(f'SUMMARY: ok={total_ok} warn={total_warn} fail={total_fail} (files total={total_ok+total_fail})')
if fail_details:
    print('FAIL DETAILS:')
    for subj, g, fn, msg in fail_details:
        print(f'  {subj} g{g} {fn}: {msg}')
