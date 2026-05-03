import { test, expect, type Page } from '@playwright/test';

test.describe('CodeAssist Web E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Wait for the page to fully load
    await page.goto('/');
  });

  test('should load the main page', async ({ page }: { page: Page }) => {
    await expect(page).toHaveTitle(/AGenNext/i);
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
    // Click on lint chip
    const lintChip = page.locator('.chip', { hasText: 'lint' });
    await lintChip.click();
    
    // Check it becomes selected
    await expect(lintChip).toHaveClass(/selected/);
  });

  test('should show backend URL in status card', async ({ page }: { page: Page }) => {
    // Check for backend status display
    await expect(page.locator('.status-card')).toContainText(/Backend/);
  });
});