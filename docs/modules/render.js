import { CATEGORY_NAMES } from './api.js';
import { getSavedIds, getReadIds } from './storage.js';
import { getSettings } from './settings.js';

// --- Source → Region Mapping ---

const SOURCE_REGION_MAP = {
    // Taiwan
    '中央社財經': 'tw', '經濟日報': 'tw', '自由時報財經': 'tw',
    'Yahoo 台股': 'tw', 'Yahoo 奇摩股市': 'tw',
    // US
    'CNBC': 'us', 'CNBC Top News': 'us', 'CNBC World': 'us',
    'MarketWatch': 'us', 'White House News': 'us', 'The Hill': 'us',
    'VentureBeat': 'us', 'Seeking Alpha': 'us', 'The Verge AI': 'us',
    'Wired AI': 'us', 'MIT Tech Review': 'us', 'Bloomberg Tech': 'us',
    'Politico Tech': 'us', 'Import AI': 'us', 'The Gradient': 'us',
    'Yahoo Finance US': 'us', 'Investing.com': 'us',
    'BBC North America': 'us', 'Guardian US': 'us',
    // Europe
    'BBC World': 'eu', 'BBC Asia': 'eu', 'Guardian World': 'eu',
    'France24': 'eu', 'FT Tech': 'eu',
    // China / HK
    'SCMP': 'cn',
    // Other Asia
    'Channel News Asia': 'asia', 'The Diplomat': 'asia',
    // International
    'Al Jazeera': 'intl', 'Foreign Affairs': 'intl', 'Foreign Policy': 'intl',
    'Project Syndicate': 'intl', 'Rest of World': 'intl',
    'OilPrice': 'intl', 'War on the Rocks': 'intl',
};

const REGION_LABELS = {
    tw: '台灣', us: '美國', eu: '歐洲', cn: '中港', asia: '亞洲', intl: '國際',
};

function getRegion(source) {
    return SOURCE_REGION_MAP[source] || 'intl';
}

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

/**
 * Convert any date string to Taiwan time display.
 * Supports RFC 2822 ("Wed, 25 Mar 2026 06:00:23 GMT") and ISO 8601.
 * Returns: { absolute: "03/26 14:00 台灣", relative: "6小時前" }
 */
function formatTimeTW(isoString) {
    if (!isoString) return { absolute: '', relative: '' };
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return { absolute: '', relative: '' };

    // Format in Asia/Taipei timezone
    const twOptions = { timeZone: 'Asia/Taipei', hour12: false };
    const twMonth = d.toLocaleString('en-US', { ...twOptions, month: '2-digit' });
    const twDay = d.toLocaleString('en-US', { ...twOptions, day: '2-digit' });
    const twHour = d.toLocaleString('en-US', { ...twOptions, hour: '2-digit' });
    const twMin = d.toLocaleString('en-US', { ...twOptions, minute: '2-digit' });

    const absolute = `${twMonth}/${twDay} ${twHour}:${twMin} 台灣`;

    // Relative time
    const diff = Date.now() - d.getTime();
    const mins = Math.floor(diff / 60000);
    let relative;
    if (mins < 0) relative = '剛剛';
    else if (mins < 1) relative = '剛剛';
    else if (mins < 60) relative = `${mins}分鐘前`;
    else if (mins < 1440) relative = `${Math.floor(mins / 60)}小時前`;
    else relative = `${Math.floor(mins / 1440)}天前`;

    return { absolute, relative };
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

    const twOptions = { timeZone: 'Asia/Taipei', hour12: false };
    const hh = d.toLocaleString('en-US', { ...twOptions, hour: '2-digit' });
    const min = d.toLocaleString('en-US', { ...twOptions, minute: '2-digit' });
    el.textContent = `資料更新：${hh}:${min}（${ago}）`;
}

export function renderWidgets(data) {
    const thresholds = data.thresholds || {};
    const settings = getSettings();

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

    const fmt = (key, price, change) => {
        if (price === null || price === undefined) return { p: '--', c: '', class: '' };

        // #9: TWII can show points or percent
        let cText = '';
        let cClass = '';
        if (change !== null && change !== undefined) {
            if (key === 'TWII' && settings.twiiFormat === 'points') {
                // Calculate approximate points from percent
                const points = Math.round(price * change / 100);
                cText = points > 0 ? `▲ +${points}` : `▼ ${points}`;
            } else {
                cText = change > 0 ? `▲ +${change}%` : `▼ ${change}%`;
            }
            cClass = change > 0 ? 'change-up' : 'change-down';
        }
        return { p: price.toLocaleString(), c: cText, class: cClass };
    };

    ['TWII', 'SP500', 'GOLD', 'OIL', 'USDTWD'].forEach(key => {
        const d = data.market[key] || {};
        const f = fmt(key, d.price, d.change_pct);
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

    // Market mood from daily digest + AI summary
    const aiEl = document.getElementById('aiSummary');
    const digest = data.daily_digest;
    const mood = digest && digest.market_snapshot && digest.market_snapshot.mood;
    const moodMap = { '避險': '🔴', '觀望': '🟡', '樂觀': '🟢', '分歧': '🟠' };
    const moodPrefix = mood ? `${moodMap[mood] || '⚪'} 市場氛圍：${mood}｜` : '';
    aiEl.textContent = moodPrefix + (data.ai_summary || '暫無 AI 評估');
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
    const time = formatTimeTW(item.published_at);
    const eid = escapeHtml(item.id);

    // Region
    const region = getRegion(item.source);
    const regionLabel = REGION_LABELS[region] || '國際';

    const card = document.createElement('div');
    card.className = `news-card region-${region} ${isRead ? 'is-read' : ''}`;
    card.dataset.id = item.id;
    card.innerHTML = `
        <div class="card-header">
            <div class="tags">
                ${breakingHtml}
                <span class="tag ${st.c}">${st.t}</span>
                <span class="tag category-tag">${escapeHtml(item.categoryName)}</span>
                <span class="tag region-badge region-badge-${region}">${escapeHtml(regionLabel)}</span>
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
                <span class="time-info">
                    <span class="time-absolute">${escapeHtml(time.absolute)}</span>
                    <span class="time-relative">${escapeHtml(time.relative)}</span>
                </span>
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
    const { currentCategory, searchQuery, filterUnread, filterSaved, sortMode } = filters;
    const savedIds = getSavedIds();
    const readIds = getReadIds();

    let filtered = allNews.filter(item => {
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

    // Sort based on user preference
    if (sortMode === 'time') {
        filtered.sort((a, b) => new Date(b.published_at) - new Date(a.published_at));
    } else {
        // Default: breaking first, then by time
        filtered.sort((a, b) => {
            if (a.is_breaking && !b.is_breaking) return -1;
            if (!a.is_breaking && b.is_breaking) return 1;
            return new Date(b.published_at) - new Date(a.published_at);
        });
    }

    if (filtered.length === 0) {
        container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted);">找不到符合條件的新聞。</div>';
        cardCache.clear();
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
