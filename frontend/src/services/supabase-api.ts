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
      
      // 使用内置查询代替自定义函数进行搜索
      let searchQuery = supabase
        .from('qa_pairs')
        .select(`
          *,
          category:categories(id, name, color, description)
        `)
      
      // 全文搜索
      if (query && query.trim()) {
        searchQuery = searchQuery.textSearch('fts_vector', query)
      }
      
      // 分类筛选
      if (category_id) {
        searchQuery = searchQuery.eq('category_id', category_id)
      }
      
      // 顾问筛选
      if (advisor) {
        searchQuery = searchQuery.ilike('advisor', `%${advisor}%`)
      }
      
      // 执行搜索查询
      const { data, error, count } = await searchQuery
        .order('created_at', { ascending: false })
        .range((page - 1) * limit, page * limit - 1)
      
      if (error) throw error
      
      const totalCount = count || 0
      
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
   * 获取统计信息 (临时简化版本，避免自定义函数问题)
   */
  async getStatistics(): Promise<ApiResponse<Statistics>> {
    try {
      // 使用简单查询代替有问题的自定义函数
      const [
        { count: totalQA },
        { count: totalCategories },
        categoriesData,
        advisorsData
      ] = await Promise.all([
        supabase.from('qa_pairs').select('*', { count: 'exact', head: true }),
        supabase.from('categories').select('*', { count: 'exact', head: true }),
        supabase.from('categories').select('id, name, color, description'),
        supabase.from('qa_pairs').select('advisor').not('advisor', 'is', null).neq('advisor', '')
      ])

      // 计算分类统计
      const categoryStats = await Promise.all(
        (categoriesData.data || []).map(async (cat) => {
          const { count } = await supabase
            .from('qa_pairs')
            .select('*', { count: 'exact', head: true })
            .eq('category_id', cat.id)
          
          return {
            ...cat,
            qa_count: count || 0
          }
        })
      )

      // 计算顾问统计
      const advisorCounts: Record<string, number> = {}
      advisorsData.data?.forEach(item => {
        if (item.advisor) {
          advisorCounts[item.advisor] = (advisorCounts[item.advisor] || 0) + 1
        }
      })
      
      const topAdvisors = Object.entries(advisorCounts)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 10)
        .map(([advisor, count]) => ({ advisor, count }))

      // 获取信心度统计
      const { data: confidenceData } = await supabase
        .from('qa_pairs')
        .select('confidence')
        .not('confidence', 'is', null)

      const confidences = confidenceData?.map(item => item.confidence) || []
      const avgConfidence = confidences.length > 0 
        ? confidences.reduce((sum, conf) => sum + conf, 0) / confidences.length 
        : 0

      const stats: Statistics = {
        total_qa: totalQA || 0,
        total_categories: totalCategories || 0,
        categories_with_count: categoryStats,
        top_advisors: topAdvisors,
        confidence_stats: {
          average: Math.round(avgConfidence * 1000) / 1000,
          high_confidence: confidences.filter(c => c >= 0.8).length,
          medium_confidence: confidences.filter(c => c >= 0.5 && c < 0.8).length,
          low_confidence: confidences.filter(c => c < 0.5).length
        },
        recent_uploads: []
      }
      
      return { data: stats, error: null }
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