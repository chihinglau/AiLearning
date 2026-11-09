-- 33 题无出处 · 回退脚本（人工执行；执行前先备份 dev 库）
-- 生成时间：2026-11-09T04:28:20
-- 复核：执行第 1 段后题量应减少 33；第 2 段确认 0 残留

-- 0) 先备份（在 04 手册第 3 节里跑 ops backup），再执行下面语句

-- math g1：10 题
DELETE FROM questions WHERE id IN (1,2,3,4,631,632,633,634,635,636);
-- chinese g1：9 题
DELETE FROM questions WHERE id IN (29,30,31,32,611,612,613,614,615);
-- english g1：9 题
DELETE FROM questions WHERE id IN (53,54,55,56,616,617,618,619,620);
-- physics g8：5 题
DELETE FROM questions WHERE id IN (637,638,639,640,641);

-- 复核：删完再跑一次，应为 0
SELECT COUNT(*) FROM questions WHERE id IN (1,2,3,4,631,632,633,634,635,636,29,30,31,32,611,612,613,614,615,53,54,55,56,616,617,618,619,620,637,638,639,640,641);

