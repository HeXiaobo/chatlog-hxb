"""
管理相关路由
"""
import os
import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from app import db
from app.models import QAPair, Category, UploadHistory
from app.services.search_service import SearchService

logger = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/stats')
def get_system_stats():
    """获取系统统计"""
    try:
        # 基础统计
        qa_stats = QAPair.get_statistics()
        
        # 上传统计
        upload_stats = _get_upload_statistics()
        
        # 搜索统计
        search_service = SearchService()
        search_stats = search_service.get_search_statistics()
        
        # 系统性能统计
        system_stats = _get_system_statistics()
        
        return jsonify({
            'success': True,
            'data': {
                'qa_statistics': qa_stats,
                'upload_statistics': upload_stats,
                'search_statistics': search_stats,
                'system_statistics': system_stats,
                'generated_at': datetime.utcnow().isoformat() + 'Z'
            },
            'message': '系统统计获取成功'
        })
        
    except Exception as e:
        logger.error(f"Get system stats error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'SYSTEM_STATS_ERROR',
                'message': '获取系统统计失败',
                'details': str(e)
            }
        }), 500


@admin_bp.route('/reindex', methods=['POST'])
def rebuild_search_index():
    """重建搜索索引"""
    try:
        search_service = SearchService()
        result = search_service.rebuild_index()
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message'],
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'REINDEX_ERROR',
                    'message': '重建索引失败',
                    'details': result['error']
                }
            }), 500
            
    except Exception as e:
        logger.error(f"Rebuild index error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'REINDEX_ERROR',
                'message': '重建索引失败',
                'details': str(e)
            }
        }), 500


@admin_bp.route('/health')
def system_health():
    """系统健康检查"""
    try:
        health_status = {
            'overall': 'healthy',
            'components': {},
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        # 数据库健康检查
        try:
            db.session.execute('SELECT 1').fetchone()
            health_status['components']['database'] = {
                'status': 'healthy',
                'message': '数据库连接正常'
            }
        except Exception as e:
            health_status['components']['database'] = {
                'status': 'unhealthy',
                'message': f'数据库连接失败: {str(e)}'
            }
            health_status['overall'] = 'unhealthy'
        
        # 搜索服务健康检查
        try:
            search_service = SearchService()
            search_stats = search_service.get_search_statistics()
            health_status['components']['search'] = {
                'status': 'healthy',
                'message': '搜索服务正常',
                'fts_enabled': search_stats.get('fts_status', {}).get('enabled', False)
            }
        except Exception as e:
            health_status['components']['search'] = {
                'status': 'degraded',
                'message': f'搜索服务异常: {str(e)}'
            }
            if health_status['overall'] == 'healthy':
                health_status['overall'] = 'degraded'
        
        # 文件系统健康检查
        try:
            from flask import current_app
            upload_folder = current_app.config.get('UPLOAD_FOLDER')
            if upload_folder and os.path.exists(upload_folder):
                health_status['components']['filesystem'] = {
                    'status': 'healthy',
                    'message': '文件系统正常',
                    'upload_folder': upload_folder
                }
            else:
                health_status['components']['filesystem'] = {
                    'status': 'unhealthy',
                    'message': '上传目录不存在',
                    'upload_folder': upload_folder
                }
                health_status['overall'] = 'unhealthy'
        except Exception as e:
            health_status['components']['filesystem'] = {
                'status': 'unhealthy',
                'message': f'文件系统检查失败: {str(e)}'
            }
            health_status['overall'] = 'unhealthy'
        
        # 内存使用检查
        try:
            import psutil
            memory_percent = psutil.virtual_memory().percent
            if memory_percent < 80:
                health_status['components']['memory'] = {
                    'status': 'healthy',
                    'message': f'内存使用正常 ({memory_percent:.1f}%)',
                    'usage_percent': memory_percent
                }
            elif memory_percent < 90:
                health_status['components']['memory'] = {
                    'status': 'warning',
                    'message': f'内存使用偏高 ({memory_percent:.1f}%)',
                    'usage_percent': memory_percent
                }
                if health_status['overall'] == 'healthy':
                    health_status['overall'] = 'degraded'
            else:
                health_status['components']['memory'] = {
                    'status': 'unhealthy',
                    'message': f'内存使用过高 ({memory_percent:.1f}%)',
                    'usage_percent': memory_percent
                }
                health_status['overall'] = 'unhealthy'
        except ImportError:
            health_status['components']['memory'] = {
                'status': 'unknown',
                'message': 'psutil未安装，无法检查内存使用'
            }
        except Exception as e:
            health_status['components']['memory'] = {
                'status': 'unknown',
                'message': f'内存检查失败: {str(e)}'
            }
        
        # 根据总体状态决定HTTP状态码
        status_code = 200
        if health_status['overall'] == 'degraded':
            status_code = 200  # 仍然可用
        elif health_status['overall'] == 'unhealthy':
            status_code = 503  # 服务不可用
        
        return jsonify({
            'success': True,
            'data': health_status,
            'message': f'系统状态: {health_status["overall"]}'
        }), status_code
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'success': False,
            'data': {
                'overall': 'unhealthy',
                'components': {},
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            },
            'error': {
                'code': 'HEALTH_CHECK_ERROR',
                'message': '健康检查失败',
                'details': str(e)
            }
        }), 503


@admin_bp.route('/cleanup', methods=['POST'])
def cleanup_system():
    """系统清理"""
    try:
        cleanup_type = request.json.get('type', 'all') if request.json else 'all'
        days = request.json.get('days', 30) if request.json else 30
        
        result = {
            'cleaned_items': {},
            'total_cleaned': 0
        }
        
        if cleanup_type in ['all', 'uploads']:
            # 清理失败的上传记录
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            failed_uploads = UploadHistory.query.filter(
                UploadHistory.status == 'failed',
                UploadHistory.created_at < cutoff_date
            )
            failed_count = failed_uploads.count()
            failed_uploads.delete()
            
            result['cleaned_items']['failed_uploads'] = failed_count
            result['total_cleaned'] += failed_count
        
        if cleanup_type in ['all', 'temp_files']:
            # 清理临时文件
            from app.services import FileProcessor
            processor = FileProcessor()
            temp_files_cleaned = processor.cleanup_temp_files(days * 24)
            
            result['cleaned_items']['temp_files'] = temp_files_cleaned
            result['total_cleaned'] += temp_files_cleaned
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': result,
            'message': f'清理完成，共清理 {result["total_cleaned"]} 项'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"System cleanup error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'CLEANUP_ERROR',
                'message': '系统清理失败',
                'details': str(e)
            }
        }), 500


def _get_upload_statistics():
    """获取上传统计"""
    try:
        from sqlalchemy import func
        
        # 基础统计
        total_uploads = UploadHistory.query.count()
        
        # 按状态统计
        status_stats = db.session.query(
            UploadHistory.status,
            func.count(UploadHistory.id).label('count')
        ).group_by(UploadHistory.status).all()
        
        # 最近7天统计
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_uploads = UploadHistory.query.filter(
            UploadHistory.uploaded_at >= week_ago
        ).count()
        
        # 成功上传统计
        successful_stats = db.session.query(
            func.sum(UploadHistory.qa_count).label('total_qa'),
            func.avg(UploadHistory.processing_time).label('avg_time'),
            func.sum(UploadHistory.file_size).label('total_size')
        ).filter(UploadHistory.status == 'completed').first()
        
        return {
            'total_uploads': total_uploads,
            'recent_uploads_7d': recent_uploads,
            'status_distribution': {
                stat[0]: stat[1] for stat in status_stats
            },
            'successful_processing': {
                'total_qa_extracted': successful_stats.total_qa or 0,
                'avg_processing_time': round(successful_stats.avg_time or 0, 2),
                'total_file_size_mb': round((successful_stats.total_size or 0) / (1024 * 1024), 2)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get upload statistics: {str(e)}")
        return {'error': str(e)}


def _get_system_statistics():
    """获取系统统计"""
    try:
        from flask import current_app
        
        # 配置信息
        config_info = {
            'debug_mode': current_app.config.get('DEBUG', False),
            'max_file_size_mb': (current_app.config.get('MAX_CONTENT_LENGTH', 0) // (1024 * 1024)),
            'upload_folder': str(current_app.config.get('UPLOAD_FOLDER', '')),
            'database_uri': current_app.config.get('SQLALCHEMY_DATABASE_URI', '').split('/')[-1]  # 只显示数据库名
        }
        
        # 数据库统计
        try:
            db_size_result = db.session.execute(
                "SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()"
            ).fetchone()
            db_size_mb = round(db_size_result[0] / (1024 * 1024), 2) if db_size_result else 0
        except:
            db_size_mb = 0
        
        return {
            'config': config_info,
            'database': {
                'size_mb': db_size_mb,
                'connection_pool_size': current_app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {}).get('pool_size', 'default')
            },
            'uptime': _get_uptime(),
            'version': '1.0.0'
        }
        
    except Exception as e:
        logger.error(f"Failed to get system statistics: {str(e)}")
        return {'error': str(e)}


def _get_uptime():
    """获取系统运行时间（简化版）"""
    try:
        # 这里可以从进程启动时间计算，简化为返回固定消息
        return {
            'message': '系统运行正常',
            'note': '具体运行时间需要在生产环境中配置'
        }
    except:
        return {'message': '无法获取运行时间'}