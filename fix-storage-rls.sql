-- 修复 Storage RLS 策略问题
-- 问题：文件上传到 Storage 时违反 RLS 策略

-- 1. 检查当前 storage.objects 表的 RLS 状态和策略
SELECT 
    schemaname, 
    tablename, 
    rowsecurity,
    hasrls
FROM pg_tables 
WHERE tablename = 'objects' AND schemaname = 'storage';

-- 2. 查看现有的 storage.objects 策略
SELECT 
    schemaname, 
    tablename, 
    policyname, 
    permissive, 
    roles, 
    cmd, 
    qual, 
    with_check
FROM pg_policies 
WHERE tablename = 'objects' AND schemaname = 'storage'
ORDER BY policyname;

-- 3. 删除可能冲突的策略
DROP POLICY IF EXISTS "Allow public file uploads" ON storage.objects;
DROP POLICY IF EXISTS "Allow public file access" ON storage.objects;
DROP POLICY IF EXISTS "Allow file updates" ON storage.objects;
DROP POLICY IF EXISTS "Allow file deletion" ON storage.objects;

-- 4. 重新创建正确的 Storage 策略
-- 允许任何人上传文件到 wechat-files 存储桶
CREATE POLICY "Enable upload for wechat-files bucket" 
ON storage.objects 
FOR INSERT 
WITH CHECK (bucket_id = 'wechat-files');

-- 允许任何人查看 wechat-files 存储桶中的文件
CREATE POLICY "Enable read for wechat-files bucket" 
ON storage.objects 
FOR SELECT 
USING (bucket_id = 'wechat-files');

-- 允许更新 wechat-files 存储桶中的文件
CREATE POLICY "Enable update for wechat-files bucket" 
ON storage.objects 
FOR UPDATE 
USING (bucket_id = 'wechat-files')
WITH CHECK (bucket_id = 'wechat-files');

-- 允许删除 wechat-files 存储桶中的文件
CREATE POLICY "Enable delete for wechat-files bucket" 
ON storage.objects 
FOR DELETE 
USING (bucket_id = 'wechat-files');

-- 5. 验证策略创建结果
SELECT 
    policyname, 
    cmd,
    qual,
    with_check
FROM pg_policies 
WHERE tablename = 'objects' 
  AND schemaname = 'storage'
  AND policyname LIKE '%wechat-files%'
ORDER BY policyname;

-- 6. 如果上述策略仍然不工作，可以临时禁用 storage.objects 的 RLS
-- 注意：这是临时解决方案，生产环境需要正确的策略
-- ALTER TABLE storage.objects DISABLE ROW LEVEL SECURITY;