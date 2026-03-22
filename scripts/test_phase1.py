"""Phase 1 重構驗證測試。"""
from utils import strip_html, make_id
from groq_summary import _parse_response

# === strip_html ===
assert strip_html('<b>Hello</b> World') == 'Hello World'
assert strip_html('  多餘   空白  ') == '多餘 空白'
assert strip_html('<a href="x">link</a>') == 'link'
assert strip_html('') == ''
print('strip_html OK')

# === make_id ===
assert len(make_id('test')) == 8
assert make_id('abc') == make_id('abc')
assert make_id('abc') != make_id('def')
print('make_id OK')

# === _parse_response ===
r = _parse_response('{"title_zh":"測試","summary":"摘要","sentiment":"正面"}', 'fallback')
assert r['title_zh'] == '測試'
assert r['summary'] == '摘要'
assert r['sentiment'] == '正面'
print('_parse_response OK')

# invalid sentiment → fallback 中性
r2 = _parse_response('{"title_zh":"T","summary":"S","sentiment":"INVALID"}', 'fb')
assert r2['sentiment'] == '中性'
print('sentiment fallback OK')

# JSON 解析失敗 → fallback
r3 = _parse_response('not json at all', 'my_title')
assert r3['title_zh'] == 'my_title'
assert r3['summary'] == 'my_title'
assert r3['sentiment'] == '中性'
print('JSON fallback OK')

# 模型回傳夾雜額外文字 → 仍能提取 JSON
r4 = _parse_response('Here is the result: {"title_zh":"A","summary":"B","sentiment":"負面"} done', 'x')
assert r4['sentiment'] == '負面'
print('extract JSON from noisy response OK')

# === config thresholds ===
from config import INDICATOR_THRESHOLDS
assert 'VIX' in INDICATOR_THRESHOLDS
assert INDICATOR_THRESHOLDS['GOLD']['type'] == 'change'
assert INDICATOR_THRESHOLDS['GOLD']['reverse'] is True
assert INDICATOR_THRESHOLDS['VIX']['type'] == 'price'
assert INDICATOR_THRESHOLDS['TWII']['type'] == 'change'
print('config thresholds OK')

# === risk_score _assess_indicators ===
from risk_score import _assess_indicators

# 正常市場
market = {
    'VIX':  {'price': 15, 'change_pct': 0.5},
    'GOLD': {'price': 2000, 'change_pct': 0.3},
    'TWII': {'price': 18000, 'change_pct': 0.5},
}
signals = _assess_indicators(market)
assert any('🟢' in s for s in signals)
print('risk normal signals OK')

# 高風險市場
market_danger = {
    'VIX':  {'price': 35, 'change_pct': 10},
    'GOLD': {'price': 2500, 'change_pct': 6},
    'TWII': {'price': 15000, 'change_pct': -4},
}
signals_danger = _assess_indicators(market_danger)
assert any('🔴' in s for s in signals_danger)
print('risk danger signals OK')

# === groq_client import ===
from groq_client import chat_completion
print('groq_client import OK')

# === models import ===
from models import RawArticle, Article, MarketTick
print('models import OK')

print()
print('=== All Phase 1 tests passed! ===')
