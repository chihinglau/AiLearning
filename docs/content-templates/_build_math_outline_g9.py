# -*- coding: utf-8 -*-
"""数学（北师大版）九年级上/下大纲 + 章节骨架。

此前数学大纲只做到 1-8 年级（自动化范围），导致九年级上下两册没有任何章节，
清理占位章节时被误停用。本脚本补齐这两册。

来源：
  九年级上册（2026 秋版）http://www.dzkbw.com/books/bsd/shuxue/9s_2026/001.htm
  九年级下册            http://www.dzkbw.com/books/bsd/shuxue/9x/001.htm
只收章/节名等事实性短名，不摘正文。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "baseline"
STAMP = "20261107"

BOOKS = {
    "first": {
        "title": "九年级上册（2026 秋版）",
        "source": "http://www.dzkbw.com/books/bsd/shuxue/9s_2026/001.htm",
        "chapters": [
            ("第一章 特殊平行四边形", ["1.认识特殊平行四边形", "2.菱形的性质与判定", "3.矩形的性质与判定",
                                        "4.正方形的性质与判定", "问题解决活动：作内嵌于正方形的正八边形"]),
            ("第二章 一元二次方程", ["1.认识一元二次方程", "2.一元二次方程的解法",
                                      "3.一元二次方程的根与系数的关系", "4.一元二次方程的应用"]),
            ("第三章 图形的相似", ["1.相似多边形", "2.探索三角形相似的条件", "3.相似三角形判定定理的证明",
                                    "4.相似三角形的性质", "5.图形的位似", "问题解决活动：利用相似三角形测高"]),
            ("第四章 投影与视图", ["1.投影", "2.视图"]),
            ("第五章 二次函数", ["1.认识二次函数", "2.二次函数的图象", "3.二次函数的应用",
                                  "4.二次函数与一元二次方程", "问题解决活动：怎样围面积最大"]),
            ("第六章 概率的进一步认识", ["1.用树状图或表格求概率", "2.用频率估计概率"]),
            ("综合与实践 池塘里有多少条鱼", []),
        ],
    },
    "second": {
        "title": "九年级下册",
        "source": "http://www.dzkbw.com/books/bsd/shuxue/9x/001.htm",
        "chapters": [
            ("第一章 直角三角形的边角关系", ["1 锐角三角函数", "2 30°，45°，60°角的三角函数值", "3 三角函数的计算",
                                              "4 解直角三角形", "5 三角函数的应用", "6 利用三角函数测高"]),
            ("第二章 二次函数", ["1 二次函数", "2 二次函数的图象与性质", "3 确定二次函数的表达式",
                                  "4 二次函数的应用", "5 二次函数与一元二次方程"]),
            ("第三章 圆", ["1 圆", "2 圆的对称性", "*3 垂径定理", "4 圆周角和圆心角的关系", "5 确定圆的条件",
                           "6 直线和圆的位置关系", "*7 切线长定理", "8 圆内接正多边形", "9 弧长及扇形的面积"]),
            ("综合与实践 视力的变化", []),
            ("综合与实践 哪种方式更合算", []),
            ("综合与实践 设计遮阳篷", []),
            ("总复习", []),
        ],
    },
}


def render_outline(semester: str) -> str:
    book = BOOKS[semester]
    zh = "上册" if semester == "first" else "下册"
    lines = [f"# 数学 九年级{zh}教材大纲基线（北师大版）", "",
             "## 一、口径", "",
             "- 深圳初中数学 9 年级用北师大版；本册此前未纳入 1-8 年级的自动化范围，单独成文。",
             f"- 来源：`{book['source']}`（{book['title']}）。",
             "- 只收章名与小节名等事实性短名，不含正文、例题与习题。",
             "",
             f"## 二、九年级{zh}目录", "",
             "| 序 | 章 | 节（课时） |", "|---|---|---|"]
    for i, (chapter, sections) in enumerate(book["chapters"], 1):
        lines.append(f"| {i} | {chapter} / {chapter.split(' ')[0]} | {' / '.join(sections) if sections else '—'} |")
    lines += ["", "## 三、待补清单", "",
              "- 本册仅有的章名与节名来自电子课本网目录页；课时级颗粒度（含问题解决活动、复习题）按上表推进。",
              "- 若日后深圳改用其他版本，需重取本文件。",
              ""]
    return "\n".join(lines)


def build_skeleton(semester: str) -> dict:
    book = BOOKS[semester]
    return {
        "subject": "math",
        "grade": 9,
        "version": "北师大版",
        "semester": semester,
        "chapters": [
            {
                "name": chapter,
                "order_index": i,
                "summary": "教材目录骨架（章节占位，待补知识点与题目）",
                "questions": [],
            }
            for i, (chapter, _sections) in enumerate(book["chapters"], 1)
        ],
    }


def main() -> None:
    out_dir = BASE / "_skeleton_math_g9"
    out_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for semester in ("first", "second"):
        text = render_outline(semester)
        p = BASE / f"_outline_math_g9_{semester}_latest.md"
        p.write_text(text, encoding="utf-8")
        doc = build_skeleton(semester)
        sp = out_dir / f"chapters_math_g9_{semester}_{STAMP}.json"
        sp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        total += len(doc["chapters"])
        print(f"[ok] {p.name} / {sp.name}: {len(doc['chapters'])} 章")
    print(f"[ok] 合计 {total} 章 → {out_dir}")


if __name__ == "__main__":
    main()
