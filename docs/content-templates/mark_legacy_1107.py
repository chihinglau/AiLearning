"""把 11-07 批次统一打上 `_legacy` 标记（元数据变更，不改内容、不改库）。

为什么：`tasks.json.policy.legacy_batches = ["20261107"]` 已经把 11-07 整批定性为历史规格，
但盘上只有 8 份 math 文件带 `_legacy`；chinese / english 的 18 份 1107 文件没打，
于是同一批历史内容在 `_validate_daily.py` 里一半按提醒、一半按错误，口径不一致。

做法（与 `mark_legacy_json.py` 的既有约定一致）：
1. 改前留**逐字节副本**到 `_archive/<name>.pre-legacy-mark.json`；
2. 只加 `_legacy` / `_legacy_note` 两个元数据键（`_METADATA_KEYS`，内容哈希不变）；
3. 同步 `_import-manifest.json` 的 `current_file_sha256`，`imported_sha256` / `imported_content_sha256` **不改**；
4. 写 `_archive/legacy-1107-mark.provenance.txt` 记录改前改后 sha。

用法：
    python mark_legacy_1107.py            # 只算不写
    python mark_legacy_1107.py --apply    # 真正写盘 + 更新 manifest
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

CT = Path(__file__).resolve().parent
ARCHIVE = CT / "_archive"
MANIFEST = CT / "_import-manifest.json"
NOTE = ("11-07 历史批次：产出规格早于「每知识点 ≥4 道 / 题型齐备」的现行口径，"
        "按 legacy 处理（校验器降级为提醒）；重跑覆盖前不要当成本轮产出")
META_KEYS = ("_legacy", "_legacy_note", "_consolidated")


def content_sha256(doc: dict) -> str:
    payload = {k: v for k, v in doc.items() if k not in META_KEYS}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def targets() -> list[Path]:
    return sorted(p for p in (CT / "daily").glob("*/g*/*_20261107.json") if p.is_file())


def main() -> int:
    parser = argparse.ArgumentParser(description="11-07 批次统一打 _legacy 标记")
    parser.add_argument("--apply", action="store_true", help="真正写盘并更新 manifest")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files = manifest.get("files") or {}
    rows, changed = [], 0
    for path in targets():
        raw = path.read_bytes()
        doc = json.loads(raw.decode("utf-8"))
        rel = path.relative_to(CT).as_posix()
        if rel.startswith("daily/"):
            rel = rel[len("daily/"):]          # manifest 的键不带 daily/ 前缀
        if doc.get("_legacy"):
            rows.append((rel, "已是 legacy", hashlib.sha256(raw).hexdigest(), ""))
            continue
        old_sha = hashlib.sha256(raw).hexdigest()
        if args.apply:
            (ARCHIVE / f"{path.stem}.pre-legacy-mark.json").write_bytes(raw)
            doc["_legacy"] = True
            doc["_legacy_note"] = NOTE
            new_raw = (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            path.write_bytes(new_raw)
            new_sha = hashlib.sha256(new_raw).hexdigest()
            entry = files.get(rel)
            if not entry:
                entry = files.get(rel.replace("/", "\\")) or None
            if entry:
                entry["current_file_sha256"] = new_sha
                entry["legacy_marked_at"] = datetime.now().strftime("%Y%m%d_%H%M%S")
            rows.append((rel, "已打标", old_sha, new_sha))
        else:
            rows.append((rel, "将打标", old_sha, ""))
        changed += 1

    if args.apply and changed:
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        lines = [f"11-07 批次统一 _legacy 标记  {datetime.now():%Y-%m-%dT%H:%M:%S}", "",
                 "改因：tasks.json.policy.legacy_batches=[\"20261107\"] 已把整批定性为历史规格，"
                 "但盘上只有 8 份 math 打了标记，口径不一致。",
                 "约束：只加 _legacy/_legacy_note（元数据键，内容哈希不变），manifest 只改 current_file_sha256，"
                 "imported_sha256 / imported_content_sha256 不动；改前逐字节副本留在本目录 *.pre-legacy-mark.json。",
                 ""]
        for rel, state, old, new in rows:
            lines.append(f"- {rel} | {state} | {old} -> {new or '(未改)'}")
        (ARCHIVE / "legacy-1107-mark.provenance.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    for rel, state, old, new in rows:
        print(f"[{state}] {rel}  {old[:12]} -> {(new or '-')[:12]}")
    print(f"合计 {len(rows)} 份，本轮改动 {changed} 份（{'已写盘' if args.apply else 'dry-run，未写盘'}）")
    if not args.apply:
        print("要真正执行请加 --apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
