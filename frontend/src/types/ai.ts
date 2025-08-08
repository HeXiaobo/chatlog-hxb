// AI系统状态
export interface AIStatus {
  timestamp: string;
  config_status: {
    total_providers: number;
    primary_provider: string | null;
    providers: {
      [provider: string]: {
        enabled: boolean;
        model: string;
        daily_limit: number;
        daily_used: number;
        remaining: number;
        cost_per_1k: number;
        can_make_request: boolean;
      };
    };
    ai_enabled: boolean;
  };
  processing_status: {
    recent_uploads_24h: number;
    ai_processed_count: number;
    ai_processing_ratio: number;
    status_distribution: {
      [status: string]: number;
    };
    avg_processing_time: number;
  };
  usage_stats: {
    total_requests: number;
    total_cost: number;
    total_tokens: number;
    providers: {
      [provider: string]: {
        requests: number;
        success_rate: number;
        tokens_used: number;
        cost: number;
        daily_usage: {
          requests: number;
          tokens: number;
          cost: number;
        };
      };
    };
  };
  quality_metrics: {
    total_ai_qa_pairs: number;
    avg_confidence: number;
    quality_distribution: {
      excellent: number;
      good: number;
      fair: number;
      poor: number;
    };
    high_quality_ratio: number;
  };
  system_health: {
    health_score: number;
    health_level: 'excellent' | 'good' | 'fair' | 'poor';
    issues: string[];
    recommendations: string[];
  };
}

// AI配置
export interface AIConfig {
  providers: AIProviderConfig[];
  primary_provider: string | null;
  total_providers: number;
}

export interface AIProviderConfig {
  provider: string;
  model_name: string;
  enabled: boolean;
  max_tokens: number;
  temperature: number;
  daily_limit: number;
  cost_per_1k_tokens: number;
  usage_stats: {
    total_requests: number;
    daily_requests: number;
    success_rate: number;
    total_cost: number;
    daily_cost: number;
  };
}

// AI性能指标
export interface AIPerformanceMetrics {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  avg_processing_time: number;
  total_tokens_used: number;
  total_cost: number;
  success_rate: number;
  avg_confidence: number;
  quality_distribution: {
    [key: string]: number;
  };
}

// AI使用报告
export interface AIUsageReport {
  period: string;
  start_date: string;
  end_date: string;
  extraction_metrics: AIPerformanceMetrics;
  classification_metrics: AIPerformanceMetrics;
  provider_breakdown: {
    [provider: string]: AIPerformanceMetrics;
  };
  cost_analysis: {
    total_cost: number;
    daily_cost: number;
    estimated_monthly_cost: number;
  };
  recommendations: string[];
}

// AI处理能力
export interface AICapabilities {
  ai_enabled: boolean;
  available_providers: string[];
  primary_provider: string | null;
  features: {
    intelligent_extraction: boolean;
    semantic_classification: boolean;
    content_enhancement: boolean;
    quality_assessment: boolean;
  };
  primary_config?: {
    model_name: string;
    max_tokens: number;
    daily_limit: number;
  };
  usage_stats?: {
    daily_requests: number;
    daily_tokens: number;
    success_rate: number;
  };
}

// AI优化建议
export interface AIOptimizationTips {
  optimization_tips: {
    performance: string[];
    cost: string[];
    quality: string[];
  };
  report_summary: {
    extraction_success_rate: number;
    classification_confidence: number;
    daily_cost: number;
    recommendations: string[];
  };
}

// AI提取结果
export interface AIExtractionResult {
  qa_pairs: any[];
  confidence_score: number;
  processing_time: number;
  tokens_used: number;
  provider_used: string;
  extraction_method: 'ai' | 'fallback' | 'hybrid';
}

// AI分类结果
export interface AIClassificationResult {
  category_match: {
    category_id: number;
    category_name: string;
    confidence: number;
    matched_keywords: string[];
  };
  processing_time: number;
  tokens_used: number;
  provider_used: string;
  classification_method: 'ai' | 'fallback';
  reasoning?: string;
}

// AI处理统计
export interface AIProcessingStats {
  total_extracted: number;
  total_saved: number;
  processing_time: number;
  processing_method: 'ai' | 'fallback' | 'hybrid';
  ai_enabled: boolean;
  statistics: {
    ai_extraction?: any;
    ai_classification?: any;
    processing?: any;
    file_info?: any;
  };
}