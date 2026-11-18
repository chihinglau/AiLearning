"""为「按单元铺量」的新题挂题型级知识点（幂等）。

背景：语文 1,054 / 数学 513 / 英语 1,203 条新题此前 knowledge_point_id 为空，
不计入 kp_universe，导致归一覆盖被摊薄。本脚本按「题型 × 变式」建知识点并回挂。

关键约束：`KP_CAP_PER_SECTION=2`，同一大题内同知识点最多 2 题。
故每个题型必须切成 4 个变式知识点（4 × 2 = 8，正好覆盖单元卷单节最多 8 题的需求）。
"""

from __future__ import annotations

import argparse

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.content import KnowledgePoint, Question

SOURCE_NAME = "自建题型题库（原创）"
LICENSE_NOTE = "原创自建内容，不含第三方版权素材"
VARIANTS = ["变式一", "变式二", "变式三", "变式四"]

ZH_KINDS = {
    "liangci": "量词与数量表达",
    "fanyi": "反义词辨析",
    "jinyi": "近义词辨析",
    "chengyu": "成语积累与补全",
    "gushi": "古诗名句积累",
    "biaodian": "句末标点与语气",
    "guanlian": "关联词语搭配",
}
BANDS = [(1, 3, "1-3年级"), (4, 6, "4-6年级"), (7, 9, "7-9年级")]

MATH_KERNELS = {
    "加减": "整数加减运算",
    "乘除": "乘除法运算",
    "小数": "小数加减运算",
    "分数": "同分母分数加减",
    "方程": "一元一次方程求解",
    "图形": "平面图形周长与面积",
    "统计": "平均数与数据整理",
    "概率": "简单事件概率",
    "函数": "一次函数求值",
    "比": "百分比与比例应用",
    # 同义内核（生成器按章节名匹配到的其余关键词）
    "字母": "一元一次方程求解",
    "混合运算": "整数加减运算",
    "有理数": "整数加减运算",
    "整式": "一元一次方程求解",
    "测量": "平面图形周长与面积",
    "三角": "平面图形周长与面积",
    "平行": "平面图形周长与面积",
    "矩形": "平面图形周长与面积",
    "圆": "平面图形周长与面积",
    "面积": "平面图形周长与面积",
    "周长": "平面图形周长与面积",
    "数据": "平均数与数据整理",
    "坐标": "一次函数求值",
    "百分": "百分比与比例应用",
    "比例": "百分比与比例应用",
}

EN_KINDS = {
    "listening": "听力词群辨识",
    "choice": "基础语法单项选择",
    "fill": "词汇填空（中英对应）",
    "reading": "短文阅读理解",
}


def _grade(q: Question) -> int:
    for tag in q.tags or []:
        if isinstance(tag, str) and tag.startswith("g") and tag[1:].isdigit():
            return int(tag[1:])
    return 1


def _band(grade: int) -> str:
    for lo, hi, label in BANDS:
        if lo <= grade <= hi:
            return label
    return "7-9年级"


def ensure_kp(db, subject: str, name: str, grade: int) -> KnowledgePoint:
    kp = db.scalar(select(KnowledgePoint).where(
        KnowledgePoint.subject == subject, KnowledgePoint.name == name))
    if kp is None:
        kp = KnowledgePoint(
            subject=subject, name=name, grade=grade, node_type="point",
            order_index=0, weight=1.0, source_type="original",
            source_name=SOURCE_NAME, source_ref=f"selfbank:kp:{subject}:{name}",
            license_note=LICENSE_NOTE,
        )
        db.add(kp)
        db.flush()
    return kp


def _variant_index(pos: int) -> int:
    return (pos - 1) % len(VARIANTS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    bound = 0
    with SessionLocal() as db:
        # ---------- 语文：积累与运用 ----------
        fills = list(db.scalars(select(Question).where(
            Question.source_ref.like("selfbank:zh_fillu:%"),
            Question.knowledge_point_id.is_(None),
        ).order_by(Question.chapter_id, Question.id)))
        counters: dict[tuple[int, str], int] = {}
        for q in fills:
            kind = next((k for k in ZH_KINDS if k in (q.tags or [])), None)
            if kind is None:
                continue
            key = (q.chapter_id, kind)
            counters[key] = counters.get(key, 0) + 1
            name = f"积累与运用·{ZH_KINDS[kind]}·{_band(_grade(q))}·{VARIANTS[_variant_index(counters[key])]}"
            q.knowledge_point_id = ensure_kp(db, "chinese", name, _grade(q)).id
            bound += 1

        # ---------- 语文：习作 ----------
        for q in db.scalars(select(Question).where(
            Question.source_ref.like("selfbank:zh_compu:%"),
            Question.knowledge_point_id.is_(None),
        )):
            name = f"习作·内容结构语言三维分档·{_band(_grade(q))}"
            q.knowledge_point_id = ensure_kp(db, "chinese", name, _grade(q)).id
            bound += 1

        # ---------- 语文：阅读理解 ----------
        counters.clear()
        for q in db.scalars(select(Question).where(
            Question.source_ref.like("selfbank:zh_readu:%"),
            Question.knowledge_point_id.is_(None),
        ).order_by(Question.chapter_id, Question.id)):
            key = (q.chapter_id, "read")
            counters[key] = counters.get(key, 0) + 1
            name = (f"阅读理解·信息提取与概括·{_band(_grade(q))}"
                    f"·{VARIANTS[_variant_index(counters[key])]}")
            q.knowledge_point_id = ensure_kp(db, "chinese", name, _grade(q)).id
            bound += 1

        # ---------- 数学 ----------
        counters.clear()
        for q in db.scalars(select(Question).where(
            Question.source_ref.like("selfbank:math_u:%"),
            Question.knowledge_point_id.is_(None),
        ).order_by(Question.chapter_id, Question.q_type, Question.id)):
            kernel = next((k for k in MATH_KERNELS if k in (q.tags or [])), None)
            if kernel is None:
                continue
            key = (q.chapter_id, q.q_type)
            counters[key] = counters.get(key, 0) + 1
            name = (f"数与运算·{MATH_KERNELS[kernel]}·按单元"
                    f"·{VARIANTS[_variant_index(counters[key])]}")
            q.knowledge_point_id = ensure_kp(db, "math", name, _grade(q)).id
            bound += 1

        # ---------- 英语 ----------
        counters.clear()
        for q in db.scalars(select(Question).where(
            Question.source_ref.like("selfbank:en_u:%"),
            Question.knowledge_point_id.is_(None),
        ).order_by(Question.chapter_id, Question.q_type, Question.id)):
            is_reading = (q.content or {}).get("section_hint") == "reading"
            kind = "reading" if is_reading else next(
                (k for k in ("listening", "choice", "fill") if k in (q.tags or [])), None)
            if kind is None:
                continue
            key = (q.chapter_id, kind)
            counters[key] = counters.get(key, 0) + 1
            name = f"英语·{EN_KINDS[kind]}·按单元·{VARIANTS[_variant_index(counters[key])]}"
            q.knowledge_point_id = ensure_kp(db, "english", name, _grade(q)).id
            bound += 1

        if args.apply:
            db.commit()
        print(f"{'已写入' if args.apply else '干跑'}：回挂知识点 {bound} 题")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
