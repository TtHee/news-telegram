import { sendChatMessage } from './api.js';
import { getSession as getAuthSession, checkDailyQuota } from './supabase.js';

const chatSessions = {};

function getChatSession(id) {
    if (!chatSessions[id]) chatSessions[id] = [];
    return chatSessions[id];
}

export function toggleChat(id) {
    const panel = document.getElementById(`chat-${id}`);
    if (!panel) return;
    const isVisible = panel.style.display === 'flex';
    panel.style.display = isVisible ? 'none' : 'flex';
    if (!isVisible) {
        document.getElementById(`chatInput-${id}`).focus();
    }
}

export async function sendChat(id, newsItemMap) {
    const input = document.getElementById(`chatInput-${id}`);
    const msgContainer = document.getElementById(`chatMsgs-${id}`);
    const question = input.value.trim();
    if (!question) return;

    const sendBtn = document.querySelector(`#chat-${id} .chat-send-btn`);
    sendBtn.disabled = true;

    // --- Auth check ---
    const authSession = await getAuthSession();
    if (!authSession) {
        appendBubble(msgContainer, 'error', '請先登入才能使用 AI 對話');
        sendBtn.disabled = false;
        return;
    }

    // --- Daily quota check ---
    try {
        const quota = await checkDailyQuota();
        if (!quota.allowed) {
            const msg = quota.reason === 'plan_no_ai'
                ? '免費方案的每日 AI 額度已用完，明天再試或升級方案'
                : quota.reason === 'daily_quota_exceeded'
                    ? `今日 AI 額度已用完（${quota.used}/${quota.limit}），明天再試`
                    : '無法使用 AI 對話';
            appendBubble(msgContainer, 'error', msg);
            sendBtn.disabled = false;
            return;
        }
    } catch {
        appendBubble(msgContainer, 'error', '額度檢查失敗，請稍後再試');
        sendBtn.disabled = false;
        return;
    }

    // --- Send chat ---
    const session = getChatSession(id);
    session.push({ role: 'user', content: question });
    appendBubble(msgContainer, 'user', question);
    input.value = '';

    const typing = document.createElement('div');
    typing.className = 'chat-typing';
    typing.textContent = 'AI 思考中...';
    msgContainer.appendChild(typing);
    msgContainer.scrollTop = msgContainer.scrollHeight;

    try {
        const item = newsItemMap.get(id);
        const reply = await sendChatMessage(item, session);
        typing.remove();
        session.push({ role: 'assistant', content: reply });
        appendBubble(msgContainer, 'assistant', reply);
    } catch (err) {
        typing.remove();
        appendBubble(msgContainer, 'error', err.message || '網路錯誤，請檢查連線後再試');
        session.pop();
    } finally {
        sendBtn.disabled = false;
        input.focus();
    }
}

function appendBubble(container, role, text) {
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble chat-${role}`;
    bubble.textContent = text;
    container.appendChild(bubble);
    container.scrollTop = container.scrollHeight;
}
