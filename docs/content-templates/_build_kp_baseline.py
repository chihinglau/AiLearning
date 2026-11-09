"""重建知识点名称基线（只读库，不写库）

输出：
    baseline/_knowledge-points-baseline_<date>.json / .md
    baseline/_knowledge-points-baseline_latest.json / .md   （覆盖为最新）

语义与 2026-11-08 版本一致：subject -> grade -> name -> 库内出现次数；
次数 >= 2 表示同名歧义，导入时按名称引用会被拒绝。

用法：
    python _build_kp_baseline.py                 # 用今天日期
    python _build_kp_baseline.py --date 20261109
"""
import argparse, datetime, json, sqlite3, pathlib

CT = pathlib.Path(__file__).resolve().parent
DB = CT.parents[1] / "backend" / "ailearning_dev.db"

LABEL = {
    "biology": "生物", "chemistry": "化学", "chinese": "语文", "english": "英语",
    "geography": "地理", "history": "历史", "math": "数学", "physics": "物理",
    "politics": "道法",
}


def build(db_path: pathlib.Path):
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    rows = con.execute("""select subject, grade, name, count(*) from knowledge_points
                          where node_type='point'
                          group by subject, grade, name""").fetchall()
    con.close()
    names = {}
    for subject, grade, name, cnt in rows:
        names.setdefault(subject, {}).setdefault(str(grade), {})[name] = cnt
    return names


def write(names, date, out_dir: pathlib.Path):
    total = sum(len(v) for s in names.values() for v in s.values())
    amb = sum(1 for s in names.values() for v in s.values() for c in v.values() if c >= 2)
    meta = {
        "generated": f"{date[:4]}-{date[4:6]}-{date[6:]}",
        "source": "sqlite:///./ailearning_dev.db（只读）",
        "semantics": "subject -> grade -> name -> 库内出现次数；次数>=2 表示同名歧义，导入时引用会被拒绝",
        "scope": "node_type='point' 全量（1–12 年级在库知识点，含尚未生产的占位年级）；"
                 "旧版（2026-11-08）为 537 名的部分口径，本版按全量重算，数字变大属口径变化而非新增节点",
        "regenerate": "新增内容导入后需重新生成本文件，否则基线过期",
        "total_names": total,
        "ambiguous": amb,
    }
    payload = {"_meta": meta, "names": names}

    d = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    for suffix in (f"_{date}", "_latest"):
        (out_dir / f"_knowledge-points-baseline{suffix}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    lines = [f"# 知识点名称基线（{d}）", "",
             "> 来源：`sqlite:///./ailearning_dev.db`（只读）",
             "> 语义：subject → grade → name → 库内出现次数；次数 ≥ 2 表示同名，导入时按名称引用会被拒绝。",
             "> 范围：`node_type='point'` 全量（1–12 年级在库知识点）；旧版 537 名为部分口径，数字变大属口径变化。",
             "> 新增内容导入后请重新运行 `python _build_kp_baseline.py`，否则基线过期。", "",
             "## 概览", "", "| 学科 | 年级数 | 名称数 | 歧义名称数 |", "|---|---|---|---|"]
    for subject in sorted(names):
        grades = names[subject]
        n_names = sum(len(v) for v in grades.values())
        n_amb = sum(1 for v in grades.values() for c in v.values() if c >= 2)
        lines.append(f"| {LABEL.get(subject, subject)}（`{subject}`） | {len(grades)} | {n_names} | {n_amb} |")

    lines += ["", f"## 歧义名称（共 {amb} 组）", ""]
    if amb:
        for subject in sorted(names):
            for grade, v in sorted(names[subject].items(), key=lambda x: int(x[0])):
                for name, c in v.items():
                    if c >= 2:
                        lines.append(f"- `{subject}` g{grade}：{name}（{c} 次）")
    else:
        lines.append("无。库内同学科同年级的知识点名称均唯一，可按名称安全引用。")

    lines += ["", "## 分学科明细", ""]
    for subject in sorted(names):
        lines.append(f"### {LABEL.get(subject, subject)}（`{subject}`）")
        lines.append("")
        for grade, v in sorted(names[subject].items(), key=lambda x: int(x[0])):
            lines.append(f"#### {grade} 年级（{len(v)} 个名字）")
            lines.append("")
            for name, c in sorted(v.items()):
                lines.append(f"- {name}" + (f"（{c} 次）" if c >= 2 else ""))
            lines.append("")

    for suffix in (f"_{date}", "_latest"):
        (out_dir / f"_knowledge-points-baseline{suffix}.md").write_text("\n".join(lines), encoding="utf-8")
    return total, amb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.date.today().strftime("%Y%m%d"))
    ap.add_argument("--db", default=str(DB))
    a = ap.parse_args()
    names = build(pathlib.Path(a.db))
    total, amb = write(names, a.date, CT / "baseline")
    print(f"学科 {len(names)} 个 / 名称 {total} 个 / 歧义 {amb} 个 → baseline/_knowledge-points-baseline_{a.date}.json(+_latest)")


if __name__ == "__main__":
    main()
