-- 更新 match_courses 函數：包含規劃中課程（status='planning'）
-- 規劃中課程可能沒有 start_date，需要特別處理

CREATE OR REPLACE FUNCTION public.match_courses(
    query_embedding extensions.vector(384),
    start_from TEXT,
    start_to TEXT,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    id TEXT,
    title TEXT,
    start_date TEXT,
    level TEXT,
    status TEXT,
    campus TEXT,
    similarity FLOAT
)
LANGUAGE sql STABLE
AS $$
    SELECT
        c.id,
        c.title,
        c.start_date,
        c.level,
        c.status,
        c.campus,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM public.courses c
    WHERE c.embedding IS NOT NULL
      AND (
          -- 已確定開班的課程：檢查日期範圍
          (c.status != 'planning' AND 
           (start_from IS NULL OR c.start_date >= start_from) AND
           (start_to IS NULL OR c.start_date <= start_to))
          OR
          -- 規劃中的課程：不限制日期，全部納入
          (c.status = 'planning')
      )
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
$$;
