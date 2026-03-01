# 將前端部署到 Netlify 指南

**說明**：Netlify 只負責放「前端」靜態網站，後端 API 仍須部署在別處（例如 Zeabur）。前端會透過 `Data/config.json` 的 `API_BASE_URL` 連到後端。

---

## 前置條件

1. **後端已部署**  
   例如已照 [DEPLOY_ZEABUR.md](DEPLOY_ZEABUR.md) 把 API 部署到 Zeabur，並取得後端網址（如 `https://your-backend-name.zeabur.app`）。

2. **程式碼已在 GitHub**  
   專案已 push 到 GitHub，且根目錄有 `netlify.toml`（已設定好前端目錄）。

---

## 步驟一：設定前端的後端網址

在部署到 Netlify 前，先讓前端知道要連哪個 API：

1. 開啟 `course_similarity_analyzer_web/Data/config.json`。
2. 將 `API_BASE_URL` 改為你的後端網址（**請用 https**，避免混合內容問題）：

```json
{
  "SUPABASE_URL": "https://你的專案.supabase.co",
  "SUPABASE_ANON_KEY": "你的_anon_key",
  "API_BASE_URL": "https://your-backend-name.zeabur.app"
}
```

3. 儲存後 commit 並 push 到 GitHub：

```bash
git add course_similarity_analyzer_web/Data/config.json
git commit -m "設定 Netlify 用後端 API 網址"
git push
```

---

## 步驟二：在 Netlify 建立站點並連結 GitHub

1. 登入 [Netlify](https://www.netlify.com/)。
2. 點 **「Add new site」→「Import an existing project」**。
3. 選 **「GitHub」**，授權 Netlify 存取你的 GitHub。
4. 選擇此專案的 **Repository**（例如 `Course_Similarity_Analyzer`）。

---

## 步驟三：確認建置設定（通常不必改）

專案根目錄已有 `netlify.toml`，Netlify 會自動套用：

- **Base directory**：`course_similarity_analyzer_web`
- **Publish directory**：`.`（即該資料夾為網站根目錄）
- **Build command**：留空（純靜態，無需建置）

若 Netlify 畫面有顯示這些欄位，請確認與上述一致；若已自動帶入，可直接下一步。

---

## 步驟四：部署

1. 點 **「Deploy site」**（或「Deploy」）。
2. 等待部署完成，Netlify 會給你一個網址，例如：  
   `https://隨機名稱.netlify.app`  
   之後可在 **Site settings → Domain management** 改自訂網域。

---

## 步驟五：測試

1. 在瀏覽器開啟 Netlify 給的網址。
2. 使用 Supabase 帳號登入。
3. 測試「③ 相似度查詢/建議」：應能連到你在 Zeabur 的後端 API。

若無法連線，請檢查：

- `config.json` 的 `API_BASE_URL` 是否為 **https** 且網址正確。
- 後端服務是否正常（到 Zeabur 看 Logs）。
- 後端 CORS 為 `allow_origins=["*"]`，Netlify 網域可正常呼叫。

---

## 選擇 Zeabur 或 Netlify 的差異

| 項目       | Zeabur 前端           | Netlify 前端        |
|------------|------------------------|----------------------|
| 部署位置   | 與後端同專案           | 獨立於後端           |
| 網址       | `xxx.zeabur.app`       | `xxx.netlify.app`    |
| 後端       | 同專案內另一服務       | 需自行設定（如 Zeabur）|
| 設定方式   | 改 `config.json` 後 push | 同上                 |

兩種方式前端程式與 `config.json` 用法相同，差別只在「要把前端部署到哪一個平台」。若要改回 Zeabur 前端，只要在 Zeabur 再建一個靜態網站服務即可。

---

## 完成

前端已可在 Netlify 上運行，並透過 `API_BASE_URL` 連到你在 Zeabur（或其它地方）的後端。
