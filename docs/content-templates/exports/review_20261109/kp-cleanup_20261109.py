"""知识点层清理（2026-11-09 复核轮）
A 删除 9 个「样章·…」占位分组及其 18 个子节点（0 题、0 引用）
B 5 个「综合实践项目 / 探究与实践」section 无子节点但自身挂题 → 改为 point（层级规范化）
C 修 2 个含 '?' 的知识点名（任务二?新闻采访 / 任务三?新闻写作）
D 为 g1/g8 中 prerequisites 为空的 point 补「同组前序点」ID
用法：python kp_cleanup.py           # 只打印方案
      python kp_cleanup.py --apply   # 备份后执行
"""
import sqlite3, sys, shutil, json, datetime, pathlib

DB = r'D:\ai\prj\trae\HuaWei\AiLearning\backend\ailearning_dev.db'
APPLY = '--apply' in sys.argv

con = sqlite3.connect(DB)
cur = con.cursor()

def rows(sql, *a):
    return cur.execute(sql, a).fetchall()

# ---------- A ----------
sample_secs = rows("""select id,subject,grade,name from knowledge_points
                      where instr(name,'样章')>0 and node_type='section' and (grade=1 or grade=8)
                      order by grade,subject""")
sec_ids = [r[0] for r in sample_secs]
kids = rows(f"""select id,name,parent_id from knowledge_points
                where parent_id in ({','.join(str(i) for i in sec_ids)})""") if sec_ids else []
kid_ids = [r[0] for r in kids]
print(f'A 样章分组 {len(sec_ids)} 个 / 子节点 {len(kid_ids)} 个；子节点挂题数',
      cur.execute(f"select count(*) from questions where knowledge_point_id in ({','.join(map(str,kid_ids)) or 'null'})").fetchone()[0],
      '；分组挂题数',
      cur.execute(f"select count(*) from questions where knowledge_point_id in ({','.join(map(str,sec_ids)) or 'null'})").fetchone()[0])

# ---------- B ----------
practice = rows("""select id,subject,grade,name,
     (select count(*) from knowledge_points ch where ch.parent_id=k.id) kids,
     (select count(*) from questions q where q.knowledge_point_id=k.id) qs
   from knowledge_points k where node_type='section' and (grade=1 or grade=8)
     and ((instr(name,'综合实践项目')>0) or (instr(name,'探究与实践')>0))
   order by grade,subject""")
practice_conv = [r for r in practice if r[4] == 0 and r[5] > 0]
print(f'B 实践类 section 共 {len(practice)}，其中无子节点但有题需转 point 的 {len(practice_conv)}')
for r in practice_conv:
    print('   ', r)

# ---------- C ----------
# 只修「中文名里的 ?」——英文 Unit 标题末尾的问号是正确标点，不能动
def is_cjk(s):
    return any('\u4e00' <= ch <= '\u9fff' for ch in s)

rename = [r for r in rows("select id,name from knowledge_points where instr(name,'?')>0")
          if is_cjk(r[1])]
print(f'C 中文名含 "?" 的知识点 {len(rename)} 个（英文 Unit 标题的问号保留）：')
for r in rename:
    print('   ', r, '->', ' '.join(r[1].replace('?', ' ').split()))

# ---------- D ----------
def fill_prereq():
    """返回 [(kp_id, prev_id)]"""
    plan = []
    groups = rows("""select subject,grade,parent_id from knowledge_points
                     where node_type='point' and (grade=1 or grade=8)
                     group by subject,grade,parent_id""")
    # 先算每个 (subject,grade) 下的 section 顺序，用于跨组衔接
    for subj, grade, parent in groups:
        pts = rows("""select id,name,coalesce(prerequisites,'') from knowledge_points
                      where subject=? and grade=? and node_type='point' and parent_id is ?
                      order by coalesce(order_index,999), id""", subj, grade, parent)
        # 同组前序
        prev = None
        for pid, name, pre in pts:
            if not pre and prev is not None:
                plan.append((pid, prev))
            prev = pid
        # 该组首个点若仍为空 → 用同 subject/grade 上一 section 的最后一个点
        if pts and not pts[0][2]:
            if parent is not None:
                prev_sec_last = prev_point_of_previous_section(subj, grade, parent)
                if prev_sec_last:
                    plan = [p for p in plan if p[0] != pts[0][0]]
                    plan.append((pts[0][0], prev_sec_last))
    return plan

def prev_point_of_previous_section(subj, grade, parent):
    secs = rows("""select id from knowledge_points where subject=? and grade=? and node_type='section' and parent_id is null
                   order by coalesce(order_index,999), id""", subj, grade)
    ids = [s[0] for s in secs]
    if parent not in ids:
        return None
    i = ids.index(parent)
    while i > 0:
        i -= 1
        last = rows("""select id from knowledge_points where parent_id=? and node_type='point'
                       order by coalesce(order_index,999), id desc limit 1""", ids[i])
        if last:
            return last[0][0]
    return None

plan_d = fill_prereq()
print(f'D 需补先修 point {len(plan_d)} 条')

if not APPLY:
    print('\n[DRY-RUN] 未写库；加 --apply 执行')
    sys.exit(0)

# ---------- 备份 ----------
ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
bak = pathlib.Path(r'D:\ai\prj\trae\HuaWei\AiLearning\backend\_backup') / f'ailearning_dev_{ts}.db'
con.close()
shutil.copy2(DB, bak)
print('[备份]', bak, bak.stat().st_size)

con = sqlite3.connect(DB)
cur = con.cursor()
before = {t: cur.execute(f'select count(*) from {t}').fetchone()[0] for t in
          ('textbooks', 'chapters', 'knowledge_points', 'questions')}
print('[before]', before)

try:
    cur.execute('BEGIN')
    n0 = 0
    for kid in kid_ids:
        assert cur.execute('select count(*) from questions where knowledge_point_id=?', (kid,)).fetchone()[0] == 0
        cur.execute('delete from knowledge_points where id=?', (kid,)); n0 += 1
    n1 = 0
    for sid in sec_ids:
        assert cur.execute('select count(*) from knowledge_points where parent_id=?', (sid,)).fetchone()[0] == 0
        cur.execute('delete from knowledge_points where id=?', (sid,)); n1 += 1
    print(f'A 删除 point {n0} 行 / section {n1} 行')

    n2 = 0
    for pid in [r[0] for r in practice_conv]:
        cur.execute("update knowledge_points set node_type='point' where id=?", (pid,)); n2 += 1
    print(f'B 转 point {n2} 行')

    n3 = 0
    for pid, name in rename:
        new = ' '.join(name.replace('?', ' ').split())
        cur.execute('update knowledge_points set name=? where id=?', (new, pid)); n3 += 1
        print(f'C {pid}: {name!r} -> {new!r}')

    n4 = 0
    for pid, prev in plan_d:
        exists = cur.execute('select count(*) from knowledge_points where id=?', (prev,)).fetchone()[0]
        if exists:
            cur.execute('update knowledge_points set prerequisites=? where id=?', (f'[{prev}]', pid)); n4 += 1
    print(f'D 写入先修 {n4} 条')

    # 事务内复核
    bad = []
    if cur.execute('select count(*) from questions where knowledge_point_id is null').fetchone()[0]:
        bad.append('有题未挂知识点')
    if cur.execute("""select count(*) from questions q left join knowledge_points k on k.id=q.knowledge_point_id
                      where k.id is null""").fetchone()[0]:
        bad.append('有题指向不存在的知识点')
    if cur.execute("""select count(*) from knowledge_points k left join knowledge_points p on p.id=k.parent_id
                      where k.parent_id is not null and p.id is null""").fetchone()[0]:
        bad.append('有孤立父引用')
    if cur.execute("select count(*) from knowledge_points where instr(name,'样章')>0 and (grade=1 or grade=8)").fetchone()[0]:
        bad.append('g1/g8 样章节点未清干净')
    if bad:
        cur.execute('ROLLBACK'); print('[复核失败] ROLLBACK', bad); sys.exit(1)

    cur.execute('COMMIT')
    after = {t: cur.execute(f'select count(*) from {t}').fetchone()[0] for t in
             ('textbooks', 'chapters', 'knowledge_points', 'questions')}
    print('[after]', after)
    print('[delta]', {k: after[k] - before[k] for k in before})
    print('quick_check', cur.execute('pragma quick_check').fetchone()[0])
    print('外键违规', len(cur.execute('pragma foreign_key_check').fetchall()))
    print('样章节点(全库)', cur.execute("select count(*) from knowledge_points where instr(name,'样章')>0").fetchone()[0])
    print('g1/g8 point 无先修', cur.execute("""select count(*) from knowledge_points where node_type='point'
           and (grade=1 or grade=8) and (prerequisites is null or prerequisites='')""").fetchone()[0])
except Exception as e:
    try:
        cur.execute('ROLLBACK')
    except Exception:
        pass
    print('[异常] 已 ROLLBACK:', repr(e))
    raise
finally:
    con.close()
