-- 新增導師欄位
ALTER TABLE public.courses ADD COLUMN IF NOT EXISTS instructor TEXT;
