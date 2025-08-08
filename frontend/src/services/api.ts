import axios from 'axios'

// API 基础 URL 配置
const getBaseURL = (): string => {
  console.log('Environment:', import.meta.env.MODE)
  console.log('API URL:', import.meta.env.VITE_API_BASE_URL)
  
  // 生产环境：使用环境变量或默认的演示 URL
  if (import.meta.env.MODE === 'production' || import.meta.env.PROD) {
    const apiUrl = import.meta.env.VITE_API_BASE_URL || 'https://chatlog-api-demo.example.com/api/v1'
    console.log('Using production API URL:', apiUrl)
    return apiUrl
  }
  // 开发环境：使用本地代理
  console.log('Using development API URL: /api/v1')
  return '/api/v1'
}

// 创建 axios 实例
const api = axios.create({
  baseURL: getBaseURL(),
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 性能优化：请求/响应缓存
const cache = new Map<string, { data: any; timestamp: number }>()
const CACHE_DURATION = 5 * 60 * 1000 // 5分钟缓存

// 生成缓存键
const getCacheKey = (config: any): string => {
  return `${config.method}-${config.url}-${JSON.stringify(config.params || {})}`
}

// 检查缓存是否有效
const isCacheValid = (timestamp: number): boolean => {
  return Date.now() - timestamp < CACHE_DURATION
}

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 性能优化：对GET请求启用缓存
    if (config.method === 'get') {
      const cacheKey = getCacheKey(config)
      const cachedItem = cache.get(cacheKey)
      
      if (cachedItem && isCacheValid(cachedItem.timestamp)) {
        // 返回缓存的Promise，模拟axios响应格式
        return Promise.reject({
          __cached: true,
          data: cachedItem.data,
          status: 200,
          statusText: 'OK',
          headers: {},
          config
        })
      }
    }
    
    // 可以在这里添加 token 等认证信息
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    // 性能优化：缓存GET请求的响应
    if (response.config.method === 'get' && response.status === 200) {
      const cacheKey = getCacheKey(response.config)
      cache.set(cacheKey, {
        data: response.data,
        timestamp: Date.now()
      })
      
      // 清理过期缓存（简单的LRU策略）
      if (cache.size > 100) {
        const entries = Array.from(cache.entries())
        const expiredKeys = entries
          .filter(([_, value]) => !isCacheValid(value.timestamp))
          .map(([key]) => key)
        
        expiredKeys.forEach(key => cache.delete(key))
      }
    }
    
    return response
  },
  (error) => {
    // 处理缓存的请求
    if (error.__cached) {
      return Promise.resolve({
        data: error.data,
        status: error.status,
        statusText: error.statusText,
        headers: error.headers,
        config: error.config
      })
    }
    
    // 统一错误处理
    if (error.response) {
      console.error('API Error:', error.response.status, error.response.data)
    } else if (error.request) {
      console.error('Network Error:', error.request)
    } else {
      console.error('Error:', error.message)
    }
    return Promise.reject(error)
  }
)

// 清理缓存的工具函数
export const clearApiCache = (): void => {
  cache.clear()
}

// 预加载关键数据的工具函数
export const preloadData = async (endpoints: string[]): Promise<void> => {
  try {
    await Promise.all(
      endpoints.map(endpoint => 
        api.get(endpoint).catch(err => console.warn(`Preload failed for ${endpoint}:`, err))
      )
    )
  } catch (error) {
    console.warn('Preload partially failed:', error)
  }
}

// ======================
// API 函数定义
// ======================

// 上传文件（同步处理）
export const uploadFile = async (formData: FormData): Promise<any> => {
  try {
    const response = await api.post('/upload/file', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 300000, // 5分钟超时
      onUploadProgress: (progressEvent) => {
        // 可以在这里处理上传进度
        if (progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          console.log(`Upload progress: ${percentCompleted}%`)
        }
      }
    })
    return response.data
  } catch (error) {
    console.error('Upload file error:', error)
    throw error
  }
}

// 异步上传文件（后台任务处理）
export const uploadFileAsync = async (formData: FormData): Promise<any> => {
  try {
    const response = await api.post('/upload/file/async', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 60000, // 1分钟超时（仅上传，不包括处理）
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          console.log(`Async upload progress: ${percentCompleted}%`)
        }
      }
    })
    return response.data
  } catch (error) {
    console.error('Async upload file error:', error)
    throw error
  }
}

// 获取异步任务状态
export const getTaskStatus = async (taskId: string): Promise<any> => {
  try {
    const response = await api.get(`/upload/task/${taskId}/status`)
    return response.data
  } catch (error) {
    console.error('Get task status error:', error)
    throw error
  }
}

// 取消异步任务
export const cancelTask = async (taskId: string): Promise<any> => {
  try {
    const response = await api.post(`/upload/task/${taskId}/cancel`)
    return response.data
  } catch (error) {
    console.error('Cancel task error:', error)
    throw error
  }
}

// 获取任务队列统计信息
export const getQueueStats = async (): Promise<any> => {
  try {
    const response = await api.get('/upload/queue/stats')
    return response.data
  } catch (error) {
    console.error('Get queue stats error:', error)
    throw error
  }
}

// 获取WebSocket连接统计
export const getWebSocketStats = async (): Promise<any> => {
  try {
    const response = await api.get('/upload/websocket/stats')
    return response.data
  } catch (error) {
    console.error('Get WebSocket stats error:', error)
    throw error
  }
}

// 获取上传状态
export const getUploadStatus = async (uploadId: number): Promise<any> => {
  try {
    const response = await api.get(`/upload/status/${uploadId}`)
    return response.data
  } catch (error) {
    console.error('Get upload status error:', error)
    throw error
  }
}

// 获取上传历史
export const getUploadHistory = async (params?: {
  page?: number
  per_page?: number
  status?: string
}): Promise<any> => {
  try {
    const response = await api.get('/upload/history', { params })
    return response.data
  } catch (error) {
    console.error('Get upload history error:', error)
    throw error
  }
}

// 清理临时文件
export const cleanupFiles = async (maxAgeHours: number = 24): Promise<any> => {
  try {
    const response = await api.post('/upload/cleanup', { max_age_hours: maxAgeHours })
    return response.data
  } catch (error) {
    console.error('Cleanup files error:', error)
    throw error
  }
}

// 搜索问答对
export const searchQA = async (params: {
  q?: string
  category?: string
  advisor?: string
  page?: number
  per_page?: number
  sort_by?: string
}): Promise<any> => {
  try {
    const response = await api.get('/search', { params })
    return response.data
  } catch (error) {
    console.error('Search QA error:', error)
    throw error
  }
}

// 获取问答对详情
export const getQADetail = async (id: number): Promise<any> => {
  try {
    const response = await api.get(`/qa/${id}`)
    return response.data
  } catch (error) {
    console.error('Get QA detail error:', error)
    throw error
  }
}

// 更新问答对
export const updateQA = async (id: number, data: any): Promise<any> => {
  try {
    const response = await api.put(`/qa/${id}`, data)
    return response.data
  } catch (error) {
    console.error('Update QA error:', error)
    throw error
  }
}

// 删除问答对
export const deleteQA = async (id: number): Promise<any> => {
  try {
    const response = await api.delete(`/qa/${id}`)
    return response.data
  } catch (error) {
    console.error('Delete QA error:', error)
    throw error
  }
}

// 获取分类列表
export const getCategories = async (): Promise<any> => {
  try {
    const response = await api.get('/categories')
    return response.data
  } catch (error) {
    console.error('Get categories error:', error)
    throw error
  }
}

// 创建分类
export const createCategory = async (data: { name: string; description?: string }): Promise<any> => {
  try {
    const response = await api.post('/categories', data)
    return response.data
  } catch (error) {
    console.error('Create category error:', error)
    throw error
  }
}

// 更新分类
export const updateCategory = async (id: number, data: { name?: string; description?: string }): Promise<any> => {
  try {
    const response = await api.put(`/categories/${id}`, data)
    return response.data
  } catch (error) {
    console.error('Update category error:', error)
    throw error
  }
}

// 获取搜索建议
export const getSearchSuggestions = async (query: string): Promise<any> => {
  try {
    const response = await api.get('/search/suggestions', { params: { q: query } })
    return response.data
  } catch (error) {
    console.error('Get search suggestions error:', error)
    throw error
  }
}

// 获取系统统计
export const getSystemStats = async (): Promise<any> => {
  try {
    const response = await api.get('/admin/stats')
    return response.data
  } catch (error) {
    console.error('Get system stats error:', error)
    throw error
  }
}

// 重建搜索索引
export const rebuildSearchIndex = async (): Promise<any> => {
  try {
    const response = await api.post('/admin/reindex')
    return response.data
  } catch (error) {
    console.error('Rebuild search index error:', error)
    throw error
  }
}

export default api