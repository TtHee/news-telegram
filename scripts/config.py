import os
from pathlib import Path

# 專案根目錄（scripts/ 的上一層）
REPO_ROOT = Path(__file__).parent.parent

# === API Keys ===
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")

# === 抓取設定 ===
FETCH_INTERVAL_HOURS = 2
MAX_ARTICLES_PER_SOURCE = 8

# === 重大新聞觸發條件 ===
BREAKING_CHANGE_PCT = 3.0        # 大盤漲跌幅閾值（%）

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

# === Groq API 設定 ===
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_MAX_RETRIES = 3
GROQ_RETRY_BASE_WAIT = 10       # 重試基礎等待秒數（10, 20, 30…）
GROQ_SUMMARY_TIMEOUT = 30       # 摘要請求逾時（秒）
GROQ_SUMMARY_TEMPERATURE = 0.3
GROQ_SUMMARY_MAX_TOKENS = 800
GROQ_RISK_TIMEOUT = 20          # 風險評估請求逾時（秒）
GROQ_RISK_TEMPERATURE = 0.4
GROQ_RISK_MAX_TOKENS = 200
GROQ_RPM_SLEEP = 2.5            # Groq 免費版 30 RPM 間隔

# === 內容處理 ===
CONTENT_TRUNCATE_LEN = 1500     # 文章內容截斷長度
MAX_TRENDS_PER_SOURCE = 20      # Google Trends 每來源最多抓取數

# === 市場指標閾值（前端也會讀取）===
INDICATOR_THRESHOLDS = {
    "TWII":  {"name": "台股加權",     "type": "change", "warn": -2,   "danger": -3,  "reverse": False},
    "SP500": {"name": "S&P 500",      "type": "change", "warn": -2,   "danger": -3,  "reverse": False},
    "VIX":   {"name": "VIX 恐慌指數", "type": "price",  "warn": 20,   "danger": 30},
    "MOVE":  {"name": "MOVE 債市波動", "type": "price",  "warn": 100,  "danger": 130},
    "DXY":   {"name": "美元指數",     "type": "price",  "warn": 105,  "danger": 110},
    "GOLD":  {"name": "黃金",         "type": "change", "warn": 2,    "danger": 5,   "reverse": True},
    "TNX":   {"name": "美債10Y殖利率","type": "price",  "warn": 4.5,  "danger": 5.0},
    "OIL":   {"name": "原油 WTI",     "type": "change", "warn": 3,    "danger": 5,   "reverse": True},
    "USDTWD":{"name": "美元/台幣",    "type": "change", "warn": 0.5,  "danger": 1.0, "reverse": True},
    "HY_OAS":{"name": "高收益債利差", "type": "price",  "warn": 400,  "danger": 500},
}

# === 新聞保留時間 ===
MAX_AGE_HOURS = 24

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
    # 美國旅行警示（STEP）
    {"name": "US Travel Advisory", "url": "https://travel.state.gov/_res/rss/TAsTWs.xml",        "category": "travel_alert"},
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
    "TWII":   "^TWII",
    "SP500":  "^GSPC",
    "NASDAQ": "^IXIC",
    "VIX":    "^VIX",
    "TNX":    "^TNX",
    "MOVE":   "^MOVE",
    "DXY":    "DX-Y.NYB",
    "GOLD":   "GC=F",
    "OIL":    "CL=F",
    "USDTWD": "TWD=X",
}

FRED_SERIES = {
    "CPI":          "CPIAUCSL",
    "UNEMPLOYMENT": "UNRATE",
    "GDP":          "GDP",
    "HY_OAS":       "BAMLH0A0HYM2",
}

# === 輸出路徑（絕對路徑，無論從哪個目錄執行都正確）===
NEWS_JSON_PATH    = REPO_ROOT / "docs" / "data" / "news.json"
TRENDS_CACHE_PATH = REPO_ROOT / "docs" / "data" / "trends_weekly.json"
