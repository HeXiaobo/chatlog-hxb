-- 最终完整修复脚本 - 包含所有必要的函数

-- 1. 删除所有旧函数
DROP FUNCTION IF EXISTS search_qa_pairs(text, bigint, text, int, int);
DROP FUNCTION IF EXISTS count_qa_pairs(text, bigint, text);
DROP FUNCTION IF EXISTS get_qa_statistics();

-- 2. 重新创建搜索函数（简化版本，避免类型冲突）
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
            WHEN search_query = '' OR search_query IS NULL THEN 1.0
            ELSE ts_rank(qp.fts_vector, plainto_tsquery('simple', search_query))
        END as search_rank
    FROM qa_pairs qp
    LEFT JOIN categories c ON qp.category_id = c.id
    WHERE 
        (search_query = '' OR search_query IS NULL OR qp.fts_vector @@ plainto_tsquery('simple', search_query))
        AND (category_filter IS NULL OR qp.category_id = category_filter)
        AND (advisor_filter IS NULL OR qp.advisor ILIKE '%' || advisor_filter || '%')
    ORDER BY 
        -- 简单的排序：相关性高的在前，时间新的在前
        search_rank DESC,
        qp.created_at DESC
    LIMIT limit_count
    OFFSET offset_count;
END;
$$;

-- 3. 重新创建计数函数
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
        (search_query = '' OR search_query IS NULL OR qp.fts_vector @@ plainto_tsquery('simple', search_query))
        AND (category_filter IS NULL OR qp.category_id = category_filter)
        AND (advisor_filter IS NULL OR qp.advisor ILIKE '%' || advisor_filter || '%');
    
    RETURN result_count;
END;
$$;

-- 4. 重新创建统计函数（简化版本）
CREATE OR REPLACE FUNCTION get_qa_statistics()
RETURNS JSON
SECURITY DEFINER
LANGUAGE sql
AS $$
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
                'average', ROUND(COALESCE(AVG(confidence), 0)::numeric, 3),
                'high_confidence', COUNT(*) FILTER (WHERE confidence >= 0.8),
                'medium_confidence', COUNT(*) FILTER (WHERE confidence >= 0.5 AND confidence < 0.8),
                'low_confidence', COUNT(*) FILTER (WHERE confidence < 0.5)
            )
            FROM qa_pairs
        ),
        'recent_uploads', '[]'::json
    )
$$;

-- 5. 更新分类表的计数
UPDATE categories SET qa_count = (
    SELECT COUNT(*) FROM qa_pairs WHERE qa_pairs.category_id = categories.id
);