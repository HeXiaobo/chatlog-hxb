/**
 * 共享类型定义
 */

export interface Category {
  id: number
  name: string
  description: string
  color: string
  qa_count?: number
  created_at?: string
  updated_at?: string
}

export interface QAPair {
  id: number
  question: string
  answer: string
  category_id: number
  category?: Category
  asker?: string
  advisor?: string
  confidence: number
  source_file?: string
  created_at: string
  updated_at: string
}

export interface UploadHistory {
  id: number
  filename: string
  file_size: number
  status: 'processing' | 'completed' | 'error'
  total_messages?: number
  extracted_qa_count?: number
  error_message?: string
  created_at: string
  updated_at: string
}

export interface SearchFilters {
  category_id?: number
  confidence_min?: number
  confidence_max?: number
  date_from?: string
  date_to?: string
  advisor?: string
}

export interface SearchSuggestion {
  text: string
  type: 'query' | 'category' | 'advisor'
  count?: number
}

export interface UploadResponse {
  upload_id: number
  filename: string
  total_messages: number
  extracted_qa_count: number
  processing_time: number
}

export interface APIResponse<T = any> {
  success: boolean
  data?: T
  message?: string
  error?: {
    code: string
    message: string
    details?: string
  }
  pagination?: {
    page: number
    per_page: number
    total: number
    pages: number
  }
  total?: number
  timestamp?: string
}

export interface SystemStats {
  totalQAs: number
  totalCategories: number
  totalUploads: number
  avgConfidence: number
  recentUploads: number
  searchCount: number
}