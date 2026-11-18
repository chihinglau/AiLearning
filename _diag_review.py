# -*- coding: utf-8 -*-
"""只读诊断：复核评审报告的校验错误与整册结构问题。"""
import os, sys, subprocess, json
from pathlib import Path

P = Path(r'D:\ai\prj\trae\HuaWei\AiLearning')
PY = P / 'backend' / '.venv' / 'Scripts' / 'python.exe'
VAL = P / 'docs' / 'content-templates' / '_validate_daily.py'
MAN = P / 'docs' / 'content-templates' / '_import-manifest.json'
DIR = P / 'docs' / 'content-templates' / 'daily_consolidated'
ENV = dict(os.environ, PYTHONIOENCODING='utf-8')


def validate(path):
    r = subprocess.run([str(PY), str(VAL), str(path), '--manifest', str(MAN)],
                       capture_output=True, text=True, encoding='utf-8', errors='replace', env=ENV)
    errs = [l.strip() for l in r.stdout.splitlines() if '[错误]' in l]
    return r.returncode, errs


for rel in ['biology/g7/biology_g7_first_20261109_book.json',
            'english/g3/english_g3_first_20261109_book.json',
            'physics/g9/physics_g9_first_20261109_book.json',
            'math/g9/math_g9_first_20261109_book.json',
            'chinese/g3/chinese_g3_first_20261109_book.json']:
    rc, errs = validate(DIR / rel)
    print(f'== {rel} rc={rc} errors={len(errs)}')
    for e in errs[:2]:
        print('   ', e[:210])

# 全目录复核
rc, errs = validate(DIR)
print('== 全目录 rc=', rc, '错误行=', len(errs))
print('   错误样本:', errs[:2])
