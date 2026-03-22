import { sendChatMessage } from './api.js';

const chatSessions = {};

function getSession(id) {
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

    const session = getSession(id);
    session.push({ role: 'user', content: question });
    appendBubble(msgContainer, 'user', question);
    input.value = '';

    const typing = document.createElement('div');
    typing.className = 'chat-typing';
    typing.textContent = 'AI 思考中...';
    msgContainer.appendChild(typing);
    msgContainer.scrollTop = msgContainer.scrollHeight;

    const sendBtn = document.querySelector(`#chat-${id} .chat-send-btn`);
    sendBtn.disabled = true;

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
