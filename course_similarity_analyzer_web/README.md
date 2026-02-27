# Course Similarity Analyzer - 前端

一般使用者可使用：② 登錄規劃中課程（檢視）、③ 相似度查詢/建議、④ 資料庫瀏覽（檢視）。  
管理員另可：① 同步爬取 TIS（檢視同步紀錄）、④ 新增/編輯/刪除課程、② 新增/編輯/刪除規劃中課程。

## 設定

1. 複製 `Data/config.json` 並填寫：
   - **SUPABASE_URL**：Supabase 專案 URL（例如 `https://xxxx.supabase.co`）
   - **SUPABASE_ANON_KEY**：Supabase 專案的 anon public key
   - **API_BASE_URL**：後端相似度 API 網址（例如 `http://localhost:8000`，需與後端 `api_server.py` 一致）

2. 預覽方式（依專案規則）：
   - 在 VS Code 安裝 **Live Server**
   - 右鍵 `index.html` → **Open with Live Server**

## 權限說明

- **① 同步爬取 TIS**：僅管理員可見；實際同步由後端排程執行 `sync_cli.py`，此頁僅顯示最近同步紀錄。
- **② 登錄規劃中課程**：所有人可檢視；管理員可新增/編輯/刪除。
- **③ 相似度查詢/建議**：所有人可用；會呼叫後端 `API_BASE_URL/api/similarity`。
- **④ 資料庫瀏覽**：所有人可檢視；管理員可刪除（編輯可再擴充）。

第一位管理員需在 Supabase 後台將該使用者的 `profiles.role` 設為 `admin`（先註冊/登入一次取得 user id，再在 Table Editor 的 `profiles` 修改該筆的 `role`）。
