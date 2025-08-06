# Supabase ChatLog 项目设置指南

## 步骤 1: 创建 Supabase 项目

1. 访问 [https://supabase.com](https://supabase.com)
2. 创建账号并登录
3. 点击 "New Project"
4. 填写项目信息：
   - **项目名称**: chatlog-kb
   - **数据库密码**: 请生成一个强密码并保存
   - **区域**: Southeast Asia (Singapore) 或 East Asia (Hong Kong)
   - **定价方案**: Free tier

5. 等待项目创建完成 (约2-3分钟)

## 步骤 2: 获取项目配置信息

项目创建后，在项目仪表板中获取以下信息：

1. 进入 **Settings > API**
2. 复制以下信息：
   - **Project URL** (类似: https://abcdefghijklmnop.supabase.co)
   - **Project API Key** (anon key)
   - **Service Role Key** (service_role key)

## 步骤 3: 创建环境变量文件

请手动创建以下环境变量文件，并填入从 Supabase 获取的信息：

### frontend/.env.production
```
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

### frontend/.env.development
```
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

## 步骤 4: 执行数据库设置

完成项目创建后，回到终端执行下一步：数据库结构创建。

---

## 重要提醒

- 🔒 **保密**: 请妥善保管 Service Role Key，不要提交到代码仓库
- 🌍 **区域**: 建议选择新加坡或香港区域以获得更好的访问速度
- 💰 **免费额度**: 免费方案包含 500MB 数据库 + 1GB 存储 + 2GB 数据传输

## 下一步

完成 Supabase 项目创建后，我们将继续配置数据库表结构。