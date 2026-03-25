export const WORKER_URL = 'https://news-ai-proxy.chiharune2.workers.dev';

export const CATEGORY_NAMES = {
    'trends': '🔥 Google Trends',
    'whitehouse': '🏛️ 美國政治',
    'ai': '🤖 AI',
    'global': '🌍 全球趨勢',
    'finance': '💰 財經',
    'stock_tw': '📉 台股',
    'stock_us': '📈 美股'
};

export async function fetchNewsData() {
    const response = await fetch(`data/news.json?t=${Date.now()}`);
    if (!response.ok) throw new Error('Network response was not ok');
    return response.json();
}

export async function sendChatMessage(item, messages) {
    const resp = await fetch(WORKER_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            category: item.categoryCode,
            articleTitle: item.title,
            articleSummary: item.summary_zh,
            messages,
        }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || 'AI 回應失敗');
    return data.reply;
}
