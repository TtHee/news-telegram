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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    NEWS_JSON_PATH,
    BREAKING_KEYWORDS, WATCH_STOCKS,
    MAX_AGE_HOURS, GROQ_RPM_SLEEP,
    INDICATOR_THRESHOLDS,
)
from rss_fetcher import fetch_all
from groq_summary import summarize
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


def _is_expired(article: dict) -> bool:
    """檢查文章是否超過 MAX_AGE_HOURS。"""
    pub = article.get("published_at", "")
    if not pub:
        return False
    try:
        pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
        age = (datetime.now(TZ_TW) - pub_dt).total_seconds() / 3600
        return age > MAX_AGE_HOURS
    except (ValueError, TypeError):
        return False


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
        # Google Trends 不需要 AI 摘要，直接通過
        if a.get("category") in ("trends", "trends_weekly"):
            a["summary_zh"]  = ""
            a["sentiment"]   = "中性"
            a["is_breaking"] = False
            a.pop("raw_content", None)
            continue

        cached = cache.get(a["id"])
        # 快取有效條件：存在、未過期、摘要不等於標題（等於代表上次失敗）
        if (cached
            and not _is_expired(cached)
            and cached.get("summary_zh", "") != cached.get("title", "")):
            a["title"]       = cached["title"]
            a["summary_zh"]  = cached["summary_zh"]
            a["sentiment"]   = cached["sentiment"]
            a["is_breaking"] = cached.get("is_breaking", False)
            a.pop("raw_content", None)
            cached_count += 1
        else:
            # 新文章，呼叫 Groq
            print(f"  [Groq] 新文章 {new_count+1}: {a['title'][:45]}")
            result = summarize(a["title"], a.get("raw_content", ""))
            a["title"]       = result["title_zh"]
            a["summary_zh"]  = result["summary"]
            a["sentiment"]   = result["sentiment"]
            a["is_breaking"] = _is_breaking(a)
            a.pop("raw_content", None)
            new_count += 1
            time.sleep(GROQ_RPM_SLEEP)

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


def build_output(categories: dict, market_info: dict, risk: dict) -> dict:
    """組合最終要寫入 news.json 的資料結構。"""
    return {
        "generated_at":  datetime.now(TZ_TW).isoformat(),
        "risk_signals":  risk["signals"],
        "ai_summary":    risk["ai_summary"],
        "market":        market_info["market"],
        "macro":         market_info.get("macro", {}),
        "categories":    categories,
        "thresholds":    INDICATOR_THRESHOLDS,
    }



def write_json(output: dict) -> None:
    Path(NEWS_JSON_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(NEWS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[JSON] 已寫入 {NEWS_JSON_PATH}")


# ── 主流程 ────────────────────────────────────────────

def main() -> None:
    print(f"[Start] {datetime.now(TZ_TW).isoformat()}")

    cache       = _load_existing()
    articles    = fetch_all()
    articles    = enrich_articles(articles, cache)
    categories  = categorize(articles)
    market_info = get_all_market_data()
    risk        = calc_risk_score(market_info["market"], articles)
    output      = build_output(categories, market_info, risk)

    write_json(output)

    print("[Done]")


if __name__ == "__main__":
    main()
