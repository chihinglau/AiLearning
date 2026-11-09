-- 2026-11-09 库内清理：1 组重复题 + 3 册旧规格 58 题
-- 执行前置：整库快照 ailearning_dev_20261109-<时刻>.db
-- 保留 id=626（有 source_name=自主命题），删除 id=1227（source_name 为空、与 626 同章同题干同题型）

-- ① 重复题
DELETE FROM questions WHERE id = 1227;

-- ② math g8 旧规格 20 题（题干 100% 命中 math_g8_first_20261107.json）
DELETE FROM questions WHERE id BETWEEN 775 AND 794;

-- ③ chinese g8 旧规格 20 题（题干 100% 命中 chinese_g8_first_20261107.json）
DELETE FROM questions WHERE id BETWEEN 988 AND 1007;

-- ④ english g8 旧规格 18 题（题干 100% 命中 english_g8_first_20261107.json）
DELETE FROM questions WHERE id BETWEEN 1155 AND 1172;

-- 复核：应为 0
SELECT COUNT(*) AS remaining FROM questions
WHERE id IN (1227, 775,776,777,778,779,780,781,782,783,784,785,786,787,788,789,790,791,792,793,794,
             988,989,990,991,992,993,994,995,996,997,998,999,1000,1001,1002,1003,1004,1005,1006,1007,
             1155,1156,1157,1158,1159,1160,1161,1162,1163,1164,1165,1166,1167,1168,1169,1170,1171,1172);
