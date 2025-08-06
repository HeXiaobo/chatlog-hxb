import axios from 'axios'

// API 基础 URL 配置
const getBaseURL = (): string => {
  // 生产环境：使用环境变量或默认的演示 URL
  if (process.env.NODE_ENV === 'production') {
    return process.env.VITE_API_BASE_URL || 'https://chatlog-api-demo.example.com/api/v1'
  }
  // 开发环境：使用本地代理
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

export default api