"""给 11-07 的 8 份 math JSON 打 `_legacy` 标记（一次性工具，留痕在 _archive + manifest）。

背景（第九轮评审 C 项）：占位章节清理后，这 8 份文件里的 `chapters[].name` 在库里
0 条命中——g1/g2/g4/g6/g7/g8 的章名已迁移到教材真实章节，g3/g5 的章已整章删除。
文件本身没有任何标记，重导时 g1/g2/g4/g6/g7/g8 会被 aliases 自动归位（无提示），
g3/g5 会被 discard 整块丢弃（rc 仍为 0，报告里和「导入成功」长得一样）。

做三件事：
  1. 改前**逐字节**副本存 `_archive/<name>.pre-legacy-mark.json` + provenance；
  2. 文件顶层加 `"_legacy": true` 与 `"_legacy_note"`；
  3. 同步 `_import-manifest.json` 里对应条目的**当前值**两列
     （`current_file_sha256` / `imported_content_sha256`）—— 校验器据此判定
     「已入库·仅元数据变更」，11-07 批次不假红；**`imported_sha256` 不动**
     （那是导入当刻，永不改写）。

只改标记，不改任何章节名 / 知识点 / 题目。用法：python mark_legacy_json.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

CT = Path(__file__).resolve().parents[2]
ARCHIVE = CT / "_archive"
MANIFEST = CT / "_import-manifest.json"
GRADES = [1, 2, 3, 4, 5, 6, 7, 8]
NOTE = (
    "2026-11-07 试跑批次的旧样章内容：本文件的章节名在教材目录上不存在。"
    "占位章节清理（2026-11-08）后该章已迁移到教材真实章节或整章删除。"
    "重导本文件时导入层按 chapter_aliases.json 处理——aliases 重定向到教材真实章节、"
    "discard 整块丢弃——不会把旧版数据写回库。"
    "详见 docs/content-templates/exports/automation_20261108_codebuddy/05-占位章节清理立项.md"
)


METADATA_KEYS = ("_legacy", "_legacy_note")


def write_if_changed(path: Path, text: str) -> bool:
    """字节一致就不落盘（第十二轮评审 C 项）：内容没变却重写一遍会污染 mtime。"""
    new = text.encode("utf-8")
    old = path.read_bytes() if path.is_file() else None
    if old == new:
        return False
    path.write_bytes(new)
    return True


def content_sha256(doc: dict) -> str:
    """与 backend/app/services/content_import.py、_validate_daily.py 同实现（三处需一致）。"""
    payload = {k: v for k, v in doc.items() if k not in METADATA_KEYS}
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def main() -> int:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    touched = []
    for g in GRADES:
        src = CT / "daily" / "math" / ("g%d" % g) / ("math_g%d_first_20261107.json" % g)
        if not src.is_file():
            print("[跳过] 不存在：%s" % src)
            continue
        raw = src.read_bytes()
        data = json.loads(raw.decode("utf-8"))
        if data.get("_legacy"):
            print("[已标记] g%d 已有 _legacy，跳过" % g)
            continue
        bak = ARCHIVE / (src.stem + ".pre-legacy-mark.json")
        shutil.copy2(src, bak)
        new = {"_legacy": True, "_legacy_note": NOTE}
        new.update(data)
        src.write_text(json.dumps(new, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8", newline="\n")
        new_raw = src.read_bytes()
        label = "math/g%d/%s" % (g, src.name)
        entry = manifest.get("files", {}).get(label)
        if entry is not None:
            # 三列语义（第十一轮整改）：imported_sha256 = 导入当刻的字节 sha（**永不改写**）；
            # 这里只更新「当前值」与「内容哈希」，让校验器判定为「已入库·仅元数据变更」。
            entry.setdefault("imported_sha256", hashlib.sha256(raw).hexdigest())
            entry["current_file_sha256"] = hashlib.sha256(new_raw).hexdigest()
            entry.setdefault("imported_content_sha256", content_sha256(data))
            entry.pop("sha256", None)
            entry["legacy_marked"] = True
            entry["legacy_marked_at"] = stamp
        touched.append({
            "grade": g, "file": str(src.relative_to(CT)).replace("\\", "/"),
            "archive": str(bak.relative_to(CT)).replace("\\", "/"),
            "sha_before": hashlib.sha256(raw).hexdigest(),
            "sha_after": hashlib.sha256(new_raw).hexdigest(),
            "bytes_before": len(raw), "bytes_after": len(new_raw),
            "chapters": [c.get("name") for c in data.get("chapters") or []],
            "manifest_updated": entry is not None,
        })
        print("[标记] g%d %s：sha %s → %s，副本 %s"
              % (g, src.name, touched[-1]["sha_before"][:12],
                 touched[-1]["sha_after"][:12], bak.name))

    if not touched:
        # 没有文件被打标记 → 不写 manifest、也不重写留痕（否则会把已有「逐份明细」覆盖成空段落）
        print("[manifest] 无需改动（无文件被打标记）")
        print("[留痕] 未重写（本次零变更）")
        return 0

    write_if_changed(MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    lines = [
        "生成时间：%s" % datetime.now().isoformat(timespec="seconds"),
        "用途：占位章节清理后，给 11-07 的 8 份 math JSON 打 `_legacy` 标记。",
        "改了什么：**只加顶层 `_legacy` / `_legacy_note` 两个键**，章节名 / 知识点 / 题目一字未改。",
        "为什么改：清理后这 8 份文件的章节名在库里 0 条命中，重导会静默归位或静默丢弃，文件上看不出来。",
        "配套动作：`_import-manifest.json` 里这 8 条已按三列语义更新"
        "（imported_sha256 保持导入当刻不改写、current_file_sha256 更新为现值、"
        "imported_content_sha256 为剥元数据后的内容哈希），"
        "校验器据此判定「已入库·仅元数据变更」，11-07 批次不假红。",
        "",
        "逐份明细（sha / 字节 / 原章节名）：",
    ]
    for t in touched:
        lines.append("  - %s：sha %s → %s，%d → %d 字节，章节 %s"
                     % (t["file"], t["sha_before"], t["sha_after"],
                        t["bytes_before"], t["bytes_after"], t["chapters"]))
        lines.append("    改前副本：%s" % t["archive"])
    prov = ARCHIVE / "math_11-07_legacy-mark.provenance.txt"
    write_if_changed(prov, "\n".join(lines) + "\n")
    print("[留痕] %s" % prov)
    print("[manifest] 已同步 %d 条 sha256" % sum(1 for t in touched if t["manifest_updated"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
