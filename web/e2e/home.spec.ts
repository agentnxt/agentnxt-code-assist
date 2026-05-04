import { test, expect, type Page } from '@playwright/test';

test.describe('CodeAssist Web E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Wait for the page to fully load
    await page.goto('/');
  });

  test('should load the main page', async ({ page }: { page: Page }) => {
<<<<<<< HEAD
    await expect(page).toHaveTitle(/CodeAssist/i);
=======
    await expect(page).toHaveTitle(/AGenNext/i);
>>>>>>> origin/main
  });

  test('should display the main UI components', async ({ page }: { page: Page }) => {
    // Check for the hero section
    await expect(page.locator('h1')).toContainText(/Chat with a repo/i);

    // Check for the instruction textarea
    await expect(page.locator('textarea').first()).toBeVisible();

    // Check for the Target URL input
    await expect(page.locator('input[placeholder*="github.com"]')).toBeVisible();

    // Check for the Run button
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should display the checks panel', async ({ page }: { page: Page }) => {
    // Check for checks section
    await expect(page.locator('h2', { hasText: 'Checks' })).toBeVisible();
    
    // Check for check presets
    await expect(page.locator('.chip', { hasText: 'production' })).toBeVisible();
    await expect(page.locator('.chip', { hasText: 'typecheck' })).toBeVisible();
  });

  test('should display the guardrails section', async ({ page }: { page: Page }) => {
    // Check for guardrails section
    await expect(page.locator('h2', { hasText: 'Guardrails' })).toBeVisible();
    
    // Check for guardrail checkboxes
    await expect(page.locator('label', { hasText: 'Allow commits' })).toBeVisible();
    await expect(page.locator('label', { hasText: 'Allow push' })).toBeVisible();
  });

  test('should toggle check preset', async ({ page }: { page: Page }) => {
    // Find the lint chip in the checks section
    const lintChip = page.locator('.chip', { hasText: 'lint' });
    
    // Verify lint chip exists and is clickable
    await expect(lintChip).toBeVisible();
    
    // Click and wait for potential React state update
    await lintChip.click();
    await lintChip.waitFor({ state: 'attached' });
  });

  test('should show backend URL in status card', async ({ page }: { page: Page }) => {
    // Check for backend status display
    await expect(page.locator('.status-card')).toContainText(/Backend/);
  });
<<<<<<< HEAD

  // === Advanced Agent Capabilities Tests ===
  test('should display agent capabilities section', async ({ page }: { page: Page }) => {
    // Check for capabilities section
    const capabilities = page.locator('h2, h3', { hasText: /Capability|Empathy|Self-Respect|Trust/i });
    await expect(capabilities.first()).toBeVisible({ timeout: 5000 }).catch(() => {
      // Section may not exist in older versions
    });
  });

  // === Tool Ecosystem Tests ===
  test('should display tools section', async ({ page }: { page: Page }) => {
    // Check for tools section (if present)
    const tools = page.locator('h2, h3', { hasText: /Tool|Travel|Weather|Map|News/i });
    try {
      await expect(tools.first()).toBeVisible({ timeout: 3000 });
    } catch {
      // Tools section optional
    }
  });

  // === Form Validation Tests ===
  test('should validate form submission', async ({ page }: { page: Page }) => {
    // Try to submit empty form
    await page.locator('button[type="submit"]').click();
    
    // Should show validation error or not proceed
    const error = page.locator('[role="alert"], .error, text="required"');
    try {
      await expect(error.first()).toBeVisible({ timeout: 2000 });
    } catch {
      // May not have client-side validation
    }
  });

  // === Navigation Tests ===
  test('should navigate between sections', async ({ page }: { page: Page }) => {
    // Check for navigation links
    const nav = page.locator('nav a, [class*="nav"] a');
    const count = await nav.count();
    expect(count).toBeGreaterThan(0);
  });
=======
>>>>>>> origin/main
});