"""三处 `content_sha256` 实现必须一致（manifest「已入库·仅元数据变更」判定的前提）。

同一份文档要算出同一个内容哈希，取决于三处实现完全一致：
  1. backend/app/services/content_import.py::content_sha256（写入侧，权威）
  2. docs/content-templates/_validate_daily.py::_content_sha256（校验侧）
  3. export 包里的 migrate_manifest_3col.py / mark_legacy_json.py / db_ops.py

任何一处漂移，manifest 的「仅元数据变更 vs 内容变更」判定就会误判——
这正是第十一轮评审 A 项要根治的问题，所以用测试锁住。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

from app.services.content_import import METADATA_KEYS, content_sha256

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "docs/content-templates/_validate_daily.py"
EXPORT_DIR = ROOT / "docs/content-templates/exports/automation_20261108_codebuddy"

DOC = {
    "subject": "math",
    "grade": 1,
    "version": "北师大版",
    "semester": "first",
    "knowledge": [{"node_type": "section", "name": "第一单元"}],
    "chapters": [{"name": "第一单元", "order_index": 1, "questions": []}],
}


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_metadata_keys_do_not_change_content_hash():
    marked = dict(DOC)
    marked["_legacy"] = True
    marked["_legacy_note"] = "占位章节清理前的旧样章内容"
    assert content_sha256(marked) == content_sha256(DOC)


def test_content_change_changes_hash():
    changed = json.loads(json.dumps(DOC))
    changed["chapters"][0]["name"] = "第二单元"
    assert content_sha256(changed) != content_sha256(DOC)


def test_validator_implementation_matches():
    validator = _load_module(VALIDATOR, "_validate_daily_under_test")
    assert validator._METADATA_KEYS == METADATA_KEYS
    assert validator._content_sha256(DOC) == content_sha256(DOC)
    marked = dict(DOC, _legacy=True, _legacy_note="x")
    assert validator._content_sha256(marked) == content_sha256(DOC)


def test_migration_and_ops_scripts_match():
    for name in ("migrate_manifest_3col.py", "mark_legacy_json.py", "db_ops.py"):
        path = EXPORT_DIR / name
        assert path.is_file(), f"缺少脚本：{path}"
        mod = _load_module(path, f"_mod_{path.stem}")
        fn = getattr(mod, "content_sha256", None) or getattr(mod, "_content_sha256", None)
        assert fn is not None, f"{name} 里找不到 content_sha256 实现"
        assert fn(DOC) == content_sha256(DOC), f"{name} 的内容哈希与权威实现不一致"


def test_validator_three_states(tmp_path: Path):
    """端到端：三态判定（unchanged / meta_only / changed）。"""
    label = "math/g1/math_g1_first_20261108.json"
    manifest = {"files": {label: {"status": "ok", "imported_sha256": "",
                                  "current_file_sha256": "",
                                  "imported_content_sha256": content_sha256(DOC)}}}
    target = tmp_path / "math" / "g1" / "math_g1_first_20261108.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    # 「导入当刻」的字节 = 初始 DOC 的字节；之后各态都不再改这一列
    imported_raw = json.dumps(DOC, ensure_ascii=False, indent=2).encode("utf-8")
    manifest["files"][label]["imported_sha256"] = hashlib.sha256(imported_raw).hexdigest()
    validator = _load_module(VALIDATOR, "_validate_daily_states")

    def state(doc: dict) -> str:
        raw = json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8")
        target.write_bytes(raw)
        entry = manifest["files"][label]
        entry["current_file_sha256"] = hashlib.sha256(raw).hexdigest()
        return validator._manifest_import_state(
            target, raw, json.loads(raw.decode("utf-8")), manifest["files"])

    # 1) 字节与内容都一致 → unchanged
    assert state(DOC) == "unchanged"
    # 2) 只加元数据键 → 字节变、内容哈希不变 → meta_only
    marked = dict(DOC, _legacy=True, _legacy_note="旧样章内容")
    assert state(marked) == "meta_only"
    # 3) 改内容键 → 内容哈希变 → changed
    changed = json.loads(json.dumps(DOC))
    changed["chapters"][0]["name"] = "第二单元"
    assert state(changed) == "changed"