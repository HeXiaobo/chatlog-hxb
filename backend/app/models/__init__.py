"""
数据库模型模块
"""
from .qa import QAPair
from .category import Category
from .upload import UploadHistory

__all__ = ['QAPair', 'Category', 'UploadHistory']