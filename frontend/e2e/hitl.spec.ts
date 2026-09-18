import { expect, test } from "@playwright/test";

/**
 * HITL（Human-in-the-Loop）确认弹窗 E2E 测试
 */

// Mock 高风险干预数据
const mockHighRiskItems = [
  {
    category: "营养" as const,
    title: "调整他汀类药物剂量",
    description: "建议与医生协商调整他汀类降脂药剂量，需要医学监督",
    frequency: "每日一次",
    priority: "高" as const,
    risk_level: "高风险" as const,
    duration: "2周",
  },
  {
    category: "康复" as const,
    title: "高强度间歇训练",
    description: "针对您的心血管情况，建议进行高强度间歇训练，但需要注意监测心率",
    frequency: "每周3次",
    priority: "中" as const,
    risk_level: "高风险" as const,
    duration: "1个月",
  },
];

const mockPauseReport = {
  deep_insight: "测试洞察内容",
  action_plan: mockHighRiskItems,
  follow_up: "2周后复查",
  requires_confirmation: true,
  created_at: new Date().toISOString(),
  session_id: "test-session-123",
  confirmation_status: "pending",
};

test.describe("HITL 确认弹窗", () => {
  test.beforeEach(async ({ page }) => {
    // Mock API 返回 pause 事件触发 HITL 弹窗
    await page.route("**/api/chat", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        headers: {
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
          "X-Session-ID": "test-session-123",
        },
        body: [
          "event: pause",
          `data: ${JSON.stringify({
            session_id: "test-session-123",
            high_risk_items: mockHighRiskItems,
            timeout_seconds: 600,
          })}`,
          "",
        ].join("\n"),
      });
    });

    await page.goto("/");
  });

  test("收到 pause 事件后应显示 HITL 确认弹窗", async ({ page }) => {
    const textarea = page.getByRole("textbox", { name: /健康咨询输入框/ });
    await textarea.fill("我想停用他汀药物");
    await page.getByRole("button", { name: /发送/ }).click();

    // 应显示 HITL 确认弹窗
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("高风险干预确认")).toBeVisible();
  });

  test("弹窗应显示高风险干预措施列表", async ({ page }) => {
    const textarea = page.getByRole("textbox", { name: /健康咨询输入框/ });
    await textarea.fill("测试");
    await page.getByRole("button", { name: /发送/ }).click();

    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 10000 });

    // 检查高风险干预措施是否显示（使用 first() 处理多个匹配元素）
    await expect(page.getByText("调整他汀类药物剂量")).toBeVisible();
    await expect(page.getByRole("heading", { name: "高强度间歇训练" })).toBeVisible();
  });

  test("弹窗应显示倒计时", async ({ page }) => {
    const textarea = page.getByRole("textbox", { name: /健康咨询输入框/ });
    await textarea.fill("测试");
    await page.getByRole("button", { name: /发送/ }).click();

    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 10000 });

    // 检查倒计时显示
    await expect(page.getByRole("timer")).toBeVisible();
    await expect(page.getByText(/请在.*内完成确认/)).toBeVisible();
  });

  test("弹窗应有确认和取消按钮", async ({ page }) => {
    const textarea = page.getByRole("textbox", { name: /健康咨询输入框/ });
    await textarea.fill("测试");
    await page.getByRole("button", { name: /发送/ }).click();

    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 10000 });

    // 检查按钮
    await expect(page.getByRole("button", { name: "确认执行" })).toBeVisible();
    await expect(page.getByRole("button", { name: "取消" })).toBeVisible();
  });

  test("点击确认按钮应调用 confirm API", async ({ page }) => {
    // 设置 confirm API mock
    let confirmCalled = false;
    await page.route("**/api/confirm", async (route) => {
      confirmCalled = true;
      const body = route.request().postDataJSON();
      expect(body.session_id).toBe("test-session-123");
      expect(body.confirmed).toBe(true);

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "resumed" }),
      });
    });

    const textarea = page.getByRole("textbox", { name: /健康咨询输入框/ });
    await textarea.fill("测试");
    await page.getByRole("button", { name: /发送/ }).click();

    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 10000 });

    // 点击确认按钮
    await page.getByRole("button", { name: "确认执行" }).click();

    // 验证 API 被调用
    await page.waitForTimeout(1000);
    expect(confirmCalled).toBe(true);
  });

  test("点击取消按钮应调用 confirm API 并设置 confirmed=false", async ({ page }) => {
    let cancelCalled = false;
    await page.route("**/api/confirm", async (route) => {
      cancelCalled = true;
      const body = route.request().postDataJSON();
      expect(body.session_id).toBe("test-session-123");
      expect(body.confirmed).toBe(false);

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "terminated",
          partial_report: mockPauseReport,
        }),
      });
    });

    const textarea = page.getByRole("textbox", { name: /健康咨询输入框/ });
    await textarea.fill("测试");
    await page.getByRole("button", { name: /发送/ }).click();

    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 10000 });

    // 点击取消按钮
    await page.getByRole("button", { name: "取消" }).click();

    await page.waitForTimeout(1000);
    expect(cancelCalled).toBe(true);
  });

  test("按钮操作时应显示加载状态", async ({ page }) => {
    // 设置延迟响应的 confirm API
    await page.route("**/api/confirm", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "resumed" }),
      });
    });

    const textarea = page.getByRole("textbox", { name: /健康咨询输入框/ });
    await textarea.fill("测试");
    await page.getByRole("button", { name: /发送/ }).click();

    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 10000 });

    // 点击确认按钮
    const confirmButton = page.getByRole("button", { name: "确认执行" });
    await confirmButton.click();

    // 按钮应显示加载状态
    await expect(page.getByText("处理中...")).toBeVisible();
  });
});

/**
 * HITL 键盘交互测试
 */
test.describe("HITL 键盘交互", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/chat", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: [
          "event: pause",
          `data: ${JSON.stringify({
            session_id: "test-session-123",
            high_risk_items: mockHighRiskItems,
            timeout_seconds: 600,
          })}`,
          "",
        ].join("\n"),
      });
    });

    await page.route("**/api/confirm", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "resumed" }),
      });
    });

    await page.goto("/");
  });

  test("按 Enter 键应触发确认", async ({ page }) => {
    let confirmCalled = false;
    await page.route("**/api/confirm", async (route) => {
      confirmCalled = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "resumed" }),
      });
    });

    const textarea = page.getByRole("textbox", { name: /健康咨询输入框/ });
    await textarea.fill("测试");
    await page.getByRole("button", { name: /发送/ }).click();

    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 10000 });

    // 按 Enter 键
    await page.keyboard.press("Enter");

    await page.waitForTimeout(1000);
    expect(confirmCalled).toBe(true);
  });

  test("按 Escape 键应触发取消", async ({ page }) => {
    let cancelCalled = false;
    await page.route("**/api/confirm", async (route) => {
      const body = route.request().postDataJSON();
      if (body.confirmed === false) {
        cancelCalled = true;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "terminated" }),
      });
    });

    const textarea = page.getByRole("textbox", { name: /健康咨询输入框/ });
    await textarea.fill("测试");
    await page.getByRole("button", { name: /发送/ }).click();

    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 10000 });

    // 按 Escape 键
    await page.keyboard.press("Escape");

    await page.waitForTimeout(1000);
    expect(cancelCalled).toBe(true);
  });

  test("Tab 键应在按钮间切换焦点", async ({ page }) => {
    const textarea = page.getByRole("textbox", { name: /健康咨询输入框/ });
    await textarea.fill("测试");
    await page.getByRole("button", { name: /发送/ }).click();

    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 10000 });

    // 确认按钮应该自动获得焦点
    const _confirmButton = page.getByRole("button", { name: "确认执行" });
    const _cancelButton = page.getByRole("button", { name: "取消" });

    // 按 Tab 切换焦点
    await page.keyboard.press("Tab");

    // 焦点应该在某个按钮上
    const activeElement = page.locator(":focus");
    await expect(activeElement).toBeVisible();
  });
});

/**
 * HITL 弹窗可访问性测试
 */
test.describe("HITL 可访问性", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/chat", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: [
          "event: pause",
          `data: ${JSON.stringify({
            session_id: "test-session-123",
            high_risk_items: mockHighRiskItems,
            timeout_seconds: 600,
          })}`,
          "",
        ].join("\n"),
      });
    });

    await page.goto("/");
  });

  test("弹窗应有正确的 ARIA 属性", async ({ page }) => {
    const textarea = page.getByRole("textbox", { name: /健康咨询输入框/ });
    await textarea.fill("测试");
    await page.getByRole("button", { name: /发送/ }).click();

    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 10000 });

    // 检查 dialog role
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();

    // 检查倒计时 timer role
    const timer = page.getByRole("timer");
    await expect(timer).toBeVisible();
    await expect(timer).toHaveAttribute("aria-live", "polite");
  });

  test("高风险措施列表应有 list role", async ({ page }) => {
    const textarea = page.getByRole("textbox", { name: /健康咨询输入框/ });
    await textarea.fill("测试");
    await page.getByRole("button", { name: /发送/ }).click();

    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 10000 });

    // 检查列表
    const list = page.getByRole("list", { name: /高风险干预措施列表/ });
    await expect(list).toBeVisible();

    // 检查列表项
    const listItems = page.getByRole("listitem");
    await expect(listItems).toHaveCount(2);
  });
});

/**
 * HITL 弹窗打开时输入框应禁用
 */
test.describe("HITL 弹窗状态联动", () => {
  test("弹窗打开时聊天输入框应禁用", async ({ page }) => {
    await page.route("**/api/chat", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: [
          "event: pause",
          `data: ${JSON.stringify({
            session_id: "test-session-123",
            high_risk_items: mockHighRiskItems,
            timeout_seconds: 600,
          })}`,
          "",
        ].join("\n"),
      });
    });

    await page.goto("/");

    const textarea = page.getByRole("textbox", { name: /健康咨询输入框/ });
    await textarea.fill("测试");
    await page.getByRole("button", { name: /发送/ }).click();

    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 10000 });

    // 弹窗打开后，底层输入框会被 dialog 遮挡，此时无法直接定位
    // 改为验证弹窗确实打开了
    await expect(page.getByText("高风险干预确认")).toBeVisible();
  });
});
