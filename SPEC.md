# 個人新聞智能推播平台 — 專案規格文件

## 1. 系統概述

自動從多個 RSS 來源抓取新聞，使用 Groq AI 進行繁體中文摘要，透過 GitHub Actions 定時執行，將結果存入 JSON 並透過 Telegram Bot 推播通知。前端以靜態 HTML 部署於 GitHub Pages。

---

## 2. 系統架構

```
RSS 來源 (5 大分類)
    │
    ▼
fetch_news.py (Python 主程式)
    ├─ 解析 RSS Feed
    ├─ Groq API 摘要 (繁體中文)
    ├─ yfinance 市場數據 (VIX / 殖利率 / 大盤)
    ├─ FRED API 總體數據
    └─ 寫入 docs/data/news.json
         │
         ├─► GitHub Actions 定時觸發
         │       ├─ 每日 09:15 (台灣時間) 推播早報
         │       └─ 每整點更新 JSON
         │
         ├─► Telegram Bot 推播通知
         │       ├─ 每日早報 (09:15)
         │       └─ 重大新聞即時偵測
         │
         └─► GitHub Pages (靜態前端)
                 └─ docs/index.html 讀取 news.json 顯示卡片
```

---

## 3. 新聞來源與分類

| 分類 | 來源 | RSS URL | 說明 |
|------|------|---------|------|
| AI | The Rundown AI | https://www.rundown.ai/rss | 每日 AI 趨勢 |
| AI | MIT Tech Review | https://www.technologyreview.com/feed/ | 深度技術分析 |
| AI | The Neuron | https://www.theneuron.ai/rss | AI 工具產業新聞 |
| 全球趨勢 | Reuters | https://feeds.reuters.com/reuters/topNews | 即時中立新聞 |
| 全球趨勢 | Semafor | https://www.semafor.com/rss | 多視角跨國新聞 |
| 財經 | Reuters Business | https://feeds.reuters.com/reuters/businessNews | 全球財經 |
| 財經 | CNBC | https://www.cnbc.com/id/100003114/device/rss/rss.html | 即時財經分析 |
| 股市 | Yahoo 奇摩股市 | https://tw.stock.yahoo.com/rss?category=news | 台股即時新聞 |
| 股市 | Yahoo 研究報告 | https://tw.stock.yahoo.com/rss?category=research | 研究報告類 |
| 股市 | 中央社財經 | https://feeds.feedburner.com/rsscna/finance | 本週中立台股 |
| 股市 | Google News 台灣財經 | https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=zh-TW&gl=TW&ceid=TW:zh-Hant | 聚合多家媒體 |

---

## 4. 功能清單

### 4.1 RSS 抓取
- 每 2 小時執行一次完整抓取
- 每個來源最多取 10 則最新文章
- 去重：以文章 URL 為唯一鍵，避免重複推播
- 抓取失敗時記錄 log，不中斷其他來源

### 4.2 Groq AI 摘要
- 模型：LLaMA 3 (via Groq API，免費額度)
- 輸出語言：繁體中文
- 摘要長度：3～5 句話
- 每則新聞附帶情緒標籤：`正面` / `中性` / `負面`
- 超過免費額度時降級為標題直接顯示（不中斷服務）

### 4.3 市場數據串接

| 數據項目 | 來源 | 說明 |
|---------|------|------|
| VIX 恐慌指數 | yfinance (`^VIX`) | 反映市場波動 |
| 台股大盤 | yfinance (`^TWII`) | 台灣加權指數 |
| 美股大盤 | yfinance (`^GSPC`, `^IXIC`) | S&P 500, Nasdaq |
| 美債殖利率 | yfinance (`^TNX`) | 10 年期美債 |
| 美國 CPI / 失業率 | FRED API | 總體經濟數據 |

### 4.4 重大新聞即時偵測

觸發條件（符合任一即立即推播）：
- 台股漲跌幅 ±3% 以上
- 以下個股出現：台積電、聯發科（可設定擴充）
- 關鍵詞命中：Fed 升降息、央行決策、台灣政治衝突、新冠/制裁
- 新聞情緒連續 3 篇負面（防誤報機制：同類警示 3 天內不重複推播）

### 4.5 預警燈號（Crisis Dashboard）
- 根據市場數據 + 新聞情緒計算 0～100 分「系統風險指數」
- 燈號：🟢 正常 / 🟡 留意 / 🔴 高風險
- 對比歷史危機特徵（2008/2000/1997/2020）輸出相似度提示

### 4.6 Telegram 推播

| 類型 | 時間 | 內容 |
|------|------|------|
| 每日早報 | 09:15 (台灣時間) | 5 大分類摘要 + 市場數據 + 預警燈號 |
| 整點更新提示 | 每整點 | 僅有新重大新聞時才推播 |
| 即時警報 | 隨時 | 觸發重大新聞條件時立即推播 |

### 4.7 前端介面
- 佈局：左側分類 + 右側卡片式
- 主題：淺色（白底乾淨清爽）
- 功能：
  - 關鍵字搜尋
  - 標記已讀 / 收藏
  - 預警燈號儀表板（顯示風險指數）
- 部署：GitHub Pages（`docs/` 目錄）

---

## 5. 資料格式

### 5.1 `docs/data/news.json`

```json
{
  "generated_at": "2026-03-14T09:00:00+08:00",
  "risk_score": 42,
  "risk_level": "normal",
  "market": {
    "TWII": { "price": 19850.5, "change_pct": -0.8 },
    "VIX": { "price": 18.3 },
    "SP500": { "price": 5200.1, "change_pct": 0.3 },
    "TNX": { "price": 4.25 }
  },
  "categories": {
    "ai": [...],
    "global": [...],
    "finance": [...],
    "stock_tw": [...],
    "stock_us": [...]
  }
}
```

### 5.2 單則新聞物件

```json
{
  "id": "sha256-前8碼",
  "title": "Fed 宣布維持利率不變",
  "url": "https://...",
  "source": "Reuters",
  "category": "finance",
  "published_at": "2026-03-14T08:30:00Z",
  "summary_zh": "Fed 於本次會議決定維持基準利率...",
  "sentiment": "neutral",
  "is_breaking": false,
  "read": false,
  "saved": false
}
```

### 5.3 Telegram 早報格式

```
📊 每日市場早報 2026-03-14

🔴 系統風險指數：72 / 100（留意）

📈 市場概況
• 台股：19,850 (-0.8%)
• S&P 500：5,200 (+0.3%)
• VIX：18.3
• 美債10Y：4.25%

🤖 AI 要聞
• [標題] — 摘要一句話
• ...

🌍 全球趨勢
• ...

💰 財經
• ...

📉 股市
• ...

---
⚠️ 以上為 AI 自動摘要，僅供參考，非投資建議
```

---

## 6. 設定參數

### 6.1 環境變數（GitHub Actions Secrets）

| 變數名稱 | 說明 | 必填 |
|---------|------|------|
| `GROQ_API_KEY` | Groq API 金鑰 | ✅ |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | ✅ |
| `TELEGRAM_CHAT_ID` | 推播目標 Chat ID | ✅ |
| `FRED_API_KEY` | FRED 總體數據 API | 選填 |

### 6.2 `config.py` 可調整參數

```python
# 時間設定（台灣時間）
MORNING_REPORT_HOUR = 9
MORNING_REPORT_MINUTE = 15

# 重大新聞觸發條件
BREAKING_CHANGE_PCT = 3.0        # 大盤漲跌幅閾值（%）
BREAKING_COOLDOWN_HOURS = 72     # 同類警示冷卻時間（小時）
BREAKING_SENTIMENT_COUNT = 3     # 連續負面新聞數觸發

# 抓取設定
FETCH_INTERVAL_HOURS = 2         # RSS 抓取頻率
MAX_ARTICLES_PER_SOURCE = 10     # 每來源最多文章數

# 風險指數設定
RISK_LEVEL_NORMAL = 40           # 0~40 綠燈
RISK_LEVEL_WATCH = 70            # 41~70 黃燈
                                 # 71~100 紅燈
```

---

## 7. 檔案結構

```
news_telegram/
├── .github/
│   └── workflows/
│       └── fetch_news.yml       # GitHub Actions 排程
├── scripts/
│   ├── fetch_news.py            # 主程式
│   ├── groq_summary.py          # Groq AI 摘要模組
│   ├── market_data.py           # yfinance + FRED 數據
│   ├── telegram_notify.py       # Telegram 推播模組
│   ├── risk_score.py            # 預警燈號計算
│   └── config.py                # 設定參數
├── docs/                        # GitHub Pages 根目錄
│   ├── index.html               # 前端介面
│   └── data/
│       └── news.json            # 自動生成的新聞資料
└── requirements.txt
```

---

## 8. 部署步驟摘要

1. Fork / 建立 GitHub Repo
2. 設定 Secrets：`GROQ_API_KEY`、`TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`
3. 啟用 GitHub Pages（來源：`docs/` 目錄）
4. 手動觸發一次 Actions 確認運作
5. 之後由 Actions 每 2 小時自動執行

---

*本文件根據 2026-03-11 討論紀錄自動整理生成*
