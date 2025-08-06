/**
 * API 适配器 - 兼容现有的 API 接口，从 Flask API 迁移到 Supabase
 * 
 * 这个文件提供了一个适配层，使现有的前端代码可以无缝迁移到 Supabase
 * 保持与原有 API 相同的接口，但底层使用 Supabase
 */

import { supabaseAPI } from './supabase-api'
import { testSupabaseConnection } from '../lib/supabase'
import type { Category, QAPair, SearchParams } from '../lib/supabase'

// 兼容原有的类型定义
export interface APIResponse<T> {
  data: T
  total?: number
  page?: number
  pages?: number
  success?: boolean
  message?: string
}

export interface SearchFilters {
  category_id?: number
  advisor?: string
}

export interface UploadResponse {
  upload_id: number
  processed_count: number
  total_count: number
  status: string
  qa_pairs?: QAPair[]
}

class APIAdapter {
  private supabaseConnected = false
  private connectionTested = false
  
  /**
   * 初始化时测试 Supabase 连接
   */
  private async ensureConnection() {
    if (!this.connectionTested) {
      this.supabaseConnected = await testSupabaseConnection()
      this.connectionTested = true
      
      if (!this.supabaseConnected) {
        console.warn('⚠️ Supabase not connected. Using fallback mode.')
      }
    }
  }

  /**
   * 通用错误处理
   */
  private handleError<T>(error: any, fallbackData: T): APIResponse<T> {
    console.error('API Error:', error)
    return {
      data: fallbackData,
      success: false,
      message: error.message || 'Unknown error occurred'
    }
  }

  /**
   * 提供默认数据（当 Supabase 未连接时）
   */
  private getDefaultCategories(): Category[] {
    return [
      { id: 1, name: '产品咨询', description: '产品相关问题', color: '#1890ff', qa_count: 0, created_at: '', updated_at: '' },
      { id: 2, name: '技术支持', description: '技术问题解答', color: '#f5222d', qa_count: 0, created_at: '', updated_at: '' },
      { id: 3, name: '价格费用', description: '价格和费用咨询', color: '#52c41a', qa_count: 0, created_at: '', updated_at: '' },
      { id: 4, name: '使用教程', description: '使用方法指导', color: '#faad14', qa_count: 0, created_at: '', updated_at: '' },
      { id: 5, name: '售后问题', description: '售后服务相关', color: '#722ed1', qa_count: 0, created_at: '', updated_at: '' }
    ]
  }

  // ==================== 分类 API ====================

  async getCategories(): Promise<APIResponse<Category[]>> {
    await this.ensureConnection()
    
    if (!this.supabaseConnected) {
      return {
        data: this.getDefaultCategories(),
        success: true
      }
    }

    try {
      const { data, error } = await supabaseAPI.getCategories()
      
      if (error) {
        return this.handleError(error, this.getDefaultCategories())
      }
      
      return {
        data: data || [],
        success: true
      }
    } catch (error) {
      return this.handleError(error, this.getDefaultCategories())
    }
  }

  // ==================== 问答 API ====================

  async getQAPairs(params: {
    page?: number
    limit?: number
    category?: string | number
  } = {}): Promise<APIResponse<QAPair[]>> {
    await this.ensureConnection()
    
    if (!this.supabaseConnected) {
      return {
        data: [],
        total: 0,
        success: true,
        message: '演示模式：Supabase 未连接'
      }
    }

    try {
      const { page = 1, limit = 20, category } = params
      const category_id = category ? Number(category) : undefined
      
      const { data, error, count } = await supabaseAPI.getQAPairs({
        page,
        limit,
        category_id
      })
      
      if (error) {
        return this.handleError(error, [])
      }
      
      return {
        data: data || [],
        total: count || 0,
        page,
        pages: Math.ceil((count || 0) / limit),
        success: true
      }
    } catch (error) {
      return this.handleError(error, [])
    }
  }

  async searchQAPairs(query: string, filters?: SearchFilters, page = 1, limit = 20): Promise<APIResponse<QAPair[]>> {
    await this.ensureConnection()
    
    if (!this.supabaseConnected) {
      return {
        data: [],
        total: 0,
        success: true,
        message: '演示模式：Supabase 未连接，请配置 Supabase 以使用搜索功能'
      }
    }

    try {
      const searchParams: SearchParams = {
        query: query.trim(),
        category_id: filters?.category_id,
        advisor: filters?.advisor,
        page,
        limit
      }
      
      const { data, error, count } = await supabaseAPI.searchQAPairs(searchParams)
      
      if (error) {
        return this.handleError(error, [])
      }
      
      return {
        data: data || [],
        total: count || 0,
        page,
        pages: Math.ceil((count || 0) / limit),
        success: true
      }
    } catch (error) {
      return this.handleError(error, [])
    }
  }

  // ==================== 统计 API ====================

  async getStatistics(): Promise<APIResponse<any>> {
    await this.ensureConnection()
    
    if (!this.supabaseConnected) {
      return {
        data: {
          total_qa: 0,
          total_categories: 5,
          categories_with_count: this.getDefaultCategories().map(cat => ({
            ...cat,
            qa_count: 0
          })),
          top_advisors: [],
          confidence_stats: {
            average: 0,
            high_confidence: 0,
            medium_confidence: 0,
            low_confidence: 0
          }
        },
        success: true,
        message: '演示模式数据'
      }
    }

    try {
      const { data, error } = await supabaseAPI.getStatistics()
      
      if (error) {
        return this.handleError(error, {})
      }
      
      return {
        data: data || {},
        success: true
      }
    } catch (error) {
      return this.handleError(error, {})
    }
  }

  // ==================== 上传 API ====================

  async uploadFile(file: File): Promise<APIResponse<UploadResponse>> {
    await this.ensureConnection()
    
    if (!this.supabaseConnected) {
      return {
        data: {
          upload_id: 0,
          processed_count: 0,
          total_count: 0,
          status: 'failed'
        },
        success: false,
        message: '演示模式：文件上传需要配置 Supabase Edge Functions'
      }
    }

    // TODO: 实现文件上传逻辑 (将在 Edge Functions 中处理)
    return {
      data: {
        upload_id: Date.now(),
        processed_count: 0,
        total_count: 0,
        status: 'pending'
      },
      success: true,
      message: '文件上传功能正在开发中...'
    }
  }

  // ==================== 实时订阅 ====================

  subscribeToUpdates(callback: (data: any) => void) {
    if (!this.supabaseConnected) {
      console.warn('实时订阅需要 Supabase 连接')
      return null
    }

    return supabaseAPI.subscribeToQAUpdates((payload) => {
      console.log('实时更新:', payload)
      callback(payload)
    })
  }

  // ==================== 工具方法 ====================

  async healthCheck(): Promise<{ status: string; supabase: boolean }> {
    await this.ensureConnection()
    
    return {
      status: this.supabaseConnected ? 'connected' : 'disconnected',
      supabase: this.supabaseConnected
    }
  }
}

// 导出单例实例
export const apiAdapter = new APIAdapter()
export default apiAdapter

// 为了兼容现有代码，保留原来的 api 导出
export { apiAdapter as api }