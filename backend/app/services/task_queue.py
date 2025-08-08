"""
后台任务队列服务 - 处理异步文件上传和长时间任务
"""
import asyncio
import logging
import json
import time
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import threading
from queue import Queue, PriorityQueue
import uuid

from app import db
from app.models import UploadHistory
from app.services.async_file_processor import AsyncFileProcessor
from app.utils.cache import cached, MultiLevelCache

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    URGENT = 0


@dataclass
class TaskResult:
    """任务执行结果"""
    task_id: str
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_time: Optional[float] = None
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['status'] = self.status.value
        if self.start_time:
            data['start_time'] = self.start_time.isoformat()
        if self.end_time:
            data['end_time'] = self.end_time.isoformat()
        return data


@dataclass
class BackgroundTask:
    """后台任务定义"""
    task_id: str
    task_type: str
    priority: TaskPriority
    func: Callable
    args: tuple
    kwargs: dict
    max_retries: int = 3
    timeout: int = 300  # 5分钟超时
    created_at: datetime = None
    scheduled_for: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def __lt__(self, other):
        # 优先级队列排序：优先级 > 创建时间
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


class TaskQueue:
    """异步任务队列管理器"""
    
    def __init__(self, max_workers: int = 5, max_queue_size: int = 1000):
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        
        # 任务队列
        self.pending_queue = PriorityQueue(maxsize=max_queue_size)
        self.running_tasks: Dict[str, BackgroundTask] = {}
        self.task_results: Dict[str, TaskResult] = {}
        
        # 线程池和事件循环
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.loop = None
        self.worker_thread = None
        self.is_running = False
        
        # 统计信息
        self.stats = {
            'tasks_submitted': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'tasks_retried': 0,
            'total_execution_time': 0.0
        }
        
        # 缓存系统
        self.cache = MultiLevelCache()
        
        # 初始化队列
        self._init_worker()
    
    def _init_worker(self):
        """初始化工作线程"""
        try:
            self.worker_thread = threading.Thread(target=self._run_worker, daemon=True)
            self.is_running = True
            self.worker_thread.start()
            logger.info(f"Task queue initialized with {self.max_workers} workers")
        except Exception as e:
            logger.error(f"Failed to initialize task queue: {str(e)}")
            raise
    
    def _run_worker(self):
        """工作线程主循环"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self._worker_main())
        except Exception as e:
            logger.error(f"Worker thread error: {str(e)}")
        finally:
            self.loop.close()
    
    async def _worker_main(self):
        """异步工作主循环"""
        while self.is_running:
            try:
                # 处理待执行任务
                if not self.pending_queue.empty() and len(self.running_tasks) < self.max_workers:
                    task = self.pending_queue.get()
                    
                    # 检查调度时间
                    if task.scheduled_for and datetime.utcnow() < task.scheduled_for:
                        # 重新放入队列等待
                        self.pending_queue.put(task)
                        await asyncio.sleep(1)
                        continue
                    
                    # 执行任务
                    await self._execute_task(task)
                
                # 清理过期的任务结果
                await self._cleanup_expired_results()
                
                # 短暂休眠避免CPU占用过高
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Worker main loop error: {str(e)}")
                await asyncio.sleep(1)
    
    async def _execute_task(self, task: BackgroundTask):
        """执行单个任务"""
        task_result = TaskResult(
            task_id=task.task_id,
            status=TaskStatus.RUNNING,
            start_time=datetime.utcnow()
        )
        
        # 将任务标记为运行中
        self.running_tasks[task.task_id] = task
        self.task_results[task.task_id] = task_result
        
        try:
            logger.info(f"Starting task {task.task_id} ({task.task_type})")
            
            # 执行任务函数
            if asyncio.iscoroutinefunction(task.func):
                # 异步函数
                result = await asyncio.wait_for(
                    task.func(*task.args, **task.kwargs),
                    timeout=task.timeout
                )
            else:
                # 同步函数，在线程池中执行
                result = await asyncio.wait_for(
                    self.loop.run_in_executor(
                        self.executor,
                        lambda: task.func(*task.args, **task.kwargs)
                    ),
                    timeout=task.timeout
                )
            
            # 任务执行成功
            task_result.status = TaskStatus.COMPLETED
            task_result.result = result
            task_result.end_time = datetime.utcnow()
            task_result.execution_time = (task_result.end_time - task_result.start_time).total_seconds()
            
            # 更新统计信息
            self.stats['tasks_completed'] += 1
            self.stats['total_execution_time'] += task_result.execution_time
            
            logger.info(f"Task {task.task_id} completed in {task_result.execution_time:.2f}s")
            
        except asyncio.TimeoutError:
            # 任务超时
            task_result.status = TaskStatus.FAILED
            task_result.error = f"Task timeout after {task.timeout} seconds"
            task_result.end_time = datetime.utcnow()
            
            self.stats['tasks_failed'] += 1
            logger.error(f"Task {task.task_id} timeout")
            
            # 尝试重试
            await self._retry_task(task)
            
        except Exception as e:
            # 任务执行异常
            task_result.status = TaskStatus.FAILED
            task_result.error = str(e)
            task_result.end_time = datetime.utcnow()
            
            self.stats['tasks_failed'] += 1
            logger.error(f"Task {task.task_id} failed: {str(e)}")
            
            # 尝试重试
            await self._retry_task(task)
            
        finally:
            # 从运行队列中移除
            self.running_tasks.pop(task.task_id, None)
    
    async def _retry_task(self, task: BackgroundTask):
        """重试失败的任务"""
        if task.max_retries > 0:
            task.max_retries -= 1
            task_result = self.task_results[task.task_id]
            task_result.retry_count += 1
            task_result.status = TaskStatus.RETRYING
            
            # 延迟重试
            retry_delay = min(2 ** task_result.retry_count, 60)  # 指数退避，最大60秒
            task.scheduled_for = datetime.utcnow() + timedelta(seconds=retry_delay)
            
            # 重新加入队列
            self.pending_queue.put(task)
            self.stats['tasks_retried'] += 1
            
            logger.info(f"Task {task.task_id} scheduled for retry in {retry_delay}s")
    
    async def _cleanup_expired_results(self):
        """清理过期的任务结果"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=1)  # 保留1小时
            expired_tasks = [
                task_id for task_id, result in self.task_results.items()
                if result.end_time and result.end_time < cutoff_time
            ]
            
            for task_id in expired_tasks:
                self.task_results.pop(task_id, None)
                
            if expired_tasks:
                logger.info(f"Cleaned up {len(expired_tasks)} expired task results")
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired results: {str(e)}")
    
    def submit_task(self, task_type: str, func: Callable, *args, 
                   priority: TaskPriority = TaskPriority.NORMAL,
                   max_retries: int = 3, timeout: int = 300, 
                   scheduled_for: Optional[datetime] = None, **kwargs) -> str:
        """
        提交新任务到队列
        
        Args:
            task_type: 任务类型标识
            func: 要执行的函数
            *args: 函数参数
            priority: 任务优先级
            max_retries: 最大重试次数
            timeout: 超时时间（秒）
            scheduled_for: 调度执行时间
            **kwargs: 函数关键字参数
        
        Returns:
            str: 任务ID
        """
        try:
            if self.pending_queue.full():
                raise Exception("Task queue is full")
            
            task_id = f"{task_type}_{uuid.uuid4().hex[:8]}"
            task = BackgroundTask(
                task_id=task_id,
                task_type=task_type,
                priority=priority,
                func=func,
                args=args,
                kwargs=kwargs,
                max_retries=max_retries,
                timeout=timeout,
                scheduled_for=scheduled_for
            )
            
            self.pending_queue.put(task)
            self.stats['tasks_submitted'] += 1
            
            # 创建初始任务结果
            self.task_results[task_id] = TaskResult(
                task_id=task_id,
                status=TaskStatus.PENDING
            )
            
            logger.info(f"Task {task_id} ({task_type}) submitted to queue")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to submit task: {str(e)}")
            raise
    
    def get_task_status(self, task_id: str) -> Optional[TaskResult]:
        """获取任务状态"""
        return self.task_results.get(task_id)
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        return {
            'queue_size': self.pending_queue.qsize(),
            'running_tasks': len(self.running_tasks),
            'total_results': len(self.task_results),
            'worker_stats': self.stats.copy(),
            'avg_execution_time': (
                self.stats['total_execution_time'] / max(self.stats['tasks_completed'], 1)
            )
        }
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            # 检查是否在运行中
            if task_id in self.running_tasks:
                logger.warning(f"Cannot cancel running task {task_id}")
                return False
            
            # 标记为取消
            if task_id in self.task_results:
                self.task_results[task_id].status = TaskStatus.CANCELLED
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {str(e)}")
            return False
    
    def shutdown(self, timeout: int = 30):
        """关闭任务队列"""
        try:
            logger.info("Shutting down task queue...")
            self.is_running = False
            
            if self.worker_thread and self.worker_thread.is_alive():
                self.worker_thread.join(timeout=timeout)
            
            if self.executor:
                self.executor.shutdown(wait=True, timeout=timeout)
            
            logger.info("Task queue shut down successfully")
            
        except Exception as e:
            logger.error(f"Error during task queue shutdown: {str(e)}")


class FileProcessingService:
    """文件处理服务 - 使用任务队列处理文件上传"""
    
    def __init__(self, task_queue: TaskQueue):
        self.task_queue = task_queue
        self.async_processor = AsyncFileProcessor()
    
    def process_file_async(self, file_path: Path, original_filename: str, 
                          priority: TaskPriority = TaskPriority.NORMAL) -> str:
        """异步处理文件"""
        return self.task_queue.submit_task(
            task_type="file_processing",
            func=self._process_file_task,
            file_path=file_path,
            original_filename=original_filename,
            priority=priority,
            timeout=600  # 10分钟超时
        )
    
    async def _process_file_task(self, file_path: Path, original_filename: str) -> Dict[str, Any]:
        """文件处理任务实现"""
        try:
            result = await self.async_processor.process_file_async(file_path, original_filename)
            return result.__dict__ if hasattr(result, '__dict__') else result
        except Exception as e:
            logger.error(f"File processing task failed: {str(e)}")
            raise
    
    def get_processing_status(self, task_id: str) -> Dict[str, Any]:
        """获取处理状态"""
        task_result = self.task_queue.get_task_status(task_id)
        if not task_result:
            return {'error': 'Task not found'}
        
        return task_result.to_dict()


# 全局任务队列实例
task_queue = TaskQueue(max_workers=3)
file_processing_service = FileProcessingService(task_queue)


def get_task_queue() -> TaskQueue:
    """获取全局任务队列实例"""
    return task_queue


def get_file_processing_service() -> FileProcessingService:
    """获取文件处理服务实例"""
    return file_processing_service