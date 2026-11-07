"""导入教研题库 / 知识库模板。

用法（在 backend 目录执行）：
    .venv\\Scripts\\python.exe -m scripts.import_content --path ..\\docs\\content-templates\\math.json
    .venv\\Scripts\\python.exe -m scripts.import_content --path ..\\docs\\content-templates --dry-run
    .venv\\Scripts\\python.exe -m scripts.import_content --path ..\\docs\\content-templates ^
        --pattern "math_g*_first_*.json" --manifest ..\\docs\\content-templates\\_import-manifest.json

模板规范见 docs/content-templates/README.md。
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
from datetime import datetime
from pathlib import Path

from app.db.session import SessionLocal
from app.services.content_import import import_document, load_document


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
    if path is None or not path.is_file():
        return {"version": 1, "files": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("files"), dict):
        data["files"] = {}
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
                and entry.get("sha256") == digest
                and entry.get("status") == "ok"
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
                manifest["files"][label] = {
                    "sha256": digest,
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
                    "sha256": digest,
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
