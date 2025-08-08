"""
分类模型
"""
from app import db
from .base import BaseModel


class Category(BaseModel):
    """分类模型"""
    __tablename__ = 'categories'
    
    # 基本信息
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    color = db.Column(db.String(7), default='#1890ff')
    qa_count = db.Column(db.Integer, default=0)
    
    # 关联关系
    qa_pairs = db.relationship('QAPair', back_populates='category', lazy='dynamic')
    
    # 约束条件
    __table_args__ = (
        db.CheckConstraint("color REGEXP '^#[0-9A-Fa-f]{6}$'", name='valid_color'),
        db.CheckConstraint("qa_count >= 0", name='non_negative_qa_count'),
    )
    
    def to_dict(self, include_relationships=False):
        """转换为字典"""
        data = super().to_dict(include_relationships=False)  # 不包含关联关系
        
        # 动态计算高质量QA数量（过滤掉低置信度的原始消息）
        from .qa import QAPair
        data['qa_count'] = self.qa_pairs.filter(QAPair.confidence >= 0.5).count()
        
        return data
    
    def update_qa_count(self):
        """更新QA数量"""
        self.qa_count = self.qa_pairs.count()
        db.session.commit()
    
    @classmethod
    def get_by_name(cls, name):
        """根据名称获取分类"""
        return cls.query.filter_by(name=name).first()
    
    @classmethod
    def get_all_with_counts(cls):
        """获取所有分类并计算QA数量"""
        categories = cls.query.all()
        for category in categories:
            category.qa_count = category.qa_pairs.count()
        return categories
    
    @classmethod
    def create_default_categories(cls):
        """创建默认分类"""
        default_categories = [
            {'name': '产品咨询', 'description': '关于产品功能和特性的问题', 'color': '#1890ff'},
            {'name': '技术支持', 'description': '技术问题和故障排除', 'color': '#f5222d'},
            {'name': '价格费用', 'description': '价格、费用相关问题', 'color': '#52c41a'},
            {'name': '使用教程', 'description': '操作指南和使用方法', 'color': '#faad14'},
            {'name': '售后问题', 'description': '售后服务相关问题', 'color': '#722ed1'},
        ]
        
        created_categories = []
        for cat_data in default_categories:
            if not cls.get_by_name(cat_data['name']):
                category = cls(**cat_data)
                db.session.add(category)
                created_categories.append(category)
        
        if created_categories:
            db.session.commit()
        
        return created_categories
    
    def __repr__(self):
        return f'<Category {self.name}>'