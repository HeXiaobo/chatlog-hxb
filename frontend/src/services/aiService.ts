import api from './api';
import type { 
  AIStatus, 
  AIConfig, 
  AIUsageReport, 
  AICapabilities,
  AIProviderConfig,
  AIOptimizationTips
} from '../types/ai';

class AIService {
  /**
   * 获取AI系统状态
   */
  async getAIStatus(): Promise<AIStatus> {
    const response = await api.get('/ai/status');
    return response.data.data;
  }

  /**
   * 获取AI配置信息
   */
  async getAIConfig(): Promise<AIConfig> {
    const response = await api.get('/ai/config');
    return response.data.data;
  }

  /**
   * 更新AI配置
   */
  async updateAIConfig(provider: string, config: Partial<AIProviderConfig>): Promise<void> {
    await api.post('/ai/config', {
      provider,
      ...config
    });
  }

  /**
   * 添加新的AI提供商
   */
  async addAIProvider(config: {
    provider: string;
    model_name: string;
    api_key: string;
    api_base?: string;
    max_tokens?: number;
    temperature?: number;
    timeout?: number;
    enabled?: boolean;
    cost_per_1k_tokens?: number;
    daily_limit?: number;
  }): Promise<void> {
    await api.post('/ai/config/add', config);
  }

  /**
   * 删除AI提供商
   */
  async removeAIProvider(provider: string): Promise<void> {
    await api.delete(`/ai/config/${provider}`);
  }

  /**
   * 测试AI提供商连接
   */
  async testProviderConnection(provider: string): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await api.get(`/ai/config/test/${provider}`);
      return { success: true };
    } catch (error: any) {
      return { 
        success: false, 
        error: error.response?.data?.error?.details || '连接测试失败' 
      };
    }
  }

  /**
   * 获取AI使用报告
   */
  async getUsageReport(period: '1h' | '24h' | '7d' | '30d'): Promise<AIUsageReport> {
    const response = await api.get(`/ai/report/${period}`);
    return response.data.data;
  }

  /**
   * 导出使用报告
   */
  async exportUsageReport(period: '1h' | '24h' | '7d' | '30d'): Promise<{ content: string }> {
    const response = await api.get(`/ai/report/${period}/export?format=json`);
    return response.data.data;
  }

  /**
   * 重置每日统计
   */
  async resetDailyStats(): Promise<void> {
    await api.post('/ai/stats/reset');
  }

  /**
   * 获取支持的AI提供商列表
   */
  async getProviders(): Promise<{ [key: string]: any }> {
    const response = await api.get('/ai/providers');
    return response.data.data.providers;
  }

  /**
   * 获取系统健康状态
   */
  async getSystemHealth(): Promise<any> {
    const response = await api.get('/ai/health');
    return response.data.data;
  }

  /**
   * 获取AI优化建议
   */
  async getOptimizationTips(): Promise<AIOptimizationTips> {
    const response = await api.post('/ai/optimize');
    return response.data.data;
  }

  /**
   * 获取AI处理能力信息
   */
  async getAICapabilities(): Promise<AICapabilities> {
    const response = await api.get('/upload/ai/capabilities');
    return response.data.data;
  }

  /**
   * 获取AI使用统计
   */
  async getAIUsage(): Promise<any> {
    const response = await api.get('/upload/ai/usage');
    return response.data.data;
  }

  /**
   * 使用AI增强现有问答对
   */
  async enhanceExistingQA(limit: number = 100): Promise<{ enhanced_count: number; total_processed: number }> {
    const response = await api.post('/upload/ai/enhance', { limit });
    return response.data.data;
  }

  /**
   * 上传文件并使用AI处理
   */
  async uploadFileWithAI(file: File, onProgress?: (progress: number) => void): Promise<{
    upload_id: number;
    filename: string;
    total_extracted: number;
    total_saved: number;
    processing_time: number;
    processing_method: string;
    ai_enabled: boolean;
    statistics: any;
  }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/upload/file/ai', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });

    return response.data.data;
  }

  /**
   * 上传文件并使用智能处理器处理
   * 实现完整流程：导入 → AI分析 → 过滤无用内容 → 整理知识库
   */
  async uploadFileWithIntelligentProcessing(file: File, onProgress?: (progress: number) => void): Promise<{
    upload_id: number;
    filename: string;
    processing_summary: {
      original_messages: number;
      useful_messages: number;
      noise_filtered: number;
      qa_pairs_extracted: number;
      final_knowledge_entries: number;
      content_quality_score: number;
      extraction_efficiency: number;
    };
    processing_performance: {
      processing_time: number;
      ai_processing_time: number;
      processing_method: string;
      ai_enabled: boolean;
    };
    ai_usage: {
      ai_provider_used: string;
      tokens_consumed: number;
      processing_cost: number;
      content_improvement_rate: number;
    };
    detailed_stats: any;
  }> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('force_ai', 'false'); // 让后端自动判断

    const response = await api.post('/upload/file/intelligent', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });

    return response.data.data;
  }

  /**
   * 比较AI处理与规则处理的效果
   */
  async compareProcessingMethods(file: File): Promise<{
    ai_result: any;
    rule_result: any;
    comparison: {
      extraction_improvement: number;
      confidence_improvement: number;
      time_difference: number;
    };
  }> {
    // 这是一个示例方法，实际需要后端支持并行处理比较
    const formData = new FormData();
    formData.append('file', file);
    formData.append('compare_methods', 'true');

    const response = await api.post('/upload/file/compare', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data.data;
  }
}

export const aiService = new AIService();
export default aiService;