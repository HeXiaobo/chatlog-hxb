import { supabase } from '../lib/supabase'
import type { 
  Category, 
  QAPair, 
  UploadHistory, 
  SearchResult, 
  Statistics, 
  SearchParams, 
  ApiResponse 
} from '../lib/supabase'

class SupabaseAPI {
  // ==================== 分类相关 ====================
  
  /**
   * 获取所有分类
   */
  async getCategories(): Promise<ApiResponse<Category[]>> {
    try {
      const { data, error, count } = await supabase
        .from('categories')
        .select('*')
        .order('name')
      
      if (error) throw error
      
      return { data, error: null, count }
    } catch (error) {
      console.error('获取分类失败:', error)
      return { data: null, error }
    }
  }

  /**
   * 创建分类
   */
  async createCategory(category: Partial<Category>): Promise<ApiResponse<Category>> {
    try {
      const { data, error } = await supabase
        .from('categories')
        .insert([category])
        .select()
        .single()
      
      if (error) throw error
      
      return { data, error: null }
    } catch (error) {
      console.error('创建分类失败:', error)
      return { data: null, error }
    }
  }

  /**
   * 更新分类
   */
  async updateCategory(id: number, updates: Partial<Category>): Promise<ApiResponse<Category>> {
    try {
      const { data, error } = await supabase
        .from('categories')
        .update(updates)
        .eq('id', id)
        .select()
        .single()
      
      if (error) throw error
      
      return { data, error: null }
    } catch (error) {
      console.error('更新分类失败:', error)
      return { data: null, error }
    }
  }

  // ==================== 问答对相关 ====================

  /**
   * 获取问答列表 (基础查询)
   */
  async getQAPairs(params: {
    page?: number
    limit?: number
    category_id?: number
    advisor?: string
  } = {}): Promise<ApiResponse<QAPair[]>> {
    try {
      const { page = 1, limit = 20, category_id, advisor } = params
      
      let query = supabase
        .from('qa_pairs')
        .select(`
          *,
          categories (
            id, name, color, description
          )
        `)
      
      // 分类筛选
      if (category_id) {
        query = query.eq('category_id', category_id)
      }
      
      // 回答者筛选
      if (advisor) {
        query = query.ilike('advisor', `%${advisor}%`)
      }
      
      const { data, error, count } = await query
        .order('created_at', { ascending: false })
        .range((page - 1) * limit, page * limit - 1)
      
      if (error) throw error
      
      return { data, error: null, count }
    } catch (error) {
      console.error('获取问答列表失败:', error)
      return { data: null, error }
    }
  }

  /**
   * 搜索问答 (使用 PostgreSQL 全文搜索)
   */
  async searchQAPairs(params: SearchParams): Promise<ApiResponse<SearchResult[]>> {
    try {
      const { 
        query = '', 
        category_id, 
        advisor, 
        page = 1, 
        limit = 20 
      } = params
      
      // 使用自定义函数进行搜索
      const { data, error } = await supabase
        .rpc('search_qa_pairs', {
          search_query: query,
          category_filter: category_id || null,
          advisor_filter: advisor || null,
          limit_count: limit,
          offset_count: (page - 1) * limit
        })
      
      if (error) throw error
      
      // 获取总数
      const { data: totalCount, error: countError } = await supabase
        .rpc('count_qa_pairs', {
          search_query: query,
          category_filter: category_id || null,
          advisor_filter: advisor || null
        })
      
      if (countError) {
        console.warn('获取搜索总数失败:', countError)
      }
      
      return { 
        data, 
        error: null, 
        count: totalCount || 0 
      }
    } catch (error) {
      console.error('搜索问答失败:', error)
      return { data: null, error }
    }
  }

  /**
   * 创建问答对
   */
  async createQAPair(qaPair: Partial<QAPair>): Promise<ApiResponse<QAPair>> {
    try {
      const { data, error } = await supabase
        .from('qa_pairs')
        .insert([qaPair])
        .select(`
          *,
          categories (
            id, name, color, description
          )
        `)
        .single()
      
      if (error) throw error
      
      return { data, error: null }
    } catch (error) {
      console.error('创建问答失败:', error)
      return { data: null, error }
    }
  }

  /**
   * 批量创建问答对
   */
  async createQAPairsBatch(qaPairs: Partial<QAPair>[]): Promise<ApiResponse<QAPair[]>> {
    try {
      const { data, error } = await supabase
        .from('qa_pairs')
        .insert(qaPairs)
        .select(`
          *,
          categories (
            id, name, color, description
          )
        `)
      
      if (error) throw error
      
      return { data, error: null }
    } catch (error) {
      console.error('批量创建问答失败:', error)
      return { data: null, error }
    }
  }

  /**
   * 更新问答对
   */
  async updateQAPair(id: number, updates: Partial<QAPair>): Promise<ApiResponse<QAPair>> {
    try {
      const { data, error } = await supabase
        .from('qa_pairs')
        .update(updates)
        .eq('id', id)
        .select(`
          *,
          categories (
            id, name, color, description
          )
        `)
        .single()
      
      if (error) throw error
      
      return { data, error: null }
    } catch (error) {
      console.error('更新问答失败:', error)
      return { data: null, error }
    }
  }

  /**
   * 删除问答对
   */
  async deleteQAPair(id: number): Promise<ApiResponse<void>> {
    try {
      const { error } = await supabase
        .from('qa_pairs')
        .delete()
        .eq('id', id)
      
      if (error) throw error
      
      return { data: null, error: null }
    } catch (error) {
      console.error('删除问答失败:', error)
      return { data: null, error }
    }
  }

  // ==================== 上传历史相关 ====================

  /**
   * 获取上传历史
   */
  async getUploadHistory(page = 1, limit = 10): Promise<ApiResponse<UploadHistory[]>> {
    try {
      const { data, error, count } = await supabase
        .from('upload_history')
        .select('*')
        .order('created_at', { ascending: false })
        .range((page - 1) * limit, page * limit - 1)
      
      if (error) throw error
      
      return { data, error: null, count }
    } catch (error) {
      console.error('获取上传历史失败:', error)
      return { data: null, error }
    }
  }

  /**
   * 创建上传记录
   */
  async createUploadRecord(upload: Partial<UploadHistory>): Promise<ApiResponse<UploadHistory>> {
    try {
      const { data, error } = await supabase
        .from('upload_history')
        .insert([upload])
        .select()
        .single()
      
      if (error) throw error
      
      return { data, error: null }
    } catch (error) {
      console.error('创建上传记录失败:', error)
      return { data: null, error }
    }
  }

  /**
   * 更新上传记录
   */
  async updateUploadRecord(id: number, updates: Partial<UploadHistory>): Promise<ApiResponse<UploadHistory>> {
    try {
      const { data, error } = await supabase
        .from('upload_history')
        .update(updates)
        .eq('id', id)
        .select()
        .single()
      
      if (error) throw error
      
      return { data, error: null }
    } catch (error) {
      console.error('更新上传记录失败:', error)
      return { data: null, error }
    }
  }

  // ==================== 统计信息相关 ====================

  /**
   * 获取统计信息
   */
  async getStatistics(): Promise<ApiResponse<Statistics>> {
    try {
      const { data, error } = await supabase
        .rpc('get_qa_statistics')
      
      if (error) throw error
      
      return { data, error: null }
    } catch (error) {
      console.error('获取统计信息失败:', error)
      return { data: null, error }
    }
  }

  // ==================== 实时订阅相关 ====================

  /**
   * 订阅问答更新
   */
  subscribeToQAUpdates(callback: (payload: any) => void) {
    return supabase
      .channel('qa_updates')
      .on('postgres_changes', 
        { 
          event: 'INSERT', 
          schema: 'public', 
          table: 'qa_pairs' 
        },
        callback
      )
      .on('postgres_changes', 
        { 
          event: 'UPDATE', 
          schema: 'public', 
          table: 'qa_pairs' 
        },
        callback
      )
      .on('postgres_changes', 
        { 
          event: 'DELETE', 
          schema: 'public', 
          table: 'qa_pairs' 
        },
        callback
      )
      .subscribe()
  }

  /**
   * 订阅分类更新
   */
  subscribeToCategoryUpdates(callback: (payload: any) => void) {
    return supabase
      .channel('category_updates')
      .on('postgres_changes', 
        { 
          event: '*', 
          schema: 'public', 
          table: 'categories' 
        },
        callback
      )
      .subscribe()
  }

  // ==================== 工具方法 ====================

  /**
   * 测试连接
   */
  async testConnection(): Promise<boolean> {
    try {
      const { data, error } = await supabase
        .from('categories')
        .select('id')
        .limit(1)
      
      if (error) {
        console.error('Supabase 连接测试失败:', error)
        return false
      }
      
      console.log('✅ Supabase 连接成功')
      return true
    } catch (error) {
      console.error('Supabase 连接错误:', error)
      return false
    }
  }

  /**
   * 获取热门问答
   */
  async getPopularQAs(limit = 10): Promise<ApiResponse<QAPair[]>> {
    try {
      const { data, error } = await supabase
        .from('qa_pairs')
        .select(`
          *,
          categories (
            id, name, color, description
          )
        `)
        .order('confidence', { ascending: false })
        .order('created_at', { ascending: false })
        .limit(limit)
      
      if (error) throw error
      
      return { data, error: null }
    } catch (error) {
      console.error('获取热门问答失败:', error)
      return { data: null, error }
    }
  }

  /**
   * 获取最新问答
   */
  async getRecentQAs(limit = 10): Promise<ApiResponse<QAPair[]>> {
    try {
      const { data, error } = await supabase
        .from('qa_pairs')
        .select(`
          *,
          categories (
            id, name, color, description
          )
        `)
        .order('created_at', { ascending: false })
        .limit(limit)
      
      if (error) throw error
      
      return { data, error: null }
    } catch (error) {
      console.error('获取最新问答失败:', error)
      return { data: null, error }
    }
  }
}

// 导出单例实例
export const supabaseAPI = new SupabaseAPI()
export default supabaseAPI