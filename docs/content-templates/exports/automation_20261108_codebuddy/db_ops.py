"""人工运维脚本：数据库备份 / 入库 / 回退 / 变更留痕。

与教研执行脚本 `_run_daily.py` 完全分离：`_run_daily.py` 不含任何连库能力，
教研会话只被允许调用 plan/lock/context/validate/commit/finish 等只读或产出命令。

本脚本**只能由人工显式调用**，且所有写库动作都必须带 `--confirm I_KNOW`：

    python db_ops.py import --date 20261108 --confirm I_KNOW
    python db_ops.py import --date 20261108 --dry-run --confirm I_KNOW
    python db_ops.py import-books --stamp 20261109 --confirm I_KNOW          # 整册（daily_consolidated）
    python db_ops.py import-books --stamp 20261109 --dry-run --confirm I_KNOW
    python db_ops.py restore --backup <backup.db> --force --confirm I_KNOW
    python db_ops.py audit --since <backup.db> --out db_op_<date>_<HHMMSS>.json

对外入口 `ops.cmd -Action import|import-dry|restore` 要求人工显式
`-ConfirmToken I_KNOW`（脚本不再代填），`run_all.*` 已彻底移除入库 Action。
第五轮加固后该口令**不再是唯一闸门**：`ops.ps1` 还要求显式 `-Date`、
`restore` 的 `-BackupPath` 必须存在，并在控制台打印一次性 6 位确认码要求人工输入；
`db_ops.py` 的直接调用同样只允许人工运维，教研提示词里明确禁止调用本脚本与上述入口。

`audit` 是只读命令，专门解决「库改了但查不到改了什么」：以任一备份库为基线，
逐行 diff `textbooks/chapters/knowledge_points/questions`，输出新增/删除/改动的 id、
字段前后值、受影响的题目数与回滚点。**规则：每一次库手术（含手工 SQL）都必须补一份
`db_op_<date>_<HHMMSS>.json`**，机器可读记录优先于文档段落。
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG_PATH = HERE / "tasks.json"
IMPORT_TABLES = ("textbooks", "chapters", "knowledge_points", "questions")


def die(msg: str, code: int = 2) -> None:
    print(f"[错误] {msg}", file=sys.stderr)
    raise SystemExit(code)


def load_cfg() -> dict:
    return json.loads(CFG_PATH.read_text(encoding="utf-8"))


def P(cfg: dict, key: str) -> Path:
    return Path(cfg["paths"][key])


def backend_paths(cfg: dict) -> tuple[Path, Path, Path, Path]:
    backend = Path(cfg["paths"]["workspace"]) / "backend"
    return (backend, Path(cfg["paths"]["python"]),
            backend / "scripts" / "import_content.py", backend / "scripts" / "db_backup.py")


def run_backend(cfg: dict, argv: list[str], env_extra: dict | None = None) -> tuple[int, str]:
    backend, py, _, _ = backend_paths(cfg)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    if env_extra:
        env.update(env_extra)
    res = subprocess.run([str(py)] + argv, cwd=str(backend), env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace")
    return res.returncode, res.stdout.strip()


def db_url_of(cfg: dict) -> str:
    rc, out = run_backend(cfg, ["-c", "from app.core.config import settings; print(settings.database_url)"])
    if rc != 0:
        die(f"读取 settings.database_url 失败：{out[-400:]}")
    url = out.splitlines()[-1].strip()
    if not url.startswith("sqlite:///"):
        die(f"入库仅支持 SQLite，当前 DATABASE_URL={url}")
    return url


def db_path_of(cfg: dict, url: str) -> Path:
    backend, _, _, _ = backend_paths(cfg)
    raw = Path(url[len("sqlite:///"):]).expanduser()
    return (raw if raw.is_absolute() else backend / raw).resolve()


def db_stats(db: Path) -> dict:
    with sqlite3.connect(str(db)) as conn:
        return {t: conn.execute(f"select count(*) from {t}").fetchone()[0] for t in IMPORT_TABLES}


def db_stems(db: Path) -> set[str]:
    stems = set()
    with sqlite3.connect(str(db)) as conn:
        for (content,) in conn.execute("select content from questions"):
            try:
                stem = str(json.loads(content).get("stem") or "").strip()
            except (json.JSONDecodeError, TypeError, AttributeError):
                continue
            if stem:
                stems.add(stem)
    return stems


def day_files(cfg: dict, batch: str) -> list[Path]:
    return sorted(P(cfg, "daily_dir").rglob(f"*_{batch}.json"))


def manifest_data(cfg: dict) -> dict:
    mp = P(cfg, "manifest")
    if not mp.is_file():
        return {"files": {}}
    return json.loads(mp.read_text(encoding="utf-8"))


def pending_import_labels(cfg: dict, batch: str) -> list[tuple[str, Path]]:
    """本次会被真正导入的文件（manifest 里没有 / 内容已改 / 上次失败）。"""
    data = manifest_data(cfg)
    pending = []
    for fp in day_files(cfg, batch):
        label = fp.relative_to(P(cfg, "daily_dir")).as_posix()
        entry = data.get("files", {}).get(label) or {}
        digest = hashlib.sha256(fp.read_bytes()).hexdigest()
        # 三列语义（2026-11-08 第十一轮整改）：imported_sha256 = 导入当刻的字节 sha（永不改写），
        # current_file_sha256 = 盘上现值，imported_content_sha256 = 导入当刻剥元数据后的内容哈希。
        # 「待导入」= 没入库过，或内容真变了（仅元数据变更不算）。
        imported_sha = str(entry.get("imported_sha256") or entry.get("sha256") or "")
        same = imported_sha == digest
        if not same and entry.get("imported_content_sha256"):
            same = entry.get("imported_content_sha256") == _content_sha256(json.loads(fp.read_text(encoding="utf-8")))
        if not (entry.get("status") == "ok" and same):
            pending.append((label, fp))
    return pending


_METADATA_KEYS = ("_legacy", "_legacy_note")


def _content_sha256(doc: dict) -> str:
    """文档内容哈希（剔除元数据键）——与 backend/app/services/content_import.py、
    docs/content-templates/_validate_daily.py 同实现，三处需保持一致。"""
    payload = {k: v for k, v in doc.items() if k not in _METADATA_KEYS}
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def stems_of(fp: Path) -> list[str]:
    data = json.loads(fp.read_text(encoding="utf-8"))
    return [str(q.get("stem") or "").strip()
            for ch in data.get("chapters") or [] for q in ch.get("questions") or []]


def run_verify(cfg: dict, batch: str) -> tuple[int, str]:
    """只读核实交给教研脚本；运维脚本不重复实现校验规则。"""
    res = subprocess.run([sys.executable, str(P(cfg, "run_daily")),
                          "all-verify", "--date", batch, "--json"],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace",
                         env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return res.returncode, res.stdout.strip()


def backup_db(cfg: dict, url: str) -> Path:
    rc, out = run_backend(cfg, ["-m", "scripts.db_backup", "--database-url", url])
    if rc != 0:
        die(f"备份失败（未做任何导入）：{out[-600:]}")
    m = re.search(r"\[backup\] wrote (.+)", out)
    if not m:
        die(f"备份命令未输出备份路径（未做任何导入）：{out[-600:]}")
    backup = Path(m.group(1).strip())
    if not backup.is_file() or backup.stat().st_size == 0:
        die(f"备份文件不存在或为空：{backup}")
    print(f"[备份] {backup}（{backup.stat().st_size} 字节）")
    return backup


def cmd_import(cfg: dict, args) -> None:
    batch = args.date or datetime.now().strftime("%Y%m%d")
    backend, _, importer, backuper = backend_paths(cfg)
    url = db_url_of(cfg)
    db = db_path_of(cfg, url)
    manifest = P(cfg, "manifest")
    daily = P(cfg, "daily_dir")
    for path, label in ((importer, "import_content.py"), (backuper, "db_backup.py"),
                        (db, "目标数据库")):
        if not path.is_file():
            die(f"{label} 不存在：{path}")
    files = day_files(cfg, batch)
    if not files:
        die(f"没有找到 BATCH_DATE={batch} 的教研文件：{daily}")

    print(f"# 一键入库 · 批次 {batch} · 库 {db}")
    print(f"- 当日文件 {len(files)} 份；manifest：{manifest}")
    rc, out = run_verify(cfg, batch)
    if rc not in (0, 1):
        die(f"离线自检脚本执行失败：{out[-400:]}")
    verify = json.loads(out)
    if verify["totals"]["fail"]:
        die(f"离线自检有 {verify['totals']['fail']} 处失败，先修 JSON 再入库；备份尚未创建")
    t = verify["totals"]
    clean = t["ok"] + t["warn"]
    print(f"- 离线自检：{clean} 份文件内容合格（0 错误，其中 {t['warn']} 份有分布/规格提醒）"
          f" / {t['fail']} 失败 / {t['missing']} 缺文件（缺文件不阻断入库，只导入已产出文件）")

    backup = backup_db(cfg, url)
    before = db_stats(db)
    print(f"- 入库前统计：{before}")
    pending = pending_import_labels(cfg, batch)
    print(f"- 本次待导入（非已入库且未变更）：{len(pending)} 份")

    base = ["-m", "scripts.import_content", "--path", str(daily),
            "--pattern", f"*_{batch}.json"]
    if args.overwrite:
        base += ["--overwrite"]
    rc, dry = run_backend(cfg, base + ["--dry-run"], env_extra={"DATABASE_URL": url})
    print(f"- 试跑（dry-run，已回滚）：EXIT={rc}")
    if dry:
        print("\n".join("  " + ln for ln in dry.splitlines()[-8:]))
    if rc != 0:
        die(f"试跑未通过，已中止；数据库未改动。回退备份：{backup}")

    if args.dry_run:
        print(f"[试跑完成] 未写入数据库；备份已保留：{backup}")
        print(f"[回退命令] Copy-Item -Force \"{backup}\" \"{db}\"")
        return

    rc, result = run_backend(cfg, base + ["--manifest", str(manifest)],
                             env_extra={"DATABASE_URL": url})
    print(f"- 正式导入：EXIT={rc}")
    if result:
        print("\n".join("  " + ln for ln in result.splitlines()[-10:]))
    if rc != 0:
        die(f"导入有失败文件，请按报告修复后重跑（幂等）。如需整体回退："
            f"Copy-Item -Force \"{backup}\" \"{db}\"")

    after = db_stats(db)
    delta = {t: after[t] - before[t] for t in IMPORT_TABLES}
    stems = db_stems(db)
    verified = {}
    for label, fp in pending:
        qs = stems_of(fp)
        verified[label] = {"questions": len(qs), "stems_in_db": sum(1 for s in qs if s in stems)}
    all_in = all(v["questions"] == v["stems_in_db"] for v in verified.values()) if verified else True
    report = {
        "batch_date": batch, "database_url": url, "database": str(db),
        "backup": str(backup), "restore_hint": f"Copy-Item -Force \"{backup}\" \"{db}\"",
        "files_total": len(files), "files_pending": len(pending),
        "overwrite": bool(args.overwrite), "dry_run_rc": 0, "import_rc": rc,
        "stats_before": before, "stats_after": after, "stats_delta": delta,
        "pending_verification": verified, "all_new_stems_in_db": all_in,
        "import_tail": result.splitlines()[-20:],
    }
    stamp = datetime.now().strftime("%H%M%S")
    report_path = HERE / f"import_report_{batch}_{stamp}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"- 入库后统计：{after}")
    print(f"- 增量：{delta}")
    for label, v in verified.items():
        print(f"  [核实] {label}: {v['stems_in_db']}/{v['questions']} 道题已入库")
    print(f"- 报告：{report_path}")
    print(f"[完成] 新数据全部入库={all_in}；回退：{report['restore_hint']}")
    if not all_in:
        die("有新增题目的题干未查到，请检查导入日志；备份仍可用上述命令回退", code=1)


def _csv(value: str | None) -> list[str]:
    return [x.strip() for x in (value or "").replace("，", ",").split(",") if x.strip()]


def _grades(value: str | None) -> set[int]:
    """解析年级白名单：'1,8' / '1-9' / '7,9'（2026-11-10 评审 P1-3）。"""
    out: set[int] = set()
    for token in _csv(value):
        if "-" in token:
            lo, _, hi = token.partition("-")
            if lo.isdigit() and hi.isdigit() and int(lo) <= int(hi):
                out.update(range(int(lo), int(hi) + 1))
                continue
        if token.startswith("g") and token[1:].isdigit():
            out.add(int(token[1:]))
        elif token.isdigit():
            out.add(int(token))
    return out


def _book_scope(files: list[Path], books_dir: Path, args) -> list[Path]:
    """把「校验范围」与「导入范围」钉在同一个集合上。

    修复 2026-11-10 评审 P1-3：旧写法是「全目录校验 + 按 stamp 导入」，
    任一坏册就能把整批锁死（实测 13 册失败 → 46 册全被挡，含已合格的 12 册）。
    """
    subjects = set(_csv(getattr(args, "subjects", None)))
    grades = _grades(getattr(args, "grades", None))
    only = _csv(getattr(args, "only", None))
    if not (subjects or grades or only):
        return files

    def rel(f: Path) -> str:
        return f.relative_to(books_dir).as_posix()

    def subject_of(f: Path) -> str:
        parts = rel(f).split("/")
        return parts[0] if parts else ""

    def grade_of(f: Path) -> int | None:
        m = re.search(r"g(\d+)", rel(f))
        return int(m.group(1)) if m else None

    kept = []
    for f in files:
        if subjects and subject_of(f) not in subjects:
            continue
        if grades and grade_of(f) not in grades:
            continue
        if only and not any(fnmatch.fnmatch(rel(f), t) or fnmatch.fnmatch(f.name, t)
                            for t in only):
            continue
        kept.append(f)
    return kept


def parse_book_lines(output: str) -> list[dict]:
    """把 import_content.py 的逐册输出解析为机读 per_book（评审复评 §八-4）。

    逐行样例：
        math/g1/math_g1_first_20261109_book.json: 教材已存在，章节 +0/~0，知识点 +0/~0，题目 +0，跳过重复 139
        math/g1/math_g1_first_20261109_book.json: 已导入且文件未变，跳过（manifest）
        math/g1/math_g1_first_20261109_book.json: 导入失败 - <原因>
    解析失败的行不会丢：以 status=other 保留 raw，控制台不截断、报告里可逐册核对。
    """
    line_re = re.compile(r"^(?P<file>\S+\.json):\s*(?P<body>.*)$")
    stat_re = re.compile(
        r"章节 \+(?P<ch_new>\d+)/~(?P<ch_upd>\d+)，知识点 \+(?P<kp_new>\d+)/~(?P<kp_upd>\d+)"
        r"，题目 \+(?P<q_new>\d+)，跳过重复 (?P<q_skip>\d+)"
    )
    rows = []
    for raw in (output or "").splitlines():
        m = line_re.match(raw.strip())
        if not m:
            continue
        file, body = m.group("file"), m.group("body")
        row = {"file": file, "status": "other", "raw": raw.strip()}
        s = stat_re.search(body)
        if s:
            row.update({
                "status": "ok",
                "textbook_created": "新建" in body.split("，")[0],
                "chapters_created": int(s.group("ch_new")),
                "chapters_updated": int(s.group("ch_upd")),
                "knowledge_created": int(s.group("kp_new")),
                "knowledge_updated": int(s.group("kp_upd")),
                "questions_created": int(s.group("q_new")),
                "questions_skipped": int(s.group("q_skip")),
            })
        elif "跳过（manifest）" in body:
            row["status"] = "skipped_manifest"
        elif "导入失败" in body:
            row["status"] = "failed"
            row["error"] = body.split(" - ", 1)[-1]
        rows.append(row)
    return rows


def book_summary(rows: list[dict]) -> dict:
    def total(key: str) -> int:
        return sum(int(r.get(key) or 0) for r in rows)

    return {
        "parsed": len(rows),
        "ok": sum(1 for r in rows if r["status"] == "ok"),
        "skipped_manifest": sum(1 for r in rows if r["status"] == "skipped_manifest"),
        "failed": sum(1 for r in rows if r["status"] == "failed"),
        "other": sum(1 for r in rows if r["status"] == "other"),
        "chapters_created": total("chapters_created"),
        "knowledge_created": total("knowledge_created"),
        "questions_created": total("questions_created"),
        "questions_skipped": total("questions_skipped"),
    }


def cmd_import_books(cfg: dict, args) -> None:
    """整册入库：`daily_consolidated/**/*_<stamp>_book.json`。

    与 `import` 的差别：daily 分片按「批次日期」扫 `daily_dir`，整册文件在另一棵目录树、
    文件名是 `*_book.json`（归集器产出），`import --date` 永远扫不到它们。此命令把
    整册文件单独走一遍「校验 → 备份 → 试跑 → 正式导入 → 逐册核对 → 报告」。

    2026-11-10 评审 P1-3：可用 --subjects / --grades / --only 圈定批次，
    校验与导入都只作用于这同一个文件集合（不再「全目录校验」）。
    """
    backend, _, importer, backuper = backend_paths(cfg)
    url = db_url_of(cfg)
    db = db_path_of(cfg, url)
    manifest = P(cfg, "manifest")
    books_dir = P(cfg, "content_root") / "daily_consolidated"
    stamp = args.stamp or ""
    pattern = f"*_{stamp}_book.json" if stamp else "*_book.json"
    for path, label in ((importer, "import_content.py"), (backuper, "db_backup.py"), (db, "目标数据库")):
        if not path.is_file():
            die(f"{label} 不存在：{path}")
    if not books_dir.is_dir():
        die(f"整册目录不存在：{books_dir}（先跑 _consolidate_daily.py --apply）")
    all_files = sorted(books_dir.rglob(pattern))
    files = _book_scope(all_files, books_dir, args)
    if not files:
        die(f"按范围过滤后没有整册文件：目录内 {len(all_files)} 份 / {pattern}；"
            f"subjects={getattr(args, 'subjects', None)} grades={getattr(args, 'grades', None)} "
            f"only={getattr(args, 'only', None)}")

    scope = {"subjects": _csv(getattr(args, "subjects", None)),
             "grades": sorted(_grades(getattr(args, "grades", None))),
             "only": _csv(getattr(args, "only", None))}
    print(f"# 整册入库 · {pattern} · 库 {db}")
    print(f"- 整册文件 {len(files)} 份（目录内 {len(all_files)} 份，范围={scope}）")

    validator = P(cfg, "validator")
    version_map = P(cfg, "baseline_dir") / "_subject-version-map.json"
    # 机读汇总（P0-2）：即使校验失败也落盘，供报告列出具体失败文件（P1-4）。
    summary_path = HERE / f"books_validation_{stamp or 'all'}_{datetime.now():%Y%m%d_%H%M%S}.json"
    argv = [str(P(cfg, "python")), str(validator), *[str(f) for f in files],
            "--manifest", str(manifest), "--json-out", str(summary_path)]
    if version_map.is_file():
        argv += ["--version-map", str(version_map)]
    proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding="utf-8", errors="replace",
                          env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    rc, vout = proc.returncode, (proc.stdout or "").strip()
    tail = vout.splitlines()[-8:]
    print("\n".join("  " + ln for ln in tail))
    if rc != 0:
        failed = []
        if summary_path.is_file():
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                failed = [f"{r['name']}（{r['errors']} 处错误）"
                          for r in summary.get("files", []) if not r.get("passed")]
            except (json.JSONDecodeError, KeyError, TypeError):
                failed = []
        print(f"- 校验失败文件 {len(failed)} 份：")
        for name in failed:
            print(f"    [失败] {name}")
        print(f"- 机读汇总：{summary_path}")
        die(f"整册校验未通过（exit {rc}），先修整册文件再入库；备份尚未创建。"
            f"失败文件：{'; '.join(failed) if failed else '见上方输出'}")

    before = db_stats(db)
    print(f"- 入库前统计：{before}")
    backup = backup_db(cfg, url)

    # 导入范围与校验范围严格同源：--only 传的就是上面校验过的同一批文件。
    labels = ",".join(f.relative_to(books_dir).as_posix() for f in files)
    base = ["-m", "scripts.import_content", "--path", str(books_dir),
            "--pattern", pattern, "--only", labels]
    if args.overwrite:
        base += ["--overwrite"]
    rc, dry = run_backend(cfg, base + ["--dry-run"], env_extra={"DATABASE_URL": url})
    per_book_dry = parse_book_lines(dry)
    dry_summary = book_summary(per_book_dry)
    print(f"- 试跑（dry-run，已回滚）：EXIT={rc}；逐册 {len(per_book_dry)}/{len(files)} 条"
          f"（完整逐册结果写入报告，控制台只打汇总）")
    print(f"- 试跑逐册汇总：{dry_summary}")
    if rc != 0:
        for row in per_book_dry:
            if row["status"] == "failed":
                print(f"    [失败] {row['file']}: {row.get('error', '')}")
        if not per_book_dry:
            print("\n".join("  " + ln for ln in dry.splitlines()[-8:]))
        die(f"试跑未通过，已中止；数据库未改动。回退备份：{backup}")

    if args.dry_run:
        report = {
            "mode": "books-dry", "stamp": stamp, "database_url": url, "database": str(db),
            "backup": str(backup), "restore_hint": f"Copy-Item -Force \"{backup}\" \"{db}\"",
            "files_total": len(files), "files_in_dir": len(all_files), "pattern": pattern,
            "scope": scope, "validation_summary": str(summary_path),
            "stats_before": before, "stats_after": db_stats(db),
            "dry_run_exit": rc, "per_book": per_book_dry, "per_book_summary": dry_summary,
        }
        report_path = HERE / f"import_report_books_{datetime.now():%Y%m%d_%H%M%S}_dry.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"- 报告：{report_path}")
        print(f"[试跑完成] 未写入数据库；备份已保留：{backup}")
        print(f"[回退命令] Copy-Item -Force \"{backup}\" \"{db}\"")
        return

    rc, result = run_backend(cfg, base + ["--manifest", str(manifest)],
                             env_extra={"DATABASE_URL": url})
    per_book = parse_book_lines(result)
    print(f"- 正式导入：EXIT={rc}；逐册 {len(per_book)}/{len(files)} 条（完整逐册结果写入报告）")
    print(f"- 正式导入逐册汇总：{book_summary(per_book)}")
    if rc != 0:
        for row in per_book:
            if row["status"] == "failed":
                print(f"    [失败] {row['file']}: {row.get('error', '')}")
        if not per_book:
            print("\n".join("  " + ln for ln in (result or "").splitlines()[-10:]))
        die(f"导入有失败文件（幂等，可修后重跑）。整体回退：Copy-Item -Force \"{backup}\" \"{db}\"")

    after = db_stats(db)
    delta = {t: after[t] - before[t] for t in IMPORT_TABLES}
    stems = db_stems(db)
    verified = {}
    for fp in files:
        qs = stems_of(fp)
        verified[fp.name] = {"questions": len(qs),
                             "stems_in_db": sum(1 for s in qs if s.strip() in stems)}
    all_in = all(v["stems_in_db"] == v["questions"] for v in verified.values())
    report = {
        "mode": "books", "stamp": stamp, "database_url": url, "database": str(db),
        "backup": str(backup), "restore_hint": f"Copy-Item -Force \"{backup}\" \"{db}\"",
        "files_total": len(files), "files_in_dir": len(all_files), "pattern": pattern,
        "scope": scope, "validation_summary": str(summary_path),
        "overwrite": bool(args.overwrite),
        "stats_before": before, "stats_after": after, "stats_delta": delta,
        "per_book": per_book, "per_book_summary": book_summary(per_book),
        "per_book_dry": per_book_dry, "per_book_dry_summary": dry_summary,
        "pending_verification": verified, "all_book_stems_in_db": all_in,
        "import_tail": (result or "").splitlines()[-20:],
    }
    report_path = HERE / f"import_report_books_{datetime.now():%Y%m%d_%H%M%S}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"- 入库后统计：{after}")
    print(f"- 增量：{delta}")
    for name, v in verified.items():
        if v["stems_in_db"] != v["questions"]:
            print(f"  [未命中] {name}: {v['stems_in_db']}/{v['questions']}（整册题量 vs 库内命中）")
    print(f"- 报告：{report_path}")
    print(f"[完成] 整册题目全部可查={all_in}；回退：{report['restore_hint']}")
    if not all_in:
        print("[提醒] 有题目未按题干查到：多见于同册旧内容还在库内、或题干空白，请逐册核对后再定是否回退",
              file=sys.stderr)


def cmd_restore(cfg: dict, args) -> None:
    backup = Path(args.backup).expanduser()
    if not backup.is_file():
        die(f"备份文件不存在：{backup}")
    if not args.force:
        die("回退会覆盖当前数据库，请显式加 --force 确认")
    url = db_url_of(cfg)
    db = db_path_of(cfg, url)
    pre = backup_db(cfg, url)
    print(f"[安全备份] 回退前的当前库已另存：{pre}")
    code = ("from pathlib import Path; "
            "from app.services.backup import restore_sqlite, verify_sqlite; "
            f"restore_sqlite(Path(r'{backup}'), Path(r'{db}'), overwrite=True); "
            f"verify_sqlite(Path(r'{db}')); print('restored ok')")
    rc, out = run_backend(cfg, ["-c", code])
    if rc != 0:
        die(f"回退失败：{out[-500:]}")
    print(f"[完成] 已从 {backup} 回退到 {db}；当前统计：{db_stats(db)}")


def read_table(db: Path, table: str) -> dict[int, dict]:
    with sqlite3.connect(str(db)) as conn:
        conn.row_factory = sqlite3.Row
        return {row["id"]: dict(row) for row in conn.execute(f"select * from {table}")}


def kp_parent_map(db: Path) -> dict[int, tuple[str, int | None]]:
    with sqlite3.connect(str(db)) as conn:
        return {r[0]: (r[1], r[2]) for r in conn.execute("select id,name,parent_id from knowledge_points")}


def section_of(kid: int, parents: dict[int, tuple[str, int | None]]) -> str:
    """沿 parent_id 上溯到顶层节点，返回其名称（顶层即 section）。"""
    cur = kid
    for _ in range(8):
        name, parent = parents.get(cur, ("", None))
        if not parent or parent not in parents:
            return name
        cur = parent
    return parents.get(cur, ("", None))[0]


def stem_head(content, limit: int = 60) -> str:
    try:
        text = str(json.loads(content).get("stem") or "")
    except (json.JSONDecodeError, TypeError):
        text = str(content)
    return " ".join(text.split())[:limit]


def slim_row(table: str, row: dict, parents: dict[int, tuple[str, int | None]]) -> dict:
    """报告只留可读字段，避免把整段题干/解析塞进 JSON。"""
    if table == "knowledge_points":
        parent_id = row.get("parent_id")
        return {
            "id": row["id"], "subject": row.get("subject"), "grade": row.get("grade"),
            "name": row.get("name"), "node_type": row.get("node_type"),
            "parent_id": parent_id,
            "parent_name": parents.get(parent_id, ("", None))[0] if parent_id else None,
            "section": section_of(row["id"], parents),
            "order_index": row.get("order_index"),
        }
    if table == "questions":
        return {
            "id": row["id"], "chapter_id": row.get("chapter_id"),
            "knowledge_point_id": row.get("knowledge_point_id"),
            "q_type": row.get("q_type"), "difficulty": row.get("difficulty"),
            "status": row.get("status"), "stem": stem_head(row.get("content")),
        }
    return {"id": row["id"], "name": row.get("name"), "order_index": row.get("order_index")}


def diff_table(ref: Path, cur: Path, table: str, parents: dict[int, tuple[str, int | None]]) -> dict:
    old, new = read_table(ref, table), read_table(cur, table)
    deleted = [slim_row(table, old[i], parents) for i in sorted(old.keys() - new.keys())]
    added = [slim_row(table, new[i], parents) for i in sorted(new.keys() - old.keys())]
    updated = []
    for i in sorted(old.keys() & new.keys()):
        changes = {
            k: {"from": old[i].get(k), "to": new[i].get(k)}
            for k in old[i]
            if k in new[i] and old[i][k] != new[i][k]
        }
        if table == "questions" and "content" in changes:
            changes["content"] = {"from": stem_head(changes["content"]["from"]),
                                  "to": stem_head(changes["content"]["to"])}
        if changes:
            updated.append({"id": i, "row": slim_row(table, new[i], parents), "changes": changes})
    return {"deleted": deleted, "added": added, "updated": updated}


def cmd_audit(cfg: dict, args) -> None:
    """只读：以备份库为基线 diff 目标库（默认当前库），产出机器可读的库变更记录。"""
    cur = (Path(args.current).expanduser() if args.current
           else db_path_of(cfg, db_url_of(cfg)))
    ref = Path(args.since).expanduser()
    if not ref.is_file():
        die(f"基线库不存在：{ref}")
    if ref.resolve() == cur.resolve():
        die("基线库与当前库是同一个文件，无需 diff")
    for db in (ref, cur):
        with sqlite3.connect(str(db)) as conn:
            names = {r[0] for r in conn.execute("select name from sqlite_master where type='table'")}
        missing = [t for t in IMPORT_TABLES if t not in names]
        if missing:
            die(f"{db} 不是内容库（缺表 {missing}）")

    parents = kp_parent_map(cur)
    tables = {t: diff_table(ref, cur, t, parents) for t in IMPORT_TABLES}

    with sqlite3.connect(str(cur)) as conn:
        qc = conn.execute("pragma quick_check").fetchone()[0]
        fk_issues = conn.execute("pragma foreign_key_check").fetchall()
        orphan = conn.execute(
            "select count(*) from knowledge_points where parent_id is not null "
            "and parent_id not in (select id from knowledge_points)"
        ).fetchone()[0]

    kp_ids = {row["id"] for t in ("deleted", "added", "updated")
              for row in tables["knowledge_points"][t]}
    with sqlite3.connect(str(cur)) as conn:
        q_on_kp = conn.execute(
            f"select count(*) from questions where knowledge_point_id in ({','.join('?' * len(kp_ids))})",
            tuple(kp_ids),
        ).fetchone()[0] if kp_ids else 0
        per_section = conn.execute(
            "select parent_id, count(*) from knowledge_points where parent_id is not null "
            "group by parent_id order by parent_id"
        ).fetchall()

    changed = {t: sum(len(tables[t][k]) for k in ("deleted", "added", "updated")) for t in tables}
    after = db_stats(cur)
    before = db_stats(ref)
    report = {
        "_meta": {
            "kind": "db_op_report",
            "generated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "tool": "db_ops.py audit（只读）",
            "reference_db": str(ref),
            "current_db": str(cur),
            "semantics": "以 reference 为基线，列出当前库新增/删除/改动的行，并给出受影响题数与回滚点",
            "rule": "每次库手术都必须补一份 db_op_<date>_<HHMMSS>.json，机器可读记录优先于文档段落",
        },
        "stats": {
            "reference": before, "current": after,
            "delta": {t: after[t] - before[t] for t in IMPORT_TABLES},
        },
        "checks": {
            "quick_check": qc,
            "foreign_key_violations": len(fk_issues),
            "orphan_parent_refs": orphan,
        },
        "changes": tables,
        "impact": {
            "knowledge_points_touched": sorted(kp_ids),
            "questions_on_touched_kps": q_on_kp,
            "questions_updated": len(tables["questions"]["updated"]),
            "kp_children_per_section": {str(k): v for k, v in per_section},
        },
        "rollback": {
            "backup": str(ref),
            "hint": (f"回退整库：python db_ops.py restore --backup \"{ref}\" --force --confirm I_KNOW"
                     "（会先自动备份当前库）"),
        },
    }

    out = Path(args.out).expanduser() if args.out else HERE / f"db_op_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"# 库变更 diff · 基线 {ref.name} → 当前 {cur.name}")
        print(f"- 计数：{before} → {after}（delta {report['stats']['delta']}）")
        print(f"- 检查：quick_check={qc}；外键问题 {len(fk_issues)}；孤立父引用 {orphan}")
        for table, item in tables.items():
            if changed[table]:
                print(f"- {table}：删除 {len(item['deleted'])} / 新增 {len(item['added'])} / 改动 {len(item['updated'])}")
                for row in item["deleted"]:
                    print(f"    [删除] id={row['id']} {row.get('name') or row.get('stem') or ''}")
                for row in item["added"]:
                    print(f"    [新增] id={row['id']} {row.get('name') or row.get('stem') or ''}")
                for row in item["updated"]:
                    keys = "、".join(row["changes"].keys())
                    label = row["row"].get("name") or row["row"].get("stem") or ""
                    print(f"    [改动] id={row['id']} {label} → {keys}")
        print(f"- 受影响题目：{q_on_kp} 道（挂在 {len(kp_ids)} 个改动/删除知识点上）")
        print(f"- 报告：{out}")
        print(f"- 回滚点：{ref}（db_ops.py restore --backup ... --force --confirm I_KNOW）")


def main() -> int:
    ap = argparse.ArgumentParser(description="人工运维：数据库备份/入库/回退/变更留痕（教研脚本不含此能力）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("import")
    sp.add_argument("--date", help="BATCH_DATE；默认今天")
    sp.add_argument("--dry-run", action="store_true", help="只备份 + 试跑，不写数据库")
    sp.add_argument("--overwrite", action="store_true",
                    help="同步已存在题目的字段（如调整后的 difficulty）；不传时同题干题按幂等跳过")
    sp.add_argument("--confirm", required=True, choices=["I_KNOW"],
                    help="显式确认会写数据库；教研会话禁止传入")
    sp = sub.add_parser("import-books",
                        help="整册入库：daily_consolidated/**/*_<stamp>_book.json（校验→备份→试跑→导入→核对）")
    sp.add_argument("--stamp", help="整册文件名里的批次日期 YYYYMMDD；不传则导全部 *_book.json")
    sp.add_argument("--subjects", help="逗号分隔的学科白名单，如 math,chinese（不传=全部）")
    sp.add_argument("--grades", help="逗号分隔/区间年级白名单，如 1,8 或 2-6 或 g7,g9（不传=全部）")
    sp.add_argument("--only", help="逗号分隔的文件白名单（相对 daily_consolidated 的路径/文件名/通配）")
    sp.add_argument("--dry-run", action="store_true", help="只校验 + 备份 + 试跑，不写数据库")
    sp.add_argument("--overwrite", action="store_true", help="同步已存在题目的字段")
    sp.add_argument("--confirm", required=True, choices=["I_KNOW"],
                    help="显式确认会写数据库；教研会话禁止传入")
    sp = sub.add_parser("restore")
    sp.add_argument("--backup", required=True, help="备份 .db 路径")
    sp.add_argument("--force", action="store_true", help="确认覆盖当前数据库")
    sp.add_argument("--confirm", required=True, choices=["I_KNOW"],
                    help="显式确认会覆盖数据库；教研会话禁止传入")
    sp = sub.add_parser("audit", help="只读：以备份库为基线 diff 当前库，产出 db_op_*.json")
    sp.add_argument("--since", required=True, help="基线备份库 .db 路径")
    sp.add_argument("--current", help="目标库 .db 路径；默认取 settings.database_url 指向的当前库")
    sp.add_argument("--out", help="报告输出路径；默认本目录 db_op_<时间戳>.json")
    sp.add_argument("--json", action="store_true", help="同时把报告打印到 stdout")
    args = ap.parse_args()
    cfg = load_cfg()
    {"import": cmd_import, "import-books": cmd_import_books, "restore": cmd_restore,
     "audit": cmd_audit}[args.cmd](cfg, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
