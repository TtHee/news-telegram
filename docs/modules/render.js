import { CATEGORY_NAMES } from './api.js';
import { getSavedIds, getReadIds } from './storage.js';

// --- Utilities ---

export function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function formatTime(isoString) {
    const diff = new Date() - new Date(isoString);
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `發布於 ${mins} 分鐘前`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `發布於 ${hrs} 小時前`;
    return `發布於 ${Math.floor(hrs / 24)} 天前`;
}

// --- Header & Widgets ---

export function renderHeader(generatedAt) {
    const el = document.getElementById('lastUpdated');
    const d = new Date(generatedAt);
    const diff = Date.now() - d.getTime();
    const mins = Math.floor(diff / 60000);
    let ago;
    if (mins < 1) ago = '剛剛';
    else if (mins < 60) ago = `${mins} 分鐘前`;
    else ago = `${Math.floor(mins / 60)} 小時前`;
    const hh = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    el.textContent = `資料更新：${hh}:${min}（${ago}）`;
}

export function renderWidgets(data) {
    const thresholds = data.thresholds || {};

    const getSignal = (key, d) => {
        const cfg = thresholds[key];
        if (!cfg || !d || d.price === null || d.price === undefined) return '⚪';
        if (cfg.type === 'change') {
            const chg = d.change_pct;
            if (chg === null || chg === undefined) return '⚪';
            if (cfg.reverse) {
                if (chg >= cfg.danger) return '🔴';
                if (chg >= cfg.warn) return '🟡';
            } else {
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

    ['TWII', 'SP500', 'GOLD', 'OIL', 'USDTWD'].forEach(key => {
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

    const singleItems = {
        'VIX':    { suffix: '' },
        'TNX':    { suffix: '%' },
        'MOVE':   { suffix: '' },
        'DXY':    { suffix: '' },
        'HY_OAS': { suffix: ' bps' },
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

    const aiEl = document.getElementById('aiSummary');
    aiEl.textContent = data.ai_summary || '暫無 AI 評估';
}

// --- Google Trends ---

function renderTrendsList(container, items, allNews) {
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

    const bySource = {};
    items.forEach(item => {
        if (!bySource[item.source]) bySource[item.source] = [];
        bySource[item.source].push(item);
    });

    const weeklyItems = allNews.filter(n => n.categoryCode === 'trends_weekly');
    weeklyItems.forEach(item => {
        if (!bySource[item.source]) bySource[item.source] = [];
        bySource[item.source].push(item);
    });

    container.innerHTML = '';

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
        container.appendChild(card);
    }
}

// --- News Cards (differential rendering) ---

const cardCache = new Map();

function createCard(item, isSaved, isRead) {
    const sentimentMap = {
        '正面': { c: 'sentiment-pos', t: '✅ 正面' },
        '負面': { c: 'sentiment-neg', t: '❌ 負面' },
        '中性': { c: 'sentiment-neu', t: '▫️ 中性' }
    };
    const st = sentimentMap[item.sentiment] || sentimentMap['中性'];
    const breakingHtml = item.is_breaking ? '<span class="tag breaking">🔔 Breaking</span>' : '';
    const timeStr = formatTime(item.published_at);
    const eid = escapeHtml(item.id);

    const card = document.createElement('div');
    card.className = `news-card ${isRead ? 'is-read' : ''}`;
    card.dataset.id = item.id;
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
                <button class="ask-ai-btn" data-action="ask-ai" data-id="${eid}">問 AI</button>
                <a href="${escapeHtml(item.url)}" target="_blank" class="read-more">原文來源</a>
            </div>
        </div>
        <div class="chat-panel" id="chat-${eid}">
            <div class="chat-messages" id="chatMsgs-${eid}"></div>
            <div class="chat-input-row">
                <input type="text" class="chat-input" id="chatInput-${eid}"
                       placeholder="問一個關於這則新聞的問題..." data-action="chat-input" data-id="${eid}">
                <button class="chat-send-btn" data-action="send-chat" data-id="${eid}">送出</button>
            </div>
        </div>
    `;
    return card;
}

function updateCardState(card, isSaved, isRead) {
    card.classList.toggle('is-read', isRead);
    const saveBtn = card.querySelector('[data-action="save"]');
    const readBtn = card.querySelector('[data-action="read"]');
    if (saveBtn) saveBtn.classList.toggle('saved', isSaved);
    if (readBtn) readBtn.classList.toggle('read', isRead);
}

export function renderNews(container, allNews, filters) {
    const { currentCategory, searchQuery, filterUnread, filterSaved } = filters;
    const savedIds = getSavedIds();
    const readIds = getReadIds();

    let filtered = allNews.filter(item => {
        if (currentCategory === 'all' && (item.categoryCode === 'trends' || item.categoryCode === 'trends_weekly')) return false;
        if (currentCategory === 'trends' && item.categoryCode === 'trends_weekly') return true;
        if (currentCategory !== 'all' && item.categoryCode !== currentCategory) return false;
        if (filterUnread && readIds.includes(item.id)) return false;
        if (filterSaved && !savedIds.includes(item.id)) return false;
        if (searchQuery) {
            const matchTitle = item.title.toLowerCase().includes(searchQuery);
            const matchSummary = item.summary_zh.toLowerCase().includes(searchQuery);
            if (!matchTitle && !matchSummary) return false;
        }
        return true;
    });

    filtered.sort((a, b) => {
        if (a.is_breaking && !b.is_breaking) return -1;
        if (!a.is_breaking && b.is_breaking) return 1;
        return new Date(b.published_at) - new Date(a.published_at);
    });

    if (filtered.length === 0) {
        container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #6B7280;">找不到符合條件的新聞。</div>';
        cardCache.clear();
        return;
    }

    if (currentCategory === 'trends') {
        cardCache.clear();
        renderTrendsList(container, filtered, allNews);
        return;
    }

    // --- Differential update ---
    const newIds = new Set(filtered.map(item => item.id));

    // Remove stale cards
    for (const [id, card] of cardCache) {
        if (!newIds.has(id)) {
            card.remove();
            cardCache.delete(id);
        }
    }

    // Build / reuse cards in correct order
    let prevNode = null;
    for (const item of filtered) {
        const isSaved = savedIds.includes(item.id);
        const isRead = readIds.includes(item.id);
        let card = cardCache.get(item.id);

        if (card) {
            updateCardState(card, isSaved, isRead);
        } else {
            card = createCard(item, isSaved, isRead);
            cardCache.set(item.id, card);
        }

        // Ensure correct DOM order
        const expectedNext = prevNode ? prevNode.nextSibling : container.firstChild;
        if (card !== expectedNext) {
            container.insertBefore(card, expectedNext);
        }
        prevNode = card;
    }

    // Remove trailing DOM nodes not in the new list
    while (prevNode && prevNode.nextSibling) {
        container.removeChild(prevNode.nextSibling);
    }
}
