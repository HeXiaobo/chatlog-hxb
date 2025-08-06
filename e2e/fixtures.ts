import { test as base, expect } from '@playwright/test';

// Sample test data that matches WeChat export format
export const sampleChatData = {
  "group_name": "客户咨询群",
  "messages": [
    {
      "sender": "张三",
      "message": "请问这个产品怎么使用？有详细的教程吗？",
      "timestamp": "2024-01-15T09:00:00Z",
      "message_type": "text"
    },
    {
      "sender": "客服小李",
      "message": "您好！使用方法很简单：\n1. 首先下载并安装应用\n2. 注册账号并登录\n3. 在主界面点击"开始使用"\n4. 按照引导完成初始设置\n\n详细教程可以在帮助中心查看，或者观看我们的视频教程。",
      "timestamp": "2024-01-15T09:02:00Z",
      "message_type": "text"
    },
    {
      "sender": "李四",
      "message": "价格是多少？有没有优惠活动？",
      "timestamp": "2024-01-15T09:30:00Z",
      "message_type": "text"
    },
    {
      "sender": "客服小王",
      "message": "我们目前有三个版本：\n- 基础版：99元/月\n- 专业版：199元/月\n- 企业版：399元/月\n\n现在新用户注册有7天免费试用，首月还可享受8折优惠！",
      "timestamp": "2024-01-15T09:32:00Z",
      "message_type": "text"
    },
    {
      "sender": "王五",
      "message": "遇到技术问题了，登录不上去",
      "timestamp": "2024-01-15T10:15:00Z",
      "message_type": "text"
    },
    {
      "sender": "客服小张",
      "message": "请尝试以下解决方案：\n1. 检查网络连接是否正常\n2. 清除浏览器缓存和Cookie\n3. 尝试使用无痕模式打开\n4. 确认用户名和密码是否正确\n\n如果问题依然存在，请提供错误截图，我们会进一步协助您解决。",
      "timestamp": "2024-01-15T10:17:00Z",
      "message_type": "text"
    }
  ]
};

// Categories data
export const categories = [
  { id: 1, name: "产品咨询", description: "产品功能、特性相关问题" },
  { id: 2, name: "技术支持", description: "技术问题、故障排除" },
  { id: 3, name: "价格费用", description: "价格、付费、优惠相关" },
  { id: 4, name: "使用教程", description: "操作指南、使用方法" },
  { id: 5, name: "售后问题", description: "售后服务、投诉建议" }
];

// API response mocks
export const mockApiResponses = {
  searchResults: {
    "results": [
      {
        "id": 1,
        "question": "这个产品怎么使用？有详细的教程吗？",
        "answer": "您好！使用方法很简单：\n1. 首先下载并安装应用...",
        "category_id": 4,
        "category_name": "使用教程",
        "confidence": 0.95,
        "created_at": "2024-01-15T09:00:00Z"
      },
      {
        "id": 2,
        "question": "价格是多少？有没有优惠活动？",
        "answer": "我们目前有三个版本：\n- 基础版：99元/月...",
        "category_id": 3,
        "category_name": "价格费用",
        "confidence": 0.88,
        "created_at": "2024-01-15T09:30:00Z"
      }
    ],
    "total": 2,
    "page": 1,
    "per_page": 20
  },
  categories: categories
};

// Extended test fixture with custom helpers
export const test = base.extend<{
  // Add custom fixtures here
  mockApiData: typeof mockApiResponses;
  testChatData: typeof sampleChatData;
}>({
  mockApiData: async ({}, use) => {
    await use(mockApiResponses);
  },
  
  testChatData: async ({}, use) => {
    await use(sampleChatData);
  }
});

export { expect } from '@playwright/test';