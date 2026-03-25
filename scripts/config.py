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
MAX_ARTICLES_PER_SOURCE = 15

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
GROQ_RPM_SLEEP = 3.0            # Groq 免費版 30 RPM 間隔（20 RPM 留餘量）

# === 內容處理 ===
CONTENT_TRUNCATE_LEN = 1500     # 文章內容截斷長度

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
    # --- 國際新聞（權威一線媒體 RSS）---
    {"name": "BBC World",          "url": "https://feeds.bbci.co.uk/news/world/rss.xml",        "category": "global"},
    {"name": "Guardian World",     "url": "https://www.theguardian.com/world/rss",              "category": "global"},
    {"name": "Al Jazeera",         "url": "https://aljazeera.com/xml/rss/all.xml",              "category": "global"},
    {"name": "BBC Asia",           "url": "https://feeds.bbci.co.uk/news/world/asia/rss.xml",   "category": "global"},

    # --- 美國政治 ---
    {"name": "White House News",   "url": "https://www.whitehouse.gov/news/feed/",              "category": "whitehouse"},
    {"name": "BBC North America",  "url": "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml", "category": "whitehouse"},
    {"name": "The Hill",           "url": "https://thehill.com/feed/",                          "category": "whitehouse"},
    {"name": "Guardian US",        "url": "https://www.theguardian.com/us-news/rss",            "category": "whitehouse"},

    # --- 國際趨勢 & 地緣政治 ---
    {"name": "Foreign Affairs",    "url": "https://www.foreignaffairs.com/rss.xml",             "category": "global"},
    {"name": "Foreign Policy",     "url": "https://foreignpolicy.com/feed/",                    "category": "global"},
    {"name": "The Diplomat",       "url": "https://thediplomat.com/feed/",                      "category": "global"},
    {"name": "SCMP",               "url": "https://www.scmp.com/rss/91/feed",                   "category": "global"},
    {"name": "France24",           "url": "https://www.france24.com/en/rss",                    "category": "global"},
    {"name": "Project Syndicate",  "url": "https://www.project-syndicate.org/rss",              "category": "global"},
    {"name": "Channel News Asia",  "url": "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml", "category": "global"},
    {"name": "OilPrice",           "url": "https://oilprice.com/rss/main",                      "category": "global"},
    {"name": "War on the Rocks",   "url": "https://warontherocks.com/feed/",                    "category": "global"},

    # --- AI & 科技 ---
    {"name": "The Verge AI",       "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "category": "ai"},
    {"name": "MIT Tech Review",    "url": "https://www.technologyreview.com/feed/",             "category": "ai"},
    {"name": "Wired AI",           "url": "https://www.wired.com/feed/tag/ai/latest/rss",       "category": "ai"},
    {"name": "VentureBeat",        "url": "https://venturebeat.com/feed/",                      "category": "ai"},
    {"name": "Import AI",          "url": "https://importai.substack.com/feed",                 "category": "ai"},
    {"name": "The Gradient",       "url": "https://thegradient.pub/rss/",                       "category": "ai"},
    {"name": "Bloomberg Tech",     "url": "https://feeds.bloomberg.com/technology/news.rss",    "category": "ai"},
    {"name": "FT Tech",            "url": "https://www.ft.com/technology?format=rss",           "category": "ai"},
    {"name": "Politico Tech",      "url": "https://rss.politico.com/technology.xml",            "category": "ai"},
    {"name": "Rest of World",      "url": "https://restofworld.org/feed/",                      "category": "ai"},

    # --- 台股財經 ---
    {"name": "中央社財經",          "url": "https://feeds.feedburner.com/rsscna/finance",        "category": "stock_tw"},
    {"name": "經濟日報",            "url": "https://money.udn.com/rssfeed/news/1001/rss2.xml",  "category": "stock_tw"},
    {"name": "自由時報財經",        "url": "https://news.ltn.com.tw/rss/business.xml",           "category": "stock_tw"},
    {"name": "Yahoo 台股",         "url": "https://tw.stock.yahoo.com/rss?category=tw-market",  "category": "stock_tw"},
]

# === NewsData.io 來源（僅保留 domainurl 正常運作的分類）===
# 其餘分類已改用直接 RSS 取得權威來源
NEWSDATA_SOURCES = [
    {
        "category": "finance",
        "params": {"language": "en", "category": "business", "domainurl": "cnbc.com,reuters.com,bloomberg.com,ft.com,wsj.com"},
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
