-- ChatLog Knowledge Base 数据库结构
-- 基于原有 Flask 应用迁移到 Supabase

-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 创建分类表
CREATE TABLE categories (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    color VARCHAR(7) DEFAULT '#1890ff' CHECK (color ~ '^#[0-9A-Fa-f]{6}$'),
    qa_count INTEGER DEFAULT 0 CHECK (qa_count >= 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建问答对表
CREATE TABLE qa_pairs (
    id BIGSERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category_id BIGINT REFERENCES categories(id) ON DELETE SET NULL,
    asker VARCHAR(100),
    advisor VARCHAR(100),
    confidence REAL DEFAULT 0.8 CHECK (confidence >= 0 AND confidence <= 1),
    source_file VARCHAR(255),
    original_context TEXT,
    -- 生成的全文搜索向量 (支持中文)
    fts_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('simple', COALESCE(question, '')), 'A') ||
        setweight(to_tsvector('simple', COALESCE(answer, '')), 'B')
    ) STORED,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建上传历史表
CREATE TABLE upload_history (
    id BIGSERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_name VARCHAR(255),
    file_size INTEGER,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    processed_count INTEGER DEFAULT 0,
    total_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
-- 问答对表索引
CREATE INDEX qa_pairs_fts_idx ON qa_pairs USING GIN (fts_vector);
CREATE INDEX qa_pairs_category_idx ON qa_pairs(category_id);
CREATE INDEX qa_pairs_confidence_idx ON qa_pairs(confidence);
CREATE INDEX qa_pairs_advisor_idx ON qa_pairs(advisor);
CREATE INDEX qa_pairs_created_idx ON qa_pairs(created_at DESC);
CREATE INDEX qa_pairs_composite_idx ON qa_pairs(category_id, advisor, created_at DESC);

-- 分类表索引
CREATE INDEX categories_name_idx ON categories(name);

-- 上传历史表索引
CREATE INDEX upload_history_status_idx ON upload_history(status);
CREATE INDEX upload_history_created_idx ON upload_history(created_at DESC);

-- 创建更新 updated_at 的触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为每个表创建 updated_at 触发器
CREATE TRIGGER update_categories_updated_at 
    BEFORE UPDATE ON categories 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_qa_pairs_updated_at 
    BEFORE UPDATE ON qa_pairs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_upload_history_updated_at 
    BEFORE UPDATE ON upload_history 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 创建函数：更新分类的 qa_count
CREATE OR REPLACE FUNCTION update_category_qa_count()
RETURNS TRIGGER AS $$
BEGIN
    -- 如果是插入操作
    IF TG_OP = 'INSERT' THEN
        UPDATE categories 
        SET qa_count = qa_count + 1 
        WHERE id = NEW.category_id;
        RETURN NEW;
    END IF;
    
    -- 如果是删除操作
    IF TG_OP = 'DELETE' THEN
        UPDATE categories 
        SET qa_count = qa_count - 1 
        WHERE id = OLD.category_id AND qa_count > 0;
        RETURN OLD;
    END IF;
    
    -- 如果是更新操作且分类发生变化
    IF TG_OP = 'UPDATE' AND OLD.category_id != NEW.category_id THEN
        -- 旧分类计数减1
        UPDATE categories 
        SET qa_count = qa_count - 1 
        WHERE id = OLD.category_id AND qa_count > 0;
        
        -- 新分类计数加1
        UPDATE categories 
        SET qa_count = qa_count + 1 
        WHERE id = NEW.category_id;
        
        RETURN NEW;
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为 qa_pairs 创建 category_count 触发器
CREATE TRIGGER qa_pairs_category_count_trigger
    AFTER INSERT OR UPDATE OR DELETE ON qa_pairs
    FOR EACH ROW EXECUTE FUNCTION update_category_qa_count();