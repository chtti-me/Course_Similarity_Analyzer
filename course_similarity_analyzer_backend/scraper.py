"""
TIS 網頁爬取：取得課程清單
產出課程 dict 列表，供 sync_cli 寫入 Supabase。
可依實際 TIS 頁面結構調整選擇器。
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import TIS_PAGES, TIS_BASE_URL
from utils import clean_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _force_utf8_console():
    """
    Windows 終端機常見會把 UTF-8 當成其他編碼解讀，導致中文變成亂碼。
    這裡嘗試把 stdout/stderr 強制改成 UTF-8，讓 CLI 訊息正常顯示。
    """
    try:
        import sys

        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        # 失敗就忽略，不要影響主流程
        pass


def _fetch_html(url: str) -> str:
    """取得 HTML 字串；若 URL 為佔位符則回傳空字串。"""
    if "<YOUR_TIS_HOST>" in url or not url.strip() or url.strip().endswith("/"):
        logger.warning("TIS URL 尚未設定，跳過: %s", url[:80])
        return ""
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logger.exception("取得頁面失敗 %s: %s", url, e)
        return ""


def _parse_roc_date(roc_date_str: str) -> str:
    """
    解析民國年日期格式（例如：115 03/10 → 2026-03-10）
    支援格式：
    - "115 03/10" 或 "115<br>03/10"
    - "115年03月10日"
    """
    if not roc_date_str:
        return None
    
    # 清理文字（移除 <br> 等標籤）
    text = re.sub(r"<[^>]+>", " ", roc_date_str)
    text = clean_text(text)
    
    # 嘗試匹配 "115 03/10" 或 "115年03月10日"
    match = re.search(r"(\d{3})\s*(?:年)?\s*(\d{1,2})\s*[/月]\s*(\d{1,2})", text)
    if match:
        roc_year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        iso_year = roc_year + 1911
        return f"{iso_year:04d}-{month:02d}-{day:02d}"
    
    return None


def _parse_courses_from_page(html: str, campus: str, page_url: str) -> List[Dict[str, Any]]:
    """
    從單一 TIS 頁面解析課程列表。
    根據實際 TIS 頁面結構解析：
    - 班代號（class_code）：班名欄位中的連結文字（例如 CT21YT009）
    - 班名（title）：班名欄位中粗體 span 的文字（例如 生成式人工智慧實戰初階班）
    - 校區（campus）：從參數或頁面標題推斷
    - 導師（instructor）：導師欄位，去除電話號碼
    - 開班日期（start_date）：期間欄位，轉換民國年為 ISO 格式
    - 對象（audience）：對象欄位，提取「對象：」後面的文字
    - 難易度（level）：目前 TIS 頁面沒有此欄位，留空
    """
    courses = []
    if not html:
        return courses
    soup = BeautifulSoup(html, "html.parser")
    
    # 如果沒有指定校區，嘗試從頁面標題提取
    if not campus or campus == "離線":
        h2 = soup.find("h2")
        if h2:
            h2_text = clean_text(h2.get_text() or "")
            if "臺中所" in h2_text or "台中所" in h2_text:
                campus = "台中所"
            elif "高雄所" in h2_text:
                campus = "高雄所"
            elif "院本部" in h2_text or "本部" in h2_text:
                campus = "院本部"
    
    # 這裡同時支援：
    # - 線上 URL（例如 https://.../xxx.jsp）
    # - 離線頁面標記（例如 offline:C:\path\to\page.html）
    if page_url.startswith("http://") or page_url.startswith("https://"):
        base_url = page_url.rsplit("/", 1)[0] + "/"
    else:
        base_url = ""

    # 尋找表格（TIS 頁面通常只有一個主要表格）
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 2:  # 至少要有表頭和一行資料
            continue
        
        # 尋找表頭行（通常有背景色或特定 class）
        header_row = None
        header_cols = []
        for row in rows:
            ths = row.find_all("th")
            if len(ths) >= 5:  # 至少要有 5 個欄位才可能是表頭
                header_row = row
                header_cols = [clean_text(th.get_text() or "") for th in ths]
                break
        
        if not header_row:
            continue
        
        # 根據實際 TIS 表格結構，欄位順序是：
        # 序號、班名、期間、對象/混成班e-Learning課程、導師、預調人數、報名人數、確認人數、地點、報名
        # 我們需要的欄位索引：
        col_class_name = 1  # 班名欄位（包含班代號連結和實際班名）
        col_period = 2      # 期間欄位
        col_audience = 3    # 對象欄位
        col_instructor = 4  # 導師欄位
        
        # 解析資料列（跳過表頭）
        for row in rows:
            if row == header_row:
                continue
            
            cells = row.find_all("td")
            if len(cells) < 5:  # 至少要有 5 個欄位
                continue
            
            # 1. 解析班名欄位（第二欄，索引 1）
            class_code = None
            title = None
            url = page_url
            
            class_name_cell = cells[col_class_name] if len(cells) > col_class_name else None
            if class_name_cell:
                # 班代號：從連結文字提取
                link = class_name_cell.find("a", href=True)
                if link:
                    class_code = clean_text(link.get_text() or "")
                    href = link.get("href", "")
                    url = urljoin(base_url, href) if base_url and not href.startswith("http") else href
                
                # 班名：從粗體 span 提取（通常是 font-weight:600 或 <b> 標籤）
                bold_span = class_name_cell.find("span", style=lambda x: x and "font-weight:600" in x)
                if not bold_span:
                    bold_span = class_name_cell.find("b")
                if not bold_span:
                    bold_span = class_name_cell.find("strong")
                
                if bold_span:
                    title = clean_text(bold_span.get_text() or "")
                else:
                    # 如果沒有粗體，嘗試提取所有文字，排除班代號和「純直播課程」等標籤
                    all_text = clean_text(class_name_cell.get_text() or "")
                    # 移除班代號
                    if class_code:
                        all_text = all_text.replace(class_code, "").strip()
                    # 移除常見標籤文字
                    all_text = re.sub(r"純直播課程|混成班|e-Learning", "", all_text).strip()
                    if all_text and len(all_text) > 2:
                        title = all_text
            
            # 2. 解析期間欄位（第三欄，索引 2）
            start_date = None
            period_cell = cells[col_period] if len(cells) > col_period else None
            if period_cell:
                period_text = period_cell.get_text() or ""
                start_date = _parse_roc_date(period_text)
            
            # 3. 解析對象欄位（第四欄，索引 3）
            audience = None
            audience_cell = cells[col_audience] if len(cells) > col_audience else None
            if audience_cell:
                audience_text = clean_text(audience_cell.get_text() or "")
                # 提取「對象：」後面的文字
                match = re.search(r"對象[：:]\s*(.+)", audience_text)
                if match:
                    audience = clean_text(match.group(1))
                else:
                    # 如果沒有「對象：」標記，直接用整個文字
                    audience = audience_text if audience_text else None
            
            # 4. 解析導師欄位（第五欄，索引 4）
            instructor = None
            instructor_cell = cells[col_instructor] if len(cells) > col_instructor else None
            if instructor_cell:
                instructor_text = clean_text(instructor_cell.get_text() or "")
                # 移除電話號碼（Tel:...）
                instructor_text = re.sub(r"Tel:.*$", "", instructor_text, flags=re.IGNORECASE).strip()
                if instructor_text:
                    instructor = instructor_text
            
            # 至少要有班代號或班名才能建立課程記錄
            if not class_code and not title:
                continue
            
            # 如果只有班名沒有班代號，用班名當作班代號（但這不是理想情況）
            if not class_code:
                class_code = re.sub(r"[^\w\-]", "", title)[:32] if title else None
            
            course = {
                "source": "tis",
                "status": "scheduled",
                "campus": campus or "離線",
                "system": None,
                "category": None,
                "class_code": class_code,
                "title": title or class_code,  # 如果沒有班名，用班代號代替
                "start_date": start_date,
                "days": None,
                "description": None,
                "audience": audience,
                "level": None,  # TIS 頁面目前沒有難易度欄位
                "instructor": instructor,
                "url": url or page_url,
            }
            courses.append(course)
    
    return courses


def scrape_tis() -> List[Dict[str, Any]]:
    """
    爬取 TIS 三所頁面，合併回傳課程列表。
    """
    all_courses = []
    for campus, url in TIS_PAGES.items():
        html = _fetch_html(url)
        if html:
            items = _parse_courses_from_page(html, campus, url)
            all_courses.extend(items)
            logger.info("從 %s 解析到 %d 筆", campus, len(items))
    return all_courses


def scrape_offline_dir(offline_dir: str, campus: str = None) -> List[Dict[str, Any]]:
    """
    離線爬取：讀取資料夾內的 .html/.htm 檔案，直接解析課程列表。

    使用情境：你先把 TIS 頁面另存成 HTML（離線網頁），就能在沒有網路 / 不想打 TIS 的狀況下做測試。

    參數：
    - offline_dir：本機資料夾路徑（例如 C:\\course_overlap_mvp\\sample_html）
    - campus：要寫入的校區標記（如果為 None，會從檔案名稱推斷：台中所.html → 台中所）
    """
    p = Path(offline_dir).expanduser()
    if not p.exists() or not p.is_dir():
        logger.error("離線資料夾不存在或不是資料夾：%s", str(p))
        return []

    files = []
    for ext in ("*.html", "*.htm"):
        files.extend(sorted(p.glob(ext)))

    if not files:
        logger.warning("離線資料夾內找不到 .html/.htm 檔：%s", str(p))
        return []

    all_courses: List[Dict[str, Any]] = []
    for fp in files:
        try:
            html = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.warning("讀取離線檔案失敗 %s：%s", str(fp), e)
            continue

        # 從檔案名稱推斷校區（如果沒有指定）
        file_campus = campus
        if not file_campus:
            filename = fp.stem  # 不含副檔名的檔名
            # 常見校區名稱對應
            if "台中所" in filename or "臺中所" in filename or "台中" in filename:
                file_campus = "台中所"
            elif "高雄所" in filename or "高雄" in filename:
                file_campus = "高雄所"
            elif "院本部" in filename or "本部" in filename:
                file_campus = "院本部"
            # 如果檔案名稱沒有校區資訊，會在 _parse_courses_from_page 中從頁面標題提取

        # 用 offline: 前綴當作來源標記，避免被誤認為線上 URL
        page_id = f"offline:{str(fp)}"
        items = _parse_courses_from_page(html, campus=file_campus, page_url=page_id)
        # 從解析結果中取得實際使用的校區（可能從頁面標題提取）
        actual_campus = items[0].get("campus", file_campus or "離線") if items else (file_campus or "離線")
        logger.info("離線檔案 %s 解析到 %d 筆（校區：%s）", fp.name, len(items), actual_campus)
        all_courses.extend(items)

    return all_courses


if __name__ == "__main__":
    # 可直接執行測試：
    # - 線上：python scraper.py
    # - 離線：python scraper.py --offline-dir C:\course_overlap_mvp\sample_html
    import argparse

    _force_utf8_console()

    ap = argparse.ArgumentParser(description="課程爬取（線上 TIS 或離線 HTML 資料夾）")
    ap.add_argument("--offline-dir", default="", help="離線 HTML 資料夾路徑（含 .html/.htm）")
    ap.add_argument("--campus", default="離線", help="離線模式的校區標記（預設：離線）")
    args = ap.parse_args()

    if args.offline_dir:
        result = scrape_offline_dir(args.offline_dir, campus=args.campus)
    else:
        result = scrape_tis()

    print(f"共 {len(result)} 筆課程")
    for c in result[:3]:
        print(c.get("title"), c.get("url"))
