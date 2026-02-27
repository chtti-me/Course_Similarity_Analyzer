"""
後端設定：Supabase、TIS、Embedding
由環境變數或 .env 覆寫，勿將 service_role key 提交版控。
"""

import os
from pathlib import Path

# 從 .env 讀取（若存在）
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# =========================
# Supabase（必填）
# =========================
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

# =========================
# TIS URL
# =========================
TIS_BASE_URL = os.environ.get("TIS_BASE_URL", "https://<YOUR_TIS_HOST>/")
TIS_PAGES = {
    "院本部": os.environ.get("TIS_PAGE_院本部", f"{TIS_BASE_URL.rstrip('/')}/classDoneQueryByPro.jsp?department=P&dtype1=C&dtype2=AD"),
    "臺中所": os.environ.get("TIS_PAGE_臺中所", f"{TIS_BASE_URL.rstrip('/')}/classDoneQueryByPro.jsp?department=T&dtype1=C&dtype2=AD"),
    "高雄所": os.environ.get("TIS_PAGE_高雄所", f"{TIS_BASE_URL.rstrip('/')}/classDoneQueryByPro.jsp?department=K&dtype1=C&dtype2=AD"),
}

# =========================
# Embedding
# =========================
EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL_NAME", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
TOP_K = int(os.environ.get("TOP_K", "10"))

# =========================
# 相似度 API（給前端 ③ 呼叫，可選）
# =========================
API_HOST = os.environ.get("API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("API_PORT", "8000"))
