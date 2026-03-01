# 將後端部署到 Railway 指南

本文件說明如何把 **課程相似度 API 後端**（`course_similarity_analyzer_backend`）部署到 [Railway](https://railway.app)，並從 GitHub 自動部署。前端可繼續用 Netlify 或 Zeabur，在 `config.json` 的 `API_BASE_URL` 填 Railway 給的網址即可。

---

## 前置準備

### 1. 程式碼已在 GitHub

專案已推送到 GitHub（例如 `Course_Similarity_Analyzer`）。

### 2. 準備 Supabase 資訊

在 Supabase Dashboard > **Settings** > **API** 取得：

- **SUPABASE_URL**：專案 URL（例如 `https://xxxx.supabase.co`）
- **SUPABASE_SERVICE_ROLE_KEY**：Service Role Key（**私密，勿公開**）

---

## 步驟一：登入 Railway 並建立專案

1. 開啟 [https://railway.app](https://railway.app)，用 GitHub 登入。
2. 點 **「New Project」**（或「Start a New Project」）。
3. 選擇 **「Deploy from GitHub repo」**（或「Deploy from GitHub」）。
4. 授權 Railway 存取 GitHub（若尚未授權）。
5. 選擇你的 **Repository**（例如 `Course_Similarity_Analyzer`）。

Railway 會建立一個新專案並嘗試偵測服務；因為這是 monorepo，我們要手動指定「只部署後端」。

---

## 步驟二：設定「只部署後端」的根目錄

1. 在專案裡會出現一個 **Service**（服務），點進去。
2. 進入 **「Settings」**（設定）分頁。
3. 找到 **「Root Directory」** 或 **「Source」** 區塊。
4. 將 **Root Directory** 設為：
   ```text
   course_similarity_analyzer_backend
   ```
   這樣 Railway 只會以這個資料夾為根目錄建置與執行，不會用到前端的 `course_similarity_analyzer_web`。

儲存後 Railway 可能會自動觸發一次重新部署。

---

## 步驟三：確認建置與啟動指令

1. 仍在 **Settings** 中，找到 **「Build」** / **「Build Command」** 與 **「Start」** / **「Start Command」**（或 **Deploy** 區塊）。
2. 建議設定如下（若 Railway 已自動偵測到 Python 且能成功跑起來，可略過）：

   | 項目 | 值 |
   |------|-----|
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `uvicorn api_server:app --host 0.0.0.0 --port $PORT` |

3. Railway 會自動提供 **PORT** 環境變數，後端已支援讀取 `PORT`，無需再額外設定。

若介面上沒有單獨的 Build/Start 欄位，Railway 可能用 **Nixpacks / Railpack** 自動偵測；只要 Root Directory 正確，通常會自動找到 `requirements.txt` 並用 `Procfile` 或偵測到的指令啟動。若部署失敗，再回來補上上述指令。

---

## 步驟四：設定環境變數

1. 在該 Service 的 **「Variables」**（變數）分頁，新增以下環境變數：

   | 變數名稱 | 值 | 說明 |
   |----------|-----|------|
   | `SUPABASE_URL` | `https://你的專案.supabase.co` | Supabase 專案 URL |
   | `SUPABASE_SERVICE_ROLE_KEY` | 你的 Service Role Key | **務必設為私密（Secret）** |
   | `EMBEDDING_MODEL_NAME` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | 可選，預設即此值 |
   | `TOP_K` | `10` | 可選，預設即此值 |

2. **SUPABASE_SERVICE_ROLE_KEY** 請使用 **Encrypted** / **Secret** 選項，不要以明文暴露在畫面上。

儲存後 Railway 通常會自動重新部署。

---

## 步驟五：產生對外網址並測試

1. 在 Service 的 **「Settings」** 中，找到 **「Networking」** 或 **「Public Networking」**。
2. 點 **「Generate Domain」**（或「Add Public Domain」），Railway 會產生一個網址，例如：
   ```text
   https://xxxxx.up.railway.app
   ```
3. 記下這個網址，即為你的 **API 後端網址**。

測試方式：

- 在瀏覽器開啟：`https://你的網址/`  
  應看到類似 `{"status":"ok","service":"course-similarity-api"}`。
- 或開啟：`https://你的網址/api/health`  
  應看到 `{"status":"ok"}`。

---

## 步驟六：讓前端連到 Railway 後端

若前端部署在 Netlify 或 Zeabur：

1. 開啟 **course_similarity_analyzer_web/Data/config.json**。
2. 將 **API_BASE_URL** 改為 Railway 給的網址（**請用 https**）：
   ```json
   {
     "SUPABASE_URL": "https://你的專案.supabase.co",
     "SUPABASE_ANON_KEY": "你的_anon_key",
     "API_BASE_URL": "https://xxxxx.up.railway.app"
   }
   ```
3. 儲存後 commit 並 push 到 GitHub；若前端也是從 GitHub 自動部署，會自動更新。

---

## 之後：自動部署

- Railway 預設會監聽你連結的 GitHub 分支（例如 `main`）；**每次 push 到該分支，會自動重新建置並部署後端**。
- 若需關閉自動部署，可在該 Service 的 Settings 裡找到 **「Disconnect」** 或 **Deploy** 相關選項，改為手動部署。

---

## 常見問題

### 部署失敗或啟動失敗

- 確認 **Root Directory** 一定是 `course_similarity_analyzer_backend`。
- 到 **「Deployments」** 或 **「Logs」** 查看錯誤訊息；常見為缺少環境變數或 `pip install` 失敗。
- 第一次部署會下載 embedding 模型，時間較久屬正常。

### 前端呼叫 API 出現 CORS 錯誤

- 後端已設定 `allow_origins=["*"]`，理論上任何網域都可呼叫；若仍有問題，請確認部署的是最新版後端。

### 健康檢查 / 根路徑 404

- 後端已提供 `GET /` 回傳 200，Railway 的健康檢查應可通過；若仍出現 404，請確認部署的程式碼包含該段修改並已重新部署。

---

## 完成

後端已部署在 Railway，並可從 GitHub 自動部署。前端只要在 `config.json` 的 `API_BASE_URL` 填上 Railway 網址即可使用。
