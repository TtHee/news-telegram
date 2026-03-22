"""
共用工具函式。
"""
import hashlib
import re


def strip_html(text: str) -> str:
    """移除 HTML 標籤，只保留純文字。"""
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def make_id(text: str) -> str:
    """產生 8 字元的短雜湊 ID。"""
    return hashlib.sha256(text.encode()).hexdigest()[:8]
