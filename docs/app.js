// Data State
let newsData = { categories: {}, market: {}, risk: {} };
let allNews = [];
let currentCategory = 'all';
let searchQuery = '';
let filterUnread = false;
let filterSaved = false;

const CATEGORY_NAMES = {
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
    // Risk Widget
    document.getElementById('riskScore').textContent = `${data.risk_score}/100`;
    const styleElem = document.createElement('style');
    styleElem.innerHTML = `.risk-bar::after { width: ${data.risk_score}%; }`;
    document.head.appendChild(styleElem);

    const riskBar = document.getElementById('riskBar');
    riskBar.className = `risk-bar ${data.risk_level}`;

    const levelMap = { 'normal': '🟢 正常', 'watch': '🟡 留意', 'danger': '🔴 高風險' };
    document.getElementById('riskLevelText').textContent = levelMap[data.risk_level] || data.risk_level;

    const signalsList = document.getElementById('riskSignals');
    signalsList.innerHTML = data.risk_signals.slice(0, 3).map(s => `<li>⚠️ ${s}</li>`).join('');

    // Market Widget
    const fmt = (price, change) => {
        if (price === null) return { p: '--', c: '', class: '' };
        let cText = '';
        let cClass = '';
        if (change !== null) {
            cText = change > 0 ? `▲ +${change}%` : `▼ ${change}%`;
            cClass = change > 0 ? 'change-up' : 'change-down';
        }
        return { p: price.toLocaleString(), c: cText, class: cClass };
    };

    const twii = data.market.TWII || {};
    const sp500 = data.market.SP500 || {};
    const vix = data.market.VIX || {};
    const tnx = data.market.TNX || {};

    const twiiData = fmt(twii.price, twii.change_pct);
    document.querySelector('#market-TWII .market-price').textContent = twiiData.p;
    document.querySelector('#market-TWII .market-change').textContent = twiiData.c;
    document.querySelector('#market-TWII .market-change').className = `market-change ${twiiData.class}`;

    const sp500Data = fmt(sp500.price, sp500.change_pct);
    document.querySelector('#market-SP500 .market-price').textContent = sp500Data.p;
    document.querySelector('#market-SP500 .market-change').textContent = sp500Data.c;
    document.querySelector('#market-SP500 .market-change').className = `market-change ${sp500Data.class}`;

    const vixVal = vix.price !== null ? vix.price : '--';
    const vixEl = document.querySelector('#market-VIX .market-price');
    vixEl.textContent = vixVal;
    if (vix.price > 25) vixEl.classList.add('text-danger');

    document.querySelector('#market-TNX .market-price').textContent = tnx.price !== null ? `${tnx.price}%` : '--';
}

// Render News
function renderNews() {
    newsContainer.innerHTML = '';
    
    // Get LocalStorage states
    const savedIds = JSON.parse(localStorage.getItem(STORE_SAVED) || '[]');
    const readIds = JSON.parse(localStorage.getItem(STORE_READ) || '[]');

    let filtered = allNews.filter(item => {
        // Category Filter
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
                    <button class="action-btn ${isSaved ? 'saved' : ''}" onclick="toggleSaved('${item.id}', this)" title="收藏">⭐</button>
                    <button class="action-btn ${isRead ? 'read' : ''}" onclick="toggleRead('${item.id}', this)" title="標示為已讀">✓</button>
                </div>
            </div>
            <h3 class="card-title">${item.title}</h3>
            <p class="card-summary" onclick="this.classList.toggle('expanded')">${item.summary_zh}</p>
            <div class="card-footer">
                <div class="meta-info">
                    <span>${item.source}</span>
                    <span>•</span>
                    <span>${timeStr}</span>
                </div>
                <a href="${item.url}" target="_blank" class="read-more">閱讀原文</a>
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
