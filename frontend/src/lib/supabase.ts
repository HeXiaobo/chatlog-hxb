import { createClient } from '@supabase/supabase-js'

// Supabase 配置
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

// 验证环境变量
if (!supabaseUrl || !supabaseAnonKey) {
  console.error('Missing Supabase environment variables')
  console.log('VITE_SUPABASE_URL:', supabaseUrl ? 'Set' : 'Missing')
  console.log('VITE_SUPABASE_ANON_KEY:', supabaseAnonKey ? 'Set' : 'Missing')
  
  // 提供友好的错误提示
  if (!supabaseUrl && !supabaseAnonKey) {
    console.warn('⚠️ Supabase not configured. Please check the supabase-setup.md file for instructions.')
  }
}

// 创建 Supabase 客户端
export const supabase = createClient(supabaseUrl || '', supabaseAnonKey || '', {
  auth: {
    persistSession: false, // 目前不需要用户认证
  },
  realtime: {
    params: {
      eventsPerSecond: 10, // 限制实时事件频率
    }
  }
})

// 类型定义
export interface Category {
  id: number
  name: string
  description: string
  color: string
  qa_count: number
  created_at: string
  updated_at: string
}

export interface QAPair {
  id: number
  question: string
  answer: string
  category_id: number | null
  asker: string | null
  advisor: string | null
  confidence: number
  source_file: string | null
  original_context: string | null
  created_at: string
  updated_at: string
  // 关联数据
  categories?: Category
  // 搜索相关
  search_rank?: number
}

export interface UploadHistory {
  id: number
  filename: string
  original_name: string | null
  file_size: number | null
  status: 'pending' | 'processing' | 'completed' | 'failed'
  processed_count: number
  total_count: number
  error_message: string | null
  created_at: string
  updated_at: string
}

// 搜索函数返回类型
export interface SearchResult extends QAPair {
  category_name?: string
  category_color?: string
  category_description?: string
}

// 统计信息类型
export interface Statistics {
  total_qa: number
  total_categories: number
  categories_with_count: Array<Category & { qa_count: number }>
  top_advisors: Array<{ advisor: string; count: number }>
  confidence_stats: {
    average: number
    high_confidence: number
    medium_confidence: number
    low_confidence: number
  }
  recent_uploads: Array<Partial<UploadHistory>>
}

// API 响应类型
export interface ApiResponse<T> {
  data: T | null
  error: any
  count?: number
}

// 搜索参数类型
export interface SearchParams {
  query?: string
  category_id?: number
  advisor?: string
  page?: number
  limit?: number
}

// 验证 Supabase 连接的工具函数
export const testSupabaseConnection = async (): Promise<boolean> => {
  try {
    const { data, error } = await supabase
      .from('categories')
      .select('id')
      .limit(1)
    
    if (error) {
      console.error('Supabase connection test failed:', error)
      return false
    }
    
    console.log('✅ Supabase connection successful')
    return true
  } catch (error) {
    console.error('Supabase connection test error:', error)
    return false
  }
}

// 调试工具：显示当前配置
export const debugSupabaseConfig = () => {
  console.log('📊 Supabase Configuration:')
  console.log('URL:', supabaseUrl)
  console.log('Key:', supabaseAnonKey ? `${supabaseAnonKey.slice(0, 10)}...` : 'Missing')
  console.log('Client created:', !!supabase)
}