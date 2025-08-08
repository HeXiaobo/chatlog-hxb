# AI提供商配置指南

本文档提供了各个AI提供商的配置方法和API获取指南。

## 🌙 月之暗面 Kimi

**获取API Key**：
1. 访问 [Kimi开放平台](https://platform.moonshot.cn/)
2. 注册账户并完成实名认证
3. 创建应用获取API Key

**环境变量配置**：
```bash
KIMI_API_KEY=your_api_key_here
KIMI_MODEL=moonshot-v1-8k  # 或 moonshot-v1-32k, moonshot-v1-128k
KIMI_API_BASE=https://api.moonshot.cn/v1/
KIMI_MAX_TOKENS=8000
KIMI_DAILY_LIMIT=5000
KIMI_COST_PER_1K=0.012
```

**特点**：
- 长文本理解能力强（最高128K上下文）
- 中文优化，适合中文场景
- 定价合理，性能稳定

## 🫘 字节豆包

**获取API Key**：
1. 访问 [火山引擎](https://console.volcengine.com/ark/)
2. 注册账户并开通豆包服务
3. 创建推理接入点获取endpoint和API Key

**环境变量配置**：
```bash
DOUBAO_API_KEY=your_api_key_here
DOUBAO_MODEL=your_endpoint_id  # 如：ep-20240611073937-h8l9s
DOUBAO_API_BASE=https://ark.cn-beijing.volces.com/api/v3/
DOUBAO_MAX_TOKENS=4000
DOUBAO_DAILY_LIMIT=15000
DOUBAO_COST_PER_1K=0.0008
```

**特点**：
- 高性价比，成本低廉
- 字节跳动出品，稳定可靠
- 支持多模态能力

## 🔍 DeepSeek

**获取API Key**：
1. 访问 [DeepSeek开放平台](https://platform.deepseek.com/)
2. 注册账户并获取API Key
3. 充值使用（极低定价）

**环境变量配置**：
```bash
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_MODEL=deepseek-chat  # 或 deepseek-coder
DEEPSEEK_API_BASE=https://api.deepseek.com/v1/
DEEPSEEK_MAX_TOKENS=4000
DEEPSEEK_DAILY_LIMIT=50000
DEEPSEEK_COST_PER_1K=0.00014
```

**特点**：
- 极具竞争力的定价（最便宜）
- 优秀的代码能力
- 支持OpenAI兼容接口

## 🧠 智谱AI (GLM)

**获取API Key**：
1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/)
2. 注册账户并实名认证
3. 创建API Key

**环境变量配置**：
```bash
ZHIPU_API_KEY=your_api_key_here
ZHIPU_MODEL=glm-4  # 或 glm-4v, glm-3-turbo
ZHIPU_API_BASE=https://open.bigmodel.cn/api/paas/v4/
ZHIPU_MAX_TOKENS=4000
ZHIPU_DAILY_LIMIT=15000
ZHIPU_COST_PER_1K=0.001
```

**特点**：
- 清华大学技术背景
- 中文理解能力强
- 支持多模态

## 🐻 百度文心一言

**获取API Key**：
1. 访问 [百度智能云](https://console.bce.baidu.com/qianfan/)
2. 开通千帆大模型平台
3. 创建应用获取API Key和Secret Key

**环境变量配置**：
```bash
BAIDU_API_KEY=your_api_key_here
BAIDU_SECRET_KEY=your_secret_key_here  # 百度需要额外的Secret Key
BAIDU_MODEL=ernie-bot-turbo  # 或 ernie-bot, ernie-bot-4
BAIDU_API_BASE=https://aip.baidubce.com/
BAIDU_MAX_TOKENS=2000
BAIDU_DAILY_LIMIT=20000
BAIDU_COST_PER_1K=0.0008
```

## ☁️ 阿里云通义千问

**获取API Key**：
1. 访问 [阿里云模型服务灵积](https://dashscope.aliyun.com/)
2. 开通服务并获取API Key

**环境变量配置**：
```bash
ALIBABA_API_KEY=your_api_key_here
ALIBABA_MODEL=qwen-turbo  # 或 qwen-plus, qwen-max
ALIBABA_API_BASE=https://dashscope.aliyuncs.com/api/v1/
ALIBABA_MAX_TOKENS=2000
ALIBABA_DAILY_LIMIT=15000
ALIBABA_COST_PER_1K=0.0008
```

## 🤖 OpenAI

**环境变量配置**：
```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-3.5-turbo  # 或 gpt-4, gpt-4-turbo
OPENAI_API_BASE=https://api.openai.com/v1/  # 或使用代理地址
OPENAI_MAX_TOKENS=4000
OPENAI_DAILY_LIMIT=10000
OPENAI_COST_PER_1K=0.002
```

## 🎭 Anthropic Claude

**环境变量配置**：
```bash
ANTHROPIC_API_KEY=your_api_key_here
ANTHROPIC_MODEL=claude-3-sonnet-20240229  # 或 claude-3-haiku, claude-3-opus
ANTHROPIC_API_BASE=https://api.anthropic.com/
ANTHROPIC_MAX_TOKENS=4000
ANTHROPIC_DAILY_LIMIT=8000
ANTHROPIC_COST_PER_1K=0.003
```

## 🏠 Ollama本地模型

**安装Ollama**：
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows - 下载安装包
# https://ollama.com/download
```

**运行模型**：
```bash
ollama run llama2:7b  # 或其他模型
ollama run qwen:7b
ollama run codellama:7b
```

**环境变量配置**：
```bash
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama2:7b  # 或其他已安装的模型
OLLAMA_MAX_TOKENS=2000
OLLAMA_DAILY_LIMIT=50000
```

## 配置优先级

系统会按以下优先级自动选择主提供商：
1. Ollama (本地模型，免费)
2. DeepSeek (最便宜)
3. Kimi (长文本能力强)
4. 字节豆包 (高性价比)
5. 智谱AI
6. 百度文心一言
7. 阿里云通义千问
8. Anthropic Claude
9. OpenAI

## 使用建议

### 场景推荐

**长文本处理**: Kimi (128K上下文)
**代码生成**: DeepSeek, OpenAI
**中文理解**: 智谱AI, 百度, Kimi
**成本敏感**: DeepSeek, 字节豆包
**本地部署**: Ollama
**企业级**: 百度, 阿里云, 智谱AI

### 性价比排名

1. **DeepSeek** - $0.00014/1K tokens
2. **字节豆包** - $0.0008/1K tokens
3. **百度文心一言** - $0.0008/1K tokens
4. **智谱AI** - $0.001/1K tokens
5. **OpenAI** - $0.002/1K tokens
6. **Anthropic** - $0.003/1K tokens
7. **Kimi** - $0.012/1K tokens (但长文本能力强)

### 安全注意事项

1. **API Key安全**: 不要在代码中硬编码API Key
2. **访问控制**: 设置合理的每日限额
3. **监控使用**: 定期检查使用量和成本
4. **备份策略**: 配置多个提供商作为备份