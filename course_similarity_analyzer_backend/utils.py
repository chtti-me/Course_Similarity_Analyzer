"""
共用工具（與 MVP 一致）
"""

import re
import hashlib
import json
from datetime import datetime


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


ROC_YEAR_OFFSET = 1911


def roc_to_iso(roc_year: int, mmdd: str):
    try:
        yyyy = roc_year + ROC_YEAR_OFFSET
        mm, dd = mmdd.split("/")
        return f"{yyyy:04d}-{int(mm):02d}-{int(dd):02d}"
    except Exception:
        return None


def normalize_for_hash(data: dict) -> str:
    keys = [
        "campus", "system", "category",
        "class_code", "title", "start_date",
        "days", "description", "audience",
        "level", "instructor", "url", "source", "status"
    ]
    payload = {k: (data.get(k) or "") for k in keys}
    for k, v in payload.items():
        if isinstance(v, str):
            payload[k] = clean_text(v)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def compute_content_hash(data: dict) -> str:
    normalized = normalize_for_hash(data).encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def now_iso():
    return datetime.utcnow().isoformat(timespec="seconds")
