-- Row Level Security (RLS) 策略配置
-- 目前为演示版本，允许匿名访问，生产环境应该配置适当的用户认证

-- 启用 RLS
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE qa_pairs ENABLE ROW LEVEL SECURITY;
ALTER TABLE upload_history ENABLE ROW LEVEL SECURITY;

-- Categories 表策略 - 允许所有人查看，暂时允许匿名插入/更新
CREATE POLICY "Allow public read access on categories" 
ON categories FOR SELECT 
USING (true);

CREATE POLICY "Allow public insert on categories" 
ON categories FOR INSERT 
WITH CHECK (true);

CREATE POLICY "Allow public update on categories" 
ON categories FOR UPDATE 
USING (true);

-- QA Pairs 表策略 - 允许所有人查看和添加
CREATE POLICY "Allow public read access on qa_pairs" 
ON qa_pairs FOR SELECT 
USING (true);

CREATE POLICY "Allow public insert on qa_pairs" 
ON qa_pairs FOR INSERT 
WITH CHECK (true);

CREATE POLICY "Allow public update on qa_pairs" 
ON qa_pairs FOR UPDATE 
USING (true);

CREATE POLICY "Allow public delete on qa_pairs" 
ON qa_pairs FOR DELETE 
USING (true);

-- Upload History 表策略 - 允许查看和插入
CREATE POLICY "Allow public read access on upload_history" 
ON upload_history FOR SELECT 
USING (true);

CREATE POLICY "Allow public insert on upload_history" 
ON upload_history FOR INSERT 
WITH CHECK (true);

CREATE POLICY "Allow public update on upload_history" 
ON upload_history FOR UPDATE 
USING (true);

-- 创建用于全文搜索的函数
CREATE OR REPLACE FUNCTION search_qa_pairs(
    search_query text DEFAULT '',
    category_filter bigint DEFAULT NULL,
    advisor_filter text DEFAULT NULL,
    limit_count int DEFAULT 20,
    offset_count int DEFAULT 0
)
RETURNS TABLE (
    id bigint,
    question text,
    answer text,
    category_id bigint,
    asker varchar(100),
    advisor varchar(100),
    confidence real,
    source_file varchar(255),
    created_at timestamp with time zone,
    category_name varchar(50),
    category_color varchar(7),
    category_description text,
    search_rank real
) 
SECURITY DEFINER
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        qp.id,
        qp.question,
        qp.answer,
        qp.category_id,
        qp.asker,
        qp.advisor,
        qp.confidence,
        qp.source_file,
        qp.created_at,
        c.name as category_name,
        c.color as category_color,
        c.description as category_description,
        CASE 
            WHEN search_query = '' THEN 1.0
            ELSE ts_rank(qp.fts_vector, plainto_tsquery('simple', search_query))
        END as search_rank
    FROM qa_pairs qp
    LEFT JOIN categories c ON qp.category_id = c.id
    WHERE 
        (search_query = '' OR qp.fts_vector @@ plainto_tsquery('simple', search_query))
        AND (category_filter IS NULL OR qp.category_id = category_filter)
        AND (advisor_filter IS NULL OR qp.advisor ILIKE '%' || advisor_filter || '%')
    ORDER BY 
        CASE 
            WHEN search_query = '' THEN qp.created_at
            ELSE ts_rank(qp.fts_vector, plainto_tsquery('simple', search_query))
        END DESC,
        qp.created_at DESC
    LIMIT limit_count
    OFFSET offset_count;
END;
$$;

-- 创建获取搜索结果数量的函数
CREATE OR REPLACE FUNCTION count_qa_pairs(
    search_query text DEFAULT '',
    category_filter bigint DEFAULT NULL,
    advisor_filter text DEFAULT NULL
)
RETURNS bigint
SECURITY DEFINER
LANGUAGE plpgsql
AS $$
DECLARE
    result_count bigint;
BEGIN
    SELECT COUNT(*)
    INTO result_count
    FROM qa_pairs qp
    WHERE 
        (search_query = '' OR qp.fts_vector @@ plainto_tsquery('simple', search_query))
        AND (category_filter IS NULL OR qp.category_id = category_filter)
        AND (advisor_filter IS NULL OR qp.advisor ILIKE '%' || advisor_filter || '%');
    
    RETURN result_count;
END;
$$;

-- 创建获取统计信息的函数
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
                    'id', id,
                    'name', name,
                    'color', color,
                    'description', description,
                    'qa_count', qa_count
                )
            )
            FROM categories
            ORDER BY qa_count DESC, name
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