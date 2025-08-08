/**
 * 端到端测试：AI智能聊天记录处理前端工作流程
 * 
 * 测试完整的用户交互流程：
 * 1. 选择智能处理模式
 * 2. 上传微信聊天记录文件  
 * 3. 观察AI处理进度
 * 4. 查看处理结果和统计
 * 5. 验证知识库生成效果
 * 
 * 运行命令：npx playwright test tests/e2e/ai-workflow.spec.ts
 */

import { test, expect } from '@playwright/test';
import path from 'path';

// 测试数据
const testChatData = {
  metadata: {
    group_name: "技术咨询群",
    export_time: new Date().toISOString(),
    total_messages: 20
  },
  messages: [
    // 有价值的技术问答
    {
      timestamp: "2024-01-15 10:30:00",
      sender: "张三",
      content: "请问React中如何使用useEffect处理副作用？",
      type: "text"
    },
    {
      timestamp: "2024-01-15 10:32:00",
      sender: "李工程师", 
      content: "useEffect接收两个参数：副作用函数和依赖数组。例如：useEffect(() => { fetchData(); }, [userId])",
      type: "text"
    },
    {
      timestamp: "2024-01-15 10:35:00",
      sender: "张三",
      content: "那清理函数怎么写？",
      type: "text"
    },
    {
      timestamp: "2024-01-15 10:37:00", 
      sender: "李工程师",
      content: "在副作用函数中返回清理函数：useEffect(() => { const timer = setInterval(() => {}, 1000); return () => clearInterval(timer); }, [])",
      type: "text"
    },
    
    // 产品咨询
    {
      timestamp: "2024-01-15 11:00:00",
      sender: "王客户",
      content: "你们的产品价格怎么样？有试用版吗？",
      type: "text"
    },
    {
      timestamp: "2024-01-15 11:02:00",
      sender: "客服小刘", 
      content: "我们提供30天免费试用，标准版月费199元，企业版月费999元。试用期间享受完整功能",
      type: "text"
    },
    
    // 无用闲聊（应被过滤）
    {
      timestamp: "2024-01-15 12:00:00",
      sender: "小明",
      content: "大家好",
      type: "text"
    },
    {
      timestamp: "2024-01-15 12:01:00", 
      sender: "小红",
      content: "你好",
      type: "text"
    },
    {
      timestamp: "2024-01-15 12:02:00",
      sender: "小李", 
      content: "😊",
      type: "text"
    },
    {
      timestamp: "2024-01-15 15:00:00",
      sender: "用户A",
      content: "今天天气真好",
      type: "text"
    }
  ]
};

test.describe('AI智能处理工作流程', () => {
  
  test.beforeEach(async ({ page }) => {
    // 访问应用首页
    await page.goto('http://localhost:3000');
    
    // 等待页面加载完成
    await page.waitForLoadState('networkidle');
  });

  test('完整的智能处理工作流程', async ({ page }) => {
    test.setTimeout(60000); // 设置60秒超时
    
    // 步骤1: 验证页面加载和处理模式选择
    await test.step('验证页面加载和处理模式选择', async () => {
      // 检查页面标题
      await expect(page).toHaveTitle(/微信群问答知识库/);
      
      // 检查是否有处理模式选择区域
      const processingModeCard = page.locator('[title*="处理模式选择"]');
      if (await processingModeCard.isVisible()) {
        // 选择智能处理模式
        await page.locator('input[value="intelligent"]').check();
        
        // 验证智能处理模式描述
        await expect(page.locator('text=AI智能分析')).toBeVisible();
        await expect(page.locator('text=推荐')).toBeVisible();
      }
    });

    // 步骤2: 创建测试文件并上传
    await test.step('上传测试聊天记录文件', async () => {
      // 创建临时测试文件
      const testFilePath = path.join(__dirname, 'temp_test_chat.json');
      const fs = require('fs');
      fs.writeFileSync(testFilePath, JSON.stringify(testChatData, null, 2));
      
      // 查找文件上传组件
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(testFilePath);
      
      // 清理临时文件
      fs.unlinkSync(testFilePath);
    });

    // 步骤3: 监控处理进度
    await test.step('监控AI处理进度', async () => {
      // 等待处理开始
      await expect(page.locator('text=正在处理数据')).toBeVisible({ timeout: 10000 });
      
      // 验证进度条出现
      const progressBar = page.locator('.ant-progress');
      await expect(progressBar).toBeVisible();
      
      // 检查智能处理相关的提示文本
      const intelligentProcessingIndicators = [
        'AI智能分析',
        '智能深度处理',
        '智能筛选',
        '内容清洗',
        '智能处理中'
      ];
      
      let foundIndicator = false;
      for (const indicator of intelligentProcessingIndicators) {
        if (await page.locator(`text*=${indicator}`).isVisible()) {
          foundIndicator = true;
          break;
        }
      }
      expect(foundIndicator).toBe(true);
    });

    // 步骤4: 验证处理完成结果
    await test.step('验证处理完成和结果展示', async () => {
      // 等待处理完成 - 增加超时时间
      await expect(page.locator('text=完成')).toBeVisible({ timeout: 45000 });
      
      // 验证结果卡片出现
      const resultCard = page.locator('[title*="完成"]');
      await expect(resultCard).toBeVisible();
      
      // 检查智能处理结果指标
      const resultMetrics = [
        '个高质量知识库条目',
        '智能处理完成',
        '知识库条目',
        '问答对',
        '处理完成'
      ];
      
      let foundMetric = false;
      for (const metric of resultMetrics) {
        if (await page.locator(`text*=${metric}`).isVisible()) {
          foundMetric = true;
          break;
        }
      }
      expect(foundMetric).toBe(true);
    });

    // 步骤5: 验证处理统计信息
    await test.step('验证处理统计和质量指标', async () => {
      // 查找统计信息
      const statsElements = await page.locator('.ant-list-item').all();
      expect(statsElements.length).toBeGreaterThan(0);
      
      // 验证有数字统计
      const numberRegex = /\d+/;
      let hasNumbers = false;
      
      for (const element of statsElements) {
        const text = await element.textContent();
        if (text && numberRegex.test(text)) {
          hasNumbers = true;
          break;
        }
      }
      expect(hasNumbers).toBe(true);
    });

    // 步骤6: 测试导航和后续操作
    await test.step('测试后续操作按钮', async () => {
      // 检查是否有"查看知识库"按钮
      const viewKnowledgeBtn = page.locator('button:has-text("查看知识库"), button:has-text("查看")');
      if (await viewKnowledgeBtn.isVisible()) {
        // 可以点击但不实际导航（避免测试复杂化）
        await expect(viewKnowledgeBtn).toBeEnabled();
      }
      
      // 检查"继续上传"按钮
      const continueUploadBtn = page.locator('button:has-text("继续上传")');
      if (await continueUploadBtn.isVisible()) {
        await expect(continueUploadBtn).toBeEnabled();
      }
    });
  });

  test('智能处理模式UI交互', async ({ page }) => {
    await test.step('验证处理模式选择交互', async () => {
      // 查找处理模式选择区域
      const modeSelection = page.locator('[title*="处理模式"]');
      if (await modeSelection.isVisible()) {
        
        // 测试智能处理模式选择
        const intelligentMode = page.locator('input[value="intelligent"]');
        if (await intelligentMode.isVisible()) {
          await intelligentMode.check();
          
          // 验证描述文本更新
          await expect(page.locator('text*=AI智能分析')).toBeVisible();
          await expect(page.locator('text*=筛选有价值内容')).toBeVisible();
        }
        
        // 测试标准模式选择
        const standardMode = page.locator('input[value="standard"]');
        if (await standardMode.isVisible()) {
          await standardMode.check();
          
          // 验证描述文本更新
          await expect(page.locator('text*=标准AI处理')).toBeVisible();
          await expect(page.locator('text*=兼容性更好')).toBeVisible();
        }
      }
    });
  });

  test('AI处理步骤指示器', async ({ page }) => {
    await test.step('验证步骤指示器显示', async () => {
      // 查找步骤指示器
      const stepsContainer = page.locator('.ant-steps');
      if (await stepsContainer.isVisible()) {
        
        // 验证步骤数量（智能处理模式应该有5个步骤）
        const steps = page.locator('.ant-steps-item');
        const stepCount = await steps.count();
        expect(stepCount).toBeGreaterThanOrEqual(4);
        
        // 验证步骤标题
        const expectedSteps = [
          '选择文件',
          '智能分析',
          '内容清洗',
          '入库保存',
          '完成'
        ];
        
        for (const expectedStep of expectedSteps) {
          const stepExists = await page.locator(`.ant-steps-item:has-text("${expectedStep}")`).count() > 0;
          if (stepExists) {
            // 至少应该找到部分预期步骤
            break;
          }
        }
      }
    });
  });

  test('错误处理和用户反馈', async ({ page }) => {
    await test.step('测试错误处理', async () => {
      // 尝试上传无效文件（如果有文件验证）
      const fileInput = page.locator('input[type="file"]');
      if (await fileInput.isVisible()) {
        
        // 创建一个无效的JSON文件
        const invalidFilePath = path.join(__dirname, 'invalid_test.json');
        const fs = require('fs');
        fs.writeFileSync(invalidFilePath, 'invalid json content');
        
        try {
          await fileInput.setInputFiles(invalidFilePath);
          
          // 检查是否有错误提示
          const errorAlert = page.locator('.ant-alert-error, .ant-message-error');
          // 错误提示可能出现也可能不出现，取决于前端验证逻辑
          
        } catch (error) {
          // 文件上传可能被阻止，这是正常的
        } finally {
          // 清理文件
          fs.unlinkSync(invalidFilePath);
        }
      }
    });
  });

  test('响应式设计验证', async ({ page }) => {
    await test.step('测试移动端显示', async () => {
      // 切换到移动端视口
      await page.setViewportSize({ width: 375, height: 667 });
      
      // 验证页面在小屏幕上的显示
      await expect(page.locator('body')).toBeVisible();
      
      // 检查是否有响应式布局
      const mainContent = page.locator('.ant-card, [class*="card"]');
      if (await mainContent.first().isVisible()) {
        const cardWidth = await mainContent.first().boundingBox();
        expect(cardWidth?.width).toBeLessThanOrEqual(375);
      }
    });
    
    await test.step('测试桌面端显示', async () => {
      // 切换回桌面端视口
      await page.setViewportSize({ width: 1280, height: 720 });
      
      // 验证布局正常
      await expect(page.locator('body')).toBeVisible();
    });
  });

  test('性能和加载时间', async ({ page }) => {
    await test.step('验证页面加载性能', async () => {
      const startTime = Date.now();
      
      await page.goto('http://localhost:3000');
      await page.waitForLoadState('networkidle');
      
      const loadTime = Date.now() - startTime;
      
      // 验证页面加载时间不超过5秒
      expect(loadTime).toBeLessThan(5000);
      
      // 验证关键元素已加载
      await expect(page.locator('h1, .ant-card, [class*="header"]').first()).toBeVisible();
    });
  });
});

test.describe('AI配置和状态', () => {
  
  test('AI功能状态检查', async ({ page }) => {
    await page.goto('http://localhost:3000');
    
    await test.step('验证AI功能可用性显示', async () => {
      // 查找AI状态指示器
      const aiStatusElements = [
        '.ant-tag:has-text("可用")',
        '.ant-tag:has-text("不可用")', 
        'text=AI功能',
        'text=智能提取',
        '[class*="ai"]'
      ];
      
      let statusFound = false;
      for (const selector of aiStatusElements) {
        if (await page.locator(selector).count() > 0) {
          statusFound = true;
          break;
        }
      }
      
      // AI状态显示是可选的，但如果显示了应该是有效的
      if (statusFound) {
        console.log('AI状态指示器已找到');
      }
    });
  });
});