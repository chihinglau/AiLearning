# -*- coding: utf-8 -*-
"""每日教研 CodeBuddy 版驱动：把导出包里"写在提示词里"的确定性动作变成可执行命令。

纯标准库；默认只读。写动作只有三处：lock acquire / commit / finish，且都支持 --dry-run。
用法：
    python _run_daily.py list
    python _run_daily.py outline --subject math --grade 4
    python _run_daily.py progress --subject math --grade 4
    python _run_daily.py context --subject math --grade 4
    python _run_daily.py plan --subject math --shift 02 --date 20261108 [--json] [--acquire]
    python _run_daily.py validate --subject math --grade 4 --date 20261108
    python _run_daily.py commit --subject math --grade 4 --date 20261108 --minutes 5 [--dry-run]
    python _run_daily.py finish --subject math --date 20261108 --done 3 --minutes 15
    python _run_daily.py prompt --subject math --shift 02
    python _run_daily.py payload --subject math --shift 02
    python _run_daily.py all-plan --date 20261108 --shift 02
    python _run_daily.py all-prompt --date 20261108 --shift 02
    python _run_daily.py all-verify --date 20261108 --strict

注意：入库 / 回退不在本脚本，见独立人工运维脚本 db_ops.py（需 --confirm I_KNOW）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG_PATH = HERE / "tasks.json"
CN_NUM = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六",
          7: "七", 8: "八", 9: "九", 10: "十", 11: "十一", 12: "十二"}

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


def load_cfg() -> dict:
    if not CFG_PATH.is_file():
        raise SystemExit(f"[错误] 找不到配置：{CFG_PATH}")
    return json.loads(CFG_PATH.read_text(encoding="utf-8"))


def P(cfg: dict, key: str) -> Path:
    return Path(cfg["paths"][key])


def dump(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def die(msg: str, code: int = 2):
    print(f"[错误] {msg}", file=sys.stderr)
    raise SystemExit(code)


def find_task(cfg: dict, subject: str) -> dict:
    for task in cfg["tasks"]:
        if task["subject"] == subject:
            return task
    die(f"未知学科 {subject!r}；可用：{', '.join(t['subject'] for t in cfg['tasks'])}")


def resolve_time(args) -> tuple[str, str, str, datetime]:
    batch = args.date or datetime.now().strftime("%Y%m%d")
    if not re.fullmatch(r"\d{8}", batch):
        die("--date 必须是 YYYYMMDD")
    hhmm = args.now or datetime.now().strftime("%H:%M")
    if not re.fullmatch(r"\d{2}:\d{2}", hhmm):
        die("--now 必须是 HH:MM")
    date_dash = f"{batch[:4]}-{batch[4:6]}-{batch[6:]}"
    now_dt = datetime.strptime(f"{date_dash} {hhmm}", "%Y-%m-%d %H:%M")
    return batch, date_dash, hhmm, now_dt


def resolve_shift(cfg: dict, args) -> str:
    if args.shift:
        shift = args.shift
    else:
        # --now 是补跑/回放的触发时刻，必须参与班次推断；否则 --now 23:45 会被当成 02 进攻班
        hhmm = getattr(args, "now", None)
        real_hour = datetime.now().hour
        if hhmm and re.fullmatch(r"\d{2}:\d{2}", hhmm):
            hour = int(hhmm[:2])
            if hour != real_hour:
                print(f"[提醒] --now {hhmm} 与真实时刻 {datetime.now():%H:%M} 不一致；"
                      "班次按 --now 推断，需固定策略请显式传 --shift", file=sys.stderr)
        else:
            hour = real_hour
        shift = "12" if hour == 12 else ("22" if hour in (22, 23) else "02")
    if shift not in cfg["shifts"]:
        die(f"未知班次 {shift!r}；可用 02 / 12 / 22")
    return shift


def range_hit(spec: str, grade: int) -> bool:
    if "-" in spec:
        lo, hi = (int(x) for x in spec.split("-", 1))
        return lo <= grade <= hi
    return int(spec) == grade


def check_params(cfg: dict, task: dict) -> list[str]:
    problems = []
    scope = cfg["compulsory_scope"].get(task["subject"])
    if scope:
        for g in task["grades"]:
            if not (scope[0] <= g <= scope[1]):
                problems.append(f"g{g} 不在 {task['subject_name']} 的义务教育开设年级 {scope[0]}-{scope[1]} 内")
    for g in task["grades"]:
        expected = next((v for spec, v in cfg["expected_version"][task["subject"]].items()
                         if range_hit(spec, g)), None)
        if expected and expected != task["version"]:
            problems.append(f"g{g} 版本应为 {expected}，配置却是 {task['version']}")
    if task["semester"] not in ("first", "second"):
        problems.append(f"semester 非法：{task['semester']}")
    return problems


def file_path(cfg: dict, task: dict, grade: int, batch: str) -> Path:
    return (P(cfg, "daily_dir") / task["subject"] / f"g{grade}" /
            f"{task['subject']}_g{grade}_{task['semester']}_{batch}.json")


def ledger_path(cfg: dict, task: dict, grade: int) -> Path:
    return P(cfg, "ledger_dir") / task["subject"] / f"g{grade}.md"


def log_path(cfg: dict, task: dict) -> Path:
    return P(cfg, "logs_dir") / f"{task['subject']}_{task['semester']}.md"


def lock_path(cfg: dict, task: dict) -> Path:
    return P(cfg, "logs_dir") / f"_daily-lock_{task['subject']}_{task['semester']}.txt"


def outline_path(cfg: dict, task: dict, grade: int) -> Path:
    name = task.get("outline_by_grade", {}).get(str(grade)) or task["outline"]
    return P(cfg, "baseline_dir") / name


def validate_argv(cfg: dict, task: dict, grade: int, fp: Path, with_kp: bool) -> list[str]:
    argv = [
        str(P(cfg, "python")), str(P(cfg, "validator")), str(fp),
        "--expect-subject", task["subject"],
        "--expect-grade", str(grade),
        "--expect-version", task["version"],
        "--expect-semester", task["semester"],
        "--outline", str(outline_path(cfg, task, grade)),
        "--manifest", str(P(cfg, "manifest")),
    ]
    if with_kp:
        argv += ["--kp-baseline", str(P(cfg, "kp_baseline"))]
    return argv


def ps_cmd(argv: list[str]) -> str:
    parts = []
    for i, a in enumerate(argv):
        if i == 0:
            parts.append(f'& "{a}"')
        elif a.startswith("--"):
            parts.append(a)
        else:
            parts.append(f'"{a}"')
    return " ".join(parts)


def run_validator(argv: list[str]) -> tuple[int, str]:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    res = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace", env=env)
    return res.returncode, res.stdout.strip()


def lock_info(cfg: dict, task: dict, now_dt: datetime) -> dict:
    lp = lock_path(cfg, task)
    info = {"path": str(lp), "state": "none", "raw": ""}
    if not lp.exists():
        return info
    raw = lp.read_text(encoding="utf-8", errors="replace").strip().splitlines()
    info["raw"] = raw[0] if raw else ""
    m = re.search(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})", info["raw"])
    if not m:
        info["state"] = "stale"
        return info
    started = datetime.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %H:%M")
    minutes = (now_dt - started).total_seconds() / 60
    info["minutes"] = round(minutes, 1)
    info["state"] = "fresh" if 0 <= minutes < cfg["policy"]["lock_ttl_minutes"] else "stale"
    return info


def outline_section(cfg: dict, task: dict, grade: int) -> tuple[Path, list[str], str]:
    op = outline_path(cfg, task, grade)
    if not op.is_file():
        return op, [], f"大纲文件不存在：{op}"
    lines = op.read_text(encoding="utf-8").splitlines()
    needle = f"{CN_NUM.get(grade, str(grade))}年级"
    start = next((i for i, line in enumerate(lines)
                  if line.startswith("##") and needle in line), None)
    if start is None:
        heads = [line for line in lines if line.startswith("##")]
        return op, lines[:80], f"大纲里没找到「{needle}」段；已给出文件头，可用标题：{heads[:12]}"
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return op, lines[start:end], ""


def collect_history(cfg: dict, task: dict, grade: int, stems_limit: int) -> dict:
    folder = P(cfg, "daily_dir") / task["subject"] / f"g{grade}"
    files = sorted(folder.glob(f"{task['subject']}_g{grade}_{task['semester']}_*.json"))
    points, sections, chapters, stems, sources = [], [], [], [], Counter()
    sections_by_file, bad = [], []
    for fp in files:
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            bad.append(f"{fp.name}: {exc}")
            continue
        file_sections = []
        for node in data.get("knowledge") or []:
            name = node.get("name", "")
            if node.get("node_type") == "section":
                sections.append(name)
                file_sections.append(name)
            else:
                points.append(name)
        for ch in data.get("chapters") or []:
            chapters.append(ch.get("name", ""))
            for q in ch.get("questions") or []:
                stems.append(q.get("stem", ""))
                sources[q.get("source_type", "original")] += 1
        sections_by_file.append((fp.name, file_sections))
    return {
        "files": [fp.name for fp in files], "bad_files": bad,
        "points": sorted(set(filter(None, points))),
        "sections": sorted(set(filter(None, sections))),
        "chapters": sorted(set(filter(None, chapters))),
        "sections_by_file": sections_by_file,
        "stems": stems[-stems_limit:] if stems_limit else [], "stem_total": len(stems),
        "source_types": dict(sources),
    }


# ---------------- 章节进度指针（防止每天重复做同一节） ----------------

_OUTLINE_SKIP = {
    "", "—", "-", "待补", "节", "章", "序", "单元", "年级", "单元/章节", "单元 / 板块",
    "节/课文", "节（课时）", "课时板块", "节（课时）", "章 / 章", "—", "— / —",
}


def norm_name(s: str) -> str:
    """把教材名规范化，容忍前导序号（3 口耳目手足 / 2.菱形的性质与判定）与空白。"""
    s = (s or "").strip().replace("**", "")
    s = re.sub(r"^\s*\d+\s*[.、．]?\s*", "", s)
    s = re.sub(r"[\s\u3000（）()·、,，。.:：;；\-—_/'\"？?！!]+", "", s)
    return s.lower()


def split_outline_names(cell: str) -> list[str]:
    parts = re.split(r"\s*/\s*", cell.replace("**", "").strip())
    out = []
    for part in parts:
        part = part.strip()
        if part in _OUTLINE_SKIP or part.startswith("（") or set(part) <= set("-: "):
            continue
        if len(part) > 80:
            continue
        out.append(part)
    return out


def parse_outline_items(lines: list[str]) -> tuple[list[dict], dict[int, int], dict[int, list[str]]]:
    """把本年级大纲表格解析成有序「节」清单；返回 (items, 行首索引, 行单元别名)。"""
    items: list[dict] = []
    row_first: dict[int, int] = {}
    row_units: dict[int, list[str]] = {}
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip().replace("**", "") for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if set(cells[0]) <= set("-: ") or cells[0] in _OUTLINE_SKIP:
            continue
        if cells[0].isdigit():
            row = int(cells[0])
            unit_cell = cells[1]
            sec_cell = cells[2] if len(cells) > 2 else ""
        else:
            row = len(row_units) + 1
            unit_cell = cells[0]
            sec_cell = cells[1] if len(cells) > 1 else ""
        units = split_outline_names(unit_cell)
        secs = split_outline_names(sec_cell)
        unit = units[0] if units else unit_cell.strip()
        row_first.setdefault(row, len(items))
        row_units[row] = units or [unit]
        for sec in (secs or [unit]):
            aliases = [sec] if secs else units or [unit]
            compound = f"{unit} / {sec}"
            aliases.append(compound)
            items.append({
                "row": row, "order": row, "unit": unit, "section": sec,
                "compound": compound, "aliases": aliases,
            })
    return items, row_first, row_units


def name_match(a: str, b: str) -> bool:
    if not a or not b:
        return False
    if a == b:
        return True
    return min(len(a), len(b)) >= 5 and (a in b or b in a)


def progress_of(cfg: dict, task: dict, grade: int) -> dict:
    """按「大纲顺序 + 历史产出」算出今天该做哪一节，杜绝无限停在同一节。"""
    op, lines, outline_warning = outline_section(cfg, task, grade)
    hist = collect_history(cfg, task, grade, stems_limit=1)
    items, row_first, row_units = parse_outline_items(lines)
    result = {
        "outline": str(op), "outline_warning": outline_warning,
        "items_count": len(items),
        "covered": sorted(set(hist["sections"] + hist["chapters"])),
        "files": hist["files"], "bad_files": hist["bad_files"],
        "last_section": None, "last_compound": None,
        "next_section": None, "next_unit": None, "next_compound": None,
        "next_order": None, "finished": False, "streak": 0, "warning": "",
        "subject": task["subject"],
    }
    if not items:
        result["warning"] = "大纲本年级段没解析出任何单元/节 → 按原指令第一步 3.7 停止执行并报告，不得凭记忆编目录"
        return result

    covered_raw = [n for n in result["covered"] if n]
    unit_alias_norms = [norm_name(u) for units in row_units.values() for u in units]
    # 英语等学科多个单元复用同名板块（Story / Ready Go …）。只按板块名匹配会一路
    # 命中到最后一个单元，导致「做完 Unit 1 的 Ready Go」却跳到 Unit 6。用历史里
    # 出现的单元名锁定 active_row，复合名与纯板块名只在该单元内匹配。
    matched_rows = [
        row
        for cn in map(norm_name, covered_raw)
        for row, units in row_units.items()
        if any(name_match(cn, norm_name(u)) for u in units)
    ]
    active_row = max(matched_rows) if matched_rows else None
    last_index, last_label, last_compound = -1, None, None
    for name in covered_raw:
        cn = norm_name(name)
        is_unit_name = (" / " not in name) and any(
            name_match(cn, un) for un in unit_alias_norms
        )
        if not is_unit_name:
            for idx, item in enumerate(items):
                if active_row is not None and item["row"] != active_row:
                    continue
                if idx > last_index and any(
                    name_match(cn, norm_name(a)) for a in item["aliases"]
                ):
                    last_index, last_label = idx, item["section"]
                    last_compound = item["compound"]
        for row, units in row_units.items():
            cand = row_first[row] - 1
            can_take = cand > last_index or (cand == last_index and last_label is None)
            if can_take and any(name_match(cn, norm_name(u)) for u in units):
                last_index, last_label, last_compound = cand, units[0], None
    result["last_section"] = last_label
    result["last_compound"] = last_compound
    result["last_index"] = last_index

    next_index = last_index + 1
    if next_index >= len(items):
        result["finished"] = True
        result["warning"] = ("大纲本册已全部覆盖：按原文进入第二轮（加深/换情境/跨章综合），"
                             "台账标注「第二轮」；确无可新增则走零新增处理，不要重复做同一节")
        return result
    nxt = items[next_index]
    # 大纲里「单元」与「板块」同名的行（如英语 g9 只有单元名）不应拼成
    # 「Unit 1 … / Unit 1 …」这种重复复合名，直接退回单元名。
    compound = (nxt["compound"] if nxt["unit"] != nxt["section"]
                else nxt["section"])
    result.update({
        # 英语一律给复合名，避免模型把纯板块名 Story 写进 section 又串单元。
        "next_section": (compound if task["subject"] == "english" else nxt["section"]),
        "next_unit": nxt["unit"], "next_compound": compound,
        "next_order": nxt["order"], "next_index": next_index,
        "last_index": last_index,
    })

    if result["last_section"]:
        target = norm_name(result["last_section"])
        streak = 0
        for _, names in reversed(hist["sections_by_file"]):
            if any(name_match(norm_name(n), target) for n in names):
                streak += 1
            else:
                break
        result["streak"] = streak
        if streak >= 2:
            result["warning"] = (f"该节「{result['last_section']}」已连续 {streak} 天产出；原文允许一节拆 2 天，"
                                 f"再继续必须在台账标注「同一节第 N 天 / 第二轮」，否则应推进到下一节")
    return result


# ---------------- 命令 ----------------

def cmd_list(cfg: dict, args) -> None:
    rows = []
    for t in cfg["tasks"]:
        rows.append({
            "subject": t["subject"], "title": t["title"], "grades": t["grades"],
            "version": t["version"], "semester": t["semester"],
            "cron": t["cron"], "minute": t["minute"],
            "rrule": f"FREQ=DAILY;BYHOUR=2,12,22;BYMINUTE={t['minute']}（未验证多值，注册请用 03 文件的单值 RRULE）",
        })
    if args.json:
        dump(rows)
    else:
        print(f"{'学科':<10}{'年级':<18}{'版本':<10}{'cron':<20}任务")
        for r in rows:
            print(f"{r['subject']:<10}{','.join(map(str, r['grades'])):<18}{r['version']:<10}{r['cron']:<20}{r['title']}")


def cmd_outline(cfg: dict, args) -> None:
    task = find_task(cfg, args.subject)
    problems = check_params(cfg, task)
    if problems:
        die("；".join(problems))
    op, lines, warning = outline_section(cfg, task, args.grade)
    print(f"# 大纲：{op.name} · {task['subject']} g{args.grade}")
    if warning:
        print(f"[提醒] {warning}")
    print("\n".join(lines))


def cmd_progress(cfg: dict, args) -> None:
    task = find_task(cfg, args.subject)
    problems = check_params(cfg, task)
    if problems:
        die("；".join(problems))
    dump(progress_of(cfg, task, args.grade))


def cmd_context(cfg: dict, args) -> None:
    task = find_task(cfg, args.subject)
    batch, _, _, _ = resolve_time(args)
    problems = check_params(cfg, task)
    if problems:
        die("；".join(problems))
    op, lines, warning = outline_section(cfg, task, args.grade)
    hist = collect_history(cfg, task, args.grade, args.stems_limit)
    lp = ledger_path(cfg, task, args.grade)
    fp = file_path(cfg, task, args.grade, batch)
    argv = validate_argv(cfg, task, args.grade, fp, args.with_kp_baseline)

    print(f"# CodeBuddy 上下文 · {task['subject_name']} g{args.grade} · {task['version']} · {task['semester']} · 批次 {batch}")
    print(f"- 格式标准：{cfg['paths']['readme']}")
    print(f"- 完整指令：{cfg['paths']['instruction']}")
    print(f"- 学科模板：{P(cfg, 'content_root') / 'templates' / (task['subject'] + '.json')}")
    print(f"- 章节基线：{cfg['paths']['chapters_baseline']}")
    print(f"- 知识点基线（人读）：{P(cfg, 'baseline_dir') / '_knowledge-points-baseline_latest.md'}")
    print(f"- 本年级大纲：{op}")
    print(f"- 今日产出：{fp}")
    print(f"- 台账：{lp}")
    print(f"- 运行日志：{log_path(cfg, task)}")
    print("- 学科规则：")
    for rule in task["rules"]:
        print(f"  · {rule}")
    pg = progress_of(cfg, task, args.grade)
    print("\n## 今日进度指针（脚本判定，必须遵守）")
    print(f"- 大纲条目：{pg['items_count']} 个节/板块；已覆盖节/章节名：{pg['covered'] or '无（首日）'}")
    print(f"- 上次做到：{pg['last_section'] or '无（首日）'}")
    if pg["finished"]:
        print(f"- 今日应做：全册已覆盖 → {pg['warning']}")
    else:
        print(f"- 今日应做（next_section）：{pg['next_section']}")
        print(f"  所属单元（chapters.name）：{pg['next_unit']}；order_index：{pg['next_order']}")
        print(f"  规则：今天只做这一节，章节名与大纲原文一致；不回头重做已覆盖节、不跳节；"
              f"一节内容多可拆 2 天但需在台账标注「同一节第 N 天」")
    if pg["streak"]:
        print(f"- 同一节连续产出：{pg['streak']} 天")
    if pg["warning"]:
        print(f"- [提醒] {pg['warning']}")
    if pg["bad_files"]:
        print(f"- [提醒] 无法解析的历史文件：{pg['bad_files']}")
    print(f"\n## 大纲（{op.name} 本年级段）")
    if warning:
        print(f"[提醒] {warning}")
    print("\n".join(lines))
    print("\n## 历史文件（查重用）")
    print(f"- 已有文件（{len(hist['files'])}）：{', '.join(hist['files']) or '无（首日）'}")
    print(f"- 已覆盖章节名：{'、'.join(hist['chapters']) or '无'}")
    print(f"- 已声明 section：{'、'.join(hist['sections']) or '无'}")
    print(f"- 已用知识点名（{len(hist['points'])}）：{'、'.join(hist['points']) or '无'}")
    print(f"- 已用题干（共 {hist['stem_total']} 条，显示最后 {len(hist['stems'])} 条）：")
    for stem in hist["stems"]:
        print(f"  · {stem[:90]}")
    if hist["bad_files"]:
        print(f"- 无法解析的历史文件：{hist['bad_files']}")
    if lp.is_file():
        text = lp.read_text(encoding="utf-8", errors="replace").splitlines()
        print(f"\n## 台账尾部（{lp.name}）")
        print("\n".join(text[-args.ledger_tail:]))
    else:
        print("\n## 台账：尚无（视为首日）")
    print("\n## 本年级命令")
    print(f"& \"{cfg['paths']['python']}\" \"{cfg['paths']['run_daily']}\" validate --subject {task['subject']} --grade {args.grade} --date {batch}")
    print(f"& \"{cfg['paths']['python']}\" \"{cfg['paths']['run_daily']}\" commit --subject {task['subject']} --grade {args.grade} --date {batch} --minutes N")
    print(f"# 自检命令（驱动内部使用）：{ps_cmd(argv)}")


def compute_plan(cfg: dict, args) -> dict:
    task = find_task(cfg, args.subject)
    batch, date_dash, hhmm, now_dt = resolve_time(args)
    shift = resolve_shift(cfg, args)
    meta = cfg["shifts"][shift]
    problems = check_params(cfg, task)
    if problems:
        die("参数不合法，停止执行：" + "；".join(problems))

    li = lock_info(cfg, task, now_dt)
    grades = []
    for grade in task["grades"]:
        fp = file_path(cfg, task, grade, batch)
        argv = validate_argv(cfg, task, grade, fp, args.with_kp_baseline)
        row = {
            "grade": grade, "file": str(fp), "exists": fp.is_file(),
            "validate_cmd": ps_cmd(argv),
            "context_cmd": (f"& \"{cfg['paths']['python']}\" \"{cfg['paths']['run_daily']}\" "
                            f"context --subject {task['subject']} --grade {grade} --date {batch}"),
            "commit_cmd": (f"& \"{cfg['paths']['python']}\" \"{cfg['paths']['run_daily']}\" "
                           f"commit --subject {task['subject']} --grade {grade} --date {batch} --minutes N"),
            "outline": str(outline_path(cfg, task, grade)),
            "ledger": str(ledger_path(cfg, task, grade)),
        }
        pg = progress_of(cfg, task, grade)
        row.update({
            "next_section": pg["next_section"], "next_unit": pg["next_unit"],
            "next_order": pg["next_order"], "progress_finished": pg["finished"],
            "progress_warning": pg["warning"],
        })
        if fp.is_file():
            if args.no_check:
                row.update(status="exists_unchecked", valid=None)
            else:
                rc, output = run_validator(argv)
                row.update(status="done" if rc == 0 else "repair", valid=(rc == 0),
                           errors=[ln.strip() for ln in output.splitlines() if "[错误]" in ln][:8])
        else:
            row.update(status="missing", valid=None)
        grades.append(row)

    todos = [g["grade"] for g in grades if g["status"] == "repair"]
    todo_missing = [g["grade"] for g in grades if g["status"] == "missing"]
    todos += todo_missing
    warnings = []
    warnings.append("章节推进以 plan.grades[].next_section / context 的「今日进度指针」为准："
                    "今天只做该节、不回头重做已覆盖节；补漏班不推进新节")
    if args.no_check:
        warnings.append("--no-check 模式：已有文件一律视为跳过，不判自检结果；补漏班不要用这个模式")
    if meta["role"] == "repair":
        cap = cfg["policy"]["max_repair_grades"]
        if len(todos) > cap:
            warnings.append(f"补漏班单次最多 {cap} 个年级，其余 {todos[cap:]} 顺延至下一班")
            todos = todos[:cap]
        warnings.append("补漏班不推进新节、不新增知识点；缺文件按台账「下一节计划」补齐当天批次")
    if shift == "22" and hhmm >= cfg["policy"]["late_stop"]:
        warnings.append(f"已过 {cfg['policy']['late_stop']}：立即停手，未轮到年级顺延至次日 02:00 首跑")
        todos = []
    if li["state"] == "fresh":
        warnings.append("检测到并行运行（锁 < 30 分钟），本次跳过，不写任何文件")
        todos = []

    py, run = cfg["paths"]["python"], cfg["paths"]["run_daily"]
    idle_log_line = (f"{date_dash} 批次 {hhmm} "
                     f"{'补漏班无待办' if meta['role'] == 'repair' else '本轮已完成，无待办'}")
    if li["state"] == "fresh":
        next_actions = ["不写任何文件，只汇报「检测到并行运行，本次跳过」"]
    elif not todos:
        next_actions = [f"把 idle_log_line 追加到运行日志 {log_path(cfg, task)}（不读 README/模板、不跑全量自检），一句话汇报后结束"]
    else:
        next_actions = [
            f"& \"{py}\" \"{run}\" lock --subject {task['subject']} --action acquire --date {batch} --now {hhmm}",
            "对 todos 里每个年级：context → 生成 JSON（write_to_file）→ validate → commit",
            f"& \"{py}\" \"{run}\" finish --subject {task['subject']} --date {batch} --done {len(todos)} --minutes N",
        ]
    plan = {
        "batch_date": batch, "date_dash": date_dash, "time": hhmm, "shift": shift,
        "role": meta["role"], "shift_label": meta["label"], "detail": meta["detail"],
        "task": {"subject": task["subject"], "title": task["title"], "version": task["version"],
                 "semester": task["semester"], "grades": task["grades"], "rules": task["rules"],
                 "cron": task["cron"]},
        "lock": li, "warnings": warnings,
        "todos": todos, "idle": not todos, "idle_log_line": idle_log_line,
        "paths": {"instruction": cfg["paths"]["instruction"], "readme": cfg["paths"]["readme"],
                  "log": str(log_path(cfg, task)), "outline_dir": cfg["paths"]["baseline_dir"]},
        "boundary": cfg["policy"]["boundary"],
        "grades": grades,
        "next_actions": next_actions,
    }
    return plan


def render_plan(plan: dict) -> str:
    lines = [
        f"# 批次计划 · {plan['task']['title']} · {plan['date_dash']} {plan['time']} · {plan['shift_label']}",
        f"- 参数：subject={plan['task']['subject']} version={plan['task']['version']} "
        f"semester={plan['task']['semester']} grades={plan['task']['grades']}",
        f"- 锁：{plan['lock']['state']} {plan['lock']['raw']}（{plan['lock']['path']}）",
    ]
    for g in plan["grades"]:
        nxt = g["next_section"] or "全册完成→第二轮/零新增"
        lines.append(f"  g{g['grade']:<2} {g['status']:<16} next={nxt}  {g['file']}")
    lines.append(f"- 待办年级：{plan['todos'] or '无'}")
    for w in plan["warnings"]:
        lines.append(f"- [提醒] {w}")
    if plan["lock"]["state"] == "fresh":
        lines.append("- 并行锁：不写任何文件，直接结束")
    elif plan["idle"]:
        lines.append(f"- 无待办：只追加一行日志「{plan['idle_log_line']}」，不读 README/模板、不跑全量自检")
    lines.append("- 边界：" + plan["boundary"])
    lines.append("- 命令：" + "\n  ".join(plan["next_actions"]))
    return "\n".join(lines)


def cmd_plan(cfg: dict, args) -> None:
    plan = compute_plan(cfg, args)
    if args.json:
        dump(plan)
    else:
        print(render_plan(plan))


def _all_args(args, subject: str):
    clone = argparse.Namespace(**vars(args))
    clone.subject = subject
    clone.json = True
    clone.acquire = False
    return clone


def all_plans(cfg: dict, args) -> dict:
    """9 学科统一计划；每次重算，已完成的年级自动跳过（幂等）。"""
    shift = resolve_shift(cfg, args)
    batch = args.date or datetime.now().strftime("%Y%m%d")
    subjects = []
    for t in cfg["tasks"]:
        p = compute_plan(cfg, _all_args(args, t["subject"]))
        subjects.append({
            "subject": t["subject"], "title": t["title"], "version": t["version"],
            "semester": t["semester"], "grades": t["grades"],
            "lock": p["lock"]["state"], "idle": p["idle"], "todos": p["todos"],
            "warnings": p["warnings"],
            "rows": [{k: g[k] for k in ("grade", "file", "status", "valid", "next_section", "next_unit")}
                     for g in p["grades"]],
        })
    rows = [r for s in subjects for r in s["rows"]]
    count = Counter(r["status"] for r in rows)
    return {
        "batch_date": batch, "shift": shift, "shift_label": cfg["shifts"][shift]["label"],
        "subjects": subjects,
        "totals": {
            "subjects": len(subjects), "grades": len(rows),
            "done": count["done"], "repair": count["repair"], "missing": count["missing"],
            "exists_unchecked": count["exists_unchecked"],
            "todo_grades": sum(len(s["todos"]) for s in subjects),
            "idle_subjects": sum(1 for s in subjects if s["idle"]),
        },
        "boundary": cfg["policy"]["boundary"],
    }


def cmd_all_plan(cfg: dict, args) -> None:
    data = all_plans(cfg, args)
    if args.json:
        dump(data)
        return
    t = data["totals"]
    print(f"# 全学科批次计划 · {data['batch_date']} · {data['shift_label']}（只读，可重复执行）")
    print(f"- 汇总：{t['subjects']} 学科 / {t['grades']} 年级；已完成 {t['done']}、待修 {t['repair']}、"
          f"缺文件 {t['missing']}、本轮待办 {t['todo_grades']}、无待办学科 {t['idle_subjects']}")
    for s in data["subjects"]:
        if s["idle"]:
            print(f"  {s['subject']:<10} 无待办（{s['lock']}）")
        else:
            nxt = ", ".join(f"g{r['grade']}:{r['next_section'] or '全册完成'}"
                            for r in s["rows"] if r["grade"] in s["todos"])
            print(f"  {s['subject']:<10} 待办 {s['todos']}  next={nxt}")
    print("- 边界：" + data["boundary"])


def verify_one(cfg: dict, task: dict, grade: int, batch: str, with_kp: bool,
               spec_since: str | None = None) -> dict:
    fp = file_path(cfg, task, grade, batch)
    item = {"subject": task["subject"], "grade": grade, "file": str(fp),
            "status": "ok", "errors": [], "warnings": [], "notes": [], "stats": {}}
    legacy_batches = {str(b) for b in (cfg["policy"].get("legacy_batches") or [])}
    is_legacy_batch = batch in legacy_batches
    if not fp.is_file():
        item["status"] = "missing"
        item["errors"].append("当日文件不存在")
        return item
    rc, output = run_validator(validate_argv(cfg, task, grade, fp, with_kp))
    st = stats_of(fp)
    data = json.loads(fp.read_text(encoding="utf-8"))
    point_names = {str(n.get("name") or "").strip() for n in data.get("knowledge") or []
                   if n.get("node_type") == "point"}
    per_point = Counter()
    for ch in data.get("chapters") or []:
        for q in ch.get("questions") or []:
            kp = str(q.get("knowledge_point") or "").strip()
            if kp in point_names:
                per_point[kp] += 1
    low = mid = high = 0
    for k, v in (st["difficulty"] or {}).items():
        try:
            d = int(k)
        except (TypeError, ValueError):
            continue
        if d <= 2:
            low += v
        elif d == 3:
            mid += v
        else:
            high += v
    item["stats"] = {
        "points": len(st["points"]), "questions": st["question_count"],
        "q_types": st["q_types"], "sections": st["sections"],
        "min_questions_per_point": min(per_point.values()) if per_point else 0,
        "difficulty_buckets": {"1-2": low, "3": mid, "4-5": high},
    }
    min_q = int(cfg["policy"].get("min_questions_per_point", 4))
    since = spec_since or str(cfg["policy"].get("min_questions_per_point_since") or "")
    grandfathered = bool(since) and batch < since
    weak = {k: v for k, v in per_point.items() if v < min_q}
    uncovered = [p for p in st["points"] if p not in per_point]
    if weak or uncovered:
        detail = weak if weak else {"未挂题": uncovered}
        # 第七轮评审 A 项：这条从 warn 升为 fail——「每点 ≥4」原先只是文字规格，
        # 任何只产 3 题的批次都能 rc=0 通过，等于没有强制点。现在它会进 errors，
        # `all-verify` 判 fail、`ops import` 第 2 步会直接中止。
        # 第八轮评审 A 项：加批次门——规格自 `min_questions_per_point_since` 起生效，
        # 更早的历史批次只提醒不判失败（grandfather），否则把规格变成 fail 的那一刻
        # 会把整个历史批次染红，等于用新规则审判旧内容。
        msg = f"每知识点 ≥{min_q} 题未达标（规格是硬约束，不接受事后补丁凑数）：{detail}"
        if grandfathered:
            item["warnings"].append(
                f"{msg}｜批次 {batch} 早于规格生效日 {since}，按历史批次宽限处理（只提醒）")
        else:
            item["errors"].append(msg)
    total = st["question_count"]
    if total:
        ratios = (low / total, mid / total, high / total)
        tol = 0.15
        if any(abs(r - t) > tol for r, t in zip(ratios, (0.4, 0.4, 0.2))):
            item["warnings"].append(
                f"难度 {low}:{mid}:{high}（{ratios[0]:.0%}/{ratios[1]:.0%}/{ratios[2]:.0%}）"
                f"偏离 40/40/20 容差 ±{tol:.0%}")
    if rc != 0:
        item["errors"].append("自检未通过：" + "；".join(
            ln.strip() for ln in output.splitlines() if "[错误]" in ln)[:300])
    validator_notices = output.count("[提醒]")
    if validator_notices:
        item["warnings"].append(
            f"_validate_daily.py 输出 {validator_notices} 条 [提醒]（非阻断；--strict 计入未通过）")
        item["stats"]["validator_notices"] = validator_notices
    if not 3 <= len(st["points"]) <= 6:
        item["warnings"].append(f"知识点 {len(st['points'])} 个，不在 3~6 区间")
    if not 18 <= st["question_count"] <= 28:
        item["warnings"].append(f"题目 {st['question_count']} 道，不在 18~28 区间")
    types = st["q_types"]
    if len(types) < 4 or "multiple" not in types or "answer" not in types:
        item["warnings"].append("题型不足 4 种或缺多选/主观题")
    if st["duplicate_stems"]:
        item["errors"].append(f"存在重复题干 {len(st['duplicate_stems'])} 条")
    op, lines, _ = outline_section(cfg, task, grade)
    items, _, _ = parse_outline_items(lines)
    allowed = [norm_name(a) for it in items for a in it["aliases"]]
    allowed = [a for a in allowed if a]
    for sec in st["sections"]:
        ns = norm_name(sec)
        if ns not in allowed and not any(name_match(ns, a) for a in allowed):
            item["errors"].append(f"section「{sec}」不在本年级大纲内")
    pg = progress_of(cfg, task, grade)
    if pg["streak"] > 2:
        item["warnings"].append(f"同一节连续 {pg['streak']} 天，检查是否卡在同一章节")
    lp, logp = ledger_path(cfg, task, grade), log_path(cfg, task)
    date_dash = f"{batch[:4]}-{batch[4:6]}-{batch[6:]}"
    ledger_text = lp.read_text(encoding="utf-8", errors="replace") if lp.is_file() else ""
    log_text = logp.read_text(encoding="utf-8", errors="replace") if logp.is_file() else ""
    if batch not in ledger_text and date_dash not in ledger_text:
        item["notes"].append("台账未记录本批次日期（历史文件，不影响内容核实）")
    if fp.name not in log_text:
        item["notes"].append("运行日志未记录该文件（历史文件，不影响内容核实）")
    if is_legacy_batch:
        # 第八轮评审 D 项：试跑样本批次不纳入回归基线——问题照样记在 legacy_errors 里，
        # 但不判 fail，避免「回头跑一次历史批次就整片飘红」。
        item["legacy_errors"] = item["errors"]
        item["errors"] = []
        item["notes"].append(
            f"批次 {batch} 属试跑样本（policy.legacy_batches）："
            f"规格未达标与旧章节名等历史问题只记录、不判失败，不纳入回归基线")
        item["status"] = "legacy"
        return item
    if item["errors"]:
        item["status"] = "fail"
    elif item["warnings"]:
        item["status"] = "warn"
    return item


def cmd_all_verify(cfg: dict, args) -> None:
    batch = args.date or datetime.now().strftime("%Y%m%d")
    results = [verify_one(cfg, t, g, batch, args.with_kp_baseline,
                          spec_since=getattr(args, "spec_since", None))
               for t in cfg["tasks"] for g in t["grades"]]
    count = Counter(r["status"] for r in results)
    legacy_rows = [r for r in results if r["status"] == "legacy"]
    include_legacy = bool(getattr(args, "include_legacy", False))
    spec_since = getattr(args, "spec_since", None) or cfg["policy"].get("min_questions_per_point_since")
    data = {
        "batch_date": batch, "strict": bool(args.strict),
        "spec_since": spec_since,
        "legacy_batches": cfg["policy"].get("legacy_batches") or [],
        "totals": {"grades": len(results), "ok": count["ok"], "warn": count["warn"],
                   "fail": count["fail"], "missing": count["missing"],
                   "legacy": count["legacy"],
                   "notes": sum(1 for r in results if r["notes"])},
        "results": results,
        "passed": count["fail"] == 0 and (not include_legacy or count["legacy"] == 0) and (
            not args.strict or (count["missing"] == 0 and count["warn"] == 0)),
    }
    if args.json:
        dump(data)
    else:
        t = data["totals"]
        print(f"# 全学科结果核实 · {batch}（只读）")
        print(f"- 汇总：{t['grades']} 年级；通过 {t['ok']} / 提醒 {t['warn']} / 失败 {t['fail']} / 缺文件 {t['missing']}"
              f" / 试跑样本 {t['legacy']}"
              f"；strict={'开' if args.strict else '关'}；结论={'通过' if data['passed'] else '未通过'}")
        if spec_since:
            print(f"- 规格生效日：{spec_since}（早于该日的历史批次按宽限处理，只提醒不判失败）")
        if data["legacy_batches"]:
            print(f"- legacy 批次：{', '.join(data['legacy_batches'])}（试跑样本，不纳入回归基线）")
        by_sub = {}
        for r in results:
            by_sub.setdefault(r["subject"], []).append(r)
        for sub, rows in by_sub.items():
            c = Counter(r["status"] for r in rows)
            q = sum(r["stats"].get("questions", 0) for r in rows)
            kp = sum(r["stats"].get("points", 0) for r in rows)
            print(f"  {sub:<10} 通过 {c['ok']} / 提醒 {c['warn']} / 失败 {c['fail']} / 缺 {c['missing']}"
                  f" / 样本 {c['legacy']}"
                  f"；知识点 {kp}、题目 {q}")
        missing = [f"{r['subject']}/g{r['grade']}" for r in results if r["status"] == "missing"]
        if missing:
            print(f"  [缺文件 {len(missing)}] " + ", ".join(missing))
        for r in results:
            if r["errors"] and r["status"] != "missing":
                print(f"  [失败] {r['subject']} g{r['grade']}: " + "；".join(r["errors"])[:240])
            elif r["warnings"]:
                print(f"  [提醒] {r['subject']} g{r['grade']}: " + "；".join(r["warnings"])[:240])
        if legacy_rows:
            print(f"  [试跑样本 {len(legacy_rows)}] 历史批次遗留问题（记录在案，不判失败）：")
            for r in legacy_rows:
                detail = "；".join(r.get("legacy_errors") or r["warnings"])[:200]
                print(f"    - {r['subject']} g{r['grade']}: {detail}")
        notes = sum(1 for r in results if r["notes"])
        if notes:
            print(f"  [记录提示 {notes}] 台账/运行日志尚未覆盖这些历史文件；后续 commit 会自动补齐，不影响内容核实")
    raise SystemExit(0 if data["passed"] else 1)


def build_all_prompt(cfg: dict, batch: str, shift: str, strict: bool = True) -> str:
    py, run = cfg["paths"]["python"], cfg["paths"]["run_daily"]
    meta = cfg["shifts"][shift]
    rows = "\n".join(
        f"  | {t['subject']} | {','.join(map(str, t['grades']))} | {t['version']} | "
        f"{t['semester']} | {t['outline']} |" for t in cfg["tasks"])
    strict_flag = " --strict" if strict else ""
    return f"""你是深圳地区资深教师兼学科教研员。本次执行【全学科一键教研】：把当天 9 个学科的教研任务推进完并核实结果。这是手动单次执行，不依赖任何定时任务；跑完即结束。

【固定配置 · 不得自行更改】
  - BATCH_DATE = {batch}（固定，文件名/台账/日志全程用它，不随系统日期变化）；班次 = {shift}（{meta['label']}）
  - 内容根：{cfg['paths']['content_root']}；参数唯一源：{CFG_PATH}
  - 规则唯一源：{HERE / '01-主提示词.md'}（含工具映射与硬约束）；格式标准 {cfg['paths']['readme']}；完整命题规则 {cfg['paths']['instruction']}
  - 驱动脚本：{run}；Python：{py}
  - 9 学科参数（顺序即执行顺序，学科内年级从小到大）：
  | subject | grades | version | semester | outline |
  |---|---|---|---|---|
{rows}

【执行方法 · 一条命令可重复执行，天然断点续做】
  第 0 步：`& "{py}" "{run}" all-plan --date {batch} --shift {shift} --json`
    它一次性给出 9 学科每个年级的状态（done / missing / repair）、今日 next_section、锁状态与待办年级。**只做它列出的 pending 年级**。
  第 1 步：按上表顺序逐学科闭环；一个学科结束才进下一个，一个年级 0 错误才进下一个年级：
    a. `& "{py}" "{run}" plan --subject <S> --shift {shift} --date {batch} --json`
       - idle=true → 该学科已全部完成，只追加 idle_log_line 到日志，跳过
       - lock.state=fresh → 跳过该学科并汇报「检测到并行运行」，不写任何文件
    b. `& "{py}" "{run}" lock --subject <S> --action acquire --date {batch}`
    c. 对 plan.todos 逐年级：
       `& "{py}" "{run}" context --subject <S> --grade <G> --date {batch}` 拿今日进度指针 next_section、大纲段、已用知识点/题干、台账尾部
       → 按 README + 01 主提示词生成 JSON，用 write_to_file 写到 plan.grades[G].file（UTF-8 无 BOM；已存在就跳过，绝不覆盖、不加 _r2）
       → `& "{py}" "{run}" validate --subject <S> --grade <G> --date {batch}`，错误修到 EXIT=0
       → `& "{py}" "{run}" commit --subject <S> --grade <G> --date {batch} --minutes <耗时>`
    d. `& "{py}" "{run}" finish --subject <S> --date {batch} --done <完成年级数> --minutes <总耗时>` 释放锁并补收尾行
  第 2 步（核实，必做）：`& "{py}" "{run}" all-verify --date {batch}{strict_flag}`
    要求退出码 0、0 失败；若有 fail 或 missing，逐条修/补后重跑核实，直到通过；提醒项逐条说明保留理由。
  第 3 步：汇报一张 9 学科汇总表（每学科：完成年级数 / 知识点数 / 题目数 / 自检 / next_section），合计、失败项、待人工复核项。

【幂等与章节推进纪律（本命令可重复执行的关键）】
  - **同一 BATCH_DATE 重复执行**：已存在且自检通过的文件一律 done/skip，不重写、不重复出题；只补 missing 与修 repair。全部完成后 `all-plan` 显示无待办、`all-verify` 通过，重复执行只会空转汇报，不会卡死。
  - **换日重复执行**：前一天的历史文件进入 `progress_of()` 的已覆盖集合，`next_section` 自动按大纲顺序前进；今天只做该节，不回头重做、不跳节。若某节连续 ≥2 天，必须标注「同一节第 N 天 / 第二轮」或推进下一节。
  - 每次 commit 都把本次真实 section 与具体下一节写进台账/日志；大纲全册覆盖完按原文进入第二轮或零新增，不靠改几个字凑数。
  - 时间/上下文不足时立刻停手：已完成年级已逐年级落盘，运行日志写明剩余学科/年级，不留半成品；**下次原样重跑这条命令即可从断点继续**（这正是允许分批跑完 46 个年级的原因）。
  - 补漏班（12/22）不推进新节，只修自检失败与补缺文件，单次最多 3 个年级/学科。

【边界】{cfg['policy']['boundary']}。发现历史文件错误不擅自修改，写进「待人工复核项」并汇报。
"""


def cmd_all_prompt(cfg: dict, args) -> None:
    batch = args.date or datetime.now().strftime("%Y%m%d")
    shift = resolve_shift(cfg, args)
    print(build_all_prompt(cfg, batch, shift, strict=not getattr(args, "no_strict", False)))


def cmd_validate(cfg: dict, args) -> None:
    task = find_task(cfg, args.subject)
    batch, _, _, _ = resolve_time(args)
    fp = Path(args.file) if args.file else file_path(cfg, task, args.grade, batch)
    if not fp.is_file():
        die(f"文件不存在：{fp}")
    argv = validate_argv(cfg, task, args.grade, fp, args.with_kp_baseline)
    print(f"# {ps_cmd(argv)}")
    rc, output = run_validator(argv)
    print(output)
    print(f"EXIT={rc}")
    raise SystemExit(rc)


def stats_of(fp: Path) -> dict:
    data = json.loads(fp.read_text(encoding="utf-8"))
    nodes = data.get("knowledge") or []
    points = [n.get("name", "") for n in nodes if n.get("node_type") == "point"]
    sections = [n.get("name", "") for n in nodes if n.get("node_type") == "section"]
    chapters = [c.get("name", "") for c in (data.get("chapters") or [])]
    questions = [q for c in (data.get("chapters") or []) for q in (c.get("questions") or [])]
    stems = [q.get("stem", "") for q in questions]
    dup = [s for s, n in Counter(stems).items() if n > 1]
    return {
        "points": points, "sections": sections, "chapters": chapters,
        "q_types": dict(Counter(q.get("q_type", "?") for q in questions)),
        "difficulty": dict(sorted(Counter(q.get("difficulty", "?") for q in questions).items(),
                                  key=lambda kv: str(kv[0]))),
        "sources": dict(Counter(q.get("source_type", "original") for q in questions)),
        "question_count": len(questions), "duplicate_stems": dup,
    }


def append_text(path: Path, block: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text(encoding="utf-8") if path.is_file() else ""
    path.write_text(old.rstrip("\n") + "\n\n" + block.strip() + "\n", encoding="utf-8")


_LOG_DETAIL_HEADER = "| 日期 | 批次 | 年级 | 文件 | 状态 | 自检 | 耗时（分） | 备注 |"
_LOG_DETAIL_SEP = "|---|---|---|---|---|---|---|---|"
_LOG_DETAIL_PREFIX = "| 日期 | 批次 | 年级 | 文件 |"


def _is_log_sep(ln: str) -> bool:
    return ln.startswith("|") and not ln.replace("|", "").replace("-", "").replace(":", "").strip()


def _is_log_detail_row(ln: str) -> bool:
    return ln.startswith("| 20") and ln.count("|") == 9


def _detail_block_end(lines: list[str]) -> int | None:
    """最后一张运行明细表的数据区末尾（插入位置）；没有明细表则返回 None。"""
    end = None
    for i, ln in enumerate(lines):
        if not (ln.startswith(_LOG_DETAIL_PREFIX) and ln.count("|") == 9):
            continue
        j = i + 1
        if j < len(lines) and _is_log_sep(lines[j]):
            j += 1
        while j < len(lines) and _is_log_detail_row(lines[j]):
            j += 1
        end = j
    return end


def _insert_log_row(old_log: str, row: str) -> str:
    """把一条运行明细插入同一张明细表，杜绝「末尾孤行」和「一张日志两套表头」。"""
    if not old_log.strip():
        return _LOG_DETAIL_HEADER + "\n" + _LOG_DETAIL_SEP + "\n" + row + "\n"
    lines = old_log.splitlines()
    end = _detail_block_end(lines)
    if end is None:
        return (old_log.rstrip("\n") + "\n\n" + _LOG_DETAIL_HEADER + "\n"
                + _LOG_DETAIL_SEP + "\n" + row + "\n")
    lines.insert(end, row)
    return "\n".join(lines) + ("\n" if old_log.endswith("\n") else "")


def _update_ledger_next(lp: Path, plan: str) -> bool:
    """把 commit 算出的下一节计划回写到台账顶部汇总表（全台账唯一来源）。

    第四轮整改 G 项：此前批次段还写一行「- 下一节计划：」，与顶部表格行
    重复，且改一处不会脏另一处。现在 commit 只回写顶部表格行。
    """
    if not lp.is_file():
        return False
    lines = lp.read_text(encoding="utf-8").splitlines()
    hit = False
    for i, ln in enumerate(lines):
        if ln.startswith("| 下一节计划 |"):
            lines[i] = f"| 下一节计划 | {plan} |"
            hit = True
    if hit:
        lp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return hit


def _ensure_ledger_next_row(lp: Path, plan: str, title: str) -> None:
    """台账缺少顶部汇总表时补齐，保证「下一节计划」始终有唯一来源。

    第六轮统一结构：46 份台账统一为「## 当前进度（唯一来源）」下的
    `| 下一节计划 | ... |` 键值行；commit 与 ledger-sync 都只回写这一行。
    """
    block = [title, "", "## 当前进度（唯一来源）", "",
             "| 项 | 内容 |", "|---|---|", f"| 下一节计划 | {plan} |", ""]
    if lp.is_file():
        lines = lp.read_text(encoding="utf-8").splitlines()
        if any(ln.startswith("| 下一节计划 |") for ln in lines):
            return
        rest = lines[1:] if lines and lines[0].startswith("# ") else lines
        while rest and not rest[0].strip():
            rest = rest[1:]
        lp.write_text("\n".join(block + rest).rstrip("\n") + "\n", encoding="utf-8")
    else:
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.write_text("\n".join(block).rstrip("\n") + "\n", encoding="utf-8")


def cmd_commit(cfg: dict, args) -> None:
    task = find_task(cfg, args.subject)
    batch, date_dash, hhmm, _ = resolve_time(args)
    shift = resolve_shift(cfg, args)
    fp = Path(args.file) if args.file else file_path(cfg, task, args.grade, batch)
    if not fp.is_file():
        die(f"文件不存在：{fp}")
    argv = validate_argv(cfg, task, args.grade, fp, args.with_kp_baseline)
    rc, output = run_validator(argv)
    if rc != 0:
        print(output)
        die(f"自检未通过（EXIT={rc}），不写台账与日志；先修到 0 错误再 commit")
    warns = output.count("[提醒]")
    st = stats_of(fp)
    label = cfg["shifts"][shift]["label"]
    pg = progress_of(cfg, task, args.grade)
    if pg["finished"] or pg["next_section"]:
        next_plan = _next_plan_text(pg)
    else:
        next_plan = f"大纲解析失败，停止并报告：{pg['warning'] or pg['outline_warning']}"
    next_label = (pg["next_compound"]
                  if task["subject"] == "english" and pg.get("next_compound")
                  else pg["next_section"]) or "全册完成/第二轮"
    chapter_hint = pg["next_unit"] or "沿用本批次写法"
    if (task["subject"] == "english" and pg.get("next_compound")
            and pg["next_compound"] != pg["next_unit"]):
        chapter_hint += f"（section 写 {pg['next_compound']}）"
    ledger = "\n".join([
        f"## 批次 {date_dash} · {hhmm} {label}",
        f"- 批次日期：{batch}；文件：{fp.name}",
        f"- 版本：{task['version']}；学期：{task['semester']}",
        f"- 覆盖章节：{'、'.join(st['chapters']) or '无'}",
        f"- 本日覆盖节（section）：{'、'.join(st['sections']) or '无'}",
        f"- 新增知识点（{len(st['points'])} 个）：{'、'.join(st['points']) or '无'}",
        f"- 题量：{st['question_count']} 道；题型分布：{st['q_types']}",
        f"- 难度分布：{st['difficulty']}；来源分布：{st['sources']}",
        f"- 题干去重：{'无重复' if not st['duplicate_stems'] else st['duplicate_stems']}",
        f"- 自检：通过（0 错误 / {warns} 提醒）",
        f"- 进度指针：大纲 {pg['items_count']} 节；上次做到 {pg['last_section'] or '首日'}；"
        f"同一节连续 {pg['streak']} 天",
        f"- 章节名写法（次日沿用）：{chapter_hint}",
    ] + ([f"- [提醒] {pg['warning']}"] if pg["warning"] else []) + [
        "",
        "## 已用知识点（本批次）",
    ] + [f"- {name}" for name in st["points"]])

    lp = ledger_path(cfg, task, args.grade)
    logp = log_path(cfg, task)
    log_row = (f"| {date_dash} | {cfg['shifts'][shift]['log_batch']} | g{args.grade} | {fp.name} | 完成 | "
               f"通过（0 错误 / {warns} 提醒） | {args.minutes} | {label}；下一节："
               f"{next_label} |")
    old_log = logp.read_text(encoding="utf-8") if logp.is_file() else ""
    new_log = _insert_log_row(old_log, log_row)
    # 兼容两套历史台账写法：新版「## 批次 YYYY-MM-DD」、原导出脚本「- 批次日期：YYYYMMDD」
    ledger_text_all = lp.read_text(encoding="utf-8", errors="replace") if lp.is_file() else ""
    batch_marks = (f"## 批次 {date_dash}", f"## 批次 {batch}", f"- 批次日期：{batch}")
    ledger_skip = bool(ledger_text_all) and any(m in ledger_text_all for m in batch_marks)

    if args.dry_run:
        print("# DRY-RUN，不写任何文件")
        print(f"# 追加到 {lp}（已存在同批次则跳过：{ledger_skip}）")
        print(ledger)
        print(f"\n# 补齐 {lp} 顶部汇总表（若缺）并回写「下一节计划」（唯一来源）：{next_plan}")
        print(f"\n# 写入 {logp}（明细行并入同一张运行明细表，不新增表头）")
        print(log_row)
        print(f"\n自检输出：{output.splitlines()[-2:]}")
        return
    _ensure_ledger_next_row(lp, next_plan,
                            f"# {task['subject_name']} · {args.grade} 年级台账")
    if not ledger_skip:
        append_text(lp, ledger)
    _update_ledger_next(lp, next_plan)
    logp.parent.mkdir(parents=True, exist_ok=True)
    logp.write_text(new_log, encoding="utf-8")
    print(f"[完成] g{args.grade} 自检 0 错误 / {warns} 提醒；台账 {lp}；日志 {logp}")
    print(f"[提醒] 本轮全部结束后执行 finish 释放锁："
          f"& \"{cfg['paths']['python']}\" \"{cfg['paths']['run_daily']}\" finish "
          f"--subject {task['subject']} --date {batch} --done N --minutes M")


_QTYPE_CN = {"choice": "选择", "single": "选择", "judge": "判断",
             "fill": "填空", "multiple": "多选", "answer": "简答"}


def _fmt_qtypes(st: dict, dict_style: bool) -> str:
    if dict_style:
        return str(st["q_types"])
    return " / ".join(f"{_QTYPE_CN.get(k, k)} {v}" for k, v in st["q_types"].items())


def _fmt_difficulty(st: dict, dict_style: bool, with_source: bool) -> str:
    if dict_style:
        s = str(st["difficulty"])
        if with_source:
            s += "；来源分布：" + str(st["sources"])
        return s
    return " / ".join(f"{k} 档 {v} 道" for k, v in st["difficulty"].items())


def _next_plan_text(pg: dict) -> str:
    if pg.get("finished"):
        return "全册已覆盖 → 第二轮（加深/换情境/跨章综合）或零新增处理，不重复做同一节"
    if pg.get("next_section"):
        # 英语多个单元复用同名板块（Story / Ready Go …），下一节必须写
        # 「Unit N 标题 / 板块」复合名，次日才不会又跳到最后一个单元。
        if pg.get("subject") == "english" and pg.get("next_compound"):
            return f"{pg['next_compound']}（order_index：{pg['next_order']}）"
        return (f"{pg['next_section']}（单元：{pg['next_unit']}；"
                f"order_index：{pg['next_order']}）")
    return ""


_NEXT_PLACEHOLDER_MARKS = ("待大纲", "按台账推进", "同单元后续课时")
_NEXT_PLAN_LIKE = ("（单元：", "order_index", "待大纲", "按台账推进", "同单元后续课时")


def _sync_ledger_text(text: str, batch: str, date_dash: str, st: dict | None,
                      pg: dict, force_next: bool = False,
                      allow_whole_file: bool = False) -> tuple:
    """就地重算台账的题量/难度/下一节；兼容新旧两套格式，重复执行 0 变更。

    st 为 None 时只重算下一节（用于没有当日 JSON 的历史台账）。
    force_next 会连已写具体值/占位表格行的下一节一起纠正（用于进度指针修错后的回写），
    此时下一节相关行全文扫描，题量/难度仍只在本批次段内重算。
    """
    lines = text.splitlines()
    headings = [i for i, ln in enumerate(lines) if ln.startswith("## 批次 ")]
    target = next((i for i in headings if date_dash in lines[i] or batch in lines[i]), None)
    if target is None:
        target = next((i for i, ln in enumerate(lines)
                       if ln.strip() == f"- 批次日期：{batch}"), None)
    if target is None:
        if not allow_whole_file:
            return text, 0, ["未找到本批次台账段（未改动）"]
        target, end = 0, len(lines)
    else:
        end = next((i for i in headings if i > target), len(lines))
    out = list(lines)
    plan = _next_plan_text(pg)
    compound = pg.get("last_compound") if pg.get("subject") == "english" else None
    warnings: list = []
    in_next = False
    scan_from = 0 if force_next else target
    scan_to = len(lines) if force_next else end

    def stale_next(ln: str) -> bool:
        return force_next or any(m in ln for m in _NEXT_PLACEHOLDER_MARKS)

    for i in range(scan_from, scan_to):
        ln = lines[i]
        in_batch = target <= i < end
        if in_batch and st is not None and ln.startswith("- 题量："):
            out[i] = (f"- 题量：{st['question_count']} 道；题型分布："
                      f"{_fmt_qtypes(st, '{' in ln)}")
        elif in_batch and st is not None and ln.startswith("- 难度分布："):
            out[i] = (f"- 难度分布："
                      f"{_fmt_difficulty(st, '{' in ln, '来源分布' in ln)}")
        elif ln.startswith("## 下一节计划"):
            in_next = True
        elif ln.startswith("## "):
            in_next = False
        elif ln.startswith("| 下一节计划 |") and stale_next(ln):
            if plan:
                out[i] = f"| 下一节计划 | {plan} |"
            else:
                warnings.append("大纲未解析出下一节，保留原占位文本")
        elif ln.startswith("- 下一节计划：") and stale_next(ln):
            if plan:
                out[i] = f"- 下一节计划：{plan}"
            else:
                warnings.append("大纲未解析出下一节，保留原占位文本")
        elif (in_next and ln.startswith("- ") and stale_next(ln)
              and any(m in ln for m in _NEXT_PLAN_LIKE)):
            if plan:
                out[i] = f"- {plan}"
            else:
                warnings.append("大纲未解析出下一节，保留原占位文本")
        elif (force_next and ln.startswith("- 章节名写法（次日沿用）：")
              and pg.get("next_unit")):
            hint = pg["next_unit"]
            if (pg.get("subject") == "english" and pg.get("next_compound")
                    and pg["next_compound"] != pg["next_unit"]):
                hint += f"（section 写 {pg['next_compound']}）"
            out[i] = f"- 章节名写法（次日沿用）：{hint}"
        elif (force_next and compound
              and ln.startswith("- 本日覆盖节（section）：")):
            out[i] = f"- 本日覆盖节（section）：{compound}"
    new_text = "\n".join(out) + ("\n" if text.endswith("\n") else "")
    changed = sum(1 for i in range(len(lines)) if out[i] != lines[i])
    return new_text, changed, warnings


def cmd_ledger_sync(cfg: dict, args) -> None:
    """人工运维：按当日 JSON 就地重算台账本批次段。只读预览用 --dry-run，写入需 --confirm I_KNOW。"""
    batch = args.date or datetime.now().strftime("%Y%m%d")
    date_dash = f"{batch[:4]}-{batch[4:6]}-{batch[6:]}"
    if not args.dry_run and args.confirm != "I_KNOW":
        die("写台账需显式 --confirm I_KNOW；只读预览请加 --dry-run")
    force_next = bool(getattr(args, "force_next", False))
    tasks = [find_task(cfg, args.subject)] if args.subject else cfg["tasks"]
    rows = []
    for task in tasks:
        for grade in task["grades"]:
            fp = file_path(cfg, task, grade, batch)
            lp = ledger_path(cfg, task, grade)
            key = f"{task['subject']}/g{grade}"
            if not lp.is_file() or (not fp.is_file() and not force_next):
                rows.append({"key": key, "status": "skipped", "changed": 0,
                             "reason": "当日 JSON 或台账不存在"})
                continue
            old = lp.read_text(encoding="utf-8")
            st = stats_of(fp) if fp.is_file() else None
            pg = progress_of(cfg, task, grade)
            new, changed, warns = _sync_ledger_text(
                old, batch, date_dash, st, pg,
                force_next=force_next, allow_whole_file=force_next)
            if pg.get("warning"):
                warns.append(f"进度指针提醒：{pg['warning']}")
            if changed and not args.dry_run:
                lp.write_text(new, encoding="utf-8")
            rows.append({"key": key, "status": "changed" if changed else "unchanged",
                         "changed": changed, "warnings": warns, "ledger": str(lp)})
    changed_files = [r for r in rows if r["changed"]]
    summary = {"batch_date": batch, "dry_run": bool(args.dry_run),
               "force_next": force_next,
               "files": len(rows), "changed_files": len(changed_files),
               "changed_lines": sum(r["changed"] for r in rows), "rows": rows}
    if args.json:
        dump(summary)
        return
    print(f"# 台账同步 · {batch}（{'DRY-RUN 只读预览' if args.dry_run else '已写入'}）")
    print(f"- 扫描 {len(rows)} 个年级；变更 {len(changed_files)} 份 / "
          f"{summary['changed_lines']} 行；未变更 {len(rows) - len(changed_files)} 份")
    for r in rows:
        if r["changed"]:
            print(f"  {r['key']:<14} 变更 {r['changed']} 行")
        if r.get("warnings"):
            print(f"  {r['key']:<14} 提醒：{'；'.join(r['warnings'])}")
    for r in rows:
        if r["status"] == "skipped":
            print(f"  {r['key']:<14} 跳过：{r['reason']}")


def _sync_log_text(text: str) -> tuple[str, int, list[str]]:
    """把运行日志归一成「一张明细表 + 唯一表头」；11-07 的历史汇总表原样保留。

    11-08 的明细行曾被 commit 直接追加到文件末尾，脱离表格、且各日志表头列名
    不一致（备注/覆盖）。这里把所有明细行按原顺序收拢到第一张明细表下。
    """
    lines = text.splitlines()
    drop: set[int] = set()
    for i, ln in enumerate(lines):
        if ln.startswith(_LOG_DETAIL_PREFIX) and ln.count("|") == 9:
            drop.add(i)
            if i + 1 < len(lines) and _is_log_sep(lines[i + 1]) and lines[i + 1].count("|") == 9:
                drop.add(i + 1)
        elif _is_log_detail_row(ln):
            drop.add(i)
    if not drop:
        return text, 0, []
    rows = [lines[i] for i in range(len(lines)) if _is_log_detail_row(lines[i])]
    insert_at = min(drop)
    out: list[str] = []
    for i, ln in enumerate(lines):
        if i in drop:
            if i == insert_at:
                out.extend([_LOG_DETAIL_HEADER, _LOG_DETAIL_SEP] + rows)
            continue
        out.append(ln)
    # 11-07 的历史汇总表已归档到 logs/_archive/；主日志只应有一张运行明细表。
    # 若又出现非明细表格块，只提示归档，不再插「勿混用」标注来掩盖双表。
    blocks: list[list[int]] = []
    cur: list[int] = []
    for i, ln in enumerate(out):
        if ln.startswith("|"):
            cur.append(i)
        elif cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    warnings = []
    for block in blocks:
        head = out[block[0]]
        if (head.startswith(_LOG_DETAIL_PREFIX) or _is_log_detail_row(head)
                or _is_log_sep(head) or len(block) < 2
                or not _is_log_sep(out[block[1]])):
            continue
        warnings.append(f"第 {block[0] + 1} 行有非运行明细表格块，请归档到 logs/_archive/")
    if out == lines:
        return text, 0, warnings
    new_text = "\n".join(out) + ("\n" if text.endswith("\n") else "")
    return new_text, len(drop), warnings


def cmd_log_sync(cfg: dict, args) -> None:
    """人工运维：归一运行日志表头（幂等）。只读预览用 --dry-run，写入需 --confirm I_KNOW。"""
    if not args.dry_run and args.confirm != "I_KNOW":
        die("写日志需显式 --confirm I_KNOW；只读预览请加 --dry-run")
    tasks = [find_task(cfg, args.subject)] if args.subject else cfg["tasks"]
    rows = []
    for task in tasks:
        lp = log_path(cfg, task)
        key = task["subject"]
        if not lp.is_file():
            rows.append({"key": key, "status": "skipped", "changed": 0,
                         "reason": "日志不存在", "log": str(lp)})
            continue
        old = lp.read_text(encoding="utf-8")
        new, changed, warns = _sync_log_text(old)
        if changed and not args.dry_run:
            lp.write_text(new, encoding="utf-8")
        rows.append({"key": key, "status": "changed" if changed else "unchanged",
                     "changed": changed, "warnings": warns, "log": str(lp)})
    changed_files = [r for r in rows if r["changed"]]
    summary = {"dry_run": bool(args.dry_run), "files": len(rows),
               "changed_files": len(changed_files),
               "changed_lines": sum(r["changed"] for r in rows), "rows": rows}
    if args.json:
        dump(summary)
        return
    print(f"# 运行日志归一（{'DRY-RUN 只读预览' if args.dry_run else '已写入'}）")
    print(f"- 扫描 {len(rows)} 份；变更 {len(changed_files)} 份 / "
          f"{summary['changed_lines']} 行；未变更 {len(rows) - len(changed_files)} 份")
    for r in rows:
        print(f"  {r['key']:<12} {r['status']:<10} {r['changed']} 行"
              + (f"  跳过：{r['reason']}" if r["status"] == "skipped" else ""))
        for w in r.get("warnings") or []:
            print(f"      [提醒] {w}")


def cmd_finish(cfg: dict, args) -> None:
    task = find_task(cfg, args.subject)
    batch, date_dash, hhmm, _ = resolve_time(args)
    lp = lock_path(cfg, task)
    logp = log_path(cfg, task)
    line = (f"- 本轮收尾 {date_dash} {hhmm}：完成 {args.done} 个年级 / 总耗时约 "
            f"{args.minutes} 分钟 / 未完成年级顺延至下一班（以运行日志为准）")
    if args.dry_run:
        print("# DRY-RUN")
        print(f"# 删除锁：{lp}（存在={lp.is_file()}）")
        print(f"# 追加到 {logp}：{line}")
        return
    if lp.is_file():
        lp.unlink()
    append_text(logp, line)
    print(f"[完成] 锁已释放：{lp}；收尾行已写入 {logp}")


def cmd_lock(cfg: dict, args) -> None:
    task = find_task(cfg, args.subject)
    batch, date_dash, hhmm, now_dt = resolve_time(args)
    lp = lock_path(cfg, task)
    li = lock_info(cfg, task, now_dt)
    if args.action == "status":
        dump(li)
        return
    if args.action == "release":
        if lp.is_file():
            lp.unlink()
            print(f"[完成] 锁已删除：{lp}")
        else:
            print(f"[完成] 锁本就不存在：{lp}")
        return
    if li["state"] == "fresh":
        die("检测到并行运行，本次跳过（锁 < 30 分钟）", code=3)
    if li["state"] == "stale":
        lp.unlink()
        print(f"[提醒] 清理残留锁：{li['raw']}")
    lp.parent.mkdir(parents=True, exist_ok=True)
    with lp.open("x", encoding="utf-8") as f:
        f.write(f"{date_dash} {hhmm}\n")
    print(f"[完成] 已加锁：{lp}（{date_dash} {hhmm}）")


def build_prompt(cfg: dict, task: dict, shift: str, batch: str | None = None) -> str:
    meta = cfg["shifts"][shift]
    py = cfg["paths"]["python"]
    run = cfg["paths"]["run_daily"]
    grades = ",".join(str(g) for g in task["grades"])
    rules = "\n".join(f"  - {r}" for r in task["rules"])
    batch_line = (f"  - 批次日期 BATCH_DATE = {batch}（固定，不随系统日期变化）；文件名、台账、日志都用它；"
                  "22:00 班最迟 23:30 停手，不补昨天\n"
                  "  - 本次为手动单次执行（非定时任务）：跑完即结束，不要等待下一次触发"
                  if batch else
                  "  - 批次日期 BATCH_DATE = 本次触发时刻的日期（YYYYMMDD，Asia/Shanghai），定下后全程不变；"
                  "文件名、台账、日志都用它；22:00 班最迟 23:30 停手，不补昨天")
    english_rule = (
        f"  - 英语 section 命名：{cfg['policy']['english_section_naming']}\n"
        if task["subject"] == "english" else ""
    )
    text = f"""你是深圳地区资深{task['subject_name']}教师兼教研员。本次是「{task['title']}」的 {shift}:{task['minute']:02d} 班次（{meta['label']}），按固定参数为学科知识库新增当日 JSON 内容。

【固定配置 · 不得自行更改】
  - subject={task['subject']}；学科={task['subject_name']}；version={task['version']}；semester={task['semester']}（上册）；grades={grades}（按此顺序）
  - 内容根：{cfg['paths']['content_root']}
{batch_line}
  - 格式标准：先读 {cfg['paths']['readme']} 的完整规则，再读 {cfg['paths']['instruction']} 的「第零步~第六步 / 三班职责 / 跨日与批次日期 / 并行防重锁」；格式与命题规则以这两份文件为准
  - 参数唯一源：{CFG_PATH}；确定性动作一律走驱动脚本 {run}
  - 大纲硬约束：单元/节必须来自 {cfg['paths']['baseline_dir']}\\{task['outline']} 中本年级那一节，清单外不写；大纲缺该年级则停止并报告
  - 章节推进（防重复做同一节）：plan.grades[].next_section 与 context 的「今日进度指针」由脚本按大纲顺序 + 历史产出算出，今天只做这一节（next_unit 写 chapters.name、next_order 写 order_index），不回头重做、不跳节；一节可拆 2 天但要标注；全册覆盖完进入第二轮或零新增。补漏班不推进新节
  - 产出量：每年级 3~6 个知识点 / 18~28 道题（每知识点 ≥4 题）；至少 4 种题型且含 1 多选、1 主观；难度 1-2:3:4-5 ≈ 4:4:2；status=published
  - 生成期约束：{cfg['policy']['generation_constraints']}
  - 来源：知识点 original/教研组自编，题目 original/自主命题；不照搬教材原题与真题
{english_rule}  - 学科规则：
{rules}

【工具映射 · 只用这些工具完成】
  - 读文件：read_file / search_content / list_dir；写新 JSON：write_to_file（UTF-8 无 BOM）；追加台账/日志：驱动脚本 commit / finish
  - 跑命令：execute_command（PowerShell）；确定性判断（批次日期、锁、快路径、自检、统计）全部交给驱动脚本，不靠自己心算

【执行步骤】
  1. 列目录做快路径：`& "{py}" "{run}" plan --subject {task['subject']} --shift {shift} --date <BATCH_DATE> --json`。若 plan.idle=true，只把 plan.idle_log_line 追加到 {cfg['paths']['logs_dir']}\\{task['subject']}_{task['semester']}.md（用 replace_in_file 或 execute_command 追加），一句话汇报后结束。
  2. 加锁：`& "{py}" "{run}" lock --subject {task['subject']} --action acquire --date <BATCH_DATE>`；返回「检测到并行运行」就立即结束。
  3. 按 plan.todos 顺序逐年级闭环，一个年级 0 错误后才进下一个：
     a. `& "{py}" "{run}" context --subject {task['subject']} --grade <G> --date <BATCH_DATE>` 拿到今日进度指针 next_section、本年级大纲段、已用知识点名、已用题干、章节名写法、台账尾部
     b. 按 README + 指令文件生成 JSON，用 write_to_file 写到 plan.grades[G].file；同批次已有同名文件就跳过，绝不覆盖
     c. `& "{py}" "{run}" validate --subject {task['subject']} --grade <G> --date <BATCH_DATE>`；有错误逐条修到 EXIT=0；提醒项逐条说明
     d. `& "{py}" "{run}" commit --subject {task['subject']} --grade <G> --date <BATCH_DATE> --minutes <耗时>` 自动追加台账与运行日志
  4. 收尾：`& "{py}" "{run}" finish --subject {task['subject']} --date <BATCH_DATE> --done <完成年级数> --minutes <总耗时>` 释放锁并补收尾行。
  5. 汇报：一张年级表（文件/知识点数/题目数/自检）、题型与难度分布、来源分布、设计意图、明日计划、待人工复核项。

【班次职责】{meta['detail']}。{('补漏班单次最多 3 个年级，先修自检失败再补缺文件，不推进新节。' if meta['role'] == 'repair' else '进攻班按年级从小到大全量推进，做完几个算几个。')}
【禁止】{cfg['policy']['boundary']}。某年级无可新增内容时不产空 JSON，只在台账追加一行「无新增：原因」。
"""
    if batch:
        text = text.replace("<BATCH_DATE>", batch)
    return text


def cmd_prompt(cfg: dict, args) -> None:
    task = find_task(cfg, args.subject)
    batch = args.date if getattr(args, "date", None) else None
    print(build_prompt(cfg, task, resolve_shift(cfg, args), batch))


def build_payload(cfg: dict, task: dict, shift: str) -> dict:
    # 第五轮 D 选 B：晚班（shift key 仍为 22）前移到 21 点档，
    # 21:30 起按学科顺序每分钟一条；02/12 两班沿用各学科原分钟值。
    hours = cfg["policy"].get("shift_hours", {"02": 2, "12": 12, "22": 22})
    hour = int(hours[shift])
    offset = int(cfg["policy"].get("rrule_minute_offset", 0))
    late_base = cfg["policy"].get("late_shift_minute_base")
    if shift == "22" and late_base is not None:
        minute = int(late_base) + int(task["minute"]) // 5
    else:
        minute = int(task["minute"]) + offset
    english_rule = (
        f"【英语 section 命名】{cfg['policy']['english_section_naming']}。"
        if task["subject"] == "english" else ""
    )
    return {
        "mode": "suggested create",
        "name": f"{task['title']}-{hour:02d}点班",
        "prompt": (f"执行每日教研：学科={task['subject']}（{task['subject_name']}），版本={task['version']}，"
                   f"学期={task['semester']}，年级={','.join(map(str, task['grades']))}，班次={shift}（{cfg['shifts'][shift]['label']}）。"
                   f"先读 {HERE / '01-主提示词.md'} 全文并严格照办；参数以 {CFG_PATH} 为准，"
                   f"BATCH_DATE 取触发当天日期（Asia/Shanghai）。用 {cfg['paths']['run_daily']} 的 plan/lock/context/validate/commit/finish 完成闭环。"
                   f"只产出 JSON 与台账/日志，不导入、不连库、不改已有文件、不读写其他学科文件。"
                   f"【生成期约束】{cfg['policy']['generation_constraints']}。"
                   f"{english_rule}"
                   f"【硬约束】禁止调用 db_ops.py / ops.*，禁止执行任何入库或回退动作"
                   f"（run_all.* 已无入库 Action，ops.* 需人工显式 -Date + -ConfirmToken I_KNOW，"
                   f"另需运行时一次性 6 位交互确认码，示例/提示词均无法代填），"
                   f"禁止执行 ledger-sync / log-sync（人工运维命令）；"
                   f"_run_daily.py 已无 import/restore 子命令。"),
        "scheduleType": "recurring",
        "rrule": f"FREQ=DAILY;BYHOUR={hour};BYMINUTE={minute}",
        "cwds": cfg["paths"]["workspace"],
        "status": "PAUSED",
    }


def cmd_payload(cfg: dict, args) -> None:
    task = find_task(cfg, args.subject)
    dump(build_payload(cfg, task, resolve_shift(cfg, args)))


def cmd_payloads(cfg: dict, args) -> None:
    data = {
        "description": "把原导出包 9 条「每天 3 班」的 cron 任务映射成 CodeBuddy 自动化载荷（启用形态 B：02/12/21 点档；审阅稿，不可直接注册）",
        "source": "../automation_20261108/01-九条任务全文可复制.md",
        "tool": "automation_update（延迟工具，经 DeferExecuteTool 调用；mode=suggested create）——本轮及此前从未调用，且当前禁止调用",
        "registration": {
            "allowed": False,
            "reason": ("02/12 两班的 BYMINUTE 仍是 0/5/…/40，与原文 9 条 cron 完全同分钟；"
                       "两套调度不得同时 ACTIVE，因此在停用原文 cron 之前，载荷自身不具备可直接注册的条件。"),
            "enablement_decision": {
                "status": "已选定 B（用户 2026-11-08 拍板）：27 条全留，原 22 点班前移到 21 点档",
                "selected": "B",
                "options": [
                    {"id": "A", "payload_count": 9, "selected": False,
                     "detail": "CodeBuddy 侧只保留 02 点班（9 条载荷），12/22 两班继续由原文 cron 承担"},
                    {"id": "B", "payload_count": 27, "selected": True,
                     "detail": "27 条全留，21 点档晚班 21:30-21:38 每学科 1 分钟错峰，避开 23:30 停手规则"},
                ],
                "schedule": {
                    "02": "BYHOUR=2;BYMINUTE=0/5/…/40（各学科原分钟）",
                    "12": "BYHOUR=12;BYMINUTE=0/5/…/40（各学科原分钟）",
                    "21": "BYHOUR=21;BYMINUTE=30..38（按学科顺序每分钟一条）",
                },
                "blocking": ("形态已定但尚未启用：必须先停用原文 9 条 cron，逐条复核 RRULE / cwds / prompt，"
                             "再把 status 从 PAUSED 改为 ACTIVE。在此之前 registration.allowed 恒为 False，"
                             "禁止把本文件喂给 automation_update"),
            },
            "prerequisites": [
                "停用原文 9 条 cron（两套调度不得同时 ACTIVE）",
                "逐条复核 27 条 RRULE 的 BYHOUR / BYMINUTE、cwds 与 prompt",
                "把 status 从 PAUSED 改为 ACTIVE",
            ],
            "note": "本文件仅供审阅与留痕；02/12 两班照现状直接喂给 automation_update 仍会同分钟对撞。",
        },
        "note": ("⚠️ 不可直接注册。RRULE 只用单个 BYHOUR（多值 BYHOUR 未验证），所以 9 学科 × 3 班次 = 27 条。"
                 "status 全部 PAUSED，与原文「当前状态：已停止」一致；本次及此前从未调用 automation_update 实际注册。"
                 "第五轮 D 用户选 B：02/12 两班 BYMINUTE = tasks.json 的 minute 原值（rrule_minute_offset=0）；"
                 "原 22 点班前移到 21 点档，BYMINUTE=30..38 按学科顺序每分钟一条"
                 "（21:30-21:59 只剩 30 分钟，放不下 9×5 分钟错峰；各学科有独立锁文件，1 分钟错峰不触发同科并行锁），"
                 "距「最迟 23:30 停手」≥1h52m，原冲突解除。不再使用「整条 RRULE BYHOUR +1」方案。"
                 "启用前先停用另一侧调度并逐条复核，禁止两套调度同时 ACTIVE；保持不注册，避免产生计划外副作用。"),
        "count": len(cfg["tasks"]) * len(cfg["shifts"]),
        "payloads": [build_payload(cfg, t, s) for t in cfg["tasks"] for s in ("02", "12", "22")],
    }
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"[完成] 已写出 {data['count']} 条载荷：{args.out}")
    else:
        print(text, end="")


# 入库 / 回退能力已迁移到独立人工运维脚本 db_ops.py；本脚本不含任何连库能力。
# 教研会话只被允许调用 plan / lock / context / validate / commit / finish 等命令。


def main() -> int:
    ap = argparse.ArgumentParser(description="每日教研 CodeBuddy 版驱动（默认只读）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(sp, grade=True):
        sp.add_argument("--subject", required=True)
        if grade:
            sp.add_argument("--grade", type=int)
        sp.add_argument("--date", help="BATCH_DATE，YYYYMMDD；默认今天")
        sp.add_argument("--now", help="触发时刻 HH:MM；默认当前")
        sp.add_argument("--shift", choices=["02", "12", "22"])
        sp.add_argument("--with-kp-baseline", action="store_true",
                        help="自检额外带 --kp-baseline（原导出口径默认不带）")

    sp = sub.add_parser("list"); sp.add_argument("--json", action="store_true")
    sp = sub.add_parser("outline"); common(sp)
    sp = sub.add_parser("progress"); common(sp)
    sp = sub.add_parser("context"); common(sp)
    sp.add_argument("--stems-limit", type=int, default=30)
    sp.add_argument("--ledger-tail", type=int, default=60)
    sp = sub.add_parser("plan"); common(sp, grade=False)
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--no-check", action="store_true", help="不跑已有文件的自检（更快，但补漏班会漏判）")
    sp.add_argument("--acquire", action="store_true", help="同时加锁（写动作）")
    sp = sub.add_parser("validate"); common(sp)
    sp.add_argument("--file", help="自定义待校验文件路径")
    sp = sub.add_parser("commit"); common(sp)
    sp.add_argument("--file", help="自定义产出文件路径")
    sp.add_argument("--minutes", type=int, default=0, help="本年级耗时（分）")
    sp.add_argument("--dry-run", action="store_true")
    sp = sub.add_parser("ledger-sync",
                        help="人工运维：按当日 JSON 就地重算台账本批次段（幂等）")
    sp.add_argument("--date", help="BATCH_DATE，YYYYMMDD；默认今天")
    sp.add_argument("--subject", help="只处理某学科；默认全 9 学科")
    sp.add_argument("--force-next", action="store_true",
                    help="按大纲重算并强制回写下一节（含占位表格行/错误具体值）；"
                         "无当日 JSON 的历史台账也能处理，配合 --subject 限定范围")
    sp.add_argument("--dry-run", action="store_true", help="只读预览，不写台账")
    sp.add_argument("--confirm", choices=["I_KNOW"], help="写入台账的显式确认")
    sp.add_argument("--json", action="store_true")
    sp = sub.add_parser("log-sync",
                        help="人工运维：把运行日志归一成一张明细表/唯一表头（幂等）")
    sp.add_argument("--subject", help="只处理某学科；默认全 9 学科")
    sp.add_argument("--dry-run", action="store_true", help="只读预览，不写日志")
    sp.add_argument("--confirm", choices=["I_KNOW"], help="写入日志的显式确认")
    sp.add_argument("--json", action="store_true")
    sp = sub.add_parser("finish"); common(sp, grade=False)
    sp.add_argument("--done", type=int, default=0)
    sp.add_argument("--minutes", type=int, default=0)
    sp.add_argument("--dry-run", action="store_true")
    sp = sub.add_parser("lock"); common(sp, grade=False)
    sp.add_argument("--action", choices=["status", "acquire", "release"], required=True)
    sp = sub.add_parser("prompt"); common(sp, grade=False)
    sp = sub.add_parser("payload"); common(sp, grade=False)
    sp = sub.add_parser("payloads"); sp.add_argument("--out", help="输出 JSON 文件路径；不传则打印")

    def all_common(sp):
        sp.add_argument("--date", help="BATCH_DATE，YYYYMMDD；默认今天")
        sp.add_argument("--now", help="触发时刻 HH:MM；默认当前")
        sp.add_argument("--shift", choices=["02", "12", "22"])
        sp.add_argument("--no-check", action="store_true", help="不跑已有文件的自检")
        sp.add_argument("--with-kp-baseline", action="store_true")
        sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("all-plan"); all_common(sp)
    sp = sub.add_parser("all-verify"); all_common(sp)
    sp.add_argument("--spec-since", help="覆盖规格生效日（YYYYMMDD）；早于该日的批次只提醒不判失败")
    sp.add_argument("--include-legacy", action="store_true",
                    help="把 legacy 试跑样本批次也计入未通过（默认不计入回归基线）")
    sp.add_argument("--strict", action="store_true", help="缺文件/提醒也算未通过，退出码 1")
    sp = sub.add_parser("all-prompt"); all_common(sp)
    sp.add_argument("--no-strict", action="store_true", help="生成的提示词核实步骤不加 --strict")

    args = ap.parse_args()
    cfg = load_cfg()
    if args.cmd in ("outline", "context", "validate", "commit", "progress") and args.grade is None:
        die("该命令必须带 --grade")
    if args.cmd == "plan" and args.acquire:
        proto = argparse.Namespace(subject=args.subject, date=args.date, now=args.now,
                                   shift=args.shift, action="acquire")
        cmd_lock(cfg, proto)
    {
        "list": cmd_list, "outline": cmd_outline, "progress": cmd_progress,
        "context": cmd_context,
        "plan": cmd_plan, "validate": cmd_validate, "commit": cmd_commit,
        "ledger-sync": cmd_ledger_sync, "log-sync": cmd_log_sync,
        "finish": cmd_finish, "lock": cmd_lock, "prompt": cmd_prompt,
        "payload": cmd_payload, "payloads": cmd_payloads,
        "all-plan": cmd_all_plan, "all-verify": cmd_all_verify,
        "all-prompt": cmd_all_prompt,
    }[args.cmd](cfg, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
