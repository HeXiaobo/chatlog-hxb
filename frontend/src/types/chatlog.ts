// Chatlog 相关类型定义

export interface ChatlogMessage {
  id: string
  senderName: string
  time: string
  content: string
  type: number
  contents?: {
    desc?: string
    recordInfo?: {
      DataList?: {
        DataItems?: Array<{
          DataDesc?: string
        }>
      }
    }
  }
}

export interface QueryParams {
  timeRange: {
    start: string // YYYY-MM-DD 格式
    end: string   // YYYY-MM-DD 格式
  }
  talker?: string // 群聊或联系人ID
  sender?: string // 发送者筛选
  keyword?: string // 关键词筛选
  format: 'json'
}

export interface ChatInfo {
  id: string
  name: string
  type: 'group' | 'contact'
  messageCount: number
}

// 会话信息（来自chatlog API）
export interface ChatlogSession {
  userName: string // 用户ID/群聊ID
  nickName: string // 显示名称
  content: string  // 最后消息内容
  nTime: string    // 最后消息时间
  nOrder: number   // 排序权重
}

// 会话列表响应
export interface SessionListResponse {
  items: ChatlogSession[]
}

// 浏览器过滤选项
export interface BrowserFilter {
  searchKeyword?: string
  sessionType?: 'all' | 'group' | 'contact'
  timeRange?: 'all' | 'today' | 'week' | 'month'
}

export interface ImportResult {
  success: boolean
  upload_id: number
  total_extracted: number
  total_saved: number
  processing_time: number
  statistics?: {
    extraction?: any
    classification?: any
    file_info?: {
      filename: string
      file_size: number
      processing_time: number
    }
  }
  error?: string
}

export interface ServiceStatus {
  available: boolean
  version?: string
  error?: string
}

// 聊天记录查询响应
export interface ChatlogQueryResponse {
  success: boolean
  data: ChatlogMessage[]
  total: number
  error?: string
}

// 导入响应
export interface ChatlogImportResponse {
  success: boolean
  data: ImportResult
  message: string
  error?: string
}