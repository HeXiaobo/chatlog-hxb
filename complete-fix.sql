-- 完整修复脚本：解决搜索函数和统计函数的所有问题

-- 1. 修复搜索函数 - 完全重写避免类型冲突
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
    -- 如果是空查询，按时间排序
    IF search_query = '' OR search_query IS NULL THEN
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
            1.0::real as search_rank
        FROM qa_pairs qp
        LEFT JOIN categories c ON qp.category_id = c.id
        WHERE 
            (category_filter IS NULL OR qp.category_id = category_filter)
            AND (advisor_filter IS NULL OR qp.advisor ILIKE '%' || advisor_filter || '%')
        ORDER BY qp.created_at DESC
        LIMIT limit_count
        OFFSET offset_count;
    ELSE
        -- 如果有查询内容，按相关性排序
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
            ts_rank(qp.fts_vector, plainto_tsquery('simple', search_query)) as search_rank
        FROM qa_pairs qp
        LEFT JOIN categories c ON qp.category_id = c.id
        WHERE 
            qp.fts_vector @@ plainto_tsquery('simple', search_query)
            AND (category_filter IS NULL OR qp.category_id = category_filter)
            AND (advisor_filter IS NULL OR qp.advisor ILIKE '%' || advisor_filter || '%')
        ORDER BY ts_rank(qp.fts_vector, plainto_tsquery('simple', search_query)) DESC, qp.created_at DESC
        LIMIT limit_count
        OFFSET offset_count;
    END IF;
END;
$$;

-- 2. 修复统计函数 - 重写避免 GROUP BY 问题
DROP FUNCTION IF EXISTS get_qa_statistics();

CREATE OR REPLACE FUNCTION get_qa_statistics()
RETURNS JSON
SECURITY DEFINER
LANGUAGE plpgsql
AS $$
DECLARE
    result JSON;
    total_qa_count int;
    total_categories_count int;
    categories_json JSON;
    advisors_json JSON;
    confidence_json JSON;
    uploads_json JSON;
BEGIN
    -- 获取总问答数
    SELECT COUNT(*) INTO total_qa_count FROM qa_pairs;
    
    -- 获取总分类数
    SELECT COUNT(*) INTO total_categories_count FROM categories;
    
    -- 获取分类统计（修复 GROUP BY 问题）
    WITH category_stats AS (
        SELECT 
            c.id,
            c.name,
            c.color,
            c.description,
            COUNT(qp.id) as qa_count
        FROM categories c
        LEFT JOIN qa_pairs qp ON c.id = qp.category_id
        GROUP BY c.id, c.name, c.color, c.description
    )
    SELECT json_agg(
        json_build_object(
            'id', id,
            'name', name,
            'color', color,
            'description', description,
            'qa_count', qa_count
        )
        ORDER BY qa_count DESC, name
    ) INTO categories_json
    FROM category_stats;
    
    -- 获取顾问统计
    WITH advisor_stats AS (
        SELECT advisor, COUNT(*) as advisor_count
        FROM qa_pairs
        WHERE advisor IS NOT NULL AND advisor != ''
        GROUP BY advisor
        ORDER BY COUNT(*) DESC
        LIMIT 10
    )
    SELECT json_agg(
        json_build_object(
            'advisor', advisor,
            'count', advisor_count
        )
    ) INTO advisors_json
    FROM advisor_stats;
    
    -- 获取信心度统计
    SELECT json_build_object(
        'average', ROUND(COALESCE(AVG(confidence), 0)::numeric, 3),
        'high_confidence', COUNT(*) FILTER (WHERE confidence >= 0.8),
        'medium_confidence', COUNT(*) FILTER (WHERE confidence >= 0.5 AND confidence < 0.8),
        'low_confidence', COUNT(*) FILTER (WHERE confidence < 0.5)
    ) INTO confidence_json
    FROM qa_pairs;
    
    -- 获取最近上传记录
    WITH recent_uploads AS (
        SELECT * FROM upload_history
        ORDER BY created_at DESC
        LIMIT 5
    )
    SELECT json_agg(
        json_build_object(
            'id', id,
            'filename', original_name,
            'status', status,
            'processed_count', processed_count,
            'created_at', created_at
        )
        ORDER BY created_at DESC
    ) INTO uploads_json
    FROM recent_uploads;
    
    -- 组合最终结果
    SELECT json_build_object(
        'total_qa', total_qa_count,
        'total_categories', total_categories_count,
        'categories_with_count', COALESCE(categories_json, '[]'::json),
        'top_advisors', COALESCE(advisors_json, '[]'::json),
        'confidence_stats', confidence_json,
        'recent_uploads', COALESCE(uploads_json, '[]'::json)
    ) INTO result;
    
    RETURN result;
END;
$$;

-- 3. 确保分类表的 qa_count 字段正确
-- 更新现有数据
UPDATE categories SET qa_count = (
    SELECT COUNT(*) FROM qa_pairs WHERE qa_pairs.category_id = categories.id
);