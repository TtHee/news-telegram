# Pulse 專案決策記錄

> 建立日期：2026-03-28
> 決策者：Claude（經 Tiffany 授權）

---

## Issue #1：RSS 新聞來源 — 付費牆替代方案

### 背景
Reuters 已於 2021 年啟用付費牆（$34.99/月），Bloomberg 自 2018 年起收費（$34.99/月）。兩者的 RSS feed 目前僅提供標題或摘要片段，完整內容需要訂閱。

### 商用 API 收費參考
| 服務 | 價格 | 說明 |
|------|------|------|
| Reuters API (via LSEG) | 企業詢價制 | 面向金融機構，個人開發者幾乎不可能取得 |
| Bloomberg API | Terminal 用戶限定（$24,000/年） | 不適合小型專案 |
| NewsAPI.org | 免費 100 req/天；付費 $449/月起 | 聚合多來源，免費版僅開發用途 |
| NewsData.io | 免費 200 req/天；付費 $75/月起 | 專案目前已在使用（finance, stock_us） |

### 決策：以免費 RSS 龍頭來源替代
專案已有 BBC、Guardian、Al Jazeera 等一線媒體。針對 **財經分類** 補強以下免費 RSS：

| 來源 | RSS URL | 分類 | 替代角色 |
|------|---------|------|---------|
| CNBC Top News | `https://www.cnbc.com/id/100003114/device/rss/rss.html` | finance | 替代 Reuters Business |
| CNBC World | `https://www.cnbc.com/id/100727362/device/rss/rss.html` | finance | 全球財經 |
| MarketWatch | `http://feeds.marketwatch.com/marketwatch/topstories/` | finance | 替代 Bloomberg |
| Investing.com | `https://www.investing.com/rss/news.rss` | finance | 綜合財經 |
| Yahoo Finance US | `https://finance.yahoo.com/news/rssheadlines` | stock_us | 美股新聞 |
| Seeking Alpha | `https://seekingalpha.com/market_currents.xml` | stock_us | 美股深度分析 |
| Barron's | `https://www.barrons.com/market-data/rss` | stock_us | 市場分析 |

現有的 NewsData.io（免費 200 req/天）繼續保留給 finance 和 stock_us 分類作為補充。

---

## Issue #2：登入帳號資訊移至漢堡選單底部

### 決策
- 手機版：登入/用戶資訊從 header 移到 sidebar 最下方
- 桌機版：保持 header 右側不變（桌機空間充裕）
- sidebar 底部新增用戶區塊：顯示頭像、名稱、登入/登出按鈕

---

## Issue #3：AI 發問額度 + 創作者帳號

### 免費會員額度決策
- **每天 3 次 AI 發問**（全站共用，非每則新聞 3 次）
- 計算依據：
  - Groq 免費額度：30 RPM / 14,400 req/天
  - Cloudflare Worker 免費：100,000 req/天
  - 假設初期 100 位活躍用戶 × 3 次/天 = 300 req/天，遠在安全範圍內
  - 3 次足以讓用戶體驗 AI 價值，又不會被濫用
- 額度改為「每日全站」而非「每月每則」，更直覺

### 方案等級調整
| 方案 | AI 對話額度 | 說明 |
|------|-----------|------|
| free | 3 次/天 | 吸引體驗 |
| light | 30 次/天 | 日常使用足夠 |
| pro | 100 次/天 | 重度用戶 |
| creator | 無限 | 創作者/管理員 |

### 創作者帳號
- Email：`chiharune2@gmail.com`
- 實作方式：在 `profiles` 表新增 `plan = 'creator'`，RPC 函式判斷 creator 直接放行
- 需要在 Supabase 手動執行 SQL 更新此帳號的 plan

### 需要手動執行的 SQL
```sql
UPDATE public.profiles
SET plan = 'creator'
WHERE id = (
  SELECT id FROM auth.users
  WHERE email = 'chiharune2@gmail.com'
);
```

---

## Issue #4：新聞時間顯示

### 問題
- 目前顯示格式：`mm/dd hh:mm`（無時區標示）
- `published_at` 來自 RSS feed 原始值，可能是 GMT/UTC
- 讀者看到較早的時間會誤以為沒有更新

### 決策
- 統一轉換為台灣時間 (UTC+8) 顯示
- 格式：`03/26 18:15 台灣 · 6小時前`
- 「台灣」字樣讓讀者明確知道時區
- 相對時間（X小時前）讓讀者知道新鮮度
- 頁面頂部「資料更新」時間代表抓取時間，卡片上的時間代表新聞發布時間

---

## Issue #5：資料更新檢查

### 現況
- `news.json` 的 `generated_at` 為 `2026-03-26T02:09:38`
- 距今約 2 天前，需確認 GitHub Actions 是否正常運作
- 若 Actions 正常，資料應為最新；若非，需檢查 workflow

### 決策
- 檢查 `published_at` 欄位格式是否統一（目前混合 RFC 2822 和 ISO 8601）
- 在前端 `formatTime` 中做容錯解析，確保兩種格式都能正確轉換

---

## Issue #6：RWD 水平滾動問題

### 決策
- 在 `body` 和 `.main-container` 加上 `overflow-x: hidden`
- 檢查 header 在窄螢幕的 flex wrap 是否造成溢出
- 修復 `.market-grid` 和 `.news-grid` 在小螢幕的寬度
- 確保所有文字有 `word-break: break-word`

---

## Issue #7：全域 AI 發問區（新聞總結分析）

### 需求
- 使用者觀察到某個現象（如：台積電大跌），想透過 AI 從所有新聞中找出可能原因
- 不同於單則新聞的 AI 問答，這是跨新聞的綜合分析

### 決策
- **位置**：頁面最上方，在「今日脈絡」區塊下方
- **UI**：一個聊天框區塊，標題為「🔍 新聞智能分析」
- **功能**：
  - AI 可存取當前所有新聞的標題和摘要作為上下文
  - 使用者輸入觀察到的現象，AI 從新聞中交叉分析找出可能原因
  - 支持多輪對話
- **後端**：新增一個 Worker endpoint `/analyze`，system prompt 包含所有新聞摘要
- **額度**：共用 AI 發問額度（每次提問算 1 次）

---

## Issue #8：新聞卡片背景顏色 — 依來源地區

### 決策：使用左側邊條 (border-left) 標示地區
整張卡片底色不變（白色），避免刺眼。用 4px 左側色條區分：

| 地區 | 顏色 | 色碼 | 聯想 |
|------|------|------|------|
| 🇹🇼 台灣 | 暖橘 | `#F59E0B` | 台灣意象、溫暖 |
| 🇺🇸 美國 | 藍色 | `#3B82F6` | 美國藍、科技感 |
| 🇪🇺 歐洲 | 靛藍 | `#6366F1` | 歐盟旗幟色、優雅 |
| 🇨🇳 中國/港澳 | 玫紅 | `#E11D48` | 中國紅但不刺眼 |
| 🌏 其他亞洲 | 青綠 | `#14B8A6` | 清爽、中性 |
| 🌐 國際通訊社 | 灰色 | `#6B7280` | 中立客觀 |

### 來源對照
- 台灣：中央社、經濟日報、自由時報、Yahoo台股
- 美國：CNBC、MarketWatch、The Hill、White House、Seeking Alpha、VentureBeat
- 歐洲：BBC、Guardian、France24、The Economist
- 中國/港澳：SCMP
- 其他亞洲：Channel News Asia、The Diplomat
- 國際：Al Jazeera、Project Syndicate、Rest of World

---

## Issue #9：市場風向設定（漢堡選單）

### 台股漲跌幅顯示切換
- 預設：百分比（%）
- 可切換：點數（例如 +500 點）
- 儲存在 localStorage

### 漢堡選單新增「設定」區塊
| 設定項目 | 選項 | 預設 |
|---------|------|------|
| 台股顯示格式 | 百分比 / 點數 | 百分比 |
| 新聞排序 | 時間優先 / 重大優先 | 重大優先 |
| 深色模式 | 開 / 關 | 關 |
| 新聞地區篩選 | 全部 / 台灣 / 美國 / 歐洲 / 亞洲 | 全部 |

---

## 實作優先順序

1. ~~決策記錄（本文件）~~ ✅
2. ~~RWD 水平滾動修復 (#6)~~ ✅ — `styles.css` overflow-x: hidden, max-width: 100vw, word-break
3. ~~時間顯示修正 (#4, #5)~~ ✅ — `render.js` formatTimeTW() 台灣時間 + 相對時間
4. ~~新聞卡片地區色條 (#8)~~ ✅ — `render.js` SOURCE_REGION_MAP + `styles.css` region classes
5. ~~登入移至漢堡選單 (#2)~~ ✅ — `index.html` sidebar-auth + `app.js` updateAuthUI
6. ~~AI 額度改制 + 創作者帳號 (#3)~~ ✅ — `migration_003_daily_quota.sql` + `supabase.js` checkDailyQuota
7. ~~漢堡選單設定 (#9)~~ ✅ — `settings.js` + `index.html` settings widget + `render.js` TWII points/percent
8. ~~全域 AI 發問區 (#7)~~ ✅ — `global-ai.js` + `ai-proxy.js` _global_analysis
9. ~~RSS 來源調查 (#1)~~ ✅ — 僅記錄於本文件，`config.py` 不動，保留原有來源。未來擴展時可直接參考上方表格新增

## 部署注意事項

### 必須執行的手動步驟
1. **Supabase SQL**：到 Dashboard → SQL Editor 貼上 `supabase/migration_003_daily_quota.sql` 執行
2. **Cloudflare Worker**：重新 deploy `workers/ai-proxy.js`（已加入 `_global_analysis` 角色）
3. **GitHub Actions**：下次觸發會自動使用新的 RSS 來源

### 修改檔案清單
| 檔案 | 修改內容 |
|------|---------|
| `docs/styles.css` | RWD 修復、dark mode、region colors、settings UI、global AI 樣式 |
| `docs/index.html` | sidebar auth、settings widget、global AI 區塊 |
| `docs/app.js` | settings 整合、sidebar auth 事件、global AI init |
| `docs/modules/render.js` | 台灣時間、region mapping、TWII points/percent、sortMode |
| `docs/modules/settings.js` | 新模組：localStorage 設定管理 |
| `docs/modules/global-ai.js` | 新模組：全域新聞 AI 分析 |
| `docs/modules/supabase.js` | checkDailyQuota RPC |
| `docs/modules/chat.js` | 改用 daily quota |
| `workers/ai-proxy.js` | _global_analysis role + buildSystemPrompt 重構 |
| `scripts/config.py` | 未修改（RSS 來源僅記錄於 decision.md 供未來參考） |
| `supabase/migration_003_daily_quota.sql` | daily_usage 表 + RPC + creator plan |
