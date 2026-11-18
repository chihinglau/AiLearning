"""g4/g5/g6 上册「计算与解答」与 g7–g9 下册「填空」供给补齐（幂等）。

用法：
    python scripts/seed_math_supplement_g4_g9.py --grades 4 5 6 7 8 9 --dry-run
    python scripts/seed_math_supplement_g4_g9.py --grades 4 5 6 7 8 9 --apply
"""

from __future__ import annotations

import argparse

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.content import Chapter, Question, Textbook

SOURCE_NAME = "自建题型题库（原创）"
LICENSE_NOTE = "原创自建内容，不含第三方版权素材"

SUPPLY = {
    # 教材 25：g4 上册，计算与解答 6 题
    25: {
        "answer": [
            ("计算：408×25。", "10200", "408×25=408×100÷4=10200。"),
            ("计算：720÷45。", "16", "45×16=720，所以 720÷45=16。"),
            ("计算：125×8+75×8。", "1600", "提取公因数：(125+75)×8=200×8=1600。"),
            ("一个长方形长 12 米，宽 8 米，求它的周长和面积。", "周长 40 米，面积 96 平方米", "周长=(12+8)×2=40（米）；面积=12×8=96（平方米）。"),
            ("学校买来 15 箱图书，每箱 24 本，一共多少本？", "360 本", "15×24=360（本）。"),
            ("计算：3600÷(25×4)。", "36", "25×4=100，3600÷100=36。"),
        ],
    },
    # 教材 33：g5 上册，计算与解答 6 题
    33: {
        "answer": [
            ("计算：2.5×4。", "10", "2.5×4=10。"),
            ("计算：0.75+1.25。", "2", "0.75+1.25=2.00，即 2。"),
            ("计算：3.6÷0.4。", "9", "3.6÷0.4=36÷4=9。"),
            ("一本书 12.5 元，买 4 本一共多少元？", "50 元", "12.5×4=50（元）。"),
            ("一个三角形的底是 8 厘米，高是 5 厘米，求它的面积。", "20 平方厘米", "三角形面积=底×高÷2=8×5÷2=20（平方厘米）。"),
            ("计算：4.8×2.5。", "12", "4.8×2.5=4.8×2+4.8×0.5=9.6+2.4=12。"),
        ],
    },
    # 教材 41：g6 上册，计算与解答 2 题
    41: {
        "answer": [
            ("计算：3/4 + 1/6。", "11/12", "通分：9/12+2/12=11/12。"),
            ("一根绳子长 12 米，用去它的 1/3，还剩多少米？", "8 米", "用去 12×1/3=4（米），还剩 12-4=8（米）。"),
        ],
    },
    # 教材 52：g7 下册，填空 8 题
    52: {
        "fill": [
            ("若 2x+3=11，则 x=____。", "4", "2x=8，x=4。"),
            ("3 的相反数是____。", "-3", "相反数只改变符号。"),
            ("计算 (-2)^3=____。", "-8", "(-2)×(-2)×(-2)=-8。"),
            ("方程 5x=20 的解是 x=____。", "4", "两边同除以 5，x=4。"),
            ("若 a=2，b=-3，则 a+b=____。", "-1", "2+(-3)=-1。"),
            ("12 的正因数共有____个。", "6", "12 的因数为 1、2、3、4、6、12，共 6 个。"),
            ("|-5|=____。", "5", "绝对值表示到原点的距离，|-5|=5。"),
            ("一个角的补角是 60°，这个角是____。", "120°", "补角之和为 180°，180°-60°=120°。"),
        ],
    },
    # 教材 65：g8 上册，填空 2 题
    65: {
        "fill": [
            ("计算 (-3)^2=____。", "9", "(-3)×(-3)=9。"),
            ("分解因式：x²-9=____。", "(x+3)(x-3)", "平方差公式 a²-b²=(a+b)(a-b)。"),
        ],
    },
    # 教材 66：g8 下册，填空 4 题 + 解答 2 题
    66: {
        "fill": [
            ("若 x²=16，则 x=____。", "±4", "16 的两个平方根为 4 和 -4。"),
            ("一次函数 y=2x+1 中，当 x=3 时 y=____。", "7", "y=2×3+1=7。"),
            ("√25=____。", "5", "25 的算术平方根是 5。"),
            ("数据 2、4、6 的平均数是____。", "4", "(2+4+6)÷3=4。"),
        ],
        "answer": [
            ("解方程：2x-5=7。", "x=6", "2x=12，x=6。"),
            ("计算：(a+2)(a-2)。", "a²-4", "平方差公式 (a+b)(a-b)=a²-b²。"),
        ],
    },
    # 教材 82：g9 下册，填空 4 题
    82: {
        "fill": [
            ("方程 x²-5x+6=0 的解是____。", "x=2 或 x=3", "因式分解为 (x-2)(x-3)=0。"),
            ("sin30°=____。", "1/2", "特殊角的三角函数值：sin30°=1/2。"),
            ("二次函数 y=x²-4 的顶点坐标是____。", "(0,-4)", "y=x² 向下平移 4 个单位，顶点为 (0,-4)。"),
            ("计算 2^(-1)=____。", "1/2", "负指数幂 a^(-n)=1/aⁿ。"),
        ],
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grades", nargs="+", type=int, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    plan: list[Question] = []
    with SessionLocal() as db:
        books = list(db.scalars(
            select(Textbook).where(Textbook.subject == "math", Textbook.grade.in_(args.grades))
        ))
        book_ids = {book.id for book in books}
        for book_id, spec in SUPPLY.items():
            if book_id not in book_ids:
                continue
            anchor = db.scalars(
                select(Chapter).where(Chapter.textbook_id == book_id)
                .order_by(Chapter.order_index, Chapter.id)
            ).first()
            if anchor is None:
                continue
            for q_type, items in spec.items():
                for index, (stem, value, analysis) in enumerate(items, start=1):
                    plan.append(Question(
                        chapter_id=anchor.id, knowledge_point_id=None,
                        subject="math", q_type=q_type,
                        content={"stem": stem},
                        options=None, answer={"value": value},
                        analysis=analysis, difficulty=3,
                        tags=[q_type, "自建补充"],
                        status="published", source_type="original", source_name=SOURCE_NAME,
                        source_ref=f"selfbank:math_supp:{book_id}:{q_type}:{index}",
                        license_note=LICENSE_NOTE,
                    ))

    print(f"计划写入 {len(plan)} 题（{sum(1 for q in plan if q.q_type=='fill')} 填空 / "
          f"{sum(1 for q in plan if q.q_type=='answer')} 解答）")
    if not args.apply:
        print("干跑模式：未写库")
        return 0

    created = skipped = 0
    with SessionLocal() as db:
        for question in plan:
            if db.scalar(select(Question.id).where(Question.source_ref == question.source_ref)):
                skipped += 1
                continue
            db.add(question)
            created += 1
        db.commit()
    print(f"入库完成：created={created} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
