# Chatlog Database Design & Storage Strategy

## Database Overview

**Database Type**: SQLite (MVP) → PostgreSQL (Production)
**ORM**: SQLAlchemy with Flask-SQLAlchemy
**Migration Tool**: Flask-Migrate (Alembic)
**Connection Pooling**: SQLAlchemy built-in

## Database Schema Design

### Core Tables

#### 1. qa_pairs (问答对表)
```sql
CREATE TABLE qa_pairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category_id INTEGER,
    asker VARCHAR(100),
    advisor VARCHAR(100),
    confidence REAL DEFAULT 0.8,
    source_file VARCHAR(255),
    original_context TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (category_id) REFERENCES categories(id),
    
    -- Indexes for performance
    CREATE INDEX idx_qa_question ON qa_pairs(question);
    CREATE INDEX idx_qa_category ON qa_pairs(category_id);
    CREATE INDEX idx_qa_advisor ON qa_pairs(advisor);
    CREATE INDEX idx_qa_created ON qa_pairs(created_at);
    CREATE INDEX idx_qa_confidence ON qa_pairs(confidence);
);
```

#### 2. categories (分类表)
```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    color VARCHAR(7) DEFAULT '#1890ff',
    qa_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (color REGEXP '^#[0-9A-Fa-f]{6}$'),
    CHECK (qa_count >= 0)
);
```

#### 3. upload_history (上传历史表)
```sql
CREATE TABLE upload_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size INTEGER NOT NULL,
    file_hash VARCHAR(64) UNIQUE, -- SHA-256 hash for deduplication
    total_messages INTEGER,
    extracted_qa_count INTEGER,
    status VARCHAR(20) DEFAULT 'processing',
    error_message TEXT,
    processing_started_at DATETIME,
    processing_completed_at DATETIME,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (status IN ('processing', 'completed', 'error', 'cancelled')),
    CHECK (file_size > 0),
    CHECK (total_messages >= 0),
    CHECK (extracted_qa_count >= 0),
    
    -- Indexes
    CREATE INDEX idx_upload_status ON upload_history(status);
    CREATE INDEX idx_upload_date ON upload_history(uploaded_at);
    CREATE INDEX idx_upload_hash ON upload_history(file_hash);
);
```

### Support Tables

#### 4. search_history (搜索历史表)
```sql
CREATE TABLE search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query VARCHAR(255) NOT NULL,
    filters_json TEXT, -- JSON string for filters
    results_count INTEGER,
    response_time REAL, -- milliseconds
    user_ip VARCHAR(45), -- IPv6 support
    searched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for analytics
    CREATE INDEX idx_search_query ON search_history(query);
    CREATE INDEX idx_search_date ON search_history(searched_at);
);
```

#### 5. qa_tags (问答标签表) - 扩展功能
```sql
CREATE TABLE qa_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL,
    color VARCHAR(7) DEFAULT '#87d068',
    usage_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE qa_pair_tags (
    qa_id INTEGER,
    tag_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (qa_id, tag_id),
    FOREIGN KEY (qa_id) REFERENCES qa_pairs(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES qa_tags(id) ON DELETE CASCADE
);
```

#### 6. system_config (系统配置表)
```sql
CREATE TABLE system_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    description TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Common configurations
    INSERT INTO system_config VALUES 
    ('search_results_per_page', '20', '搜索结果每页显示数量'),
    ('max_upload_file_size', '52428800', '最大上传文件大小(字节)'),
    ('auto_classification_enabled', 'true', '是否启用自动分类'),
    ('search_cache_ttl', '300', '搜索缓存过期时间(秒)');
);
```

### Full-Text Search Tables

#### 7. qa_pairs_fts (全文搜索表)
```sql
-- SQLite FTS5 virtual table
CREATE VIRTUAL TABLE qa_pairs_fts USING fts5(
    question, 
    answer, 
    category_name,
    advisor,
    content_source='qa_pairs',
    tokenize='porter unicode61'
);

-- Triggers to maintain FTS table
CREATE TRIGGER qa_pairs_fts_insert AFTER INSERT ON qa_pairs BEGIN
    INSERT INTO qa_pairs_fts(rowid, question, answer, category_name, advisor)
    SELECT NEW.id, NEW.question, NEW.answer, 
           COALESCE((SELECT name FROM categories WHERE id = NEW.category_id), ''),
           COALESCE(NEW.advisor, '');
END;

CREATE TRIGGER qa_pairs_fts_update AFTER UPDATE ON qa_pairs BEGIN
    UPDATE qa_pairs_fts SET 
        question = NEW.question,
        answer = NEW.answer,
        category_name = COALESCE((SELECT name FROM categories WHERE id = NEW.category_id), ''),
        advisor = COALESCE(NEW.advisor, '')
    WHERE rowid = NEW.id;
END;

CREATE TRIGGER qa_pairs_fts_delete AFTER DELETE ON qa_pairs BEGIN
    DELETE FROM qa_pairs_fts WHERE rowid = OLD.id;
END;
```

## SQLAlchemy Models

### Base Model
```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Real, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class BaseModel(db.Model):
    __abstract__ = True
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def update(self, **kwargs):
        """Update model attributes"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()
```

### Core Models
```python
class Category(BaseModel):
    __tablename__ = 'categories'
    
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    color = Column(String(7), default='#1890ff')
    qa_count = Column(Integer, default=0)
    
    # Relationships
    qa_pairs = relationship("QAPair", back_populates="category", lazy='dynamic')
    
    def __repr__(self):
        return f"<Category {self.name}>"
    
    def to_dict(self):
        data = super().to_dict()
        data['qa_count'] = self.qa_pairs.count()
        return data

class QAPair(BaseModel):
    __tablename__ = 'qa_pairs'
    
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'))
    asker = Column(String(100))
    advisor = Column(String(100))
    confidence = Column(Real, default=0.8)
    source_file = Column(String(255))
    original_context = Column(Text)
    
    # Relationships
    category = relationship("Category", back_populates="qa_pairs")
    tags = relationship("QATag", secondary="qa_pair_tags", back_populates="qa_pairs")
    
    # Indexes
    __table_args__ = (
        db.Index('idx_qa_question', 'question'),
        db.Index('idx_qa_category', 'category_id'),
        db.Index('idx_qa_advisor', 'advisor'),
        db.Index('idx_qa_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<QAPair {self.id}: {self.question[:50]}...>"
    
    def to_dict(self):
        data = super().to_dict()
        data['category'] = self.category.to_dict() if self.category else None
        data['tags'] = [tag.to_dict() for tag in self.tags]
        return data

class UploadHistory(BaseModel):
    __tablename__ = 'upload_history'
    
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_hash = Column(String(64), unique=True)
    total_messages = Column(Integer)
    extracted_qa_count = Column(Integer)
    status = Column(String(20), default='processing')
    error_message = Column(Text)
    processing_started_at = Column(DateTime)
    processing_completed_at = Column(DateTime)
    
    __table_args__ = (
        db.CheckConstraint("status IN ('processing', 'completed', 'error', 'cancelled')"),
        db.CheckConstraint("file_size > 0"),
        db.Index('idx_upload_status', 'status'),
        db.Index('idx_upload_date', 'created_at'),
    )
    
    def __repr__(self):
        return f"<UploadHistory {self.filename}: {self.status}>"
    
    @property
    def processing_duration(self):
        """Calculate processing duration in seconds"""
        if self.processing_started_at and self.processing_completed_at:
            return (self.processing_completed_at - self.processing_started_at).total_seconds()
        return None

class SearchHistory(BaseModel):
    __tablename__ = 'search_history'
    __table_args__ = {'extend_existing': True}
    
    query = Column(String(255), nullable=False)
    filters_json = Column(Text)
    results_count = Column(Integer)
    response_time = Column(Real)  # milliseconds
    user_ip = Column(String(45))
    searched_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_search_query', 'query'),
        db.Index('idx_search_date', 'searched_at'),
    )
    
    def __repr__(self):
        return f"<SearchHistory: {self.query}>"
```

### Extended Models
```python
class QATag(BaseModel):
    __tablename__ = 'qa_tags'
    
    name = Column(String(50), unique=True, nullable=False)
    color = Column(String(7), default='#87d068')
    usage_count = Column(Integer, default=0)
    
    # Relationships
    qa_pairs = relationship("QAPair", secondary="qa_pair_tags", back_populates="tags")
    
    def __repr__(self):
        return f"<QATag {self.name}>"

# Association table for many-to-many relationship
qa_pair_tags = db.Table('qa_pair_tags',
    Column('qa_id', Integer, ForeignKey('qa_pairs.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('qa_tags.id'), primary_key=True),
    Column('created_at', DateTime, default=datetime.utcnow)
)

class SystemConfig(db.Model):
    __tablename__ = 'system_config'
    
    key = Column(String(100), primary_key=True)
    value = Column(Text)
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<SystemConfig {self.key}: {self.value}>"
    
    @classmethod
    def get_value(cls, key, default=None):
        """Get configuration value"""
        config = cls.query.filter_by(key=key).first()
        return config.value if config else default
    
    @classmethod
    def set_value(cls, key, value, description=None):
        """Set configuration value"""
        config = cls.query.filter_by(key=key).first()
        if config:
            config.value = value
            config.updated_at = datetime.utcnow()
        else:
            config = cls(key=key, value=value, description=description)
            db.session.add(config)
        db.session.commit()
        return config
```

## Database Queries & Repository Pattern

### Repository Base Class
```python
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Query
from sqlalchemy import func, desc, asc

class BaseRepository:
    def __init__(self, model):
        self.model = model
    
    def get_by_id(self, id: int) -> Optional[Any]:
        return self.model.query.get(id)
    
    def get_all(self, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        query = self.model.query
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        return {
            'items': pagination.items,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    
    def create(self, **kwargs) -> Any:
        instance = self.model(**kwargs)
        db.session.add(instance)
        db.session.commit()
        return instance
    
    def update(self, id: int, **kwargs) -> Optional[Any]:
        instance = self.get_by_id(id)
        if instance:
            instance.update(**kwargs)
            db.session.commit()
        return instance
    
    def delete(self, id: int) -> bool:
        instance = self.get_by_id(id)
        if instance:
            db.session.delete(instance)
            db.session.commit()
            return True
        return False
```

### QA Repository
```python
class QARepository(BaseRepository):
    def __init__(self):
        super().__init__(QAPair)
    
    def search(self, query: str, filters: Dict[str, Any] = None, 
               page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Full-text search with filters"""
        # Use FTS5 for search
        search_query = db.session.query(QAPair).join(
            db.session.query(func.rowid).select_from(
                func.qa_pairs_fts(query)
            ).subquery(),
            QAPair.id == func.rowid
        )
        
        # Apply filters
        if filters:
            if filters.get('category_id'):
                search_query = search_query.filter(
                    QAPair.category_id.in_(filters['category_id'])
                )
            if filters.get('advisor'):
                search_query = search_query.filter(
                    QAPair.advisor.in_(filters['advisor'])
                )
            if filters.get('start_date'):
                search_query = search_query.filter(
                    QAPair.created_at >= filters['start_date']
                )
            if filters.get('end_date'):
                search_query = search_query.filter(
                    QAPair.created_at <= filters['end_date']
                )
        
        # Order by relevance (FTS5 rank)
        search_query = search_query.order_by(desc('rank'))
        
        # Paginate
        pagination = search_query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return {
            'items': pagination.items,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    
    def get_by_category(self, category_id: int, 
                       page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Get QA pairs by category"""
        query = self.model.query.filter_by(category_id=category_id)
        query = query.order_by(desc(QAPair.created_at))
        
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return {
            'items': pagination.items,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    
    def get_popular(self, limit: int = 10) -> List[QAPair]:
        """Get popular QA pairs based on search frequency"""
        return self.model.query.join(SearchHistory).group_by(
            QAPair.id
        ).order_by(
            desc(func.count(SearchHistory.id))
        ).limit(limit).all()
    
    def get_recent(self, limit: int = 10) -> List[QAPair]:
        """Get recent QA pairs"""
        return self.model.query.order_by(
            desc(QAPair.created_at)
        ).limit(limit).all()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get QA statistics"""
        total_qa = self.model.query.count()
        
        category_stats = db.session.query(
            Category.name,
            func.count(QAPair.id).label('count')
        ).outerjoin(QAPair).group_by(Category.id).all()
        
        advisor_stats = db.session.query(
            QAPair.advisor,
            func.count(QAPair.id).label('count')
        ).filter(QAPair.advisor.isnot(None)).group_by(
            QAPair.advisor
        ).order_by(desc('count')).limit(10).all()
        
        confidence_stats = db.session.query(
            func.avg(QAPair.confidence).label('avg_confidence'),
            func.min(QAPair.confidence).label('min_confidence'),
            func.max(QAPair.confidence).label('max_confidence')
        ).first()
        
        return {
            'total_qa': total_qa,
            'category_distribution': [
                {'category': stat[0], 'count': stat[1]} 
                for stat in category_stats
            ],
            'top_advisors': [
                {'advisor': stat[0], 'count': stat[1]} 
                for stat in advisor_stats
            ],
            'confidence_stats': {
                'average': float(confidence_stats.avg_confidence or 0),
                'minimum': float(confidence_stats.min_confidence or 0),
                'maximum': float(confidence_stats.max_confidence or 0)
            }
        }
```

### Category Repository
```python
class CategoryRepository(BaseRepository):
    def __init__(self):
        super().__init__(Category)
    
    def get_with_counts(self) -> List[Category]:
        """Get categories with QA counts"""
        return db.session.query(Category).outerjoin(QAPair).group_by(
            Category.id
        ).add_columns(
            func.count(QAPair.id).label('qa_count')
        ).all()
    
    def update_counts(self):
        """Update QA counts for all categories"""
        categories = self.model.query.all()
        for category in categories:
            category.qa_count = category.qa_pairs.count()
        db.session.commit()
```

## Database Migration Strategy

### Migration Scripts
```python
# migrations/versions/001_initial_schema.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Create categories table
    op.create_table('categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('color', sa.String(7), default='#1890ff'),
        sa.Column('qa_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create qa_pairs table
    op.create_table('qa_pairs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('category_id', sa.Integer()),
        sa.Column('asker', sa.String(100)),
        sa.Column('advisor', sa.String(100)),
        sa.Column('confidence', sa.Real(), default=0.8),
        sa.Column('source_file', sa.String(255)),
        sa.Column('original_context', sa.Text()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_qa_question', 'qa_pairs', ['question'])
    op.create_index('idx_qa_category', 'qa_pairs', ['category_id'])
    op.create_index('idx_qa_advisor', 'qa_pairs', ['advisor'])
    op.create_index('idx_qa_created', 'qa_pairs', ['created_at'])

def downgrade():
    op.drop_table('qa_pairs')
    op.drop_table('categories')
```

### Data Seeding
```python
# seeds/initial_data.py
from app.models import Category, SystemConfig

def seed_categories():
    """Seed initial categories"""
    categories = [
        {'name': '产品咨询', 'description': '关于产品功能和特性的问题', 'color': '#1890ff'},
        {'name': '技术支持', 'description': '技术问题和故障排除', 'color': '#f5222d'},
        {'name': '价格费用', 'description': '价格、费用相关问题', 'color': '#52c41a'},
        {'name': '使用教程', 'description': '操作指南和使用方法', 'color': '#faad14'},
        {'name': '售后问题', 'description': '售后服务相关问题', 'color': '#722ed1'},
    ]
    
    for cat_data in categories:
        if not Category.query.filter_by(name=cat_data['name']).first():
            category = Category(**cat_data)
            db.session.add(category)
    
    db.session.commit()

def seed_system_config():
    """Seed system configuration"""
    configs = [
        ('search_results_per_page', '20', '搜索结果每页显示数量'),
        ('max_upload_file_size', '52428800', '最大上传文件大小(字节)'),
        ('auto_classification_enabled', 'true', '是否启用自动分类'),
        ('search_cache_ttl', '300', '搜索缓存过期时间(秒)'),
    ]
    
    for key, value, description in configs:
        if not SystemConfig.query.filter_by(key=key).first():
            config = SystemConfig(key=key, value=value, description=description)
            db.session.add(config)
    
    db.session.commit()
```

## Performance Optimization

### Database Optimization
```sql
-- Query optimization
EXPLAIN QUERY PLAN 
SELECT * FROM qa_pairs 
WHERE question MATCH 'chatlog' 
ORDER BY rank;

-- Index usage analysis
PRAGMA index_info(idx_qa_question);
PRAGMA index_list(qa_pairs);

-- Database statistics
ANALYZE qa_pairs;
ANALYZE qa_pairs_fts;
```

### Connection Pooling
```python
# config.py
import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///chatlog.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 120,
        'pool_pre_ping': True,
        'max_overflow': 0,
    }
```

### Backup & Maintenance
```python
# Database backup script
import sqlite3
import shutil
from datetime import datetime

def backup_database():
    """Create database backup"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f'backups/chatlog_backup_{timestamp}.db'
    
    # SQLite backup
    shutil.copy2('chatlog.db', backup_path)
    
    # Verify backup
    with sqlite3.connect(backup_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM qa_pairs")
        count = cursor.fetchone()[0]
        print(f"Backup created: {backup_path} ({count} QA pairs)")

def cleanup_old_data():
    """Clean up old search history"""
    cutoff_date = datetime.now() - timedelta(days=90)
    SearchHistory.query.filter(
        SearchHistory.created_at < cutoff_date
    ).delete()
    db.session.commit()
```