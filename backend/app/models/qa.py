"""
问答对模型
"""
from app import db
from .base import BaseModel
from sqlalchemy import Index, func


class QAPair(BaseModel):
    """问答对模型"""
    __tablename__ = 'qa_pairs'
    
    # 问答内容
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    
    # 分类关联
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    category = db.relationship('Category', back_populates='qa_pairs')
    
    # 用户信息
    asker = db.Column(db.String(100))  # 提问者
    advisor = db.Column(db.String(100))  # 回答者
    
    # 质量指标
    confidence = db.Column(db.Float, default=0.8)  # 置信度 0.0-1.0
    
    # 源数据信息
    source_file = db.Column(db.String(255))  # 来源文件
    original_context = db.Column(db.Text)  # 原始上下文
    
    # 索引优化
    __table_args__ = (
        Index('idx_qa_question', 'question'),
        Index('idx_qa_category', 'category_id'),
        Index('idx_qa_advisor', 'advisor'),
        Index('idx_qa_created', 'created_at'),
        Index('idx_qa_confidence', 'confidence'),
        Index('idx_qa_composite', 'category_id', 'advisor', 'created_at'),
    )
    
    def to_dict(self, include_relationships=True, highlight_query=None):
        """
        转换为字典
        
        Args:
            include_relationships: 是否包含关联关系
            highlight_query: 搜索关键词，用于高亮显示
        
        Returns:
            dict: 字典表示
        """
        data = super().to_dict(include_relationships=False)
        
        # 包含分类信息
        if include_relationships and self.category:
            data['category'] = self.category.to_dict()
        
        # 高亮显示搜索关键词
        if highlight_query:
            data['question'] = self._highlight_text(data['question'], highlight_query)
            data['answer'] = self._highlight_text(data['answer'], highlight_query)
        
        return data
    
    def _highlight_text(self, text, query):
        """
        在文本中高亮显示查询关键词
        
        Args:
            text: 原始文本
            query: 查询关键词
        
        Returns:
            str: 高亮后的文本
        """
        if not text or not query:
            return text
        
        # 简单的关键词高亮（实际项目中可以使用更复杂的算法）
        import re
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        return pattern.sub(f'<mark>{query}</mark>', text)
    
    @classmethod
    def search(cls, query, category_ids=None, advisor=None, start_date=None, end_date=None, page=1, per_page=20):
        """
        搜索问答对
        
        Args:
            query: 搜索关键词
            category_ids: 分类ID列表
            advisor: 回答者
            start_date: 开始日期
            end_date: 结束日期
            page: 页码
            per_page: 每页数量
        
        Returns:
            Pagination: 分页结果
        """
        # 基础查询
        base_query = cls.query
        
        # 全文搜索（简单实现，生产环境建议使用FTS5）
        if query:
            search_filter = db.or_(
                cls.question.contains(query),
                cls.answer.contains(query)
            )
            base_query = base_query.filter(search_filter)
        
        # 分类筛选
        if category_ids:
            base_query = base_query.filter(cls.category_id.in_(category_ids))
        
        # 回答者筛选
        if advisor:
            base_query = base_query.filter(cls.advisor == advisor)
        
        # 日期范围筛选
        if start_date:
            base_query = base_query.filter(cls.created_at >= start_date)
        if end_date:
            base_query = base_query.filter(cls.created_at <= end_date)
        
        # 按相关性和时间排序
        if query:
            # 简单的相关性排序：question匹配优先于answer匹配
            base_query = base_query.order_by(
                db.case(
                    (cls.question.contains(query), 1),
                    else_=2
                ),
                cls.created_at.desc()
            )
        else:
            base_query = base_query.order_by(cls.created_at.desc())
        
        return base_query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
    
    @classmethod
    def get_by_category(cls, category_id, page=1, per_page=20):
        """获取指定分类的问答对"""
        return cls.query.filter_by(category_id=category_id)\
                      .order_by(cls.created_at.desc())\
                      .paginate(page=page, per_page=per_page, error_out=False)
    
    @classmethod
    def get_popular(cls, limit=10):
        """获取热门问答（这里简单按置信度排序）"""
        return cls.query.order_by(cls.confidence.desc(), cls.created_at.desc())\
                       .limit(limit).all()
    
    @classmethod
    def get_recent(cls, limit=10):
        """获取最新问答"""
        return cls.query.order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_statistics(cls):
        """获取问答统计信息"""
        from .category import Category
        
        # 总数统计
        total_qa = cls.query.count()
        
        # 分类统计
        category_stats = db.session.query(
            Category.name,
            func.count(cls.id).label('count')
        ).outerjoin(cls).group_by(Category.id).all()
        
        # 回答者统计
        advisor_stats = db.session.query(
            cls.advisor,
            func.count(cls.id).label('count')
        ).filter(cls.advisor.isnot(None))\
         .group_by(cls.advisor)\
         .order_by(func.count(cls.id).desc())\
         .limit(10).all()
        
        # 置信度统计
        confidence_stats = db.session.query(
            func.avg(cls.confidence).label('avg_confidence'),
            func.min(cls.confidence).label('min_confidence'),
            func.max(cls.confidence).label('max_confidence'),
            func.count(db.case([(cls.confidence >= 0.8, 1)])).label('high_confidence'),
            func.count(db.case([(db.and_(cls.confidence >= 0.5, cls.confidence < 0.8), 1)])).label('medium_confidence'),
            func.count(db.case([(cls.confidence < 0.5, 1)])).label('low_confidence')
        ).first()
        
        return {
            'total_qa': total_qa,
            'category_distribution': [
                {'category': stat[0], 'count': stat[1]} 
                for stat in category_stats
            ],
            'top_advisors': [
                {'advisor': stat[0], 'count': stat[1]} 
                for stat in advisor_stats if stat[0]
            ],
            'confidence_stats': {
                'average': float(confidence_stats.avg_confidence or 0),
                'minimum': float(confidence_stats.min_confidence or 0),
                'maximum': float(confidence_stats.max_confidence or 0),
                'high_confidence': confidence_stats.high_confidence or 0,
                'medium_confidence': confidence_stats.medium_confidence or 0,
                'low_confidence': confidence_stats.low_confidence or 0
            }
        }
    
    def __repr__(self):
        question_preview = self.question[:50] + '...' if len(self.question) > 50 else self.question
        return f'<QAPair {self.id}: {question_preview}>'