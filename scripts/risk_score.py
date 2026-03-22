"""
市場風險評估模組：根據指標閾值產生信號，並用 AI 生成綜合評估。
"""
from config import (
    GROQ_API_KEY, INDICATOR_THRESHOLDS,
    GROQ_RISK_TIMEOUT, GROQ_RISK_TEMPERATURE, GROQ_RISK_MAX_TOKENS,
)
from groq_client import chat_completion


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
        threshold_type = cfg.get("type", "price")

        if threshold_type == "change" and chg is not None:
            reverse = cfg.get("reverse", False)
            if reverse:
                # 黃金：漲越多越危險（市場避險）
                if chg >= cfg["danger"]:
                    signals.append(f"🔴 {name} {price}（急漲 {chg:+}%，市場避險）")
                elif chg >= cfg["warn"]:
                    signals.append(f"🟡 {name} {price}（漲 {chg:+}%，留意）")
                else:
                    signals.append(f"🟢 {name} {price}（正常）")
            else:
                # 大盤：跌越多越危險
                if chg <= cfg["danger"]:
                    signals.append(f"🔴 {name} {price}（急跌 {chg:+}%）")
                elif chg <= cfg["warn"]:
                    signals.append(f"🟡 {name} {price}（下跌 {chg:+}%，留意）")
                else:
                    signals.append(f"🟢 {name} {price}（正常）")
        elif threshold_type == "price":
            if price >= cfg["danger"]:
                signals.append(f"🔴 {name} {price}（高風險區間）")
            elif price >= cfg["warn"]:
                signals.append(f"🟡 {name} {price}（留意）")
            else:
                signals.append(f"🟢 {name} {price}（正常）")
    return signals


def _ai_summary(market: dict, signals: list) -> str:
    """用 AI 根據市場指標生成一句綜合評估。"""
    if not GROQ_API_KEY:
        return "目前無法生成 AI 評估（未設定 API Key）"

    indicators_text = "\n".join(signals)

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

    text = chat_completion(
        messages=[
            {"role": "system", "content": "你是專業財經分析師，用繁體中文回覆。"},
            {"role": "user", "content": prompt},
        ],
        temperature=GROQ_RISK_TEMPERATURE,
        max_tokens=GROQ_RISK_MAX_TOKENS,
        timeout=GROQ_RISK_TIMEOUT,
    )

    return text or "AI 評估暫時無法使用"


def calc_risk_score(market: dict, articles: list) -> dict:
    """
    回傳 {"signals": list, "ai_summary": str}
    """
    signals = _assess_indicators(market)
    ai_summary = _ai_summary(market, signals)
    print(f"[Risk] AI 評估：{ai_summary[:80]}")
    return {"signals": signals, "ai_summary": ai_summary}
