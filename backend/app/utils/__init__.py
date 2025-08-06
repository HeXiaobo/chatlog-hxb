"""
工具模块
"""

from .cache import (
    cached, 
    get_cached, 
    set_cached, 
    delete_cached, 
    clear_cache, 
    get_cache_stats,
    cache_key
)

__all__ = [
    'cached',
    'get_cached',
    'set_cached', 
    'delete_cached',
    'clear_cache',
    'get_cache_stats',
    'cache_key'
]