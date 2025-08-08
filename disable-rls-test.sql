-- 临时禁用 RLS 来测试上传功能
-- 这是诊断步骤，确认 RLS 是问题所在

-- 禁用 RLS（临时测试用）
ALTER TABLE upload_history DISABLE ROW LEVEL SECURITY;
ALTER TABLE qa_pairs DISABLE ROW LEVEL SECURITY;

-- 保持 categories 启用 RLS（因为它工作正常）
-- ALTER TABLE categories DISABLE ROW LEVEL SECURITY;

-- 检查当前 RLS 状态
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE tablename IN ('categories', 'qa_pairs', 'upload_history')
ORDER BY tablename;