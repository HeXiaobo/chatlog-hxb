"""
AI智能分类服务
基于大模型的问答内容语义分类器
"""
import json
import logging
import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import asyncio

from .ai_config import ai_config_manager, AIProvider
from .qa_classifier import QAClassifier, CategoryMatch

logger = logging.getLogger(__name__)


@dataclass
class AIClassificationResult:
    """AI分类结果"""
    category_match: CategoryMatch
    processing_time: float
    tokens_used: int
    provider_used: str
    classification_method: str  # 'ai' 或 'fallback'
    reasoning: Optional[str] = None  # AI的分类推理过程


class AIClassifier:
    """AI智能分类器"""
    
    def __init__(self):
        self.fallback_classifier = QAClassifier()  # 规则分类器作为后备
        self.system_prompts = self._init_system_prompts()
        self.min_confidence_threshold = 0.5
        self.batch_size = 25  # 增加批量分类大小以提高性能
        
    def _init_system_prompts(self) -> Dict[str, str]:
        """初始化系统提示词"""
        return {
            'classification': """你是一个专业的内容分类助手，擅长对问答内容进行准确分类。

当前支持的分类体系：
1. 产品咨询 - 关于产品功能、特性、版本、兼容性等问题
2. 技术支持 - 关于使用过程中遇到的错误、故障、bug等技术问题
3. 价格费用 - 关于产品定价、付费方案、优惠活动等费用相关问题
4. 使用教程 - 关于如何使用、操作步骤、设置配置等教学性问题
5. 售后问题 - 关于客服、反馈、投诉、退款等售后服务问题

任务要求：
1. 分析问答内容的主题和意图
2. 选择最合适的分类类别
3. 评估分类的置信度(0.0-1.0)
4. 提供分类的理由说明

输出格式（JSON）：
```json
{
  "classifications": [
    {
      "index": 0,
      "category_id": 1,
      "category_name": "产品咨询",
      "confidence": 0.85,
      "matched_keywords": ["功能", "版本"],
      "reasoning": "用户询问产品的具体功能，属于产品咨询类问题"
    }
  ]
}
```

请分析以下问答内容：""",

            'dynamic_category': """你是一个内容分析专家，能够识别新的主题分类。

任务：分析给定的问答内容，识别其主要主题和可能的新分类类别。

当前已有分类：{existing_categories}

要求：
1. 如果内容适合现有分类，选择最佳匹配
2. 如果内容不适合现有分类，建议新的分类类别
3. 提供详细的分析理由

输出格式：
```json
{
  "analysis": {
    "fits_existing": true/false,
    "best_existing_category": "类别名称",
    "confidence": 0.85,
    "suggested_new_category": {
      "name": "新分类名称",
      "description": "分类描述",
      "keywords": ["关键词1", "关键词2"]
    },
    "reasoning": "分析理由"
  }
}
```

分析内容：""",

            'bulk_classification': """你是一个高效的批量分类助手。

分类体系：
{categories}

任务：对以下多个问答对进行批量分类，要求：
1. 快速准确地判断每个问答对的分类
2. 保持分类标准的一致性
3. 对不确定的内容给出较低置信度

输出格式：
```json
{
  "results": [
    {
      "index": 0,
      "category_id": 1,
      "category_name": "产品咨询", 
      "confidence": 0.85,
      "keywords": ["功能", "版本"]
    }
  ],
  "summary": {
    "total_processed": 5,
    "avg_confidence": 0.78,
    "category_distribution": {
      "产品咨询": 2,
      "技术支持": 1,
      "使用教程": 2
    }
  }
}
```

待分类内容："""
        }
    
    async def classify_qa(self, question: str, answer: str, 
                         context: str = "", 
                         use_ai: bool = True) -> AIClassificationResult:
        """
        分类问答对的简化接口 (用于测试兼容性)
        """
        context_list = [context] if context else []
        return await self.classify_qa_with_ai(question, answer, context_list, use_ai)

    async def classify_qa_with_ai(self, question: str, answer: str, 
                                 context: List[str] = None, 
                                 use_ai: bool = True) -> AIClassificationResult:
        """
        使用AI对单个问答对进行分类
        
        Args:
            question: 问题内容
            answer: 答案内容
            context: 上下文信息
            use_ai: 是否使用AI分类
        
        Returns:
            AIClassificationResult: AI分类结果
        """
        start_time = time.time()
        
        try:
            if use_ai and self._should_use_ai_classification():
                return await self._ai_classify_single(question, answer, context, start_time)
            else:
                return await self._fallback_classify_single(question, answer, context, start_time)
                
        except Exception as e:
            logger.error(f"Classification failed: {str(e)}")
            return await self._fallback_classify_single(question, answer, context, start_time)
    
    async def classify_batch_with_ai(self, qa_data: List[Tuple[str, str, List[str]]], 
                                   use_ai: bool = True) -> List[AIClassificationResult]:
        """
        批量分类问答对
        
        Args:
            qa_data: 问答数据列表 [(question, answer, context)]
            use_ai: 是否使用AI分类
        
        Returns:
            List[AIClassificationResult]: 分类结果列表
        """
        if not qa_data:
            return []
        
        try:
            if use_ai and self._should_use_ai_classification():
                return await self._ai_classify_batch(qa_data)
            else:
                return await self._fallback_classify_batch(qa_data)
                
        except Exception as e:
            logger.error(f"Batch classification failed: {str(e)}")
            return await self._fallback_classify_batch(qa_data)
    
    def _should_use_ai_classification(self) -> bool:
        """判断是否应该使用AI分类"""
        primary_provider = ai_config_manager.get_primary_provider()
        if not primary_provider:
            logger.info("No AI provider configured, using fallback classification")
            return False
        
        if not ai_config_manager.can_make_request(primary_provider):
            logger.warning(f"Cannot make AI request to {primary_provider}, using fallback")
            return False
        
        return True
    
    async def _ai_classify_single(self, question: str, answer: str, 
                                context: List[str], start_time: float) -> AIClassificationResult:
        """使用AI对单个问答对进行分类"""
        provider = ai_config_manager.get_primary_provider()
        
        try:
            # 构建分类内容
            content = self._format_qa_for_classification(question, answer, context)
            
            # 构建提示词
            prompt = self.system_prompts['classification'] + "\n\n" + content
            
            # 调用AI API
            response = await self._call_ai_api(provider, prompt)
            
            if response:
                # 解析AI响应
                result = self._parse_classification_response(response)
                if result:
                    processing_time = time.time() - start_time
                    tokens_used = len(response) // 4  # 粗略估算
                    
                    # 记录使用统计
                    ai_config_manager.record_request(provider, tokens_used, success=True)
                    
                    return AIClassificationResult(
                        category_match=result['category_match'],
                        processing_time=processing_time,
                        tokens_used=tokens_used,
                        provider_used=provider,
                        classification_method='ai',
                        reasoning=result.get('reasoning')
                    )
            
            # AI分类失败，降级到规则分类
            return await self._fallback_classify_single(question, answer, context, start_time)
            
        except Exception as e:
            logger.error(f"AI classification failed: {str(e)}")
            return await self._fallback_classify_single(question, answer, context, start_time)
    
    async def _ai_classify_batch(self, qa_data: List[Tuple[str, str, List[str]]]) -> List[AIClassificationResult]:
        """使用AI批量分类"""
        results = []
        provider = ai_config_manager.get_primary_provider()
        
        # 分批处理
        batches = [qa_data[i:i + self.batch_size] for i in range(0, len(qa_data), self.batch_size)]
        
        for batch in batches:
            try:
                start_time = time.time()
                
                # 构建批量分类内容
                content = self._format_batch_for_classification(batch)
                
                # 构建提示词
                categories_info = self._get_categories_info()
                prompt = self.system_prompts['bulk_classification'].format(
                    categories=categories_info
                ) + "\n\n" + content
                
                # 调用AI API
                response = await self._call_ai_api(provider, prompt)
                
                if response:
                    # 解析批量分类结果
                    batch_results = self._parse_batch_classification_response(response, batch)
                    if batch_results:
                        processing_time = time.time() - start_time
                        tokens_used = len(response) // 4
                        
                        # 记录使用统计
                        ai_config_manager.record_request(provider, tokens_used, success=True)
                        
                        # 为每个结果添加统计信息
                        for result in batch_results:
                            result.processing_time = processing_time / len(batch_results)
                            result.tokens_used = tokens_used // len(batch_results)
                            result.provider_used = provider
                            result.classification_method = 'ai'
                        
                        results.extend(batch_results)
                    else:
                        # 解析失败，使用规则分类
                        fallback_results = await self._fallback_classify_batch(batch)
                        results.extend(fallback_results)
                else:
                    # AI调用失败，使用规则分类
                    fallback_results = await self._fallback_classify_batch(batch)
                    results.extend(fallback_results)
                
                # 避免频率限制
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Batch classification error: {str(e)}")
                # 降级到规则分类
                fallback_results = await self._fallback_classify_batch(batch)
                results.extend(fallback_results)
        
        return results
    
    async def _fallback_classify_single(self, question: str, answer: str, 
                                      context: List[str], start_time: float) -> AIClassificationResult:
        """使用规则分类器"""
        try:
            category_match = self.fallback_classifier.classify_qa(question, answer, context)
            processing_time = time.time() - start_time
            
            return AIClassificationResult(
                category_match=category_match,
                processing_time=processing_time,
                tokens_used=0,
                provider_used='rule_based',
                classification_method='fallback'
            )
            
        except Exception as e:
            logger.error(f"Fallback classification failed: {str(e)}")
            # 返回默认分类
            return self._create_default_classification_result(start_time)
    
    async def _fallback_classify_batch(self, qa_data: List[Tuple[str, str, List[str]]]) -> List[AIClassificationResult]:
        """批量使用规则分类器"""
        results = []
        
        for question, answer, context in qa_data:
            start_time = time.time()
            result = await self._fallback_classify_single(question, answer, context, start_time)
            results.append(result)
        
        return results
    
    def _format_qa_for_classification(self, question: str, answer: str, context: List[str]) -> str:
        """格式化问答内容供分类"""
        content_parts = [
            f"问题: {question}",
            f"回答: {answer}"
        ]
        
        if context:
            content_parts.append(f"上下文: {' | '.join(context[:3])}")  # 限制上下文长度
        
        return "\n".join(content_parts)
    
    def _format_batch_for_classification(self, batch: List[Tuple[str, str, List[str]]]) -> str:
        """格式化批量内容供分类"""
        formatted_items = []
        
        for i, (question, answer, context) in enumerate(batch):
            item_text = f"[{i}] 问题: {question}\n回答: {answer}"
            if context:
                item_text += f"\n上下文: {' | '.join(context[:2])}"
            formatted_items.append(item_text)
        
        return "\n\n".join(formatted_items)
    
    def _get_categories_info(self) -> str:
        """获取分类信息"""
        categories = [
            "1. 产品咨询 - 产品功能、特性、版本、兼容性等",
            "2. 技术支持 - 错误、故障、bug等技术问题", 
            "3. 价格费用 - 定价、付费方案、优惠等费用问题",
            "4. 使用教程 - 操作步骤、设置配置等教学问题",
            "5. 售后问题 - 客服、反馈、投诉、退款等售后服务"
        ]
        return "\n".join(categories)
    
    async def _call_ai_api(self, provider: str, prompt: str) -> Optional[str]:
        """调用AI API"""
        config = ai_config_manager.get_model_config(provider)
        if not config:
            return None
        
        try:
            # 这里需要根据不同的AI提供商实现具体的API调用
            # 实际使用时需要集成具体的AI SDK
            
            if provider == AIProvider.OPENAI.value:
                return await self._call_openai_api(config, prompt)
            elif provider == AIProvider.ANTHROPIC.value:
                return await self._call_anthropic_api(config, prompt)
            elif provider == AIProvider.ZHIPU.value:
                return await self._call_zhipu_api(config, prompt)
            # ... 其他提供商
            
            return None
            
        except Exception as e:
            logger.error(f"AI API call failed for {provider}: {str(e)}")
            return None
    
    async def _call_openai_api(self, config, prompt: str) -> Optional[str]:
        """调用OpenAI API"""
        try:
            # 这里需要实际的OpenAI API调用实现
            return None
        except ImportError:
            logger.warning("OpenAI library not installed")
            return None
    
    async def _call_anthropic_api(self, config, prompt: str) -> Optional[str]:
        """调用Anthropic API"""
        try:
            # 这里需要实际的Anthropic API调用实现
            return None
        except ImportError:
            logger.warning("Anthropic library not installed")
            return None
    
    async def _call_zhipu_api(self, config, prompt: str) -> Optional[str]:
        """调用智谱AI API"""
        try:
            # 这里需要实际的智谱AI API调用实现
            return None
        except ImportError:
            logger.warning("ZhipuAI library not installed")
            return None
    
    def _parse_classification_response(self, response: str) -> Optional[Dict]:
        """解析单个分类响应"""
        try:
            if response.startswith('```json'):
                response = response.split('```json')[1].split('```')[0]
            elif response.startswith('```'):
                response = response.split('```')[1]
            
            data = json.loads(response.strip())
            classifications = data.get('classifications', [])
            
            if classifications:
                classification = classifications[0]
                category_match = CategoryMatch(
                    category_id=classification.get('category_id', 1),
                    category_name=classification.get('category_name', '产品咨询'),
                    confidence=classification.get('confidence', 0.7),
                    matched_keywords=classification.get('matched_keywords', [])
                )
                
                return {
                    'category_match': category_match,
                    'reasoning': classification.get('reasoning', '')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to parse classification response: {str(e)}")
            return None
    
    def _parse_batch_classification_response(self, response: str, 
                                           original_batch: List) -> Optional[List[AIClassificationResult]]:
        """解析批量分类响应"""
        try:
            if response.startswith('```json'):
                response = response.split('```json')[1].split('```')[0]
            elif response.startswith('```'):
                response = response.split('```')[1]
            
            data = json.loads(response.strip())
            results_data = data.get('results', [])
            
            results = []
            for i, result_data in enumerate(results_data):
                if i < len(original_batch):
                    category_match = CategoryMatch(
                        category_id=result_data.get('category_id', 1),
                        category_name=result_data.get('category_name', '产品咨询'),
                        confidence=result_data.get('confidence', 0.7),
                        matched_keywords=result_data.get('keywords', [])
                    )
                    
                    classification_result = AIClassificationResult(
                        category_match=category_match,
                        processing_time=0,  # 稍后设置
                        tokens_used=0,      # 稍后设置
                        provider_used='',   # 稍后设置
                        classification_method='ai'
                    )
                    
                    results.append(classification_result)
            
            return results if results else None
            
        except Exception as e:
            logger.error(f"Failed to parse batch classification response: {str(e)}")
            return None
    
    def _create_default_classification_result(self, start_time: float) -> AIClassificationResult:
        """创建默认分类结果"""
        default_match = CategoryMatch(
            category_id=1,
            category_name='产品咨询',
            confidence=0.2,
            matched_keywords=[]
        )
        
        return AIClassificationResult(
            category_match=default_match,
            processing_time=time.time() - start_time,
            tokens_used=0,
            provider_used='default',
            classification_method='fallback'
        )
    
    async def suggest_new_categories(self, qa_contents: List[str]) -> List[Dict[str, Any]]:
        """基于内容建议新的分类类别"""
        provider = ai_config_manager.get_primary_provider()
        if not provider or not ai_config_manager.can_make_request(provider):
            return []
        
        try:
            # 构建分析内容
            content = "\n\n".join([f"[{i+1}] {text}" for i, text in enumerate(qa_contents[:10])])
            
            existing_categories = self._get_categories_info()
            prompt = self.system_prompts['dynamic_category'].format(
                existing_categories=existing_categories
            ) + "\n\n" + content
            
            response = await self._call_ai_api(provider, prompt)
            
            if response:
                return self._parse_category_suggestions(response)
            
        except Exception as e:
            logger.error(f"Failed to suggest new categories: {str(e)}")
        
        return []
    
    def _parse_category_suggestions(self, response: str) -> List[Dict[str, Any]]:
        """解析分类建议"""
        try:
            if response.startswith('```json'):
                response = response.split('```json')[1].split('```')[0]
            elif response.startswith('```'):
                response = response.split('```')[1]
            
            data = json.loads(response.strip())
            analysis = data.get('analysis', {})
            
            suggestions = []
            if not analysis.get('fits_existing', True):
                suggested = analysis.get('suggested_new_category', {})
                if suggested:
                    suggestions.append({
                        'name': suggested.get('name', ''),
                        'description': suggested.get('description', ''),
                        'keywords': suggested.get('keywords', []),
                        'reasoning': analysis.get('reasoning', '')
                    })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Failed to parse category suggestions: {str(e)}")
            return []
    
    async def classify_qa_batch(self, qa_data: List[Dict[str, Any]], use_ai: bool = True) -> List[Dict[str, Any]]:
        """
        批量分类问答对 (为了测试兼容性)
        
        Args:
            qa_data: 问答数据列表，格式: [{'question': str, 'answer': str, 'confidence': float, 'context': str}]
            use_ai: 是否使用AI分类
        
        Returns:
            List[Dict[str, Any]]: 分类结果列表
        """
        results = []
        
        for qa in qa_data:
            question = qa.get('question', '')
            answer = qa.get('answer', '')
            context = qa.get('context', '')
            
            try:
                result = await self.classify_qa(question, answer, context, use_ai)
                
                results.append({
                    'category': result.category_match.category_name,
                    'confidence': result.category_match.confidence,
                    'keywords': result.category_match.matched_keywords,
                    'method': result.classification_method,
                    'processing_time': result.processing_time,
                    'reasoning': result.reasoning
                })
            except Exception as e:
                logger.error(f"Failed to classify QA: {str(e)}")
                # 返回默认分类结果
                results.append({
                    'category': '其他',
                    'confidence': 0.1,
                    'keywords': [],
                    'method': 'error_fallback',
                    'processing_time': 0.0,
                    'reasoning': f"分类失败: {str(e)}"
                })
        
        return results

    def get_classification_stats(self, results) -> Dict[str, Any]:
        """获取分类统计信息 - 支持AIClassificationResult和Dict格式"""
        if not results:
            return {
                'total_classified': 0,
                'avg_confidence': 0,
                'classification_methods': {},
                'provider_usage': {},
                'total_processing_time': 0,
                'total_tokens_used': 0
            }
        
        # 分类分布
        category_dist = {}
        confidences = []
        methods = {}
        providers = {}
        total_time = 0
        total_tokens = 0
        
        for result in results:
            # 支持两种格式: AIClassificationResult 或 Dict
            if isinstance(result, dict):
                # Dict格式 (用于测试)
                category_name = result.get('category', '未分类')
                confidence = result.get('confidence', 0.0)
                method = result.get('method', 'unknown')
                processing_time = result.get('processing_time', 0.0)
                
                category_dist[category_name] = category_dist.get(category_name, 0) + 1
                confidences.append(confidence)
                methods[method] = methods.get(method, 0) + 1
                total_time += processing_time
            else:
                # AIClassificationResult格式
                category_name = result.category_match.category_name
                category_dist[category_name] = category_dist.get(category_name, 0) + 1
                confidences.append(result.category_match.confidence)
                
                # 方法统计
                methods[result.classification_method] = methods.get(result.classification_method, 0) + 1
                
                # 提供商统计
                providers[result.provider_used] = providers.get(result.provider_used, 0) + 1
                
                # 时间和token统计
                total_time += result.processing_time
                total_tokens += result.tokens_used
        
        avg_confidence = sum(confidences) / len(confidences)
        
        return {
            'total_classified': len(results),
            'avg_confidence': round(avg_confidence, 3),
            'category_distribution': category_dist,
            'classification_methods': methods,
            'provider_usage': providers,
            'total_processing_time': round(total_time, 2),
            'total_tokens_used': total_tokens,
            'high_confidence_ratio': len([c for c in confidences if c >= 0.8]) / len(confidences)
        }


# 全局实例
ai_classifier = AIClassifier()