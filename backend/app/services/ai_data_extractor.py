"""
AI智能数据提取服务
基于大模型的微信对话问答提取器
"""
import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import asyncio
import time

from .ai_config import ai_config_manager, AIProvider
from .data_extractor import QACandidate, DataExtractor

logger = logging.getLogger(__name__)


@dataclass
class AIExtractionResult:
    """AI提取结果"""
    qa_pairs: List[QACandidate]
    confidence_score: float
    processing_time: float
    tokens_used: int
    provider_used: str
    extraction_method: str  # 'ai' 或 'fallback'


class AIDataExtractor:
    """AI智能数据提取器"""
    
    def __init__(self):
        self.fallback_extractor = DataExtractor()  # 规则提取器作为后备
        self.system_prompts = self._init_system_prompts()
        self.max_messages_per_batch = 50  # 每批处理的消息数量
        self.min_confidence_threshold = 0.6
        
    def _init_system_prompts(self) -> Dict[str, str]:
        """初始化系统提示词"""
        return {
            'extraction': """你是一个专业的对话分析助手，擅长从微信群聊记录中识别和提取问答对。

任务要求：
1. 分析提供的对话记录，识别其中的问答关系
2. 一个有效的问答对应该包含：
   - 明确的问题或求助信息
   - 针对该问题的有价值回答
   - 问答双方是不同的人
   - 回答内容对问题有实际帮助

3. 提取标准：
   - 问题可以是直接疑问句、求助、咨询等
   - 回答应该是有针对性的建议、解释、指导等
   - 避免提取日常闲聊、问候、简单确认等
   - 评估每个问答对的有用性和置信度

4. 输出格式（JSON）：
```json
{
  "qa_pairs": [
    {
      "question": "问题内容",
      "answer": "回答内容", 
      "asker": "提问者昵称",
      "advisor": "回答者昵称",
      "confidence": 0.85,
      "context_summary": "上下文摘要",
      "topic": "主题分类"
    }
  ],
  "summary": {
    "total_found": 3,
    "high_confidence": 2,
    "avg_confidence": 0.78
  }
}
```

请分析以下对话记录：""",

            'quality_check': """请评估以下问答对的质量和准确性。

评估标准：
1. 问题是否清晰明确？
2. 回答是否针对问题且有价值？
3. 问答关系是否正确匹配？
4. 内容是否适合作为知识库？

输出格式：
```json
{
  "overall_quality": 0.85,
  "issues_found": ["问题描述"],
  "suggestions": ["改进建议"],
  "approved_pairs": [{"index": 0, "confidence": 0.9}],
  "rejected_pairs": [{"index": 1, "reason": "答非所问"}]
}
```

问答对数据：""",

            'content_enhancement': """请优化以下问答对的内容质量。

优化要求：
1. 使问题表达更清晰简洁
2. 使回答更完整准确
3. 去除无关信息和口语化表达
4. 保持原意不变
5. 适合作为知识库内容

输出格式：
```json
{
  "enhanced_pairs": [
    {
      "original_question": "原问题",
      "enhanced_question": "优化后问题",
      "original_answer": "原回答", 
      "enhanced_answer": "优化后回答",
      "improvement_notes": "优化说明"
    }
  ]
}
```

待优化内容："""
        }
    
    async def extract_from_json(self, json_data: str, source_file: str, 
                               use_ai: bool = True) -> AIExtractionResult:
        """
        从WeChat JSON数据中提取问答对
        
        Args:
            json_data: WeChat导出的JSON数据
            source_file: 源文件路径
            use_ai: 是否使用AI提取
        
        Returns:
            AIExtractionResult: AI提取结果
        """
        start_time = time.time()
        
        try:
            # 解析消息数据
            data = json.loads(json_data)
            messages = self.fallback_extractor._parse_messages(data)
            
            if len(messages) == 0:
                logger.warning(f"No valid messages found in {source_file}")
                return self._create_empty_result(start_time, 'fallback')
            
            logger.info(f"Parsed {len(messages)} messages from {source_file}")
            
            # 决定是否使用AI提取
            if use_ai and self._should_use_ai_extraction(messages):
                return await self._ai_extract(messages, source_file, start_time)
            else:
                return await self._fallback_extract(messages, source_file, start_time)
                
        except Exception as e:
            logger.error(f"Failed to extract from {source_file}: {str(e)}")
            return self._create_error_result(start_time, str(e))
    
    def _should_use_ai_extraction(self, messages: List[Dict]) -> bool:
        """判断是否应该使用AI提取"""
        # 检查是否有可用的AI配置
        primary_provider = ai_config_manager.get_primary_provider()
        if not primary_provider:
            logger.info("No AI provider configured, using fallback extraction")
            return False
        
        if not ai_config_manager.can_make_request(primary_provider):
            logger.warning(f"Cannot make AI request to {primary_provider}, using fallback")
            return False
        
        # 如果消息数量太少，使用规则提取可能就足够了
        if len(messages) < 10:
            logger.info("Message count too low for AI extraction")
            return False
        
        return True
    
    async def _ai_extract(self, messages: List[Dict], source_file: str, 
                         start_time: float) -> AIExtractionResult:
        """使用AI进行提取"""
        try:
            # 分批处理消息
            all_qa_pairs = []
            total_tokens = 0
            provider_used = ai_config_manager.get_primary_provider()
            
            batches = self._split_messages_to_batches(messages)
            logger.info(f"Processing {len(batches)} batches with AI extraction")
            
            for i, batch in enumerate(batches):
                logger.info(f"Processing batch {i+1}/{len(batches)}")
                
                # 调用AI提取
                batch_result = await self._extract_batch_with_ai(batch, provider_used)
                
                if batch_result:
                    all_qa_pairs.extend(batch_result['qa_pairs'])
                    total_tokens += batch_result.get('tokens_used', 0)
                
                # 避免频率限制
                await asyncio.sleep(0.5)
            
            # 后处理：去重、质量检查
            final_qa_pairs = await self._post_process_qa_pairs(all_qa_pairs)
            
            processing_time = time.time() - start_time
            confidence_score = self._calculate_overall_confidence(final_qa_pairs)
            
            # 记录使用统计
            ai_config_manager.record_request(
                provider_used, 
                total_tokens, 
                success=True
            )
            
            logger.info(f"AI extraction completed: {len(final_qa_pairs)} QA pairs, "
                       f"confidence: {confidence_score:.2f}")
            
            return AIExtractionResult(
                qa_pairs=final_qa_pairs,
                confidence_score=confidence_score,
                processing_time=processing_time,
                tokens_used=total_tokens,
                provider_used=provider_used,
                extraction_method='ai'
            )
            
        except Exception as e:
            logger.error(f"AI extraction failed: {str(e)}")
            # 降级到规则提取
            return await self._fallback_extract(messages, source_file, start_time)
    
    async def _fallback_extract(self, messages: List[Dict], source_file: str,
                               start_time: float) -> AIExtractionResult:
        """使用规则提取器作为后备方案"""
        try:
            logger.info("Using fallback rule-based extraction")
            
            # 重构消息为规则提取器可以处理的格式
            json_data = json.dumps(messages, ensure_ascii=False)
            qa_candidates = self.fallback_extractor.extract_from_json(
                json_data, source_file
            )
            
            processing_time = time.time() - start_time
            confidence_score = self._calculate_overall_confidence(qa_candidates)
            
            return AIExtractionResult(
                qa_pairs=qa_candidates,
                confidence_score=confidence_score,
                processing_time=processing_time,
                tokens_used=0,
                provider_used='rule_based',
                extraction_method='fallback'
            )
            
        except Exception as e:
            logger.error(f"Fallback extraction failed: {str(e)}")
            return self._create_error_result(start_time, str(e))
    
    def _split_messages_to_batches(self, messages: List[Dict]) -> List[List[Dict]]:
        """将消息分批处理"""
        batches = []
        
        for i in range(0, len(messages), self.max_messages_per_batch):
            batch = messages[i:i + self.max_messages_per_batch]
            batches.append(batch)
        
        return batches
    
    async def _extract_batch_with_ai(self, messages: List[Dict], 
                                   provider: str) -> Optional[Dict]:
        """使用AI提取一批消息"""
        try:
            # 构建对话上下文
            conversation_text = self._format_messages_for_ai(messages)
            
            # 构建提示词
            prompt = self.system_prompts['extraction'] + "\n\n" + conversation_text
            
            # 调用AI API
            response = await self._call_ai_api(provider, prompt)
            
            if response:
                # 解析AI响应
                return self._parse_ai_response(response, messages)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract batch with AI: {str(e)}")
            return None
    
    def _format_messages_for_ai(self, messages: List[Dict]) -> str:
        """格式化消息供AI分析"""
        formatted_lines = []
        
        for i, msg in enumerate(messages):
            timestamp_str = ""
            if isinstance(msg.get('timestamp'), datetime):
                timestamp_str = msg['timestamp'].strftime("%H:%M")
            
            formatted_lines.append(
                f"[{i+1}] {timestamp_str} {msg['sender']}: {msg['content']}"
            )
        
        return "\n".join(formatted_lines)
    
    async def _call_ai_api(self, provider: str, prompt: str) -> Optional[str]:
        """调用AI API"""
        config = ai_config_manager.get_model_config(provider)
        if not config:
            return None
        
        try:
            # 这里需要根据不同的AI提供商实现具体的API调用
            # 为了简化示例，这里返回模拟响应
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
        """调用OpenAI API（需要安装openai库）"""
        try:
            # 这里需要实际的OpenAI API调用
            # import openai
            # 示例代码，需要实际实现
            return None
        except ImportError:
            logger.warning("OpenAI library not installed")
            return None
    
    async def _call_anthropic_api(self, config, prompt: str) -> Optional[str]:
        """调用Anthropic API"""
        try:
            # 这里需要实际的Anthropic API调用
            # 示例代码，需要实际实现
            return None
        except ImportError:
            logger.warning("Anthropic library not installed")
            return None
    
    async def _call_zhipu_api(self, config, prompt: str) -> Optional[str]:
        """调用智谱AI API"""
        try:
            # 这里需要实际的智谱AI API调用
            # 示例代码，需要实际实现
            return None
        except ImportError:
            logger.warning("ZhipuAI library not installed")
            return None
    
    def _parse_ai_response(self, response: str, original_messages: List[Dict]) -> Dict:
        """解析AI响应"""
        try:
            # 尝试解析JSON响应
            if response.startswith('```json'):
                response = response.split('```json')[1].split('```')[0]
            elif response.startswith('```'):
                response = response.split('```')[1]
            
            data = json.loads(response.strip())
            
            # 转换为QACandidate对象
            qa_candidates = []
            
            for qa_data in data.get('qa_pairs', []):
                try:
                    # 寻找原始消息的时间戳
                    timestamp = datetime.now()
                    for msg in original_messages:
                        if msg['sender'] == qa_data.get('asker', ''):
                            timestamp = msg.get('timestamp', datetime.now())
                            break
                    
                    qa_candidate = QACandidate(
                        question=qa_data.get('question', ''),
                        answer=qa_data.get('answer', ''),
                        asker=qa_data.get('asker', ''),
                        advisor=qa_data.get('advisor', ''),
                        timestamp=timestamp,
                        confidence=qa_data.get('confidence', 0.7),
                        context=[qa_data.get('context_summary', '')]
                    )
                    
                    qa_candidates.append(qa_candidate)
                    
                except Exception as e:
                    logger.error(f"Failed to parse QA candidate: {str(e)}")
                    continue
            
            return {
                'qa_pairs': qa_candidates,
                'tokens_used': len(response) // 4,  # 粗略估算
                'summary': data.get('summary', {})
            }
            
        except Exception as e:
            logger.error(f"Failed to parse AI response: {str(e)}")
            return {'qa_pairs': [], 'tokens_used': 0}
    
    async def _post_process_qa_pairs(self, qa_pairs: List[QACandidate]) -> List[QACandidate]:
        """后处理问答对：去重、质量检查等"""
        if not qa_pairs:
            return []
        
        # 去重
        unique_pairs = self._deduplicate_qa_pairs(qa_pairs)
        
        # 质量过滤
        filtered_pairs = [
            qa for qa in unique_pairs 
            if qa.confidence >= self.min_confidence_threshold and 
               len(qa.question.strip()) >= 5 and 
               len(qa.answer.strip()) >= 10
        ]
        
        logger.info(f"Post-processing: {len(qa_pairs)} -> {len(unique_pairs)} -> {len(filtered_pairs)}")
        
        return filtered_pairs
    
    def _deduplicate_qa_pairs(self, qa_pairs: List[QACandidate]) -> List[QACandidate]:
        """去重问答对"""
        seen = set()
        unique_pairs = []
        
        for qa in sorted(qa_pairs, key=lambda x: x.confidence, reverse=True):
            # 创建内容指纹
            fingerprint = self._create_content_fingerprint(qa.question, qa.answer)
            
            if fingerprint not in seen:
                seen.add(fingerprint)
                unique_pairs.append(qa)
        
        return unique_pairs
    
    def _create_content_fingerprint(self, question: str, answer: str) -> str:
        """创建内容指纹"""
        # 标准化文本
        q_normalized = re.sub(r'\s+', ' ', question.lower().strip())
        a_normalized = re.sub(r'\s+', ' ', answer.lower().strip())
        
        return f"{q_normalized[:100]}|{a_normalized[:100]}"
    
    def _calculate_overall_confidence(self, qa_pairs: List[QACandidate]) -> float:
        """计算总体置信度"""
        if not qa_pairs:
            return 0.0
        
        return sum(qa.confidence for qa in qa_pairs) / len(qa_pairs)
    
    def _create_empty_result(self, start_time: float, method: str) -> AIExtractionResult:
        """创建空结果"""
        return AIExtractionResult(
            qa_pairs=[],
            confidence_score=0.0,
            processing_time=time.time() - start_time,
            tokens_used=0,
            provider_used='none',
            extraction_method=method
        )
    
    def _create_error_result(self, start_time: float, error: str) -> AIExtractionResult:
        """创建错误结果"""
        logger.error(f"Extraction error: {error}")
        return AIExtractionResult(
            qa_pairs=[],
            confidence_score=0.0,
            processing_time=time.time() - start_time,
            tokens_used=0,
            provider_used='error',
            extraction_method='error'
        )
    
    def get_extraction_stats(self, result: AIExtractionResult) -> Dict[str, Any]:
        """获取提取统计信息"""
        if not result.qa_pairs:
            return {
                'total_extracted': 0,
                'avg_confidence': 0,
                'extraction_method': result.extraction_method,
                'provider_used': result.provider_used,
                'processing_time': result.processing_time,
                'tokens_used': result.tokens_used,
                'extraction_quality': 'no_results'
            }
        
        confidences = [qa.confidence for qa in result.qa_pairs]
        avg_confidence = sum(confidences) / len(confidences)
        
        # 置信度分布
        confidence_dist = {
            'high': len([c for c in confidences if c >= 0.8]),
            'medium': len([c for c in confidences if 0.6 <= c < 0.8]),
            'low': len([c for c in confidences if c < 0.6])
        }
        
        # 质量评估
        quality = 'excellent' if avg_confidence >= 0.8 else \
                  'good' if avg_confidence >= 0.7 else \
                  'fair' if avg_confidence >= 0.6 else 'poor'
        
        return {
            'total_extracted': len(result.qa_pairs),
            'avg_confidence': round(avg_confidence, 3),
            'confidence_distribution': confidence_dist,
            'extraction_method': result.extraction_method,
            'provider_used': result.provider_used,
            'processing_time': round(result.processing_time, 2),
            'tokens_used': result.tokens_used,
            'extraction_quality': quality,
            'confidence_score': result.confidence_score
        }