"""
文件上传相关路由 - 支持异步处理和实时状态更新
"""
from flask import Blueprint, jsonify, request, current_app
from werkzeug.utils import secure_filename
import os
import logging
from datetime import datetime
from pathlib import Path
from app import db
from app.models import UploadHistory
from app.services import FileProcessor
from app.services.ai_file_processor import AIFileProcessor
from app.services.intelligent_file_processor import intelligent_file_processor
from app.services.task_queue import get_file_processing_service, TaskPriority
from app.services.websocket_service import get_websocket_manager

logger = logging.getLogger(__name__)
upload_bp = Blueprint('upload', __name__)


@upload_bp.route('/file', methods=['POST'])
def upload_file():
    """上传并处理微信聊天记录JSON文件"""
    try:
        # 检查文件
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NO_FILE',
                    'message': '未选择文件',
                    'details': '请选择要上传的JSON文件'
                }
            }), 400
        
        file = request.files['file']
        if not file.filename:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'EMPTY_FILENAME',
                    'message': '文件名为空',
                    'details': '请选择有效的文件'
                }
            }), 400
        
        # 保存上传的文件
        original_filename = file.filename
        filename = secure_filename(original_filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        
        upload_folder = Path(current_app.config['UPLOAD_FOLDER'])
        upload_folder.mkdir(exist_ok=True)
        file_path = upload_folder / filename
        
        # 保存文件
        file.save(str(file_path))
        logger.info(f"File saved: {file_path}")
        
        # 强制调试输出
        print(f"[UPLOAD-DEBUG] File received: {original_filename}")
        print(f"[UPLOAD-DEBUG] File size: {file_path.stat().st_size} bytes")
        print(f"[UPLOAD-DEBUG] Saved to: {file_path}")
        
        # 调试：备份前端发送的文件用于分析
        debug_path = file_path.parent / f"debug_{filename}"
        try:
            import shutil
            shutil.copy2(file_path, debug_path)
            print(f"[UPLOAD-DEBUG] Debug copy saved: {debug_path}")
            logger.info(f"Debug copy saved: {debug_path}")
        except Exception as e:
            print(f"[UPLOAD-DEBUG] Failed to create debug copy: {e}")
        
        # 获取处理选项
        use_ai = request.form.get('use_ai', 'true').lower() == 'true'
        processing_mode = request.form.get('processing_mode', 'standard')  # 'standard' 或 'intelligent'
        
        # 选择处理器
        if processing_mode == 'intelligent':
            # 使用新的智能处理器
            import asyncio
            result_obj = asyncio.run(intelligent_file_processor.process_file_intelligently(
                file_path, original_filename, force_ai=use_ai
            ))
            
            # 转换为兼容格式
            result = {
                'success': result_obj.success,
                'upload_id': result_obj.upload_id,
                'total_extracted': result_obj.qa_pairs_extracted,
                'total_saved': result_obj.final_knowledge_entries,
                'processing_time': result_obj.processing_time,
                'processing_method': result_obj.processing_method,
                'ai_enabled': result_obj.ai_enabled,
                'statistics': {
                    'original_messages': result_obj.original_messages,
                    'useful_messages': result_obj.useful_messages,
                    'noise_filtered': result_obj.noise_filtered,
                    'extraction_efficiency': result_obj.extraction_efficiency,
                    'content_improvement_rate': result_obj.content_improvement_rate,
                    'ai_provider_used': result_obj.ai_provider_used,
                    'tokens_consumed': result_obj.tokens_consumed,
                    'processing_cost': result_obj.processing_cost
                },
                'message': f'智能处理完成! 从{result_obj.original_messages}条消息中生成{result_obj.final_knowledge_entries}个高质量知识库条目',
                'error': result_obj.error_message
            }
        elif use_ai:
            processor = AIFileProcessor()
            result = processor.process_file_async_with_ai(file_path, original_filename, use_ai=True)
        else:
            processor = FileProcessor()
            result = processor.process_file_async(file_path, original_filename)
        
        # 清理临时文件（仅在成功时清理）
        try:
            if result['success']:
                file_path.unlink()
                print(f"[UPLOAD-DEBUG] Cleaned up temp file: {file_path}")
            else:
                print(f"[UPLOAD-DEBUG] Keeping failed file for analysis: {file_path}")
        except Exception as e:
            print(f"[UPLOAD-DEBUG] Failed to clean temp file: {str(e)}")
            logger.warning(f"Failed to remove temp file {file_path}: {str(e)}")
        
        # 返回处理结果
        if result['success']:
            response_data = {
                'success': True,
                'data': {
                    'upload_id': result['upload_id'],
                    'filename': original_filename,
                    'total_extracted': result.get('total_extracted', 0),
                    'total_saved': result.get('total_saved', 0),
                    'processing_time': result.get('processing_time', 0),
                    'statistics': result.get('statistics', {})
                },
                'message': result.get('message', '文件处理完成')
            }
            
            return jsonify(response_data), 200
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'PROCESSING_ERROR',
                    'message': '文件处理失败',
                    'details': result.get('error', '未知错误')
                }
            }), 400
            
    except Exception as e:
        logger.error(f"Upload file error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'UPLOAD_ERROR',
                'message': '文件上传失败',
                'details': str(e)
            }
        }), 500


@upload_bp.route('/status/<int:upload_id>')
def get_upload_status(upload_id):
    """获取上传处理状态"""
    try:
        processor = FileProcessor()
        result = processor.get_processing_status(upload_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': {
                    'upload_id': result['upload_id'],
                    'filename': result['filename'],
                    'status': result['status'],
                    'qa_count': result['qa_count'],
                    'processing_time': result['processing_time'],
                    'uploaded_at': result['uploaded_at'],
                    'completed_at': result['completed_at'],
                    'error_message': result['error_message']
                },
                'message': '状态获取成功'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NOT_FOUND',
                    'message': result['error']
                }
            }), 404
            
    except Exception as e:
        logger.error(f"Get upload status error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'STATUS_ERROR',
                'message': '获取状态失败',
                'details': str(e)
            }
        }), 500


@upload_bp.route('/history')
def get_upload_history():
    """获取上传历史记录"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        
        # 构建查询
        query = UploadHistory.query
        
        # 状态筛选
        if status and status in ['processing', 'completed', 'failed']:
            query = query.filter_by(status=status)
        
        # 分页查询
        pagination = query.order_by(UploadHistory.uploaded_at.desc()).paginate(
            page=page,
            per_page=min(per_page, 100),
            error_out=False
        )
        
        # 转换数据
        history_data = []
        for record in pagination.items:
            history_data.append({
                'id': record.id,
                'filename': record.filename,
                'file_size': record.file_size,
                'status': record.status,
                'qa_count': record.qa_count or 0,
                'processing_time': record.processing_time,
                'uploaded_at': record.uploaded_at.isoformat() if record.uploaded_at else None,
                'completed_at': record.completed_at.isoformat() if record.completed_at else None,
                'error_message': record.error_message
            })
        
        return jsonify({
            'success': True,
            'data': history_data,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages
            },
            'message': '上传历史获取成功'
        }), 200
        
    except Exception as e:
        logger.error(f"Get upload history error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'HISTORY_ERROR',
                'message': '获取上传历史失败',
                'details': str(e)
            }
        }), 500


@upload_bp.route('/cleanup', methods=['POST'])
def cleanup_files():
    """清理临时文件"""
    try:
        max_age_hours = request.json.get('max_age_hours', 24) if request.json else 24
        
        processor = FileProcessor()
        cleaned_count = processor.cleanup_temp_files(max_age_hours)
        
        return jsonify({
            'success': True,
            'data': {
                'cleaned_files': cleaned_count
            },
            'message': f'清理了 {cleaned_count} 个临时文件'
        }), 200
        
    except Exception as e:
        logger.error(f"Cleanup files error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'CLEANUP_ERROR',
                'message': '清理文件失败',
                'details': str(e)
            }
        }), 500


@upload_bp.route('/ai/capabilities')
def get_ai_capabilities():
    """获取AI处理能力信息"""
    try:
        processor = AIFileProcessor()
        capabilities = processor.get_ai_processing_capabilities()
        
        return jsonify({
            'success': True,
            'data': capabilities,
            'message': 'AI能力信息获取成功'
        }), 200
        
    except Exception as e:
        logger.error(f"Get AI capabilities error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'AI_CAPABILITIES_ERROR',
                'message': '获取AI能力信息失败',
                'details': str(e)
            }
        }), 500


@upload_bp.route('/ai/enhance', methods=['POST'])
def enhance_existing_qa():
    """使用AI增强现有的低质量问答对"""
    try:
        import asyncio
        limit = request.json.get('limit', 100) if request.json else 100
        
        processor = AIFileProcessor()
        result = asyncio.run(processor.enhance_existing_qa_pairs(limit))
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': {
                    'enhanced_count': result['enhanced_count'],
                    'total_processed': result.get('total_processed', 0)
                },
                'message': result['message']
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'AI_ENHANCE_ERROR',
                    'message': result['error']
                }
            }), 400
            
    except Exception as e:
        logger.error(f"Enhance existing QA error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'ENHANCE_ERROR',
                'message': 'AI增强失败',
                'details': str(e)
            }
        }), 500


@upload_bp.route('/ai/usage')
def get_ai_usage():
    """获取AI使用统计"""
    try:
        processor = AIFileProcessor()
        usage_summary = processor.get_ai_usage_summary()
        
        return jsonify({
            'success': True,
            'data': usage_summary,
            'message': 'AI使用统计获取成功'
        }), 200
        
    except Exception as e:
        logger.error(f"Get AI usage error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'AI_USAGE_ERROR',
                'message': '获取AI使用统计失败',
                'details': str(e)
            }
        }), 500


@upload_bp.route('/file/ai', methods=['POST'])
def upload_file_with_ai():
    """使用AI处理的文件上传接口"""
    try:
        # 检查文件
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NO_FILE',
                    'message': '未选择文件'
                }
            }), 400
        
        file = request.files['file']
        if not file.filename:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'EMPTY_FILENAME',
                    'message': '文件名为空'
                }
            }), 400
        
        # 保存文件
        original_filename = file.filename
        filename = secure_filename(original_filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_ai_{filename}"
        
        upload_folder = Path(current_app.config['UPLOAD_FOLDER'])
        upload_folder.mkdir(exist_ok=True)
        file_path = upload_folder / filename
        
        file.save(str(file_path))
        logger.info(f"AI processing file saved: {file_path}")
        
        # 使用AI处理器
        processor = AIFileProcessor()
        result = processor.process_file_async_with_ai(file_path, original_filename, use_ai=True)
        
        # 清理临时文件
        try:
            if result['success']:
                file_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to remove temp file: {str(e)}")
        
        # 返回结果
        if result['success']:
            return jsonify({
                'success': True,
                'data': {
                    'upload_id': result['upload_id'],
                    'filename': original_filename,
                    'total_extracted': result.get('total_extracted', 0),
                    'total_saved': result.get('total_saved', 0),
                    'processing_time': result.get('processing_time', 0),
                    'processing_method': result.get('processing_method', 'ai'),
                    'ai_enabled': result.get('ai_enabled', True),
                    'statistics': result.get('statistics', {})
                },
                'message': result.get('message', 'AI处理完成')
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'AI_PROCESSING_ERROR',
                    'message': 'AI处理失败',
                    'details': result.get('error', '未知错误')
                }
            }), 400
            
    except Exception as e:
        logger.error(f"Upload file with AI error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'AI_UPLOAD_ERROR',
                'message': 'AI文件上传失败',
                'details': str(e)
            }
        }), 500


@upload_bp.route('/file/intelligent', methods=['POST'])
def upload_file_intelligent():
    """使用智能处理器上传并处理文件
    实现用户描述的完整流程：导入 → AI分析 → 过滤无用内容 → 整理知识库
    """
    import asyncio
    
    async def process_intelligent():
        try:
            # 检查文件
            if 'file' not in request.files:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'NO_FILE',
                        'message': '未选择文件'
                    }
                }), 400
            
            file = request.files['file']
            if not file.filename:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'EMPTY_FILENAME',
                        'message': '文件名为空'
                    }
                }), 400
            
            # 保存文件
            original_filename = file.filename
            filename = secure_filename(original_filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_intelligent_{filename}"
            
            upload_folder = Path(current_app.config['UPLOAD_FOLDER'])
            upload_folder.mkdir(exist_ok=True)
            file_path = upload_folder / filename
            
            file.save(str(file_path))
            logger.info(f"Intelligent processing file saved: {file_path}")
            
            # 获取处理参数
            force_ai = request.form.get('force_ai', 'false').lower() == 'true'
            
            # 使用智能处理器
            try:
                result = await intelligent_file_processor.process_file_intelligently(
                    file_path, original_filename, force_ai=force_ai
                )
            except Exception as e:
                logger.error(f"Intelligent processing failed: {str(e)}")
                # 清理临时文件
                try:
                    file_path.unlink()
                except:
                    pass
                
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'INTELLIGENT_PROCESSING_ERROR',
                        'message': '智能处理失败',
                        'details': str(e)
                    }
                }), 500
            
            # 清理临时文件
            try:
                if result.success:
                    file_path.unlink()
                    logger.info(f"Cleaned up temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temp file: {str(e)}")
            
            # 返回结果
            if result.success:
                return jsonify({
                    'success': True,
                    'data': {
                        'upload_id': result.upload_id,
                        'filename': result.filename,
                        'processing_summary': {
                            'original_messages': result.original_messages,
                            'useful_messages': result.useful_messages,
                            'noise_filtered': result.noise_filtered,
                            'qa_pairs_extracted': result.qa_pairs_extracted,
                            'final_knowledge_entries': result.final_knowledge_entries,
                            'content_quality_score': result.content_quality_score,
                            'extraction_efficiency': result.extraction_efficiency
                        },
                        'processing_performance': {
                            'processing_time': result.processing_time,
                            'ai_processing_time': result.ai_processing_time,
                            'processing_method': result.processing_method,
                            'ai_enabled': result.ai_enabled
                        },
                        'ai_usage': {
                            'ai_provider_used': result.ai_provider_used,
                            'tokens_consumed': result.tokens_consumed,
                            'processing_cost': result.processing_cost,
                            'content_improvement_rate': result.content_improvement_rate
                        },
                        'detailed_stats': result.detailed_stats
                    },
                    'message': f'🤖 智能处理完成! 从 {result.original_messages} 条消息中生成 {result.final_knowledge_entries} 个高质量知识库条目'
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'INTELLIGENT_PROCESSING_FAILED',
                        'message': '智能处理失败',
                        'details': result.error_message or '未知错误'
                    }
                }), 400
                
        except Exception as e:
            logger.error(f"Upload file with intelligent processing error: {str(e)}")
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INTELLIGENT_UPLOAD_ERROR',
                    'message': '智能文件上传失败',
                    'details': str(e)
                }
            }), 500
    
    # 运行异步处理
    return asyncio.run(process_intelligent())


@upload_bp.route('/file/async', methods=['POST'])
def upload_file_async():
    """异步文件上传 - 使用后台任务队列处理"""
    try:
        # 检查文件
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NO_FILE',
                    'message': '未选择文件'
                }
            }), 400
        
        file = request.files['file']
        if not file.filename:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'EMPTY_FILENAME',
                    'message': '文件名为空'
                }
            }), 400
        
        # 保存上传的文件
        original_filename = file.filename
        filename = secure_filename(original_filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_async_{filename}"
        
        upload_folder = Path(current_app.config['UPLOAD_FOLDER'])
        upload_folder.mkdir(exist_ok=True)
        file_path = upload_folder / filename
        
        # 保存文件
        file.save(str(file_path))
        logger.info(f"Async file saved: {file_path}")
        
        # 获取处理选项
        priority_str = request.form.get('priority', 'normal').lower()
        priority_map = {
            'low': TaskPriority.LOW,
            'normal': TaskPriority.NORMAL,
            'high': TaskPriority.HIGH,
            'urgent': TaskPriority.URGENT
        }
        priority = priority_map.get(priority_str, TaskPriority.NORMAL)
        
        # 提交到后台任务队列
        file_processing_service = get_file_processing_service()
        task_id = file_processing_service.process_file_async(
            file_path, original_filename, priority=priority
        )
        
        # 返回任务ID，客户端可以通过WebSocket监听进度
        return jsonify({
            'success': True,
            'data': {
                'task_id': task_id,
                'filename': original_filename,
                'message': '文件已提交后台处理，请通过WebSocket监听处理进度'
            },
            'websocket_info': {
                'subscribe_event': 'subscribe_task',
                'task_id': task_id,
                'status_event': 'task_status_update'
            }
        }), 202
        
    except Exception as e:
        logger.error(f"Async upload error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'ASYNC_UPLOAD_ERROR',
                'message': '异步文件上传失败',
                'details': str(e)
            }
        }), 500


@upload_bp.route('/task/<task_id>/status')
def get_task_status(task_id):
    """获取异步任务状态"""
    try:
        file_processing_service = get_file_processing_service()
        status_data = file_processing_service.get_processing_status(task_id)
        
        if 'error' in status_data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TASK_NOT_FOUND',
                    'message': status_data['error']
                }
            }), 404
        
        return jsonify({
            'success': True,
            'data': status_data,
            'message': '任务状态获取成功'
        }), 200
        
    except Exception as e:
        logger.error(f"Get task status error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'TASK_STATUS_ERROR',
                'message': '获取任务状态失败',
                'details': str(e)
            }
        }), 500


@upload_bp.route('/queue/stats')
def get_queue_stats():
    """获取任务队列统计信息"""
    try:
        from app.services.task_queue import get_task_queue
        task_queue = get_task_queue()
        stats = task_queue.get_queue_stats()
        
        return jsonify({
            'success': True,
            'data': stats,
            'message': '队列统计获取成功'
        }), 200
        
    except Exception as e:
        logger.error(f"Get queue stats error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'QUEUE_STATS_ERROR',
                'message': '获取队列统计失败',
                'details': str(e)
            }
        }), 500


@upload_bp.route('/websocket/stats')
def get_websocket_stats():
    """获取WebSocket连接统计信息"""
    try:
        websocket_manager = get_websocket_manager()
        stats = websocket_manager.get_connection_stats()
        
        return jsonify({
            'success': True,
            'data': stats,
            'message': 'WebSocket统计获取成功'
        }), 200
        
    except Exception as e:
        logger.error(f"Get WebSocket stats error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'WEBSOCKET_STATS_ERROR',
                'message': '获取WebSocket统计失败',
                'details': str(e)
            }
        }), 500


@upload_bp.route('/task/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    """取消异步任务"""
    try:
        from app.services.task_queue import get_task_queue
        task_queue = get_task_queue()
        
        success = task_queue.cancel_task(task_id)
        
        if success:
            # 通知WebSocket客户端任务已取消
            websocket_manager = get_websocket_manager()
            websocket_manager.notify_task_update(task_id)
            
            return jsonify({
                'success': True,
                'data': {'task_id': task_id},
                'message': '任务已取消'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'CANCEL_FAILED',
                    'message': '任务取消失败，可能正在运行中或已完成'
                }
            }), 400
        
    except Exception as e:
        logger.error(f"Cancel task error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'CANCEL_ERROR',
                'message': '取消任务失败',
                'details': str(e)
            }
        }), 500