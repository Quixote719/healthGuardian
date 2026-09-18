import { test, expect } from '@playwright/test';

/**
 * 聊天功能 E2E 测试
 * 
 * 注意：这些测试需要后端服务运行才能完整执行
 * 部分测试会 mock 后端响应以独立运行
 */
test.describe('聊天功能', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('用户可以在输入框中输入文本', async ({ page }) => {
    const textarea = page.getByRole('textbox', { name: /健康咨询输入框/ });
    
    await textarea.fill('我最近血脂偏高，睡眠质量不好');
    await expect(textarea).toHaveValue('我最近血脂偏高，睡眠质量不好');
  });

  test('按 Enter 键应触发发送（非 Shift+Enter）', async ({ page }) => {
    const textarea = page.getByRole('textbox', { name: /健康咨询输入框/ });
    
    await textarea.fill('测试消息');
    
    // 监听请求
    const requestPromise = page.waitForRequest(
      (request) => request.url().includes('/api/chat'),
      { timeout: 5000 }
    ).catch(() => null);

    await textarea.press('Enter');
    
    // 输入框应被清空（消息已发送）
    await expect(textarea).toHaveValue('');
  });

  test('Shift+Enter 应换行而非发送', async ({ page }) => {
    const textarea = page.getByRole('textbox', { name: /健康咨询输入框/ });
    
    await textarea.fill('第一行');
    await textarea.press('Shift+Enter');
    await textarea.type('第二行');
    
    // 输入框应包含换行
    const value = await textarea.inputValue();
    expect(value).toContain('第一行');
    expect(value).toContain('第二行');
  });

  test('发送消息后应显示用户消息', async ({ page }) => {
    // Mock 后端 API 响应
    await page.route('**/api/chat', async (route) => {
      // 返回一个 SSE 流模拟
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: `event: status\ndata: {"agent_name": "Controller_Agent", "progress": "处理中", "percentage": 10}\n\n`,
      });
    });

    const textarea = page.getByRole('textbox', { name: /健康咨询输入框/ });
    const sendButton = page.getByRole('button', { name: /发送/ });

    await textarea.fill('测试健康咨询消息');
    await sendButton.click();

    // 用户消息应显示在页面上
    await expect(page.getByText('测试健康咨询消息')).toBeVisible({ timeout: 5000 });
  });

  test('发送消息时应显示加载状态', async ({ page }) => {
    // Mock 后端 API 响应（延迟响应以观察加载状态）
    await page.route('**/api/chat', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: `event: status\ndata: {"agent_name": "Controller_Agent", "progress": "处理中", "percentage": 10}\n\n`,
      });
    });

    const textarea = page.getByRole('textbox', { name: /健康咨询输入框/ });
    const sendButton = page.getByRole('button', { name: /发送/ });

    await textarea.fill('测试消息');
    await sendButton.click();

    // 发送按钮应显示加载状态
    await expect(sendButton).toBeDisabled();
  });

  test('输入框为空时发送按钮应禁用', async ({ page }) => {
    const sendButton = page.getByRole('button', { name: /发送/ });
    await expect(sendButton).toBeDisabled();
  });

  test('只有空白字符时发送按钮应禁用', async ({ page }) => {
    const textarea = page.getByRole('textbox', { name: /健康咨询输入框/ });
    const sendButton = page.getByRole('button', { name: /发送/ });

    await textarea.fill('   ');
    await expect(sendButton).toBeDisabled();
  });
});

/**
 * SSE 流式响应测试
 */
test.describe('流式响应处理', () => {
  test('应正确处理 status 事件', async ({ page }) => {
    await page.route('**/api/chat', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        headers: {
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        },
        body: [
          'event: status',
          'data: {"agent_name": "Controller_Agent", "progress": "正在分析请求...", "percentage": 10}',
          '',
          'event: status',
          'data: {"agent_name": "Nutrition_Agent", "progress": "营养分析中...", "percentage": 40}',
          '',
        ].join('\n'),
      });
    });

    await page.goto('/');
    
    const textarea = page.getByRole('textbox', { name: /健康咨询输入框/ });
    await textarea.fill('我血脂高');
    await page.getByRole('button', { name: /发送/ }).click();

    // 发送后应显示用户消息
    await expect(page.getByText('我血脂高')).toBeVisible({ timeout: 5000 });
  });

  test('应正确处理 report 事件并显示报告', async ({ page }) => {
    const mockReport = {
      deep_insight: '## 健康分析\n\n根据您的描述，您可能存在血脂代谢异常。',
      action_plan: [
        {
          category: '营养',
          title: '调整饮食结构',
          description: '减少饱和脂肪摄入，增加膳食纤维',
          frequency: '每日三餐',
          priority: '高',
          risk_level: '低风险',
          duration: '3个月',
        },
      ],
      follow_up: '建议2周后复查血脂指标',
      requires_confirmation: false,
      created_at: new Date().toISOString(),
      session_id: 'test-session-123',
      confirmation_status: 'pending',
    };

    await page.route('**/api/chat', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: [
          'event: report',
          `data: ${JSON.stringify(mockReport)}`,
          '',
        ].join('\n'),
      });
    });

    await page.goto('/');
    
    const textarea = page.getByRole('textbox', { name: /健康咨询输入框/ });
    await textarea.fill('我血脂高');
    await page.getByRole('button', { name: /发送/ }).click();

    // 应显示深度洞察（使用 first() 处理多个匹配元素）
    await expect(page.getByText(/健康分析/).first()).toBeVisible({ timeout: 10000 });
    
    // 应显示行动计划
    await expect(page.getByText('调整饮食结构')).toBeVisible();
    
    // 应显示随访计划
    await expect(page.getByText(/随访计划/)).toBeVisible();
  });

  test('应正确处理 error 事件', async ({ page }) => {
    await page.route('**/api/chat', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: [
          'event: error',
          'data: {"error_type": "internal_error", "error_message": "服务暂时不可用"}',
          '',
        ].join('\n'),
      });
    });

    await page.goto('/');
    
    const textarea = page.getByRole('textbox', { name: /健康咨询输入框/ });
    await textarea.fill('测试');
    await page.getByRole('button', { name: /发送/ }).click();

    // 应显示错误信息和重试按钮
    await expect(page.getByRole('button', { name: /重试/ })).toBeVisible({ timeout: 5000 });
  });
});

/**
 * 网络错误处理测试
 */
test.describe('网络错误处理', () => {
  test('网络请求失败时应显示错误提示', async ({ page }) => {
    await page.route('**/api/chat', async (route) => {
      await route.abort('failed');
    });

    await page.goto('/');
    
    const textarea = page.getByRole('textbox', { name: /健康咨询输入框/ });
    await textarea.fill('测试');
    await page.getByRole('button', { name: /发送/ }).click();

    // 应显示重试按钮
    await expect(page.getByRole('button', { name: /重试/ })).toBeVisible({ timeout: 5000 });
  });

  test('服务器错误时应显示错误提示', async ({ page }) => {
    await page.route('**/api/chat', async (route) => {
      await route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Internal Server Error' }),
      });
    });

    await page.goto('/');
    
    const textarea = page.getByRole('textbox', { name: /健康咨询输入框/ });
    await textarea.fill('测试');
    await page.getByRole('button', { name: /发送/ }).click();

    // 应显示重试按钮
    await expect(page.getByRole('button', { name: /重试/ })).toBeVisible({ timeout: 5000 });
  });
});
