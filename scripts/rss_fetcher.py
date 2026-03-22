"""
RSS 抓取與去重邏輯。
職責：從各來源抓取文章，回傳去重後的原始文章列表。
"""
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote_plus

import feedparser

from config import (
    RSS_SOURCES, MAX_ARTICLES_PER_SOURCE,
    MAX_TRENDS_PER_SOURCE, CONTENT_TRUNCATE_LEN,
)
from models import RawArticle
from utils import strip_html, make_id


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


def _parse_feed(source: dict) -> list[RawArticle]:
    articles = []
    is_trends = "trends.google" in source["url"]
    limit = MAX_TRENDS_PER_SOURCE if is_trends else MAX_ARTICLES_PER_SOURCE

    try:
        feed = feedparser.parse(source["url"])
        for entry in feed.entries[:limit]:
            title = strip_html(entry.get("title", "")).strip()
            if not title:
                continue

            if is_trends:
                # Google Trends: 用「來源名+標題」產生唯一 ID，避免被去重
                unique_key = f"{source['name']}:{title}"
                article_id = make_id(unique_key)
                # 連結到 Google 搜尋該關鍵字
                url = f"https://www.google.com/search?q={quote_plus(title)}"
            else:
                url = entry.get("link", "")
                if not url:
                    continue
                article_id = make_id(url)

            raw = entry.get("summary") or entry.get("description") or ""
            clean_content = strip_html(raw)

            articles.append({
                "id":           article_id,
                "title":        title,
                "url":          url,
                "source":       source["name"],
                "category":     source["category"],
                "published_at": entry.get("published", ""),
                "raw_content":  clean_content[:CONTENT_TRUNCATE_LEN],
            })
    except (OSError, ConnectionError) as e:
        print(f"[RSS] {source['name']} 網路錯誤：{e}")
    except ValueError as e:
        print(f"[RSS] {source['name']} 解析錯誤：{e}")
    except Exception as e:
        print(f"[RSS] {source['name']} 未預期錯誤：{type(e).__name__}: {e}")
    return articles


def _deduplicate(articles: list) -> list:
    seen = {}
    for a in articles:
        seen[a["id"]] = a
    return list(seen.values())


def fetch_all() -> list[RawArticle]:
    """並行抓取所有 RSS 來源，回傳去重後的文章列表。"""
    raw = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_parse_feed, src): src for src in RSS_SOURCES}
        for future in as_completed(futures):
            source = futures[future]
            try:
                items = future.result()
                print(f"  [RSS] {source['name']}：{len(items)} 則")
                raw.extend(items)
            except Exception as e:
                print(f"  [RSS] {source['name']} 執行緒錯誤：{e}")
    unique = _deduplicate(raw)
    print(f"[RSS] 去重後共 {len(unique)} 則")
    return unique
