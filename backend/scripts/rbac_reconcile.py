"""RBAC 目录与用户角色对账脚本（P2-01，D-03 §9.2 阶段 B）。

用法：

    python -m scripts.rbac_reconcile            # 只检查，输出差异并返回非 0
    python -m scripts.rbac_reconcile --fix      # 同步常量目录并修复 user_roles
"""

import argparse
import json
import sys

from app.db.session import SessionLocal
from app.services.rbac import has_drift, reconcile


def main() -> int:
    parser = argparse.ArgumentParser(description="RBAC 数据表对账")
    parser.add_argument("--fix", action="store_true", help="发现差异后执行修复")
    args = parser.parse_args()

    with SessionLocal() as db:
        report = reconcile(db, fix=args.fix)
        if args.fix:
            db.commit()

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not args.fix and has_drift(report):
        print("检测到 RBAC 差异，可加 --fix 修复", file=sys.stderr)
        return 1
    print("RBAC 对账通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
