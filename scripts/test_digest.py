"""今日脈絡改版測試：_validate_digest, _parse_digest, _build_news_context, DIGEST_SYSTEM_PROMPT."""
import json
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent))

from daily_digest import _validate_digest, _parse_digest, _build_news_context, DIGEST_SYSTEM_PROMPT


# ============================================================
# _validate_digest
# ============================================================

def test_validate_digest():
    # 1) 正常新結構 → 通過
    d = {"key_themes": [{"title": "T", "summary": "S"}], "watch_next": [], "cross_links": []}
    assert _validate_digest(d), "正常結構應通過"

    # 2) 只有 key_themes → 通過，自動補欄位
    d2 = {"key_themes": [{"title": "A", "summary": "B"}]}
    assert _validate_digest(d2), "只有 key_themes 也應通過"
    assert "watch_next" in d2, "應自動補 watch_next"
    assert "cross_links" in d2, "應自動補 cross_links"

    # 3) 舊結構含 timeline → 通過並移除 timeline
    d3 = {
        "key_themes": [{"title": "T", "summary": "S"}],
        "timeline": [{"time": "08:00", "event": "E"}],
        "watch_next": [],
    }
    assert _validate_digest(d3), "含 timeline 的舊結構應通過"
    assert "timeline" not in d3, "timeline 應被移除"

    # 4) 無 key_themes → 不通過
    assert not _validate_digest({"timeline": []}), "無 key_themes 應不通過"

    # 5) key_themes 不是 list → 不通過
    assert not _validate_digest({"key_themes": "not a list"}), "key_themes 非 list 應不通過"

    # 6) 非 dict → 不通過
    assert not _validate_digest([]), "非 dict 應不通過"
    assert not _validate_digest("string"), "字串應不通過"

    # 7) 空 key_themes list → 通過（LLM 可能產出空主題）
    d7 = {"key_themes": []}
    assert _validate_digest(d7), "空 key_themes list 仍應通過"

    print("_validate_digest: ALL PASSED")


# ============================================================
# _parse_digest
# ============================================================

def test_parse_digest():
    # 1) 正常 JSON
    raw = json.dumps({
        "key_themes": [{"title": "主題", "summary": "分析"}],
        "watch_next": [{"topic": "T", "reason": "R"}],
        "cross_links": [],
    })
    result = _parse_digest(raw)
    assert result is not None, "正常 JSON 應成功解析"
    assert len(result["key_themes"]) == 1

    # 2) markdown code block 包裝
    raw_md = '```json\n' + raw + '\n```'
    result2 = _parse_digest(raw_md)
    assert result2 is not None, "markdown code block 應成功解析"

    # 3) 前後夾雜文字
    raw_noisy = 'Here is the result:\n' + raw + '\nDone.'
    result3 = _parse_digest(raw_noisy)
    assert result3 is not None, "夾雜文字應成功解析"

    # 4) 完全無效 → None
    assert _parse_digest("not json at all") is None, "無效文字應回傳 None"

    # 5) 舊格式含 timeline → 解析成功並移除 timeline
    raw_old = json.dumps({
        "key_themes": [{"title": "T", "summary": "S"}],
        "timeline": [{"time": "09:00", "event": "E", "impact": "I", "category": "C"}],
        "watch_next": [],
        "cross_links": [],
    })
    result5 = _parse_digest(raw_old)
    assert result5 is not None, "舊格式應成功解析"
    assert "timeline" not in result5, "解析後 timeline 應被移除"

    # 6) 截斷 JSON 修復
    truncated = '{"key_themes":[{"title":"T","summary":"S"}],"watch_next":[{"topic":"T","reason":"R"}],"cross_links":[]}'
    # 模擬截斷：移除最後的 }
    raw_trunc = truncated[:-1]  # 缺少最後 }
    # 這可能無法修復，但不應 crash
    result6 = _parse_digest(raw_trunc)
    # 不強制要求修復成功，但確保不 crash

    print("_parse_digest: ALL PASSED")


# ============================================================
# _build_news_context
# ============================================================

def test_build_news_context():
    articles = [
        {"category": "finance", "title": "Fed holds rates", "summary_zh": "聯準會維持利率", "sentiment": "中性"},
        {"category": "finance", "title": "股市上漲", "summary_zh": "台股大盤上揚", "sentiment": "正面"},
        {"category": "security", "title": "Cyber attack", "summary_zh": "大規模網路攻擊", "sentiment": "負面"},
    ]

    context = _build_news_context(articles)

    # 1) 應按 category 分組
    assert "【finance】" in context, "應含 finance 分組標題"
    assert "【security】" in context, "應含 security 分組標題"

    # 2) 每篇文章都在
    assert "Fed holds rates" in context
    assert "股市上漲" in context
    assert "Cyber attack" in context

    # 3) 摘要截斷到 300 字
    long_summary = "A" * 500
    long_articles = [{"category": "test", "title": "T", "summary_zh": long_summary, "sentiment": "中性"}]
    long_ctx = _build_news_context(long_articles)
    # 摘要部分最多 300 個 A
    a_count = long_ctx.count("A")
    assert a_count == 300, f"摘要應截斷到 300 字，實際 {a_count}"

    # 4) 空文章列表
    assert _build_news_context([]) == "", "空列表應回傳空字串"

    # 5) 缺少欄位容錯
    sparse = [{"title": "T"}]
    ctx = _build_news_context(sparse)
    assert "T" in ctx, "缺少欄位應不 crash"

    print("_build_news_context: ALL PASSED")


# ============================================================
# DIGEST_SYSTEM_PROMPT 格式化
# ============================================================

def test_system_prompt_format():
    today = date.today().isoformat()
    prompt = DIGEST_SYSTEM_PROMPT.format(today=today)

    # 1) 日期注入成功
    assert today in prompt, f"prompt 應包含今天日期 {today}"

    # 2) 不應包含 timeline 相關指示
    assert "timeline" not in prompt.lower(), "prompt 不應提及 timeline"

    # 3) 應包含深度分析指示
    assert "背景脈絡" in prompt, "prompt 應要求背景脈絡"
    assert "關鍵發展" in prompt, "prompt 應要求關鍵發展"
    assert "潛在影響" in prompt, "prompt 應要求潛在影響"

    # 4) 不應有未替換的 placeholder
    assert "{today}" not in prompt, "不應有未替換的 {today}"
    # 雙括號 {{ }} 在 format 後變成 { }，確認 JSON 範例正確
    assert '"key_themes"' in prompt, "JSON 範例應正確展開"

    print("DIGEST_SYSTEM_PROMPT format: ALL PASSED")


# ============================================================

if __name__ == "__main__":
    test_validate_digest()
    test_parse_digest()
    test_build_news_context()
    test_system_prompt_format()
    print()
    print("=== All digest tests passed! ===")
