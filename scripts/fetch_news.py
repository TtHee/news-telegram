#!/usr/bin/env python3
"""
主程式：串接所有模組，執行完整新聞抓取流水線。

流水線：
  1. RSS 抓取與去重       (rss_fetcher)
  2. Groq AI 摘要與標記   (groq_summary)
  3. 市場數據             (market_data)
  4. 風險評分             (risk_score)
  5. 寫入 news.json       (本模組)
  6. Telegram 推播        (telegram_notify)
"""
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    NEWS_JSON_PATH, SENT_IDS_PATH,
    BREAKING_KEYWORDS, WATCH_STOCKS, BREAKING_COOLDOWN_HOURS,
)
from rss_fetcher import fetch_all
from groq_summary import summarize
from market_data import get_all_market_data
from risk_score import calc_risk_score
from telegram_notify import send_morning_report, send_breaking_news

TZ_TW = timezone(timedelta(hours=8))


# ── 輔助函式 ──────────────────────────────────────────

def _is_breaking(article: dict) -> bool:
    text = (article.get("title", "") + " " + article.get("summary_zh", "")).lower()
    keyword_hit = any(kw.lower() in text for kw in BREAKING_KEYWORDS)
    stock_hit   = any(s.lower() in text for s in WATCH_STOCKS)
    return keyword_hit or stock_hit or article.get("sentiment") == "負面"


def _cooldown_ok(article_id: str, sent: dict) -> bool:
    if article_id not in sent:
        return True
    sent_at = datetime.fromisoformat(sent[article_id])
    elapsed_hours = (datetime.now(TZ_TW) - sent_at).total_seconds() / 3600
    return elapsed_hours >= BREAKING_COOLDOWN_HOURS


def _load_sent_ids() -> dict:
    try:
        with open(SENT_IDS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_sent_ids(sent: dict) -> None:
    Path(SENT_IDS_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(SENT_IDS_PATH, "w", encoding="utf-8") as f:
        json.dump(sent, f)


# ── 流水線各步驟 ──────────────────────────────────────

def enrich_articles(articles: list) -> list:
    """為每篇文章加上 AI 摘要、情緒標籤、重大新聞標記。"""
    for i, a in enumerate(articles):
        print(f"  [Groq] {i+1}/{len(articles)}: {a['title'][:45]}")
        result = summarize(a["title"], a.get("raw_content", ""))
        a["summary_zh"]  = result["summary"]
        a["sentiment"]   = result["sentiment"]
        a["is_breaking"] = _is_breaking(a)
        a.pop("raw_content", None)
        time.sleep(0.3)
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
        "generated_at": datetime.now(TZ_TW).isoformat(),
        "risk_score":   risk["score"],
        "risk_level":   risk["level"],
        "risk_signals": risk["signals"],
        "market":       market_info["market"],
        "macro":        market_info.get("macro", {}),
        "categories":   categories,
    }


def write_json(output: dict) -> None:
    Path(NEWS_JSON_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(NEWS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[JSON] 已寫入 {NEWS_JSON_PATH}")


def handle_telegram(output: dict, risk: dict) -> None:
    """發送早報（09:15）及重大新聞即時推播。"""
    sent = _load_sent_ids()
    now  = datetime.now(TZ_TW)

    if now.hour == 9 and 5 <= now.minute <= 25:
        print("[Telegram] 發送每日早報...")
        send_morning_report(output, risk)

    for cat_articles in output.get("categories", {}).values():
        for a in cat_articles:
            if a.get("is_breaking") and _cooldown_ok(a["id"], sent):
                print(f"[Telegram] 重大新聞推播：{a['title'][:50]}")
                if send_breaking_news(a):
                    sent[a["id"]] = now.isoformat()

    _save_sent_ids(sent)


# ── 主流程 ────────────────────────────────────────────

def main() -> None:
    print(f"[Start] {datetime.now(TZ_TW).isoformat()}")

    articles    = fetch_all()
    articles    = enrich_articles(articles)
    categories  = categorize(articles)
    market_info = get_all_market_data()
    risk        = calc_risk_score(market_info["market"], articles)
    output      = build_output(categories, market_info, risk)

    write_json(output)
    handle_telegram(output, risk)

    print("[Done]")


if __name__ == "__main__":
    main()
