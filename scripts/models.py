"""
資料結構定義。
使用 TypedDict 讓 dict 用法不變，同時提供型別提示。
"""
from typing import TypedDict


class RawArticle(TypedDict, total=False):
    """RSS 抓取後的原始文章。"""
    id: str
    title: str
    url: str
    source: str
    category: str
    published_at: str
    raw_content: str


class Article(TypedDict, total=False):
    """經過摘要處理後的完整文章。"""
    id: str
    title: str
    url: str
    source: str
    category: str
    published_at: str
    title_zh: str
    summary_zh: str
    sentiment: str
    is_breaking: bool


class MarketTick(TypedDict):
    """單一市場指標資料。"""
    price: float | None
    change_pct: float | None
