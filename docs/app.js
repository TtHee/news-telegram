// Data State
let newsData = { categories: {}, market: {}, risk: {} };
let allNews = [];
let currentCategory = 'all';
let searchQuery = '';
let filterUnread = false;
let filterSaved = false;

// AI Chat State
const chatSessions = {};   // key: item.id, value: [{role, content}, ...]
const newsItemMap = {};     // key: item.id, value: item object
const WORKER_URL = 'https://news-ai-proxy.chiharune2.workers.dev';

const CATEGORY_NAMES = {
    'trends': '🔥 Google Trends',
    'whitehouse': '🏛️ 白宮',
    'trump': '🇺🇸 川普',
    'ai': '🤖 AI',
    'global': '🌍 全球趨勢',
    'finance': '💰 財經',
    'stock_tw': '📉 台股',
    'stock_us': '📈 美股'
};

// HTML Escape — prevent XSS from external RSS data
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// LocalStorage Keys
const STORE_SAVED = 'news_saved';
const STORE_READ = 'news_read';

// DOM Elements
const newsContainer = document.getElementById('newsContainer');
const loadingEl = document.getElementById('loading');
const errorMsgEl = document.getElementById('errorMsg');
const searchInput = document.getElementById('searchInput');
const menuBtns = document.querySelectorAll('.chip');
const mobileMenuBtn = document.getElementById('mobileMenuBtn');
const sidebar = document.getElementById('sidebar');
const sidebarOverlay = document.getElementById('sidebarOverlay');

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    fetchData();
    setupEventListeners();
});

function setupEventListeners() {
    searchInput.addEventListener('input', (e) => {
        searchQuery = e.target.value.trim().toLowerCase();
        renderNews();
    });

    menuBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            menuBtns.forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentCategory = e.target.dataset.category;
            renderNews();
            // 手機版點選後自動收合
            sidebar.classList.remove('show');
            sidebarOverlay.classList.remove('show');
        });
    });

    document.getElementById('filterUnread').addEventListener('change', (e) => {
        filterUnread = e.target.checked;
        renderNews();
    });

    document.getElementById('filterSaved').addEventListener('change', (e) => {
        filterSaved = e.target.checked;
        renderNews();
    });

    mobileMenuBtn.addEventListener('click', () => {
        sidebar.classList.toggle('show');
        sidebarOverlay.classList.toggle('show');
    });

    sidebarOverlay.addEventListener('click', () => {
        sidebar.classList.remove('show');
        sidebarOverlay.classList.remove('show');
    });

    // 手機 tooltip：點擊有 title 的元素顯示說明
    document.querySelectorAll('.market-name[title]').forEach(el => {
        el.addEventListener('click', (e) => {
            // 移除其他已開啟的 tooltip
            document.querySelectorAll('.mobile-tooltip').forEach(t => t.remove());

            const tooltip = document.createElement('div');
            tooltip.className = 'mobile-tooltip';
            tooltip.textContent = el.getAttribute('title');
            el.parentElement.appendChild(tooltip);

            // 點其他地方關閉
            setTimeout(() => {
                document.addEventListener('click', function close(ev) {
                    if (!tooltip.contains(ev.target) && ev.target !== el) {
                        tooltip.remove();
                        document.removeEventListener('click', close);
                    }
                });
            }, 10);
        });
    });
}

// Fetch Data
async function fetchData() {
    try {
        const response = await fetch('data/news.json');
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();
        
        // Flatten news categories
        allNews = [];
        for (const [cat, items] of Object.entries(data.categories)) {
            items.forEach(item => {
                item.categoryCode = cat;
                item.categoryName = CATEGORY_NAMES[cat] || cat;
                allNews.push(item);
            });
        }

        newsData = data;
        renderHeader(data.generated_at);
        renderWidgets(data);
        renderNews();
        
        loadingEl.style.display = 'none';
        errorMsgEl.style.display = 'none';
    } catch (error) {
        console.error('Fetch error:', error);
        loadingEl.style.display = 'none';
        errorMsgEl.style.display = 'block';
    }
}

// Render Header
function renderHeader(generatedAt) {
    const el = document.getElementById('lastUpdated');
    const d = new Date(generatedAt);
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    const hh = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    el.textContent = `更新於 ${mm}/${dd} ${hh}:${min}`;
}

// Render Widgets
function renderWidgets(data) {
    // 燈號閾值從 news.json 的 thresholds 欄位讀取（單一來源）
    const thresholds = data.thresholds || {};

    const getSignal = (key, d) => {
        const cfg = thresholds[key];
        if (!cfg || !d || d.price === null || d.price === undefined) return '⚪';
        if (cfg.type === 'change') {
            const chg = d.change_pct;
            if (chg === null || chg === undefined) return '⚪';
            if (cfg.reverse) {
                // 黃金：漲越多越危險（市場避險）
                if (chg >= cfg.danger) return '🔴';
                if (chg >= cfg.warn) return '🟡';
            } else {
                // 大盤：跌越多越危險
                if (chg <= cfg.danger) return '🔴';
                if (chg <= cfg.warn) return '🟡';
            }
            return '🟢';
        }
        if (cfg.type === 'price') {
            if (d.price >= cfg.danger) return '🔴';
            if (d.price >= cfg.warn) return '🟡';
            return '🟢';
        }
        return '⚪';
    };

    const fmt = (price, change) => {
        if (price === null || price === undefined) return { p: '--', c: '', class: '' };
        let cText = '';
        let cClass = '';
        if (change !== null && change !== undefined) {
            cText = change > 0 ? `▲ +${change}%` : `▼ ${change}%`;
            cClass = change > 0 ? 'change-up' : 'change-down';
        }
        return { p: price.toLocaleString(), c: cText, class: cClass };
    };

    // 有漲跌幅的指標
    ['TWII', 'SP500', 'GOLD'].forEach(key => {
        const d = data.market[key] || {};
        const f = fmt(d.price, d.change_pct);
        const el = document.getElementById(`market-${key}`);
        if (!el) return;
        el.querySelector('.market-price').textContent = f.p;
        el.querySelector('.market-change').textContent = f.c;
        el.querySelector('.market-change').className = `market-change ${f.class}`;
        const sig = document.getElementById(`signal-${key}`);
        if (sig) sig.textContent = getSignal(key, d);
    });

    // 單值指標
    const singleItems = {
        'VIX':  { suffix: '' },
        'TNX':  { suffix: '%' },
        'MOVE': { suffix: '' },
        'DXY':  { suffix: '' },
    };
    for (const [key, cfg] of Object.entries(singleItems)) {
        const d = data.market[key] || {};
        const el = document.querySelector(`#market-${key} .market-price`);
        if (!el) continue;
        el.textContent = d.price !== null && d.price !== undefined
            ? `${d.price.toLocaleString()}${cfg.suffix}` : '--';
        const sig = document.getElementById(`signal-${key}`);
        if (sig) sig.textContent = getSignal(key, d);
    }

    // AI Summary
    const aiEl = document.getElementById('aiSummary');
    aiEl.textContent = data.ai_summary || '暫無 AI 評估';
}

// Render Google Trends as ranked list by country (daily + weekly)
function renderTrendsList(items) {
    const COUNTRY_CONFIG = [
        { daily: 'Google Trends 台灣', weekly: 'Google Trends 台灣 7天', label: '🇹🇼 台灣',
          dailyUrl: 'https://trends.google.com.tw/trending?geo=TW',
          weeklyUrl: 'https://trends.google.com.tw/trending?geo=TW&hours=168' },
        { daily: 'Google Trends 日本', weekly: 'Google Trends 日本 7天', label: '🇯🇵 日本',
          dailyUrl: 'https://trends.google.com/trending?geo=JP',
          weeklyUrl: 'https://trends.google.com/trending?geo=JP&hours=168' },
        { daily: 'Google Trends 美國', weekly: 'Google Trends 美國 7天', label: '🇺🇸 美國',
          dailyUrl: 'https://trends.google.com/trending?geo=US',
          weeklyUrl: 'https://trends.google.com/trending?geo=US&hours=168' },
    ];

    // Group all trends items by source
    const bySource = {};
    items.forEach(item => {
        if (!bySource[item.source]) bySource[item.source] = [];
        bySource[item.source].push(item);
    });

    // Also include trends_weekly from categories
    const weeklyItems = allNews.filter(n => n.categoryCode === 'trends_weekly');
    weeklyItems.forEach(item => {
        if (!bySource[item.source]) bySource[item.source] = [];
        bySource[item.source].push(item);
    });

    for (const cfg of COUNTRY_CONFIG) {
        const dailyList = bySource[cfg.daily] || [];
        const weeklyList = bySource[cfg.weekly] || [];

        const card = document.createElement('div');
        card.className = 'news-card trends-card';

        let dailyHtml = dailyList.map((t, i) =>
            `<li><span class="trend-rank">${i + 1}</span><a href="${escapeHtml(t.url)}" target="_blank" class="trend-link">${escapeHtml(t.title)}</a></li>`
        ).join('') || '<li class="trend-empty">暫無資料</li>';

        let weeklyHtml = weeklyList.map((t, i) =>
            `<li><span class="trend-rank">${i + 1}</span><a href="${escapeHtml(t.url)}" target="_blank" class="trend-link">${escapeHtml(t.title)}</a></li>`
        ).join('') || '<li class="trend-empty">暫無資料</li>';

        card.innerHTML = `
            <div class="trends-header">
                <h3 class="card-title">${cfg.label}</h3>
            </div>
            <div class="trends-columns">
                <div class="trends-col">
                    <div class="trends-col-title">過去 24 小時 <a href="${cfg.dailyUrl}" target="_blank" class="trends-source">↗</a></div>
                    <ol class="trends-list">${dailyHtml}</ol>
                </div>
                <div class="trends-col">
                    <div class="trends-col-title">過去 7 天 <a href="${cfg.weeklyUrl}" target="_blank" class="trends-source">↗</a></div>
                    <ol class="trends-list">${weeklyHtml}</ol>
                </div>
            </div>
        `;
        newsContainer.appendChild(card);
    }
}

// Render News
function renderNews() {
    newsContainer.innerHTML = '';
    
    // Get LocalStorage states
    const savedIds = JSON.parse(localStorage.getItem(STORE_SAVED) || '[]');
    const readIds = JSON.parse(localStorage.getItem(STORE_READ) || '[]');

    let filtered = allNews.filter(item => {
        // Category Filter — Google Trends 不在「全部」中顯示
        if (currentCategory === 'all' && (item.categoryCode === 'trends' || item.categoryCode === 'trends_weekly')) return false;
        if (currentCategory === 'trends' && item.categoryCode === 'trends_weekly') return true;
        if (currentCategory !== 'all' && item.categoryCode !== currentCategory) return false;
        
        // State Filter
        if (filterUnread && readIds.includes(item.id)) return false;
        if (filterSaved && !savedIds.includes(item.id)) return false;
        
        // Search Filter
        if (searchQuery) {
            const matchTitle = item.title.toLowerCase().includes(searchQuery);
            const matchSummary = item.summary_zh.toLowerCase().includes(searchQuery);
            if (!matchTitle && !matchSummary) return false;
        }
        return true;
    });

    // Sorting: breaking first, then by published_at (desc)
    filtered.sort((a, b) => {
        if (a.is_breaking && !b.is_breaking) return -1;
        if (!a.is_breaking && b.is_breaking) return 1;
        return new Date(b.published_at) - new Date(a.published_at);
    });

    if (filtered.length === 0) {
        newsContainer.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #6B7280;">找不到符合條件的新聞。</div>';
        return;
    }

    // Google Trends 用排名列表顯示
    if (currentCategory === 'trends') {
        renderTrendsList(filtered);
        return;
    }

    filtered.forEach(item => {
        const isSaved = savedIds.includes(item.id);
        const isRead = readIds.includes(item.id);
        
        const sentimentMap = { '正面': { c: 'sentiment-pos', t: '✅ 正面' }, '負面': { c: 'sentiment-neg', t: '❌ 負面' }, '中性': { c: 'sentiment-neu', t: '▫️ 中性' }};
        const st = sentimentMap[item.sentiment] || sentimentMap['中性'];

        const breakingHtml = item.is_breaking ? `<span class="tag breaking">🔔 Breaking</span>` : '';
        const timeStr = formatTime(item.published_at);

        const card = document.createElement('div');
        card.className = `news-card ${isRead ? 'is-read' : ''}`;
        const eid = escapeHtml(item.id);
        card.innerHTML = `
            <div class="card-header">
                <div class="tags">
                    ${breakingHtml}
                    <span class="tag ${st.c}">${st.t}</span>
                    <span class="tag category-tag">${escapeHtml(item.categoryName)}</span>
                </div>
                <div class="actions">
                    <button class="action-btn ${isSaved ? 'saved' : ''}" data-action="save" data-id="${eid}" title="收藏">★</button>
                    <button class="action-btn ${isRead ? 'read' : ''}" data-action="read" data-id="${eid}" title="標示為已讀">✓</button>
                </div>
            </div>
            <h3 class="card-title">${escapeHtml(item.title)}</h3>
            <p class="card-summary">${escapeHtml(item.summary_zh)}</p>
            <div class="card-footer">
                <div class="meta-info">
                    <span>${escapeHtml(item.source)}</span>
                    <span>•</span>
                    <span>${escapeHtml(timeStr)}</span>
                </div>
                <div style="display:flex;gap:0.5rem;align-items:center;">
                    <button class="ask-ai-btn" data-id="${eid}">問 AI</button>
                    <a href="${escapeHtml(item.url)}" target="_blank" class="read-more">原文來源</a>
                </div>
            </div>
            <div class="chat-panel" id="chat-${eid}">
                <div class="chat-messages" id="chatMsgs-${eid}"></div>
                <div class="chat-input-row">
                    <input type="text" class="chat-input" id="chatInput-${eid}"
                           placeholder="問一個關於這則新聞的問題...">
                    <button class="chat-send-btn" data-id="${eid}">送出</button>
                </div>
            </div>
        `;

        // Store item reference for chat
        newsItemMap[item.id] = item;

        // Bind events (no inline onclick — avoids XSS via item.id)
        card.querySelector('[data-action="save"]').addEventListener('click', function () { toggleSaved(item.id, this); });
        card.querySelector('[data-action="read"]').addEventListener('click', function () { toggleRead(item.id, this); });
        card.querySelector('.ask-ai-btn').addEventListener('click', () => toggleChat(item.id));
        card.querySelector('.chat-send-btn').addEventListener('click', () => sendChat(item.id));
        card.querySelector('.chat-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') sendChat(item.id);
        });

        newsContainer.appendChild(card);
    });
}

// Time Format
function formatTime(isoString) {
    const diff = new Date() - new Date(isoString);
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins} 分鐘前`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs} 小時前`;
    return `${Math.floor(hrs / 24)} 天前`;
}

// Toggle States
window.toggleSaved = (id, btn) => {
    let saved = JSON.parse(localStorage.getItem(STORE_SAVED) || '[]');
    if (saved.includes(id)) {
        saved = saved.filter(x => x !== id);
        btn.classList.remove('saved');
    } else {
        saved.push(id);
        btn.classList.add('saved');
    }
    localStorage.setItem(STORE_SAVED, JSON.stringify(saved));
    if (filterSaved) renderNews(); // re-render if filtering
};

window.toggleRead = (id, btn) => {
    let read = JSON.parse(localStorage.getItem(STORE_READ) || '[]');
    const card = btn.closest('.news-card');
    if (read.includes(id)) {
        read = read.filter(x => x !== id);
        btn.classList.remove('read');
        card.classList.remove('is-read');
    } else {
        read.push(id);
        btn.classList.add('read');
        card.classList.add('is-read');
    }
    localStorage.setItem(STORE_READ, JSON.stringify(read));
    if (filterUnread) renderNews(); // re-render if filtering
};

// AI Chat Functions
function toggleChat(id) {
    const panel = document.getElementById(`chat-${id}`);
    const isVisible = panel.style.display === 'flex';
    panel.style.display = isVisible ? 'none' : 'flex';
    if (!isVisible) {
        document.getElementById(`chatInput-${id}`).focus();
    }
}

async function sendChat(id) {
    const input = document.getElementById(`chatInput-${id}`);
    const msgContainer = document.getElementById(`chatMsgs-${id}`);
    const question = input.value.trim();
    if (!question) return;

    // Init session
    if (!chatSessions[id]) chatSessions[id] = [];

    // Show user message
    chatSessions[id].push({ role: 'user', content: question });
    appendChatBubble(msgContainer, 'user', question);
    input.value = '';

    // Show typing indicator
    const typing = document.createElement('div');
    typing.className = 'chat-typing';
    typing.textContent = 'AI 思考中...';
    msgContainer.appendChild(typing);
    msgContainer.scrollTop = msgContainer.scrollHeight;

    // Disable send button
    const sendBtn = document.querySelector(`#chat-${id} .chat-send-btn`);
    sendBtn.disabled = true;

    try {
        const item = newsItemMap[id];
        const resp = await fetch(WORKER_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                category: item.categoryCode,
                articleTitle: item.title,
                articleSummary: item.summary_zh,
                messages: chatSessions[id],
            }),
        });

        typing.remove();

        const data = await resp.json();
        if (!resp.ok) {
            appendChatBubble(msgContainer, 'error', data.error || 'AI 回應失敗');
            chatSessions[id].pop(); // remove failed user msg from history
            return;
        }

        chatSessions[id].push({ role: 'assistant', content: data.reply });
        appendChatBubble(msgContainer, 'assistant', data.reply);

    } catch (err) {
        typing.remove();
        appendChatBubble(msgContainer, 'error', '網路錯誤，請檢查連線後再試');
        chatSessions[id].pop();
    } finally {
        sendBtn.disabled = false;
        input.focus();
    }
}

function appendChatBubble(container, role, text) {
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble chat-${role}`;
    bubble.textContent = text;
    container.appendChild(bubble);
    container.scrollTop = container.scrollHeight;
}
