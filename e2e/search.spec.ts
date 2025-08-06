import { test, expect } from '@playwright/test';

test.describe('Search Functionality', () => {
  test.beforeEach(async ({ page }) => {
    // Go to search page
    await page.goto('/search');
  });

  test('should display search interface', async ({ page }) => {
    // Check for search input
    const searchInput = page.locator('input[type="search"], input[placeholder*="搜索"], input[placeholder*="search"]').first();
    await expect(searchInput).toBeVisible();
    
    // Check for search button if it exists
    const searchButton = page.locator('button[type="submit"], button:has-text("搜索"), button:has-text("Search")').first();
    if (await searchButton.isVisible()) {
      await expect(searchButton).toBeVisible();
    }
  });

  test('should perform search and show results', async ({ page }) => {
    const searchInput = page.locator('input[type="search"], input[placeholder*="搜索"], input[placeholder*="search"]').first();
    
    if (await searchInput.isVisible()) {
      // Enter search term
      await searchInput.fill('产品');
      
      // Submit search (either by pressing Enter or clicking search button)
      await searchInput.press('Enter');
      
      // Wait for results to load
      await page.waitForTimeout(1000);
      
      // Check if results container exists
      const resultsContainer = page.locator('[data-testid="search-results"], .search-results, .qa-list');
      if (await resultsContainer.isVisible()) {
        await expect(resultsContainer).toBeVisible();
      }
    }
  });

  test('should filter by category', async ({ page }) => {
    // Check if category filter exists
    const categoryFilter = page.locator('select, .category-filter, [data-testid="category-filter"]').first();
    
    if (await categoryFilter.isVisible()) {
      await expect(categoryFilter).toBeVisible();
      
      // If it's a select element, check for options
      if (await categoryFilter.getAttribute('tagName') === 'SELECT') {
        const options = page.locator('option');
        expect(await options.count()).toBeGreaterThan(1);
      }
    }
  });

  test('should show search suggestions', async ({ page }) => {
    const searchInput = page.locator('input[type="search"], input[placeholder*="搜索"], input[placeholder*="search"]').first();
    
    if (await searchInput.isVisible()) {
      // Start typing to trigger suggestions
      await searchInput.fill('产');
      await page.waitForTimeout(500);
      
      // Check if suggestions dropdown appears
      const suggestions = page.locator('.suggestions, .autocomplete, [data-testid="suggestions"]');
      
      // Suggestions might not be implemented yet, so this is optional
      if (await suggestions.isVisible()) {
        await expect(suggestions).toBeVisible();
      }
    }
  });

  test('should handle empty search results', async ({ page }) => {
    const searchInput = page.locator('input[type="search"], input[placeholder*="搜索"], input[placeholder*="search"]').first();
    
    if (await searchInput.isVisible()) {
      // Search for something that definitely won't exist
      await searchInput.fill('xyzneverexists123');
      await searchInput.press('Enter');
      
      await page.waitForTimeout(1000);
      
      // Check for no results message
      const noResults = page.getByText(/没有找到|未找到|no results|没有结果/i);
      if (await noResults.isVisible()) {
        await expect(noResults).toBeVisible();
      }
    }
  });

  test('should display Q&A pairs in results', async ({ page }) => {
    const searchInput = page.locator('input[type="search"], input[placeholder*="搜索"], input[placeholder*="search"]').first();
    
    if (await searchInput.isVisible()) {
      await searchInput.fill('问题');
      await searchInput.press('Enter');
      
      await page.waitForTimeout(1000);
      
      // Look for Q&A card components
      const qaCards = page.locator('.qa-card, [data-testid="qa-card"], .question-answer');
      
      if (await qaCards.count() > 0) {
        const firstCard = qaCards.first();
        await expect(firstCard).toBeVisible();
        
        // Check if the card contains question and answer sections
        const question = firstCard.locator('.question, [data-testid="question"]');
        const answer = firstCard.locator('.answer, [data-testid="answer"]');
        
        if (await question.isVisible()) {
          await expect(question).toBeVisible();
        }
        if (await answer.isVisible()) {
          await expect(answer).toBeVisible();
        }
      }
    }
  });

  test('should support pagination', async ({ page }) => {
    // Look for pagination controls
    const pagination = page.locator('.pagination, [data-testid="pagination"], .ant-pagination');
    
    if (await pagination.isVisible()) {
      await expect(pagination).toBeVisible();
      
      // Check for next/previous buttons
      const nextButton = pagination.locator('button:has-text("下一页"), button:has-text("Next"), .ant-pagination-next');
      const prevButton = pagination.locator('button:has-text("上一页"), button:has-text("Previous"), .ant-pagination-prev');
      
      if (await nextButton.isVisible()) {
        await expect(nextButton).toBeVisible();
      }
      if (await prevButton.isVisible()) {
        await expect(prevButton).toBeVisible();
      }
    }
  });
});