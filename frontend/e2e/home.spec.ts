import { test, expect } from '@playwright/test';

/**
 * 首页加载和基础 UI 测试
 */
test.describe('首页基础功能', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('页面应正确加载并显示标题', async ({ page }) => {
    // 检查页面标题
    await expect(page).toHaveTitle(/健康智能助手/);

    // 检查页面头部
    const header = page.locator('header');
    await expect(header).toBeVisible();
    await expect(header.getByText('健康顾问')).toBeVisible();
  });

  test('应显示欢迎界面和功能介绍卡片', async ({ page }) => {
    // 检查欢迎标题
    await expect(page.getByRole('heading', { name: '欢迎使用健康顾问' })).toBeVisible();

    // 检查功能介绍卡片
    await expect(page.getByText('营养专家')).toBeVisible();
    await expect(page.getByText('康复专家')).toBeVisible();
    await expect(page.getByText('心理专家')).toBeVisible();
  });

  test('应显示聊天输入框', async ({ page }) => {
    // 检查输入框
    const textarea = page.getByRole('textbox', { name: /健康咨询输入框/ });
    await expect(textarea).toBeVisible();
    await expect(textarea).toBeEnabled();

    // 检查发送按钮
    const sendButton = page.getByRole('button', { name: /发送/ });
    await expect(sendButton).toBeVisible();
    await expect(sendButton).toBeDisabled(); // 输入为空时按钮应禁用
  });

  test('应显示连接状态指示器', async ({ page }) => {
    // 检查连接状态显示
    const connectionStatus = page.locator('header').getByText(/已连接|未连接|重连中/);
    await expect(connectionStatus).toBeVisible();
  });

  test('输入文本后发送按钮应启用', async ({ page }) => {
    const textarea = page.getByRole('textbox', { name: /健康咨询输入框/ });
    const sendButton = page.getByRole('button', { name: /发送/ });

    // 初始状态：按钮禁用
    await expect(sendButton).toBeDisabled();

    // 输入文本后：按钮启用
    await textarea.fill('测试消息');
    await expect(sendButton).toBeEnabled();

    // 清空文本后：按钮禁用
    await textarea.fill('');
    await expect(sendButton).toBeDisabled();
  });

  test('页面应有正确的可访问性结构', async ({ page }) => {
    // 检查 header 标签
    await expect(page.locator('header')).toBeVisible();

    // 检查 main 标签（页面可能有嵌套的 main，检查至少存在一个）
    await expect(page.locator('main').first()).toBeVisible();

    // 检查输入框有 aria-label
    const textarea = page.getByRole('textbox', { name: /健康咨询输入框/ });
    await expect(textarea).toHaveAttribute('aria-label');
  });

  test('页面应响应式布局 - 移动端', async ({ page }) => {
    // 设置移动端视口
    await page.setViewportSize({ width: 375, height: 667 });

    // 页面内容应仍然可见
    await expect(page.getByRole('heading', { name: '欢迎使用健康顾问' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: /健康咨询输入框/ })).toBeVisible();
  });

  test('页面应响应式布局 - 桌面端', async ({ page }) => {
    // 设置桌面端视口
    await page.setViewportSize({ width: 1440, height: 900 });

    // 页面内容应仍然可见
    await expect(page.getByRole('heading', { name: '欢迎使用健康顾问' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: /健康咨询输入框/ })).toBeVisible();
  });
});

/**
 * 页面底部提示测试
 */
test.describe('页面提示信息', () => {
  test('应显示免责声明', async ({ page }) => {
    await page.goto('/');
    
    await expect(
      page.getByText(/本系统仅提供健康参考建议，不构成医疗诊断/)
    ).toBeVisible();
  });

  test('应显示输入提示', async ({ page }) => {
    await page.goto('/');
    
    await expect(
      page.getByText(/按 Enter 发送，Shift \+ Enter 换行/)
    ).toBeVisible();
  });
});
