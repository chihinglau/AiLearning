"""数学按单元（章节）铺量：以「计算可验证」的题型为核心，答案由程序计算得出。

每个章节产出 4 选择 + 5 填空 + 3 解答（单元卷需求：choice4 / fill5 / answer3），
题型按章节主题关键词选择（加减、乘除、小数、分数、方程、图形、统计、概率、函数、比与百分）。
所有数值由 (chapter_id, i) 决定，重跑结果一致，并可机器验算。
"""

from __future__ import annotations

from fractions import Fraction


def _rnd(a: int, b: int, seed: int) -> int:
    return a + (seed * 2654435761) % (b - a + 1) if b > a else a


def _fmt(x: float) -> str:
    if isinstance(x, Fraction):
        return f"{x.numerator}/{x.denominator}" if x.denominator != 1 else str(x.numerator)
    if isinstance(x, float):
        return str(int(x)) if x == int(x) else f"{x:.2f}".rstrip("0").rstrip(".")
    return str(x)


def _distractors(ans: str, seed: int) -> list[str]:
    """由正确答案派生三个不同干扰项（数值型）。"""
    base = float(ans)
    cands = [base + 1, base - 1, base + 10, base - 10, base * 2, base + 2]
    out = []
    for c in cands:
        v = _fmt(round(c, 2))
        if v != ans and v not in out and v not in {_fmt(-1)}:
            out.append(v)
        if len(out) == 3:
            break
    return out


def _mc(stem: str, answer: str, seed: int, options: list[str] | None = None):
    opts = options or ([answer] + _distractors(answer, seed))
    # 确定性打乱
    idx = [0, 1, 2, 3]
    for k in range(3):
        idx[k], idx[3 - k] = idx[3 - k], idx[k] if (seed + k) % 2 else idx[k]
    rotated = opts[(seed % 4):] + opts[:(seed % 4)]
    keys = "ABCD"
    return {
        "stem": stem,
        "options": [{"key": keys[i], "text": t} for i, t in enumerate(rotated)],
        "answer": keys[rotated.index(answer)],
        "analysis": f"正确答案为 {answer}。",
    }


# ---------------- 各主题内核：返回 (choice, fill, answer) ----------------

def _arith(chapter_id: int, i: int, op: str):
    a = _rnd(11, 89, chapter_id + i)
    b = _rnd(11, 89, chapter_id * 3 + i)
    if op == "+":
        res = a + b
        return (
            _mc(f"{a}+{b}的结果是（  ）", _fmt(res), chapter_id + i),
            {"stem": f"{a}+{b}=（  ）", "answer": _fmt(res)},
            {"stem": f"小明有 {a} 张卡片，又买了 {b} 张，一共有多少张？写出算式。",
             "answer": f"{a}+{b}={res}（张），一共 {res} 张。"},
        )
    res = a + b if a > b else b - a
    big, small = (a, b) if a > b else (b, a)
    res = big - small
    return (
        _mc(f"{big}-{small}的结果是（  ）", _fmt(res), chapter_id + i),
        {"stem": f"{big}-{small}=（  ）", "answer": _fmt(res)},
        {"stem": f"图书角有 {big} 本书，借出 {small} 本，还剩多少本？写出算式。",
         "answer": f"{big}-{small}={res}（本），还剩 {res} 本。"},
    )


def _muldiv(chapter_id: int, i: int):
    a = _rnd(2, 9, chapter_id + i)
    b = _rnd(2, 9, chapter_id * 5 + i)
    prod = a * b
    return (
        _mc(f"{a}×{b}的结果是（  ）", _fmt(prod), chapter_id + i),
        {"stem": f"{prod}÷{b}=（  ）", "answer": _fmt(a)},
        {"stem": f"每盒有 {a} 支铅笔，{b} 盒一共有多少支？写出算式。",
         "answer": f"{a}×{b}={prod}（支），一共 {prod} 支。"},
    )


def _decimal(chapter_id: int, i: int):
    a = (_rnd(11, 89, chapter_id + i)) / 10
    b = (_rnd(11, 79, chapter_id * 7 + i)) / 10
    res = round(a + b, 1)
    return (
        _mc(f"{_fmt(a)}+{_fmt(b)}的结果是（  ）", _fmt(res), chapter_id + i),
        {"stem": f"{_fmt(a)}+{_fmt(b)}=（  ）", "answer": _fmt(res)},
        {"stem": f"一根绳子长 {_fmt(a)} 米，另一根长 {_fmt(b)} 米，两根一共多少米？",
         "answer": f"{_fmt(a)}+{_fmt(b)}={_fmt(res)}（米）。"},
    )


def _fraction(chapter_id: int, i: int):
    d = _rnd(3, 9, chapter_id + i)
    n1 = _rnd(1, d - 1, chapter_id * 2 + i)
    n2 = _rnd(1, d - n1, chapter_id * 3 + i)
    total = n1 + n2
    res = Fraction(total, d)
    return (
        _mc(f"{n1}/{d}+{n2}/{d}的结果是（  ）",
            f"{res.numerator}/{res.denominator}",
            chapter_id + i,
            options=[f"{res.numerator}/{res.denominator}", f"{total}/{d * 2}",
                     f"{n1 + n2}/{2 * d}", f"{max(1, total - 1)}/{d}"]),
        {"stem": f"{n1}/{d}+{n2}/{d}=（  ）（结果用分数表示）",
         "answer": f"{res.numerator}/{res.denominator}"},
        {"stem": f"一张纸先用去 {n1}/{d}，又用去 {n2}/{d}，一共用去几分之几？",
         "answer": f"{n1}/{d}+{n2}/{d}={res.numerator}/{res.denominator}。"},
    )


def _equation(chapter_id: int, i: int):
    a = _rnd(2, 9, chapter_id + i)
    x = _rnd(2, 12, chapter_id * 3 + i)
    b = _rnd(3, 20, chapter_id * 5 + i)
    c = a * x + b
    return (
        _mc(f"方程 {a}x+{b}={c} 的解是 x=（  ）", _fmt(x), chapter_id + i),
        {"stem": f"若 {a}x+{b}={c}，则 x=（  ）", "answer": _fmt(x)},
        {"stem": f"解方程：{a}x+{b}={c}，写出过程。",
         "answer": f"{a}x={c}-{b}={c - b}，x={c - b}÷{a}={x}。"},
    )


def _geometry(chapter_id: int, i: int):
    l = _rnd(4, 15, chapter_id + i)
    w = _rnd(3, 12, chapter_id * 4 + i)
    area = l * w
    peri = 2 * (l + w)
    if i % 3 == 0:
        return (
            _mc("三角形的内角和是（  ）", "180°", chapter_id + i,
                options=["180°", "90°", "360°", "270°"]),
            {"stem": "长方形有（  ）条边，（  ）个直角。", "answer": ["4", "4"]},
            {"stem": f"一个长方形长 {l} 厘米、宽 {w} 厘米，求它的周长和面积。",
             "answer": f"周长=({l}+{w})×2={peri}（厘米），面积={l}×{w}={area}（平方厘米）。"},
        )
    return (
        _mc(f"长 {l} 厘米、宽 {w} 厘米的长方形，面积是（  ）平方厘米",
            _fmt(area), chapter_id + i),
        {"stem": f"长 {l} 厘米、宽 {w} 厘米的长方形，周长是（  ）厘米", "answer": _fmt(peri)},
        {"stem": f"一块长方形菜地长 {l} 米、宽 {w} 米，它的面积是多少平方米？",
         "answer": f"{l}×{w}={area}（平方米）。"},
    )


def _statistics(chapter_id: int, i: int):
    base = _rnd(10, 40, chapter_id + i)
    vals = [base, base + 2, base + 4, base + 6]
    mean = sum(vals) // 4
    return (
        _mc(f"数据 {'、'.join(map(str, vals))} 的平均数是（  ）", _fmt(mean), chapter_id + i),
        {"stem": f"{'、'.join(map(str, vals))} 这组数据的平均数是（  ）", "answer": _fmt(mean)},
        {"stem": f"四次数学测验的成绩分别是 {'、'.join(map(str, vals))} 分，平均分是多少？",
         "answer": f"({'+'.join(map(str, vals))})÷4={mean}（分）。"},
    )


def _probability(chapter_id: int, i: int):
    red = _rnd(2, 6, chapter_id + i)
    blue = _rnd(2, 6, chapter_id * 6 + i)
    total = red + blue
    f = Fraction(red, total)
    ans = f"{f.numerator}/{f.denominator}"
    return (
        _mc(f"袋中有 {red} 个红球、{blue} 个蓝球，任摸一个，摸到红球的概率是（  ）",
            ans, chapter_id + i,
            options=[ans, f"{blue}/{total}", "1/2", f"{red}/{red + 1}"]),
        {"stem": f"袋中 {red} 红 {blue} 蓝共 {total} 个球，摸到红球的概率是（  ）", "answer": ans},
        {"stem": f"袋中有 {red} 个红球和 {blue} 个蓝球，任摸一个，摸到红球的概率是多少？",
         "answer": f"{red}/{total}（即 {ans}）。"},
    )


def _function(chapter_id: int, i: int):
    k = _rnd(2, 5, chapter_id + i)
    b = _rnd(1, 9, chapter_id * 4 + i)
    x = _rnd(1, 6, chapter_id * 7 + i)
    y = k * x + b
    return (
        _mc(f"一次函数 y={k}x+{b}，当 x={x} 时，y=（  ）", _fmt(y), chapter_id + i),
        {"stem": f"y={k}x+{b}，当 x={x} 时，y=（  ）", "answer": _fmt(y)},
        {"stem": f"已知一次函数 y={k}x+{b}，求当 x={x} 时的函数值，并写出代入过程。",
         "answer": f"y={k}×{x}+{b}={y}。"},
    )


def _ratio(chapter_id: int, i: int):
    total = _rnd(20, 60, chapter_id + i) * 2
    part = total // 2
    pct = _rnd(10, 90, chapter_id * 3 + i)
    return (
        _mc(f"{part} 的 50% 是（  ）", _fmt(part * 0.5), chapter_id + i),
        {"stem": f"{total} 的 50% 是（  ）", "answer": _fmt(total * 0.5)},
        {"stem": f"一本书共 {total} 页，小明读了全书的 50%，他读了多少页？",
         "answer": f"{total}×50%={_fmt(total * 0.5)}（页）。"},
    )


KERNELS = {
    "加减": lambda cid, i: _arith(cid, i, "+" if i % 2 == 0 else "-"),
    "乘除": _muldiv,
    "小数": _decimal,
    "分数": _fraction,
    "方程": _equation,
    "字母": _equation,
    "图形": _geometry,
    "三角": _geometry,
    "平行": _geometry,
    "矩形": _geometry,
    "圆": _geometry,
    "面积": _geometry,
    "周长": _geometry,
    "统计": _statistics,
    "数据": _statistics,
    "概率": _probability,
    "函数": _function,
    "坐标": _function,
    "比": _ratio,
    "百分": _ratio,
    "比例": _ratio,
    "有理数": lambda cid, i: _arith(cid, i, "+" if i % 2 == 0 else "-"),
    "整式": _equation,
    "混合运算": lambda cid, i: _arith(cid, i, "+"),
    "测量": _geometry,
}


def kernel_for(chapter_name: str, grade: int):
    for key, fn in KERNELS.items():
        if key in (chapter_name or ""):
            return key, fn
    # 兜底：低年级加减，高年级方程/整式
    if grade <= 3:
        return "加减", KERNELS["加减"]
    if grade <= 6:
        return "乘除", KERNELS["乘除"]
    return "方程", KERNELS["方程"]


def items_for_chapter(chapter_id: int, chapter_name: str, grade: int):
    key, fn = kernel_for(chapter_name, grade)
    out = []
    for i in range(1, 5):
        c, _, _ = fn(chapter_id, i)
        out.append(("choice", c["stem"], c["options"], c["answer"], c["analysis"], 2))
    for i in range(5, 10):
        _, f, _ = fn(chapter_id, i)
        out.append(("fill", f["stem"], None, f["answer"], "按题意计算填空。", 3))
    for i in range(10, 13):
        _, _, a = fn(chapter_id, i)
        out.append(("answer", a["stem"], None, a["answer"], "写出算式与结果。", 3))
    return key, out


__all__ = ["items_for_chapter", "kernel_for"]
