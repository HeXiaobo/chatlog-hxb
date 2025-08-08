"""
性能测试API路由
"""
from flask import Blueprint, jsonify, request
import logging
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.utils.performance_tester import get_performance_tester, run_quick_performance_test, run_full_performance_test
from app.utils.memory_monitor import get_memory_monitor
from app.services.task_queue import get_task_queue
from app.services.websocket_service import get_websocket_manager

logger = logging.getLogger(__name__)
performance_bp = Blueprint('performance', __name__)


@performance_bp.route('/test/quick', methods=['POST'])
def run_quick_test():
    """运行快速性能测试"""
    try:
        logger.info("Starting quick performance test")
        
        # 运行快速测试
        report = run_quick_performance_test()
        
        return jsonify({
            'success': True,
            'data': report,
            'message': '快速性能测试完成'
        }), 200
        
    except Exception as e:
        logger.error(f"Quick performance test failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'QUICK_TEST_ERROR',
                'message': '快速性能测试失败',
                'details': str(e)
            }
        }), 500


@performance_bp.route('/test/full', methods=['POST'])
def run_full_test():
    """运行完整性能测试"""
    try:
        logger.info("Starting full performance test")
        
        # 获取测试参数
        test_params = request.json or {}
        iterations = test_params.get('iterations', 5)
        
        # 配置测试器
        tester = get_performance_tester()
        tester.test_iterations = iterations
        
        # 运行完整测试
        results = tester.run_benchmark_suite()
        report = tester.generate_performance_report()
        
        return jsonify({
            'success': True,
            'data': {
                'report': report,
                'benchmark_count': len(results)
            },
            'message': f'完整性能测试完成，共执行 {len(results)} 个基准测试'
        }), 200
        
    except Exception as e:
        logger.error(f"Full performance test failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'FULL_TEST_ERROR',
                'message': '完整性能测试失败',
                'details': str(e)
            }
        }), 500


@performance_bp.route('/test/async', methods=['POST'])
def run_async_test():
    """运行异步性能测试"""
    try:
        # 获取任务队列并提交后台测试
        task_queue = get_task_queue()
        
        # 获取测试参数
        test_params = request.json or {}
        test_type = test_params.get('type', 'quick')  # quick 或 full
        
        # 提交后台任务
        def background_test():
            if test_type == 'full':
                return run_full_performance_test()
            else:
                return run_quick_performance_test()
        
        task_id = task_queue.submit_task(
            task_type="performance_test",
            func=background_test,
            priority=task_queue.TaskPriority.HIGH,
            timeout=600  # 10分钟超时
        )
        
        return jsonify({
            'success': True,
            'data': {
                'task_id': task_id,
                'test_type': test_type,
                'message': '性能测试已提交后台执行，可通过WebSocket监听进度'
            },
            'websocket_info': {
                'subscribe_event': 'subscribe_task',
                'task_id': task_id,
                'status_event': 'task_status_update'
            }
        }), 202
        
    except Exception as e:
        logger.error(f"Async performance test failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'ASYNC_TEST_ERROR',
                'message': '异步性能测试失败',
                'details': str(e)
            }
        }), 500


@performance_bp.route('/metrics/memory')
def get_memory_metrics():
    """获取内存使用指标"""
    try:
        memory_monitor = get_memory_monitor()
        stats = memory_monitor.get_memory_stats()
        
        return jsonify({
            'success': True,
            'data': stats,
            'message': '内存指标获取成功'
        }), 200
        
    except Exception as e:
        logger.error(f"Get memory metrics error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'MEMORY_METRICS_ERROR',
                'message': '获取内存指标失败',
                'details': str(e)
            }
        }), 500


@performance_bp.route('/metrics/system')
def get_system_metrics():
    """获取系统性能指标"""
    try:
        import psutil
        import platform
        
        # CPU信息
        cpu_info = {
            'cpu_count': psutil.cpu_count(),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'cpu_freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
        }
        
        # 内存信息
        memory = psutil.virtual_memory()
        memory_info = {
            'total_gb': memory.total / (1024**3),
            'available_gb': memory.available / (1024**3),
            'used_gb': memory.used / (1024**3),
            'percent': memory.percent
        }
        
        # 磁盘信息
        disk = psutil.disk_usage('/')
        disk_info = {
            'total_gb': disk.total / (1024**3),
            'free_gb': disk.free / (1024**3),
            'used_gb': disk.used / (1024**3),
            'percent': (disk.used / disk.total) * 100
        }
        
        # 系统信息
        system_info = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'architecture': platform.architecture()
        }
        
        return jsonify({
            'success': True,
            'data': {
                'cpu': cpu_info,
                'memory': memory_info,
                'disk': disk_info,
                'system': system_info,
                'timestamp': datetime.utcnow().isoformat()
            },
            'message': '系统指标获取成功'
        }), 200
        
    except Exception as e:
        logger.error(f"Get system metrics error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'SYSTEM_METRICS_ERROR',
                'message': '获取系统指标失败',
                'details': str(e)
            }
        }), 500


@performance_bp.route('/metrics/queue')
def get_queue_metrics():
    """获取任务队列性能指标"""
    try:
        task_queue = get_task_queue()
        queue_stats = task_queue.get_queue_stats()
        
        return jsonify({
            'success': True,
            'data': queue_stats,
            'message': '队列指标获取成功'
        }), 200
        
    except Exception as e:
        logger.error(f"Get queue metrics error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'QUEUE_METRICS_ERROR',
                'message': '获取队列指标失败',
                'details': str(e)
            }
        }), 500


@performance_bp.route('/metrics/websocket')
def get_websocket_metrics():
    """获取WebSocket性能指标"""
    try:
        websocket_manager = get_websocket_manager()
        stats = websocket_manager.get_connection_stats()
        
        return jsonify({
            'success': True,
            'data': stats,
            'message': 'WebSocket指标获取成功'
        }), 200
        
    except Exception as e:
        logger.error(f"Get WebSocket metrics error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'WEBSOCKET_METRICS_ERROR',
                'message': '获取WebSocket指标失败',
                'details': str(e)
            }
        }), 500


@performance_bp.route('/benchmark/single', methods=['POST'])
def run_single_benchmark():
    """运行单个基准测试"""
    try:
        params = request.json or {}
        benchmark_type = params.get('type')
        iterations = params.get('iterations', 3)
        
        if not benchmark_type:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_PARAMS',
                    'message': '缺少基准测试类型参数'
                }
            }), 400
        
        tester = get_performance_tester()
        tester.test_iterations = iterations
        
        # 运行指定的基准测试
        benchmark_methods = {
            'database': tester.benchmark_database_operations,
            'search': tester.benchmark_search_operations,
            'file_processing': tester.benchmark_file_processing,
            'memory': tester.benchmark_memory_operations,
            'concurrent': tester.benchmark_concurrent_operations
        }
        
        if benchmark_type not in benchmark_methods:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_BENCHMARK_TYPE',
                    'message': f'不支持的基准测试类型: {benchmark_type}',
                    'available_types': list(benchmark_methods.keys())
                }
            }), 400
        
        logger.info(f"Running single benchmark: {benchmark_type}")
        result = benchmark_methods[benchmark_type]()
        
        return jsonify({
            'success': True,
            'data': {
                'test_name': result.test_name,
                'summary': result.summary,
                'timestamp': result.timestamp.isoformat(),
                'metrics_count': len(result.metrics)
            },
            'message': f'{benchmark_type} 基准测试完成'
        }), 200
        
    except Exception as e:
        logger.error(f"Single benchmark failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'SINGLE_BENCHMARK_ERROR',
                'message': '单个基准测试失败',
                'details': str(e)
            }
        }), 500


@performance_bp.route('/reports')
def list_performance_reports():
    """获取性能报告列表"""
    try:
        from pathlib import Path
        
        report_dir = Path("performance_reports")
        if not report_dir.exists():
            return jsonify({
                'success': True,
                'data': {
                    'reports': [],
                    'total_count': 0
                },
                'message': '暂无性能报告'
            }), 200
        
        # 获取报告文件列表
        report_files = []
        for report_file in report_dir.glob("performance_report_*.json"):
            try:
                stat = report_file.stat()
                report_files.append({
                    'filename': report_file.name,
                    'path': str(report_file),
                    'size_kb': stat.st_size // 1024,
                    'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except Exception as e:
                logger.warning(f"Failed to get report file info {report_file}: {str(e)}")
        
        # 按修改时间排序
        report_files.sort(key=lambda x: x['modified_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': {
                'reports': report_files,
                'total_count': len(report_files)
            },
            'message': '性能报告列表获取成功'
        }), 200
        
    except Exception as e:
        logger.error(f"List performance reports error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'LIST_REPORTS_ERROR',
                'message': '获取性能报告列表失败',
                'details': str(e)
            }
        }), 500


@performance_bp.route('/reports/<report_name>')
def get_performance_report(report_name):
    """获取特定性能报告"""
    try:
        from pathlib import Path
        import json
        
        # 安全文件名检查
        if '..' in report_name or '/' in report_name:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_FILENAME',
                    'message': '无效的报告文件名'
                }
            }), 400
        
        report_dir = Path("performance_reports")
        report_file = report_dir / report_name
        
        if not report_file.exists():
            return jsonify({
                'success': False,
                'error': {
                    'code': 'REPORT_NOT_FOUND',
                    'message': '性能报告不存在'
                }
            }), 404
        
        # 读取报告内容
        with open(report_file, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        return jsonify({
            'success': True,
            'data': report_data,
            'message': '性能报告获取成功'
        }), 200
        
    except Exception as e:
        logger.error(f"Get performance report error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'GET_REPORT_ERROR',
                'message': '获取性能报告失败',
                'details': str(e)
            }
        }), 500


@performance_bp.route('/cleanup/memory', methods=['POST'])
def trigger_memory_cleanup():
    """触发内存清理"""
    try:
        memory_monitor = get_memory_monitor()
        
        # 强制垃圾回收
        gc_result = memory_monitor.force_garbage_collection()
        
        # 获取清理后的内存状态
        after_stats = memory_monitor.get_memory_stats()
        
        return jsonify({
            'success': True,
            'data': {
                'garbage_collection': gc_result,
                'memory_stats': after_stats
            },
            'message': '内存清理完成'
        }), 200
        
    except Exception as e:
        logger.error(f"Memory cleanup error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'MEMORY_CLEANUP_ERROR',
                'message': '内存清理失败',
                'details': str(e)
            }
        }), 500


@performance_bp.route('/monitoring/start', methods=['POST'])
def start_performance_monitoring():
    """开始性能监控"""
    try:
        memory_monitor = get_memory_monitor()
        
        if not memory_monitor.is_monitoring:
            memory_monitor.start_monitoring()
            message = '性能监控已启动'
        else:
            message = '性能监控已经在运行中'
        
        return jsonify({
            'success': True,
            'data': {
                'monitoring_status': memory_monitor.is_monitoring,
                'monitoring_interval': memory_monitor.monitoring_interval
            },
            'message': message
        }), 200
        
    except Exception as e:
        logger.error(f"Start monitoring error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'START_MONITORING_ERROR',
                'message': '启动性能监控失败',
                'details': str(e)
            }
        }), 500


@performance_bp.route('/monitoring/stop', methods=['POST'])
def stop_performance_monitoring():
    """停止性能监控"""
    try:
        memory_monitor = get_memory_monitor()
        
        if memory_monitor.is_monitoring:
            memory_monitor.stop_monitoring()
            message = '性能监控已停止'
        else:
            message = '性能监控未在运行'
        
        return jsonify({
            'success': True,
            'data': {
                'monitoring_status': memory_monitor.is_monitoring
            },
            'message': message
        }), 200
        
    except Exception as e:
        logger.error(f"Stop monitoring error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'STOP_MONITORING_ERROR',
                'message': '停止性能监控失败',
                'details': str(e)
            }
        }), 500