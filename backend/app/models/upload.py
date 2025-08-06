"""
上传历史模型
"""
from datetime import datetime
from app import db
from .base import BaseModel


class UploadHistory(BaseModel):
    """上传历史模型"""
    __tablename__ = 'upload_history'
    
    # 文件信息
    filename = db.Column(db.String(255), nullable=False)  # 存储文件名
    file_size = db.Column(db.BigInteger, nullable=True)  # 文件大小（字节）
    file_hash = db.Column(db.String(32), nullable=True)  # MD5文件哈希，用于去重
    
    # 处理状态
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, processing, completed, failed
    
    # 处理结果
    qa_count = db.Column(db.Integer, nullable=True)  # 提取的问答对数量
    processing_time = db.Column(db.Float, nullable=True)  # 处理时间（秒）
    error_message = db.Column(db.Text, nullable=True)  # 错误消息
    
    # 处理时间
    uploaded_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # 约束条件
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name='valid_status'
        ),
        db.CheckConstraint("file_size >= 0", name='non_negative_file_size'),
        db.CheckConstraint("qa_count >= 0", name='non_negative_qa_count'),
        db.CheckConstraint("processing_time >= 0", name='non_negative_processing_time'),
        # 索引
        db.Index('idx_upload_status', 'status'),
        db.Index('idx_upload_uploaded_at', 'uploaded_at'),
        db.Index('idx_upload_hash', 'file_hash'),
    )
    
    def to_dict(self, include_relationships=False):
        """转换为字典"""
        data = super().to_dict(include_relationships=False)
        return data
    
    def __repr__(self):
        return f'<UploadHistory {self.id}: {self.filename} ({self.status})>'