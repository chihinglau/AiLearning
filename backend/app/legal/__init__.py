"""公开发布的法务文档（R-03）：隐私政策与用户协议。

文档正文以 Markdown 存放在本目录，后端按需渲染为 HTML（公网页面）或返回 JSON
（App 内展示）。
版本号与正文分离：版本升高后 App 端会重新征求同意。
"""

from __future__ import annotations

import html
import re
from pathlib import Path

LEGAL_DIR = Path(__file__).resolve().parent

PRIVACY_VERSION = "2026.11.06"
TERMS_VERSION = "2026.11.06"

TITLES = {"privacy": "隐私政策", "terms": "用户协议"}

_FILES = {"privacy": "privacy.md", "terms": "terms.md"}


def doc_names() -> tuple[str, str]:
    return ("privacy", "terms")


def current_version(doc_type: str) -> str:
    return PRIVACY_VERSION if doc_type == "privacy" else TERMS_VERSION


def read_markdown(doc_type: str) -> str:
    path = LEGAL_DIR / _FILES[doc_type]
    return path.read_text(encoding="utf-8")


_UPDATED = re.compile(r"最后更新\*\*：(\d{4}-\d{2}-\d{2})")


def updated_at(doc_type: str) -> str:
    match = _UPDATED.search(read_markdown(doc_type))
    return match.group(1) if match else current_version(doc_type)


def _inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return text


_HEADING = re.compile(r"^(#{1,3})\s+(.*)$")
_HR = re.compile(r"^---+$")


def _render_table(rows: list[str]) -> str:
    cells = []
    for row in rows:
        if re.match(r"^[\s|:-]+$", row):
            continue
        parts = [part.strip() for part in row.strip().strip("|").split("|")]
        cells.append(parts)
    if not cells:
        return ""
    head, *body = cells
    head_html = "".join(f"<th>{_inline(item)}</th>" for item in head)
    body_html = "".join(
        "<tr>" + "".join(f"<td>{_inline(item)}</td>" for item in row) + "</tr>"
        for row in body
    )
    return (
        '<table><thead><tr>' + head_html + "</tr></thead><tbody>"
        + body_html
        + "</tbody></table>"
    )


def render_html(title: str, markdown: str) -> str:
    """轻量 Markdown → HTML（仅覆盖文档实际使用的语法：标题/列表/表格/引用/分隔线）。"""
    out: list[str] = []
    paragraph: list[str] = []
    bullets: list[str] = []
    table: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            joined = "<br/>".join(_inline(line) for line in paragraph)
            out.append(f"<p>{joined}</p>")
            paragraph.clear()

    def flush_bullets() -> None:
        if bullets:
            items = "".join(f"<li>{_inline(item)}</li>" for item in bullets)
            out.append(f"<ul>{items}</ul>")
            bullets.clear()

    def flush_table() -> None:
        if table:
            out.append(_render_table(table))
            table.clear()

    def flush_all() -> None:
        flush_paragraph()
        flush_bullets()
        flush_table()

    for raw in markdown.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if stripped.startswith("|"):
            flush_paragraph()
            flush_bullets()
            table.append(stripped)
            continue
        flush_table()
        if not stripped:
            flush_all()
            continue
        heading = _HEADING.match(stripped)
        if heading:
            flush_all()
            level = len(heading.group(1))
            out.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
            continue
        if _HR.match(stripped):
            flush_all()
            out.append("<hr/>")
            continue
        if stripped.startswith("- ") or stripped.startswith("* "):
            flush_paragraph()
            bullets.append(stripped[2:])
            continue
        if stripped.startswith(">"):
            flush_all()
            quoted = _inline(stripped.lstrip("> "))
            out.append(f"<blockquote>{quoted}</blockquote>")
            continue
        flush_bullets()
        paragraph.append(stripped)

    flush_all()

    body = "\n".join(out)
    safe_title = html.escape(title)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{safe_title} · 深爱学</title>
<style>
body{{margin:0;background:#f7f9fc;color:#1f2937;
font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
line-height:1.75;}}
main{{max-width:820px;margin:0 auto;padding:32px 20px 64px;}}
h1{{font-size:24px;margin:8px 0 16px;}}
h2{{font-size:19px;margin:28px 0 10px;}}
h3{{font-size:16px;margin:20px 0 8px;}}
p,li{{font-size:15px;}}
table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px;
background:#fff;}}
th,td{{border:1px solid #e5e7eb;padding:8px 10px;text-align:left;vertical-align:top;}}
th{{background:#eef4ff;}}
blockquote{{margin:10px 0;padding:8px 12px;background:#eef4ff;
border-left:3px solid #1e6fd9;color:#374151;font-size:14px;}}
hr{{border:none;border-top:1px solid #e5e7eb;margin:24px 0;}}
code{{background:#eef2f7;padding:1px 5px;border-radius:4px;}}
</style>
</head>
<body><main>
{body}
</main></body>
</html>"""
