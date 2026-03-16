"""
RSS 抓取與去重邏輯。
職責：從各來源抓取文章，回傳去重後的原始文章列表。
"""
import hashlib
import time

import feedparser

from config import RSS_SOURCES, MAX_ARTICLES_PER_SOURCE


def _make_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:8]


def _parse_feed(source: dict) -> list:
    articles = []
    try:
        feed = feedparser.parse(source["url"])
        for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
            url = entry.get("link", "")
            if not url:
                continue
            articles.append({
                "id":           _make_id(url),
                "title":        entry.get("title", "").strip(),
                "url":          url,
                "source":       source["name"],
                "category":     source["category"],
                "published_at": entry.get("published", ""),
                "raw_content":  (entry.get("summary") or entry.get("description") or "")[:800],
            })
    except Exception as e:
        print(f"[RSS] {source['name']} 失敗：{e}")
    return articles


def _deduplicate(articles: list) -> list:
    seen = {}
    for a in articles:
        seen[a["id"]] = a
    return list(seen.values())


def fetch_all() -> list:
    """抓取所有 RSS 來源，回傳去重後的文章列表。"""
    raw = []
    for source in RSS_SOURCES:
        items = _parse_feed(source)
        print(f"  [RSS] {source['name']}：{len(items)} 則")
        raw.extend(items)
        time.sleep(0.5)
    unique = _deduplicate(raw)
    print(f"[RSS] 去重後共 {len(unique)} 則")
    return unique
