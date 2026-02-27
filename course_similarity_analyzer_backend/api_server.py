"""
相似度查詢 API：供前端 ③ 呼叫
需在可連線 Supabase 與載入 embedding 模型的環境執行（可與 sync 同一台或獨立）。
"""

import logging
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from sentence_transformers import SentenceTransformer
from supabase import create_client

from config import (
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY,
    EMBEDDING_MODEL_NAME,
    TOP_K,
    API_HOST,
    API_PORT,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="課程相似度 API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SimilarityRequest(BaseModel):
    query: str
    level: str | None = None
    n_days_back: int = 100
    n_days_forward: int = 100
    top_k: int = 10
    min_similarity: float = 0.0  # 最小相似度門檻（0.0-1.0，例如 0.6 表示 60%）


class EmbeddingRequest(BaseModel):
    title: str
    description: str | None = None
    audience: str | None = None


# 啟動時載入模型與 Supabase（可改為 lazy load）
_model = None
_sb = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def get_supabase():
    global _sb
    if _sb is None:
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise ValueError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY 未設定")
        _sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return _sb


@app.post("/api/similarity")
def similarity(req: SimilarityRequest):
    """依查詢文字回傳相似課程（歷史 N 天 + 未來 M 天內）。"""
    try:
        today = datetime.utcnow().date()
        start_from = (today - timedelta(days=req.n_days_back)).isoformat()
        start_to = (today + timedelta(days=req.n_days_forward)).isoformat()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"日期計算錯誤: {e}")

    text = req.query.strip()
    if not text:
        return {"results": [], "message": "查詢為空"}

    model = get_model()
    sb = get_supabase()
    try:
        emb = model.encode(text, normalize_embeddings=True)
        emb_list = emb.tolist()
    except Exception as e:
        logger.exception("embedding 失敗")
        raise HTTPException(status_code=500, detail=f"embedding 失敗: {e}")

    try:
        # 先查詢較多筆（最多 100 筆），以便後續過濾
        r = sb.rpc(
            "match_courses",
            {
                "query_embedding": emb_list,
                "start_from": start_from,
                "start_to": start_to,
                "match_count": min(req.top_k * 2, 100),  # 查詢更多筆，以便過濾後仍有足夠結果
            },
        ).execute()
        rows = r.data or []
    except Exception as e:
        logger.exception("RPC match_courses 失敗")
        raise HTTPException(status_code=500, detail=f"查詢失敗: {e}")

    # 過濾：最小相似度門檻
    if req.min_similarity > 0:
        rows = [x for x in rows if (x.get("similarity") or 0.0) >= req.min_similarity]

    # 可選：依 level 過濾
    if req.level and req.level.strip():
        rows = [x for x in rows if (x.get("level") or "").strip() == req.level.strip()]

    # 只取前 top_k 筆
    return {"results": rows[: req.top_k]}


@app.post("/api/generate-embedding")
def generate_embedding(req: EmbeddingRequest):
    """
    為規劃中課程生成 embedding。
    前端在新增/更新規劃中課程時，應呼叫此端點來生成 embedding。
    """
    title = req.title.strip()
    description = (req.description or "").strip()
    audience = (req.audience or "").strip()
    
    if not title:
        raise HTTPException(status_code=400, detail="課程名稱（title）為必填")
    
    # 組合文字：標題 + 說明 + 對象
    text = f"{title} {description} {audience}".strip()
    
    model = get_model()
    try:
        emb = model.encode(text, normalize_embeddings=True)
        emb_list = emb.tolist()
        return {"embedding": emb_list, "embedding_dim": len(emb_list)}
    except Exception as e:
        logger.exception("embedding 生成失敗")
        raise HTTPException(status_code=500, detail=f"embedding 生成失敗: {e}")


@app.get("/api/health")
def health():
    return {"status": "ok"}


def run():
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)


if __name__ == "__main__":
    run()
