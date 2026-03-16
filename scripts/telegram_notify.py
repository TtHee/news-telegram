from datetime import datetime, timezone, timedelta

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

TZ_TW = timezone(timedelta(hours=8))

CATEGORY_LABELS = {
    "trends":     "🔥 Google Trends",
    "whitehouse": "🏛️ 白宮/川普",
    "ai":         "🤖 AI 人工智慧",
    "global":     "🌍 全球趨勢",
    "finance":    "💰 財經",
    "stock_tw":   "📉 台股",
    "stock_us":   "📈 美股",
}

SENTIMENT_EMOJI = {"正面": "✅", "負面": "❌", "中性": "▫️"}


def _api_url() -> str:
    return f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


def send_message(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] 未設定 Token 或 Chat ID，跳過推播")
        return False
    try:
        resp = requests.post(_api_url(), json={
            "chat_id":    TELEGRAM_CHAT_ID,
            "text":       text,
            "parse_mode": "HTML",
        }, timeout=15)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[Telegram] 推播失敗：{e}")
        return False


def _format_market(market: dict):
    def fmt(key, label):
        d = market.get(key, {})
        price, chg = d.get("price"), d.get("change_pct")
        if price is None:
            return f"• {label}：資料不可用"
        chg_str = f" ({'+' if chg and chg > 0 else ''}{chg}%)" if chg is not None else ""
        return f"• {label}：{price:,}{chg_str}"

    return [
        fmt("TWII",  "台股"),
        fmt("SP500", "S&P 500"),
        fmt("VIX",   "VIX"),
        fmt("TNX",   "美債10Y"),
    ]


def _format_category(cat: str, articles: list) -> list[str]:
    label = CATEGORY_LABELS.get(cat, cat)
    lines = [f"", f"<b>{label}</b>"]
    for a in articles[:3]:
        emoji = SENTIMENT_EMOJI.get(a.get("sentiment", "中性"), "▫️")
        summary = a.get("summary_zh", a.get("title", ""))[:80]
        lines.append(f"{emoji} {summary}")
    return lines


def send_morning_report(news_data: dict, risk: dict) -> bool:
    today = datetime.now(TZ_TW).strftime("%Y-%m-%d")

    lines = [
        f"📊 <b>每日市場早報 {today}</b>",
        "",
        f"{risk['emoji']} 系統風險指數：<b>{risk['score']} / 100</b>",
    ]

    if risk.get("signals"):
        lines.append("⚠️ 警示：" + "；".join(risk["signals"][:3]))

    lines.extend(["", "📈 <b>市場概況</b>"])
    lines.extend(_format_market(news_data.get("market", {})))

    for cat in CATEGORY_LABELS:
        articles = news_data.get("categories", {}).get(cat, [])
        if articles:
            lines.extend(_format_category(cat, articles))

    lines.extend(["", "---", "⚠️ 以上為 AI 自動摘要，僅供參考，非投資建議"])
    return send_message("\n".join(lines))


def send_breaking_news(article: dict) -> bool:
    sentiment = article.get("sentiment", "中性")
    emoji = {"正面": "✅", "負面": "🚨", "中性": "⚡"}.get(sentiment, "⚡")
    text = (
        f"🔔 <b>重大新聞</b>\n\n"
        f"{emoji} <b>{article.get('title', '')}</b>\n\n"
        f"{article.get('summary_zh', '')}\n\n"
        f"🔗 <a href=\"{article.get('url', '')}\">閱讀原文</a>"
    )
    return send_message(text)
