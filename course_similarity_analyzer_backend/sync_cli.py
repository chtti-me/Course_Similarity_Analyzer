"""
同步 CLI：執行爬取並寫入 Supabase
供排程（如 cron / 工作排程器）每日執行。
"""

import logging
import sys
import argparse
import os
import warnings
from sentence_transformers import SentenceTransformer

from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, EMBEDDING_MODEL_NAME, TOP_K
from scraper import scrape_tis, scrape_offline_dir
from supabase_db import get_client, upsert_course, log_sync
from utils import now_iso

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _force_utf8_console():
    """
    Windows 終端機常見會把 UTF-8 當成其他編碼解讀，導致中文變成亂碼。
    這裡嘗試把 stdout/stderr 強制改成 UTF-8，讓 CLI 訊息正常顯示。
    """
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    _force_utf8_console()

    # 盡量降低第三方套件的英文提示/雜訊（避免干擾初學者）
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    warnings.filterwarnings(
        "ignore",
        message=r"You are sending unauthenticated requests to the HF Hub.*",
    )
    try:
        # transformers 內建的 log 控制（若版本不支援就略過）
        from transformers.utils import logging as tf_logging  # type: ignore

        tf_logging.set_verbosity_error()
    except Exception:
        pass

    # 這些套件常輸出大量英文細節（下載、載入進度），對初學者干擾大；預設先壓到 ERROR
    for noisy in ("httpx", "sentence_transformers", "huggingface_hub"):
        logging.getLogger(noisy).setLevel(logging.ERROR)

    ap = argparse.ArgumentParser(description="同步爬取並寫入 Supabase（支援離線 HTML 資料夾模式）")
    ap.add_argument("--offline-dir", default="", help="離線 HTML 資料夾路徑（含 .html/.htm），用於測試")
    ap.add_argument("--offline-campus", default="離線", help="離線模式的校區標記（預設：離線）")
    ap.add_argument("--dry-run", action="store_true", help="只爬取與計算 embedding，不寫入 Supabase（用於測試）")
    args = ap.parse_args()

    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        logger.error("請設定環境變數 SUPABASE_URL、SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)

    sb = None
    if not args.dry_run:
        sb = get_client()

    if args.offline_dir:
        logger.info("使用離線模式，資料夾：%s", args.offline_dir)
        courses = scrape_offline_dir(args.offline_dir, campus=args.offline_campus)
    else:
        courses = scrape_tis()

    if not courses:
        if sb:
            log_sync(sb, "ok", "無新課程或爬取為空", 0)
        logger.info("無課程可寫入")
        return

    logger.info("載入 embedding 模型: %s", EMBEDDING_MODEL_NAME)

    # Hugging Face 下載模型時，可能會印出英文警告/進度條（通常寫到 stderr）。
    # 這裡用「過濾 stderr」的方式，只濾掉特定警告，避免終端機被英文洗版。
    class _FilteredStderr:
        def __init__(self, real):
            self._real = real

        def write(self, s):
            if not s:
                return 0
            # 只過濾這個常見英文警告（不影響其他真正錯誤）
            if "unauthenticated requests to the HF Hub" in s:
                return len(s)
            return self._real.write(s)

        def flush(self):
            return self._real.flush()

    _real_stderr = sys.stderr
    try:
        sys.stderr = _FilteredStderr(_real_stderr)
        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    finally:
        sys.stderr = _real_stderr

    changed = 0
    for c in courses:
        # 用標題＋簡述做 embedding 文字
        text = f"{c.get('title') or ''} {c.get('description') or ''}".strip() or c.get("id", "")
        try:
            emb = model.encode(text, normalize_embeddings=True)
            c["embedding"] = emb
            c["embedding_dim"] = len(emb)
        except Exception as e:
            logger.warning("embedding 失敗 %s: %s", c.get("id"), e)
            c["embedding"] = None
            c["embedding_dim"] = None
        if sb:
            _, is_changed = upsert_course(sb, c)
            if is_changed:
                changed += 1

    if sb:
        log_sync(sb, "ok", None, changed)
        logger.info("同步完成，本次寫入/更新 %d 筆", changed)
    else:
        logger.info("dry-run 完成：共處理 %d 筆（未寫入 Supabase）", len(courses))


if __name__ == "__main__":
    main()
