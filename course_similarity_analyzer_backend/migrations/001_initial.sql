-- Course Similarity Analyzer：Supabase 初始結構
-- 請在 Supabase Dashboard > SQL Editor 執行此檔（或建立新專案後執行）

-- 啟用 pgvector（用於相似度查詢）
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

-- =========================
-- 課程表（與 MVP 對齊，embedding 改為 vector 型別）
-- =========================
CREATE TABLE IF NOT EXISTS public.courses (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    status TEXT NOT NULL,

    campus TEXT,
    system TEXT,
    category TEXT,

    class_code TEXT,
    title TEXT NOT NULL,
    start_date TEXT,
    days INTEGER,

    description TEXT,
    audience TEXT,
    level TEXT,
    url TEXT,

    content_hash TEXT NOT NULL,

    -- 使用 pgvector，維度與 paraphrase-multilingual-MiniLM-L12-v2 一致 (384)
    embedding extensions.vector(384),
    embedding_dim INTEGER,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_courses_source_class
    ON public.courses(source, class_code)
    WHERE class_code IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_courses_start_date ON public.courses(start_date);
CREATE INDEX IF NOT EXISTS ix_courses_status ON public.courses(status);

-- =========================
-- 同步紀錄（給後台 ① 顯示最後同步狀態）
-- =========================
CREATE TABLE IF NOT EXISTS public.sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT NOT NULL,
    message TEXT,
    courses_upserted INTEGER DEFAULT 0
);

-- =========================
-- 使用者角色（Supabase Auth 搭配）
-- =========================
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 僅允許透過 service_role 或 trigger 寫入 profiles
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- =========================
-- RLS：courses
-- 所有人（含 anon）可讀；寫入僅 service_role（後端 sync_cli / 管理員透過 API）
-- =========================
ALTER TABLE public.courses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "courses_select_all"
    ON public.courses FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "courses_insert_service"
    ON public.courses FOR INSERT
    TO service_role
    WITH CHECK (true);

CREATE POLICY "courses_update_service"
    ON public.courses FOR UPDATE
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "courses_delete_service"
    ON public.courses FOR DELETE
    TO service_role
    USING (true);

-- 管理員（authenticated + profiles.role = admin）可修改課程
CREATE POLICY "courses_admin_all"
    ON public.courses FOR ALL
    TO authenticated
    USING (
        EXISTS (SELECT 1 FROM public.profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin')
    )
    WITH CHECK (
        EXISTS (SELECT 1 FROM public.profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin')
    );

-- =========================
-- RLS：sync_log
-- =========================
ALTER TABLE public.sync_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "sync_log_select_all"
    ON public.sync_log FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "sync_log_insert_service"
    ON public.sync_log FOR INSERT
    TO service_role
    WITH CHECK (true);

-- =========================
-- RLS：profiles（使用者只能讀自己的）
-- =========================
CREATE POLICY "profiles_select_own"
    ON public.profiles FOR SELECT
    TO authenticated
    USING (auth.uid() = id);

-- 管理員由 service_role 或後台建立，不開放一般使用者寫入
CREATE POLICY "profiles_insert_service"
    ON public.profiles FOR INSERT
    TO service_role
    WITH CHECK (true);

CREATE POLICY "profiles_update_service"
    ON public.profiles FOR UPDATE
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =========================
-- 相似度查詢 RPC（供後端 API 或 Edge Function 呼叫）
-- =========================
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
    similarity FLOAT
)
LANGUAGE sql STABLE
AS $$
    SELECT
        c.id,
        c.title,
        c.start_date,
        c.level,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM public.courses c
    WHERE c.embedding IS NOT NULL
      AND (start_from IS NULL OR c.start_date >= start_from)
      AND (start_to IS NULL OR c.start_date <= start_to)
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- 新使用者註冊時自動建立 profile（role 預設 user）
-- 第一位管理員請在 Table Editor 將該使用者的 profiles.role 改為 'admin'
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    INSERT INTO public.profiles (id, role)
    VALUES (NEW.id, 'user')
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
