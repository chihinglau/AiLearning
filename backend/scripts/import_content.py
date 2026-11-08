"""导入教研题库 / 知识库模板。

用法（在 backend 目录执行）：
    .venv\\Scripts\\python.exe -m scripts.import_content --path ..\\docs\\content-templates\\templates\\math.json
    .venv\\Scripts\\python.exe -m scripts.import_content --path ..\\docs\\content-templates\\daily ^
        --pattern "*_20261107.json" --manifest ..\\docs\\content-templates\\_import-manifest.json
    .venv\\Scripts\\python.exe -m scripts.import_content --path ..\\docs\\content-templates --dry-run

manifest 会记录目标库（settings.database_url）；换库或重建库后旧记录自动作废。
模板规范见 docs/content-templates/README.md。
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.content_import import content_sha256, import_document, load_document


def _collect_files(path: Path, pattern: str) -> list[Path]:
    if path.is_file():
        if not fnmatch.fnmatch(path.name, pattern):
            return []
        return [path]
    if not path.is_dir():
        raise FileNotFoundError(f"路径不存在：{path}")
    files = [
        item
        for item in sorted(path.rglob("*.json"))
        if not item.name.startswith("_")
        and fnmatch.fnmatch(item.relative_to(path).as_posix(), pattern)
    ]
    if not files:
        raise FileNotFoundError(f"目录下没有匹配 {pattern} 的 JSON：{path}")
    return files


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_manifest(path: Path | None) -> dict:
    database = settings.database_url
    if path is None or not path.is_file():
        return {"version": 1, "database": database, "files": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("files"), dict):
        data["files"] = {}
    recorded = data.get("database")
    if recorded and recorded != database:
        print(f"manifest 记录的目标库为 {recorded}，当前为 {database}，旧导入记录全部作废")
        data["files"] = {}
    data["database"] = database
    return data


def _save_manifest(path: Path | None, data: dict) -> None:
    if path is None:
        return
    data["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="导入题库/知识库 JSON 模板")
    parser.add_argument("--path", required=True, help="JSON 文件或模板目录（递归查找 *.json）")
    parser.add_argument(
        "--pattern",
        default="*.json",
        help="目录模式下按相对路径过滤，如 math_g*_first_*.json（默认 *.json）",
    )
    parser.add_argument("--overwrite", action="store_true", help="覆盖同章节同题干同题型的题目")
    parser.add_argument("--dry-run", action="store_true", help="只校验并统计，不落库")
    parser.add_argument(
        "--manifest",
        help="导入清单 JSON；记录文件 hash 与结果，相同文件自动跳过",
    )
    args = parser.parse_args()

    root = Path(args.path)
    files = _collect_files(root, args.pattern)
    manifest = _load_manifest(Path(args.manifest) if args.manifest else None)
    session = SessionLocal()
    failed = 0
    try:
        for file in files:
            label = file.name if root.is_file() else file.relative_to(root).as_posix()
            digest = _sha256(file)
            entry = manifest["files"].get(label)
            if (
                not args.dry_run
                and not args.overwrite
                and entry
                and entry.get("status") == "ok"
                and (
                    entry.get("current_file_sha256") == digest
                    or entry.get("sha256") == digest          # 旧版 manifest 兼容
                )
            ):
                print(f"{label}: 已导入且文件未变，跳过（manifest）")
                continue
            try:
                data = load_document(file)
                report = import_document(session, data, overwrite=args.overwrite)
                print(
                    f"{label}: 教材{'新建' if report['textbook_created'] else '已存在'}"
                    f"，章节 +{report['chapters_created']}/~{report['chapters_updated']}"
                    f"，知识点 +{report['knowledge_created']}/~{report['knowledge_updated']}"
                    f"，题目 +{report['questions_created']}"
                    f"，跳过重复 {report['questions_skipped']}"
                )
                if report.get("legacy_file"):
                    print(
                        "    [legacy] 该文件带 `_legacy` 标记（占位章节清理前的旧样章内容）："
                        "重导时按 chapter_aliases.json 处理，不会把旧版数据写回库"
                    )
                if report.get("chapters_discarded") or report.get("questions_discarded"):
                    detail = "、".join(report.get("discarded_detail") or []) or "-"
                    print(
                        f"    已丢弃（旧版数据，不入库）：{data.get('subject')} g{data.get('grade')}"
                        f" · {report.get('questions_discarded', 0)} 题"
                        f" · 章 {report.get('chapters_discarded', 0)}"
                        f" · 知识点 {report.get('knowledge_discarded', 0)}"
                        f" · [{detail}]"
                    )
                manifest["files"][label] = {
                    # 三列语义（2026-11-08 第十一轮整改）：
                    #   imported_sha256      导入当刻的字节 sha，**永不改写**
                    #   current_file_sha256  盘上现值
                    #   imported_content_sha256 导入当刻「剔除元数据键后」的内容哈希
                    # 判定「已入库」用：字节一致 → 未变更；字节不一致但内容哈希一致
                    # → 仅元数据变更（如打 legacy 标记），仍算已入库；否则 → 文件已变更、未重导。
                    "imported_sha256": digest,
                    "current_file_sha256": digest,
                    "imported_content_sha256": content_sha256(data),
                    "status": "ok",
                    "report": report,
                    "imported_at": datetime.now().astimezone().isoformat(
                        timespec="seconds"
                    ),
                }
            except Exception as exc:  # noqa: BLE001 - CLI 逐文件失败不影响其余模板
                session.rollback()
                failed += 1
                manifest["files"][label] = {
                    "imported_sha256": digest,
                    "current_file_sha256": digest,
                    "status": "failed",
                    "error": str(exc),
                }
                print(f"{label}: 导入失败 - {exc}")
                continue
            # 批量导入按文件独立提交：单个文件失败不会回滚已成功的文件
            if args.dry_run:
                session.rollback()
            else:
                session.commit()
        if args.dry_run:
            print("dry-run：已回滚，未写入数据库")
        else:
            _save_manifest(Path(args.manifest) if args.manifest else None, manifest)
    finally:
        session.close()
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
