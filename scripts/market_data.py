import requests
from config import FRED_API_KEY, YFINANCE_TICKERS, FRED_SERIES

YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=2d&interval=1d"
YAHOO_HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_yfinance_data() -> dict:
    """用 Yahoo Finance HTTP API 抓取市場數據（不依賴 yfinance 套件）"""
    result = {}
    for key, ticker in YFINANCE_TICKERS.items():
        try:
            resp = requests.get(
                YAHOO_URL.format(symbol=ticker),
                headers=YAHOO_HEADERS,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            # 過濾掉 None 值
            closes = [c for c in closes if c is not None]

            if len(closes) >= 2:
                prev, close = closes[-2], closes[-1]
                change_pct = round((close - prev) / prev * 100, 2)
                result[key] = {"price": round(close, 2), "change_pct": change_pct}
            elif len(closes) == 1:
                result[key] = {"price": round(closes[-1], 2), "change_pct": None}
            else:
                result[key] = {"price": None, "change_pct": None}
        except Exception as e:
            print(f"[Market] {key} ({ticker}) 失敗：{e}")
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
