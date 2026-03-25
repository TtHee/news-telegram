#!/usr/bin/env python3
"""
主程式：串接所有模組，執行完整新聞抓取流水線。

流水線：
  1. 讀取現有 news.json（快取）
  2. RSS 抓取與去重       (rss_fetcher)
  3. 過濾已摘要文章，只對新文章呼叫 Groq
  4. 合併新舊文章
  5. 市場數據             (market_data)
  6. 風險評分             (risk_score)
  7. 寫入 news.json       (本模組)
"""
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    NEWS_JSON_PATH,
    BREAKING_KEYWORDS, WATCH_STOCKS,
    MAX_AGE_HOURS, GROQ_RPM_SLEEP,
    INDICATOR_THRESHOLDS,
)
from rss_fetcher import fetch_all as rss_fetch_all
from newsdata_fetcher import fetch_all as newsdata_fetch_all
from groq_summary import summarize
from daily_digest import generate_daily_digest
from market_data import get_all_market_data
from risk_score import calc_risk_score

TZ_TW = timezone(timedelta(hours=8))


# ── 快取相關 ──────────────────────────────────────────

def _load_existing() -> dict:
    """讀取現有 news.json，回傳已摘要文章的 ID → 文章 dict 對照表。"""
    try:
        with open(NEWS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        cache = {}
        for cat_articles in data.get("categories", {}).values():
            for a in cat_articles:
                cache[a["id"]] = a
        print(f"[Cache] 載入 {len(cache)} 則已摘要文章")
        return cache
    except FileNotFoundError:
        print("[Cache] 無現有資料，全部重新摘要")
        return {}
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[Cache] 快取格式錯誤：{e}，全部重新摘要")
        return {}


def _parse_published(pub: str) -> datetime | None:
    """解析多種日期格式，回傳 aware datetime 或 None。"""
    if not pub:
        return None
    # 1. ISO 格式（含時區）
    try:
        dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        pass
    # 2. RFC 2822 格式（RSS 常見）
    try:
        return parsedate_to_datetime(pub)
    except (ValueError, TypeError):
        pass
    return None


def _is_expired(article: dict) -> bool:
    """檢查文章是否超過 MAX_AGE_HOURS。"""
    pub_dt = _parse_published(article.get("published_at", ""))
    if not pub_dt:
        return False
    age = (datetime.now(TZ_TW) - pub_dt).total_seconds() / 3600
    return age > MAX_AGE_HOURS


# ── 輔助函式 ──────────────────────────────────────────

def _is_breaking(article: dict) -> bool:
    text = (article.get("title", "") + " " + article.get("summary_zh", "")).lower()
    keyword_hit = any(kw.lower() in text for kw in BREAKING_KEYWORDS)
    stock_hit   = any(s.lower() in text for s in WATCH_STOCKS)
    return keyword_hit or stock_hit or article.get("sentiment") == "負面"



# ── 流水線各步驟 ──────────────────────────────────────

def enrich_articles(articles: list, cache: dict) -> list:
    """只對新文章呼叫 Groq 摘要，已有的直接用快取。"""
    new_count = 0
    cached_count = 0

    for i, a in enumerate(articles):
        cached = cache.get(a["id"])
        # 快取有效條件：存在、未過期、摘要不等於標題、已經過 AI 分類
        if (cached
            and not _is_expired(cached)
            and cached.get("summary_zh", "") != cached.get("title", "")
            and cached.get("ai_classified")):
            a["title"]       = cached["title"]
            a["summary_zh"]  = cached["summary_zh"]
            a["sentiment"]   = cached["sentiment"]
            a["is_breaking"] = cached.get("is_breaking", False)
            a["category"]    = cached["category"]
            a["ai_classified"] = True
            a.pop("raw_content", None)
            cached_count += 1
        else:
            # 新文章或尚未 AI 分類，呼叫 Groq
            title_for_groq = cached["title"] if cached and cached.get("summary_zh") else a["title"]
            content_for_groq = a.get("raw_content", "") or (cached.get("summary_zh", "") if cached else "")
            print(f"  [Groq] 新文章 {new_count+1}: {title_for_groq[:45]}")
            result = summarize(title_for_groq, content_for_groq)
            a["title"]       = result["title_zh"]
            a["summary_zh"]  = result["summary"]
            a["sentiment"]   = result["sentiment"]
            # AI 重新分類：覆蓋靜態分類
            if result.get("category"):
                a["category"] = result["category"]
            a["ai_classified"] = True
            a["is_breaking"] = _is_breaking(a)
            a.pop("raw_content", None)
            new_count += 1
            time.sleep(GROQ_RPM_SLEEP)

    # 過濾掉 AI 判定為不相關的文章
    skip_count = sum(1 for a in articles if a.get("category") == "skip")
    if skip_count:
        print(f"[Filter] AI 判定 {skip_count} 則為不相關雜聞，已移除")
    articles = [a for a in articles if a.get("category") != "skip"]

    print(f"[Groq] 新摘要 {new_count} 則，快取命中 {cached_count} 則")
    return articles


def categorize(articles: list) -> dict:
    """依 category 欄位分組文章。"""
    result = {}
    for a in articles:
        cat = a["category"]
        if cat not in result:
            result[cat] = []
        result[cat].append(a)
    return result


def build_output(categories: dict, market_info: dict, risk: dict,
                  daily_digest: dict | None = None) -> dict:
    """組合最終要寫入 news.json 的資料結構。"""
    output = {
        "generated_at":  datetime.now(TZ_TW).isoformat(),
        "risk_signals":  risk["signals"],
        "ai_summary":    risk["ai_summary"],
        "market":        market_info["market"],
        "macro":         market_info.get("macro", {}),
        "categories":    categories,
        "thresholds":    INDICATOR_THRESHOLDS,
    }
    if daily_digest:
        output["daily_digest"] = daily_digest
    return output



def write_json(output: dict) -> None:
    Path(NEWS_JSON_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(NEWS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[JSON] 已寫入 {NEWS_JSON_PATH}")


# ── 主流程 ────────────────────────────────────────────

def _normalize_title(title: str) -> str:
    """正規化標題：移除標點、轉小寫，用於相似度比對。"""
    import re
    return re.sub(r'[^\w\s]', '', title.lower()).strip()


def _is_similar_title(t1: str, t2: str) -> bool:
    """檢查兩個標題是否高度相似（子字串包含或詞級重疊率 > 70%）。"""
    n1 = _normalize_title(t1)
    n2 = _normalize_title(t2)
    if not n1 or not n2:
        return False
    # 短標題包含在長標題中
    if n1 in n2 or n2 in n1:
        return True
    # 詞級重疊率（用詞集合而非字元集合）
    words1 = set(n1.split())
    words2 = set(n2.split())
    if not words1 or not words2:
        return False
    overlap = len(words1 & words2) / max(len(words1), len(words2))
    return overlap > 0.7


def _deduplicate(articles: list) -> list:
    """跨來源去重：先比 ID（URL hash），再比標題相似度。同 category 內才去重。"""
    # 1. ID 去重
    seen_ids = {}
    for a in articles:
        seen_ids[a["id"]] = a
    unique = list(seen_ids.values())

    # 2. 標題去重（同 category 內）
    by_cat = {}
    for a in unique:
        cat = a.get("category", "")
        by_cat.setdefault(cat, []).append(a)

    result = []
    for cat, items in by_cat.items():
        kept = []
        for a in items:
            if any(_is_similar_title(a["title"], k["title"]) for k in kept):
                print(f"  [Dedup] 標題重複跳過：{a['title'][:50]}")
                continue
            kept.append(a)
        result.extend(kept)

    return result


def main() -> None:
    print(f"[Start] {datetime.now(TZ_TW).isoformat()}")

    cache       = _load_existing()
    rss_articles     = rss_fetch_all()
    newsdata_articles = newsdata_fetch_all()
    articles    = _deduplicate(rss_articles + newsdata_articles)
    print(f"[Fetch] RSS {len(rss_articles)} + NewsData {len(newsdata_articles)} → 去重後 {len(articles)}")
    articles    = enrich_articles(articles, cache)
    expired = [a for a in articles if _is_expired(a)]
    articles = [a for a in articles if not _is_expired(a)]
    if expired:
        print(f"[Filter] 移除 {len(expired)} 則過期文章（>{MAX_AGE_HOURS}h）")
    categories  = categorize(articles)
    market_info = get_all_market_data()
    risk        = calc_risk_score(market_info["market"], articles)
    digest      = generate_daily_digest(articles)
    output      = build_output(categories, market_info, risk, digest)

    write_json(output)

    print("[Done]")


if __name__ == "__main__":
    main()
