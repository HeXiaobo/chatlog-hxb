"""
AI智能内容处理器
专门用于聊天记录的智能筛选、清洗和知识库生成
"""
import json
import logging
import re
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from .ai_config import ai_config_manager, AIProvider
from .data_extractor import QACandidate

logger = logging.getLogger(__name__)


@dataclass
class ContentAnalysisResult:
    """内容分析结果"""
    useful_messages: List[Dict[str, Any]]
    noise_messages: List[Dict[str, Any]]
    participants_analysis: Dict[str, Any]
    content_quality_score: float
    recommendations: List[str]
    processing_time: float


@dataclass
class KnowledgeBaseEntry:
    """知识库条目"""
    question: str
    answer: str
    category: str
    confidence: float
    context: str
    tags: List[str]
    source_info: Dict[str, Any]
    quality_score: float


class AIContentProcessor:
    """AI智能内容处理器
    
    实现完整的聊天记录 → 知识库转换流程：
    1. 对话质量分析
    2. 无用内容过滤
    3. 有效问答提取
    4. 内容清洗优化
    5. 知识库条目生成
    """
    
    def __init__(self):
        self.system_prompts = self._init_system_prompts()
        self.content_filters = self._init_content_filters()
        
    def _init_system_prompts(self) -> Dict[str, str]:
        """初始化系统提示词"""
        return {
            'content_analysis': """你是一个专业的聊天记录分析师，负责分析微信群聊内容的价值和质量。

**分析任务**：
1. **参与者分析**：识别活跃用户、专业程度、回答质量
2. **内容质量评估**：区分有价值信息 vs 无用闲聊
3. **对话模式识别**：问答、讨论、分享、求助等模式

**筛选标准**：
🟢 **保留内容**：
- 专业问答和技术讨论
- 经验分享和实用建议
- 问题求助和解决方案
- 重要通知和信息分享
- 有教育价值的对话

🔴 **过滤内容**：
- 日常问候和闲聊
- 无意义的表情和符号
- 重复的内容和刷屏
- 广告推销和垃圾信息
- 纯社交性质的对话

**输出格式**：
```json
{
  "content_analysis": {
    "total_messages": 100,
    "useful_count": 35,
    "noise_count": 65,
    "quality_score": 0.75
  },
  "participants": {
    "experts": ["张三", "李四"],
    "active_helpers": ["王五"],
    "question_askers": ["赵六"]
  },
  "useful_messages": [
    {
      "index": 5,
      "speaker": "张三",
      "content": "消息内容",
      "timestamp": "2024-01-01 10:00:00",
      "value_reason": "包含专业建议",
      "category": "技术问答"
    }
  ],
  "noise_messages": [
    {
      "index": 1,
      "reason": "日常问候"
    }
  ],
  "recommendations": [
    "建议重点关注张三和李四的专业回答",
    "可以过滤掉大量的日常问候消息"
  ]
}
```

请分析以下聊天记录：""",

            'qa_extraction': """你是一个专业的知识库构建专家，负责从筛选出的有价值对话中提取和整理问答对。

**提取原则**：
1. **问题识别**：
   - 直接疑问句（什么、怎么、为什么等）
   - 求助表达（请教、帮忙看看等）
   - 困惑陈述（搞不懂、不明白等）

2. **答案匹配**：
   - 必须针对特定问题
   - 提供有价值的解决方案
   - 来自不同的回答者
   - 内容完整且实用

3. **质量标准**：
   - 问题表述清楚
   - 答案准确有用
   - 具备普遍适用性
   - 适合知识库收录

**输出格式**：
```json
{
  "qa_pairs": [
    {
      "question": "如何解决数据库连接超时问题？",
      "answer": "可以通过增加连接池大小和设置合理的超时时间来解决，具体配置参数是...",
      "asker": "小王",
      "advisor": "张工程师", 
      "confidence": 0.9,
      "context": "在讨论系统性能优化时",
      "topic": "技术问题",
      "quality_indicators": ["专业术语准确", "解决方案完整", "可操作性强"]
    }
  ],
  "extraction_stats": {
    "total_qa_found": 5,
    "high_quality": 3,
    "medium_quality": 2,
    "avg_confidence": 0.82
  }
}
```

请从以下有价值的对话中提取问答对：""",

            'content_cleaning': """你是一个内容编辑专家，负责清洗和优化问答内容，使其更适合知识库存储。

**清洗任务**：
1. **语言规范化**：
   - 修正错别字和语法错误
   - 统一专业术语表达
   - 改进句子结构和可读性

2. **内容优化**：
   - 去除冗余和重复信息
   - 补充必要的上下文
   - 标准化格式和结构

3. **信息完善**：
   - 添加相关标签
   - 补充关键词
   - 建议分类标签

**输出格式**：
```json
{
  "cleaned_entries": [
    {
      "original_question": "原始问题",
      "cleaned_question": "清洗后的问题",
      "original_answer": "原始回答", 
      "cleaned_answer": "清洗后的回答",
      "suggested_category": "建议分类",
      "tags": ["标签1", "标签2"],
      "keywords": ["关键词1", "关键词2"],
      "quality_improvements": ["改进说明"],
      "final_quality_score": 0.95
    }
  ],
  "cleaning_summary": {
    "entries_processed": 5,
    "improvement_rate": 0.25,
    "common_issues_fixed": ["错别字", "格式问题"]
  }
}
```

请清洗和优化以下问答内容："""
        }
    
    def _init_content_filters(self) -> Dict[str, Any]:
        """初始化内容过滤规则"""
        return {
            'noise_patterns': [
                r'^[哈呵嘿嘻]{1,}$',  # 笑声
                r'^[好的？？！！。。，，]{1,3}$',  # 简单回复
                r'^\+1$|^同\+1$|^同意$',  # 简单附和
                r'^早上?好$|^晚安$|^午安$',  # 问候语
                r'^谢谢$|^3[qQ]$|^多谢$',  # 简单感谢
                r'^\[表情\]$|^\[图片\]$|^\[文件\]$',  # 纯媒体消息
            ],
            'spam_keywords': [
                '微商', '代理', '加盟', '赚钱', '兼职',
                '推广', '广告', '优惠', '折扣', '促销'
            ],
            'min_message_length': 5,  # 最小消息长度
            'min_meaningful_chars': 3  # 最小有意义字符数
        }
    
    async def process_chat_content(self, messages: List[Dict[str, Any]], 
                                 source_info: Dict[str, Any]) -> Dict[str, Any]:
        """完整的聊天内容处理流程
        
        Args:
            messages: 原始聊天消息列表
            source_info: 来源信息（文件名、群名等）
        
        Returns:
            包含分析结果、提取内容和知识库条目的完整结果
        """
        logger.info(f"开始处理聊天内容，消息数量: {len(messages)}")
        start_time = time.time()
        
        try:
            # 步骤1: 内容质量分析和筛选
            analysis_result = await self._analyze_content_quality(messages)
            
            # 步骤2: 从有价值内容中提取问答对
            qa_extraction_result = await self._extract_qa_pairs(
                analysis_result.useful_messages
            )
            
            # 步骤3: 内容清洗和优化
            cleaned_entries = await self._clean_and_optimize_content(
                qa_extraction_result['qa_pairs']
            )
            
            # 步骤4: 生成最终知识库条目
            knowledge_entries = self._generate_knowledge_entries(
                cleaned_entries, source_info
            )
            
            processing_time = time.time() - start_time
            
            result = {
                'success': True,
                'processing_time': processing_time,
                'content_analysis': analysis_result,
                'qa_extraction': qa_extraction_result,
                'cleaned_content': cleaned_entries,
                'knowledge_entries': knowledge_entries,
                'statistics': {
                    'original_messages': len(messages),
                    'useful_messages': len(analysis_result.useful_messages),
                    'noise_filtered': len(analysis_result.noise_messages),
                    'qa_pairs_extracted': len(qa_extraction_result.get('qa_pairs', [])),
                    'final_knowledge_entries': len(knowledge_entries),
                    'content_quality_score': analysis_result.content_quality_score,
                    'processing_efficiency': len(knowledge_entries) / len(messages) if messages else 0
                }
            }
            
            logger.info(f"内容处理完成，生成知识库条目: {len(knowledge_entries)}个")
            return result
            
        except Exception as e:
            logger.error(f"内容处理失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    async def _analyze_content_quality(self, messages: List[Dict[str, Any]]) -> ContentAnalysisResult:
        """分析内容质量和过滤无用信息"""
        logger.info("开始内容质量分析...")
        start_time = time.time()
        
        # 预过滤明显的垃圾内容
        pre_filtered = self._pre_filter_messages(messages)
        
        # 分批处理消息
        batch_size = 50  # 增加批量处理大小以提高性能
        useful_messages = []
        noise_messages = []
        
        for i in range(0, len(pre_filtered), batch_size):
            batch = pre_filtered[i:i+batch_size]
            batch_result = await self._analyze_message_batch(batch)
            
            useful_messages.extend(batch_result.get('useful_messages', []))
            noise_messages.extend(batch_result.get('noise_messages', []))
        
        # 分析参与者特征
        participants_analysis = self._analyze_participants(useful_messages)
        
        # 计算整体质量分数
        quality_score = len(useful_messages) / len(messages) if messages else 0
        
        # 生成处理建议
        recommendations = self._generate_recommendations(
            participants_analysis, quality_score, len(messages)
        )
        
        return ContentAnalysisResult(
            useful_messages=useful_messages,
            noise_messages=noise_messages,
            participants_analysis=participants_analysis,
            content_quality_score=quality_score,
            recommendations=recommendations,
            processing_time=time.time() - start_time
        )
    
    def _pre_filter_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """预过滤明显的垃圾消息"""
        filtered = []
        filters = self.content_filters
        
        for msg in messages:
            content = msg.get('content', '').strip()
            
            # 长度过滤
            if len(content) < filters['min_message_length']:
                continue
                
            # 模式匹配过滤
            is_noise = False
            for pattern in filters['noise_patterns']:
                if re.match(pattern, content):
                    is_noise = True
                    break
            
            if is_noise:
                continue
                
            # 垃圾关键词过滤
            content_lower = content.lower()
            has_spam = any(keyword in content_lower for keyword in filters['spam_keywords'])
            
            if has_spam:
                continue
                
            filtered.append(msg)
        
        logger.info(f"预过滤完成: {len(messages)} -> {len(filtered)} 消息")
        return filtered
    
    async def _analyze_message_batch(self, batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析一批消息的质量"""
        try:
            # 构建分析请求
            batch_content = self._format_messages_for_analysis(batch)
            prompt = self.system_prompts['content_analysis'] + batch_content
            
            # 调用AI进行分析
            result = await self._call_ai_api(prompt, max_tokens=2000)
            
            if result['success']:
                analysis = json.loads(result['content'])
                return analysis
            else:
                logger.warning(f"批量分析失败，使用规则后备: {result.get('error')}")
                return self._fallback_batch_analysis(batch)
                
        except Exception as e:
            logger.error(f"消息批量分析失败: {str(e)}")
            return self._fallback_batch_analysis(batch)
    
    async def _extract_qa_pairs(self, useful_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """从有价值消息中提取问答对"""
        logger.info(f"开始从{len(useful_messages)}条有价值消息中提取问答对...")
        
        try:
            # 格式化消息用于问答提取
            formatted_content = self._format_messages_for_qa_extraction(useful_messages)
            prompt = self.system_prompts['qa_extraction'] + formatted_content
            
            # 调用AI进行问答提取
            result = await self._call_ai_api(prompt, max_tokens=3000)
            
            if result['success']:
                qa_result = json.loads(result['content'])
                logger.info(f"AI提取到{len(qa_result.get('qa_pairs', []))}个问答对")
                return qa_result
            else:
                logger.warning("AI问答提取失败，使用规则后备方案")
                return self._fallback_qa_extraction(useful_messages)
                
        except Exception as e:
            logger.error(f"问答提取失败: {str(e)}")
            return {'qa_pairs': [], 'extraction_stats': {'total_qa_found': 0}}
    
    async def _clean_and_optimize_content(self, qa_pairs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """清洗和优化问答内容"""
        logger.info(f"开始清洗和优化{len(qa_pairs)}个问答对...")
        
        try:
            if not qa_pairs:
                return {'cleaned_entries': [], 'cleaning_summary': {'entries_processed': 0}}
            
            # 格式化问答对用于清洗
            formatted_content = json.dumps(qa_pairs, ensure_ascii=False, indent=2)
            prompt = self.system_prompts['content_cleaning'] + formatted_content
            
            # 调用AI进行内容清洗
            result = await self._call_ai_api(prompt, max_tokens=4000)
            
            if result['success']:
                cleaned_result = json.loads(result['content'])
                logger.info(f"内容清洗完成，处理了{len(cleaned_result.get('cleaned_entries', []))}个条目")
                return cleaned_result
            else:
                logger.warning("AI内容清洗失败，使用基础清洗")
                return self._basic_content_cleaning(qa_pairs)
                
        except Exception as e:
            logger.error(f"内容清洗失败: {str(e)}")
            return self._basic_content_cleaning(qa_pairs)
    
    def _generate_knowledge_entries(self, cleaned_content: Dict[str, Any], 
                                  source_info: Dict[str, Any]) -> List[KnowledgeBaseEntry]:
        """生成最终的知识库条目"""
        entries = []
        cleaned_entries = cleaned_content.get('cleaned_entries', [])
        
        for entry in cleaned_entries:
            knowledge_entry = KnowledgeBaseEntry(
                question=entry.get('cleaned_question', entry.get('original_question', '')),
                answer=entry.get('cleaned_answer', entry.get('original_answer', '')),
                category=entry.get('suggested_category', '未分类'),
                confidence=entry.get('confidence', 0.7),
                context=entry.get('context', ''),
                tags=entry.get('tags', []),
                source_info={
                    **source_info,
                    'processing_method': 'ai_enhanced',
                    'quality_score': entry.get('final_quality_score', 0.7)
                },
                quality_score=entry.get('final_quality_score', 0.7)
            )
            entries.append(knowledge_entry)
        
        return entries
    
    async def _call_ai_api(self, prompt: str, max_tokens: int = 2000) -> Dict[str, Any]:
        """调用AI API"""
        try:
            # 获取主要AI提供商
            primary_provider = ai_config_manager.get_primary_provider()
            if not primary_provider:
                return {'success': False, 'error': 'No AI provider available'}
            
            config = ai_config_manager.get_model_config(primary_provider)
            if not config or not ai_config_manager.can_make_request(primary_provider):
                return {'success': False, 'error': f'Provider {primary_provider} not available'}
            
            # 这里应该实现实际的AI API调用
            # 目前返回模拟结果
            return {
                'success': True,
                'content': '{"analysis": "AI processing completed"}',
                'tokens_used': 500,
                'provider': primary_provider
            }
            
        except Exception as e:
            logger.error(f"AI API调用失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    # 辅助方法
    def _format_messages_for_analysis(self, messages: List[Dict[str, Any]]) -> str:
        """格式化消息用于分析"""
        formatted = "\n对话记录:\n"
        for i, msg in enumerate(messages):
            timestamp = msg.get('timestamp', '')
            sender = msg.get('sender', '未知')
            content = msg.get('content', '')
            formatted += f"[{i}] {timestamp} {sender}: {content}\n"
        return formatted
    
    def _format_messages_for_qa_extraction(self, messages: List[Dict[str, Any]]) -> str:
        """格式化消息用于问答提取"""
        return self._format_messages_for_analysis(messages)
    
    def _analyze_participants(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析参与者特征"""
        participants = {}
        for msg in messages:
            sender = msg.get('speaker', msg.get('sender', '未知'))
            if sender not in participants:
                participants[sender] = {
                    'message_count': 0,
                    'avg_message_length': 0,
                    'categories': []
                }
            participants[sender]['message_count'] += 1
        
        return {
            'total_participants': len(participants),
            'active_users': list(participants.keys())[:5],  # 前5个活跃用户
            'participant_stats': participants
        }
    
    def _generate_recommendations(self, participants: Dict[str, Any], 
                                quality_score: float, total_messages: int) -> List[str]:
        """生成处理建议"""
        recommendations = []
        
        if quality_score < 0.3:
            recommendations.append("聊天内容质量较低，建议重新筛选聊天对象")
        elif quality_score < 0.5:
            recommendations.append("建议进一步过滤无关内容，提高处理效率")
        else:
            recommendations.append("内容质量良好，适合构建知识库")
        
        if total_messages > 1000:
            recommendations.append("消息量较大，建议分批处理以提高效率")
        
        return recommendations
    
    def _fallback_batch_analysis(self, batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """后备的批量分析方案"""
        useful_messages = []
        noise_messages = []
        
        for i, msg in enumerate(batch):
            content = msg.get('content', '')
            # 简单的规则判断
            if len(content) > 10 and ('?' in content or '吗' in content or '怎么' in content):
                useful_messages.append({
                    'index': i,
                    'speaker': msg.get('sender', ''),
                    'content': content,
                    'value_reason': '包含疑问',
                    'category': '可能问题'
                })
            else:
                noise_messages.append({'index': i, 'reason': '内容过短或无明显价值'})
        
        return {
            'useful_messages': useful_messages,
            'noise_messages': noise_messages
        }
    
    def _fallback_qa_extraction(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """后备的问答提取方案"""
        # 这里可以使用现有的规则提取器
        return {'qa_pairs': [], 'extraction_stats': {'total_qa_found': 0}}
    
    def _basic_content_cleaning(self, qa_pairs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """基础的内容清洗"""
        cleaned_entries = []
        
        for qa in qa_pairs:
            cleaned_entry = {
                'original_question': qa.get('question', ''),
                'cleaned_question': qa.get('question', '').strip(),
                'original_answer': qa.get('answer', ''),
                'cleaned_answer': qa.get('answer', '').strip(),
                'suggested_category': qa.get('topic', '未分类'),
                'tags': [],
                'keywords': [],
                'final_quality_score': qa.get('confidence', 0.7)
            }
            cleaned_entries.append(cleaned_entry)
        
        return {
            'cleaned_entries': cleaned_entries,
            'cleaning_summary': {'entries_processed': len(qa_pairs)}
        }


# 全局实例
ai_content_processor = AIContentProcessor()