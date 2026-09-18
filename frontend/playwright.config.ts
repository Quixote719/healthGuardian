import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E 测试配置
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  // 测试文件目录
  testDir: './e2e',
  
  // 每个测试的超时时间
  timeout: 30 * 1000,
  
  // 期望超时
  expect: {
    timeout: 5000,
  },
  
  // 并行运行测试
  fullyParallel: true,
  
  // CI 环境下失败时不重试
  forbidOnly: !!process.env.CI,
  
  // 重试次数
  retries: process.env.CI ? 2 : 0,
  
  // 并行 worker 数量
  workers: process.env.CI ? 1 : undefined,
  
  // 测试报告
  reporter: [
    ['html', { open: 'never' }],
    ['list'],
  ],
  
  // 全局配置
  use: {
    // 基础 URL
    baseURL: 'http://localhost:3000',
    
    // 收集失败测试的 trace
    trace: 'on-first-retry',
    
    // 截图策略
    screenshot: 'only-on-failure',
    
    // 视频录制
    video: 'on-first-retry',
  },

  // 配置测试项目（浏览器）
  projects: [
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        // 使用系统 Chrome（如果 Playwright 浏览器下载失败）
        channel: 'chrome',
      },
    },
  ],

  // 测试前启动开发服务器
  webServer: {
    command: 'pnpm dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});
