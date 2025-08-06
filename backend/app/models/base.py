"""
数据库模型基类
"""
from datetime import datetime
from app import db


class BaseModel(db.Model):
    """数据库模型基类"""
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self, include_relationships=False):
        """
        将模型转换为字典
        
        Args:
            include_relationships: 是否包含关联对象
        
        Returns:
            dict: 模型字典表示
        """
        data = {}
        
        # 基本字段
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            
            # 处理日期时间
            if isinstance(value, datetime):
                value = value.isoformat() + 'Z'
            
            data[column.name] = value
        
        # 关联对象
        if include_relationships:
            for relationship in self.__mapper__.relationships:
                name = relationship.key
                value = getattr(self, name)
                
                if value is not None:
                    if hasattr(value, 'to_dict'):
                        # 单个关联对象
                        data[name] = value.to_dict()
                    elif hasattr(value, '__iter__'):
                        # 多个关联对象
                        data[name] = [
                            item.to_dict() if hasattr(item, 'to_dict') else str(item)
                            for item in value
                        ]
                    else:
                        data[name] = str(value)
        
        return data
    
    def update(self, **kwargs):
        """
        更新模型属性
        
        Args:
            **kwargs: 要更新的属性
        """
        for key, value in kwargs.items():
            if hasattr(self, key) and key not in ('id', 'created_at'):
                setattr(self, key, value)
        
        self.updated_at = datetime.utcnow()
    
    def save(self):
        """保存到数据库"""
        db.session.add(self)
        db.session.commit()
        return self
    
    def delete(self):
        """从数据库删除"""
        db.session.delete(self)
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, id):
        """根据ID获取对象"""
        return cls.query.get(id)
    
    @classmethod
    def get_or_404(cls, id):
        """根据ID获取对象，不存在则返回404"""
        return cls.query.get_or_404(id)
    
    def __repr__(self):
        return f'<{self.__class__.__name__} {self.id}>'