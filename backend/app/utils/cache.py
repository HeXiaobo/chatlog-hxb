"""
缓存工具模块
"""
import time
import json
import hashlib
from functools import wraps
from typing import Any, Dict, Optional, Callable, Union
import logging

logger = logging.getLogger(__name__)


class SimpleCache:
    """简单的内存缓存实现"""
    
    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        """
        初始化缓存
        
        Args:
            default_ttl: 默认缓存时间（秒）
            max_size: 最大缓存条目数
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.max_size = max_size
        
    def _cleanup_expired(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = [
            key for key, value in self.cache.items()
            if value['expires_at'] < current_time
        ]
        
        for key in expired_keys:
            del self.cache[key]
    
    def _evict_if_needed(self):
        """如果需要，执行缓存淘汰（简单LRU）"""
        if len(self.cache) >= self.max_size:
            # 移除最旧的缓存项
            oldest_key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k]['accessed_at']
            )
            del self.cache[oldest_key]
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        self._cleanup_expired()
        
        if key in self.cache:
            item = self.cache[key]
            if item['expires_at'] > time.time():
                item['accessed_at'] = time.time()
                return item['value']
            else:
                del self.cache[key]
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        self._cleanup_expired()
        self._evict_if_needed()
        
        ttl = ttl or self.default_ttl
        current_time = time.time()
        
        self.cache[key] = {
            'value': value,
            'expires_at': current_time + ttl,
            'accessed_at': current_time,
            'created_at': current_time
        }
    
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        self.cache.clear()
    
    def size(self) -> int:
        """获取当前缓存大小"""
        self._cleanup_expired()
        return len(self.cache)
    
    def keys(self) -> list:
        """获取所有缓存键"""
        self._cleanup_expired()
        return list(self.cache.keys())


# 全局缓存实例
_global_cache = SimpleCache()


def cache_key(*args, **kwargs) -> str:
    """生成缓存键"""
    key_data = {
        'args': args,
        'kwargs': sorted(kwargs.items())
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached(ttl: int = 300, key_prefix: str = ''):
    """
    缓存装饰器
    
    Args:
        ttl: 缓存时间（秒）
        key_prefix: 缓存键前缀
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            func_key = f"{key_prefix}{func.__module__}.{func.__name__}"
            cache_key_str = f"{func_key}:{cache_key(*args, **kwargs)}"
            
            # 尝试从缓存获取
            cached_result = _global_cache.get(cache_key_str)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # 执行函数并缓存结果
            try:
                result = func(*args, **kwargs)
                _global_cache.set(cache_key_str, result, ttl)
                logger.debug(f"Cache miss for {func.__name__}, result cached")
                return result
            except Exception as e:
                logger.error(f"Function {func.__name__} failed: {str(e)}")
                raise
        
        return wrapper
    return decorator


class CacheStats:
    """缓存统计"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
    
    def hit(self):
        self.hits += 1
    
    def miss(self):
        self.misses += 1
    
    def set_op(self):
        self.sets += 1
    
    def delete_op(self):
        self.deletes += 1
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Union[int, float]]:
        return {
            'hits': self.hits,
            'misses': self.misses,
            'sets': self.sets,
            'deletes': self.deletes,
            'hit_rate': self.hit_rate,
            'total_operations': self.hits + self.misses
        }


# 缓存统计实例
cache_stats = CacheStats()


def get_cache_stats() -> Dict[str, Any]:
    """获取缓存统计信息"""
    return {
        'stats': cache_stats.to_dict(),
        'cache_size': _global_cache.size(),
        'max_size': _global_cache.max_size,
        'keys_sample': _global_cache.keys()[:10]  # 显示前10个缓存键作为示例
    }


def clear_cache() -> bool:
    """清空全局缓存"""
    try:
        _global_cache.clear()
        logger.info("Global cache cleared")
        return True
    except Exception as e:
        logger.error(f"Failed to clear cache: {str(e)}")
        return False


# 导出缓存操作函数
def get_cached(key: str) -> Optional[Any]:
    """获取缓存值"""
    result = _global_cache.get(key)
    if result is not None:
        cache_stats.hit()
    else:
        cache_stats.miss()
    return result


def set_cached(key: str, value: Any, ttl: Optional[int] = None) -> None:
    """设置缓存值"""
    _global_cache.set(key, value, ttl)
    cache_stats.set_op()


def delete_cached(key: str) -> bool:
    """删除缓存值"""
    result = _global_cache.delete(key)
    if result:
        cache_stats.delete_op()
    return result