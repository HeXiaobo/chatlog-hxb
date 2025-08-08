"""
优化的文件处理服务 - 专注内存使用和大文件处理
"""
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import gc

from app import db
from app.models import QAPair, Category, UploadHistory
from app.services.data_extractor import DataExtractor
from app.services.qa_classifier import QAClassifier
from app.services.file_processor import ProcessingResult
from app.utils.memory_monitor import get_memory_monitor, memory_profile
from app.utils.streaming_processor import StreamingJSONProcessor, memory_limited_operation

logger = logging.getLogger(__name__)


class OptimizedFileProcessor:
    """优化的文件处理器 - 内存友好的大文件处理"""
    
    def __init__(self):
        self.data_extractor = DataExtractor()
        self.qa_classifier = QAClassifier()
        self.memory_monitor = get_memory_monitor()
        self.streaming_processor = StreamingJSONProcessor()
        
        # 内存和性能配置
        self.memory_warning_threshold = 150  # 150MB
        self.large_file_threshold = 5 * 1024 * 1024  # 5MB使用流式处理
        self.batch_size = 500  # 数据库批量操作大小
        self.gc_frequency = 100  # 每处理100个对象执行GC
        
        # 统计信息
        self.processing_stats = {
            'files_processed': 0,
            'total_memory_saved_mb': 0.0,
            'streaming_mode_used': 0,
            'standard_mode_used': 0
        }
    
    @memory_profile("optimized_file_processing")
    def process_file_optimized(self, file_path: Path, upload_record: UploadHistory) -> ProcessingResult:
        """
        优化的文件处理主方法
        
        Args:
            file_path: 文件路径
            upload_record: 上传记录
            
        Returns:
            ProcessingResult: 处理结果
        """
        start_time = datetime.utcnow()
        initial_memory = self.memory_monitor.get_current_snapshot().rss_mb
        
        try:
            # 更新状态
            upload_record.status = 'processing'
            upload_record.started_at = start_time
            db.session.commit()
            
            # 检查文件大小决定处理策略
            file_size = file_path.stat().st_size
            use_streaming = file_size > self.large_file_threshold
            
            logger.info(f"Processing {file_path.name} ({file_size / 1024 / 1024:.1f}MB) "
                       f"using {'streaming' if use_streaming else 'standard'} method")
            
            if use_streaming:
                result = self._process_streaming(file_path, upload_record, start_time)
                self.processing_stats['streaming_mode_used'] += 1
            else:
                result = self._process_standard_optimized(file_path, upload_record, start_time)
                self.processing_stats['standard_mode_used'] += 1
            
            # 计算内存节省
            final_memory = self.memory_monitor.get_current_snapshot().rss_mb
            memory_saved = max(0, initial_memory - final_memory)
            self.processing_stats['total_memory_saved_mb'] += memory_saved
            self.processing_stats['files_processed'] += 1
            
            logger.info(f"File processing completed. Memory usage: {initial_memory:.1f}MB → {final_memory:.1f}MB "
                       f"(saved {memory_saved:.1f}MB)")
            
            return result
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Optimized file processing failed for upload {upload_record.id}: {error_message}")
            
            # 更新失败状态
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
    
    def _process_standard_optimized(self, file_path: Path, upload_record: UploadHistory, 
                                  start_time: datetime) -> ProcessingResult:
        """优化的标准处理方式（小文件）"""
        
        with memory_limited_operation(self.memory_warning_threshold):
            try:
                # 分块读取和处理JSON数据
                logger.info(f"Reading file {file_path} in memory-optimized mode")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                # 解析消息
                messages = self.data_extractor._parse_messages(json_data)
                logger.info(f"Parsed {len(messages)} messages")
                
                # 分批处理消息以节省内存
                all_qa_candidates = []
                processed_messages = 0
                
                for i in range(0, len(messages), self.batch_size):
                    batch_messages = messages[i:i + self.batch_size]
                    
                    # 提取QA对
                    batch_candidates = self.data_extractor._extract_qa_pairs(
                        batch_messages, str(file_path)
                    )
                    
                    if batch_candidates:
                        all_qa_candidates.extend(batch_candidates)
                    
                    processed_messages += len(batch_messages)
                    
                    # 定期垃圾回收和内存检查
                    if processed_messages % self.gc_frequency == 0:
                        current_memory = self.memory_monitor.get_current_snapshot().rss_mb
                        if current_memory > self.memory_warning_threshold:
                            logger.warning(f"Memory usage high: {current_memory:.1f}MB, running GC")
                            gc.collect()
                
                logger.info(f"Extracted {len(all_qa_candidates)} QA candidates")
                
                # 分批分类和保存
                return self._classify_and_save_batched(all_qa_candidates, upload_record, start_time, messages)
                
            except Exception as e:
                logger.error(f"Standard optimized processing failed: {str(e)}")
                raise
    
    def _process_streaming(self, file_path: Path, upload_record: UploadHistory, 
                          start_time: datetime) -> ProcessingResult:
        """流式处理方式（大文件）"""
        
        logger.info(f"Starting streaming processing for {file_path}")
        
        try:
            all_qa_candidates = []
            total_messages = 0
            
            # 检查是否需要拆分文件
            file_size = file_path.stat().st_size
            if file_size > 20 * 1024 * 1024:  # 20MB以上拆分处理
                split_files = self.streaming_processor.split_large_file(file_path, max_size_mb=10)
                process_files = split_files
                logger.info(f"Split large file into {len(split_files)} parts")
            else:
                process_files = [file_path]
            
            # 处理每个文件
            for file_to_process in process_files:
                try:
                    # 流式解析JSON
                    json_objects = self.streaming_processor.stream_parse_large_json(file_to_process)
                    
                    # 批量处理消息
                    def process_batch(batch_objects):
                        batch_messages = []
                        for obj in batch_objects:
                            if isinstance(obj, dict):
                                if 'messages' in obj:
                                    batch_messages.extend(obj['messages'])
                                elif isinstance(obj, list):
                                    batch_messages.extend(obj)
                                else:
                                    batch_messages.append(obj)
                        
                        return self.data_extractor._extract_qa_pairs(
                            batch_messages, str(file_to_process)
                        )
                    
                    # 流式批量处理
                    batch_results = self.streaming_processor.process_in_batches(
                        json_objects, batch_size=50, processor=process_batch
                    )
                    
                    for batch_candidates in batch_results:
                        if batch_candidates:
                            all_qa_candidates.extend(batch_candidates)
                            total_messages += len(batch_candidates)
                        
                        # 内存监控
                        current_memory = self.memory_monitor.get_current_snapshot().rss_mb
                        if current_memory > self.memory_warning_threshold:
                            logger.warning(f"High memory during streaming: {current_memory:.1f}MB")
                            gc.collect()
                
                except Exception as e:
                    logger.error(f"Error processing file part {file_to_process}: {str(e)}")
                    continue
            
            logger.info(f"Streaming processing completed: {len(all_qa_candidates)} QA candidates from {total_messages} messages")
            
            # 分类和保存
            return self._classify_and_save_batched(all_qa_candidates, upload_record, start_time, [])
            
        except Exception as e:
            logger.error(f"Streaming processing failed: {str(e)}")
            raise
        
        finally:
            # 清理临时文件
            self.streaming_processor.cleanup_temp_files()
    
    def _classify_and_save_batched(self, qa_candidates: List, upload_record: UploadHistory,
                                  start_time: datetime, original_messages: List = None) -> ProcessingResult:
        """批量分类和保存QA对"""
        
        logger.info(f"Starting classification and saving of {len(qa_candidates)} candidates")
        
        try:
            classified_results = []
            saved_count = 0
            
            # 预加载分类信息
            categories_dict = {cat.id: cat for cat in Category.query.all()}
            existing_fingerprints = self._get_existing_content_fingerprints()
            
            # 分批处理
            for i in range(0, len(qa_candidates), self.batch_size):
                batch = qa_candidates[i:i + self.batch_size]
                
                # 分类批次
                batch_classified = []
                for qa in batch:
                    try:
                        classification = self.qa_classifier.classify_qa(
                            qa.question, qa.answer, qa.context
                        )
                        batch_classified.append((qa, classification))
                    except Exception as e:
                        logger.warning(f"Classification failed for QA: {str(e)}")
                        continue
                
                # 保存批次
                if batch_classified:
                    batch_saved = self._save_qa_pairs_optimized(
                        batch_classified, categories_dict, existing_fingerprints, upload_record.id
                    )
                    saved_count += batch_saved
                    classified_results.extend(batch_classified)
                
                # 内存管理
                if i % (self.gc_frequency * 10) == 0:
                    current_memory = self.memory_monitor.get_current_snapshot().rss_mb
                    if current_memory > self.memory_warning_threshold:
                        logger.warning(f"Memory usage during save: {current_memory:.1f}MB")
                        gc.collect()
                
                logger.debug(f"Processed batch {i // self.batch_size + 1}, saved {batch_saved} items")
            
            # 处理原始消息（如果没有QA候选）
            if not classified_results and original_messages:
                raw_pairs = self._create_raw_qa_pairs_optimized(original_messages, upload_record.id)
                saved_count = len(raw_pairs)
                logger.info(f"Saved {saved_count} raw messages for manual review")
            
            # 更新上传记录
            processing_time = (datetime.utcnow() - start_time).total_seconds()
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
            
            statistics = {
                'extraction': extraction_stats,
                'classification': classification_stats,
                'processing': {
                    'total_candidates': len(qa_candidates),
                    'successfully_saved': saved_count,
                    'processing_method': 'optimized',
                    'memory_efficient': True,
                    'batch_size': self.batch_size
                }
            }
            
            logger.info(f"Processing completed successfully: {saved_count} items saved in {processing_time:.2f}s")
            
            return ProcessingResult(
                success=True,
                upload_id=upload_record.id,
                total_extracted=len(qa_candidates),
                total_saved=saved_count,
                processing_time=processing_time,
                statistics=statistics
            )
            
        except Exception as e:
            logger.error(f"Classification and saving failed: {str(e)}")
            raise
    
    def _save_qa_pairs_optimized(self, classified_results: List, categories_dict: Dict,
                               existing_fingerprints: set, upload_id: int) -> int:
        """优化的QA对保存"""
        
        saved_count = 0
        batch_objects = []
        
        try:
            for qa_candidate, classification in classified_results:
                try:
                    # 内容去重检查
                    content_fingerprint = self._generate_content_fingerprint(
                        qa_candidate.question, qa_candidate.answer,
                        qa_candidate.asker, qa_candidate.advisor
                    )
                    
                    if content_fingerprint in existing_fingerprints:
                        continue
                    
                    # 创建QA对象
                    category_id = classification.category_id if classification.category_id in categories_dict else 1
                    
                    qa_pair = QAPair(
                        question=qa_candidate.question[:2000],
                        answer=qa_candidate.answer[:2000],
                        category_id=category_id,
                        asker=qa_candidate.asker[:100] if qa_candidate.asker else None,
                        advisor=qa_candidate.advisor[:100] if qa_candidate.advisor else None,
                        confidence=qa_candidate.confidence,
                        source_file=f"upload_{upload_id}",
                        original_context=self._safe_serialize_context(qa_candidate.context)
                    )
                    
                    batch_objects.append(qa_pair)
                    existing_fingerprints.add(content_fingerprint)
                    
                except Exception as e:
                    logger.warning(f"Failed to create QA pair: {str(e)}")
                    continue
            
            # 批量保存
            if batch_objects:
                db.session.bulk_save_objects(batch_objects)
                db.session.commit()
                saved_count = len(batch_objects)
                
                logger.debug(f"Batch saved {saved_count} QA pairs")
            
            return saved_count
            
        except Exception as e:
            logger.error(f"Optimized save failed: {str(e)}")
            db.session.rollback()
            raise
    
    def _create_raw_qa_pairs_optimized(self, messages: List[Dict], upload_id: int) -> List:
        """优化的原始QA对创建"""
        
        logger.info(f"Creating optimized raw QA pairs from {len(messages)} messages")
        
        raw_pairs = []
        existing_fingerprints = self._get_existing_content_fingerprints()
        
        # 分批处理消息
        for i in range(0, len(messages) - 1, 2):
            try:
                question_msg = messages[i]
                answer_msg = messages[i + 1] if i + 1 < len(messages) else question_msg
                
                # 避免同一人的连续消息
                if question_msg['sender'] == answer_msg['sender'] and i + 2 < len(messages):
                    answer_msg = messages[i + 2]
                
                # 内容处理
                question_content = question_msg['content'][:2000]
                answer_content = answer_msg['content'][:2000] if question_msg != answer_msg else "待补充回答"
                
                # 去重检查
                content_fingerprint = self._generate_content_fingerprint(
                    question_content, answer_content,
                    question_msg['sender'], answer_msg['sender']
                )
                
                if content_fingerprint in existing_fingerprints:
                    continue
                
                qa_pair = QAPair(
                    question=question_content,
                    answer=answer_content,
                    category_id=1,
                    asker=question_msg['sender'][:100],
                    advisor=answer_msg['sender'][:100] if question_msg != answer_msg else "系统",
                    confidence=0.1,
                    source_file=f"upload_{upload_id}_raw",
                    original_context=json.dumps({
                        'raw_import': True,
                        'needs_review': True,
                        'question_timestamp': str(question_msg.get('timestamp', '')),
                        'answer_timestamp': str(answer_msg.get('timestamp', ''))
                    }, ensure_ascii=False)
                )
                
                raw_pairs.append(qa_pair)
                existing_fingerprints.add(content_fingerprint)
                
            except Exception as e:
                logger.warning(f"Failed to create raw QA pair: {str(e)}")
                continue
        
        # 批量保存
        if raw_pairs:
            for i in range(0, len(raw_pairs), self.batch_size):
                batch = raw_pairs[i:i + self.batch_size]
                try:
                    db.session.bulk_save_objects(batch)
                    db.session.commit()
                except Exception as e:
                    logger.error(f"Failed to save raw batch: {str(e)}")
                    db.session.rollback()
        
        logger.info(f"Created {len(raw_pairs)} raw QA pairs")
        return raw_pairs
    
    def _safe_serialize_context(self, context) -> str:
        """安全的上下文序列化"""
        try:
            if not context:
                return json.dumps({}, ensure_ascii=False)
            
            # 限制上下文大小
            if isinstance(context, list) and len(context) > 10:
                context = context[:10]
            
            safe_context = []
            for item in context if isinstance(context, list) else [context]:
                if isinstance(item, dict):
                    safe_item = {}
                    for key, value in item.items():
                        if isinstance(value, datetime):
                            safe_item[key] = value.isoformat()
                        else:
                            safe_item[key] = str(value)[:200]  # 限制长度
                    safe_context.append(safe_item)
                else:
                    safe_context.append(str(item)[:200])
            
            return json.dumps(safe_context, ensure_ascii=False)
            
        except Exception as e:
            logger.warning(f"Context serialization failed: {str(e)}")
            return json.dumps({"error": "Serialization failed"}, ensure_ascii=False)
    
    def _get_existing_content_fingerprints(self) -> set:
        """获取现有内容指纹（内存优化版本）"""
        try:
            fingerprints = set()
            
            # 分批查询避免内存问题
            batch_size = 10000
            offset = 0
            
            while True:
                batch_pairs = db.session.query(
                    QAPair.question, QAPair.answer, QAPair.asker, QAPair.advisor
                ).offset(offset).limit(batch_size).all()
                
                if not batch_pairs:
                    break
                
                for question, answer, asker, advisor in batch_pairs:
                    fingerprint = self._generate_content_fingerprint(question, answer, asker, advisor)
                    fingerprints.add(fingerprint)
                
                offset += batch_size
                
                # 定期垃圾回收
                if offset % 50000 == 0:
                    gc.collect()
            
            logger.info(f"Loaded {len(fingerprints)} content fingerprints")
            return fingerprints
            
        except Exception as e:
            logger.error(f"Failed to load fingerprints: {str(e)}")
            return set()
    
    def _generate_content_fingerprint(self, question: str, answer: str, asker: str, advisor: str) -> str:
        """生成内容指纹"""
        import hashlib
        import re
        
        try:
            def normalize_text(text):
                if not text:
                    return ""
                text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
                text = re.sub(r'\s+', ' ', text)
                return text.lower().strip()
            
            norm_question = normalize_text(question)[:200]
            norm_answer = normalize_text(answer)[:200]
            norm_asker = normalize_text(asker) if asker else ""
            norm_advisor = normalize_text(advisor) if advisor else ""
            
            content = f"{norm_question}|{norm_answer}|{norm_asker}|{norm_advisor}"
            return hashlib.md5(content.encode('utf-8')).hexdigest()
            
        except Exception as e:
            logger.error(f"Fingerprint generation failed: {str(e)}")
            return f"fallback_{len(question or '')}_{len(answer or '')}"
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        return {
            'processing_stats': self.processing_stats.copy(),
            'memory_stats': self.memory_monitor.get_memory_stats(),
            'configuration': {
                'memory_warning_threshold_mb': self.memory_warning_threshold,
                'large_file_threshold_mb': self.large_file_threshold / 1024 / 1024,
                'batch_size': self.batch_size,
                'gc_frequency': self.gc_frequency
            }
        }
    
    def cleanup_resources(self):
        """清理资源"""
        try:
            self.streaming_processor.cleanup_temp_files()
            self.memory_monitor.cleanup_resources()
            gc.collect()
            logger.info("Resources cleaned up successfully")
        except Exception as e:
            logger.error(f"Resource cleanup failed: {str(e)}")


# 全局优化处理器实例
optimized_processor = OptimizedFileProcessor()


def get_optimized_processor() -> OptimizedFileProcessor:
    """获取优化的文件处理器实例"""
    return optimized_processor