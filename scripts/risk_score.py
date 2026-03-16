import json
import re
import time
import requests
from config import GROQ_API_KEY

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

INDICATOR_THRESHOLDS = {
    "VIX":  {"name": "VIX 恐慌指數", "warn": 20, "danger": 30},
    "MOVE": {"name": "MOVE 債市波動", "warn": 100, "danger": 130},
    "DXY":  {"name": "美元指數", "warn": 105, "danger": 110},
    "GOLD": {"name": "黃金", "warn": None, "danger": None, "change_warn": 2, "change_danger": 5},
    "TNX":  {"name": "美債10Y殖利率", "warn": 4.5, "danger": 5.0},
}


def _assess_indicators(market: dict) -> list:
    """根據閾值評估各指標狀態，回傳摘要列表。"""
    signals = []
    for key, cfg in INDICATOR_THRESHOLDS.items():
        data = market.get(key, {})
        price = data.get("price")
        if price is None:
            continue
        name = cfg["name"]
        chg = data.get("change_pct")
        # 黃金用漲跌幅判斷
        if cfg.get("change_warn") and chg is not None:
            if chg >= cfg["change_danger"]:
                signals.append(f"🔴 {name} {price}（急漲 {chg:+}%，市場避險）")
            elif chg >= cfg["change_warn"]:
                signals.append(f"🟡 {name} {price}（漲 {chg:+}%，留意）")
            else:
                signals.append(f"🟢 {name} {price}（正常）")
        elif cfg["danger"] and price >= cfg["danger"]:
            signals.append(f"🔴 {name} {price}（高風險區間）")
        elif cfg["warn"] and price >= cfg["warn"]:
            signals.append(f"🟡 {name} {price}（留意）")
        else:
            signals.append(f"🟢 {name} {price}（正常）")
    return signals


def _ai_summary(market: dict, signals: list) -> str:
    """用 AI 根據市場指標生成一句綜合評估。"""
    if not GROQ_API_KEY:
        return "目前無法生成 AI 評估（未設定 API Key）"

    indicators_text = "\n".join(signals)

    # 加入漲跌資訊
    extras = []
    for key in ["TWII", "SP500", "NASDAQ"]:
        data = market.get(key, {})
        price, chg = data.get("price"), data.get("change_pct")
        if price and chg is not None:
            name = {"TWII": "台股", "SP500": "S&P500", "NASDAQ": "那斯達克"}[key]
            extras.append(f"{name} {price:,} ({'+' if chg > 0 else ''}{chg}%)")
    if extras:
        indicators_text += "\n" + "\n".join(extras)

    prompt = f"""根據以下市場指標，用繁體中文寫一段 2～3 句的市場氛圍評估。
直接說結論，不要廢話。語氣專業但簡潔，像財經主播的快評。

{indicators_text}

只回覆評估文字，不要加任何格式或標題。"""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "你是專業財經分析師，用繁體中文回覆。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 200,
    }

    try:
        resp = requests.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[Risk AI] 評估失敗：{e}")
        return "AI 評估暫時無法使用"


def calc_risk_score(market: dict, articles: list) -> dict:
    """
    回傳 {"signals": list, "ai_summary": str}
    不再自製分數，改為真實指標 + AI 結語。
    """
    signals = _assess_indicators(market)
    ai_summary = _ai_summary(market, signals)
    print(f"[Risk] AI 評估：{ai_summary[:80]}")

    return {"signals": signals, "ai_summary": ai_summary}
