"""
文件处理服务
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
            
            # 读取JSON数据
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = f.read()
            
            # 提取问答对
            logger.info(f"Starting extraction for upload {upload_record.id}")
            qa_candidates = self.data_extractor.extract_from_json(json_data, str(file_path))
            
            if not qa_candidates:
                raise ValueError("未能从文件中提取到任何问答对")
            
            logger.info(f"Extracted {len(qa_candidates)} QA candidates")
            
            # 分类问答对
            classified_results = []
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
            
            # 保存到数据库
            saved_count = self._save_qa_pairs(classified_results, upload_record.id)
            
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
            )
            
            statistics = {
                'extraction': extraction_stats,
                'classification': classification_stats,
                'file_info': {
                    'filename': upload_record.filename,
                    'file_size': upload_record.file_size,
                    'processing_time': processing_time
                }
            }
            
            logger.info(f"Successfully processed upload {upload_record.id}: "
                       f"{len(qa_candidates)} extracted, {saved_count} saved")
            
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
        batch_size = 500  # 增大批量大小以提高性能
        
        try:
            # 优化：预加载所有分类到内存中，避免重复查询
            categories_dict = {cat.id: cat for cat in Category.query.all()}
            
            for i in range(0, len(classified_results), batch_size):
                batch = classified_results[i:i + batch_size]
                batch_objects = []
                
                for qa_candidate, classification in batch:
                    try:
                        # 使用预加载的分类字典
                        category_id = classification.category_id if classification.category_id in categories_dict else 1
                        
                        # 创建问答对对象但不立即添加到session
                        qa_pair = QAPair(
                            question=qa_candidate.question[:2000],  # 限制长度
                            answer=qa_candidate.answer[:2000],
                            category_id=category_id,
                            asker=qa_candidate.asker[:100] if qa_candidate.asker else None,
                            advisor=qa_candidate.advisor[:100] if qa_candidate.advisor else None,
                            confidence=qa_candidate.confidence,
                            source_file=f"upload_{upload_id}",
                            original_context=json.dumps(qa_candidate.context[:10], ensure_ascii=False) if qa_candidate.context else None
                        )
                        
                        batch_objects.append(qa_pair)
                        saved_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to create QA pair: {str(e)}")
                        continue
                
                # 批量添加到session
                if batch_objects:
                    db.session.bulk_save_objects(batch_objects)
                    db.session.commit()
                    
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
            
            return {
                'success': result.success,
                'upload_id': result.upload_id,
                'message': '文件处理完成' if result.success else result.error_message,
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