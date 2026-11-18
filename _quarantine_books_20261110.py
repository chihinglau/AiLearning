# -*- coding: utf-8 -*-
"""2026-11-10 评审 P0-1：把不合格整册改名隔离，只留已入库的 g1/g8 12 册。

- 默认只出方案（dry-run）；--apply 才改名；--restore 依据留痕文件一键还原。
- 改名后 `rglob('*_book.json')` / `--pattern "*_book.json"` 都不再匹配隔离件；
  `_validate_daily.py` 目录模式默认跳过 *.quarantined.json（--include-quarantined 可复核）。
- 留痕：exports/review_20261110/quarantine_manifest_20261110.json
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(r'D:\ai\prj\trae\HuaWei\AiLearning')
BOOKS = ROOT / 'docs' / 'content-templates' / 'daily_consolidated'
TRACE = ROOT / 'docs' / 'content-templates' / 'exports' / 'review_20261110' / 'quarantine_manifest_20261110.json'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--keep-grades', default='1,8', help='保留的年级（已入库），逗号分隔')
    ap.add_argument('--apply', action='store_true', help='真正改名（默认 dry-run）')
    ap.add_argument('--restore', action='store_true', help='按留痕还原')
    args = ap.parse_args()

    if args.restore:
        if not TRACE.is_file():
            print('无留痕文件，无法还原')
            return 1
        pairs = json.loads(TRACE.read_text(encoding='utf-8'))['pairs']
        n = 0
        for old, new in pairs:
            o, w = BOOKS / old, BOOKS / new
            if w.is_file() and not o.exists():
                w.rename(o)
                n += 1
        print(f'已还原 {n}/{len(pairs)} 份')
        return 0

    keep = {g.strip() for g in args.keep_grades.split(',') if g.strip()}
    books = sorted(BOOKS.rglob('*_book.json'))

    def grade_of(p: Path) -> str:
        return p.parent.name.lstrip('g')

    quarantine = [p for p in books if grade_of(p) not in keep]
    keep_list = [p for p in books if grade_of(p) in keep]
    print(f'整册 {len(books)} 份：保留 {len(keep_list)} 份（grades={sorted(keep)}），隔离 {len(quarantine)} 份')
    for p in quarantine:
        print(f'  [隔离] {p.relative_to(BOOKS).as_posix()}')

    if not args.apply:
        print('\n[dry-run] 未改任何文件；确认后加 --apply')
        return 0
    pairs = []
    for p in quarantine:
        rel = p.relative_to(BOOKS)
        new_rel = rel.with_name(rel.name[:-len('.json')] + '.quarantined.json')
        new = BOOKS / new_rel
        if new.exists():
            print(f'[跳过] 目标已存在：{new_rel.as_posix()}')
            continue
        p.rename(new)
        pairs.append([rel.as_posix(), new_rel.as_posix()])
    TRACE.parent.mkdir(parents=True, exist_ok=True)
    TRACE.write_text(json.dumps({
        'schema_version': 1, 'reason': '2026-11-10 daily_consolidated 评审 P0-1',
        'keep_grades': sorted(keep), 'stamp': '20261109', 'pairs': pairs,
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'\n[完成] 隔离 {len(pairs)} 份；留痕 {TRACE}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
