# 部署到 Zeabur 完整指南

## 前置準備

### 1. 將專案推送到 GitHub

```bash
cd C:\Course_Similarity_Analyzer
git init
git add .
git commit -m "準備部署到 Zeabur"
git branch -M main
git remote add origin https://github.com/你的帳號/你的專案名稱.git
git push -u origin main
```

### 2. 準備 Supabase 資訊

請準備好以下資訊（在 Supabase Dashboard > Settings > API）：
- `SUPABASE_URL`：你的 Supabase 專案 URL
- `SUPABASE_SERVICE_ROLE_KEY`：Service Role Key（**私密金鑰，不要公開**）

---

## 在 Zeabur 部署後端 API

### 步驟 1：建立新專案

1. 登入 [Zeabur](https://zeabur.com)
2. 點擊「**New Project**」或「**新增專案**」
3. 輸入專案名稱（例如：`course-similarity-analyzer`）

### 步驟 2：連結 GitHub Repository

1. 在專案頁面，點擊「**+ New Service**」或「**新增服務**」
2. 選擇「**GitHub**」或「**Import from Git**」
3. 選擇你的 Repository（儲存庫）
4. 授權 Zeabur 存取你的 GitHub

### 步驟 3：設定後端服務

Zeabur 會自動偵測到這是 Python 專案。如果沒有自動偵測，請手動設定：

#### 方式 A：使用自動偵測（推薦）

Zeabur 應該會自動偵測到 `requirements.txt` 和 `Procfile`，直接按「**Deploy**」即可。

#### 方式 B：手動設定

如果沒有自動偵測，請在服務設定中：

1. **Runtime（執行環境）**：選擇「**Python**」
2. **Root Directory（根目錄）**：填 `course_similarity_analyzer_backend`
3. **Build Command（建置指令）**：
   ```bash
   pip install -r requirements.txt
   ```
4. **Start Command（啟動指令）**：
   ```bash
   uvicorn api_server:app --host 0.0.0.0 --port $PORT
   ```

### 步驟 4：設定環境變數

在服務的「**Environment Variables**」或「**環境變數**」區塊，新增：

| 變數名稱 | 值 | 說明 |
|---------|-----|------|
| `SUPABASE_URL` | `https://你的專案.supabase.co` | Supabase 專案 URL |
| `SUPABASE_SERVICE_ROLE_KEY` | `你的_service_role_key` | **設為 Secret（私密）** |
| `EMBEDDING_MODEL_NAME` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | （可選，預設值） |
| `TOP_K` | `10` | （可選，預設值） |

**重要**：`SUPABASE_SERVICE_ROLE_KEY` 務必設為 **Secret（私密）**，不要公開顯示。

### 步驟 5：部署

1. 點擊「**Deploy**」或「**部署**」
2. 等待建置完成（第一次會比較久，因為要下載 embedding 模型）
3. 部署成功後，會得到一個網址，例如：`https://your-backend-name.zeabur.app`

**請記下這個後端網址，下一步會用到！**

---

## 在 Zeabur 部署前端

### 步驟 1：新增前端服務

1. 在同一個 Zeabur 專案中，點擊「**+ New Service**」
2. 選擇「**Static Site**」或「**靜態網站**」
3. 選擇同一個 GitHub Repository

### 步驟 2：設定前端服務

1. **Root Directory（根目錄）**：填 `course_similarity_analyzer_web`
2. **Output Directory（輸出目錄）**：留空或填 `.`（表示整個資料夾就是網站根目錄）

### 步驟 3：更新前端設定檔

**在部署前，先在本機修改 `config.json`：**

開啟 `course_similarity_analyzer_web/Data/config.json`，把 `API_BASE_URL` 改成你剛剛得到的後端網址：

```json
{
  "SUPABASE_URL": "https://你的專案.supabase.co",
  "SUPABASE_ANON_KEY": "你的_anon_key",
  "API_BASE_URL": "https://your-backend-name.zeabur.app"
}
```

然後 commit 並 push：

```bash
git add course_similarity_analyzer_web/Data/config.json
git commit -m "設定 Zeabur 後端 API_BASE_URL"
git push
```

### 步驟 4：部署前端

1. 回到 Zeabur 前端服務頁面
2. 點擊「**Deploy**」或「**重新部署**」
3. 部署成功後，會得到前端網址，例如：`https://your-frontend-name.zeabur.app`

---

## 測試部署

1. 在瀏覽器開啟前端網址
2. 用你的 Supabase 帳號登入
3. 測試功能：
   - 點擊「④ 資料庫瀏覽」：應該能看到課程資料
   - 點擊「③ 相似度查詢/建議」：輸入關鍵字測試相似度查詢

---

## 常見問題

### Q1：後端啟動失敗，顯示「PORT 未設定」

**解決方法**：確認 `config.py` 已更新為優先讀取 `PORT` 環境變數（已修正）。

### Q2：前端無法連線到後端 API

**檢查項目**：
1. 確認 `config.json` 中的 `API_BASE_URL` 是正確的後端網址
2. 確認後端服務正在運行（在 Zeabur Dashboard 查看 Logs）
3. 確認後端的 CORS 設定允許前端網域（目前設定為 `allow_origins=["*"]`，應該沒問題）

### Q3：後端第一次啟動很慢

**原因**：需要下載 embedding 模型（約 400MB），這是正常的。

### Q4：如何查看後端 Logs（日誌）？

在 Zeabur Dashboard > 後端服務 > 「**Logs**」或「**日誌**」分頁。

---

## 完成！

現在你的系統已經部署到 Zeabur，可以分享前端網址給大家使用了！🎉
