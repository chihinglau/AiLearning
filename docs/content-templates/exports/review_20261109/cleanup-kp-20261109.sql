-- 知识点层清理（2026-11-09 复核轮 · A/B/C/D）
-- 执行脚本：exports\review_20261109\kp-cleanup_20261109.py（--apply，单事务 + 前置备份）
-- 备份：backend\_backup\ailearning_dev_20261109-050711.db（3,317,760 B）
-- 结果：knowledge_points 1120 → 1093（−27）；questions 2434 不变；quick_check=ok；外键 0

-- ============ A 删除 9 个「样章·…」占位分组 + 18 个子点（挂题数均为 0）============
-- 分组 id：37(politics g1) / 175(chinese g8) / 178(math g8) / 181(english g8) / 184(physics g8)
--          187(biology g8) / 190(history g8) / 193(geography g8) / 196(politics g8)
-- 子点：上述每个分组下各 2 个（id 38,39 / 176,177 / 179,180 / 182,183 / 185,186 / 188,189 / 191,192 / 194,195 / 197,198）
-- 理由：05 阶段 4「旧版占位数据删除」口径的延续；这些节点 0 题、0 引用，纯 seed 残留。
DELETE FROM knowledge_points WHERE id IN (38,39,176,177,179,180,182,183,185,186,188,189,191,192,194,195,197,198);
DELETE FROM knowledge_points WHERE id IN (37,175,178,181,184,187,190,193,196);

-- ============ B 5 个实践类节点 section → point ============
-- 这 5 个节点无子节点、各挂 1 题；按 knowledge_points 语义（section=分组、point=最小学习单位）转为 point，
-- 使「题目挂 point」在 node_type 上自洽（此前全库有 5 道题挂在 section 上）。
UPDATE knowledge_points SET node_type='point' WHERE id IN (615,630,901,912,921);

-- ============ C 修 2 个中文知识点的 '?' 脏字符 ============
UPDATE knowledge_points SET name='任务二 新闻采访' WHERE id=716 AND name='任务二?新闻采访';
UPDATE knowledge_points SET name='任务三 新闻写作' WHERE id=717 AND name='任务三?新闻写作';
-- 注意：英文 Unit 标题末尾的问号是正确标点（如 'Unit 1 What can you do?'），不得替换。

-- ============ D 补 prerequisites（156 条，规则化，脚本按当前树结构生成）============
-- 规则：同一 (subject, grade, parent) 内，按 (order_index, id) 排序后取「前一个 point」的 id；
--       若该点是分组首点，则取其前一个分组的最后一个 point。
--       例：UPDATE knowledge_points SET prerequisites='[310]' WHERE id=311;
--       实际 156 条由脚本一次性生成（未被写入的 18 条因前序点恰好是 A 中删除的占位子点）。

-- ============ 复核（执行后应返回下列值）============
-- SELECT count(*) FROM knowledge_points;                      -- 1093
-- SELECT count(*) FROM questions WHERE knowledge_point_id IS NULL;  -- 0
-- SELECT count(*) FROM questions q LEFT JOIN knowledge_points k ON k.id=q.knowledge_point_id WHERE k.id IS NULL;  -- 0
-- SELECT count(*) FROM questions q JOIN knowledge_points k ON k.id=q.knowledge_point_id WHERE k.node_type='section';  -- 0
-- SELECT count(*) FROM knowledge_points WHERE instr(name,'样章')>0 AND grade IN (1,8);  -- 0（g2–g7/g9–g12 仍有 55 个，本轮不动）
