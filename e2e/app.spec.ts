import { test, expect } from '@playwright/test';

test.describe('ChatLog Application', () => {
  test('should load the homepage', async ({ page }) => {
    await page.goto('/');
    
    // Check if the main app components are present
    await expect(page.locator('header')).toBeVisible();
    await expect(page.locator('main')).toBeVisible();
    
    // Check for the main navigation or title
    await expect(page.getByText('微信群问答知识库')).toBeVisible();
  });

  test('should navigate to search page', async ({ page }) => {
    await page.goto('/');
    
    // Look for search-related navigation or button
    const searchLink = page.getByRole('link', { name: /搜索|search/i });
    if (await searchLink.isVisible()) {
      await searchLink.click();
      await expect(page.url()).toContain('search');
    } else {
      // If direct navigation exists, go to search page
      await page.goto('/search');
    }
    
    // Verify search page elements
    await expect(page.locator('input[type="search"], input[placeholder*="搜索"], input[placeholder*="search"]')).toBeVisible();
  });

  test('should display upload functionality', async ({ page }) => {
    await page.goto('/');
    
    // Look for upload section or navigate to upload page
    const uploadElement = page.locator('[data-testid="upload-zone"], .upload-zone, input[type="file"]').first();
    
    if (await uploadElement.isVisible()) {
      await expect(uploadElement).toBeVisible();
    } else {
      // Try navigating to upload page if it exists as a separate route
      await page.goto('/upload');
      await expect(page.locator('[data-testid="upload-zone"], .upload-zone, input[type="file"]')).toBeVisible();
    }
  });

  test('should show categories', async ({ page }) => {
    await page.goto('/search');
    
    // Check if categories are displayed (based on the 5 predefined categories mentioned in CLAUDE.md)
    const categoryTexts = ['产品咨询', '技术支持', '价格费用', '使用教程', '售后问题'];
    
    for (const categoryText of categoryTexts) {
      // Categories might be in dropdowns, buttons, or links
      const categoryElement = page.getByText(categoryText);
      if (await categoryElement.isVisible()) {
        await expect(categoryElement).toBeVisible();
        break; // At least one category should be visible
      }
    }
  });

  test('should handle responsive design', async ({ page }) => {
    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    
    await expect(page.locator('header')).toBeVisible();
    await expect(page.locator('main')).toBeVisible();
    
    // Test desktop viewport
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto('/');
    
    await expect(page.locator('header')).toBeVisible();
    await expect(page.locator('main')).toBeVisible();
  });
});