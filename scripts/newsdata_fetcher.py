"""
NewsData.io API 抓取模組。
職責：從 NewsData.io 取得商用授權新聞，回傳與 rss_fetcher 相同的 RawArticle 格式。
"""
import requests

from config import (
    NEWSDATA_API_KEY, NEWSDATA_API_URL,
    NEWSDATA_SOURCES, NEWSDATA_MAX_PER_CATEGORY,
    CONTENT_TRUNCATE_LEN,
)
from models import RawArticle
from utils import make_id


def _fetch_category(source: dict) -> list[RawArticle]:
    """呼叫 NewsData.io API 取得單一 category 的新聞。422 時自動去掉 domainurl 重試。"""
    if not NEWSDATA_API_KEY:
        print("[NewsData] 未設定 NEWSDATA_API_KEY，跳過")
        return []

    params = {"apikey": NEWSDATA_API_KEY, "size": NEWSDATA_MAX_PER_CATEGORY}

    for key, val in source["params"].items():
        if val is not None:
            params[key] = val

    try:
        resp = requests.get(NEWSDATA_API_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.HTTPError as e:
        if resp.status_code == 422 and "domainurl" in params:
            dropped = params.pop("domainurl")
            print(f"[NewsData] {source['category']} domainurl 不支援（{dropped}），改為不限來源重試")
            try:
                resp = requests.get(NEWSDATA_API_URL, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as retry_e:
                print(f"[NewsData] {source['category']} 重試仍失敗：{retry_e}")
                return []
        else:
            print(f"[NewsData] {source['category']} 請求失敗：{e}")
            return []
    except requests.RequestException as e:
        print(f"[NewsData] {source['category']} 請求失敗：{e}")
        return []
    except ValueError as e:
        print(f"[NewsData] {source['category']} JSON 解析失敗：{e}")
        return []

    if data.get("status") != "success":
        print(f"[NewsData] {source['category']} API 錯誤：{data.get('results', {}).get('message', 'unknown')}")
        return []

    articles = []
    sources_seen = set()
    for item in data.get("results") or []:
        url = item.get("link", "")
        title = (item.get("title") or "").strip()
        if not url or not title:
            continue

        content = item.get("description") or item.get("content") or ""
        source_name = item.get("source_name", "NewsData")
        sources_seen.add(source_name)

        articles.append({
            "id":           make_id(url),
            "title":        title,
            "url":          url,
            "source":       source_name,
            "category":     source["category"],
            "published_at": item.get("pubDate", ""),
            "raw_content":  content[:CONTENT_TRUNCATE_LEN],
        })

    if sources_seen:
        print(f"    [NewsData] {source['category']} 來源：{', '.join(sorted(sources_seen))}")
    return articles


def fetch_all() -> list[RawArticle]:
    """依序抓取所有 NewsData.io 來源，回傳文章列表。"""
    all_articles = []
    for source in NEWSDATA_SOURCES:
        items = _fetch_category(source)
        print(f"  [NewsData] {source['category']}：{len(items)} 則")
        all_articles.extend(items)
    print(f"[NewsData] 共 {len(all_articles)} 則")
    return all_articles
