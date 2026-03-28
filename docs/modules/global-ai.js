/**
 * Global AI Analysis — cross-news intelligent analysis.
 * Sends all current news headlines + summaries as context,
 * letting the user ask questions about observed phenomena.
 */

import { WORKER_URL } from './api.js';
import { getSession as getAuthSession, checkDailyQuota } from './supabase.js';

const messages = [];

export function initGlobalAi(allNews) {
    const container = document.getElementById('globalAiContainer');
    const msgContainer = document.getElementById('globalAiMessages');
    const input = document.getElementById('globalAiInput');
    const sendBtn = document.getElementById('globalAiSend');
    const quotaEl = document.getElementById('globalAiQuota');

    if (!container || !input || !sendBtn) return;

    async function send() {
        const question = input.value.trim();
        if (!question) return;

        sendBtn.disabled = true;

        // Auth check
        const authSession = await getAuthSession();
        if (!authSession) {
            appendBubble(msgContainer, 'error', '請先登入才能使用 AI 分析');
            sendBtn.disabled = false;
            return;
        }

        // Quota check
        try {
            const quota = await checkDailyQuota();
            if (!quota.allowed) {
                const msg = quota.reason === 'plan_no_ai'
                    ? '免費方案不含 AI 對話功能，請升級為 Light 或 Pro'
                    : quota.reason === 'daily_quota_exceeded'
                        ? `今日 AI 額度已用完（${quota.used}/${quota.limit}），明天再試`
                        : '無法使用 AI 分析';
                appendBubble(msgContainer, 'error', msg);
                sendBtn.disabled = false;
                return;
            }
            // Update quota display
            if (quotaEl && quota.limit !== 999999) {
                quotaEl.textContent = `今日已用 ${quota.used}/${quota.limit} 次`;
            }
        } catch {
            appendBubble(msgContainer, 'error', '額度檢查失敗，請稍後再試');
            sendBtn.disabled = false;
            return;
        }

        // Add user message
        messages.push({ role: 'user', content: question });
        appendBubble(msgContainer, 'user', question);
        input.value = '';

        // Typing indicator
        const typing = document.createElement('div');
        typing.className = 'chat-typing';
        typing.textContent = 'AI 分析中...';
        msgContainer.appendChild(typing);
        msgContainer.scrollTop = msgContainer.scrollHeight;

        try {
            // Build context from all news
            const newsContext = buildNewsContext(allNews);

            const resp = await fetch(WORKER_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    category: '_global_analysis',
                    articleTitle: '全域新聞分析',
                    articleSummary: newsContext,
                    messages,
                }),
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.error || 'AI 回應失敗');

            typing.remove();
            messages.push({ role: 'assistant', content: data.reply });
            appendBubble(msgContainer, 'assistant', data.reply);
        } catch (err) {
            typing.remove();
            appendBubble(msgContainer, 'error', err.message || '網路錯誤，請稍後再試');
            messages.pop();
        } finally {
            sendBtn.disabled = false;
            input.focus();
        }
    }

    sendBtn.addEventListener('click', send);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') send();
    });
}

function buildNewsContext(allNews) {
    // Limit to latest 50 news items to stay within token limits
    const sorted = [...allNews]
        .sort((a, b) => new Date(b.published_at) - new Date(a.published_at))
        .slice(0, 50);

    const lines = sorted.map((item, i) =>
        `${i + 1}. [${item.source}] ${item.title}\n   ${item.summary_zh || ''}`
    );
    return lines.join('\n\n');
}

function appendBubble(container, role, text) {
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble chat-${role}`;
    bubble.textContent = text;
    container.appendChild(bubble);
    container.scrollTop = container.scrollHeight;
}
