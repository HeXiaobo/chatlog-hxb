/**
 * 手动部署 Edge Function 到 Supabase
 * 使用 Supabase Management API
 */

const fs = require('fs');
const path = require('path');

// 读取 Edge Function 代码
const functionCode = fs.readFileSync(
  path.join(__dirname, 'supabase/functions/process-wechat-file/index.ts'), 
  'utf-8'
);

console.log('Edge Function 代码准备完成');
console.log('请手动在 Supabase Dashboard 中创建 Edge Function：');
console.log('1. 进入 Edge Functions 页面');
console.log('2. 创建名为 "process-wechat-file" 的函数');
console.log('3. 将以下代码粘贴到编辑器中：');
console.log('4. 点击 Deploy');

console.log('\n=== Edge Function 代码 ===');
console.log(functionCode);
console.log('=== 代码结束 ===\n');

console.log('创建完成后，函数的 URL 将是：');
console.log('https://atgkpaszasqhycvvszll.supabase.co/functions/v1/process-wechat-file');