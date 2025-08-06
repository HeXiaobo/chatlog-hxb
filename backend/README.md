# WeChat Group Q&A Knowledge Base - Backend

微信群问答知识库系统后端API服务

## 🚀 快速开始

### 开发环境启动
```bash
# 安装依赖
pip install -r requirements.txt

# 初始化环境和数据库
python run_dev.py --setup

# 启动开发服务器
python run_dev.py
```

### 生产环境部署
```bash
# 使用gunicorn启动
gunicorn -c gunicorn.conf.py run:app
```

## 📋 功能特性

### ✅ 核心服务
- **智能数据提取**: WeChat JSON → Q&A pairs (多种模式识别)
- **自动分类系统**: 5大类别智能分类 (产品咨询/技术支持/价格费用/使用教程/售后问题)
- **全文搜索**: FTS5 + jieba中文分词 + 同义词扩展
- **文件处理**: 完整的上传→验证→提取→保存流程
- **数据验证**: 多层验证和错误处理机制

### ✅ API端点

#### 基础API (`/api/v1/`)
- `GET /health` - 系统健康检查
- `GET /info` - API信息
- `GET /categories` - 获取分类列表
- `GET /qa` - 获取问答列表 (支持分页)
- `GET /qa/{id}` - 获取问答详情

#### 文件上传 (`/api/v1/upload/`)
- `POST /file` - 上传并处理WeChat JSON文件
- `GET /status/{id}` - 查询处理状态
- `GET /history` - 上传历史 (支持分页和筛选)
- `POST /cleanup` - 清理临时文件

#### 搜索功能 (`/api/v1/search/`)
- `GET /` - 全文搜索 (支持分类/回答者筛选和排序)
- `GET /suggestions` - 搜索建议
- `GET /popular` - 热门搜索
- `GET /stats` - 搜索统计
- `POST /rebuild-index` - 重建搜索索引

#### 管理功能 (`/api/v1/admin/`)
- `GET /stats` - 系统综合统计
- `GET /health` - 详细健康检查
- `POST /reindex` - 重建搜索索引
- `POST /cleanup` - 系统清理

## 🏗️ 系统架构

```
backend/
├── app/
│   ├── models/          # 数据模型
│   │   ├── qa.py       # 问答对模型
│   │   ├── category.py # 分类模型
│   │   └── upload.py   # 上传历史模型
│   ├── routes/         # API路由
│   │   ├── api.py      # 基础API
│   │   ├── upload.py   # 文件上传
│   │   ├── search.py   # 搜索功能
│   │   └── admin.py    # 管理功能
│   └── services/       # 业务服务
│       ├── data_extractor.py    # 数据提取
│       ├── qa_classifier.py     # 智能分类
│       ├── file_processor.py    # 文件处理
│       ├── search_service.py    # 搜索服务
│       └── validator.py         # 数据验证
├── migrations/         # 数据库迁移
├── config.py          # 配置管理
├── run_dev.py         # 开发工具
└── test_api.py        # API测试
```

## 🧠 智能特性

### 问答提取算法
- **3种识别模式**: 直接问答、问题解决、教程指南
- **上下文分析**: 时间窗口内的对话关联
- **置信度评分**: 0.6-1.0动态评分系统
- **去重机制**: 内容指纹防重复

### 智能分类系统
- **关键词匹配**: 60%权重
- **模式识别**: 40%权重  
- **权重调节**: 技术支持1.2x、价格费用1.1x
- **批量处理**: 高效分类算法

### 全文搜索引擎
- **FTS5支持**: SQLite全文搜索索引
- **中文分词**: jieba智能分词
- **同义词扩展**: 内置同义词词典
- **多维筛选**: 分类、回答者、时间范围
- **相关性排序**: 智能结果排序

## 📊 性能指标

- **文件处理**: <30s for 10MB JSON
- **搜索响应**: <2s for any query
- **提取准确率**: ≥80% Q&A识别
- **分类准确率**: ≥70% 自动分类
- **API响应**: <500ms average

## 🔧 开发工具

### 开发脚本 (`run_dev.py`)
```bash
python run_dev.py --setup    # 初始化环境
python run_dev.py --reset    # 重置数据库
python run_dev.py --check    # 系统检查
python run_dev.py           # 启动服务器
```

### API测试 (`test_api.py`)
```bash
python test_api.py           # 完整API测试
python test_api.py --url http://prod-server  # 测试生产环境
```

### 数据库管理
```bash
# 创建迁移
flask db migrate -m "description"

# 应用迁移
flask db upgrade

# 初始化数据
flask init-db
flask create-sample-data
```

## 📁 数据格式

### WeChat JSON输入格式
```json
{
  "messages": [
    {
      "sender": "用户名",
      "content": "消息内容", 
      "timestamp": "2024-08-06 10:00:00",
      "type": "text"
    }
  ]
}
```

### API响应格式
```json
{
  "success": true,
  "data": {...},
  "message": "操作成功",
  "pagination": {...}  // 分页时包含
}
```

## 🛠️ 配置选项

### 环境变量
- `FLASK_ENV`: 运行环境 (development/production)
- `DATABASE_URL`: 数据库连接字符串
- `SECRET_KEY`: 应用密钥
- `MAX_CONTENT_LENGTH`: 最大文件大小

### 配置文件 (`config.py`)
- 数据库配置
- 文件上传限制
- 搜索参数
- 日志配置
- CORS设置

## 🔍 故障排除

### 常见问题

**数据库连接失败**
```bash
python run_dev.py --setup
```

**搜索功能异常**
```bash
curl -X POST http://localhost:5000/api/v1/search/rebuild-index
```

**依赖缺失**
```bash
pip install -r requirements.txt
```

### 日志查看
```bash
tail -f logs/app.log
```

## 🔒 安全特性

- 文件类型验证
- 文件大小限制
- SQL注入防护
- XSS防护
- CORS配置
- 错误信息脱敏

## 📈 监控指标

- API响应时间
- 数据库查询性能
- 文件处理统计
- 搜索使用情况
- 系统健康状态

---

**版本**: 1.0.0  
**更新时间**: 2024-08-06  
**Python要求**: 3.7+