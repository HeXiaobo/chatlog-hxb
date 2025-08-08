import axios from 'axios'
import type { 
  ChatlogMessage, 
  QueryParams, 
  ChatInfo, 
  ImportResult, 
  ServiceStatus,
  ChatlogQueryResponse,
  ChatlogImportResponse,
  ChatlogSession,
  SessionListResponse,
  BrowserFilter
} from '../types/chatlog'

// Chatlog API 基础配置
const getChatlogBaseURL = () => {
  // 开发环境使用代理，生产环境可能需要不同配置
  if (import.meta.env.MODE === 'development') {
    return '/chatlog-api' // 通过Vite代理
  }
  return 'http://127.0.0.1:5030' // 生产环境直连
}

// 创建专用的axios实例用于chatlog API
const chatlogApi = axios.create({
  baseURL: getChatlogBaseURL(),
  timeout: 60000, // 60秒超时，因为查询可能需要较长时间
  headers: {
    'Content-Type': 'application/json'
  }
})

// 创建用于知识库API的axios实例（复用现有配置）
const getKnowledgeBaseAPI = () => {
  const baseURL = import.meta.env.MODE === 'production' 
    ? import.meta.env.VITE_API_BASE_URL || '/api/v1'
    : '/api/v1'
    
  return axios.create({
    baseURL,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

class ChatlogService {
  /**
   * 检查chatlog服务状态
   */
  async checkServiceStatus(): Promise<boolean> {
    try {
      console.log('Checking chatlog service status...')
      
      // 直接调用实际的API端点来验证服务状态
      const response = await chatlogApi.get('/api/v1/chatlog', { 
        params: { 
          time: '2024-01-01~2024-01-02',
          talker: 'test',
          format: 'json' 
        },
        timeout: 10000 
      })
      
      // 如果能正常返回数据（即使是空数组），说明服务正常
      return response.status === 200
    } catch (error) {
      console.error('Chatlog service check failed:', error)
      
      // 如果是参数错误或其他非连接错误，说明服务是运行的
      if (axios.isAxiosError(error)) {
        if (error.response?.status === 400 || error.response?.status === 422) {
          return true // 参数错误但服务在运行
        }
        if (error.code === 'ECONNREFUSED' || error.code === 'ENOTFOUND') {
          return false // 连接被拒绝，服务未运行
        }
      }
      
      return false
    }
  }

  /**
   * 获取可用的聊天对象列表（如果API支持）
   */
  async getAvailableChats(): Promise<ChatInfo[]> {
    try {
      // 注意：这个端点可能不存在，取决于chatlog API的实现
      const response = await chatlogApi.get('/api/v1/chats')
      return response.data || []
    } catch (error) {
      console.warn('Failed to get available chats:', error)
      return []
    }
  }

  /**
   * 获取会话列表
   */
  async getSessionList(): Promise<ChatlogSession[]> {
    try {
      console.log('Fetching session list from chatlog...')
      const response = await chatlogApi.get('/api/v1/session', {
        params: { format: 'json' }
      })

      if (response.data && response.data.items) {
        console.log(`Retrieved ${response.data.items.length} sessions`)
        return response.data.items
      }

      return []
    } catch (error: any) {
      console.error('Failed to fetch session list:', error)
      
      if (axios.isAxiosError(error)) {
        if (error.code === 'ECONNREFUSED') {
          throw new Error('无法连接到Chatlog服务，请确保服务正在运行')
        }
        if (error.response?.status === 404) {
          throw new Error('会话列表API不可用，请检查服务版本')
        }
      }
      
      throw new Error(`获取会话列表失败: ${error.message || '未知错误'}`)
    }
  }

  /**
   * 搜索会话
   */
  async searchSessions(filter: BrowserFilter): Promise<ChatlogSession[]> {
    try {
      const sessions = await this.getSessionList()
      let filtered = sessions

      // 按关键词搜索
      if (filter.searchKeyword && filter.searchKeyword.trim()) {
        const keyword = filter.searchKeyword.trim().toLowerCase()
        filtered = filtered.filter(session => 
          session.nickName.toLowerCase().includes(keyword) ||
          session.userName.toLowerCase().includes(keyword) ||
          session.content.toLowerCase().includes(keyword)
        )
      }

      // 按类型筛选
      if (filter.sessionType && filter.sessionType !== 'all') {
        filtered = filtered.filter(session => {
          const isGroup = session.userName.includes('@chatroom')
          return filter.sessionType === 'group' ? isGroup : !isGroup
        })
      }

      // 按时间范围筛选（简单实现）
      if (filter.timeRange && filter.timeRange !== 'all') {
        const now = new Date()
        const cutoffTime = new Date()
        
        switch (filter.timeRange) {
          case 'today':
            cutoffTime.setHours(0, 0, 0, 0)
            break
          case 'week':
            cutoffTime.setDate(now.getDate() - 7)
            break
          case 'month':
            cutoffTime.setMonth(now.getMonth() - 1)
            break
        }

        filtered = filtered.filter(session => {
          const sessionTime = new Date(session.nTime)
          return sessionTime >= cutoffTime
        })
      }

      return filtered
    } catch (error) {
      console.error('Failed to search sessions:', error)
      throw error
    }
  }

  /**
   * 查询聊天记录
   */
  async queryChatlog(params: QueryParams): Promise<ChatlogMessage[]> {
    try {
      console.log('Querying chatlog with params:', params)
      
      // 构建查询参数
      const queryParams = {
        time: `${params.timeRange.start}~${params.timeRange.end}`,
        format: 'json' as const,
        ...(params.talker && { talker: params.talker }),
        ...(params.sender && { sender: params.sender }),
        ...(params.keyword && { keyword: params.keyword })
      }

      const response = await chatlogApi.get('/api/v1/chatlog', {
        params: queryParams
      })

      // chatlog API直接返回消息数组
      const messages = Array.isArray(response.data) ? response.data : []
      
      console.log(`Retrieved ${messages.length} messages from chatlog`)
      return messages
    } catch (error: any) {
      console.error('Failed to query chatlog:', error)
      
      if (axios.isAxiosError(error)) {
        if (error.code === 'ECONNREFUSED') {
          throw new Error('无法连接到Chatlog服务，请确保服务正在运行')
        }
        if (error.response?.status === 404) {
          throw new Error('Chatlog API端点不存在，请检查服务配置')
        }
        if (error.response?.data?.error) {
          throw new Error(error.response.data.error)
        }
        throw new Error(`查询失败: ${error.message}`)
      }
      
      throw new Error(`查询聊天记录失败: ${error.message || '未知错误'}`)
    }
  }

  /**
   * 将消息导入到知识库
   */
  async importToKnowledgeBase(messages: ChatlogMessage[]): Promise<ImportResult> {
    try {
      console.log(`Importing ${messages.length} messages to knowledge base`)
      
      // 将chatlog消息转换为知识库期望的格式
      const convertedMessages = messages.map((msg, index) => ({
        id: msg.id || `msg_${String(index + 1).padStart(6, '0')}`,
        timestamp: this.parseTimestamp(msg.time),
        from_user: msg.senderName || 'Unknown',
        content: this.extractContent(msg),
        message_type: 'text'
      }))

      // 创建虚拟文件内容
      const fileContent = JSON.stringify(convertedMessages, null, 2)
      const fileName = `chatlog_import_${Date.now()}.json`

      // 调用知识库API
      const kbApi = getKnowledgeBaseAPI()
      
      // 使用现有的文件上传端点
      const formData = new FormData()
      const blob = new Blob([fileContent], { type: 'application/json' })
      formData.append('file', blob, fileName)

      const response = await kbApi.post('/upload/file', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      if (response.data.success) {
        return {
          success: true,
          upload_id: response.data.data.upload_id,
          total_extracted: response.data.data.total_extracted || convertedMessages.length,
          total_saved: response.data.data.total_saved || 0,
          processing_time: response.data.data.processing_time || 0,
          statistics: response.data.data.statistics
        }
      } else {
        throw new Error(response.data.error?.message || '导入失败')
      }
    } catch (error: any) {
      console.error('Failed to import to knowledge base:', error)
      
      if (axios.isAxiosError(error) && error.response?.data) {
        const errorData = error.response.data
        throw new Error(errorData.error?.message || errorData.message || '导入到知识库失败')
      }
      
      throw new Error(`导入失败: ${error.message || '未知错误'}`)
    }
  }

  /**
   * 解析时间戳
   */
  private parseTimestamp(timeStr: string): number {
    try {
      const date = new Date(timeStr)
      return date.getTime()
    } catch {
      return Date.now()
    }
  }

  /**
   * 提取消息内容（复用后端逻辑）
   */
  private extractContent(msg: ChatlogMessage): string {
    let content = ''
    
    // 优先处理复杂内容结构
    if (msg.contents) {
      if (msg.contents.desc) {
        content = msg.contents.desc.trim()
      } else if (msg.contents.recordInfo?.DataList?.DataItems) {
        for (const item of msg.contents.recordInfo.DataList.DataItems) {
          if (item.DataDesc) {
            const nestedContent = item.DataDesc.trim()
            if (nestedContent && nestedContent.length > content.length) {
              content = nestedContent
            }
          }
        }
      }
    }
    
    // 如果没有找到复杂内容，使用简单内容
    if (!content && msg.content) {
      content = msg.content.trim()
    }
    
    // 清理内容格式
    if (content) {
      // 移除用户名前缀（如 "林: "）
      content = content.replace(/^[^:：]+[:：]\s*/, '')
      // 移除多余的空白字符
      content = content.replace(/\s+/g, ' ').trim()
    }
    
    return content
  }

  /**
   * 获取服务信息
   */
  async getServiceInfo(): Promise<ServiceStatus> {
    try {
      const isAvailable = await this.checkServiceStatus()
      return {
        available: isAvailable,
        version: 'unknown'
      }
    } catch (error: any) {
      return {
        available: false,
        error: error.message
      }
    }
  }
}

// 导出单例
export const chatlogService = new ChatlogService()