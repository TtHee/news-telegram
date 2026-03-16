import requests
import yfinance as yf
from config import FRED_API_KEY, YFINANCE_TICKERS, FRED_SERIES


def get_yfinance_data() -> dict:
    """抓取大盤、VIX、殖利率等即時數據"""
    result = {}
    for key, ticker in YFINANCE_TICKERS.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d")
            if len(hist) >= 2:
                prev  = hist["Close"].iloc[-2]
                close = hist["Close"].iloc[-1]
                change_pct = round((close - prev) / prev * 100, 2)
                result[key] = {"price": round(float(close), 2), "change_pct": change_pct}
            elif len(hist) == 1:
                close = hist["Close"].iloc[-1]
                result[key] = {"price": round(float(close), 2), "change_pct": None}
            else:
                result[key] = {"price": None, "change_pct": None}
        except Exception as e:
            print(f"[yfinance] {key} 失敗：{e}")
            result[key] = {"price": None, "change_pct": None}
    return result


def get_fred_data() -> dict:
    """抓取 FRED 總體經濟數據（需要 FRED_API_KEY）"""
    if not FRED_API_KEY:
        return {}

    result = {}
    base = "https://api.stlouisfed.org/fred/series/observations"
    for key, series_id in FRED_SERIES.items():
        try:
            resp = requests.get(base, params={
                "series_id":       series_id,
                "api_key":         FRED_API_KEY,
                "file_type":       "json",
                "sort_order":      "desc",
                "limit":           1,
                "observation_start": "2020-01-01",
            }, timeout=10)
            resp.raise_for_status()
            obs = resp.json().get("observations", [])
            if obs:
                result[key] = {"value": obs[0]["value"], "date": obs[0]["date"]}
        except Exception as e:
            print(f"[FRED] {key} 失敗：{e}")
    return result


def get_all_market_data() -> dict:
    market = get_yfinance_data()
    fred   = get_fred_data()
    return {"market": market, "macro": fred}
