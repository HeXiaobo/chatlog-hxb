# 微信群问答知识库系统

基于微信群聊记录的智能问答知识库，帮助客服团队快速复用历史经验，提升响应效率。

## 项目架构

```
chatlog/
├── backend/              # Python Flask 后端
│   ├── app/
│   │   ├── models/       # 数据库模型
│   │   ├── routes/       # API路由
│   │   ├── services/     # 业务逻辑
│   │   └── utils/        # 工具函数
│   ├── migrations/       # 数据库迁移
│   ├── config.py         # 配置文件
│   └── requirements.txt  # Python依赖
├── frontend/             # React 前端
│   ├── src/
│   │   ├── components/   # React组件
│   │   ├── pages/        # 页面组件
│   │   ├── services/     # API服务
│   │   └── hooks/        # 自定义钩子
│   ├── package.json      # Node.js依赖
│   └── vite.config.ts    # Vite配置
├── docker-compose.yml    # Docker编排
├── product-design/       # 产品设计文档
└── README.md
```

## 技术栈

### 数据采集
- **chatlog工具**: GitHub开源项目 `sjzar/chatlog`
- 支持微信群聊记录导出为JSON格式

### 后端 (Python)
- **框架**: Flask + Flask-SQLAlchemy
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **搜索**: SQLite FTS5 全文搜索
- **API**: RESTful API

### 前端 (React)
- **框架**: React 18 + TypeScript
- **UI库**: Ant Design
- **构建工具**: Vite
- **状态管理**: React Context + useReducer

### 部署
- **容器化**: Docker + Docker Compose
- **Web服务**: Nginx (生产环境)

## 快速开始

### 1. 环境准备
```bash
# 安装chatlog工具 (数据导出)
wget https://github.com/sjzar/chatlog/releases/latest/download/chatlog-darwin-amd64
chmod +x chatlog-darwin-amd64
mv chatlog-darwin-amd64 /usr/local/bin/chatlog

# 克隆项目
git clone https://github.com/HeXiaobo/hexiaobo-projects.git
cd hexiaobo-projects/chatlog
```

### 2. 导出微信数据
```bash
# 导出微信群聊记录
chatlog export --platform wechat --group-name "客户咨询群" --output ./data/wechat_data.json
```

### 3. 启动开发环境
```bash
# Docker方式 (推荐)
docker-compose up -d

# 或手动启动
# 后端
cd backend
pip install -r requirements.txt
flask run

# 前端
cd frontend  
npm install
npm run dev
```

### 4. 访问应用
- 前端界面: http://localhost:3000
- 后端API: http://localhost:5000/api/v1

## 主要功能

### ✅ MVP版本功能
- [x] 微信群JSON文件上传
- [x] 自动问答对提取 (准确率≥80%)
- [x] 5个基础分类管理
- [x] 关键词搜索 (响应时间<2秒)
- [x] Web端知识库浏览
- [x] 手动数据更新机制

### 🚀 计划中功能
- [ ] 多群组支持
- [ ] 实时数据同步
- [ ] 智能问答推荐
- [ ] 移动端适配
- [ ] 高级权限管理

## API文档

详见 `product-design/api-specification.md`

主要接口：
- `POST /api/v1/upload/file` - 上传JSON文件
- `GET /api/v1/search?q=关键词` - 搜索问答
- `GET /api/v1/qa` - 获取问答列表
- `GET /api/v1/categories` - 获取分类列表

## 数据格式

### 输入格式 (chatlog工具导出)
```json
{
  "messages": [
    {
      "id": "123456789",
      "timestamp": "2024-08-06 10:30:00",
      "sender": "客户张三", 
      "content": "请问这个产品怎么使用？",
      "type": "text",
      "group": "客户咨询群"
    }
  ]
}
```

### 处理后格式 (知识库存储)
```json
{
  "question": "请问这个产品怎么使用？",
  "answer": "您好，这个产品使用方法如下...",
  "category": "使用教程",
  "asker": "客户张三",
  "advisor": "李顾问",
  "confidence": 0.85,
  "timestamp": "2024-08-06 10:30:00"
}
```

## 开发指南

### 后端开发
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
flask db upgrade
flask run --debug
```

### 前端开发
```bash
cd frontend
npm install
npm run dev
```

### 数据库操作
```bash
# 创建迁移
flask db migrate -m "描述"

# 执行迁移
flask db upgrade

# 数据库重置
flask db downgrade
```

## 测试

### 后端测试
```bash
cd backend
python -m pytest tests/ -v
```

### 前端测试
```bash
cd frontend
npm run test
```

## 部署

### Docker部署
```bash
# 构建并启动
docker-compose up --build -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 生产部署
详见 `product-design/system-architecture.md` 中的部署章节。

## 许可证

MIT License

## 贡献

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/新功能`)
3. 提交更改 (`git commit -am '添加新功能'`)
4. 推送分支 (`git push origin feature/新功能`)
5. 创建 Pull Request

## 支持

如有问题，请创建 [Issue](https://github.com/HeXiaobo/hexiaobo-projects/issues)