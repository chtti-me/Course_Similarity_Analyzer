# Course Similarity Analyzer - 後端

後端由**系統管理人員**在本地或指定主機執行，負責：  
① 排程執行爬取並寫入 Supabase、④ 管理員可透過前端修改資料（由 Supabase RLS 控管）。

## 目錄結構

- `migrations/001_initial.sql`：Supabase 資料表與 RLS，請在**新 Supabase 專案**的 SQL Editor 執行一次。
- `config.py`：設定（可由環境變數或 `.env` 覆寫）。
- `utils.py`：共用工具。
- `supabase_db.py`：Supabase 寫入/查詢。
- `scraper.py`：TIS 網頁爬取，產出課程列表。
- `sync_cli.py`：執行爬取 + embedding + 寫入 Supabase，供排程呼叫。
- `api_server.py`：相似度查詢 API，供前端「③ 相似度查詢/建議」呼叫。

## 1. 建立 Supabase 專案

1. 至 [Supabase](https://supabase.com) 建立新專案（例如「Course Similarity Analyzer」）。
2. 在 **SQL Editor** 貼上並執行 `migrations/001_initial.sql`。
3. 在 **Authentication > Providers** 啟用 Email（或需要的登入方式）。
4. 在 **Table Editor** 的 `profiles` 手動為第一位管理員設定 `role = 'admin'`（該使用者的 `id` 為 Auth 的 user id）。

## 2. 環境變數

在專案目錄建立 `.env`（勿提交版控）：

```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
TIS_BASE_URL=https://tis12.cht.com.tw/jap/tis/
```

可選：`EMBEDDING_MODEL_NAME`、`TOP_K`、`API_HOST`、`API_PORT`。

## 3. 安裝與執行

```bash
pip install -r requirements.txt
```

- **排程同步**（每日執行）：

  ```bash
  python sync_cli.py
  ```

  建議用系統排程（cron / Windows 工作排程）固定時間執行。

- **相似度 API**（供前端 ③ 使用，可常駐或與 sync 同一台）：

  ```bash
  python api_server.py
  ```

  預設 `http://0.0.0.0:8000`。前端需設定與此 API 的網址（例如 `http://主機:8000`）。

## 4. 權限說明

- **① 同步爬取 TIS**：由管理員電腦排程執行 `sync_cli.py`，寫入 Supabase（使用 service_role key）。
- **④ 資料庫瀏覽與修改**：管理員登入前端後，依 RLS 可對 `courses` 做新增/修改/刪除；一般使用者僅可檢視。
