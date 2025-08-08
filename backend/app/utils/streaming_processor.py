"""
流式文件处理工具 - 处理大文件时避免内存溢出
"""
import json
import logging
import mmap
import os
import gc
from typing import Iterator, Dict, Any, List, Optional, Callable, TextIO
from pathlib import Path
from dataclasses import dataclass
import tempfile
import shutil
import ijson
from contextlib import contextmanager

from app.utils.memory_monitor import memory_monitor

logger = logging.getLogger(__name__)


@dataclass
class StreamingConfig:
    """流式处理配置"""
    chunk_size: int = 64 * 1024  # 64KB
    memory_limit_mb: int = 100   # 内存限制
    temp_dir: Optional[str] = None
    enable_compression: bool = True
    gc_frequency: int = 1000     # 每处理多少个对象执行一次GC


class StreamingJSONProcessor:
    """流式JSON处理器"""
    
    def __init__(self, config: StreamingConfig = None):
        self.config = config or StreamingConfig()
        self.processed_count = 0
        self.temp_files: List[Path] = []
    
    @contextmanager
    def memory_safe_processing(self, operation_name: str):
        """内存安全处理上下文"""
        with memory_monitor.memory_profile(operation_name):
            try:
                yield
            finally:
                # 定期垃圾回收
                if self.processed_count % self.config.gc_frequency == 0:
                    memory_monitor.force_garbage_collection()
    
    def stream_parse_large_json(self, file_path: Path) -> Iterator[Dict[str, Any]]:
        """
        流式解析大型JSON文件
        
        Args:
            file_path: JSON文件路径
        
        Yields:
            Dict[str, Any]: JSON对象
        """
        try:
            file_size = file_path.stat().st_size
            logger.info(f"Starting streaming parse of {file_path} ({file_size / 1024 / 1024:.1f}MB)")
            
            with open(file_path, 'rb') as file:
                # 尝试使用ijson进行流式解析
                try:
                    # 假设JSON是一个对象数组或包含messages数组
                    parser = ijson.parse(file)
                    
                    current_object = {}
                    object_stack = []
                    key_stack = []
                    
                    for prefix, event, value in parser:
                        if event == 'start_map':
                            new_obj = {}
                            if object_stack:
                                if isinstance(object_stack[-1], list):
                                    object_stack[-1].append(new_obj)
                                else:
                                    object_stack[-1][key_stack[-1]] = new_obj
                            object_stack.append(new_obj)
                            
                        elif event == 'end_map':
                            if object_stack:
                                completed_obj = object_stack.pop()
                                if not object_stack:  # 根对象完成
                                    self.processed_count += 1
                                    yield completed_obj
                                    
                                    # 内存检查
                                    if self.processed_count % 100 == 0:
                                        current_memory = memory_monitor.get_current_snapshot().rss_mb
                                        if current_memory > self.config.memory_limit_mb:
                                            logger.warning(f"Memory usage high: {current_memory:.1f}MB")
                                            gc.collect()
                        
                        elif event == 'start_array':
                            new_array = []
                            if object_stack and key_stack:
                                object_stack[-1][key_stack[-1]] = new_array
                            object_stack.append(new_array)
                            
                        elif event == 'end_array':
                            if object_stack:
                                object_stack.pop()
                        
                        elif event == 'map_key':
                            if len(key_stack) > len(object_stack):
                                key_stack.pop()
                            key_stack.append(value)
                        
                        elif event in ['string', 'number', 'boolean', 'null']:
                            if object_stack:
                                if isinstance(object_stack[-1], list):
                                    object_stack[-1].append(value)
                                elif key_stack:
                                    object_stack[-1][key_stack[-1]] = value
                
                except Exception as ijson_error:
                    logger.warning(f"ijson failed: {str(ijson_error)}, falling back to chunk processing")
                    # 回退到分块处理
                    file.seek(0)
                    yield from self._chunk_parse_fallback(file)
                    
        except Exception as e:
            logger.error(f"Failed to stream parse JSON: {str(e)}")
            raise
    
    def _chunk_parse_fallback(self, file: TextIO) -> Iterator[Dict[str, Any]]:
        """分块解析回退方案"""
        buffer = ""
        brace_count = 0
        in_string = False
        escape_next = False
        
        while True:
            chunk = file.read(self.config.chunk_size)
            if not chunk:
                break
                
            buffer += chunk.decode('utf-8', errors='ignore') if isinstance(chunk, bytes) else chunk
            
            # 查找完整的JSON对象
            start_pos = 0
            i = 0
            
            while i < len(buffer):
                char = buffer[i]
                
                if escape_next:
                    escape_next = False
                elif char == '\\' and in_string:
                    escape_next = True
                elif char == '"':
                    in_string = not in_string
                elif not in_string:
                    if char == '{':
                        if brace_count == 0:
                            start_pos = i
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            # 找到完整的JSON对象
                            json_str = buffer[start_pos:i + 1]
                            try:
                                obj = json.loads(json_str)
                                self.processed_count += 1
                                yield obj
                            except json.JSONDecodeError as e:
                                logger.warning(f"Invalid JSON object: {str(e)}")
                            
                            # 更新缓冲区
                            buffer = buffer[i + 1:]
                            i = -1  # 重置索引
                
                i += 1
    
    def process_in_batches(self, 
                          items: Iterator[Dict[str, Any]], 
                          batch_size: int = 1000,
                          processor: Callable[[List[Dict[str, Any]]], Any] = None) -> Iterator[Any]:
        """
        批量处理流式数据
        
        Args:
            items: 数据流
            batch_size: 批量大小
            processor: 批处理函数
        
        Yields:
            处理结果
        """
        batch = []
        
        with self.memory_safe_processing("batch_processing"):
            for item in items:
                batch.append(item)
                
                if len(batch) >= batch_size:
                    if processor:
                        try:
                            result = processor(batch)
                            if result is not None:
                                yield result
                        except Exception as e:
                            logger.error(f"Batch processing error: {str(e)}")
                    else:
                        yield batch
                    
                    batch = []
                    self.processed_count += len(batch)
                    
                    # 内存检查
                    current_memory = memory_monitor.get_current_snapshot().rss_mb
                    if current_memory > self.config.memory_limit_mb:
                        logger.warning(f"High memory usage: {current_memory:.1f}MB, running GC")
                        gc.collect()
            
            # 处理剩余数据
            if batch:
                if processor:
                    try:
                        result = processor(batch)
                        if result is not None:
                            yield result
                    except Exception as e:
                        logger.error(f"Final batch processing error: {str(e)}")
                else:
                    yield batch
    
    def create_temp_file(self, suffix: str = '.json') -> Path:
        """创建临时文件"""
        temp_dir = Path(self.config.temp_dir) if self.config.temp_dir else Path(tempfile.gettempdir())
        temp_file = temp_dir / f"streaming_temp_{os.getpid()}_{len(self.temp_files)}{suffix}"
        self.temp_files.append(temp_file)
        return temp_file
    
    def split_large_file(self, file_path: Path, max_size_mb: int = 50) -> List[Path]:
        """
        拆分大文件为小文件
        
        Args:
            file_path: 原文件路径
            max_size_mb: 每个文件的最大大小（MB）
        
        Returns:
            List[Path]: 拆分后的文件列表
        """
        file_size = file_path.stat().st_size
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if file_size <= max_size_bytes:
            return [file_path]
        
        logger.info(f"Splitting large file {file_path} ({file_size / 1024 / 1024:.1f}MB)")
        
        split_files = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as source:
                # 尝试解析为JSON数组
                data = json.load(source)
                
                if isinstance(data, dict) and 'messages' in data:
                    messages = data['messages']
                    chunk_size = max_size_bytes // (len(json.dumps(messages[0]).encode()) + 100)
                    
                    for i in range(0, len(messages), chunk_size):
                        chunk_data = {
                            **{k: v for k, v in data.items() if k != 'messages'},
                            'messages': messages[i:i + chunk_size]
                        }
                        
                        temp_file = self.create_temp_file()
                        with open(temp_file, 'w', encoding='utf-8') as f:
                            json.dump(chunk_data, f, ensure_ascii=False)
                        
                        split_files.append(temp_file)
                        
                elif isinstance(data, list):
                    chunk_size = max_size_bytes // (len(json.dumps(data[0]).encode()) + 100)
                    
                    for i in range(0, len(data), chunk_size):
                        chunk_data = data[i:i + chunk_size]
                        
                        temp_file = self.create_temp_file()
                        with open(temp_file, 'w', encoding='utf-8') as f:
                            json.dump(chunk_data, f, ensure_ascii=False)
                        
                        split_files.append(temp_file)
                
                logger.info(f"Split into {len(split_files)} files")
                return split_files
                
        except Exception as e:
            logger.error(f"Failed to split file: {str(e)}")
            # 清理已创建的临时文件
            for temp_file in split_files:
                try:
                    temp_file.unlink()
                except:
                    pass
            return [file_path]
    
    def memory_mapped_read(self, file_path: Path) -> Iterator[str]:
        """
        使用内存映射读取大文件
        
        Args:
            file_path: 文件路径
        
        Yields:
            str: 文件行
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as mapped_file:
                    for line in iter(mapped_file.readline, b""):
                        yield line.decode('utf-8', errors='ignore')
                        
        except Exception as e:
            logger.error(f"Memory mapped read failed: {str(e)}")
            # 回退到普通读取
            with open(file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    yield line
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    logger.debug(f"Cleaned temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to clean temp file {temp_file}: {str(e)}")
        
        self.temp_files.clear()
    
    def __del__(self):
        """析构函数，确保清理临时文件"""
        self.cleanup_temp_files()


class StreamingCSVProcessor:
    """流式CSV处理器"""
    
    def __init__(self, config: StreamingConfig = None):
        self.config = config or StreamingConfig()
        self.processed_count = 0
    
    def stream_csv_to_json(self, csv_path: Path, output_path: Path, 
                          chunk_size: int = 10000) -> int:
        """
        流式将CSV转换为JSON
        
        Args:
            csv_path: CSV文件路径
            output_path: 输出JSON文件路径
            chunk_size: 处理块大小
        
        Returns:
            int: 处理的记录数
        """
        import csv
        
        processed = 0
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as csv_file:
                reader = csv.DictReader(csv_file)
                
                with open(output_path, 'w', encoding='utf-8') as json_file:
                    json_file.write('[')
                    
                    first_record = True
                    chunk = []
                    
                    for row in reader:
                        chunk.append(row)
                        
                        if len(chunk) >= chunk_size:
                            if not first_record:
                                json_file.write(',')
                            
                            json_data = json.dumps(chunk, ensure_ascii=False)
                            json_file.write(json_data[1:-1])  # 移除数组括号
                            
                            processed += len(chunk)
                            chunk = []
                            first_record = False
                            
                            # 内存检查
                            current_memory = memory_monitor.get_current_snapshot().rss_mb
                            if current_memory > self.config.memory_limit_mb:
                                gc.collect()
                    
                    # 处理剩余记录
                    if chunk:
                        if not first_record:
                            json_file.write(',')
                        
                        json_data = json.dumps(chunk, ensure_ascii=False)
                        json_file.write(json_data[1:-1])
                        processed += len(chunk)
                    
                    json_file.write(']')
            
            logger.info(f"Converted {processed} CSV records to JSON")
            return processed
            
        except Exception as e:
            logger.error(f"CSV to JSON conversion failed: {str(e)}")
            raise


# 便捷函数
def create_streaming_processor(memory_limit_mb: int = 100) -> StreamingJSONProcessor:
    """创建流式处理器"""
    config = StreamingConfig(memory_limit_mb=memory_limit_mb)
    return StreamingJSONProcessor(config)


def process_large_json_file(file_path: Path, 
                           processor_func: Callable[[Dict[str, Any]], Any],
                           batch_size: int = 1000) -> List[Any]:
    """
    处理大型JSON文件的便捷函数
    
    Args:
        file_path: JSON文件路径
        processor_func: 处理函数
        batch_size: 批处理大小
    
    Returns:
        List[Any]: 处理结果列表
    """
    streaming_processor = create_streaming_processor()
    results = []
    
    try:
        # 流式解析JSON
        json_stream = streaming_processor.stream_parse_large_json(file_path)
        
        # 批量处理
        def batch_processor(batch):
            return [processor_func(item) for item in batch if item]
        
        batch_results = streaming_processor.process_in_batches(
            json_stream, batch_size, batch_processor
        )
        
        for batch_result in batch_results:
            if batch_result:
                results.extend(batch_result)
        
        return results
        
    finally:
        streaming_processor.cleanup_temp_files()


@contextmanager
def memory_limited_operation(memory_limit_mb: int = 200):
    """内存限制操作上下文管理器"""
    original_threshold = gc.get_threshold()
    
    try:
        # 设置更积极的GC策略
        gc.set_threshold(700, 10, 10)
        
        # 监控内存使用
        with memory_monitor.memory_profile("memory_limited_operation"):
            yield
            
    finally:
        # 恢复原始GC设置
        gc.set_threshold(*original_threshold)
        
        # 强制垃圾回收
        gc.collect()