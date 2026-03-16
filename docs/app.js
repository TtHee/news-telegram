// Data State
let newsData = { categories: {}, market: {}, risk: {} };
let allNews = [];
let currentCategory = 'all';
let searchQuery = '';
let filterUnread = false;
let filterSaved = false;

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

// LocalStorage Keys
const STORE_SAVED = 'news_saved';
const STORE_READ = 'news_read';

// DOM Elements
const newsContainer = document.getElementById('newsContainer');
const loadingEl = document.getElementById('loading');
const errorMsgEl = document.getElementById('errorMsg');
const searchInput = document.getElementById('searchInput');
const menuBtns = document.querySelectorAll('.menu-btn');
const mobileMenuBtn = document.getElementById('mobileMenuBtn');
const sidebar = document.getElementById('sidebar');

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
    // Risk / Market Signals
    const signalsList = document.getElementById('riskSignals');
    if (data.risk_signals && data.risk_signals.length) {
        signalsList.innerHTML = data.risk_signals.map(s => `<li>${s}</li>`).join('');
    } else {
        signalsList.innerHTML = '<li>暫無指標資料</li>';
    }

    // AI Summary
    const aiEl = document.getElementById('aiSummary');
    aiEl.textContent = data.ai_summary || '暫無 AI 評估';

    // Market Widget
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

    // 大盤（有漲跌幅）
    ['TWII', 'SP500'].forEach(key => {
        const d = data.market[key] || {};
        const f = fmt(d.price, d.change_pct);
        const el = document.getElementById(`market-${key}`);
        if (!el) return;
        el.querySelector('.market-price').textContent = f.p;
        el.querySelector('.market-change').textContent = f.c;
        el.querySelector('.market-change').className = `market-change ${f.class}`;
    });

    // 單值指標
    const singleItems = {
        'VIX':  { suffix: '', warnAbove: 25 },
        'TNX':  { suffix: '%', warnAbove: 4.5 },
        'MOVE': { suffix: '', warnAbove: 100 },
        'DXY':  { suffix: '', warnAbove: 105 },
        'GOLD': { suffix: '', warnAbove: null },
    };
    for (const [key, cfg] of Object.entries(singleItems)) {
        const d = data.market[key] || {};
        const el = document.querySelector(`#market-${key} .market-price`);
        if (!el) continue;
        el.textContent = d.price !== null && d.price !== undefined
            ? `${d.price.toLocaleString()}${cfg.suffix}` : '--';
        if (cfg.warnAbove && d.price > cfg.warnAbove) {
            el.classList.add('text-danger');
        }
    }
}

// Render Google Trends as ranked list by country
function renderTrendsList(items) {
    const COUNTRY_MAP = {
        'Google Trends 台灣': { label: '🇹🇼 台灣', url: 'https://trends.google.com.tw/trending?geo=TW' },
        'Google Trends 日本': { label: '🇯🇵 日本', url: 'https://trends.google.com/trending?geo=JP' },
        'Google Trends 美國': { label: '🇺🇸 美國', url: 'https://trends.google.com/trending?geo=US' },
    };

    // Group by source (country)
    const groups = {};
    items.forEach(item => {
        const info = COUNTRY_MAP[item.source] || { label: item.source, url: '' };
        const key = item.source;
        if (!groups[key]) groups[key] = { info, items: [] };
        groups[key].items.push(item);
    });

    for (const { info, items: trends } of Object.values(groups)) {
        const card = document.createElement('div');
        card.className = 'news-card trends-card';
        let listHtml = trends.map((t, i) =>
            `<li><span class="trend-rank">${i + 1}</span><a href="${t.url}" target="_blank" class="trend-link">${t.title}</a></li>`
        ).join('');
        const sourceLink = info.url
            ? `<a href="${info.url}" target="_blank" class="trends-source">Google Trends ↗</a>`
            : '';
        card.innerHTML = `
            <div class="trends-header">
                <h3 class="card-title">${info.label} 熱門搜尋</h3>
                ${sourceLink}
            </div>
            <ol class="trends-list">${listHtml}</ol>
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
        if (currentCategory === 'all' && item.categoryCode === 'trends') return false;
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
        card.innerHTML = `
            <div class="card-header">
                <div class="tags">
                    ${breakingHtml}
                    <span class="tag ${st.c}">${st.t}</span>
                    <span class="tag category-tag">${item.categoryName}</span>
                </div>
                <div class="actions">
                    <button class="action-btn ${isSaved ? 'saved' : ''}" onclick="toggleSaved('${item.id}', this)" title="收藏">★</button>
                    <button class="action-btn ${isRead ? 'read' : ''}" onclick="toggleRead('${item.id}', this)" title="標示為已讀">✓</button>
                </div>
            </div>
            <h3 class="card-title">${item.title}</h3>
            <p class="card-summary">${item.summary_zh}</p>
            <div class="card-footer">
                <div class="meta-info">
                    <span>${item.source}</span>
                    <span>•</span>
                    <span>${timeStr}</span>
                </div>
                <a href="${item.url}" target="_blank" class="read-more">原文來源</a>
            </div>
        `;
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
