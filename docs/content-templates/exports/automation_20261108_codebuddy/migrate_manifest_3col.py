"""把 `_import-manifest.json` 从「单列 sha256」迁移到「三列语义」（一次性，带留痕）。

背景（第十一轮评审 A 项，P1 概念问题）：
上一轮给 8 份 11-07 math JSON 打 `_legacy` 标记时，为了不让校验器假红，把 manifest 里
这 8 条的 `sha256` 就地刷成了当前文件版本。于是 manifest 记的从「导入当刻那一版」变成了
「盘上现值」——「已入库」这个信号的含义被降级成「这个文件被登记过」：任何对内容的就地
改写，只要顺手刷 sha，校验器仍会说「已入库」。

三列语义（本脚本落地）：
  imported_sha256         导入当刻的字节 sha，永不改写
  current_file_sha256     盘上现值
  imported_content_sha256 导入当刻剔除元数据键后的内容哈希

判定「已入库」三态（_validate_daily.py::_manifest_import_state）：
  字节一致 → unchanged；字节不同但内容哈希一致 → meta_only；两者都不同 → changed。

迁移规则：
  - 8 份 legacy 文件：imported_sha256 = 打标记之前的 sha（_archive/*.pre-legacy-mark.json
    就是那 8 份的逐字节副本）；imported_content_sha256 = 剥掉元数据键后的内容哈希。
  - 其余 41 条：文件自导入后未变更 → 三列都取当前值。

只改 manifest 的这 3 个键，status / report / imported_at 等原样保留。
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

CT = Path(__file__).resolve().parents[2]
MANIFEST = CT / "_import-manifest.json"
ARCHIVE = CT / "_archive"
METADATA_KEYS = ("_legacy", "_legacy_note")


def content_sha256(doc: dict) -> str:
    """与 backend/app/services/content_import.py、_validate_daily.py 同实现（三处需一致）。"""
    payload = {k: v for k, v in doc.items() if k not in METADATA_KEYS}
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def write_if_changed(path: Path, text: str) -> bool:
    """字节一致就不落盘（第十二轮评审 C 项）。

    mtime 是这套体系里「这个文件何时被动过」的唯一证据：内容没变却重写一遍，会让
    以后的审计误判成「有人改过」。所以任何脚本写盘前都先比字节。
    """
    new = text.encode("utf-8")
    old = path.read_bytes() if path.is_file() else None
    if old == new:
        return False
    path.write_bytes(new)
    return True


def main() -> int:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = ARCHIVE / "_import-manifest.pre-3col.json"

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files = data.get("files", {})
    before = {label: {k: entry.get(k) for k in
                      ("imported_sha256", "current_file_sha256", "imported_content_sha256")}
              for label, entry in files.items()}
    rows = []
    expected: dict[str, dict] = {}
    pending: list[tuple[dict, dict]] = []
    for label, entry in files.items():
        fp = CT / "daily" / label
        if not fp.is_file():
            rows.append({"label": label, "state": "missing_file"})
            continue
        cur_raw = fp.read_bytes()
        cur_sha = hashlib.sha256(cur_raw).hexdigest()
        cur_doc = json.loads(cur_raw.decode("utf-8"))
        legacy_bak = ARCHIVE / (fp.stem + ".pre-legacy-mark.json")
        if cur_doc.get("_legacy") and legacy_bak.is_file():
            old_raw = legacy_bak.read_bytes()
            imported_sha = hashlib.sha256(old_raw).hexdigest()
            imported_content = content_sha256(json.loads(old_raw.decode("utf-8")))
            origin = "legacy 标记前副本"
        else:
            imported_sha = cur_sha
            imported_content = content_sha256(cur_doc)
            origin = "当前文件（导入后未变更）"
        rows.append({
            "label": label,
            "state": "legacy_meta_only" if imported_sha != cur_sha else "unchanged",
            "origin": origin,
            "imported_sha256": imported_sha,
            "current_file_sha256": cur_sha,
            "imported_content_sha256": imported_content,
        })
        expected[label] = {"imported_sha256": imported_sha,
                           "current_file_sha256": cur_sha,
                           "imported_content_sha256": imported_content}
        pending.append((entry, expected[label]))

    # 幂等：已是 schema v3 且三列与本次计算结果完全一致 → 什么都不做（保住 mtime 与留痕）
    same = (data.get("manifest_schema", {}).get("version") == 3
            and len(expected) == len(files)
            and all(before[label] == expected[label] for label in expected))
    if same:
        unchanged = sum(1 for r in rows if r["state"] == "unchanged")
        legacy = sum(1 for r in rows if r["state"] == "legacy_meta_only")
        print("[幂等] manifest 已是 schema v3 且三列一致（共 %d 条：unchanged %d / legacy_meta_only %d），"
              "本次不落盘、不改 mtime" % (len(rows), unchanged, legacy))
        return 0

    for entry, values in pending:
        entry.pop("sha256", None)
        entry.update(values)
        entry["manifest_3col_at"] = stamp

    shutil.copy2(MANIFEST, bak)

    data["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    data["manifest_schema"] = {
        "version": 3,
        "columns": {
            "imported_sha256": "导入当刻的字节 sha，永不改写",
            "current_file_sha256": "盘上现值",
            "imported_content_sha256": "导入当刻剔除元数据键（_legacy/_legacy_note）后的内容哈希",
        },
        "note": "「已入库」判定：字节一致 → 未变更；字节不同但内容哈希一致 → 仅元数据变更；"
                "否则 → 文件已变更、未重导（从严检查）",
    }
    wrote = write_if_changed(MANIFEST, json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print("[manifest] %s" % ("已写入" if wrote else "字节一致，未落盘"))

    lines = [
        "生成时间：%s" % datetime.now().isoformat(timespec="seconds"),
        "用途：把 _import-manifest.json 从单列 sha256 迁移到三列语义。",
        "为什么：上一轮打 _legacy 标记时把 8 条的 sha 就地刷成了当前文件版本，「已入库」的判据",
        "        被降级成「文件被登记过」——任何就地改写只要顺手刷 sha，校验器仍会说已入库。",
        "改了什么：每条加 imported_sha256（导入当刻，永不改写）/ current_file_sha256（盘上现值）",
        "        / imported_content_sha256（导入当刻剥元数据后的内容哈希）；删除旧的 sha256 键。",
        "        status / report / imported_at 等字段原样保留。",
        "配套：_validate_daily.py 的「已入库」判定改为三态（unchanged / meta_only / changed）；",
        "        backend/scripts/import_content.py 写入按三列落盘；db_ops.py 的待导入判定同步。",
        "",
        "改前副本：%s" % bak,
        "",
        "逐条明细：",
    ]
    for r in rows:
        lines.append("  - %-52s %-16s %s" % (r["label"], r["state"], r.get("origin", "文件不存在")))
    prov = ARCHIVE / "_import-manifest.pre-3col.provenance.txt"
    prov.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("[留痕] %s" % prov)
    print("[改前副本] %s" % bak)
    unchanged = sum(1 for r in rows if r["state"] == "unchanged")
    legacy = sum(1 for r in rows if r["state"] == "legacy_meta_only")
    print("[迁移] 共 %d 条：unchanged %d 条 / legacy_meta_only %d 条 / missing %d 条"
          % (len(rows), unchanged, legacy, len(rows) - unchanged - legacy))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())