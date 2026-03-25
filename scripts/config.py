import os
from pathlib import Path

# 專案根目錄（scripts/ 的上一層）
REPO_ROOT = Path(__file__).parent.parent

# === API Keys ===
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")
NEWSDATA_API_KEY = os.environ.get("NEWSDATA_API_KEY", "")

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
GROQ_DIGEST_MODEL = "llama-3.3-70b-versatile"  # digest 需要更強的模型穩定產出 JSON
GROQ_MAX_RETRIES = 3
GROQ_RETRY_BASE_WAIT = 10       # 重試基礎等待秒數（10, 20, 30…）
GROQ_SUMMARY_TIMEOUT = 30       # 摘要請求逾時（秒）
GROQ_SUMMARY_TEMPERATURE = 0.3
GROQ_SUMMARY_MAX_TOKENS = 800
GROQ_RISK_TIMEOUT = 20          # 風險評估請求逾時（秒）
GROQ_RISK_TEMPERATURE = 0.4
GROQ_RISK_MAX_TOKENS = 200
GROQ_DIGEST_TIMEOUT = 60        # 今日脈絡請求逾時（秒）
GROQ_DIGEST_TEMPERATURE = 0.4
GROQ_DIGEST_MAX_TOKENS = 4000
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

# === RSS 來源（僅保留公共領域 & 非新聞內容）===
RSS_SOURCES = [
    # Google Trends 每日熱門搜尋
    {"name": "Google Trends 台灣", "url": "https://trends.google.com.tw/trending/rss?geo=TW",            "category": "trends"},
    {"name": "Google Trends 日本", "url": "https://trends.google.com/trending/rss?geo=JP",               "category": "trends"},
    {"name": "Google Trends 美國", "url": "https://trends.google.com/trending/rss?geo=US",               "category": "trends"},
    # Google Trends 過去 7 天
    {"name": "Google Trends 台灣 7天", "url": "https://trends.google.com.tw/trending/rss?geo=TW&hours=168", "category": "trends_weekly"},
    {"name": "Google Trends 日本 7天", "url": "https://trends.google.com/trending/rss?geo=JP&hours=168",    "category": "trends_weekly"},
    {"name": "Google Trends 美國 7天", "url": "https://trends.google.com/trending/rss?geo=US&hours=168",    "category": "trends_weekly"},
    # 白宮（美國政府公共領域）
    {"name": "White House News",  "url": "https://www.whitehouse.gov/news/feed/",                "category": "whitehouse"},
]

# === NewsData.io 來源（商用授權，明確指定一線媒體 domainurl）===
# 免費版每次最多 5 個 domainurl，格式: "cnn.com,bbc.com"
NEWSDATA_SOURCES = [
    {
        "category": "ai",
        "params": {"q": "AI OR artificial intelligence", "language": "en", "domainurl": "techcrunch.com,theverge.com,wired.com,arstechnica.com,venturebeat.com"},
    },
    {
        "category": "whitehouse",
        "params": {"q": "White House OR president", "language": "en", "domainurl": "cnn.com,bbc.com,reuters.com,apnews.com,nytimes.com"},
    },
    {
        "category": "trump",
        "params": {"q": "Trump", "language": "en", "domainurl": "cnn.com,bbc.com,reuters.com,theguardian.com,apnews.com"},
    },
    {
        "category": "global",
        "params": {"language": "en", "category": "world", "domainurl": "cnn.com,bbc.com,reuters.com,aljazeera.com,theguardian.com"},
    },
    {
        "category": "finance",
        "params": {"language": "en", "category": "business", "domainurl": "cnbc.com,reuters.com,bloomberg.com,ft.com,wsj.com"},
    },
    {
        "category": "stock_tw",
        "params": {"q": "股市 OR 台股 OR 台積電", "country": "tw", "language": "zh", "domainurl": "udn.com,ltn.com.tw,ctee.com.tw,chinatimes.com,cna.com.tw"},
    },
    {
        "category": "stock_us",
        "params": {"q": "stock OR market OR Wall Street", "language": "en", "domainurl": "cnbc.com,reuters.com,bloomberg.com,marketwatch.com,wsj.com"},
    },
]

# === NewsData.io 設定 ===
NEWSDATA_API_URL = "https://newsdata.io/api/1/latest"
NEWSDATA_MAX_PER_CATEGORY = 10   # 每個 category 最多抓幾則

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
