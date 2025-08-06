-- 修复搜索函数的数据类型匹配问题

DROP FUNCTION IF EXISTS search_qa_pairs(text, bigint, text, int, int);

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
        -- 修复：分离排序逻辑，避免类型混合
        (CASE 
            WHEN search_query = '' THEN 0  -- 空查询时按时间排序
            ELSE 1  -- 有查询时按相关性排序
        END),
        (CASE 
            WHEN search_query = '' THEN NULL
            ELSE ts_rank(qp.fts_vector, plainto_tsquery('simple', search_query))
        END) DESC NULLS LAST,
        qp.created_at DESC
    LIMIT limit_count
    OFFSET offset_count;
END;
$$;