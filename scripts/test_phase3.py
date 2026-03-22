"""Phase 3 單元測試：_is_breaking, _is_expired, _parse_response, calc_risk_score."""
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))

from config import BREAKING_KEYWORDS, WATCH_STOCKS, MAX_AGE_HOURS
from groq_summary import _parse_response
from risk_score import _assess_indicators

# 為了測試 _is_breaking / _is_expired，需要從 fetch_news 匯入
from fetch_news import _is_breaking, _is_expired

TZ_TW = timezone(timedelta(hours=8))

# ============================================================
# _is_breaking
# ============================================================

def test_is_breaking():
    # 1) 關鍵字命中（title）
    for kw in BREAKING_KEYWORDS[:3]:
        a = {"title": f"速報：{kw}最新消息", "summary_zh": ""}
        assert _is_breaking(a), f"應命中關鍵字 '{kw}'"

    # 2) 關鍵字命中（summary_zh）
    a = {"title": "一般標題", "summary_zh": "美國 Federal Reserve 宣布 rate cut"}
    assert _is_breaking(a), "summary 含關鍵字 rate cut"

    # 3) 觀察股命中
    for stock in WATCH_STOCKS[:2]:
        a = {"title": f"{stock} 大漲", "summary_zh": ""}
        assert _is_breaking(a), f"應命中觀察股 '{stock}'"

    # 4) 負面情緒
    a = {"title": "普通標題", "summary_zh": "普通摘要", "sentiment": "負面"}
    assert _is_breaking(a), "負面情緒應為 breaking"

    # 5) 一般新聞 → 非 breaking
    a = {"title": "天氣晴朗", "summary_zh": "今日天氣不錯", "sentiment": "正面"}
    assert not _is_breaking(a), "一般新聞不應為 breaking"

    # 6) 空字串
    a = {"title": "", "summary_zh": "", "sentiment": "中性"}
    assert not _is_breaking(a), "空內容不應為 breaking"

    # 7) 大小寫不敏感
    a = {"title": "FEDERAL RESERVE raises rates", "summary_zh": ""}
    assert _is_breaking(a), "大小寫不敏感應命中 'federal reserve'"

    print("_is_breaking: ALL PASSED")

# ============================================================
# _is_expired
# ============================================================

def test_is_expired():
    now = datetime.now(TZ_TW)

    # 1) 剛發布 → 未過期
    fresh = {"published_at": (now - timedelta(hours=1)).isoformat()}
    assert not _is_expired(fresh), "1 小時前不應過期"

    # 2) 超過 MAX_AGE_HOURS → 過期
    old = {"published_at": (now - timedelta(hours=MAX_AGE_HOURS + 1)).isoformat()}
    assert _is_expired(old), f"超過 {MAX_AGE_HOURS} 小時應過期"

    # 3) 剛好在邊界
    edge = {"published_at": (now - timedelta(hours=MAX_AGE_HOURS - 0.1)).isoformat()}
    assert not _is_expired(edge), "未滿上限不應過期"

    # 4) 無 published_at → 不過期（保守策略）
    assert not _is_expired({}), "無日期不應過期"
    assert not _is_expired({"published_at": ""}), "空日期不應過期"

    # 5) 格式錯誤 → 不過期
    assert not _is_expired({"published_at": "not-a-date"}), "格式錯誤不應過期"

    # 6) UTC 格式帶 Z
    utc_now = datetime.now(timezone.utc)
    utc_old = {"published_at": (utc_now - timedelta(hours=MAX_AGE_HOURS + 2)).strftime("%Y-%m-%dT%H:%M:%SZ")}
    assert _is_expired(utc_old), "UTC Z 格式應正確解析並判斷過期"

    print("_is_expired: ALL PASSED")

# ============================================================
# _parse_response
# ============================================================

def test_parse_response():
    # 1) 正常 JSON
    r = _parse_response('{"title_zh":"標題","summary":"摘要","sentiment":"正面"}', "fb")
    assert r["title_zh"] == "標題"
    assert r["summary"] == "摘要"
    assert r["sentiment"] == "正面"

    # 2) 無效 sentiment → 中性
    r = _parse_response('{"title_zh":"T","summary":"S","sentiment":"INVALID"}', "fb")
    assert r["sentiment"] == "中性"

    # 3) JSON 解析失敗 → fallback
    r = _parse_response("not json", "my_title")
    assert r["title_zh"] == "my_title"
    assert r["summary"] == "my_title"
    assert r["sentiment"] == "中性"

    # 4) 夾雜額外文字 → 仍能提取
    r = _parse_response('Here: {"title_zh":"A","summary":"B","sentiment":"負面"} done', "x")
    assert r["sentiment"] == "負面"
    assert r["title_zh"] == "A"

    # 5) 空 title_zh → 用 fallback
    r = _parse_response('{"title_zh":"","summary":"S","sentiment":"正面"}', "fallback")
    assert r["title_zh"] == "fallback"

    # 6) 空 summary → 用 fallback
    r = _parse_response('{"title_zh":"T","summary":"","sentiment":"正面"}', "fallback")
    assert r["summary"] == "fallback"

    # 7) 完全空的 JSON
    r = _parse_response("{}", "fb")
    assert r["title_zh"] == "fb"
    assert r["summary"] == "fb"
    assert r["sentiment"] == "中性"

    print("_parse_response: ALL PASSED")

# ============================================================
# _assess_indicators (risk_score 核心邏輯)
# ============================================================

def test_assess_indicators():
    # 1) 正常市場 → 全綠
    market = {
        "VIX":  {"price": 15, "change_pct": 0.5},
        "GOLD": {"price": 2000, "change_pct": 0.3},
        "TWII": {"price": 18000, "change_pct": 0.5},
        "SP500": {"price": 5000, "change_pct": 0.2},
        "DXY":  {"price": 100, "change_pct": 0.1},
        "TNX":  {"price": 4.0, "change_pct": 0.0},
        "MOVE": {"price": 80, "change_pct": 0.0},
    }
    signals = _assess_indicators(market)
    assert all("🟢" in s for s in signals), f"正常市場應全綠: {signals}"

    # 2) VIX 高風險 → 紅燈
    market_vix = {"VIX": {"price": 35, "change_pct": 0}}
    signals = _assess_indicators(market_vix)
    assert any("🔴" in s for s in signals), "VIX 35 應觸發紅燈"

    # 3) VIX 警告區 → 黃燈
    market_vix_warn = {"VIX": {"price": 22, "change_pct": 0}}
    signals = _assess_indicators(market_vix_warn)
    assert any("🟡" in s for s in signals), "VIX 22 應觸發黃燈"

    # 4) 台股急跌 → 紅燈
    market_twii = {"TWII": {"price": 17000, "change_pct": -4}}
    signals = _assess_indicators(market_twii)
    assert any("🔴" in s for s in signals), "台股 -4% 應觸發紅燈"

    # 5) 台股小跌警告 → 黃燈
    market_twii_warn = {"TWII": {"price": 17500, "change_pct": -2.5}}
    signals = _assess_indicators(market_twii_warn)
    assert any("🟡" in s for s in signals), "台股 -2.5% 應觸發黃燈"

    # 6) 黃金急漲（reverse）→ 紅燈
    market_gold = {"GOLD": {"price": 2500, "change_pct": 6}}
    signals = _assess_indicators(market_gold)
    assert any("🔴" in s for s in signals), "黃金 +6% 應觸發紅燈（reverse）"

    # 7) 黃金小漲警告 → 黃燈
    market_gold_warn = {"GOLD": {"price": 2100, "change_pct": 3}}
    signals = _assess_indicators(market_gold_warn)
    assert any("🟡" in s for s in signals), "黃金 +3% 應觸發黃燈（reverse）"

    # 8) 空市場 → 空信號
    assert _assess_indicators({}) == [], "空市場應無信號"

    # 9) price 為 None → 跳過
    market_none = {"VIX": {"price": None, "change_pct": 0}}
    assert _assess_indicators(market_none) == [], "price=None 應跳過"

    # 10) DXY 高風險
    market_dxy = {"DXY": {"price": 112, "change_pct": 0}}
    signals = _assess_indicators(market_dxy)
    assert any("🔴" in s for s in signals), "DXY 112 應觸發紅燈"

    # 11) 原油急漲 → 紅燈（reverse）
    market_oil = {"OIL": {"price": 85, "change_pct": 6}}
    signals = _assess_indicators(market_oil)
    assert any("🔴" in s for s in signals), "原油 +6% 應觸發紅燈"

    # 12) 原油小漲 → 黃燈
    market_oil_warn = {"OIL": {"price": 80, "change_pct": 3.5}}
    signals = _assess_indicators(market_oil_warn)
    assert any("🟡" in s for s in signals), "原油 +3.5% 應觸發黃燈"

    # 13) USD/TWD 急貶 → 紅燈（reverse）
    market_twd = {"USDTWD": {"price": 32.5, "change_pct": 1.2}}
    signals = _assess_indicators(market_twd)
    assert any("🔴" in s for s in signals), "USD/TWD +1.2% 應觸發紅燈"

    # 14) 高收益債利差高風險 → 紅燈
    market_hy = {"HY_OAS": {"price": 520, "change_pct": None}}
    signals = _assess_indicators(market_hy)
    assert any("🔴" in s for s in signals), "HY_OAS 520 應觸發紅燈"

    # 15) 高收益債利差警告 → 黃燈
    market_hy_warn = {"HY_OAS": {"price": 430, "change_pct": None}}
    signals = _assess_indicators(market_hy_warn)
    assert any("🟡" in s for s in signals), "HY_OAS 430 應觸發黃燈"

    print("_assess_indicators: ALL PASSED")

# ============================================================
# calc_risk_score (整合測試，mock AI)
# ============================================================

def test_calc_risk_score():
    from risk_score import calc_risk_score

    market = {
        "VIX": {"price": 35, "change_pct": 5},
        "TWII": {"price": 17000, "change_pct": -3.5},
    }

    with patch("risk_score.GROQ_API_KEY", "fake-key"), \
         patch("risk_score.chat_completion", return_value="市場氣氛緊張"):
        result = calc_risk_score(market, [])

    assert "signals" in result
    assert "ai_summary" in result
    assert isinstance(result["signals"], list)
    assert len(result["signals"]) > 0
    assert any("🔴" in s for s in result["signals"])
    assert result["ai_summary"] == "市場氣氛緊張"

    # 無 API Key 時的 fallback
    with patch("risk_score.GROQ_API_KEY", ""):
        with patch("risk_score.chat_completion", return_value=None):
            result = calc_risk_score({"VIX": {"price": 15, "change_pct": 0}}, [])
            assert "ai_summary" in result

    print("calc_risk_score: ALL PASSED")

# ============================================================

if __name__ == "__main__":
    test_is_breaking()
    test_is_expired()
    test_parse_response()
    test_assess_indicators()
    test_calc_risk_score()
    print()
    print("=== All Phase 3 tests passed! ===")
