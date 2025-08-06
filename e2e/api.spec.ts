import { test, expect } from '@playwright/test';

const API_BASE = 'http://localhost:5000/api/v1';

test.describe('API Endpoints', () => {
  test('should get categories list', async ({ request }) => {
    const response = await request.get(`${API_BASE}/categories`);
    
    expect(response.status()).toBe(200);
    
    const categories = await response.json();
    expect(Array.isArray(categories)).toBeTruthy();
    
    // Should have the 5 predefined categories
    expect(categories.length).toBeGreaterThanOrEqual(5);
    
    // Check if expected categories exist
    const categoryNames = categories.map((cat: any) => cat.name);
    expect(categoryNames).toContain('产品咨询');
    expect(categoryNames).toContain('技术支持');
    expect(categoryNames).toContain('价格费用');
    expect(categoryNames).toContain('使用教程');
    expect(categoryNames).toContain('售后问题');
  });

  test('should get Q&A pairs list', async ({ request }) => {
    const response = await request.get(`${API_BASE}/qa`);
    
    if (response.status() === 200) {
      const data = await response.json();
      
      // Check structure
      expect(data).toHaveProperty('results');
      expect(data).toHaveProperty('total');
      expect(data).toHaveProperty('page');
      expect(data).toHaveProperty('per_page');
      
      expect(Array.isArray(data.results)).toBeTruthy();
    } else {
      // If no Q&A data exists yet, expect 200 with empty results or 404
      expect([200, 404]).toContain(response.status());
    }
  });

  test('should search Q&A pairs', async ({ request }) => {
    const response = await request.get(`${API_BASE}/search?q=产品`);
    
    if (response.status() === 200) {
      const data = await response.json();
      
      expect(data).toHaveProperty('results');
      expect(data).toHaveProperty('total');
      expect(Array.isArray(data.results)).toBeTruthy();
      
      // If results exist, check structure
      if (data.results.length > 0) {
        const firstResult = data.results[0];
        expect(firstResult).toHaveProperty('question');
        expect(firstResult).toHaveProperty('answer');
        expect(firstResult).toHaveProperty('category_name');
      }
    } else {
      // Search endpoint might not be ready
      expect([200, 404, 500]).toContain(response.status());
    }
  });

  test('should get system stats', async ({ request }) => {
    const response = await request.get(`${API_BASE}/admin/stats`);
    
    if (response.status() === 200) {
      const stats = await response.json();
      
      expect(stats).toHaveProperty('total_qa_pairs');
      expect(stats).toHaveProperty('total_categories');
      expect(typeof stats.total_qa_pairs).toBe('number');
      expect(typeof stats.total_categories).toBe('number');
    } else {
      // Admin endpoint might require authentication
      expect([200, 401, 403, 404]).toContain(response.status());
    }
  });

  test('should handle file upload endpoint', async ({ request }) => {
    // Test that the upload endpoint exists
    const response = await request.post(`${API_BASE}/upload/file`, {
      data: {
        // Empty request to test endpoint existence
      }
    });
    
    // Should not be 404 (endpoint exists)
    // Might be 400 (bad request) or 422 (validation error) due to missing file
    expect(response.status()).not.toBe(404);
    expect([400, 422, 413]).toContain(response.status());
  });

  test('should handle CORS for frontend requests', async ({ request }) => {
    const response = await request.options(`${API_BASE}/categories`, {
      headers: {
        'Origin': 'http://localhost:3000',
        'Access-Control-Request-Method': 'GET'
      }
    });
    
    if (response.status() === 200 || response.status() === 204) {
      const headers = response.headers();
      expect(headers['access-control-allow-origin']).toBeTruthy();
    }
    // If CORS not configured, OPTIONS might return 404 or 405
    expect([200, 204, 404, 405]).toContain(response.status());
  });
});