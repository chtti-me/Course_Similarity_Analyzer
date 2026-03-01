# 課程相似度 API 後端 - 供 Google Cloud Run 等容器環境使用
# Cloud Run 會注入 PORT 環境變數（預設 8080）

FROM python:3.11-slim

WORKDIR /app

# 安裝依賴（sentence-transformers 會拉取較多套件，建置時間較長）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製後端程式碼
COPY . .

# Cloud Run 會對 GET / 做健康檢查，後端已提供根路徑 200
EXPOSE 8080
CMD uvicorn api_server:app --host 0.0.0.0 --port ${PORT:-8080}
