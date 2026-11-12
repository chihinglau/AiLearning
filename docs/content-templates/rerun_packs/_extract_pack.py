# -*- coding: utf-8 -*-
"""把子代理输出（tool-results/*.txt）里的 Python 草案提取成内容包文件。

子代理是只读的，不能写工作区文件；它把完整草案输出为 ```python 代码块，
由本脚本提取落盘，避免把长文本读回主会话上下文。

章数多的册一次输出会被截断，故支持「分片合并」：mapping 的值可以是
路径数组，脚本按顺序提取每个文件里最长的 python 代码块并拼接成一个 pack。

用法：
    python _extract_pack.py <tool-result.txt> <target_pack_name>
    python _extract_pack.py --batch <mapping.json>
mapping.json:
    {"politics_g3": "C:/.../a.txt"}
或（分片）：
    {"math_g4": ["C:/.../partA.txt", "C:/.../partB.txt"]}
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def grab(src: Path) -> str | None:
    text = src.read_text(encoding="utf-8", errors="replace")
    blocks = re.findall(r"```python\s*\n(.*?)\n```", text, re.S)
    blocks += re.findall(r"```py\s*\n(.*?)\n```", text, re.S)
    if not blocks:
        print(f"[失败] {src.name} 里没有 python 代码块")
        return None
    code = max(blocks, key=len).strip()
    if "PACK" not in code or "chapters" not in code:
        print(f"[失败] {src.name} 最长代码块不像内容包（缺 PACK/chapters）")
        return None
    return code


def extract(src: Path, dst: Path) -> int:
    code = grab(src)
    if not code:
        return 0
    dst.write_text(code + "\n", encoding="utf-8")
    print(f"[提取] {dst.name} <- {src.name}（{len(code)} 字符）")
    return len(code)


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "--batch":
        mapping = json.loads(Path(args[1]).read_text(encoding="utf-8"))
        total = 0
        for name, src in mapping.items():
            sources = src if isinstance(src, list) else [src]
            parts = [grab(Path(s)) for s in sources]
            if any(p is None for p in parts):
                print(f"[失败] {name} 有分片无有效代码块，跳过该册")
                continue
            code = "\n\n".join(parts)
            (HERE / f"{name}.py").write_text(code + "\n", encoding="utf-8")
            print(f"[提取] {name}.py <- {len(sources)} 段（{len(code)} 字符）")
            total += len(code)
        print(f"合计提取 {len(mapping)} 册，字符 {total}")
        return 0
    if len(args) != 2:
        print("用法：python _extract_pack.py <tool-result.txt> <pack_name>")
        return 1
    return 0 if extract(Path(args[0]), HERE / f"{args[1]}.py") else 1


if __name__ == "__main__":
    raise SystemExit(main())
