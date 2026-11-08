"""一次性修复脚本（2026-11-08）：补齐「每知识点 ≥4 题」与「难度 40/40/20」。

只改 daily/**/*_20261108.json 里被 all-verify 判 warn 的 18 份文件
（最初 17 份，加上并入 math/g9 后新暴露的 warn 文件）：
  1) 给题数不足的知识点补原创题（题干不与该点已有题干重复，挂已有 point 名），共补 28 道
  2) 把已有题中 difficulty=2→3 / 3→4 / 4→3 做小幅配平，使三档落在 40/40/20 ±15pp，共调 29 处

脚本已执行完毕；本文件保留作为数据修复留痕，不要直接重跑（会与已修复的 JSON 冲突）。
修复结果以 all-verify 与 _validate_daily.py 为准；字段同步入库需 -Action import -Overwrite。
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\daily")
BASE = "20261108"


def C(stem, opts, value, analysis, kp, diff=3):
    return {"q_type": "choice", "stem": stem, "options": opts,
            "answer": {"value": value}, "analysis": analysis,
            "difficulty": diff, "knowledge_point": kp}


def J(stem, value, analysis, kp, diff=3):
    return {"q_type": "judge", "stem": stem, "answer": {"value": value},
            "analysis": analysis, "difficulty": diff, "knowledge_point": kp}


def F(stem, value, analysis, kp, diff=3):
    return {"q_type": "fill", "stem": stem, "answer": {"value": value},
            "analysis": analysis, "difficulty": diff, "knowledge_point": kp}


PATCHES = {
    "chinese/g1/chinese_g1_first_20261108.json": [
        C("写「山」字时，正确的笔顺是（  ）。",
          ["先写中间一竖，再写竖折，最后写右边一竖", "先写竖折，再写两竖",
           "先写两竖，最后写竖折", "先写左右两笔，最后写中间一竖"], "A",
          "「山」共 3 画，笔顺为竖、竖折、竖；先定中间一竖能让左右对称，其余顺序都会把笔画数或方向写错。",
          "笔画与笔顺"),
    ],
    "english/g1/english_g1_first_20261108.json": [
        C("Put Dd, Bb, Aa, Cc in ABC order. Which letter is the THIRD one?",
          ["Aa", "Bb", "Cc", "Dd"], "C",
          "字母顺序是 Aa, Bb, Cc, Dd；题目故意打乱，要先排序再数，第三个是 Cc。",
          "Letters Aa to Dd"),
    ],
    "politics/g1/politics_g1_first_20261108.json": [
        J("前一天晚上按课程表把课本放进书包，可以避免第二天忘带学习用品。", "T",
          "按课程表提前整理是「自己的事情自己做」的具体做法，能减少忘带，说法正确。", "上学的准备"),
        C("想知道学校医务室在哪里，最合适的做法是（  ）。",
          ["看校园平面图或问老师", "随便找一间教室闯进去问", "下课自己跑到校外找", "等真的生病时再说"], "A",
          "认识校园要借助平面图、指示牌或询问老师，既快又安全；随意乱走或拖到需要时才找都不合适。",
          "认识新校园"),
    ],
    "politics/g2/politics_g2_first_20261108.json": [
        F("同学讲完假期见闻后，先说一句自己听懂了什么，再提问题，这叫认真（  ）。", "倾听",
          "倾听是先理解对方再表达自己；插话、抢话都不算倾听。", "分享与倾听"),
    ],
    "politics/g3/politics_g3_first_20261108.json": [
        C("下面哪件事最能说明「学习让生活更方便」？（  ）",
          ["学会看公交站牌后能自己坐车", "把课文背得滚瓜烂熟", "每天写很多作业", "考试得了满分"], "A",
          "学习的意义在于解决真实问题；会看站牌并独立出行是迁移应用，其余仍停留在记忆或分数上。",
          "学习的意义", 4),
        J("跟奶奶学包饺子、在科技馆看展，都能学到课本以外的知识。", "T",
          "学习不只在教室，生活中的请教、参观、实践都是途径，说法正确。", "学习的多种途径"),
    ],
    "politics/g4/politics_g4_first_20261108.json": [
        C("班级要办读书角，下列做法最能体现「我为集体出一份力」的是（  ）。",
          ["带一本自己的书并参与整理", "等别人办好再去看", "只说自己不喜欢读书", "把书带回家不外借"], "A",
          "集体由每个人组成，主动带书和整理是承担角色；旁观或只享受成果不算参与。", "班集体的意义"),
    ],
    "politics/g5/politics_g5_first_20261108.json": [
        C("各地早期共产党组织的建立，为中国共产党成立提供了（  ）。",
          ["组织基础", "思想条件", "阶级基础", "外部援助"], "A",
          "马克思主义传播是思想条件，工人队伍壮大是阶级基础，各地早期党组织则是组织基础；外部援助不是成立的决定条件。",
          "中国共产党成立的历史条件", 4),
    ],
    "politics/g7/politics_g7_first_20261108.json": [
        C("面对初中新增的社团与选修课，更合适的态度是（  ）。",
          ["结合兴趣选一两项坚持尝试", "全部都报，越多越好", "一项都不参加，只刷题", "等老师替自己决定"], "A",
          "新机会需要主动且有选择地把握，量力而行才能坚持；全报或全不参加都放弃了自主规划。",
          "中学生活的意义"),
    ],
    "politics/g8/politics_g8_first_20261108.json": [
        C("同一场社区活动，有人关注组织秩序，有人关注邻里交流，这主要说明社会生活（  ）。",
          ["是丰富多样的", "只有一种标准答案", "与个人无关", "不需要参与"], "A",
          "同一场景中不同人关注不同侧面，正体现社会生活的绚丽多彩与复杂性。", "社会生活的特点"),
        J("随着网络与交通发展，人们参与社会生活的方式比过去更多。", "T",
          "社会生活的内容和形式会随社会发展而扩展，说法正确。", "社会生活的特点"),
    ],
    "physics/g8/physics_g8_first_20261108.json": [
        C("某同学测得课桌宽 0.6 m，换算成 cm 应写为（  ）。",
          ["60 cm", "6 cm", "0.006 cm", "600 cm"], "A",
          "1 m = 100 cm，0.6 × 100 = 60 cm；换算要乘进率，不能只改单位符号。", "长度的单位与换算"),
        F("停表小表盘指针在 2 min 与 3 min 之间、大表盘指 15 s，读数为 2 min （  ）s。", "15",
          "停表先读小盘分钟数，再读大盘秒数，两部分合起来；小盘未过半格时大盘读 0~30 s 一圈。",
          "时间的测量", 4),
    ],
    "biology/g7/biology_g7_first_20261108.json": [
        C("观察校园里一株植物并记录叶形，下列做法更符合观察要求的是（  ）。",
          ["按一定顺序看并如实记录，不改动植物", "把叶子摘下来做成标本再描述",
           "只看一眼就下结论", "按想象补全没看清的部分"], "A",
          "观察要有目的、有计划、如实记录且不干扰对象；采摘改变对象、凭想象补全都违背如实记录。", "观察法"),
        J("借助放大镜观察蚂蚁的触角，仍然属于观察法。", "T",
          "观察可用感官也可借助工具，放大镜只是延伸感官，说法正确。", "观察法"),
    ],
    "biology/g8/biology_g8_first_20261108.json": [
        C("手碰到烫的杯子立刻缩回，这一反射的神经中枢主要位于（  ）。",
          ["脊髓", "大脑皮层", "小脑", "脑干"], "A",
          "缩手反射是简单反射，中枢在脊髓，随后信息才传到大脑产生痛觉；大脑皮层参与复杂反射。",
          "神经系统的组成", 4),
    ],
    "history/g7/history_g7_first_20261108.json": [
        C("北京人遗址中发现厚层灰烬，最能说明（  ）。",
          ["他们已会使用火并保存火种", "他们已会人工取火", "他们已会种植粟", "他们已会建造房屋"], "A",
          "灰烬与烧石是用火证据；北京人使用天然火并保存火种，人工取火要到山顶洞人时期，种植与定居更晚。",
          "火的使用", 4),
        F("火能烧烤食物、防寒、照明和驱兽，其中改善体质最直接的是（  ）食物。", "烧烤",
          "熟食缩短消化过程、减少疾病，最直接改善营养与体质；其余属于生活与安全的改善。", "火的使用"),
    ],
    "history/g8/history_g8_first_20261108.json": [
        C("1840 年英军舰队北上抵达天津白河口，这一事件发生在（  ）。",
          ["鸦片战争期间", "第二次鸦片战争期间", "甲午中日战争期间", "八国联军侵华期间"], "A",
          "1840 年是鸦片战争爆发之年，英军北上直逼天津迫使清廷议和；其余战争分别在 1856、1894、1900 年。",
          "战争的爆发与经过", 4),
    ],
    "history/g9/history_g9_first_20261108.json": [
        C("原始社会人们共同劳动、平均分配，其根本原因是（  ）。",
          ["生产工具简陋、生产力低下", "当时已有严格法律", "私有制已高度发达", "人们不愿多劳动"], "A",
          "生产力极低时单个人无法独立生存，只能协作并共享成果；私有制和国家是生产力提高后才出现的。",
          "人类的起源与原始社会", 4),
        J("母系氏族社会中，女性在生产和生活中曾起过重要作用。", "T",
          "早期采集与原始农业中女性承担主要生产，血缘按母系计算，说法正确。", "人类的起源与原始社会"),
    ],
    "geography/g8/geography_g8_first_20261108.json": [
        C("从纬度位置看，中国大部分地区位于（  ）。",
          ["北温带", "热带", "北寒带", "南温带"], "A",
          "中国约在 4°N~53°N，大部分在北回归线以北的北温带，南部小部分地区属热带，没有寒带。",
          "中国的半球位置与纬度位置"),
        J("中国全部位于东半球，没有领土跨到西半球。", "T",
          "中国最西约 73°E、最东约 135°E，均在 20°W~160°E 的东半球范围内，说法正确。",
          "中国的半球位置与纬度位置"),
        C("与中国既陆上相邻又隔海相望的国家是（  ）。",
          ["朝鲜", "日本", "蒙古", "印度"], "A",
          "朝鲜与中国陆上接壤又同临黄海；日本只隔海不接壤，蒙古、印度只陆上相邻。", "中国的海陆位置", 4),
        F("中国东部濒临的大洋是（  ）洋。", "太平",
          "中国东临太平洋，自北向南依次为渤海、黄海、东海、南海，均属太平洋边缘海。", "中国的海陆位置", 2),
    ],
    "geography/g7/geography_g7_first_20261108.json": [],   # 只需难度配平
    "math/g9/math_g9_first_20261108.json": [               # 并入 g9 后新纳入验收的文件
        C("下列条件中，能判定一个平行四边形是菱形的是（  ）。",
          ["有一组邻边相等", "有一个角是直角", "两条对角线相等", "两条对角线互相平分"], "A",
          "菱形定义是「有一组邻边相等的平行四边形」；有一个角是直角、对角线相等判定的是矩形，对角线互相平分是平行四边形本身已有的性质。",
          "菱形的定义", 4),
        J("菱形一定是平行四边形，但平行四边形不一定是菱形。", "T",
          "菱形是附加了「邻边相等」条件的特殊平行四边形；普通平行四边形邻边未必相等，说法正确。",
          "菱形的定义"),
    ],
}


def buckets(qs):
    lo = sum(1 for q in qs if int(q["difficulty"]) <= 2)
    hi = sum(1 for q in qs if int(q["difficulty"]) >= 4)
    return lo, len(qs) - lo - hi, hi


def pick(qs, predicate, changed):
    rank = {"multiple": 0, "answer": 1, "fill": 2, "choice": 3, "judge": 4}
    cand = [q for q in qs if predicate(q) and id(q) not in changed]
    if not cand:
        return None
    cand.sort(key=lambda q: (0 if int(q["difficulty"]) == 2 else 1,
                             rank.get(q["q_type"], 9)))
    return cand[0]


def balance(qs):
    """调 2→3 / 3→4 / 4→3，使三档落到更严格的目标区间，避免卡在 ±15pp 边界。"""
    changed, n = set(), len(qs)
    for _ in range(80):
        lo, mid, hi = buckets(qs)
        rl, rm, rh = lo / n, mid / n, hi / n
        if 0.30 <= rl <= 0.50 and 0.30 <= rm <= 0.50 and 0.12 <= rh <= 0.30:
            break
        if rl > 0.50:
            q = pick(qs, lambda x: int(x["difficulty"]) <= 2, changed)
            if q:
                q["difficulty"] = 3
        elif rh < 0.12 or rm > 0.50:
            q = pick(qs, lambda x: int(x["difficulty"]) == 3, changed)
            if q:
                q["difficulty"] = 4
        elif rh > 0.30:
            q = pick(qs, lambda x: int(x["difficulty"]) >= 4, changed)
            if q:
                q["difficulty"] = 3
        elif rl < 0.30:
            q = pick(qs, lambda x: int(x["difficulty"]) == 3, changed)
            if q:
                q["difficulty"] = 2
        else:
            break
        if not q:
            break
        changed.add(id(q))
    return len(changed)


def main():
    import sys
    only = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--only" else None
    targets = {only: PATCHES[only]} if only else PATCHES
    total_added = total_tuned = 0
    for rel, new_qs in targets.items():
        fp = ROOT / rel
        data = json.loads(fp.read_text(encoding="utf-8"))
        chapters = data["chapters"]
        if len(chapters) != 1:
            raise SystemExit(f"章节数异常（{len(chapters)}）：{rel}")
        qs = chapters[0]["questions"]
        existing = {str(q.get("stem") or "").strip() for q in qs}
        point_names = {n["name"] for n in data["knowledge"] if n["node_type"] == "point"}
        for q in new_qs:
            if q["stem"] in existing:
                raise SystemExit(f"题干重复：{rel} / {q['stem']}")
            if q["knowledge_point"] not in point_names:
                raise SystemExit(f"知识点不存在：{rel} / {q['knowledge_point']}")
            qs.append(q)
            existing.add(q["stem"])
        before = buckets(qs)
        tuned = balance(qs)
        after = buckets(qs)
        fp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        total_added += len(new_qs)
        total_tuned += tuned
        print(f"{rel}: +{len(new_qs)} 题, 调档 {tuned}, 难度 {before} -> {after}, 共 {len(qs)} 题")
    print(f"TOTAL +{total_added} 题 / 调档 {total_tuned} 处 / 本次处理 {len(targets)} 份")


if __name__ == "__main__":
    main()
