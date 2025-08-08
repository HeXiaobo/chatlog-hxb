-- 全面诊断所有 RLS 相关问题

-- 1. 检查所有表的 RLS 状态
SELECT schemaname, tablename, rowsecurity, hasrls 
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;

-- 2. 检查所有现有的 RLS 策略
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies 
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- 3. 临时禁用所有表的 RLS（仅用于诊断）
DO $$ 
DECLARE 
    r RECORD;
BEGIN 
    FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND rowsecurity = true
    LOOP
        EXECUTE 'ALTER TABLE ' || quote_ident(r.tablename) || ' DISABLE ROW LEVEL SECURITY';
        RAISE NOTICE 'Disabled RLS for table: %', r.tablename;
    END LOOP;
END $$;

-- 4. 验证所有表都已禁用 RLS
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' AND rowsecurity = true;