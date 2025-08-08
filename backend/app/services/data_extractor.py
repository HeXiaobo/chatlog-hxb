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
        self.confidence_threshold = 0.1  # 进一步降低阈值，适应真实聊天场景
    
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
            },
            {
                'name': 'casual_conversation',
                'question_patterns': [
                    r'.*[?？].*',  # 包含问号的任何内容
                    r'(什么时候|几点|多久|时间)',  # 时间相关问题
                    r'(哪里|在哪|地点|位置)',  # 地点相关问题
                    r'(方便|可以|能不能|行吗)',  # 询问可行性
                ],
                'answer_indicators': [
                    r'(可以|行|好|没问题|OK)',  # 肯定回答
                    r'(不行|不可以|不方便|没时间)',  # 否定回答
                    r'(点|分钟|小时|明天|今天)',  # 时间回答
                ],
                'confidence_boost': 0.15
            },
            {
                'name': 'educational_consultation',
                'question_patterns': [
                    r'.*[您你].*(有|什么|怎么).*(好的)?.*[办法方法建议吗].*[？?]?',  # 请教问题：您有好的办法吗？
                    r'.*老师.*[，,].*[问咨询请教].*',  # 老师，我想咨询/问...
                    r'.*[如何怎么什么].*[申请办理处理].*[？?]?',  # 如何申请...
                    r'.*(FAFSA|CSS|学费|助学金|申请|学校|孩子).*[问题困惑疑问].*',  # 教育相关问题
                    r'.*[该怎么应该].*[办做处理].*[？?]?',  # 该怎么办？
                ],
                'answer_indicators': [
                    r'(我想说|我建议|我的建议|根据经验)',  # 专业建议开头
                    r'(首先|第一|第二|最重要的是)',  # 步骤式回答
                    r'(这个问题|关于这个|针对这种情况)',  # 针对性回答
                    r'(需要注意|要记住|关键是)',  # 要点提醒
                    r'(申请|学校|FAFSA|CSS|助学金)',  # 专业术语回答
                ],
                'confidence_boost': 0.3
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
            print(f"[DEBUG] === DEBUGGING IMPORT ===")
            print(f"[DEBUG] Data from {source_file}")
            print(f"[DEBUG] Data type: {type(data)}")
            logger.info(f"=== DEBUGGING IMPORT ===")
            logger.info(f"Data from {source_file}")
            logger.info(f"Data type: {type(data)}")
            
            if isinstance(data, dict):
                print(f"[DEBUG] Dict keys: {list(data.keys())}")
                logger.info(f"Dict keys: {list(data.keys())}")
            elif isinstance(data, list):
                print(f"[DEBUG] List length: {len(data)}")
                logger.info(f"List length: {len(data)}")
                if len(data) > 0:
                    print(f"[DEBUG] First item type: {type(data[0])}")
                    logger.info(f"First item type: {type(data[0])}")
                    if isinstance(data[0], dict):
                        print(f"[DEBUG] First item keys: {list(data[0].keys())}")
                        print(f"[DEBUG] First item sample: {str(data[0])[:300]}")
                        logger.info(f"First item keys: {list(data[0].keys())}")
                        logger.info(f"First item sample: {str(data[0])[:300]}")
            
            messages = self._parse_messages(data)
            logger.info(f"=== AFTER PARSING ===")
            logger.info(f"Parsed {len(messages)} normalized messages")
            
            # 打印前几条消息样本
            for i, msg in enumerate(messages[:3]):
                logger.info(f"Message {i+1}: sender={msg.get('sender')}, content={msg.get('content', '')[:50]}...")
            
            if len(messages) == 0:
                logger.warning(f"No valid messages found in {source_file}")
                return []
            
            qa_candidates = self._extract_qa_pairs(messages, source_file)
            logger.info(f"=== FINAL RESULT ===")
            logger.info(f"Extracted {len(qa_candidates)} QA candidates from {source_file}")
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
                # 检查是否是前端转换的简化格式
                if self._is_frontend_format(msg):
                    logger.info(f"Processing frontend format message: {msg.get('id', 'no-id')}")
                    normalized_msg = self._normalize_frontend_message(msg)
                    if normalized_msg:
                        if self._is_noise(normalized_msg['content']):
                            logger.info(f"Message filtered as noise: {normalized_msg['content'][:50]}")
                        else:
                            logger.info(f"Added normalized message: {normalized_msg['content'][:50]}")
                            normalized.append(normalized_msg)
                    else:
                        logger.info(f"Failed to normalize message: {msg}")
                    continue
                
                # 处理原始chatlog格式
                # 跳过chatlog格式的无效消息类型
                msg_type = msg.get('type', 1)
                if msg_type in [3, 10000]:  # 系统消息等无效类型
                    continue
                
                # 跳过没有发送者的消息
                if not msg.get('senderName') and not msg.get('sender') and not msg.get('from_user'):
                    continue
                
                content = self._extract_content(msg)
                
                # 跳过内容过短或为空的消息 (放宽限制以便原始消息保存)
                if not content or len(content.strip()) < 2:
                    continue
                
                # 跳过纯表情或特殊字符
                if re.match(r'^[\s\U0001F300-\U0001F9FF\u2600-\u27BF\u2B05-\u2B07\u2934-\u2935\u2B05-\u2B07\u25B6\u25C0\u23CF-\u23FA\U0001F680-\U0001F6FF]+$', content):
                    continue
                
                normalized_msg = {
                    'content': content,
                    'sender': self._extract_sender(msg),
                    'timestamp': self._extract_timestamp(msg),
                    'msg_type': msg_type,
                    'original': msg
                }
                
                if not self._is_noise(normalized_msg['content']):
                    normalized.append(normalized_msg)
            except Exception as e:
                logger.debug(f"Failed to normalize message: {str(e)}")
                continue
        
        return normalized
    
    def _is_frontend_format(self, msg: Dict[str, Any]) -> bool:
        """判断是否是前端转换的简化格式"""
        # 前端格式特征：有id, timestamp, from_user, content, message_type字段
        required_fields = ['id', 'timestamp', 'from_user', 'content', 'message_type']
        result = all(field in msg for field in required_fields)
        
        # 如果不是前端格式，检查是否是原始chatlog格式但有基本字段
        if not result:
            # 检查是否有基本的消息结构（更宽松的检测）
            basic_fields = ['id', 'content'] 
            has_sender = any(field in msg for field in ['senderName', 'sender', 'from_user', 'from'])
            has_basic = all(field in msg for field in basic_fields) and has_sender
            
            if has_basic:
                logger.debug(f"Detected basic message format with fields: {list(msg.keys())}")
                return True
            
            logger.debug(f"Not frontend format - missing fields: {[f for f in required_fields if f not in msg]}")
            logger.debug(f"Available fields: {list(msg.keys())}")
        
        return result
    
    def _normalize_frontend_message(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """标准化前端转换的消息格式"""
        try:
            content = str(msg.get('content', '')).strip()
            
            # 跳过内容过短或为空的消息 (进一步放宽以支持原始消息保存)
            if not content or len(content) < 2:
                return None
            
            # 跳过纯表情或特殊字符
            if re.match(r'^[\s\U0001F300-\U0001F9FF\u2600-\u27BF\u2B05-\u2B07\u2934-\u2935\u2B05-\u2B07\u25B6\u25C0\u23CF-\u23FA\U0001F680-\U0001F6FF]+$', content):
                return None
            
            # 解析时间戳（支持多种格式）
            parsed_timestamp = self._extract_timestamp(msg)
            
            # 提取发送者（支持多种字段名）
            sender = self._extract_sender(msg)
            
            return {
                'content': content,
                'sender': sender,
                'timestamp': parsed_timestamp,
                'msg_type': 1,  # 文本消息
                'original': msg
            }
        except Exception as e:
            logger.debug(f"Failed to normalize frontend message: {str(e)}")
            return None
    
    def _extract_content(self, msg: Dict[str, Any]) -> str:
        """提取消息内容"""
        content = ''
        
        # 优先处理chatlog格式的复杂内容结构
        if 'contents' in msg and isinstance(msg['contents'], dict):
            contents = msg['contents']
            
            # 处理描述内容
            if contents.get('desc'):
                content = str(contents['desc']).strip()
            
            # 处理嵌套的聊天记录内容
            elif contents.get('recordInfo') and contents['recordInfo'].get('DataList'):
                data_list = contents['recordInfo']['DataList']
                if data_list.get('DataItems'):
                    for item in data_list['DataItems']:
                        if item.get('DataDesc'):
                            nested_content = str(item['DataDesc']).strip()
                            if nested_content and len(nested_content) > len(content):
                                content = nested_content
        
        # 如果没有找到复杂内容，尝试标准字段
        if not content:
            for field in ['content', 'text', 'message', 'body']:
                if field in msg and msg[field]:
                    content = str(msg[field]).strip()
                    break
        
        # 清理内容格式
        if content:
            # 移除用户名前缀（如 "林: "）
            import re
            content = re.sub(r'^[^:：]+[:：]\s*', '', content)
            # 移除多余的空白字符
            content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    def _extract_sender(self, msg: Dict[str, Any]) -> str:
        """提取发送者信息"""
        # 优先处理chatlog格式的发送者字段
        if 'senderName' in msg and msg['senderName']:
            return str(msg['senderName']).strip()
        
        # 尝试其他常见字段
        for field in ['sender', 'from', 'user', 'nickname', 'name', 'from_user']:
            if field in msg and msg[field]:
                return str(msg[field]).strip()
        return 'Unknown'
    
    def _extract_timestamp(self, msg: Dict[str, Any]) -> datetime:
        """提取时间戳"""
        timestamp = None
        
        for field in ['timestamp', 'time', 'created_at', 'date']:
            if field in msg and msg[field] is not None:
                timestamp = msg[field]
                logger.debug(f"Found timestamp field '{field}': {timestamp} (type: {type(timestamp)})")
                break
        
        if timestamp is not None:
            try:
                if isinstance(timestamp, str):
                    logger.debug(f"Parsing string timestamp: {timestamp}")
                    # 尝试解析字符串时间，支持chatlog的ISO格式
                    formats = [
                        '%Y-%m-%d %H:%M:%S',
                        '%Y/%m/%d %H:%M:%S',
                        '%Y-%m-%dT%H:%M:%S',
                        '%Y-%m-%dT%H:%M:%SZ',
                        '%Y-%m-%dT%H:%M:%S.%f',
                        '%Y-%m-%dT%H:%M:%S.%fZ'
                    ]
                    for fmt in formats:
                        try:
                            result = datetime.strptime(timestamp, fmt)
                            logger.debug(f"Successfully parsed with format {fmt}: {result}")
                            return result
                        except ValueError:
                            continue
                    
                    # 处理chatlog的复杂ISO格式（如2025-07-28T09:21:50+08:00）
                    try:
                        # 移除时区信息后解析
                        clean_timestamp = re.sub(r'[+\-]\d{2}:\d{2}$', '', timestamp)
                        clean_timestamp = clean_timestamp.replace('Z', '')
                        for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f']:
                            try:
                                result = datetime.strptime(clean_timestamp, fmt)
                                logger.debug(f"Successfully parsed cleaned timestamp with format {fmt}: {result}")
                                return result
                            except ValueError:
                                continue
                    except:
                        pass
                elif isinstance(timestamp, (int, float)):
                    logger.debug(f"Parsing numeric timestamp: {timestamp}")
                    # Unix时间戳 - 前端parseTimestamp返回的是毫秒时间戳
                    if timestamp > 1e12:  # 毫秒时间戳（调整阈值）
                        timestamp = timestamp / 1000
                    elif timestamp > 1e10:  # 也可能是毫秒
                        timestamp = timestamp / 1000
                    result = datetime.fromtimestamp(timestamp)
                    logger.debug(f"Successfully parsed numeric timestamp: {result}")
                    return result
                elif isinstance(timestamp, datetime):
                    logger.debug(f"Using datetime object directly: {timestamp}")
                    return timestamp
            except Exception as e:
                logger.warning(f"Failed to parse timestamp {timestamp}: {str(e)}")
        
        default_time = datetime.now()
        logger.debug(f"Using default timestamp: {default_time}")
        return default_time
    
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
        question_words = ['什么', '如何', '怎么', '为什么', '哪里', '哪个', '能否', '可以', '请问', '有没有', '您有', '老师']
        for word in question_words:
            if word in content:
                question_score += 0.5
                break
        
        # 教育咨询特殊词汇加分
        educational_words = ['FAFSA', 'CSS', '学费', '助学金', '申请', '学校', '孩子', '办法', '建议']
        for word in educational_words:
            if word in content:
                question_score += 0.3
                break
        
        # 长文本中的问题模式（如：...您有好的办法吗？）
        if re.search(r'.*[您你].*(有|什么|怎么).*(好的)?.*[办法方法建议].*[吗？?]?', content):
            question_score += 0.8
        
        # 求助模式
        if re.search(r'.*(老师|请教|咨询|求助|帮忙).*', content):
            question_score += 0.4
            
        return question_score >= 0.3  # 保持较低阈值
    
    def _find_answers(self, messages: List[Dict[str, Any]], question_index: int, question_msg: Dict[str, Any]) -> List[Tuple[Dict[str, Any], float]]:
        """寻找问题的答案"""
        answers = []
        question_time = question_msg['timestamp']
        
        # 在问题后的15条消息中寻找答案（教育咨询场景答案可能较远）
        search_range = min(len(messages), question_index + 16)
        
        for i in range(question_index + 1, search_range):
            candidate_msg = messages[i]
            
            # 跳过同一人的后续消息（可能是补充问题）
            if candidate_msg['sender'] == question_msg['sender']:
                continue
            
            # 时间间隔不能太长（教育咨询允许30分钟内）
            time_diff = (candidate_msg['timestamp'] - question_time).total_seconds()
            if time_diff > 1800:  # 30分钟，因为专业回答需要更多时间准备
                break
            
            # 计算答案置信度
            confidence = self._calculate_answer_confidence(
                question_msg['content'], 
                candidate_msg['content']
            )
            
            if confidence > 0.1:  # 最低答案阈值，更宽松
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