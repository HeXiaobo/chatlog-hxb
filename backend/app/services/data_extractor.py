"""
微信聊天记录数据提取服务
"""
import json
import re
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class QACandidate:
    """问答候选对象"""
    question: str
    answer: str
    asker: str
    advisor: str
    timestamp: datetime
    confidence: float
    context: List[str]  # 上下文消息


class DataExtractor:
    """微信聊天记录数据提取器"""
    
    def __init__(self):
        self.qa_patterns = self._init_qa_patterns()
        self.noise_patterns = self._init_noise_patterns()
        self.confidence_threshold = 0.6
    
    def _init_qa_patterns(self) -> List[Dict[str, Any]]:
        """初始化问答识别模式"""
        return [
            {
                'name': 'direct_question',
                'question_patterns': [
                    r'.*[?？]$',  # 以问号结尾
                    r'^(如何|怎么|怎样|为什么|什么|哪个|能否|可以|请问)',  # 疑问词开头
                    r'(请教|咨询|求助)',  # 求助词
                ],
                'answer_indicators': [
                    r'^(回答|答)',  # 明确回答指示词
                    r'(可以|建议|推荐|应该|方法|步骤)',
                ],
                'confidence_boost': 0.3
            },
            {
                'name': 'problem_solution',
                'question_patterns': [
                    r'(问题|错误|故障|异常|失败)',
                    r'(不能|无法|不行|不会|不知道)',
                    r'(报错|出错|bug)',
                ],
                'answer_indicators': [
                    r'(解决|处理|修复|修改)',
                    r'(试试|尝试|检查)',
                    r'(原因|因为|由于)',
                ],
                'confidence_boost': 0.2
            },
            {
                'name': 'how_to_guide',
                'question_patterns': [
                    r'(教程|指南|说明|文档)',
                    r'(操作|使用|设置|配置)',
                ],
                'answer_indicators': [
                    r'(步骤|流程|过程)',
                    r'(首先|然后|接着|最后)',
                    r'(第[一二三四五六七八九十])',
                ],
                'confidence_boost': 0.25
            }
        ]
    
    def _init_noise_patterns(self) -> List[str]:
        """初始化噪声过滤模式"""
        return [
            r'^[。！!？?]*$',  # 只有标点符号
            r'^[哈嘿呵呀啊嗯噢哦]+$',  # 语气词
            r'^\[.*\]$',  # 系统消息
            r'^@.*',  # @某人
            r'(收到|好的|谢谢|没事|没关系)',  # 简单回复
            r'^[0-9\s]+$',  # 纯数字
            r'(图片|语音|视频|文件|表情)',  # 媒体文件
        ]
    
    def extract_from_json(self, json_data: str, source_file: str) -> List[QACandidate]:
        """
        从WeChat JSON数据中提取问答对
        
        Args:
            json_data: WeChat导出的JSON数据
            source_file: 源文件路径
        
        Returns:
            List[QACandidate]: 提取的问答候选列表
        """
        try:
            data = json.loads(json_data)
            messages = self._parse_messages(data)
            qa_candidates = self._extract_qa_pairs(messages, source_file)
            return qa_candidates
        except Exception as e:
            logger.error(f"Failed to extract data from {source_file}: {str(e)}")
            return []
    
    def _parse_messages(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析消息数据"""
        messages = []
        
        if isinstance(data, dict):
            # 处理单个群聊数据
            if 'messages' in data:
                messages.extend(self._normalize_messages(data['messages']))
            elif 'data' in data and isinstance(data['data'], list):
                messages.extend(self._normalize_messages(data['data']))
        elif isinstance(data, list):
            # 处理消息列表
            messages.extend(self._normalize_messages(data))
        
        return sorted(messages, key=lambda x: x.get('timestamp', 0))
    
    def _normalize_messages(self, raw_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """标准化消息格式"""
        normalized = []
        
        for msg in raw_messages:
            try:
                normalized_msg = {
                    'content': self._extract_content(msg),
                    'sender': self._extract_sender(msg),
                    'timestamp': self._extract_timestamp(msg),
                    'msg_type': msg.get('type', 'text'),
                    'original': msg
                }
                
                if normalized_msg['content'] and not self._is_noise(normalized_msg['content']):
                    normalized.append(normalized_msg)
            except Exception as e:
                logger.debug(f"Failed to normalize message: {str(e)}")
                continue
        
        return normalized
    
    def _extract_content(self, msg: Dict[str, Any]) -> str:
        """提取消息内容"""
        content = ''
        
        # 尝试不同的字段名
        for field in ['content', 'text', 'message', 'body']:
            if field in msg:
                content = str(msg[field]).strip()
                break
        
        return content
    
    def _extract_sender(self, msg: Dict[str, Any]) -> str:
        """提取发送者信息"""
        for field in ['sender', 'from', 'user', 'nickname', 'name']:
            if field in msg and msg[field]:
                return str(msg[field]).strip()
        return 'Unknown'
    
    def _extract_timestamp(self, msg: Dict[str, Any]) -> datetime:
        """提取时间戳"""
        timestamp = None
        
        for field in ['timestamp', 'time', 'created_at', 'date']:
            if field in msg and msg[field]:
                try:
                    timestamp = msg[field]
                    break
                except:
                    continue
        
        if timestamp:
            try:
                if isinstance(timestamp, str):
                    # 尝试解析字符串时间
                    formats = [
                        '%Y-%m-%d %H:%M:%S',
                        '%Y/%m/%d %H:%M:%S',
                        '%Y-%m-%dT%H:%M:%S',
                        '%Y-%m-%dT%H:%M:%SZ'
                    ]
                    for fmt in formats:
                        try:
                            return datetime.strptime(timestamp, fmt)
                        except ValueError:
                            continue
                elif isinstance(timestamp, (int, float)):
                    # Unix时间戳
                    if timestamp > 1e10:  # 毫秒时间戳
                        timestamp = timestamp / 1000
                    return datetime.fromtimestamp(timestamp)
                elif isinstance(timestamp, datetime):
                    return timestamp
            except Exception as e:
                logger.debug(f"Failed to parse timestamp {timestamp}: {str(e)}")
        
        return datetime.now()
    
    def _is_noise(self, content: str) -> bool:
        """判断是否为噪声内容"""
        if len(content.strip()) < 2:
            return True
        
        for pattern in self.noise_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        
        return False
    
    def _extract_qa_pairs(self, messages: List[Dict[str, Any]], source_file: str) -> List[QACandidate]:
        """提取问答对"""
        qa_candidates = []
        
        for i, msg in enumerate(messages):
            if self._is_potential_question(msg['content']):
                answers = self._find_answers(messages, i, msg)
                
                for answer_msg, confidence in answers:
                    if confidence >= self.confidence_threshold:
                        context = self._extract_context(messages, i, answer_msg.get('index', i+1))
                        
                        qa_candidate = QACandidate(
                            question=msg['content'],
                            answer=answer_msg['content'],
                            asker=msg['sender'],
                            advisor=answer_msg['sender'],
                            timestamp=msg['timestamp'],
                            confidence=confidence,
                            context=context
                        )
                        qa_candidates.append(qa_candidate)
        
        return self._deduplicate_qa(qa_candidates)
    
    def _is_potential_question(self, content: str) -> bool:
        """判断是否为潜在问题"""
        question_score = 0
        
        for pattern_group in self.qa_patterns:
            for pattern in pattern_group['question_patterns']:
                if re.search(pattern, content, re.IGNORECASE):
                    question_score += 1
                    break
        
        # 问句长度判断
        if len(content) > 5:
            question_score += 0.5
        
        # 包含疑问词
        question_words = ['什么', '如何', '怎么', '为什么', '哪里', '哪个', '能否', '可以', '请问']
        for word in question_words:
            if word in content:
                question_score += 0.5
                break
        
        return question_score >= 1
    
    def _find_answers(self, messages: List[Dict[str, Any]], question_index: int, question_msg: Dict[str, Any]) -> List[Tuple[Dict[str, Any], float]]:
        """寻找问题的答案"""
        answers = []
        question_time = question_msg['timestamp']
        
        # 在问题后的10条消息中寻找答案
        search_range = min(len(messages), question_index + 11)
        
        for i in range(question_index + 1, search_range):
            candidate_msg = messages[i]
            
            # 跳过同一人的后续消息（可能是补充问题）
            if candidate_msg['sender'] == question_msg['sender']:
                continue
            
            # 时间间隔不能太长（5分钟内）
            time_diff = (candidate_msg['timestamp'] - question_time).total_seconds()
            if time_diff > 300:  # 5分钟
                break
            
            # 计算答案置信度
            confidence = self._calculate_answer_confidence(
                question_msg['content'], 
                candidate_msg['content']
            )
            
            if confidence > 0.3:  # 最低答案阈值
                candidate_msg['index'] = i  # 添加索引信息
                answers.append((candidate_msg, confidence))
        
        return sorted(answers, key=lambda x: x[1], reverse=True)[:3]  # 返回最多3个答案
    
    def _calculate_answer_confidence(self, question: str, answer: str) -> float:
        """计算答案置信度"""
        confidence = 0.0
        
        # 基础长度判断
        if len(answer) < 5:
            return 0.1
        
        # 答案指示词匹配
        for pattern_group in self.qa_patterns:
            for pattern in pattern_group.get('answer_indicators', []):
                if re.search(pattern, answer, re.IGNORECASE):
                    confidence += pattern_group.get('confidence_boost', 0.2)
                    break
        
        # 关键词重叠
        question_words = set(re.findall(r'[\u4e00-\u9fff]+', question))
        answer_words = set(re.findall(r'[\u4e00-\u9fff]+', answer))
        
        if question_words and answer_words:
            overlap_ratio = len(question_words & answer_words) / len(question_words | answer_words)
            confidence += overlap_ratio * 0.3
        
        # 答案结构特征
        if re.search(r'(可以|建议|推荐|方法|步骤|解决|处理)', answer):
            confidence += 0.2
        
        if re.search(r'(首先|然后|接着|最后|第[一二三四五六七八九十])', answer):
            confidence += 0.15
        
        # 答案长度合理性
        if 10 <= len(answer) <= 200:
            confidence += 0.1
        elif len(answer) > 200:
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def _extract_context(self, messages: List[Dict[str, Any]], question_index: int, answer_index: int) -> List[str]:
        """提取上下文"""
        context = []
        
        # 获取问题前2条和答案后1条消息作为上下文
        start_idx = max(0, question_index - 2)
        end_idx = min(len(messages), answer_index + 2)
        
        for i in range(start_idx, end_idx):
            if i != question_index and i != answer_index:
                msg = messages[i]
                context.append(f"{msg['sender']}: {msg['content']}")
        
        return context
    
    def _deduplicate_qa(self, qa_candidates: List[QACandidate]) -> List[QACandidate]:
        """去重问答对"""
        seen = set()
        unique_candidates = []
        
        for qa in sorted(qa_candidates, key=lambda x: x.confidence, reverse=True):
            # 简单的内容指纹
            fingerprint = (
                qa.question[:50],  # 问题前50字符
                qa.answer[:50],    # 答案前50字符
                qa.asker,
                qa.advisor
            )
            
            if fingerprint not in seen:
                seen.add(fingerprint)
                unique_candidates.append(qa)
        
        return unique_candidates
    
    def get_extraction_stats(self, qa_candidates: List[QACandidate]) -> Dict[str, Any]:
        """获取提取统计信息"""
        if not qa_candidates:
            return {
                'total_extracted': 0,
                'avg_confidence': 0,
                'confidence_distribution': {},
                'top_advisors': [],
                'extraction_quality': 'poor'
            }
        
        confidences = [qa.confidence for qa in qa_candidates]
        avg_confidence = sum(confidences) / len(confidences)
        
        # 置信度分布
        confidence_dist = {
            'high': len([c for c in confidences if c >= 0.8]),
            'medium': len([c for c in confidences if 0.6 <= c < 0.8]),
            'low': len([c for c in confidences if c < 0.6])
        }
        
        # 热门回答者
        advisor_count = {}
        for qa in qa_candidates:
            advisor_count[qa.advisor] = advisor_count.get(qa.advisor, 0) + 1
        
        top_advisors = sorted(advisor_count.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # 提取质量评估
        quality = 'excellent' if avg_confidence >= 0.8 else \
                  'good' if avg_confidence >= 0.7 else \
                  'fair' if avg_confidence >= 0.6 else 'poor'
        
        return {
            'total_extracted': len(qa_candidates),
            'avg_confidence': round(avg_confidence, 3),
            'confidence_distribution': confidence_dist,
            'top_advisors': top_advisors,
            'extraction_quality': quality
        }