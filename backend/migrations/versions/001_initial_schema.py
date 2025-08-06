"""Initial schema migration

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-08-06 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create initial database schema"""
    
    # Create categories table
    op.create_table('categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for categories
    op.create_index('idx_categories_name', 'categories', ['name'], unique=True)
    
    # Create upload_history table
    op.create_table('upload_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('file_hash', sa.String(32), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('qa_count', sa.Integer(), nullable=True),
        sa.Column('processing_time', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for upload_history
    op.create_index('idx_upload_history_status', 'upload_history', ['status'])
    op.create_index('idx_upload_history_uploaded_at', 'upload_history', ['uploaded_at'])
    op.create_index('idx_upload_history_file_hash', 'upload_history', ['file_hash'])
    
    # Create qa_pairs table
    op.create_table('qa_pairs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('asker', sa.String(100), nullable=True),
        sa.Column('advisor', sa.String(100), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True, default=0.8),
        sa.Column('source_file', sa.String(255), nullable=True),
        sa.Column('original_context', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL')
    )
    
    # Create indexes for qa_pairs
    op.create_index('idx_qa_question', 'qa_pairs', ['question'])
    op.create_index('idx_qa_category', 'qa_pairs', ['category_id'])
    op.create_index('idx_qa_advisor', 'qa_pairs', ['advisor'])
    op.create_index('idx_qa_created', 'qa_pairs', ['created_at'])
    op.create_index('idx_qa_confidence', 'qa_pairs', ['confidence'])
    op.create_index('idx_qa_composite', 'qa_pairs', ['category_id', 'advisor', 'created_at'])
    
    # Insert default categories
    categories_table = sa.table('categories',
        sa.column('name', sa.String),
        sa.column('description', sa.Text),
        sa.column('color', sa.String),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime)
    )
    
    default_categories = [
        {
            'name': '产品咨询',
            'description': '关于产品功能和特性的问题',
            'color': '#1890ff',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        },
        {
            'name': '技术支持',
            'description': '技术问题和故障排除',
            'color': '#f5222d',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        },
        {
            'name': '价格费用',
            'description': '价格、费用相关问题',
            'color': '#52c41a',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        },
        {
            'name': '使用教程',
            'description': '操作指南和使用方法',
            'color': '#faad14',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        },
        {
            'name': '售后问题',
            'description': '售后服务相关问题',
            'color': '#722ed1',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
    ]
    
    op.bulk_insert(categories_table, default_categories)


def downgrade():
    """Drop all tables"""
    op.drop_table('qa_pairs')
    op.drop_table('upload_history')
    op.drop_table('categories')