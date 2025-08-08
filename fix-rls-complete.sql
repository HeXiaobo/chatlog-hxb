-- 完整修复 RLS 策略问题
-- 先删除可能存在的重复策略，然后重新创建

-- 删除可能存在的策略（忽略不存在的错误）
DROP POLICY IF EXISTS "Allow upload history insert" ON upload_history;
DROP POLICY IF EXISTS "Allow upload history select" ON upload_history;
DROP POLICY IF EXISTS "Allow upload history update" ON upload_history;
DROP POLICY IF EXISTS "Allow qa_pairs insert" ON qa_pairs;
DROP POLICY IF EXISTS "Allow qa_pairs select" ON qa_pairs;
DROP POLICY IF EXISTS "Allow qa_pairs update" ON qa_pairs;
DROP POLICY IF EXISTS "Allow qa_pairs delete" ON qa_pairs;

-- 删除原有策略（如果存在）
DROP POLICY IF EXISTS "Allow public read access on upload_history" ON upload_history;
DROP POLICY IF EXISTS "Allow public insert on upload_history" ON upload_history;
DROP POLICY IF EXISTS "Allow public update on upload_history" ON upload_history;
DROP POLICY IF EXISTS "Allow public read access on qa_pairs" ON qa_pairs;
DROP POLICY IF EXISTS "Allow public insert on qa_pairs" ON qa_pairs;
DROP POLICY IF EXISTS "Allow public update on qa_pairs" ON qa_pairs;
DROP POLICY IF EXISTS "Allow public delete on qa_pairs" ON qa_pairs;

-- 确保 RLS 已启用
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE qa_pairs ENABLE ROW LEVEL SECURITY;
ALTER TABLE upload_history ENABLE ROW LEVEL SECURITY;

-- 重新创建 upload_history 策略
CREATE POLICY "Allow public read access on upload_history" 
ON upload_history FOR SELECT 
USING (true);

CREATE POLICY "Allow public insert on upload_history" 
ON upload_history FOR INSERT 
WITH CHECK (true);

CREATE POLICY "Allow public update on upload_history" 
ON upload_history FOR UPDATE 
USING (true);

-- 重新创建 qa_pairs 策略
CREATE POLICY "Allow public read access on qa_pairs" 
ON qa_pairs FOR SELECT 
USING (true);

CREATE POLICY "Allow public insert on qa_pairs" 
ON qa_pairs FOR INSERT 
WITH CHECK (true);

CREATE POLICY "Allow public update on qa_pairs" 
ON qa_pairs FOR UPDATE 
USING (true);

CREATE POLICY "Allow public delete on qa_pairs" 
ON qa_pairs FOR DELETE 
USING (true);

-- 验证策略创建情况
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies 
WHERE tablename IN ('upload_history', 'qa_pairs', 'categories')
ORDER BY tablename, policyname;