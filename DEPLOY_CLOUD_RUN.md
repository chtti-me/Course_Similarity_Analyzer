# 將後端部署到 Google Cloud Run 指南

本文件說明如何把 **課程相似度 API 後端**（`course_similarity_analyzer_backend`）部署到 [Google Cloud Run](https://cloud.google.com/run)。Cloud Run 依請求計費、可設較大記憶體（建議 2GB 以上以載入 embedding 模型），並支援從本機或 CI 用 `gcloud` 指令部署。

---

## 前置準備

### 1. 本機已安裝 gcloud CLI

- 若尚未安裝：到 [Google Cloud SDK 下載頁](https://cloud.google.com/sdk/docs/install) 安裝並完成 `gcloud init`。
- 終端機執行 `gcloud --version` 確認可用。

### 2. 已建立 GCP 專案並啟用計費

- 到 [Google Cloud Console](https://console.cloud.google.com/) 建立專案（或使用既有專案）。
- Cloud Run 需啟用計費帳戶，但提供 [免費額度](https://cloud.google.com/run/pricing#free-tier)，小流量通常在免費額度內。

### 3. 啟用必要 API

在終端機執行（將 `YOUR_PROJECT_ID` 換成你的專案 ID）：

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### 4. 準備 Supabase 資訊

- **SUPABASE_URL**：Supabase 專案 URL（例如 `https://xxxx.supabase.co`）
- **SUPABASE_SERVICE_ROLE_KEY**：Service Role Key（**私密，勿提交版控**）

---

## 步驟一：在後端目錄建置並部署

專案為 monorepo，後端在 `course_similarity_analyzer_backend`。請在 **專案根目錄**（`Course_Similarity_Analyzer`）執行：

```bash
gcloud run deploy course-similarity-api \
  --source ./course_similarity_analyzer_backend \
  --region asia-east1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --set-env-vars "SUPABASE_URL=你的_SUPABASE_URL,SUPABASE_SERVICE_ROLE_KEY=你的_SERVICE_ROLE_KEY"
```

說明：

- **--source**：指定後端子目錄，Cloud Build 會用該目錄內的 `Dockerfile` 建置映像並部署。
- **--region**：可改為離你較近的區域（例如 `us-central1`）。
- **--memory 2Gi**：建議至少 2GB，以順利載入 sentence-transformers 模型。
- **--allow-unauthenticated**：允許未登入 GCP 的使用者呼叫 API（前端才能連）。若只允許登入身分呼叫，可改為不加此參數並在 GCP 設定 IAM。
- **--set-env-vars**：必填的 Supabase 變數；請把 `你的_SUPABASE_URL`、`你的_SERVICE_ROLE_KEY` 換成實際值。

若不想在指令列寫私密金鑰，可先不設 `SUPABASE_SERVICE_ROLE_KEY`，部署完成後到 Console 補上（見步驟三）。

第一次部署會上傳程式碼、建置 Docker 映像（下載 Python 與 sentence-transformers 等，可能需數分鐘），完成後會輸出服務網址，例如：

```text
Service [course-similarity-api] revision has been deployed and is serving 100 percent of traffic.
Service URL: https://course-similarity-api-xxxxx-as.a.run.app
```

請記下此 **Service URL**，即為你的後端 API 網址。

---

## 步驟二：驗證部署

在瀏覽器開啟：

- `https://你的-Service-URL/`  
  應看到：`{"status":"ok","service":"course-similarity-api"}`
- `https://你的-Service-URL/api/health`  
  應看到：`{"status":"ok"}`

若出現 502 或 503，請到 Cloud Console > Cloud Run > 該服務 > **Logs** 查看錯誤（常見為環境變數未設或記憶體不足）。

---

## 步驟三：用 Console 設定或修改環境變數（可選）

若部署時未設定環境變數，或之後要改：

1. 開啟 [Cloud Run 主頁](https://console.cloud.google.com/run)。
2. 點選服務名稱（例如 `course-similarity-api`）。
3. 上方 **「編輯與部署新修訂版本」**。
4. 在 **「變數與密碼」** 分頁新增：
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`（建議用「參考密碼」連結 Secret Manager，較安全）
   - 可選：`EMBEDDING_MODEL_NAME`、`TOP_K`
5. **「部署」** 儲存。

若要提高記憶體，在同一畫面 **「容器」** 區塊可調整記憶體（例如 2GB、4GB）。

---

## 步驟四：讓前端連到 Cloud Run 後端

1. 開啟 **course_similarity_analyzer_web/Data/config.json**。
2. 將 **API_BASE_URL** 改為 Cloud Run 的 Service URL（**請用 https**）：

```json
{
  "SUPABASE_URL": "https://你的專案.supabase.co",
  "SUPABASE_ANON_KEY": "你的_anon_key",
  "API_BASE_URL": "https://course-similarity-api-xxxxx-as.a.run.app"
}
```

3. 儲存後 commit 並 push；若前端由 Netlify/Zeabur 自動部署，會自動更新。

---

## 之後：重新部署

程式碼或 `Dockerfile` 修改後，在專案根目錄再次執行：

```bash
gcloud run deploy course-similarity-api \
  --source ./course_similarity_analyzer_backend \
  --region asia-east1
```

已設定的環境變數、記憶體會保留；若要一併修改，可加上 `--memory`、`--set-env-vars` 或 `--update-env-vars`。

---

## 使用 Secret Manager 存放金鑰（建議正式環境）

若要避免在指令列或 Console 直接貼上 Service Role Key：

1. 在 GCP 建立 Secret（例如名稱 `supabase-service-role-key`），將金鑰內容存入。
2. 部署時改為：

```bash
gcloud run deploy course-similarity-api \
  --source ./course_similarity_analyzer_backend \
  --region asia-east1 \
  --memory 2Gi \
  --set-env-vars "SUPABASE_URL=你的_SUPABASE_URL" \
  --set-secrets "SUPABASE_SERVICE_ROLE_KEY=supabase-service-role-key:latest"
```

或於 Console 的「變數與密碼」中選擇「參考密碼」並指向該 Secret。

---

## 常見問題

### 建置或啟動失敗、記憶體不足

- 到 Cloud Run > 該服務 > **Logs** 查看錯誤。
- 確認 **記憶體至少 2Gi**；若模型載入仍失敗，可試 4Gi。

### 冷啟動較慢

- Cloud Run 在無請求時會縮到零，第一個請求會冷啟動（載入模型可能需 30 秒～1 分鐘）。可考慮設定「最小執行個數 1」以保持一個實例常駐（會增加費用）。

### 免費額度

- [Cloud Run 定價與免費額度](https://cloud.google.com/run/pricing#free-tier) 每月有免費請求數與 vCPU/記憶體時數，小流量通常在免費範圍內；超過後依用量計費。

---

## 完成

後端已部署到 Google Cloud Run，前端在 `config.json` 的 `API_BASE_URL` 改為 Cloud Run 的 Service URL 即可使用。
