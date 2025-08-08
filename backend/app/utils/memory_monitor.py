"""
内存监控工具 - 监控系统内存使用和优化内存管理
"""
import psutil
import gc
import sys
import logging
import threading
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from contextlib import contextmanager
import resource
import tracemalloc

logger = logging.getLogger(__name__)


@dataclass
class MemorySnapshot:
    """内存快照"""
    timestamp: datetime
    rss_mb: float  # 实际物理内存使用
    vms_mb: float  # 虚拟内存使用
    percent: float  # 内存使用百分比
    available_mb: float  # 可用内存
    heap_size_mb: float  # 堆内存大小
    gc_stats: Dict[str, int]  # 垃圾回收统计
    thread_count: int  # 线程数量
    fd_count: int  # 文件描述符数量


@dataclass
class MemoryAlert:
    """内存告警"""
    level: str  # warning, critical
    message: str
    threshold: float
    current_value: float
    timestamp: datetime
    suggested_action: str


class MemoryMonitor:
    """内存监控器"""
    
    def __init__(self, 
                 warning_threshold: float = 75.0,  # 警告阈值（百分比）
                 critical_threshold: float = 90.0,  # 严重阈值（百分比）
                 monitoring_interval: int = 30,     # 监控间隔（秒）
                 max_snapshots: int = 1000):       # 最大快照数量
        
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.monitoring_interval = monitoring_interval
        self.max_snapshots = max_snapshots
        
        self.snapshots: List[MemorySnapshot] = []
        self.alerts: List[MemoryAlert] = []
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # 内存优化配置
        self.auto_gc = True
        self.gc_threshold_multiplier = 2.0
        
        # 回调函数
        self.alert_callbacks: List[Callable[[MemoryAlert], None]] = []
        
        # 启用内存追踪
        if not tracemalloc.is_tracing():
            tracemalloc.start()
    
    def add_alert_callback(self, callback: Callable[[MemoryAlert], None]):
        """添加告警回调函数"""
        self.alert_callbacks.append(callback)
    
    def get_current_snapshot(self) -> MemorySnapshot:
        """获取当前内存快照"""
        try:
            # 系统内存信息
            memory = psutil.virtual_memory()
            process = psutil.Process()
            
            # 进程内存信息
            memory_info = process.memory_info()
            
            # GC统计
            gc_stats = {
                f'gen_{i}': len(gc.get_objects(i)) for i in range(3)
            }
            
            # 堆内存大小（Python对象）
            heap_size = sys.getsizeof(gc.get_objects()) / 1024 / 1024
            
            # 线程和文件描述符统计
            thread_count = process.num_threads()
            try:
                fd_count = process.num_fds()
            except AttributeError:
                fd_count = 0  # Windows不支持
            
            return MemorySnapshot(
                timestamp=datetime.utcnow(),
                rss_mb=memory_info.rss / 1024 / 1024,
                vms_mb=memory_info.vms / 1024 / 1024,
                percent=memory.percent,
                available_mb=memory.available / 1024 / 1024,
                heap_size_mb=heap_size,
                gc_stats=gc_stats,
                thread_count=thread_count,
                fd_count=fd_count
            )
            
        except Exception as e:
            logger.error(f"Failed to get memory snapshot: {str(e)}")
            # 返回空快照
            return MemorySnapshot(
                timestamp=datetime.utcnow(),
                rss_mb=0, vms_mb=0, percent=0, available_mb=0,
                heap_size_mb=0, gc_stats={}, thread_count=0, fd_count=0
            )
    
    def check_thresholds(self, snapshot: MemorySnapshot):
        """检查内存阈值并生成告警"""
        current_time = datetime.utcnow()
        
        # 检查内存使用百分比
        if snapshot.percent >= self.critical_threshold:
            alert = MemoryAlert(
                level='critical',
                message=f'Critical memory usage: {snapshot.percent:.1f}%',
                threshold=self.critical_threshold,
                current_value=snapshot.percent,
                timestamp=current_time,
                suggested_action='Immediate memory cleanup required. Consider restarting the service.'
            )
            self.alerts.append(alert)
            self._trigger_alert_callbacks(alert)
            
            # 自动触发内存优化
            if self.auto_gc:
                self.force_garbage_collection()
                
        elif snapshot.percent >= self.warning_threshold:
            alert = MemoryAlert(
                level='warning',
                message=f'High memory usage: {snapshot.percent:.1f}%',
                threshold=self.warning_threshold,
                current_value=snapshot.percent,
                timestamp=current_time,
                suggested_action='Consider running garbage collection or clearing caches.'
            )
            self.alerts.append(alert)
            self._trigger_alert_callbacks(alert)
        
        # 检查进程内存使用（RSS）
        rss_threshold = 1024  # 1GB
        if snapshot.rss_mb >= rss_threshold:
            alert = MemoryAlert(
                level='warning',
                message=f'High process memory usage: {snapshot.rss_mb:.1f}MB',
                threshold=rss_threshold,
                current_value=snapshot.rss_mb,
                timestamp=current_time,
                suggested_action='Monitor for memory leaks. Consider process restart if continues growing.'
            )
            self.alerts.append(alert)
            self._trigger_alert_callbacks(alert)
        
        # 清理旧告警
        self._cleanup_old_alerts()
    
    def _trigger_alert_callbacks(self, alert: MemoryAlert):
        """触发告警回调"""
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {str(e)}")
    
    def _cleanup_old_alerts(self):
        """清理1小时前的告警"""
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        self.alerts = [alert for alert in self.alerts if alert.timestamp > cutoff_time]
    
    def start_monitoring(self):
        """开始监控"""
        if self.is_monitoring:
            logger.warning("Memory monitoring is already running")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Memory monitoring started")
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        logger.info("Memory monitoring stopped")
    
    def _monitoring_loop(self):
        """监控主循环"""
        while self.is_monitoring:
            try:
                snapshot = self.get_current_snapshot()
                self.snapshots.append(snapshot)
                
                # 限制快照数量
                if len(self.snapshots) > self.max_snapshots:
                    self.snapshots = self.snapshots[-self.max_snapshots:]
                
                # 检查阈值
                self.check_thresholds(snapshot)
                
                # 休眠
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(5)
    
    def force_garbage_collection(self) -> Dict[str, Any]:
        """强制垃圾回收"""
        try:
            logger.info("Running forced garbage collection...")
            
            # 获取GC前的统计
            before_stats = {f'gen_{i}': len(gc.get_objects(i)) for i in range(3)}
            before_memory = self.get_current_snapshot()
            
            # 执行垃圾回收
            collected = gc.collect()
            
            # 获取GC后的统计
            after_stats = {f'gen_{i}': len(gc.get_objects(i)) for i in range(3)}
            after_memory = self.get_current_snapshot()
            
            result = {
                'objects_collected': collected,
                'memory_freed_mb': before_memory.rss_mb - after_memory.rss_mb,
                'before_objects': before_stats,
                'after_objects': after_stats,
                'before_memory_mb': before_memory.rss_mb,
                'after_memory_mb': after_memory.rss_mb
            }
            
            logger.info(f"GC completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to run garbage collection: {str(e)}")
            return {'error': str(e)}
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取内存统计信息"""
        if not self.snapshots:
            return {'error': 'No snapshots available'}
        
        current = self.snapshots[-1]
        
        # 计算趋势（最近10个快照）
        recent_snapshots = self.snapshots[-10:]
        if len(recent_snapshots) > 1:
            memory_trend = recent_snapshots[-1].rss_mb - recent_snapshots[0].rss_mb
            percent_trend = recent_snapshots[-1].percent - recent_snapshots[0].percent
        else:
            memory_trend = 0
            percent_trend = 0
        
        # 获取内存热点
        top_stats = self.get_memory_top_stats()
        
        return {
            'current': {
                'rss_mb': current.rss_mb,
                'vms_mb': current.vms_mb,
                'percent': current.percent,
                'available_mb': current.available_mb,
                'heap_size_mb': current.heap_size_mb,
                'thread_count': current.thread_count,
                'fd_count': current.fd_count
            },
            'trends': {
                'memory_trend_mb': memory_trend,
                'percent_trend': percent_trend,
                'snapshots_count': len(self.snapshots)
            },
            'alerts': {
                'warning_count': len([a for a in self.alerts if a.level == 'warning']),
                'critical_count': len([a for a in self.alerts if a.level == 'critical']),
                'recent_alerts': [
                    {
                        'level': a.level,
                        'message': a.message,
                        'timestamp': a.timestamp.isoformat()
                    }
                    for a in self.alerts[-5:]
                ]
            },
            'gc_stats': current.gc_stats,
            'top_memory_usage': top_stats
        }
    
    def get_memory_top_stats(self) -> List[Dict[str, Any]]:
        """获取内存热点统计"""
        try:
            if not tracemalloc.is_tracing():
                return []
            
            # 获取当前内存快照
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')
            
            # 返回前10个内存消耗最大的位置
            return [
                {
                    'filename': stat.traceback.format()[-1].split(',')[0].strip(),
                    'lineno': stat.traceback.format()[-1].split(',')[1].strip(),
                    'size_mb': stat.size / 1024 / 1024,
                    'count': stat.count
                }
                for stat in top_stats[:10]
            ]
            
        except Exception as e:
            logger.error(f"Failed to get memory top stats: {str(e)}")
            return []
    
    @contextmanager
    def memory_profile(self, operation_name: str):
        """内存使用分析上下文管理器"""
        start_snapshot = self.get_current_snapshot()
        start_time = time.time()
        
        try:
            yield
        finally:
            end_snapshot = self.get_current_snapshot()
            end_time = time.time()
            
            duration = end_time - start_time
            memory_diff = end_snapshot.rss_mb - start_snapshot.rss_mb
            
            logger.info(
                f"Memory profile for '{operation_name}': "
                f"Duration={duration:.2f}s, "
                f"Memory delta={memory_diff:.2f}MB, "
                f"Peak RSS={max(start_snapshot.rss_mb, end_snapshot.rss_mb):.2f}MB"
            )
    
    def set_memory_limits(self, max_memory_mb: int):
        """设置进程内存限制"""
        try:
            # 设置虚拟内存限制
            max_memory_bytes = max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))
            logger.info(f"Set memory limit to {max_memory_mb}MB")
        except (OSError, ValueError) as e:
            logger.warning(f"Failed to set memory limit: {str(e)}")
    
    def cleanup_resources(self):
        """清理资源"""
        try:
            # 强制垃圾回收
            self.force_garbage_collection()
            
            # 清理快照历史（保留最新的100个）
            if len(self.snapshots) > 100:
                self.snapshots = self.snapshots[-100:]
            
            # 清理告警历史
            self._cleanup_old_alerts()
            
            logger.info("Resource cleanup completed")
            
        except Exception as e:
            logger.error(f"Failed to cleanup resources: {str(e)}")


# 全局内存监控实例
memory_monitor = MemoryMonitor()


def get_memory_monitor() -> MemoryMonitor:
    """获取全局内存监控实例"""
    return memory_monitor


def start_memory_monitoring():
    """启动内存监控"""
    memory_monitor.start_monitoring()


def stop_memory_monitoring():
    """停止内存监控"""
    memory_monitor.stop_monitoring()


def memory_profile(operation_name: str):
    """内存分析装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with memory_monitor.memory_profile(operation_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# 内存优化工具函数
def clear_cache_if_needed(cache_obj, threshold_mb: float = 100):
    """条件性清理缓存"""
    current_memory = memory_monitor.get_current_snapshot().rss_mb
    if current_memory > threshold_mb:
        if hasattr(cache_obj, 'clear'):
            cache_obj.clear()
            logger.info(f"Cache cleared due to high memory usage: {current_memory:.1f}MB")


def optimize_for_memory():
    """内存优化建议执行"""
    # 强制垃圾回收
    memory_monitor.force_garbage_collection()
    
    # 调整GC阈值
    gc.set_threshold(700, 10, 10)  # 更激进的GC策略
    
    # 清理导入的模块缓存
    import sys
    if hasattr(sys, '_clear_type_cache'):
        sys._clear_type_cache()
    
    logger.info("Memory optimization completed")