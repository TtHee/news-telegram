import os
from pathlib import Path

# 專案根目錄（scripts/ 的上一層）
REPO_ROOT = Path(__file__).parent.parent

# === Telegram ===
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# === API Keys ===
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")

# === 時間設定（台灣時間 UTC+8）===
MORNING_REPORT_HOUR = 11
MORNING_REPORT_MINUTE = 15

# === 勿擾時段（台灣時間）===
QUIET_HOUR_START = 1   # 凌晨 1:00 開始靜音
QUIET_HOUR_END = 11    # 上午 11:00 恢復通知

# === 抓取設定 ===
FETCH_INTERVAL_HOURS = 2
MAX_ARTICLES_PER_SOURCE = 8

# === 重大新聞觸發條件 ===
BREAKING_CHANGE_PCT = 3.0        # 大盤漲跌幅閾值（%）
BREAKING_COOLDOWN_HOURS = 72     # 同類警示冷卻時間（小時）
BREAKING_SENTIMENT_COUNT = 3     # 連續負面新聞數觸發

BREAKING_KEYWORDS = [
    "Fed升息", "Fed降息", "聯準會", "央行", "升息", "降息",
    "台灣海峽", "兩岸", "制裁", "戰爭", "衝突",
    "破產", "倒閉", "金融危機", "股市崩盤",
    "rate hike", "rate cut", "federal reserve", "sanctions",
    "bankruptcy", "crisis", "crash", "recession",
]

WATCH_STOCKS = ["台積電", "聯發科", "TSMC", "2330", "2454"]

# === 風險指數燈號閾值 ===
RISK_LEVEL_NORMAL_MAX = 40   # 0~40 🟢
RISK_LEVEL_WATCH_MAX = 70    # 41~70 🟡
                              # 71~100 🔴

# === RSS 來源 ===
RSS_SOURCES = [
    # AI
    {"name": "MIT Tech Review",   "url": "https://www.technologyreview.com/feed/",               "category": "ai"},
    {"name": "Google News",       "url": "https://news.google.com/rss/search?q=AI+artificial+intelligence&hl=en-US&gl=US&ceid=US:en", "category": "ai"},
    {"name": "Google News",       "url": "https://news.google.com/rss/search?q=人工智慧+OR+AI&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",       "category": "ai"},
    # Google Trends 每日熱門搜尋
    {"name": "Google Trends 台灣", "url": "https://trends.google.com.tw/trending/rss?geo=TW",            "category": "trends"},
    {"name": "Google Trends 日本", "url": "https://trends.google.com/trending/rss?geo=JP",               "category": "trends"},
    {"name": "Google Trends 美國", "url": "https://trends.google.com/trending/rss?geo=US",               "category": "trends"},
    # Google Trends 過去 7 天
    {"name": "Google Trends 台灣 7天", "url": "https://trends.google.com.tw/trending/rss?geo=TW&hours=168", "category": "trends_weekly"},
    {"name": "Google Trends 日本 7天", "url": "https://trends.google.com/trending/rss?geo=JP&hours=168",    "category": "trends_weekly"},
    {"name": "Google Trends 美國 7天", "url": "https://trends.google.com/trending/rss?geo=US&hours=168",    "category": "trends_weekly"},
    # 白宮
    {"name": "White House News",  "url": "https://www.whitehouse.gov/news/feed/",                "category": "whitehouse"},
    {"name": "Google News",       "url": "https://news.google.com/rss/search?q=%22白宮%22+總統+OR+政策+OR+行政命令+OR+%22White+House%22+president+policy&hl=zh-TW&gl=TW&ceid=TW:zh-Hant", "category": "whitehouse"},
    # 川普
    {"name": "Google News",       "url": "https://news.google.com/rss/search?q=Trump+OR+川普&hl=zh-TW&gl=TW&ceid=TW:zh-Hant", "category": "trump"},
    {"name": "CNN",               "url": "https://news.google.com/rss/search?q=site:cnn.com+Trump&hl=en-US&gl=US&ceid=US:en",     "category": "trump"},
    {"name": "Reuters",           "url": "https://news.google.com/rss/search?q=site:reuters.com+Trump&hl=en-US&gl=US&ceid=US:en", "category": "trump"},
    {"name": "BBC",               "url": "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",                              "category": "trump"},
    # 全球趨勢
    {"name": "Google News",       "url": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=zh-TW&gl=TW&ceid=TW:zh-Hant", "category": "global"},
    {"name": "BBC World",         "url": "https://feeds.bbci.co.uk/news/world/rss.xml",          "category": "global"},
    # 財經
    {"name": "Google News",       "url": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en", "category": "finance"},
    {"name": "CNBC",              "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html","category": "finance"},
    # 台股
    {"name": "Yahoo 台股新聞",    "url": "https://tw.stock.yahoo.com/rss?category=news",         "category": "stock_tw"},
    {"name": "Yahoo 研究報告",    "url": "https://tw.stock.yahoo.com/rss?category=research",     "category": "stock_tw"},
    {"name": "中央社財經",        "url": "https://feeds.feedburner.com/rsscna/finance",           "category": "stock_tw"},
    # 美股（Google News 聚合）
    {"name": "Google News",       "url": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=zh-TW&gl=TW&ceid=TW:zh-Hant", "category": "stock_us"},
]

# === 市場數據代碼 ===
YFINANCE_TICKERS = {
    "TWII":  "^TWII",
    "SP500": "^GSPC",
    "NASDAQ":"^IXIC",
    "VIX":   "^VIX",
    "TNX":   "^TNX",
    "MOVE":  "^MOVE",
    "DXY":   "DX-Y.NYB",
    "GOLD":  "GC=F",
}

FRED_SERIES = {
    "CPI":          "CPIAUCSL",
    "UNEMPLOYMENT": "UNRATE",
    "GDP":          "GDP",
}

# === 輸出路徑（絕對路徑，無論從哪個目錄執行都正確）===
NEWS_JSON_PATH    = REPO_ROOT / "docs" / "data" / "news.json"
SENT_IDS_PATH     = REPO_ROOT / "scripts" / ".sent_ids.json"
TRENDS_CACHE_PATH = REPO_ROOT / "docs" / "data" / "trends_weekly.json"
