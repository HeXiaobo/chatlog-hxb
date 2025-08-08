"""
AI增强的文件处理服务
集成AI智能提取和分类功能的文件处理器
"""
import os
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from app import db
from app.models import QAPair, Category, UploadHistory
from .file_processor import FileProcessor, ProcessingResult
from .ai_data_extractor import AIDataExtractor, AIExtractionResult
from .ai_classifier import AIClassifier, AIClassificationResult
from .ai_config import ai_config_manager

logger = logging.getLogger(__name__)


@dataclass
class AIProcessingResult(ProcessingResult):
    """AI处理结果（扩展原ProcessingResult）"""
    ai_extraction_stats: Optional[Dict[str, Any]] = None
    ai_classification_stats: Optional[Dict[str, Any]] = None
    processing_method: str = 'hybrid'  # 'ai', 'fallback', 'hybrid'


class AIFileProcessor(FileProcessor):
    """AI增强的文件处理器"""
    
    def __init__(self):
        super().__init__()
        self.ai_extractor = AIDataExtractor()
        self.ai_classifier = AIClassifier()
        self.ai_enabled = self._check_ai_availability()
        
    def _check_ai_availability(self) -> bool:
        """检查AI功能是否可用"""
        providers = ai_config_manager.get_available_providers()
        return len(providers) > 0
    
    async def process_file_with_ai(self, file_path: Path, upload_record: UploadHistory, 
                                  force_ai: bool = False) -> AIProcessingResult:
        """
        使用AI处理文件
        
        Args:
            file_path: 文件路径
            upload_record: 上传记录
            force_ai: 是否强制使用AI（忽略可用性检查）
        
        Returns:
            AIProcessingResult: AI处理结果
        """
        start_time = datetime.utcnow()
        use_ai = force_ai or self.ai_enabled
        
        try:
            # 更新状态为处理中
            upload_record.status = 'processing'
            upload_record.started_at = start_time
            db.session.commit()
            
            # 读取JSON数据
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = f.read()
            
            logger.info(f"Starting {'AI-enhanced' if use_ai else 'standard'} processing for upload {upload_record.id}")
            
            # 使用AI提取问答对
            extraction_result = await self.ai_extractor.extract_from_json(
                json_data, str(file_path), use_ai=use_ai
            )
            
            if not extraction_result.qa_pairs:
                logger.warning(f"No QA pairs extracted from {file_path}")
                return await self._create_empty_ai_result(upload_record, start_time, extraction_result)
            
            logger.info(f"Extracted {len(extraction_result.qa_pairs)} QA pairs using {extraction_result.extraction_method}")
            
            # 使用AI分类问答对
            classification_results = await self._classify_qa_pairs_with_ai(
                extraction_result.qa_pairs, use_ai=use_ai
            )
            
            # 保存到数据库
            saved_count = await self._save_ai_processed_qa_pairs(
                extraction_result.qa_pairs, 
                classification_results, 
                upload_record.id
            )
            
            # 计算处理时间
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # 更新上传记录
            upload_record.status = 'completed'
            upload_record.completed_at = datetime.utcnow()
            upload_record.qa_count = saved_count
            upload_record.processing_time = processing_time
            db.session.commit()
            
            # 生成统计信息
            ai_extraction_stats = self.ai_extractor.get_extraction_stats(extraction_result)
            ai_classification_stats = self.ai_classifier.get_classification_stats(classification_results)
            
            statistics = {
                'ai_extraction': ai_extraction_stats,
                'ai_classification': ai_classification_stats,
                'processing': {
                    'total_qa_pairs': len(extraction_result.qa_pairs),
                    'saved_count': saved_count,
                    'processing_method': extraction_result.extraction_method,
                    'ai_enabled': use_ai,
                    'total_tokens_used': extraction_result.tokens_used + sum(r.tokens_used for r in classification_results),
                    'providers_used': list(set([extraction_result.provider_used] + [r.provider_used for r in classification_results]))
                },
                'file_info': {
                    'filename': upload_record.filename,
                    'file_size': upload_record.file_size,
                    'processing_time': processing_time
                }
            }
            
            logger.info(f"AI processing completed for upload {upload_record.id}: "
                       f"{saved_count} QA pairs saved using {extraction_result.extraction_method}")
            
            return AIProcessingResult(
                success=True,
                upload_id=upload_record.id,
                total_extracted=len(extraction_result.qa_pairs),
                total_saved=saved_count,
                processing_time=processing_time,
                statistics=statistics,
                ai_extraction_stats=ai_extraction_stats,
                ai_classification_stats=ai_classification_stats,
                processing_method=extraction_result.extraction_method
            )
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"AI processing failed for upload {upload_record.id}: {error_message}")
            
            # 更新上传记录为失败状态
            upload_record.status = 'failed'
            upload_record.error_message = error_message
            upload_record.completed_at = datetime.utcnow()
            db.session.commit()
            
            return AIProcessingResult(
                success=False,
                upload_id=upload_record.id,
                total_extracted=0,
                total_saved=0,
                processing_time=(datetime.utcnow() - start_time).total_seconds(),
                error_message=error_message,
                processing_method='error'
            )
    
    async def _classify_qa_pairs_with_ai(self, qa_pairs: List, use_ai: bool = True) -> List[AIClassificationResult]:
        """使用AI对问答对进行分类"""
        if not qa_pairs:
            return []
        
        try:
            # 准备分类数据
            qa_data = [
                (qa.question, qa.answer, qa.context) 
                for qa in qa_pairs
            ]
            
            # 批量分类
            classification_results = await self.ai_classifier.classify_batch_with_ai(
                qa_data, use_ai=use_ai
            )
            
            logger.info(f"Classified {len(classification_results)} QA pairs using "
                       f"{classification_results[0].classification_method if classification_results else 'none'}")
            
            return classification_results
            
        except Exception as e:
            logger.error(f"Failed to classify QA pairs: {str(e)}")
            # 返回默认分类结果
            return [
                AIClassificationResult(
                    category_match=self.ai_classifier.fallback_classifier.classify_qa(
                        qa.question, qa.answer, qa.context
                    ),
                    processing_time=0,
                    tokens_used=0,
                    provider_used='fallback',
                    classification_method='fallback'
                )
                for qa in qa_pairs
            ]
    
    async def _save_ai_processed_qa_pairs(self, qa_pairs: List, 
                                        classification_results: List[AIClassificationResult],
                                        upload_id: int) -> int:
        """保存AI处理的问答对到数据库"""
        saved_count = 0
        batch_size = 500
        
        try:
            # 预加载所有分类到内存中
            categories_dict = {cat.id: cat for cat in Category.query.all()}
            
            # 内容去重
            existing_fingerprints = self._get_existing_content_fingerprints()
            
            # 合并问答对和分类结果
            combined_data = list(zip(qa_pairs, classification_results))
            
            for i in range(0, len(combined_data), batch_size):
                batch = combined_data[i:i + batch_size]
                batch_objects = []
                
                for qa_candidate, classification_result in batch:
                    try:
                        # 使用AI分类结果
                        category_id = classification_result.category_match.category_id
                        if category_id not in categories_dict:
                            category_id = 1  # 默认分类
                        
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
                        
                        # 创建问答对对象
                        qa_pair = QAPair(
                            question=qa_candidate.question[:2000],
                            answer=qa_candidate.answer[:2000],
                            category_id=category_id,
                            asker=qa_candidate.asker[:100] if qa_candidate.asker else None,
                            advisor=qa_candidate.advisor[:100] if qa_candidate.advisor else None,
                            confidence=qa_candidate.confidence,
                            source_file=f"upload_{upload_id}_ai",
                            original_context=json.dumps({
                                'context': qa_candidate.context[:5],
                                'ai_processed': True,
                                'extraction_method': 'ai',
                                'classification_method': classification_result.classification_method,
                                'classification_confidence': classification_result.category_match.confidence,
                                'matched_keywords': classification_result.category_match.matched_keywords,
                                'reasoning': classification_result.reasoning
                            }, ensure_ascii=False)
                        )
                        
                        batch_objects.append(qa_pair)
                        existing_fingerprints.add(content_fingerprint)
                        
                    except Exception as e:
                        logger.error(f"Failed to create QA pair: {str(e)}")
                        continue
                
                # 批量保存
                if batch_objects:
                    db.session.bulk_save_objects(batch_objects)
                    db.session.commit()
                    
                    saved_count += len(batch_objects)
                    
                    # 更新FTS索引（如果启用）
                    try:
                        from .search_service import SearchService
                        search_service = SearchService()
                        if search_service.fts_enabled:
                            for qa_pair in batch_objects:
                                db.session.refresh(qa_pair)
                                search_service.update_fts_record(qa_pair, 'insert')
                    except Exception as fts_error:
                        logger.warning(f"Failed to update FTS index: {fts_error}")
                    
                    logger.debug(f"Saved AI batch {i//batch_size + 1}, count: {len(batch_objects)}")
            
            return saved_count
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to save AI processed QA pairs: {str(e)}")
            raise
    
    async def _create_empty_ai_result(self, upload_record: UploadHistory, 
                                    start_time: datetime,
                                    extraction_result: AIExtractionResult) -> AIProcessingResult:
        """创建空的AI处理结果"""
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # 更新上传记录
        upload_record.status = 'completed'
        upload_record.completed_at = datetime.utcnow()
        upload_record.qa_count = 0
        upload_record.processing_time = processing_time
        db.session.commit()
        
        statistics = {
            'ai_extraction': self.ai_extractor.get_extraction_stats(extraction_result),
            'ai_classification': {'total_classified': 0},
            'processing': {
                'total_qa_pairs': 0,
                'saved_count': 0,
                'processing_method': extraction_result.extraction_method,
                'message': '未找到有效的问答对话，可能需要调整AI提示词或检查数据格式'
            }
        }
        
        return AIProcessingResult(
            success=True,
            upload_id=upload_record.id,
            total_extracted=0,
            total_saved=0,
            processing_time=processing_time,
            statistics=statistics,
            processing_method=extraction_result.extraction_method
        )
    
    def process_file_async_with_ai(self, file_path: Path, filename: str, 
                                  use_ai: bool = None) -> Dict[str, Any]:
        """
        异步处理文件（AI增强版）
        
        Args:
            file_path: 文件路径
            filename: 文件名
            use_ai: 是否使用AI（None表示自动判断）
        
        Returns:
            Dict: 包含upload_id和处理信息的响应
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
            
            # 确定是否使用AI
            if use_ai is None:
                use_ai = self.ai_enabled
            
            # 使用asyncio运行异步处理
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    self.process_file_with_ai(file_path, upload_record, force_ai=use_ai)
                )
            finally:
                loop.close()
            
            # 生成用户友好的处理结果消息
            if result.success:
                method_desc = {
                    'ai': 'AI智能提取',
                    'fallback': '规则提取', 
                    'hybrid': '混合提取'
                }.get(result.processing_method, '未知方法')
                
                if result.total_extracted > 0:
                    message = f"处理完成：使用{method_desc}成功提取到 {result.total_extracted} 个问答对"
                    if result.ai_extraction_stats:
                        quality = result.ai_extraction_stats.get('extraction_quality', 'unknown')
                        message += f"，质量评级：{quality}"
                else:
                    message = f"处理完成：使用{method_desc}但未找到明显的问答对话"
                    if use_ai:
                        message += "。AI分析建议：检查对话内容是否包含明确的问答形式，或尝试调整处理参数。"
            else:
                message = result.error_message
            
            return {
                'success': result.success,
                'upload_id': result.upload_id,
                'message': message,
                'total_extracted': result.total_extracted,
                'total_saved': result.total_saved,
                'processing_time': result.processing_time,
                'processing_method': result.processing_method,
                'ai_enabled': use_ai,
                'statistics': result.statistics
            }
            
        except Exception as e:
            logger.error(f"Failed to process file with AI: {str(e)}")
            return {
                'success': False,
                'error': f'AI处理失败: {str(e)}'
            }
    
    def get_ai_processing_capabilities(self) -> Dict[str, Any]:
        """获取AI处理能力信息"""
        providers = ai_config_manager.get_available_providers()
        primary_provider = ai_config_manager.get_primary_provider()
        
        capabilities = {
            'ai_enabled': self.ai_enabled,
            'available_providers': providers,
            'primary_provider': primary_provider,
            'features': {
                'intelligent_extraction': self.ai_enabled,
                'semantic_classification': self.ai_enabled,
                'content_enhancement': self.ai_enabled,
                'quality_assessment': self.ai_enabled
            }
        }
        
        if primary_provider:
            config = ai_config_manager.get_model_config(primary_provider)
            capabilities['primary_config'] = {
                'model_name': config.model_name,
                'max_tokens': config.max_tokens,
                'daily_limit': config.daily_limit
            }
            
            stats = ai_config_manager.usage_stats.get(primary_provider)
            if stats:
                capabilities['usage_stats'] = {
                    'daily_requests': stats.daily_requests,
                    'daily_tokens': stats.daily_tokens,
                    'success_rate': (stats.successful_requests / max(stats.total_requests, 1)) * 100
                }
        
        return capabilities
    
    async def enhance_existing_qa_pairs(self, limit: int = 100) -> Dict[str, Any]:
        """使用AI增强现有的低质量问答对"""
        if not self.ai_enabled:
            return {'success': False, 'error': 'AI功能未启用'}
        
        try:
            # 找出置信度较低的问答对
            low_confidence_pairs = QAPair.query.filter(
                QAPair.confidence < 0.6
            ).order_by(QAPair.created_at.desc()).limit(limit).all()
            
            if not low_confidence_pairs:
                return {
                    'success': True,
                    'message': '没有找到需要增强的问答对',
                    'enhanced_count': 0
                }
            
            enhanced_count = 0
            
            # 重新分类
            qa_data = [(qa.question, qa.answer, []) for qa in low_confidence_pairs]
            classification_results = await self.ai_classifier.classify_batch_with_ai(qa_data)
            
            # 更新分类结果
            for qa_pair, classification in zip(low_confidence_pairs, classification_results):
                if classification.category_match.confidence > qa_pair.confidence:
                    qa_pair.category_id = classification.category_match.category_id
                    qa_pair.confidence = max(qa_pair.confidence, classification.category_match.confidence)
                    enhanced_count += 1
            
            db.session.commit()
            
            return {
                'success': True,
                'message': f'成功增强了 {enhanced_count} 个问答对',
                'enhanced_count': enhanced_count,
                'total_processed': len(low_confidence_pairs)
            }
            
        except Exception as e:
            logger.error(f"Failed to enhance existing QA pairs: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_ai_usage_summary(self) -> Dict[str, Any]:
        """获取AI使用摘要"""
        return ai_config_manager.get_usage_summary()