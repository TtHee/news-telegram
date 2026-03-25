"""
RSS 抓取與去重邏輯。
職責：從各來源抓取文章，回傳去重後的原始文章列表。
"""
from concurrent.futures import ThreadPoolExecutor, as_completed

import feedparser

from config import (
    RSS_SOURCES, MAX_ARTICLES_PER_SOURCE,
    CONTENT_TRUNCATE_LEN,
)
from models import RawArticle
from utils import strip_html, make_id


def _parse_feed(source: dict) -> list[RawArticle]:
    articles = []

    try:
        feed = feedparser.parse(source["url"])
        for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
            title = strip_html(entry.get("title", "")).strip()
            if not title:
                continue

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
