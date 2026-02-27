"""
Supabase 資料層：課程 upsert、查詢、同步紀錄
使用 service_role key，供 sync_cli 與 API 使用。
"""

import uuid
from typing import List, Tuple, Optional

from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
from utils import compute_content_hash, now_iso


def get_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("請設定 SUPABASE_URL 與 SUPABASE_SERVICE_ROLE_KEY")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def _course_to_row(course: dict) -> dict:
    """將課程 dict 轉成 Supabase 可寫入的 row（embedding 轉 list）。"""
    row = {
        "id": course["id"],
        "source": course.get("source"),
        "status": course.get("status"),
        "campus": course.get("campus"),
        "system": course.get("system"),
        "category": course.get("category"),
        "class_code": course.get("class_code"),
        "title": course.get("title") or "",
        "start_date": course.get("start_date"),
        "days": course.get("days"),
        "description": course.get("description"),
        "audience": course.get("audience"),
        "level": course.get("level"),
        "instructor": course.get("instructor"),
        "url": course.get("url"),
        "content_hash": course.get("content_hash"),
        "embedding_dim": course.get("embedding_dim"),
        "created_at": course.get("created_at"),
        "updated_at": course.get("updated_at"),
    }
    emb = course.get("embedding")
    if emb is not None:
        if hasattr(emb, "tolist"):
            row["embedding"] = emb.tolist()
        elif isinstance(emb, list):
            row["embedding"] = emb
        else:
            row["embedding"] = list(emb)
    return row


def upsert_course(sb: Client, course: dict) -> Tuple[str, bool]:
    """
    回傳 (id, 是否有變更)。
    若 content_hash 相同則不寫入。
    """
    now = now_iso()
    if not course.get("id"):
        if course.get("source") == "tis" and course.get("class_code"):
            course["id"] = f"tis:{course['class_code']}"
        else:
            course["id"] = f"manual:{uuid.uuid4().hex}"
    course["content_hash"] = compute_content_hash(course)

    # 查既有
    if course.get("source") == "tis" and course.get("class_code"):
        r = sb.table("courses").select("id,content_hash,created_at").eq("source", course["source"]).eq("class_code", course["class_code"]).execute()
    else:
        r = sb.table("courses").select("id,content_hash,created_at").eq("id", course["id"]).execute()

    existing = r.data[0] if r.data else None
    if existing and existing.get("content_hash") == course["content_hash"]:
        return existing["id"], False

    if existing:
        course["created_at"] = existing["created_at"]
    else:
        course["created_at"] = now
    course["updated_at"] = now

    row = _course_to_row(course)
    sb.table("courses").upsert(row, on_conflict="id").execute()
    return course["id"], True


def list_all(sb: Client) -> List[dict]:
    r = sb.table("courses").select("*").order("start_date").execute()
    return r.data or []


def get_courses_in_window(sb: Client, start_iso: str, end_iso: str) -> List[dict]:
    r = (
        sb.table("courses")
        .select("*")
        .not_.is_("start_date", "null")
        .gte("start_date", start_iso)
        .lte("start_date", end_iso)
        .order("start_date")
        .execute()
    )
    return r.data or []


def get_planning_courses(sb: Client) -> List[dict]:
    r = sb.table("courses").select("*").eq("status", "planning").order("updated_at", desc=True).execute()
    return r.data or []


def log_sync(sb: Client, status: str, message: Optional[str] = None, courses_upserted: int = 0):
    sb.table("sync_log").insert({
        "status": status,
        "message": message,
        "courses_upserted": courses_upserted,
    }).execute()
