"""学期切换与学年升级定时任务入口（D-03 §4.4）。

部署侧通过 cron / Windows 任务计划程序定期调用（建议每月 1 日执行一次，任务内自带月份判断与幂等保护）：

    .venv\\Scripts\\python.exe -m scripts.semester_jobs --job all
    .venv\\Scripts\\python.exe -m scripts.semester_jobs --job semester
    .venv\\Scripts\\python.exe -m scripts.semester_jobs --job promote
"""

import argparse
import json
from dataclasses import asdict

from app.db.session import SessionLocal
from app.services.promotion import promote_grades, switch_semester


def main() -> None:
    parser = argparse.ArgumentParser(description="学期切换 / 学年升级任务")
    parser.add_argument(
        "--job", choices=["semester", "promote", "all"], default="all", help="执行的任务"
    )
    args = parser.parse_args()

    result = {}
    with SessionLocal() as db:
        if args.job in ("semester", "all"):
            result["semester"] = asdict(switch_semester(db))
        if args.job in ("promote", "all"):
            result["promote"] = asdict(promote_grades(db))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
