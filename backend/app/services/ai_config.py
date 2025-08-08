"""
AI大模型配置管理服务
"""
import os
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import json

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """AI提供商枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    ZHIPU = "zhipu"  # 智谱AI
    BAIDU = "baidu"  # 百度文心一言
    ALIBABA = "alibaba"  # 阿里云通义千问
    KIMI = "kimi"  # 月之暗面Kimi
    DOUBAO = "doubao"  # 字节豆包
    DEEPSEEK = "deepseek"  # DeepSeek
    OLLAMA = "ollama"  # 本地模型


@dataclass
class AIModelConfig:
    """AI模型配置"""
    provider: str
    model_name: str
    api_key: str
    api_base: Optional[str] = None
    max_tokens: int = 2000
    temperature: float = 0.7
    timeout: int = 60
    enabled: bool = True
    cost_per_1k_tokens: float = 0.0
    daily_limit: int = 10000
    

@dataclass 
class AIUsageStats:
    """AI使用统计"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens_used: int = 0
    total_cost: float = 0.0
    daily_requests: int = 0
    daily_tokens: int = 0
    daily_cost: float = 0.0


class AIConfigManager:
    """AI配置管理器"""
    
    def __init__(self):
        self.config_file = os.getenv('AI_CONFIG_FILE', 'ai_config.json')
        self.models_config = {}
        self.usage_stats = {}
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        try:
            # 从环境变量加载默认配置
            self._load_default_config()
            
            # 尝试从配置文件加载
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    
                for provider, model_data in config_data.get('models', {}).items():
                    self.models_config[provider] = AIModelConfig(**model_data)
                
                # 加载使用统计
                self.usage_stats = {
                    provider: AIUsageStats(**stats) 
                    for provider, stats in config_data.get('usage_stats', {}).items()
                }
        except Exception as e:
            logger.error(f"Failed to load AI config: {str(e)}")
            self._load_default_config()
    
    def _load_default_config(self):
        """加载默认配置"""
        # OpenAI配置
        if os.getenv('OPENAI_API_KEY'):
            self.models_config[AIProvider.OPENAI.value] = AIModelConfig(
                provider=AIProvider.OPENAI.value,
                model_name=os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
                api_key=os.getenv('OPENAI_API_KEY'),
                api_base=os.getenv('OPENAI_API_BASE'),
                max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '2000')),
                temperature=float(os.getenv('OPENAI_TEMPERATURE', '0.7')),
                cost_per_1k_tokens=float(os.getenv('OPENAI_COST_PER_1K', '0.002')),
                daily_limit=int(os.getenv('OPENAI_DAILY_LIMIT', '10000'))
            )
        
        # Anthropic配置
        if os.getenv('ANTHROPIC_API_KEY'):
            self.models_config[AIProvider.ANTHROPIC.value] = AIModelConfig(
                provider=AIProvider.ANTHROPIC.value,
                model_name=os.getenv('ANTHROPIC_MODEL', 'claude-3-sonnet-20240229'),
                api_key=os.getenv('ANTHROPIC_API_KEY'),
                api_base=os.getenv('ANTHROPIC_API_BASE'),
                max_tokens=int(os.getenv('ANTHROPIC_MAX_TOKENS', '2000')),
                temperature=float(os.getenv('ANTHROPIC_TEMPERATURE', '0.7')),
                cost_per_1k_tokens=float(os.getenv('ANTHROPIC_COST_PER_1K', '0.003')),
                daily_limit=int(os.getenv('ANTHROPIC_DAILY_LIMIT', '8000'))
            )
        
        # 智谱AI配置
        if os.getenv('ZHIPU_API_KEY'):
            self.models_config[AIProvider.ZHIPU.value] = AIModelConfig(
                provider=AIProvider.ZHIPU.value,
                model_name=os.getenv('ZHIPU_MODEL', 'glm-4'),
                api_key=os.getenv('ZHIPU_API_KEY'),
                api_base=os.getenv('ZHIPU_API_BASE', 'https://open.bigmodel.cn/api/paas/v4/'),
                max_tokens=int(os.getenv('ZHIPU_MAX_TOKENS', '2000')),
                temperature=float(os.getenv('ZHIPU_TEMPERATURE', '0.7')),
                cost_per_1k_tokens=float(os.getenv('ZHIPU_COST_PER_1K', '0.001')),
                daily_limit=int(os.getenv('ZHIPU_DAILY_LIMIT', '15000'))
            )
        
        # 百度文心一言配置
        if os.getenv('BAIDU_API_KEY'):
            self.models_config[AIProvider.BAIDU.value] = AIModelConfig(
                provider=AIProvider.BAIDU.value,
                model_name=os.getenv('BAIDU_MODEL', 'ernie-bot-turbo'),
                api_key=os.getenv('BAIDU_API_KEY'),
                api_base=os.getenv('BAIDU_API_BASE', 'https://aip.baidubce.com/'),
                max_tokens=int(os.getenv('BAIDU_MAX_TOKENS', '2000')),
                temperature=float(os.getenv('BAIDU_TEMPERATURE', '0.7')),
                cost_per_1k_tokens=float(os.getenv('BAIDU_COST_PER_1K', '0.0008')),
                daily_limit=int(os.getenv('BAIDU_DAILY_LIMIT', '20000'))
            )
        
        # 月之暗面Kimi配置
        if os.getenv('KIMI_API_KEY'):
            self.models_config[AIProvider.KIMI.value] = AIModelConfig(
                provider=AIProvider.KIMI.value,
                model_name=os.getenv('KIMI_MODEL', 'moonshot-v1-8k'),
                api_key=os.getenv('KIMI_API_KEY'),
                api_base=os.getenv('KIMI_API_BASE', 'https://api.moonshot.cn/v1/'),
                max_tokens=int(os.getenv('KIMI_MAX_TOKENS', '2000')),
                temperature=float(os.getenv('KIMI_TEMPERATURE', '0.7')),
                cost_per_1k_tokens=float(os.getenv('KIMI_COST_PER_1K', '0.012')),
                daily_limit=int(os.getenv('KIMI_DAILY_LIMIT', '5000'))
            )
        
        # 字节豆包大模型配置
        if os.getenv('DOUBAO_API_KEY'):
            self.models_config[AIProvider.DOUBAO.value] = AIModelConfig(
                provider=AIProvider.DOUBAO.value,
                model_name=os.getenv('DOUBAO_MODEL', 'ep-20240611073937-h8l9s'),
                api_key=os.getenv('DOUBAO_API_KEY'),
                api_base=os.getenv('DOUBAO_API_BASE', 'https://ark.cn-beijing.volces.com/api/v3/'),
                max_tokens=int(os.getenv('DOUBAO_MAX_TOKENS', '2000')),
                temperature=float(os.getenv('DOUBAO_TEMPERATURE', '0.7')),
                cost_per_1k_tokens=float(os.getenv('DOUBAO_COST_PER_1K', '0.0008')),
                daily_limit=int(os.getenv('DOUBAO_DAILY_LIMIT', '15000'))
            )
        
        # DeepSeek配置
        if os.getenv('DEEPSEEK_API_KEY'):
            self.models_config[AIProvider.DEEPSEEK.value] = AIModelConfig(
                provider=AIProvider.DEEPSEEK.value,
                model_name=os.getenv('DEEPSEEK_MODEL', 'deepseek-chat'),
                api_key=os.getenv('DEEPSEEK_API_KEY'),
                api_base=os.getenv('DEEPSEEK_API_BASE', 'https://api.deepseek.com/v1/'),
                max_tokens=int(os.getenv('DEEPSEEK_MAX_TOKENS', '2000')),
                temperature=float(os.getenv('DEEPSEEK_TEMPERATURE', '0.7')),
                cost_per_1k_tokens=float(os.getenv('DEEPSEEK_COST_PER_1K', '0.00014')),
                daily_limit=int(os.getenv('DEEPSEEK_DAILY_LIMIT', '50000'))
            )
        
        # Ollama本地模型配置
        if os.getenv('OLLAMA_HOST'):
            self.models_config[AIProvider.OLLAMA.value] = AIModelConfig(
                provider=AIProvider.OLLAMA.value,
                model_name=os.getenv('OLLAMA_MODEL', 'llama2:7b'),
                api_key='',  # Ollama不需要API Key
                api_base=os.getenv('OLLAMA_HOST', 'http://localhost:11434'),
                max_tokens=int(os.getenv('OLLAMA_MAX_TOKENS', '2000')),
                temperature=float(os.getenv('OLLAMA_TEMPERATURE', '0.7')),
                cost_per_1k_tokens=0.0,  # 本地模型无成本
                daily_limit=int(os.getenv('OLLAMA_DAILY_LIMIT', '50000'))
            )
        
        # 初始化使用统计
        for provider in self.models_config.keys():
            if provider not in self.usage_stats:
                self.usage_stats[provider] = AIUsageStats()
    
    def save_config(self):
        """保存配置到文件"""
        try:
            config_data = {
                'models': {
                    provider: asdict(config) 
                    for provider, config in self.models_config.items()
                },
                'usage_stats': {
                    provider: asdict(stats) 
                    for provider, stats in self.usage_stats.items()
                }
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"AI config saved to {self.config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save AI config: {str(e)}")
    
    def get_available_providers(self) -> List[str]:
        """获取可用的AI提供商"""
        return [
            provider for provider, config in self.models_config.items() 
            if config.enabled
        ]
    
    def get_model_config(self, provider: str) -> Optional[AIModelConfig]:
        """获取模型配置"""
        return self.models_config.get(provider)
    
    def get_primary_provider(self) -> Optional[str]:
        """获取主要的AI提供商"""
        available = self.get_available_providers()
        
        # 优先级：本地模型 > 国产模型 > 国外模型
        priority_order = [
            AIProvider.OLLAMA.value,
            AIProvider.DEEPSEEK.value,  # DeepSeek性价比高
            AIProvider.KIMI.value,      # Kimi长文本能力强
            AIProvider.DOUBAO.value,    # 字节豆包
            AIProvider.ZHIPU.value, 
            AIProvider.BAIDU.value,
            AIProvider.ALIBABA.value,
            AIProvider.ANTHROPIC.value,
            AIProvider.OPENAI.value
        ]
        
        for provider in priority_order:
            if provider in available:
                return provider
        
        return available[0] if available else None
    
    def can_make_request(self, provider: str) -> bool:
        """检查是否可以发起请求"""
        if provider not in self.models_config:
            return False
        
        config = self.models_config[provider]
        if not config.enabled:
            return False
        
        stats = self.usage_stats.get(provider, AIUsageStats())
        if stats.daily_requests >= config.daily_limit:
            logger.warning(f"Provider {provider} has reached daily limit")
            return False
        
        return True
    
    def record_request(self, provider: str, tokens_used: int, success: bool = True):
        """记录请求统计"""
        if provider not in self.usage_stats:
            self.usage_stats[provider] = AIUsageStats()
        
        stats = self.usage_stats[provider]
        config = self.models_config.get(provider)
        
        # 更新统计
        stats.total_requests += 1
        stats.daily_requests += 1
        
        if success:
            stats.successful_requests += 1
            stats.total_tokens_used += tokens_used
            stats.daily_tokens += tokens_used
            
            if config:
                token_cost = (tokens_used / 1000) * config.cost_per_1k_tokens
                stats.total_cost += token_cost
                stats.daily_cost += token_cost
        else:
            stats.failed_requests += 1
        
        # 保存统计
        self.save_config()
    
    def reset_daily_stats(self):
        """重置每日统计"""
        for stats in self.usage_stats.values():
            stats.daily_requests = 0
            stats.daily_tokens = 0
            stats.daily_cost = 0.0
        
        self.save_config()
        logger.info("Daily stats reset")
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """获取使用统计摘要"""
        total_requests = sum(stats.total_requests for stats in self.usage_stats.values())
        total_cost = sum(stats.total_cost for stats in self.usage_stats.values())
        total_tokens = sum(stats.total_tokens_used for stats in self.usage_stats.values())
        
        return {
            'total_requests': total_requests,
            'total_cost': round(total_cost, 4),
            'total_tokens': total_tokens,
            'providers': {
                provider: {
                    'requests': stats.total_requests,
                    'success_rate': (stats.successful_requests / max(stats.total_requests, 1)) * 100,
                    'tokens_used': stats.total_tokens_used,
                    'cost': round(stats.total_cost, 4),
                    'daily_usage': {
                        'requests': stats.daily_requests,
                        'tokens': stats.daily_tokens,
                        'cost': round(stats.daily_cost, 4)
                    }
                }
                for provider, stats in self.usage_stats.items()
            }
        }
    
    def add_model_config(self, config: AIModelConfig):
        """添加模型配置"""
        self.models_config[config.provider] = config
        if config.provider not in self.usage_stats:
            self.usage_stats[config.provider] = AIUsageStats()
        self.save_config()
    
    def update_model_config(self, provider: str, **kwargs):
        """更新模型配置"""
        if provider in self.models_config:
            config = self.models_config[provider]
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            self.save_config()
    
    def remove_model_config(self, provider: str):
        """移除模型配置"""
        if provider in self.models_config:
            del self.models_config[provider]
        if provider in self.usage_stats:
            del self.usage_stats[provider]
        self.save_config()
    
    def test_provider_connection(self, provider: str) -> Dict[str, Any]:
        """测试AI提供商连接"""
        config = self.get_model_config(provider)
        if not config:
            return {'success': False, 'error': 'Provider not configured'}
        
        try:
            # 基本配置检查
            if not config.api_key and provider != AIProvider.OLLAMA.value:
                return {'success': False, 'error': 'API key not configured'}
            
            # 实际API连接测试
            import requests
            import json
            import time
            
            start_time = time.time()
            
            if provider == AIProvider.OLLAMA.value:
                return self._test_ollama_connection(config, start_time)
            else:
                return self._test_openai_compatible_connection(config, provider, start_time)
            
        except Exception as e:
            logger.error(f"Connection test error for {provider}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _test_ollama_connection(self, config: AIModelConfig, start_time: float) -> Dict[str, Any]:
        """测试Ollama连接"""
        import requests
        import time
        
        try:
            response = requests.get(f"{config.api_base}/api/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model['name'] for model in models]
                
                return {
                    'success': True,
                    'provider': config.provider,
                    'model': config.model_name,
                    'available_models': model_names,
                    'response_time': round(time.time() - start_time, 3),
                    'message': f'Ollama connection successful. Found {len(models)} models.'
                }
            else:
                return {'success': False, 'error': f'Ollama server returned status {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': f'Failed to connect to Ollama: {str(e)}'}
    
    def _test_openai_compatible_connection(self, config: AIModelConfig, provider: str, start_time: float) -> Dict[str, Any]:
        """测试OpenAI兼容接口连接"""
        import requests
        import json
        
        try:
            # 构建请求头
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'ChatLog-AI-Test/1.0'
            }
            
            # 不同提供商的认证方式
            if provider in [AIProvider.KIMI.value, AIProvider.DEEPSEEK.value, AIProvider.OPENAI.value]:
                headers['Authorization'] = f'Bearer {config.api_key}'
            elif provider == AIProvider.ANTHROPIC.value:
                headers['x-api-key'] = config.api_key
                headers['anthropic-version'] = '2023-06-01'
            elif provider == AIProvider.ZHIPU.value:
                headers['Authorization'] = f'Bearer {config.api_key}'
            elif provider == AIProvider.DOUBAO.value:
                headers['Authorization'] = f'Bearer {config.api_key}'
            else:
                headers['Authorization'] = f'Bearer {config.api_key}'
            
            # 构建测试请求
            test_data = {
                'model': config.model_name,
                'messages': [
                    {'role': 'user', 'content': 'Hello! Please respond with "Connection test successful" to verify the API is working.'}
                ],
                'max_tokens': 50,
                'temperature': 0.1
            }
            
            # 特殊处理不同提供商的端点
            if provider == AIProvider.ANTHROPIC.value:
                endpoint = f"{config.api_base.rstrip('/')}/messages"
                test_data = {
                    'model': config.model_name,
                    'max_tokens': 50,
                    'messages': test_data['messages']
                }
            else:
                endpoint = f"{config.api_base.rstrip('/')}/chat/completions"
            
            # 发送测试请求
            response = requests.post(
                endpoint,
                headers=headers,
                json=test_data,
                timeout=30
            )
            
            response_time = round(time.time() - start_time, 3)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    
                    # 解析响应内容
                    if provider == AIProvider.ANTHROPIC.value:
                        content = result.get('content', [{}])[0].get('text', '')
                    else:
                        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                    
                    return {
                        'success': True,
                        'provider': provider,
                        'model': config.model_name,
                        'response_time': response_time,
                        'response_content': content[:100],  # 限制响应内容长度
                        'message': f'API connection successful! Response time: {response_time}s'
                    }
                except json.JSONDecodeError:
                    return {
                        'success': True,
                        'provider': provider,
                        'model': config.model_name,
                        'response_time': response_time,
                        'message': f'API connection successful but response format unexpected. Response time: {response_time}s'
                    }
            else:
                error_detail = ''
                try:
                    error_data = response.json()
                    error_detail = error_data.get('error', {}).get('message', str(error_data))
                except:
                    error_detail = response.text[:200]
                
                return {
                    'success': False,
                    'error': f'API returned status {response.status_code}: {error_detail}',
                    'response_time': response_time
                }
                
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Request timeout (30s). Please check your network connection.'}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': 'Connection failed. Please check the API base URL.'}
        except Exception as e:
            return {'success': False, 'error': f'Unexpected error: {str(e)}'}


# 全局配置管理器实例
ai_config_manager = AIConfigManager()