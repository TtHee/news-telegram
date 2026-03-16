"""
RSS 抓取與去重邏輯。
職責：從各來源抓取文章，回傳去重後的原始文章列表。
"""
import hashlib
import re
import time
from urllib.parse import quote_plus

import feedparser

from config import RSS_SOURCES, MAX_ARTICLES_PER_SOURCE

# Google Trends 每來源最多抓 20 則（頁面上大約就這麼多）
MAX_TRENDS_PER_SOURCE = 20


def _make_id(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:8]


def _strip_html(text: str) -> str:
    """移除 HTML 標籤，只保留純文字。"""
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def _extract_news_url(entry) -> str:
    """從 Google Trends RSS 的 ht:news_item 中提取真正的新聞連結。"""
    for key in ['ht_news_item_url', 'news_item_url']:
        val = entry.get(key, "")
        if val:
            return val

    raw = entry.get("summary") or entry.get("description") or ""
    url_match = re.search(r'href=["\']?(https?://[^"\'>\s]+)', raw)
    if url_match:
        return url_match.group(1)

    return ""


def _parse_feed(source: dict) -> list:
    articles = []
    is_trends = "trends.google" in source["url"]
    limit = MAX_TRENDS_PER_SOURCE if is_trends else MAX_ARTICLES_PER_SOURCE

    try:
        feed = feedparser.parse(source["url"])
        for entry in feed.entries[:limit]:
            title = _strip_html(entry.get("title", "")).strip()
            if not title:
                continue

            if is_trends:
                # Google Trends: 用「來源名+標題」產生唯一 ID，避免被去重
                unique_key = f"{source['name']}:{title}"
                article_id = _make_id(unique_key)
                # 連結到 Google 搜尋該關鍵字
                url = f"https://www.google.com/search?q={quote_plus(title)}"
            else:
                url = entry.get("link", "")
                if not url:
                    continue
                article_id = _make_id(url)

            raw = entry.get("summary") or entry.get("description") or ""
            clean_content = _strip_html(raw)

            articles.append({
                "id":           article_id,
                "title":        title,
                "url":          url,
                "source":       source["name"],
                "category":     source["category"],
                "published_at": entry.get("published", ""),
                "raw_content":  clean_content[:1500],
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
