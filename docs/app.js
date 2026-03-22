import { fetchNewsData, CATEGORY_NAMES } from './modules/api.js';
import { renderHeader, renderWidgets, renderNews } from './modules/render.js';
import { toggleSaved, toggleRead } from './modules/storage.js';
import { toggleChat, sendChat } from './modules/chat.js';

// Module-scoped state — no globals, no window.*
const state = {
    allNews: [],
    currentCategory: 'all',
    searchQuery: '',
    filterUnread: false,
    filterSaved: false,
};

const newsItemMap = new Map();

// DOM references
const newsContainer = document.getElementById('newsContainer');
const loadingEl = document.getElementById('loading');
const errorMsgEl = document.getElementById('errorMsg');
const searchInput = document.getElementById('searchInput');
const sidebar = document.getElementById('sidebar');
const sidebarOverlay = document.getElementById('sidebarOverlay');

// --- Bootstrap ---

fetchData();
setupSidebarEvents();
setupDelegation();

// --- Data ---

async function fetchData() {
    try {
        const data = await fetchNewsData();

        state.allNews = [];
        for (const [cat, items] of Object.entries(data.categories)) {
            items.forEach(item => {
                item.categoryCode = cat;
                item.categoryName = CATEGORY_NAMES[cat] || cat;
                state.allNews.push(item);
                newsItemMap.set(item.id, item);
            });
        }

        renderHeader(data.generated_at);
        renderWidgets(data);
        doRender();

        loadingEl.style.display = 'none';
        errorMsgEl.style.display = 'none';
    } catch (error) {
        console.error('Fetch error:', error);
        loadingEl.style.display = 'none';
        errorMsgEl.style.display = 'block';
    }
}

function doRender() {
    renderNews(newsContainer, state.allNews, {
        currentCategory: state.currentCategory,
        searchQuery: state.searchQuery,
        filterUnread: state.filterUnread,
        filterSaved: state.filterSaved,
    });
}

// --- Sidebar & Filter Events ---

function setupSidebarEvents() {
    searchInput.addEventListener('input', (e) => {
        state.searchQuery = e.target.value.trim().toLowerCase();
        doRender();
    });

    // Category chips — delegation on menu container
    document.getElementById('categoryMenu').addEventListener('click', (e) => {
        const chip = e.target.closest('.chip');
        if (!chip) return;
        document.querySelectorAll('.chip').forEach(b => b.classList.remove('active'));
        chip.classList.add('active');
        state.currentCategory = chip.dataset.category;
        doRender();
        sidebar.classList.remove('show');
        sidebarOverlay.classList.remove('show');
    });

    document.getElementById('filterUnread').addEventListener('change', (e) => {
        state.filterUnread = e.target.checked;
        doRender();
    });

    document.getElementById('filterSaved').addEventListener('change', (e) => {
        state.filterSaved = e.target.checked;
        doRender();
    });

    document.getElementById('mobileMenuBtn').addEventListener('click', () => {
        sidebar.classList.toggle('show');
        sidebarOverlay.classList.toggle('show');
    });

    sidebarOverlay.addEventListener('click', () => {
        sidebar.classList.remove('show');
        sidebarOverlay.classList.remove('show');
    });

    // Mobile tooltips for market indicators
    document.querySelectorAll('.market-name[title]').forEach(el => {
        el.addEventListener('click', () => {
            document.querySelectorAll('.mobile-tooltip').forEach(t => t.remove());
            const tooltip = document.createElement('div');
            tooltip.className = 'mobile-tooltip';
            tooltip.textContent = el.getAttribute('title');
            el.parentElement.appendChild(tooltip);
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

// --- Event Delegation for News Cards ---

function setupDelegation() {
    newsContainer.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;

        const action = btn.dataset.action;
        const id = btn.dataset.id;

        switch (action) {
            case 'save': {
                const isSaved = toggleSaved(id);
                btn.classList.toggle('saved', isSaved);
                if (state.filterSaved) doRender();
                break;
            }
            case 'read': {
                const isRead = toggleRead(id);
                btn.classList.toggle('read', isRead);
                btn.closest('.news-card').classList.toggle('is-read', isRead);
                if (state.filterUnread) doRender();
                break;
            }
            case 'ask-ai':
                toggleChat(id);
                break;
            case 'send-chat':
                sendChat(id, newsItemMap);
                break;
        }
    });

    newsContainer.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.target.dataset.action === 'chat-input') {
            sendChat(e.target.dataset.id, newsItemMap);
        }
    });
}
