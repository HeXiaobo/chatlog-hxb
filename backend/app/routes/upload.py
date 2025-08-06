"""
文件上传相关路由
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
        
        # 使用FileProcessor处理文件
        processor = FileProcessor()
        result = processor.process_file_async(file_path, original_filename)
        
        # 清理临时文件
        try:
            file_path.unlink()
        except Exception as e:
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