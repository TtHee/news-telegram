from config import RISK_LEVEL_NORMAL_MAX, RISK_LEVEL_WATCH_MAX

# 歷史危機特徵（簡化關鍵詞集合）
CRISIS_PATTERNS = {
    "2008金融危機": ["銀行倒閉", "信用緊縮", "次貸", "雷曼", "bailout", "credit crunch", "subprime"],
    "2000網路泡沫": ["本益比過高", "科技泡沫", "dot-com", "燒錢", "IPO熱潮", "tech bubble"],
    "1997亞洲風暴": ["外債暴增", "貨幣貶值", "資本外逃", "IMF", "currency crisis"],
    "2020 COVID": ["低波動率", "極度樂觀", "封城", "pandemic", "lockdown", "supply chain"],
}


def calc_risk_score(market: dict, articles: list) -> dict:
    """
    輸入：market dict（來自 market_data）、articles list
    輸出：{"score": int, "level": str, "signals": list}
    """
    score = 0
    signals = []

    # --- 市場數據評分 ---
    vix = market.get("VIX", {}).get("price")
    if vix:
        if vix > 30:
            score += 30
            signals.append(f"VIX 高位 {vix}（恐慌區間）")
        elif vix > 20:
            score += 15
            signals.append(f"VIX 偏高 {vix}")

    twii_chg = market.get("TWII", {}).get("change_pct")
    if twii_chg is not None:
        if abs(twii_chg) >= 3:
            score += 25
            signals.append(f"台股大漲/大跌 {twii_chg}%")
        elif abs(twii_chg) >= 1.5:
            score += 10

    tnx = market.get("TNX", {}).get("price")
    if tnx and tnx > 4.5:
        score += 10
        signals.append(f"美債10年殖利率 {tnx}%（偏高）")

    # --- 新聞情緒評分 ---
    neg_count = sum(1 for a in articles if a.get("sentiment") == "負面")
    if neg_count >= 5:
        score += 20
        signals.append(f"負面新聞 {neg_count} 則")
    elif neg_count >= 3:
        score += 10
        signals.append(f"負面新聞 {neg_count} 則")

    # --- 歷史危機相似度 ---
    all_text = " ".join(
        (a.get("title", "") + " " + a.get("summary_zh", "")).lower()
        for a in articles
    )
    matched_crisis = []
    for crisis_name, keywords in CRISIS_PATTERNS.items():
        hits = [kw for kw in keywords if kw.lower() in all_text]
        if len(hits) >= 2:
            matched_crisis.append(f"{crisis_name}（命中：{', '.join(hits)}）")

    if matched_crisis:
        score += min(15, len(matched_crisis) * 5)
        signals.extend(matched_crisis)

    score = min(100, score)

    if score <= RISK_LEVEL_NORMAL_MAX:
        level = "normal"
        emoji = "🟢"
    elif score <= RISK_LEVEL_WATCH_MAX:
        level = "watch"
        emoji = "🟡"
    else:
        level = "danger"
        emoji = "🔴"

    return {"score": score, "level": level, "emoji": emoji, "signals": signals}
