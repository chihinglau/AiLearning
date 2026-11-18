# -*- coding: utf-8 -*-
"""为自建知识点（selfbank:kp:*）补齐 explanation 与 prerequisites。

用法（cwd=backend，PYTHONPATH=backend）：
    python scripts/fill_kp_explanations.py            # 预演
    python scripts/fill_kp_explanations.py --apply    # 落库

前置关系按「类别链」建立：同一前置类别下的所有 KP id 都写入 prerequisites，
并限制在 3 条以内；找不到前置类别时留空而不是编造。
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.content import KnowledgePoint
from scripts.selfbank_kp_explanations import EXPLANATIONS, PREREQUISITES, category_of


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="实际落库（默认只预演）")
    opts = ap.parse_args()

    with SessionLocal() as db:
        kps = list(db.scalars(select(KnowledgePoint).where(
            KnowledgePoint.source_ref.like("selfbank:kp:%"))))
        print(f"自建知识点 {len(kps)} 条")

        by_cat: dict[str, list[KnowledgePoint]] = defaultdict(list)
        unknown = []
        for kp in kps:
            cat = category_of(kp.name)
            if cat is None:
                unknown.append(kp.name)
            else:
                by_cat[cat].append(kp)

        if unknown:
            print(f"未匹配讲解的类别 {len(unknown)} 条（保持原样）：")
            for name in sorted(set(unknown))[:10]:
                print("   ", name)

        filled = 0
        pre_filled = 0
        for cat, items in sorted(by_cat.items()):
            text = EXPLANATIONS[cat]
            pre_cats = PREREQUISITES.get(cat, ())
            pre_ids: list[int] = []
            for pcat in pre_cats:
                for p in by_cat.get(pcat, []):
                    if p.id not in pre_ids:
                        pre_ids.append(p.id)
            pre_ids = pre_ids[:3]
            for kp in items:
                changed = False
                if kp.explanation != text:
                    kp.explanation = text
                    changed = True
                    filled += 1
                if pre_ids and list(kp.prerequisites or []) != pre_ids and kp.id not in pre_ids:
                    kp.prerequisites = pre_ids
                    pre_filled += 1
                elif not pre_ids and kp.prerequisites is None:
                    pass  # 无前置类别，保持空，不编造
            print(f"   {cat:<32} KP={len(items):<2} 前置={pre_ids}")

        print(f"\n写入讲解 {filled} 条 / 写入前置 {pre_filled} 条")
        if opts.apply:
            db.commit()
            print("已提交")
            # 复核
            kps2 = list(db.scalars(select(KnowledgePoint).where(
                KnowledgePoint.source_ref.like("selfbank:kp:%"))))
            miss_ex = sum(1 for k in kps2 if not (k.explanation or "").strip())
            has_pre = sum(1 for k in kps2 if k.prerequisites)
            print(f"复核：explanation 空 {miss_ex}/{len(kps2)}，有前置 {has_pre}/{len(kps2)}")
        else:
            db.rollback()
            print("预演完成（未落库），加 --apply 生效")
    return 0


if __name__ == "__main__":
    sys.exit(main())
