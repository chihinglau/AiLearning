# -*- coding: utf-8 -*-
"""批量抓取电子课本网各学科目录（单元 + 课文/节），存 baseline/_raw/{subject}[_second].json。

用法：`python _fetch_outlines.py [subject|all] [first|second]`
- first（默认）抓上册与全一册，写 `_raw/{subject}.json`
- second 抓下册与全一册，写 `_raw/{subject}_second.json`

目录位于课本每页侧栏，锚点指向同册页码，单元行形如「第一单元·识字」「第一章·丰富的图形世界」。
只抓目录标题，不下载课文正文与图片。
"""
import json
import re
import sys
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "baseline" / "_raw"
BASE = "http://www.dzkbw.com"

# subject -> (入口页, 目录里必须出现的学科词, 允许年级)
PLAN = {
    "chinese": ("/books/rjb/yuwen/", "语文", range(1, 10)),
    "physics": ("/books/rjb/wuli/", "物理", range(8, 10)),
    "chemistry": ("/books/rjb/huaxue/", "化学", range(9, 10)),
    "biology": ("/books/rjb/shengwu/", "生物", range(7, 9)),
    "history": ("/books/rjb/lishi/", "历史", range(7, 10)),
    "politics": ("/books/rjb/zhengzhi/", "道德与法治", range(1, 10)),
    "geography": ("/books/xjb/dili/", "地理", range(7, 9)),
    "math": ("/books/bsd/shuxue/", "数学", range(1, 9)),
}

GRADE_CN = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"[ \t\u3000]+")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = resp.read()
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "ignore")


def text_of(html: str) -> str:
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.I | re.S)
    return unescape(TAG_RE.sub(" ", html))


def anchors(html: str):
    for m in re.finditer(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.I | re.S):
        yield m.group(1), SPACE_RE.sub(" ", text_of(m.group(2))).strip()


SEMESTER = "first"


def book_list(entry: str, keyword: str, grades):
    html = fetch(BASE + entry)
    out, seen = [], set()
    wanted = ("上册", "全一册") if SEMESTER == "first" else ("下册", "全一册")
    for href, label in anchors(html):
        if keyword not in label:
            continue
        if not any(word in label for word in wanted):
            continue
        if "图册" in label:
            continue
        m = re.search(r"([一二三四五六七八九])年级", label)
        if not m:
            continue
        grade = GRADE_CN[m.group(1)]
        if grade not in grades:
            continue
        url = urllib.parse.urljoin(BASE + entry, href).rstrip("/") + "/"
        slug = url.rstrip("/").split("/")[-1]
        if slug.startswith("ws"):  # 五四制，跳过
            continue
        key = (grade, slug)
        if key in seen:
            continue
        seen.add(key)
        out.append({"grade": grade, "label": label, "url": url, "slug": slug})
    return sorted(out, key=lambda b: b["grade"])


def toc_of(book):
    """扫前若干页，取节点最多的那页：部分册次（如数学 4-6）只有正文页侧栏才列到节。"""
    pat = re.compile(re.escape(book["slug"]) + r"/\d+\.htm$")
    best = []
    for i in range(1, 7):
        try:
            html = fetch(f"{book['url']}{i:03d}.htm")
        except Exception:
            continue
        items, seen = [], set()
        for href, label in anchors(html):
            if not pat.search(href):
                continue
            label = label.replace("**", "").strip()
            if not label or label.startswith("封面") or label in seen:
                continue
            seen.add(label)
            items.append(label)
        if len(items) > len(best):
            best = items
    return best


def main() -> int:
    global SEMESTER
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    if only in ("first", "second"):
        only, SEMESTER = "", only
    elif len(sys.argv) > 2:
        SEMESTER = sys.argv[2]
    if only == "all":
        only = ""
    suffix = "" if SEMESTER == "first" else "_second"
    summary = []
    for subject, (entry, keyword, grades) in PLAN.items():
        if only and subject != only:
            continue
        books = book_list(entry, keyword, grades)
        result = []
        for b in books:
            items = toc_of(b)
            result.append({"grade": b["grade"], "label": b["label"], "url": b["url"], "items": items})
            print(f"  g{b['grade']} {b['label'][:24]} -> {len(items)} 条  {b['url']}")
        (RAW_DIR / f"{subject}{suffix}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        summary.append((subject, len(result), sum(len(r["items"]) for r in result)))
        print(f"[{subject}] {len(result)} 册 / {summary[-1][2]} 条")
    print("\n汇总：")
    for s, n, k in summary:
        print(f"  {s}: {n} 册 / {k} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
