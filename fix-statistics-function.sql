-- 修复统计函数的 GROUP BY 问题

DROP FUNCTION IF EXISTS get_qa_statistics();

CREATE OR REPLACE FUNCTION get_qa_statistics()
RETURNS JSON
SECURITY DEFINER
LANGUAGE plpgsql
AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'total_qa', (SELECT COUNT(*) FROM qa_pairs),
        'total_categories', (SELECT COUNT(*) FROM categories),
        'categories_with_count', (
            SELECT json_agg(
                json_build_object(
                    'id', c.id,
                    'name', c.name,
                    'color', c.color,
                    'description', c.description,
                    'qa_count', COALESCE(qa_counts.count, 0)
                )
                ORDER BY COALESCE(qa_counts.count, 0) DESC, c.name
            )
            FROM categories c
            LEFT JOIN (
                SELECT category_id, COUNT(*) as count
                FROM qa_pairs 
                WHERE category_id IS NOT NULL
                GROUP BY category_id
            ) qa_counts ON c.id = qa_counts.category_id
        ),
        'top_advisors', (
            SELECT json_agg(
                json_build_object(
                    'advisor', advisor,
                    'count', advisor_count
                )
            )
            FROM (
                SELECT advisor, COUNT(*) as advisor_count
                FROM qa_pairs
                WHERE advisor IS NOT NULL AND advisor != ''
                GROUP BY advisor
                ORDER BY COUNT(*) DESC
                LIMIT 10
            ) top_advisors_query
        ),
        'confidence_stats', (
            SELECT json_build_object(
                'average', ROUND(AVG(confidence)::numeric, 3),
                'high_confidence', COUNT(*) FILTER (WHERE confidence >= 0.8),
                'medium_confidence', COUNT(*) FILTER (WHERE confidence >= 0.5 AND confidence < 0.8),
                'low_confidence', COUNT(*) FILTER (WHERE confidence < 0.5)
            )
            FROM qa_pairs
        ),
        'recent_uploads', (
            SELECT json_agg(
                json_build_object(
                    'id', id,
                    'filename', original_name,
                    'status', status,
                    'processed_count', processed_count,
                    'created_at', created_at
                )
                ORDER BY created_at DESC
            )
            FROM (
                SELECT * FROM upload_history
                ORDER BY created_at DESC
                LIMIT 5
            ) recent_uploads_query
        )
    ) INTO result;
    
    RETURN result;
END;
$$;

-- 同时修复分类表的 qa_count 字段
-- 首先更新现有数据
UPDATE categories SET qa_count = (
    SELECT COUNT(*) FROM qa_pairs WHERE qa_pairs.category_id = categories.id
);

-- 创建触发器函数来自动更新 qa_count
CREATE OR REPLACE FUNCTION update_category_qa_count()
RETURNS TRIGGER AS $$
BEGIN
    -- 处理 INSERT 操作
    IF TG_OP = 'INSERT' THEN
        UPDATE categories 
        SET qa_count = qa_count + 1 
        WHERE id = NEW.category_id;
        RETURN NEW;
    END IF;
    
    -- 处理 DELETE 操作
    IF TG_OP = 'DELETE' THEN
        UPDATE categories 
        SET qa_count = qa_count - 1 
        WHERE id = OLD.category_id AND qa_count > 0;
        RETURN OLD;
    END IF;
    
    -- 处理 UPDATE 操作（分类更改）
    IF TG_OP = 'UPDATE' THEN
        -- 如果分类发生变化
        IF OLD.category_id IS DISTINCT FROM NEW.category_id THEN
            -- 减少旧分类的计数
            IF OLD.category_id IS NOT NULL THEN
                UPDATE categories 
                SET qa_count = qa_count - 1 
                WHERE id = OLD.category_id AND qa_count > 0;
            END IF;
            -- 增加新分类的计数
            IF NEW.category_id IS NOT NULL THEN
                UPDATE categories 
                SET qa_count = qa_count + 1 
                WHERE id = NEW.category_id;
            END IF;
        END IF;
        RETURN NEW;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 创建触发器（如果不存在）
DROP TRIGGER IF EXISTS qa_pairs_category_count_trigger ON qa_pairs;
CREATE TRIGGER qa_pairs_category_count_trigger
    AFTER INSERT OR UPDATE OR DELETE ON qa_pairs
    FOR EACH ROW
    EXECUTE FUNCTION update_category_qa_count();