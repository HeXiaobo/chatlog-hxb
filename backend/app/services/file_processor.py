"""
文件处理服务 - 优化内存使用和大文件处理
"""
import os
import json
import logging
import hashlib
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from app import db
from app.models import QAPair, Category, UploadHistory
from .data_extractor import DataExtractor, QACandidate
from .qa_classifier import QAClassifier
from app.utils.memory_monitor import get_memory_monitor, memory_profile
from app.utils.streaming_processor import StreamingJSONProcessor, memory_limited_operation

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """处理结果"""
    success: bool
    upload_id: int
    total_extracted: int
    total_saved: int
    processing_time: float
    error_message: Optional[str] = None
    statistics: Optional[Dict[str, Any]] = None


class FileProcessor:
    """文件处理器"""
    
    def __init__(self):
        self.data_extractor = DataExtractor()
        self.qa_classifier = QAClassifier()
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.allowed_extensions = {'.json'}
        self.max_concurrent_processes = 3
        self.memory_monitor = get_memory_monitor()
        self.streaming_processor = StreamingJSONProcessor()
        
        # 内存使用阈值
        self.memory_warning_threshold = 200  # 200MB
        self.large_file_threshold = 10 * 1024 * 1024  # 10MB使用流式处理
        
    def validate_file(self, file_path: Path) -> Tuple[bool, str]:
        """
        验证上传文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        try:
            # 检查文件是否存在
            if not file_path.exists():
                return False, "文件不存在"
            
            # 检查文件大小
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size:
                return False, f"文件大小超过限制({self.max_file_size // (1024*1024)}MB)"
            
            if file_size == 0:
                return False, "文件为空"
            
            # 检查文件扩展名
            if file_path.suffix.lower() not in self.allowed_extensions:
                return False, f"不支持的文件类型，仅支持: {', '.join(self.allowed_extensions)}"
            
            # 验证JSON格式
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                return False, f"JSON格式错误: {str(e)}"
            except UnicodeDecodeError:
                return False, "文件编码错误，请使用UTF-8编码"
            
            return True, ""
            
        except Exception as e:
            logger.error(f"Failed to validate file {file_path}: {str(e)}")
            return False, f"文件验证失败: {str(e)}"
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希值"""
        hasher = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate hash for {file_path}: {str(e)}")
            return ""
    
    def check_duplicate_upload(self, file_hash: str) -> Optional[UploadHistory]:
        """检查重复上传"""
        try:
            return UploadHistory.query.filter_by(
                file_hash=file_hash,
                status='completed'
            ).first()
        except Exception as e:
            logger.error(f"Failed to check duplicate upload: {str(e)}")
            return None
    
    def create_upload_record(self, filename: str, file_size: int, file_hash: str) -> UploadHistory:
        """创建上传记录"""
        try:
            upload_record = UploadHistory(
                filename=filename,
                file_size=file_size,
                file_hash=file_hash,
                status='processing',
                uploaded_at=datetime.utcnow()
            )
            
            db.session.add(upload_record)
            db.session.commit()
            
            logger.info(f"Created upload record {upload_record.id} for {filename}")
            return upload_record
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create upload record: {str(e)}")
            raise
    
    @memory_profile("file_processing")
    def process_file(self, file_path: Path, upload_record: UploadHistory) -> ProcessingResult:
        """
        处理单个文件
        
        Args:
            file_path: 文件路径
            upload_record: 上传记录
        
        Returns:
            ProcessingResult: 处理结果
        """
        start_time = datetime.utcnow()
        
        try:
            # 更新状态为处理中
            upload_record.status = 'processing'
            upload_record.started_at = start_time
            db.session.commit()
            
            # 检查文件大小决定处理方式
            file_size = file_path.stat().st_size
            use_streaming = file_size > self.large_file_threshold
            
            logger.info(f"Processing file {file_path.name} ({file_size / 1024 / 1024:.1f}MB) "
                       f"using {'streaming' if use_streaming else 'standard'} method")
            
            if use_streaming:
                return self._process_file_streaming(file_path, upload_record, start_time)
            else:
                return self._process_file_standard(file_path, upload_record, start_time)
                
        except Exception as e:
            error_message = str(e)
            logger.error(f"Failed to process upload {upload_record.id}: {error_message}")
            
            # 更新上传记录为失败状态
            upload_record.status = 'failed'
            upload_record.error_message = error_message
            upload_record.completed_at = datetime.utcnow()
            db.session.commit()
            
            return ProcessingResult(
                success=False,
                upload_id=upload_record.id,
                total_extracted=0,
                total_saved=0,
                processing_time=(datetime.utcnow() - start_time).total_seconds(),
                error_message=error_message
            )
    
    def _process_file_standard(self, file_path: Path, upload_record: UploadHistory, start_time: datetime) -> ProcessingResult:
        """标准方式处理文件（小文件）"""
        with memory_limited_operation(self.memory_warning_threshold):
            # 读取JSON数据
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = f.read()
            
            # 提取问答对
            logger.info(f"Starting extraction for upload {upload_record.id}")
            print(f"[DEBUG] Starting extraction for upload {upload_record.id}")
            print(f"[DEBUG] JSON data length: {len(json_data)} characters")
            print(f"[DEBUG] JSON data preview: {json_data[:500]}...")
            
            # 先解析消息获取所有聊天记录
            try:
                data = json.loads(json_data)
                messages = self.data_extractor._parse_messages(data)
                logger.info(f"Parsed {len(messages)} messages from file")
            except Exception as e:
                logger.error(f"Failed to parse messages: {str(e)}")
                messages = []
            
            qa_candidates = self.data_extractor.extract_from_json(json_data, str(file_path))
            
            print(f"[DEBUG] Extraction completed, found {len(qa_candidates)} candidates")
            
            # 先保存所有消息到数据库，然后再进行分析
            all_messages = messages
            logger.info(f"Found {len(all_messages)} valid messages, proceeding with storage and analysis")
            
            # 创建基础记录存储所有消息
            raw_qa_pairs = self._create_raw_qa_pairs_from_messages(all_messages, upload_record.id)
            
            if not qa_candidates:
                print(f"[DEBUG] No high-confidence QA candidates found, but saved {len(raw_qa_pairs)} raw messages")
                logger.warning(f"No high-confidence QA pairs extracted, but saved {len(raw_qa_pairs)} raw messages for manual review")
            
            logger.info(f"Extracted {len(qa_candidates)} QA candidates")
            
            # 分类问答对（如果有的话）
            classified_results = []
            if qa_candidates:
                for qa in qa_candidates:
                    try:
                        classification = self.qa_classifier.classify_qa(
                            qa.question, qa.answer, qa.context
                        )
                        classified_results.append((qa, classification))
                    except Exception as e:
                        logger.error(f"Failed to classify QA: {str(e)}")
                        # 使用默认分类
                        from .qa_classifier import CategoryMatch
                        classification = CategoryMatch(1, '产品咨询', 0.2, [])
                        classified_results.append((qa, classification))
            
            # 保存到数据库 - 优先保存高质量问答对，其次保存原始消息
            saved_count = 0
            if classified_results:
                saved_count = self._save_qa_pairs(classified_results, upload_record.id)
                logger.info(f"Saved {saved_count} high-quality QA pairs")
            
            # 如果没有高质量问答对但有原始消息，则保存原始消息用于人工审核
            if not classified_results and raw_qa_pairs:
                saved_count = len(raw_qa_pairs)
                logger.info(f"Saved {saved_count} raw messages for manual review")
            
            # 计算处理时间
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # 更新上传记录
            upload_record.status = 'completed'
            upload_record.completed_at = datetime.utcnow()
            upload_record.qa_count = saved_count
            upload_record.processing_time = processing_time
            db.session.commit()
            
            # 生成统计信息
            extraction_stats = self.data_extractor.get_extraction_stats(qa_candidates)
            classification_stats = self.qa_classifier.get_classification_stats(
                [result[1] for result in classified_results]
            ) if classified_results else {}
            
            # 补充原始消息统计
            processing_summary = {
                'total_messages_parsed': len(messages),
                'high_quality_qa_pairs': len(qa_candidates),
                'raw_messages_saved': len(raw_qa_pairs) if raw_qa_pairs else 0,
                'processing_strategy': 'high_quality' if classified_results else 'raw_import'
            }
            
            statistics = {
                'extraction': extraction_stats,
                'classification': classification_stats,
                'processing': processing_summary,
                'file_info': {
                    'filename': upload_record.filename,
                    'file_size': upload_record.file_size,
                    'processing_time': processing_time
                }
            }
            
            success_message = f"Successfully processed upload {upload_record.id}: "
            if classified_results:
                success_message += f"{len(qa_candidates)} high-quality QA pairs extracted and saved"
            else:
                success_message += f"{len(messages)} messages parsed, {saved_count} raw records saved for manual review"
            
            logger.info(success_message)
            
            return ProcessingResult(
                success=True,
                upload_id=upload_record.id,
                total_extracted=len(qa_candidates),
                total_saved=saved_count,
                processing_time=processing_time,
                statistics=statistics
            )
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Failed to process upload {upload_record.id}: {error_message}")
            
            # 更新上传记录为失败状态
            upload_record.status = 'failed'
            upload_record.error_message = error_message
            upload_record.completed_at = datetime.utcnow()
            db.session.commit()
            
            return ProcessingResult(
                success=False,
                upload_id=upload_record.id,
                total_extracted=0,
                total_saved=0,
                processing_time=(datetime.utcnow() - start_time).total_seconds(),
                error_message=error_message
            )
    
    def _save_qa_pairs(self, classified_results: List, upload_id: int) -> int:
        """保存问答对到数据库"""
        saved_count = 0
        batch_size = 1000  # 进一步增大批量大小以提高性能
        
        try:
            # 优化：预加载所有分类到内存中，避免重复查询
            categories_dict = {cat.id: cat for cat in Category.query.all()}
            
            # 内容去重：预加载现有问答对的内容指纹
            existing_fingerprints = self._get_existing_content_fingerprints()
            
            for i in range(0, len(classified_results), batch_size):
                batch = classified_results[i:i + batch_size]
                batch_objects = []
                
                for qa_candidate, classification in batch:
                    try:
                        # 使用预加载的分类字典
                        category_id = classification.category_id if classification.category_id in categories_dict else 1
                        
                        # 创建内容指纹进行去重检查
                        content_fingerprint = self._generate_content_fingerprint(
                            qa_candidate.question, 
                            qa_candidate.answer,
                            qa_candidate.asker,
                            qa_candidate.advisor
                        )
                        
                        # 检查是否重复
                        if content_fingerprint in existing_fingerprints:
                            logger.debug(f"Skipping duplicate QA pair: {qa_candidate.question[:50]}...")
                            continue
                        
                        # 安全的上下文JSON序列化
                        safe_context = None
                        if qa_candidate.context:
                            try:
                                # 将上下文转换为可序列化格式
                                context_data = []
                                for item in qa_candidate.context[:10]:
                                    if isinstance(item, str):
                                        context_data.append(item)
                                    elif hasattr(item, '__dict__'):
                                        # 转换对象为字典，处理datetime等特殊类型
                                        item_dict = {}
                                        for key, value in item.__dict__.items():
                                            if isinstance(value, datetime):
                                                item_dict[key] = value.isoformat()
                                            else:
                                                item_dict[key] = str(value)
                                        context_data.append(item_dict)
                                    else:
                                        context_data.append(str(item))
                                safe_context = json.dumps(context_data, ensure_ascii=False)
                            except Exception as e:
                                logger.warning(f"Failed to serialize context: {str(e)}")
                                safe_context = json.dumps({"error": "Context serialization failed"}, ensure_ascii=False)
                        
                        # 创建问答对对象但不立即添加到session
                        qa_pair = QAPair(
                            question=qa_candidate.question[:2000],  # 限制长度
                            answer=qa_candidate.answer[:2000],
                            category_id=category_id,
                            asker=qa_candidate.asker[:100] if qa_candidate.asker else None,
                            advisor=qa_candidate.advisor[:100] if qa_candidate.advisor else None,
                            confidence=qa_candidate.confidence,
                            source_file=f"upload_{upload_id}",
                            original_context=safe_context
                        )
                        
                        batch_objects.append(qa_pair)
                        existing_fingerprints.add(content_fingerprint)  # 添加到已存在指纹集合
                        
                    except Exception as e:
                        logger.error(f"Failed to create QA pair: {str(e)}")
                        continue
                
                # 批量添加到session
                if batch_objects:
                    db.session.bulk_save_objects(batch_objects)
                    db.session.commit()
                    
                    # 计数实际保存的对象数量
                    saved_count += len(batch_objects)
                    
                    # 更新FTS索引（如果启用）
                    try:
                        from .search_service import SearchService
                        search_service = SearchService()
                        if search_service.fts_enabled:
                            # 批量插入到FTS索引
                            for qa_pair in batch_objects:
                                # 获取实际保存的ID
                                db.session.refresh(qa_pair)
                                search_service.update_fts_record(qa_pair, 'insert')
                    except Exception as fts_error:
                        logger.warning(f"Failed to update FTS index: {fts_error}")
                    
                    logger.debug(f"Saved batch {i//batch_size + 1}, batch size: {len(batch_objects)}, total saved: {saved_count}")
            
            return saved_count
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to save QA pairs: {str(e)}")
            raise
    
    def process_file_async(self, file_path: Path, filename: str) -> Dict[str, Any]:
        """
        异步处理文件（用于API调用）
        
        Args:
            file_path: 文件路径
            filename: 文件名
        
        Returns:
            Dict: 包含upload_id和基本信息的响应
        """
        try:
            # 文件验证
            is_valid, error_msg = self.validate_file(file_path)
            if not is_valid:
                return {
                    'success': False,
                    'error': error_msg
                }
            
            # 计算文件信息
            file_size = file_path.stat().st_size
            file_hash = self.calculate_file_hash(file_path)
            
            # 检查重复上传
            duplicate = self.check_duplicate_upload(file_hash)
            if duplicate:
                return {
                    'success': True,
                    'upload_id': duplicate.id,
                    'message': '文件已存在，跳过处理',
                    'qa_count': duplicate.qa_count,
                    'status': duplicate.status
                }
            
            # 创建上传记录
            upload_record = self.create_upload_record(filename, file_size, file_hash)
            
            # 在后台处理（实际生产中应该使用Celery等任务队列）
            # 这里简化为直接处理
            result = self.process_file(file_path, upload_record)
            
            # 生成用户友好的处理结果消息
            if result.success:
                if result.statistics and result.statistics.get('processing', {}).get('processing_strategy') == 'high_quality':
                    message = f"处理完成：提取到 {result.total_extracted} 个高质量问答对"
                elif result.statistics and result.statistics.get('processing', {}).get('raw_messages_saved', 0) > 0:
                    raw_count = result.statistics['processing']['raw_messages_saved']
                    message = f"处理完成：暂未找到明显的问答对话，已保存 {raw_count} 条原始记录供人工审核。建议检查文件格式或内容是否包含问答形式的对话。"
                else:
                    message = f"处理完成：保存了 {result.total_saved} 条记录"
            else:
                message = result.error_message
            
            return {
                'success': result.success,
                'upload_id': result.upload_id,
                'message': message,
                'total_extracted': result.total_extracted,
                'total_saved': result.total_saved,
                'processing_time': result.processing_time,
                'statistics': result.statistics
            }
            
        except Exception as e:
            logger.error(f"Failed to process file async: {str(e)}")
            return {
                'success': False,
                'error': f'处理失败: {str(e)}'
            }
    
    def get_processing_status(self, upload_id: int) -> Dict[str, Any]:
        """获取处理状态"""
        try:
            upload_record = UploadHistory.query.get(upload_id)
            if not upload_record:
                return {
                    'success': False,
                    'error': '上传记录不存在'
                }
            
            return {
                'success': True,
                'upload_id': upload_id,
                'filename': upload_record.filename,
                'status': upload_record.status,
                'qa_count': upload_record.qa_count or 0,
                'processing_time': upload_record.processing_time,
                'uploaded_at': upload_record.uploaded_at.isoformat() if upload_record.uploaded_at else None,
                'completed_at': upload_record.completed_at.isoformat() if upload_record.completed_at else None,
                'error_message': upload_record.error_message
            }
            
        except Exception as e:
            logger.error(f"Failed to get processing status: {str(e)}")
            return {
                'success': False,
                'error': f'获取状态失败: {str(e)}'
            }
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """清理临时文件"""
        try:
            from flask import current_app
            upload_folder = Path(current_app.config['UPLOAD_FOLDER'])
            
            cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
            
            cleaned_count = 0
            for file_path in upload_folder.glob('*'):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                    except Exception as e:
                        logger.error(f"Failed to remove temp file {file_path}: {str(e)}")
            
            logger.info(f"Cleaned up {cleaned_count} temporary files")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup temp files: {str(e)}")
            return 0
    
    def _create_raw_qa_pairs_from_messages(self, messages: List[Dict], upload_id: int) -> List[object]:
        """从所有消息创建原始Q&A记录用于后续人工审核"""
        raw_pairs = []
        batch_size = 100
        
        try:
            logger.info(f"Creating raw QA pairs from {len(messages)} messages")
            
            # 获取现有指纹进行去重
            existing_fingerprints = self._get_existing_content_fingerprints()
            
            # 将连续的消息组合成问答对
            for i in range(0, len(messages) - 1, 2):  # 每2条消息组成一对
                try:
                    question_msg = messages[i]
                    answer_msg = messages[i + 1] if i + 1 < len(messages) else question_msg
                    
                    # 避免同一人的连续消息
                    if question_msg['sender'] == answer_msg['sender'] and i + 2 < len(messages):
                        answer_msg = messages[i + 2]
                    
                    # 检查内容去重
                    question_content = question_msg['content'][:2000]
                    answer_content = answer_msg['content'][:2000] if question_msg != answer_msg else "待补充回答"
                    asker = question_msg['sender'][:100]
                    advisor = answer_msg['sender'][:100] if question_msg != answer_msg else "系统"
                    
                    content_fingerprint = self._generate_content_fingerprint(
                        question_content, answer_content, asker, advisor
                    )
                    
                    # 跳过重复内容
                    if content_fingerprint in existing_fingerprints:
                        logger.debug(f"Skipping duplicate raw message pair: {question_content[:30]}...")
                        continue
                    
                    qa_pair = QAPair(
                        question=question_content,
                        answer=answer_content,
                        category_id=1,  # 默认分类：产品咨询
                        asker=asker,
                        advisor=advisor,
                        confidence=0.1,  # 低置信度标记为待审核
                        source_file=f"upload_{upload_id}_raw",
                        original_context=json.dumps({
                            'question_timestamp': question_msg['timestamp'].isoformat() if isinstance(question_msg['timestamp'], datetime) else str(question_msg['timestamp']),
                            'answer_timestamp': answer_msg['timestamp'].isoformat() if isinstance(answer_msg['timestamp'], datetime) else str(answer_msg['timestamp']),
                            'raw_import': True,
                            'needs_review': True
                        }, ensure_ascii=False)
                    )
                    raw_pairs.append(qa_pair)
                    existing_fingerprints.add(content_fingerprint)  # 添加到已存在集合
                    
                except Exception as e:
                    logger.error(f"Failed to create raw QA pair from messages {i}, {i+1}: {str(e)}")
                    continue
            
            # 批量保存原始记录
            if raw_pairs:
                saved_count = 0
                for i in range(0, len(raw_pairs), batch_size):
                    batch = raw_pairs[i:i + batch_size]
                    try:
                        db.session.bulk_save_objects(batch)
                        db.session.commit()
                        saved_count += len(batch)
                        logger.debug(f"Saved raw batch {i//batch_size + 1}, total: {saved_count}")
                    except Exception as e:
                        logger.error(f"Failed to save raw batch: {str(e)}")
                        db.session.rollback()
                        continue
                
                logger.info(f"Successfully saved {saved_count} raw QA pairs for manual review")
            
            return raw_pairs
            
        except Exception as e:
            logger.error(f"Failed to create raw QA pairs: {str(e)}")
            return []
    
    def _get_existing_content_fingerprints(self) -> set:
        """获取现有问答对的内容指纹"""
        try:
            existing_pairs = db.session.query(
                QAPair.question, 
                QAPair.answer, 
                QAPair.asker, 
                QAPair.advisor
            ).all()
            
            fingerprints = set()
            for question, answer, asker, advisor in existing_pairs:
                fingerprint = self._generate_content_fingerprint(question, answer, asker, advisor)
                fingerprints.add(fingerprint)
            
            logger.info(f"Loaded {len(fingerprints)} existing content fingerprints for deduplication")
            return fingerprints
            
        except Exception as e:
            logger.error(f"Failed to load existing fingerprints: {str(e)}")
            return set()
    
    def _generate_content_fingerprint(self, question: str, answer: str, asker: str, advisor: str) -> str:
        """生成内容指纹用于去重"""
        try:
            import hashlib
            import re
            
            # 标准化文本：移除多余空白、标点，转为小写
            def normalize_text(text):
                if not text:
                    return ""
                # 移除多余空白和标点
                text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
                text = re.sub(r'\s+', ' ', text)
                return text.lower().strip()
            
            # 标准化各字段
            norm_question = normalize_text(question)[:200]  # 限制长度避免过长指纹
            norm_answer = normalize_text(answer)[:200]
            norm_asker = normalize_text(asker) if asker else ""
            norm_advisor = normalize_text(advisor) if advisor else ""
            
            # 生成组合指纹
            content = f"{norm_question}|{norm_answer}|{norm_asker}|{norm_advisor}"
            
            # 使用MD5生成短指纹
            fingerprint = hashlib.md5(content.encode('utf-8')).hexdigest()
            
            return fingerprint
            
        except Exception as e:
            logger.error(f"Failed to generate content fingerprint: {str(e)}")
            # 返回基于内容长度的简单指纹作为降级方案
            return f"fallback_{len(question or '')}_{len(answer or '')}"