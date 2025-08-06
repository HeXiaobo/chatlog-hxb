"""
数据验证服务
"""
import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """验证错误"""
    field: str
    message: str
    code: str
    value: Any = None


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    
    def add_error(self, field: str, message: str, code: str, value: Any = None):
        """添加错误"""
        self.errors.append(ValidationError(field, message, code, value))
        self.is_valid = False
    
    def add_warning(self, field: str, message: str, code: str, value: Any = None):
        """添加警告"""
        self.warnings.append(ValidationError(field, message, code, value))
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'is_valid': self.is_valid,
            'errors': [
                {
                    'field': err.field,
                    'message': err.message,
                    'code': err.code,
                    'value': err.value
                }
                for err in self.errors
            ],
            'warnings': [
                {
                    'field': warn.field,
                    'message': warn.message,
                    'code': warn.code,
                    'value': warn.value
                }
                for warn in self.warnings
            ]
        }


class DataValidator:
    """数据验证器"""
    
    def __init__(self):
        self.max_text_length = 2000
        self.min_text_length = 2
        self.max_name_length = 100
        self.confidence_range = (0.0, 1.0)
        
    def validate_qa_pair(self, question: str, answer: str, asker: str = None, 
                        advisor: str = None, confidence: float = None) -> ValidationResult:
        """
        验证问答对数据
        
        Args:
            question: 问题内容
            answer: 答案内容
            asker: 提问者
            advisor: 回答者
            confidence: 置信度
        
        Returns:
            ValidationResult: 验证结果
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # 验证问题
        if not question or not isinstance(question, str):
            result.add_error('question', '问题不能为空', 'QUESTION_REQUIRED', question)
        else:
            question = question.strip()
            if len(question) < self.min_text_length:
                result.add_error('question', f'问题长度不能少于{self.min_text_length}个字符', 
                               'QUESTION_TOO_SHORT', question)
            elif len(question) > self.max_text_length:
                result.add_warning('question', f'问题长度超过{self.max_text_length}个字符，将被截断', 
                                 'QUESTION_TOO_LONG', question)
            
            # 检查问题质量
            if not self._is_valid_question(question):
                result.add_warning('question', '问题格式可能不规范', 'QUESTION_FORMAT_WARNING', question)
        
        # 验证答案
        if not answer or not isinstance(answer, str):
            result.add_error('answer', '答案不能为空', 'ANSWER_REQUIRED', answer)
        else:
            answer = answer.strip()
            if len(answer) < self.min_text_length:
                result.add_error('answer', f'答案长度不能少于{self.min_text_length}个字符', 
                               'ANSWER_TOO_SHORT', answer)
            elif len(answer) > self.max_text_length:
                result.add_warning('answer', f'答案长度超过{self.max_text_length}个字符，将被截断', 
                                 'ANSWER_TOO_LONG', answer)
        
        # 验证提问者和回答者
        if asker is not None:
            if not isinstance(asker, str):
                result.add_error('asker', '提问者必须为字符串类型', 'ASKER_TYPE_ERROR', asker)
            elif len(asker.strip()) > self.max_name_length:
                result.add_warning('asker', f'提问者名称长度超过{self.max_name_length}个字符，将被截断', 
                                 'ASKER_TOO_LONG', asker)
        
        if advisor is not None:
            if not isinstance(advisor, str):
                result.add_error('advisor', '回答者必须为字符串类型', 'ADVISOR_TYPE_ERROR', advisor)
            elif len(advisor.strip()) > self.max_name_length:
                result.add_warning('advisor', f'回答者名称长度超过{self.max_name_length}个字符，将被截断', 
                                 'ADVISOR_TOO_LONG', advisor)
        
        # 验证置信度
        if confidence is not None:
            if not isinstance(confidence, (int, float)):
                result.add_error('confidence', '置信度必须为数字类型', 'CONFIDENCE_TYPE_ERROR', confidence)
            elif not (self.confidence_range[0] <= confidence <= self.confidence_range[1]):
                result.add_error('confidence', 
                               f'置信度必须在{self.confidence_range[0]}到{self.confidence_range[1]}之间', 
                               'CONFIDENCE_RANGE_ERROR', confidence)
            elif confidence < 0.3:
                result.add_warning('confidence', '置信度过低，建议人工审核', 'CONFIDENCE_LOW_WARNING', confidence)
        
        return result
    
    def validate_file_data(self, file_path: str, data: Dict[str, Any]) -> ValidationResult:
        """
        验证上传文件数据
        
        Args:
            file_path: 文件路径
            data: JSON数据
        
        Returns:
            ValidationResult: 验证结果
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # 验证JSON结构
        if not isinstance(data, dict):
            result.add_error('data', '数据必须为JSON对象格式', 'DATA_FORMAT_ERROR', type(data).__name__)
            return result
        
        # 检查必要字段
        messages = data.get('messages', [])
        if not messages:
            # 尝试其他可能的字段
            if 'data' in data and isinstance(data['data'], list):
                messages = data['data']
            elif isinstance(data, list):
                messages = data
            else:
                result.add_error('messages', '未找到消息数据', 'MESSAGES_NOT_FOUND', None)
                return result
        
        if not isinstance(messages, list):
            result.add_error('messages', '消息数据必须为数组格式', 'MESSAGES_FORMAT_ERROR', type(messages).__name__)
            return result
        
        if len(messages) == 0:
            result.add_error('messages', '消息数据为空', 'MESSAGES_EMPTY', len(messages))
            return result
        
        # 验证消息结构
        valid_messages = 0
        for i, msg in enumerate(messages[:100]):  # 只检查前100条消息
            if not isinstance(msg, dict):
                result.add_warning('messages', f'第{i+1}条消息格式不正确', 'MESSAGE_FORMAT_WARNING', msg)
                continue
            
            # 检查内容字段
            content = self._extract_message_content(msg)
            if content:
                valid_messages += 1
            else:
                result.add_warning('messages', f'第{i+1}条消息缺少内容', 'MESSAGE_CONTENT_MISSING', msg)
        
        if valid_messages == 0:
            result.add_error('messages', '没有找到有效的消息内容', 'NO_VALID_MESSAGES', valid_messages)
        elif valid_messages < len(messages) * 0.5:  # 少于50%的消息有效
            result.add_warning('messages', f'有效消息比例较低 ({valid_messages}/{len(messages)})', 
                             'LOW_VALID_MESSAGE_RATIO', valid_messages)
        
        # 文件大小警告
        try:
            import os
            file_size = os.path.getsize(file_path)
            if file_size > 10 * 1024 * 1024:  # 大于10MB
                result.add_warning('file_size', '文件较大，处理可能需要较长时间', 'FILE_SIZE_WARNING', file_size)
        except:
            pass
        
        return result
    
    def validate_category_data(self, name: str, description: str = None, color: str = None) -> ValidationResult:
        """
        验证分类数据
        
        Args:
            name: 分类名称
            description: 分类描述
            color: 分类颜色
        
        Returns:
            ValidationResult: 验证结果
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # 验证分类名称
        if not name or not isinstance(name, str):
            result.add_error('name', '分类名称不能为空', 'NAME_REQUIRED', name)
        else:
            name = name.strip()
            if len(name) < 2:
                result.add_error('name', '分类名称长度不能少于2个字符', 'NAME_TOO_SHORT', name)
            elif len(name) > 50:
                result.add_error('name', '分类名称长度不能超过50个字符', 'NAME_TOO_LONG', name)
            elif not re.match(r'^[\u4e00-\u9fff\w\s]+$', name):
                result.add_warning('name', '分类名称包含特殊字符', 'NAME_SPECIAL_CHARS', name)
        
        # 验证描述
        if description is not None:
            if not isinstance(description, str):
                result.add_error('description', '分类描述必须为字符串类型', 'DESCRIPTION_TYPE_ERROR', description)
            elif len(description) > 200:
                result.add_warning('description', '分类描述长度超过200个字符', 'DESCRIPTION_TOO_LONG', description)
        
        # 验证颜色
        if color is not None:
            if not isinstance(color, str):
                result.add_error('color', '颜色值必须为字符串类型', 'COLOR_TYPE_ERROR', color)
            elif not re.match(r'^#[0-9a-fA-F]{6}$', color):
                result.add_error('color', '颜色值格式不正确，应为#RRGGBB格式', 'COLOR_FORMAT_ERROR', color)
        
        return result
    
    def sanitize_text(self, text: str, max_length: int = None) -> str:
        """
        清理文本内容
        
        Args:
            text: 原始文本
            max_length: 最大长度
        
        Returns:
            str: 清理后的文本
        """
        if not text or not isinstance(text, str):
            return ""
        
        # 去除首尾空格
        text = text.strip()
        
        # 清理控制字符
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        # 清理多余空格
        text = re.sub(r'\s+', ' ', text)
        
        # 限制长度
        if max_length and len(text) > max_length:
            text = text[:max_length].rstrip()
        
        return text
    
    def _is_valid_question(self, question: str) -> bool:
        """判断是否为有效问题"""
        # 检查问题标志
        question_indicators = ['?', '？', '吗', '呢', '如何', '怎么', '怎样', '什么', '哪里', '哪个', '为什么', '能否', '可以', '请问']
        
        return any(indicator in question for indicator in question_indicators)
    
    def _extract_message_content(self, msg: Dict[str, Any]) -> Optional[str]:
        """提取消息内容"""
        content_fields = ['content', 'text', 'message', 'body']
        
        for field in content_fields:
            if field in msg and msg[field]:
                content = str(msg[field]).strip()
                if content:
                    return content
        
        return None


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def handle_processing_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        处理处理过程中的错误
        
        Args:
            error: 异常对象
            context: 上下文信息
        
        Returns:
            Dict: 错误响应
        """
        error_type = type(error).__name__
        error_message = str(error)
        
        # 记录详细错误日志
        self.logger.error(f"Processing error: {error_type} - {error_message}", 
                         extra={'context': context}, exc_info=True)
        
        # 根据错误类型生成用户友好的错误信息
        user_message, error_code = self._get_user_friendly_error(error_type, error_message)
        
        return {
            'success': False,
            'error': {
                'code': error_code,
                'message': user_message,
                'details': error_message if context and context.get('debug') else None,
                'context': context.get('operation') if context else None
            }
        }
    
    def _get_user_friendly_error(self, error_type: str, error_message: str) -> Tuple[str, str]:
        """获取用户友好的错误信息"""
        
        error_mappings = {
            'JSONDecodeError': ('JSON文件格式错误', 'INVALID_JSON'),
            'UnicodeDecodeError': ('文件编码错误，请使用UTF-8编码', 'ENCODING_ERROR'),
            'FileNotFoundError': ('文件不存在', 'FILE_NOT_FOUND'),
            'PermissionError': ('文件访问权限不足', 'PERMISSION_DENIED'),
            'MemoryError': ('内存不足，请减少文件大小', 'MEMORY_ERROR'),
            'TimeoutError': ('处理超时，请稍后重试', 'TIMEOUT_ERROR'),
            'ConnectionError': ('数据库连接失败', 'DATABASE_CONNECTION_ERROR'),
            'IntegrityError': ('数据完整性错误', 'DATA_INTEGRITY_ERROR'),
            'ValidationError': ('数据验证失败', 'VALIDATION_ERROR'),
        }
        
        # 检查特定错误消息
        if 'disk space' in error_message.lower():
            return '磁盘空间不足', 'DISK_FULL'
        elif 'too large' in error_message.lower():
            return '文件过大', 'FILE_TOO_LARGE'
        elif 'database' in error_message.lower():
            return '数据库操作失败', 'DATABASE_ERROR'
        
        # 使用映射表
        user_message, error_code = error_mappings.get(error_type, ('系统内部错误', 'INTERNAL_ERROR'))
        
        return user_message, error_code
    
    def create_validation_response(self, validation_result: ValidationResult) -> Dict[str, Any]:
        """创建验证响应"""
        if validation_result.is_valid:
            return {
                'success': True,
                'data': {
                    'is_valid': True,
                    'warnings': validation_result.to_dict()['warnings']
                },
                'message': '数据验证通过' + (f'，有{len(validation_result.warnings)}个警告' 
                                  if validation_result.warnings else '')
            }
        else:
            return {
                'success': False,
                'error': {
                    'code': 'VALIDATION_FAILED',
                    'message': '数据验证失败',
                    'validation_errors': validation_result.to_dict()['errors'],
                    'warnings': validation_result.to_dict()['warnings']
                }
            }