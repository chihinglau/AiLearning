#!/usr/bin/env python
"""R-08：生成商店素材（应用图标 / 特性图 / 手机截图 / 素材清单）。

用法（需 Pillow；Windows 默认 Python 已内置）：
    python scripts/make-store-assets.py
    python scripts/make-store-assets.py --install-android   # 同步覆盖 Android Launcher 图标

输出 release/store-assets/：
    icon-1024.png、icon-512.png、feature-graphic-1024x500.png
    screenshots/01-home.png … 08-profile.png
    assets.json（尺寸 / 大小 / sha256）

素材要求：全部为虚构示例数据，不含教材封面、学校标识、真实学生姓名或手机号。
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "release" / "store-assets"
SHOT_DIR = OUT_DIR / "screenshots"
ANDROID_RES = ROOT / "app" / "android" / "app" / "src" / "main" / "res"
OHOS_MEDIA = ROOT / "app" / "ohos" / "AppScope" / "resources" / "base" / "media"

W, H = 1080, 1920
PAD = 48

PRIMARY = (30, 111, 217)
PRIMARY_DARK = (16, 74, 160)
PRIMARY_SOFT = (234, 242, 253)
TEXT = (31, 41, 55)
MUTED = (107, 114, 128)
LINE = (229, 231, 235)
BG = (245, 247, 251)
CARD = (255, 255, 255)
SUCCESS = (22, 163, 74)
SUCCESS_SOFT = (220, 245, 228)
WARN = (208, 122, 12)
WARN_SOFT = (253, 238, 220)
WHITE = (255, 255, 255)

FONT_DIR = Path("C:/Windows/Fonts")
FONT_REGULAR = FONT_DIR / "msyh.ttc"
FONT_BOLD = FONT_DIR / "msyhbd.ttc"

_FONTS: dict[tuple[int, bool], object] = {}


def font(size: int, bold: bool = False):
    key = (size, bold)
    if key not in _FONTS:
        candidates = [FONT_BOLD, FONT_REGULAR] if bold else [FONT_REGULAR]
        for path in candidates:
            if path.exists():
                _FONTS[key] = ImageFont.truetype(str(path), size)
                break
        else:  # 非 Windows 环境回退到内置位图字体
            _FONTS[key] = ImageFont.load_default()
    return _FONTS[key]


def text(draw, xy, value, size, fill=TEXT, bold=False, anchor="la"):
    draw.text(xy, value, font=font(size, bold), fill=fill, anchor=anchor)


def text_width(draw, value, size, bold=False):
    return draw.textbbox((0, 0), value, font=font(size, bold))[2]


def gradient(size, start, end, horizontal=True):
    width, height = size
    image = Image.new("RGB", size)
    draw = ImageDraw.Draw(image)
    steps = width if horizontal else height
    for index in range(steps):
        ratio = index / max(steps - 1, 1)
        color = tuple(
            round(start[channel] + (end[channel] - start[channel]) * ratio)
            for channel in range(3)
        )
        if horizontal:
            draw.line([(index, 0), (index, height)], fill=color)
        else:
            draw.line([(0, index), (width, index)], fill=color)
    return image


def rounded(image, radius):
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, image.width - 1, image.height - 1), radius=radius, fill=255
    )
    result = image.convert("RGBA")
    result.putalpha(mask)
    return result


def canvas():
    return Image.new("RGB", (W, H), BG)


def card(draw, box, fill=CARD, radius=28, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def progress(draw, box, ratio, color=PRIMARY):
    x0, y0, x1, y1 = box
    height = y1 - y0
    draw.rounded_rectangle(box, radius=height / 2, fill=LINE)
    filled = max(height, int((x1 - x0) * ratio))
    draw.rounded_rectangle((x0, y0, x0 + filled, y1), radius=height / 2, fill=color)


def pill(draw, box, label, fill=PRIMARY, color=WHITE, size=34, bold=True):
    draw.rounded_rectangle(box, radius=(box[3] - box[1]) / 2, fill=fill)
    text(draw, ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), label, size, color,
         bold=bold, anchor="mm")


def chip(draw, xy, label, active=False, fill_soft=PRIMARY_SOFT, color=PRIMARY):
    width = text_width(draw, label, 28, bold=True) + 48
    box = (xy[0], xy[1], xy[0] + width, xy[1] + 56)
    draw.rounded_rectangle(
        box, radius=28, fill=PRIMARY if active else fill_soft,
        outline=None if active else LINE, width=1,
    )
    text(draw, (xy[0] + 24, xy[1] + 13), label, 28, WHITE if active else color, bold=True)
    return width


def status_bar(draw):
    text(draw, (PAD, 40), "9:41", 32, TEXT, bold=True)
    base = 74
    for index in range(4):
        height = 10 + index * 8
        draw.rounded_rectangle(
            (W - PAD - 150 + index * 12, base - height, W - PAD - 146 + index * 12, base),
            radius=2, fill=TEXT,
        )
    draw.rounded_rectangle((W - PAD - 44, 44, W - PAD - 6, 74), radius=8, outline=TEXT, width=2)
    draw.rounded_rectangle((W - PAD - 39, 48, W - PAD - 16, 70), radius=5, fill=TEXT)


def app_bar(draw, title, subtitle=None):
    text(draw, (PAD, 116), title, 44, TEXT, bold=True)
    if subtitle:
        text(draw, (PAD, 176), subtitle, 28, MUTED)


def banner(draw, has_nav=False):
    label = "示例数据 · 仅用于商店展示"
    text(draw, (W / 2, 1608 if has_nav else 1684), label, 24, (156, 163, 175), anchor="ma")


def check_mark(draw, center, color=WHITE, size=16):
    cx, cy = center
    draw.line([(cx - size, cy), (cx - size * 0.2, cy + size * 0.75)], fill=color, width=5)
    draw.line([(cx - size * 0.2, cy + size * 0.75), (cx + size, cy - size * 0.7)],
              fill=color, width=5)


def bottom_nav(draw, active=0, labels=("学习", "练习", "错题", "我的")):
    draw.rounded_rectangle(
        (PAD, 1700, W - PAD, 1856), radius=36, fill=CARD, outline=LINE, width=1
    )
    step = (W - 2 * PAD) / len(labels)
    for index, label in enumerate(labels):
        center_x = PAD + step * (index + 0.5)
        active_item = index == active
        radius = 12 if active_item else 9
        draw.ellipse(
            (center_x - radius, 1730 - radius, center_x + radius, 1730 + radius),
            fill=PRIMARY if active_item else LINE,
        )
        text(draw, (center_x, 1772), label, 28, PRIMARY if active_item else MUTED,
             bold=active_item, anchor="ma")


def tile_icon(draw, xy, glyph, color):
    draw.rounded_rectangle((xy[0], xy[1], xy[0] + 72, xy[1] + 72), radius=18, fill=color)
    text(draw, (xy[0] + 36, xy[1] + 34), glyph, 30, WHITE, bold=True, anchor="mm")


def toggle(draw, xy, on=True):
    x0, y0 = xy
    width, height = 108, 60
    draw.rounded_rectangle(
        (x0, y0, x0 + width, y0 + height), radius=height / 2,
        fill=PRIMARY if on else LINE,
    )
    knob = 48
    knob_x = x0 + width - knob - 6 if on else x0 + 6
    draw.ellipse((knob_x, y0 + 6, knob_x + knob, y0 + height - 6), fill=WHITE)


def screen_home():
    image = canvas()
    draw = ImageDraw.Draw(image)
    status_bar(draw)
    text(draw, (PAD, 132), "晚上好，小深", 52, TEXT, bold=True)
    text(draw, (PAD, 200), "今天已完成 2 个练习，继续保持", 30, MUTED)
    draw.ellipse((W - PAD - 96, 140, W - PAD - 16, 220), fill=PRIMARY_SOFT)
    text(draw, (W - PAD - 56, 180), "深", 32, PRIMARY, bold=True, anchor="mm")

    card(draw, (PAD, 284, W - PAD, 512))
    text(draw, (PAD + 36, 316), "今日计划", 34, TEXT, bold=True)
    text(draw, (W - PAD - 36, 318), "2 / 3", 30, PRIMARY, bold=True, anchor="ra")
    progress(draw, (PAD + 36, 388, W - PAD - 36, 412), 0.66)
    text(draw, (PAD + 36, 438), "再完成 1 个练习即可达成今日目标", 26, MUTED)

    card(draw, (PAD, 540, W - PAD, 800))
    text(draw, (PAD + 36, 568), "当前教材", 26, MUTED)
    text(draw, (PAD + 36, 608), "数学 · 三年级上册", 44, TEXT, bold=True)
    text(draw, (PAD + 36, 676), "第 4 单元 万以内的加减法", 30, MUTED)
    pill(draw, (PAD + 36, 722, W - PAD - 36, 782), "继续学习", size=30)

    text(draw, (PAD, 838), "快捷入口", 34, TEXT, bold=True)
    items = [
        ("错", PRIMARY, "错题本", "24 题待复习"),
        ("报", (14, 138, 125), "学情报告", "本周正确率 82%"),
        ("测", (180, 118, 12), "单元测", "3 套可用"),
        ("家", (109, 68, 196), "家长中心", "时长与青少年模式"),
    ]
    tile_width = (W - 2 * PAD - 24) / 2
    for index, (glyph, color, title, subtitle) in enumerate(items):
        column, row = index % 2, index // 2
        x0 = PAD + column * (tile_width + 24)
        y0 = 892 + row * 264
        card(draw, (x0, y0, x0 + tile_width, y0 + 240))
        tile_icon(draw, (x0 + 32, y0 + 32), glyph, color)
        text(draw, (x0 + 32, y0 + 128), title, 34, TEXT, bold=True)
        text(draw, (x0 + 32, y0 + 178), subtitle, 24, MUTED)

    card(draw, (PAD, 1440, W - PAD, 1580), fill=PRIMARY_SOFT)
    text(draw, (PAD + 32, 1470), "小提示", 28, PRIMARY, bold=True)
    text(draw, (PAD + 32, 1514), "错题会在第 1 / 3 / 7 天自动安排复习", 26, TEXT)

    banner(draw, has_nav=True)
    bottom_nav(draw, active=0)
    return image


def screen_knowledge():
    image = canvas()
    draw = ImageDraw.Draw(image)
    status_bar(draw)
    app_bar(draw, "三年级 · 数学", "第 4 单元 万以内的加减法")

    card(draw, (PAD, 248, W - PAD, 428))
    text(draw, (PAD + 36, 280), "单元掌握度", 28, MUTED)
    text(draw, (PAD + 36, 324), "76%", 56, PRIMARY, bold=True)
    text(draw, (W - PAD - 36, 340), "较上周 +8%", 28, SUCCESS, bold=True, anchor="ra")
    progress(draw, (PAD + 36, 396, W - PAD - 36, 412), 0.76)

    text(draw, (PAD, 468), "知识点分层", 34, TEXT, bold=True)
    rows = [
        ("口算两位数加法", 0.92, "已掌握", SUCCESS, SUCCESS_SOFT),
        ("三位数进位加法", 0.76, "巩固中", PRIMARY, PRIMARY_SOFT),
        ("三位数退位减法", 0.58, "待加强", WARN, WARN_SOFT),
    ]
    for index, (title, ratio, label, color, soft) in enumerate(rows):
        y0 = 524 + index * 196
        card(draw, (PAD, y0, W - PAD, y0 + 172))
        text(draw, (PAD + 32, y0 + 28), title, 34, TEXT, bold=True)
        tag_width = text_width(draw, label, 24, bold=True) + 32
        draw.rounded_rectangle(
            (W - PAD - 32 - tag_width, y0 + 24, W - PAD - 32, y0 + 72),
            radius=24, fill=soft,
        )
        text(draw, (W - PAD - 32 - tag_width / 2, y0 + 34), label, 24, color,
             bold=True, anchor="ma")
        progress(draw, (PAD + 32, y0 + 106, W - PAD - 118, y0 + 128), ratio, color)
        text(draw, (W - PAD - 32, y0 + 100), f"{round(ratio * 100)}%", 28, color,
             bold=True, anchor="ra")

    text(draw, (PAD, 1140), "本单元练习", 34, TEXT, bold=True)
    card(draw, (PAD, 1196, W - PAD, 1426))
    text(draw, (PAD + 32, 1224), "随堂练 · 12 题", 34, TEXT, bold=True)
    text(draw, (PAD + 32, 1278), "覆盖 6 个知识点 · 约 10 分钟", 26, MUTED)
    pill(draw, (PAD + 32, 1332, PAD + 312, 1392), "去练习", size=28)
    pill(draw, (PAD + 332, 1332, W - PAD - 32, 1392), "单元测", fill=PRIMARY_SOFT,
         color=PRIMARY, size=28)

    card(draw, (PAD, 1466, W - PAD, 1600), fill=PRIMARY_SOFT)
    text(draw, (PAD + 32, 1494), "小提示", 28, PRIMARY, bold=True)
    text(draw, (PAD + 32, 1538), "优先巩固「待加强」知识点，效率更高", 26, TEXT)

    banner(draw)
    return image


def screen_question():
    image = canvas()
    draw = ImageDraw.Draw(image)
    status_bar(draw)
    app_bar(draw, "随堂练", "第 3 / 10 题 · 万以内的加减法")
    progress(draw, (PAD, 246, W - PAD, 266), 0.3)

    card(draw, (PAD, 304, W - PAD, 604))
    text(draw, (PAD + 36, 336), "选择题", 26, MUTED)
    text(draw, (PAD + 36, 384), "计算：356 + 478 = ?", 46, TEXT, bold=True)
    text(draw, (PAD + 36, 480), "请选择正确的结果", 28, MUTED)
    text(draw, (PAD + 36, 540), "提示：注意个位与十位的进位", 26, PRIMARY)

    options = [("A", "824"), ("B", "834"), ("C", "734"), ("D", "724")]
    for index, (key, value) in enumerate(options):
        y0 = 660 + index * 150
        selected = key == "B"
        card(
            draw, (PAD, y0, W - PAD, y0 + 120),
            fill=PRIMARY_SOFT if selected else CARD,
            outline=PRIMARY if selected else LINE,
            width=3 if selected else 1,
        )
        draw.ellipse((PAD + 32, y0 + 32, PAD + 88, y0 + 88),
                     fill=PRIMARY if selected else LINE)
        text(draw, (PAD + 60, y0 + 60), key, 30, WHITE if selected else MUTED,
             bold=True, anchor="mm")
        text(draw, (PAD + 116, y0 + 42), value, 38, TEXT, bold=selected)
        if selected:
            draw.ellipse((W - PAD - 92, y0 + 34, W - PAD - 40, y0 + 86), fill=SUCCESS)
            check_mark(draw, (W - PAD - 66, y0 + 60))

    card(draw, (PAD, 1268, W - PAD, 1408))
    text(draw, (PAD + 32, 1292), "本题知识点", 26, MUTED)
    text(draw, (PAD + 32, 1334), "三位数进位加法 · 难度 基础", 32, TEXT, bold=True)

    pill(draw, (PAD, 1500, W - PAD, 1606), "提交答案", size=36)
    text(draw, (W / 2, 1630), "答错将自动加入错题本", 26, MUTED, anchor="ma")
    banner(draw)
    return image


def screen_practice():
    image = canvas()
    draw = ImageDraw.Draw(image)
    status_bar(draw)
    app_bar(draw, "练习预览", "第 4 单元 · 万以内的加减法")

    card(draw, (PAD, 248, W - PAD, 470))
    text(draw, (PAD + 36, 280), "本单元随堂练", 44, TEXT, bold=True)
    text(draw, (PAD + 36, 348), "按知识点分层出题，难度适中", 28, MUTED)
    pill(draw, (PAD + 36, 396, PAD + 250, 444), "推荐", size=26)

    stats = [("12", "道题"), ("6", "个知识点"), ("10", "分钟")]
    step = (W - 2 * PAD) / 3
    for index, (value, label) in enumerate(stats):
        center_x = PAD + step * (index + 0.5)
        card(draw, (center_x - step / 2 + 12, 502, center_x + step / 2 - 12, 662))
        text(draw, (center_x, 522), value, 48, PRIMARY, bold=True, anchor="ma")
        text(draw, (center_x, 600), label, 26, MUTED, anchor="ma")

    text(draw, (PAD, 712), "知识点覆盖", 34, TEXT, bold=True)
    chips = ["两位数加法", "三位数进位", "退位减法", "估算", "应用题", "验算"]
    cursor_x, cursor_y = PAD, 766
    for label in chips:
        width = text_width(draw, label, 28, bold=True) + 44
        if cursor_x + width > W - PAD:
            cursor_x, cursor_y = PAD, cursor_y + 72
        chip(draw, (cursor_x, cursor_y), label)
        cursor_x += width + 20

    text(draw, (PAD, 1000), "难度分布", 34, TEXT, bold=True)
    levels = [("基础", 0.5, PRIMARY), ("进阶", 0.35, (14, 138, 125)), ("挑战", 0.15, WARN)]
    for index, (label, ratio, color) in enumerate(levels):
        y0 = 1060 + index * 100
        text(draw, (PAD, y0 + 8), label, 28, MUTED)
        progress(draw, (PAD + 140, y0, W - PAD - 130, y0 + 26), ratio, color)
        text(draw, (W - PAD, y0 - 4), f"{round(ratio * 100)}%", 28, color,
             bold=True, anchor="ra")

    card(draw, (PAD, 1310, W - PAD, 1442), fill=PRIMARY_SOFT)
    text(draw, (PAD + 32, 1336), "练习说明", 26, PRIMARY, bold=True)
    text(draw, (PAD + 32, 1378), "答错自动加入错题本，按 1 / 3 / 7 天安排复习", 26, TEXT)

    pill(draw, (PAD, 1500, W - PAD, 1606), "开始练习", size=36)
    text(draw, (W / 2, 1630), "中途退出会保留做题进度", 26, MUTED, anchor="ma")
    banner(draw)
    return image


def screen_wrongbook():
    image = canvas()
    draw = ImageDraw.Draw(image)
    status_bar(draw)
    app_bar(draw, "错题本", "共 24 题待复习 · 今天 8 题")

    filters = ["全部", "计算", "应用题", "几何"]
    cursor_x = PAD
    for index, label in enumerate(filters):
        cursor_x += chip(draw, (cursor_x, 248), label, active=index == 0) + 20

    items = [
        ("计算 · 三年级", "478 - 259 = ?", "我的答案 229 · 正确答案 219",
         "错因：退位遗漏", "复习计划：今天 · 明天 · 第 7 天"),
        ("应用题 · 三年级", "图书角有 356 本书，借出 178 本，还剩多少本？",
         "我的答案 188 本 · 正确答案 178 本", "错因：多退了一位",
         "复习计划：明天 · 第 3 天"),
        ("计算 · 三年级", "608 - 349 = ?", "我的答案 269 · 正确答案 259",
         "错因：连续退位", "复习计划：今天 · 第 3 天"),
    ]
    for index, (tag, stem, compare, reason, plan) in enumerate(items):
        y0 = 340 + index * 320
        card(draw, (PAD, y0, W - PAD, y0 + 292))
        text(draw, (PAD + 32, y0 + 24), tag, 24, MUTED)
        text(draw, (PAD + 32, y0 + 66), stem, 34, TEXT, bold=True)
        text(draw, (PAD + 32, y0 + 120), compare, 26, MUTED)
        tag_width = text_width(draw, reason, 24, bold=True) + 32
        draw.rounded_rectangle(
            (PAD + 32, y0 + 166, PAD + 32 + tag_width, y0 + 214), radius=24, fill=WARN_SOFT
        )
        text(draw, (PAD + 48, y0 + 176), reason, 24, WARN, bold=True)
        text(draw, (PAD + 32, y0 + 238), plan, 24, PRIMARY)

    banner(draw, has_nav=True)
    bottom_nav(draw, active=2)
    return image


def screen_report():
    image = canvas()
    draw = ImageDraw.Draw(image)
    status_bar(draw)
    app_bar(draw, "学情报告", "本周 · 11 月 2 日 - 11 月 8 日")

    ring_box = (W / 2 - 118, 262, W / 2 + 118, 498)
    draw.ellipse((ring_box[0] - 30, ring_box[1] - 30, ring_box[2] + 30, ring_box[3] + 30),
                 outline=LINE, width=22)
    draw.arc((ring_box[0] - 30, ring_box[1] - 30, ring_box[2] + 30, ring_box[3] + 30),
             start=-90, end=-90 + 295, fill=PRIMARY, width=22)
    text(draw, (W / 2, 358), "82%", 72, PRIMARY, bold=True, anchor="mm")
    text(draw, (W / 2, 424), "掌握度", 26, MUTED, anchor="mm")

    stats = [("126 题", "本周练习"), ("82%", "正确率")]
    card_width = (W - 2 * PAD - 24) / 2
    for index, (value, label) in enumerate(stats):
        x0 = PAD + index * (card_width + 24)
        card(draw, (x0, 556, x0 + card_width, 704))
        text(draw, (x0 + 32, 584), value, 38, TEXT, bold=True)
        text(draw, (x0 + 32, 646), label, 26, MUTED)

    text(draw, (PAD, 756), "薄弱知识点", 34, TEXT, bold=True)
    weak = [("三位数退位减法", 0.58, WARN), ("连续进位加法", 0.64, WARN),
            ("应用题单位", 0.71, PRIMARY)]
    for index, (label, ratio, color) in enumerate(weak):
        y0 = 812 + index * 108
        text(draw, (PAD, y0), label, 28, TEXT)
        progress(draw, (PAD + 40, y0 + 48, W - PAD - 110, y0 + 70), ratio, color)
        text(draw, (W - PAD, y0 + 40), f"{round(ratio * 100)}%", 26, color,
             bold=True, anchor="ra")

    text(draw, (PAD, 1164), "近 7 天练习量", 34, TEXT, bold=True)
    card(draw, (PAD, 1220, W - PAD, 1500))
    heights = [52, 78, 44, 96, 70, 112, 84]
    labels = ["一", "二", "三", "四", "五", "六", "日"]
    slot = (W - 2 * PAD - 64) / 7
    for index, (height, label) in enumerate(zip(heights, labels)):
        center_x = PAD + 32 + slot * (index + 0.5)
        draw.rounded_rectangle(
            (center_x - 18, 1450 - height * 1.6, center_x + 18, 1450),
            radius=12, fill=PRIMARY if index < 5 else (147, 197, 253),
        )
        text(draw, (center_x, 1462), label, 24, MUTED, anchor="ma")

    banner(draw)
    return image


def screen_parent():
    image = canvas()
    draw = ImageDraw.Draw(image)
    status_bar(draw)
    app_bar(draw, "家长中心", "陪伴与时长管理")

    card(draw, (PAD, 248, W - PAD, 452))
    draw.ellipse((PAD + 32, 280, PAD + 132, 380), fill=PRIMARY_SOFT)
    text(draw, (PAD + 82, 330), "深", 40, PRIMARY, bold=True, anchor="mm")
    text(draw, (PAD + 152, 292), "小深 · 三年级", 40, TEXT, bold=True)
    text(draw, (PAD + 152, 354), "监护人：示例家长 · 已确认", 26, MUTED)
    draw.rounded_rectangle((W - PAD - 196, 288, W - PAD - 32, 340), radius=26,
                           fill=SUCCESS_SOFT)
    text(draw, (W - PAD - 114, 304), "已绑定", 24, SUCCESS, bold=True, anchor="ma")

    rows = [
        ("每日使用时长", "40 分钟", "达到上限后需监护人验证", True, PRIMARY),
        ("休息时段", "22:00 - 06:00", "夜间自动锁定学习入口", True, PRIMARY),
        ("青少年模式", "已开启", "关闭需监护人验证", True, PRIMARY),
    ]
    for index, (title, value, note, on, color) in enumerate(rows):
        y0 = 484 + index * 292
        card(draw, (PAD, y0, W - PAD, y0 + 264))
        text(draw, (PAD + 32, y0 + 32), title, 36, TEXT, bold=True)
        text(draw, (PAD + 32, y0 + 92), value, 40, color, bold=True)
        text(draw, (PAD + 32, y0 + 156), note, 26, MUTED)
        toggle(draw, (W - PAD - 140, y0 + 44), on=on)

    text(draw, (PAD, 1384), "绑定与解除均需双方确认，解除后不再读取孩子学情。", 26, MUTED)
    text(draw, (PAD, 1424), "每日时长按中国时区统计，可在账号与安全中调整。", 26, MUTED)

    banner(draw)
    return image


def screen_profile():
    image = canvas()
    draw = ImageDraw.Draw(image)
    status_bar(draw)
    app_bar(draw, "我的")

    card(draw, (PAD, 232, W - PAD, 428))
    draw.ellipse((PAD + 36, 270, PAD + 156, 390), fill=PRIMARY)
    text(draw, (PAD + 96, 330), "深", 44, WHITE, bold=True, anchor="mm")
    text(draw, (PAD + 184, 284), "小深", 42, TEXT, bold=True)
    text(draw, (PAD + 184, 342), "三年级 · 学生（示例账号）", 26, MUTED)
    text(draw, (W - PAD - 36, 312), ">", 34, MUTED, anchor="ra")

    entries = [
        ("隐", PRIMARY, "隐私政策", "查看个人信息处理说明"),
        ("协", (14, 138, 125), "用户协议", "了解服务条款与免责声明"),
        ("举", (180, 118, 12), "内容举报", "24 小时内核实处理"),
        ("安", (109, 68, 196), "账号与安全", "注销账号 · 数据导出"),
        ("关", (71, 85, 105), "关于深爱学", "版本 1.0.0 · 备案信息"),
    ]
    card(draw, (PAD, 468, W - PAD, 468 + 120 * len(entries) + 8))
    for index, (glyph, color, title, subtitle) in enumerate(entries):
        y0 = 476 + index * 120
        tile_icon(draw, (PAD + 28, y0 + 24), glyph, color)
        text(draw, (PAD + 120, y0 + 26), title, 32, TEXT, bold=True)
        text(draw, (PAD + 120, y0 + 72), subtitle, 24, MUTED)
        text(draw, (W - PAD - 28, y0 + 44), ">", 30, (209, 213, 219), anchor="ra")
        if index < len(entries) - 1:
            draw.line((PAD + 120, y0 + 118, W - PAD - 28, y0 + 118), fill=LINE)

    text(draw, (W / 2, 1130), "深爱学 1.0.0", 26, MUTED, anchor="ma")
    text(draw, (W / 2, 1172), "内容仅供学习参考，与教材出版方无关", 24, MUTED, anchor="ma")

    banner(draw, has_nav=True)
    bottom_nav(draw, active=3)
    return image


def make_icon(size):
    image = gradient((size, size), (46, 137, 237), (16, 74, 160), horizontal=False)
    draw = ImageDraw.Draw(image)
    halo = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    halo_draw = ImageDraw.Draw(halo)
    halo_draw.ellipse(
        (-size * 0.15, -size * 0.4, size * 0.95, size * 0.55),
        fill=(255, 255, 255, 26),
    )
    image = Image.alpha_composite(image.convert("RGBA"), halo)
    draw = ImageDraw.Draw(image)
    glyph = "深"
    text(draw, (size / 2, size * 0.44), glyph, int(size * 0.40), WHITE, bold=True,
         anchor="mm")
    line_y = int(size * 0.66)
    line_width = int(size * 0.30)
    draw.rounded_rectangle(
        (size / 2 - line_width / 2, line_y, size / 2 + line_width / 2, line_y + size * 0.012),
        radius=size * 0.006, fill=(255, 255, 255, 220),
    )
    text(draw, (size / 2, size * 0.74), "爱学", int(size * 0.11), WHITE, bold=False,
         anchor="mm")
    return image.convert("RGB")


def make_feature_graphic():
    width, height = 1024, 500
    image = gradient((width, height), (30, 111, 217), (52, 146, 240))
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.ellipse((-160, -240, 300, 220), fill=(255, 255, 255, 22))
    overlay_draw.ellipse((760, 250, 1140, 630), fill=(255, 255, 255, 16))
    image = Image.alpha_composite(image.convert("RGBA"), overlay)

    icon = rounded(make_icon(300), 64)
    image.alpha_composite(icon, (86, 100))
    draw = ImageDraw.Draw(image)
    text(draw, (430, 138), "深爱学", 92, WHITE, bold=True)
    text(draw, (428, 262), "教材同步练习 · 错题回顾 · 学情报告", 34, WHITE)
    text(draw, (428, 318), "家长可设置时长与青少年模式", 30, (222, 235, 251))
    text(draw, (428, 374), "内容仅供学习参考，与教材出版方无关", 26, (200, 221, 246))
    return image.convert("RGB")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save(image, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG", optimize=True)
    return path


def install_android_icons(icon):
    targets = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }
    for folder, size in targets.items():
        destination = ANDROID_RES / folder / "ic_launcher.png"
        icon.resize((size, size), Image.LANCZOS).save(destination, "PNG", optimize=True)


def main():
    parser = argparse.ArgumentParser(description="生成商店素材")
    parser.add_argument("--install-android", action="store_true",
                        help="同步覆盖 Android Launcher 图标（mipmap-mdpi~xxxhdpi）")
    parser.add_argument("--install-ohos", action="store_true",
                        help="同步覆盖鸿蒙 AppScope 图标（114×114）")
    args = parser.parse_args()

    shots = [
        ("01-home.png", screen_home),
        ("02-knowledge.png", screen_knowledge),
        ("03-question.png", screen_question),
        ("04-practice.png", screen_practice),
        ("05-wrongbook.png", screen_wrongbook),
        ("06-report.png", screen_report),
        ("07-parent.png", screen_parent),
        ("08-profile.png", screen_profile),
    ]

    icon_large = make_icon(1024)
    outputs = [
        save(icon_large, OUT_DIR / "icon-1024.png"),
        save(icon_large.resize((512, 512), Image.LANCZOS), OUT_DIR / "icon-512.png"),
        save(icon_large.resize((216, 216), Image.LANCZOS), OUT_DIR / "icon-216.png"),
        save(make_feature_graphic(), OUT_DIR / "feature-graphic-1024x500.png"),
    ]
    for name, builder in shots:
        outputs.append(save(builder(), SHOT_DIR / name))

    if args.install_android:
        install_android_icons(icon_large)
    if args.install_ohos:
        icon_large.resize((114, 114), Image.LANCZOS).save(
            OHOS_MEDIA / "app_icon.png", "PNG", optimize=True
        )

    manifest = {
        "task": "R-08",
        "notes": "全部为虚构示例数据；不含教材封面、学校标识、真实学生信息",
        "assets": [
            {
                "path": str(path.relative_to(OUT_DIR)).replace("\\", "/"),
                "width": Image.open(path).width,
                "height": Image.open(path).height,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in outputs
        ],
    }
    (OUT_DIR / "assets.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    for item in manifest["assets"]:
        print(f"{item['path']:<34} {item['width']}x{item['height']}  {item['bytes'] / 1024:.1f} KB")
    print(f"\n共 {len(manifest['assets'])} 个素材，输出目录：{OUT_DIR}")


if __name__ == "__main__":
    main()
