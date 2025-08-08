"""
高性能缓存系统
支持TTL、LRU淘汰、压缩和分层缓存
"""
import time
import json
import hashlib
import logging
from typing import Any, Dict, Optional, Callable, Union
from functools import wraps
from collections import OrderedDict
import threading
from dataclasses import dataclass
import gzip
import pickle

logger = logging.getLogger(__name__)


@dataclass
class CacheItem:
    """缓存项"""
    value: Any
    timestamp: float
    ttl: int
    access_count: int = 0
    compressed: bool = False
    size_bytes: int = 0


class LRUCache:
    """高性能LRU缓存实现"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = ttl
        self.cache: OrderedDict[str, CacheItem] = OrderedDict()
        self.lock = threading.RLock()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size_bytes': 0
        }
    
    def _calculate_size(self, value: Any) -> int:
        """估算对象大小"""
        try:
            if isinstance(value, (str, bytes)):
                return len(value.encode('utf-8') if isinstance(value, str) else value)
            elif isinstance(value, (int, float, bool)):
                return 8
            elif isinstance(value, (list, tuple, dict)):
                return len(json.dumps(value, default=str).encode('utf-8'))
            else:
                return len(pickle.dumps(value))
        except:
            return 100  # 默认估计值
    
    def _compress_if_needed(self, value: Any, size_bytes: int) -> tuple[Any, bool]:
        """如果值较大则压缩"""
        if size_bytes > 1024:  # 大于1KB时压缩
            try:
                if isinstance(value, str):
                    compressed = gzip.compress(value.encode('utf-8'))
                    return compressed, True
                else:
                    serialized = pickle.dumps(value)
                    compressed = gzip.compress(serialized)
                    return compressed, True
            except:
                pass
        return value, False
    
    def _decompress_if_needed(self, value: Any, compressed: bool) -> Any:
        """如果需要则解压缩"""
        if compressed:
            try:
                decompressed = gzip.decompress(value)
                try:
                    return decompressed.decode('utf-8')
                except:
                    return pickle.loads(decompressed)
            except:
                logger.warning("Failed to decompress cached value")
        return value
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            item = self.cache.get(key)
            
            if item is None:
                self.stats['misses'] += 1
                return None
            
            # 检查TTL
            if time.time() - item.timestamp > item.ttl:
                del self.cache[key]
                self.stats['size_bytes'] -= item.size_bytes
                self.stats['misses'] += 1
                return None
            
            # 更新访问统计
            item.access_count += 1
            self.stats['hits'] += 1
            
            # LRU: 移动到末尾
            self.cache.move_to_end(key)
            
            # 解压缩并返回值
            return self._decompress_if_needed(item.value, item.compressed)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        with self.lock:
            current_time = time.time()
            ttl = ttl or self.default_ttl
            
            # 计算大小和压缩
            size_bytes = self._calculate_size(value)
            compressed_value, is_compressed = self._compress_if_needed(value, size_bytes)
            
            # 如果压缩了，重新计算大小
            if is_compressed:
                size_bytes = len(compressed_value)
            
            # 创建缓存项
            cache_item = CacheItem(
                value=compressed_value,
                timestamp=current_time,
                ttl=ttl,
                compressed=is_compressed,
                size_bytes=size_bytes
            )
            
            # 如果key已存在，更新统计
            if key in self.cache:
                old_item = self.cache[key]
                self.stats['size_bytes'] -= old_item.size_bytes
            
            # 添加/更新缓存项
            self.cache[key] = cache_item
            self.stats['size_bytes'] += size_bytes
            
            # LRU: 移动到末尾
            self.cache.move_to_end(key)
            
            # 如果超过最大大小，清理最旧的项
            while len(self.cache) > self.max_size:
                oldest_key, oldest_item = self.cache.popitem(last=False)
                self.stats['size_bytes'] -= oldest_item.size_bytes
                self.stats['evictions'] += 1
    
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        with self.lock:
            if key in self.cache:
                item = self.cache.pop(key)
                self.stats['size_bytes'] -= item.size_bytes
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.stats = {
                'hits': 0,
                'misses': 0,
                'evictions': 0,
                'size_bytes': 0
            }
    
    def cleanup_expired(self) -> int:
        """清理过期项"""
        with self.lock:
            current_time = time.time()
            expired_keys = []
            
            for key, item in self.cache.items():
                if current_time - item.timestamp > item.ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                item = self.cache.pop(key)
                self.stats['size_bytes'] -= item.size_bytes
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'hit_rate': f"{hit_rate:.1f}%",
                'evictions': self.stats['evictions'],
                'size_bytes': self.stats['size_bytes'],
                'size_mb': f"{self.stats['size_bytes'] / 1024 / 1024:.2f}MB"
            }


class MultiLevelCache:
    """多级缓存系统"""
    
    def __init__(self):
        # L1缓存：高速小容量（最近访问的数据）
        self.l1_cache = LRUCache(max_size=100, ttl=300)  # 5分钟
        
        # L2缓存：中速中容量（常用数据）
        self.l2_cache = LRUCache(max_size=1000, ttl=1800)  # 30分钟
        
        # L3缓存：低速大容量（长期数据）
        self.l3_cache = LRUCache(max_size=5000, ttl=3600)  # 1小时
    
    def get(self, key: str) -> Optional[Any]:
        """多级缓存获取"""
        # L1缓存查找
        value = self.l1_cache.get(key)
        if value is not None:
            return value
        
        # L2缓存查找
        value = self.l2_cache.get(key)
        if value is not None:
            # 提升到L1缓存
            self.l1_cache.set(key, value, ttl=300)
            return value
        
        # L3缓存查找
        value = self.l3_cache.get(key)
        if value is not None:
            # 提升到L2缓存
            self.l2_cache.set(key, value, ttl=1800)
            return value
        
        return None
    
    def set(self, key: str, value: Any, level: int = 1) -> None:
        """设置缓存到指定级别"""
        if level == 1:
            self.l1_cache.set(key, value, ttl=300)
        elif level == 2:
            self.l2_cache.set(key, value, ttl=1800)
        else:
            self.l3_cache.set(key, value, ttl=3600)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取所有缓存级别的统计"""
        return {
            'l1_cache': self.l1_cache.get_stats(),
            'l2_cache': self.l2_cache.get_stats(),
            'l3_cache': self.l3_cache.get_stats()
        }


# 全局缓存实例
_global_cache = MultiLevelCache()


def get_cache_key(func_name: str, args: tuple, kwargs: dict, key_prefix: str = "") -> str:
    """生成缓存键"""
    # 创建参数的哈希值
    args_str = str(args) + str(sorted(kwargs.items()))
    args_hash = hashlib.md5(args_str.encode('utf-8')).hexdigest()[:12]
    
    return f"{key_prefix}{func_name}:{args_hash}"


def cached(ttl: int = 3600, key_prefix: str = "", level: int = 1, 
           condition: Optional[Callable] = None):
    """
    缓存装饰器
    
    Args:
        ttl: 缓存时间（秒）
        key_prefix: 缓存键前缀
        level: 缓存级别 (1=L1高速, 2=L2中速, 3=L3长期)
        condition: 缓存条件函数，返回True才缓存
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = get_cache_key(func.__name__, args, kwargs, key_prefix)
            
            # 尝试从缓存获取
            cached_result = _global_cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 检查缓存条件
            if condition is None or condition(result):
                _global_cache.set(cache_key, result, level=level)
                logger.debug(f"Cached result for {func.__name__}")
            
            return result
        
        return wrapper
    return decorator


def cache_clear(key_pattern: Optional[str] = None) -> int:
    """清理缓存"""
    if key_pattern is None:
        _global_cache.l1_cache.clear()
        _global_cache.l2_cache.clear()
        _global_cache.l3_cache.clear()
        return 0
    else:
        # TODO: 实现模式匹配清理
        return 0


def cache_stats() -> Dict[str, Any]:
    """获取缓存统计信息"""
    stats = _global_cache.get_stats()
    
    # 计算总体统计
    total_hits = sum(cache['hits'] for cache in stats.values())
    total_misses = sum(cache['misses'] for cache in stats.values())
    total_requests = total_hits + total_misses
    overall_hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0
    
    return {
        'overall_hit_rate': f"{overall_hit_rate:.1f}%",
        'total_requests': total_requests,
        'cache_levels': stats,
        'performance_summary': {
            'l1_efficiency': f"{stats['l1_cache']['hit_rate']}",
            'l2_efficiency': f"{stats['l2_cache']['hit_rate']}",
            'l3_efficiency': f"{stats['l3_cache']['hit_rate']}",
            'memory_usage': f"{sum(float(cache['size_mb'][:-2]) for cache in stats.values()):.2f}MB"
        }
    }


# 定期清理过期缓存
def cleanup_expired_cache() -> Dict[str, int]:
    """清理所有级别的过期缓存"""
    return {
        'l1_expired': _global_cache.l1_cache.cleanup_expired(),
        'l2_expired': _global_cache.l2_cache.cleanup_expired(),
        'l3_expired': _global_cache.l3_cache.cleanup_expired()
    }


# 为特定场景优化的缓存装饰器
def search_cache(ttl: int = 300):
    """搜索结果缓存装饰器（L2级别，5分钟）"""
    return cached(ttl=ttl, key_prefix="search:", level=2)


def ai_response_cache(ttl: int = 3600):
    """AI响应缓存装饰器（L3级别，1小时）"""
    return cached(ttl=ttl, key_prefix="ai:", level=3, 
                  condition=lambda result: result is not None)


def file_process_cache(ttl: int = 1800):
    """文件处理结果缓存装饰器（L2级别，30分钟）"""
    return cached(ttl=ttl, key_prefix="file:", level=2)


def category_cache(ttl: int = 7200):
    """分类数据缓存装饰器（L3级别，2小时）"""
    return cached(ttl=ttl, key_prefix="category:", level=3)