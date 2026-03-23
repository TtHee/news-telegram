import { fetchNewsData, CATEGORY_NAMES } from './modules/api.js';
import { renderHeader, renderWidgets, renderNews } from './modules/render.js';
import { renderDigest } from './modules/digest.js';
import { toggleSaved, toggleRead } from './modules/storage.js';
import { toggleChat, sendChat } from './modules/chat.js';
import { signInWithGoogle, signOut, getSession, getProfile, onAuthStateChange } from './modules/supabase.js';

// Module-scoped state — no globals, no window.*
const state = {
    allNews: [],
    currentCategory: 'all',
    searchQuery: '',
    filterUnread: false,
    filterSaved: false,
    user: null,
    profile: null,
    digestData: null,
};

const newsItemMap = new Map();

// DOM references
const newsContainer = document.getElementById('newsContainer');
const loadingEl = document.getElementById('loading');
const errorMsgEl = document.getElementById('errorMsg');
const searchInput = document.getElementById('searchInput');
const sidebar = document.getElementById('sidebar');
const sidebarOverlay = document.getElementById('sidebarOverlay');
const digestContainer = document.getElementById('digestContainer');

// --- Bootstrap ---

initAuth();
fetchData();
setupSidebarEvents();
setupDelegation();
setupAuthEvents();

// --- Auth ---

async function initAuth() {
    // getSession() triggers URL fragment parsing on OAuth redirect
    const session = await getSession();
    await updateAuthUI(session?.user ?? null);

    onAuthStateChange(async (user) => {
        await updateAuthUI(user);
    });
}

async function updateAuthUI(user) {
    state.user = user;
    const authArea = document.getElementById('authArea');

    if (user) {
        try {
            state.profile = await getProfile(user.id);
        } catch {
            state.profile = null;
        }
        const name = state.profile?.display_name || user.user_metadata?.full_name || user.email;
        const avatar = state.profile?.avatar_url || user.user_metadata?.avatar_url;
        authArea.innerHTML = `
            <div class="user-info">
                ${avatar ? `<img class="user-avatar" src="${avatar}" alt="" referrerpolicy="no-referrer">` : ''}
                <span class="user-name">${escapeHtmlAttr(name)}</span>
                <button class="auth-btn auth-btn-outline" id="logoutBtn">登出</button>
            </div>
        `;
    } else {
        state.profile = null;
        authArea.innerHTML = '<button class="auth-btn" id="loginBtn">登入</button>';
    }
    // Re-render digest with updated auth state
    if (state.digestData) {
        renderDigest(digestContainer, state.digestData, state.user);
    }
}

function escapeHtmlAttr(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function setupAuthEvents() {
    document.getElementById('authArea').addEventListener('click', async (e) => {
        if (e.target.id === 'loginBtn') {
            await signInWithGoogle();
        } else if (e.target.id === 'logoutBtn') {
            await signOut();
        }
    });
}

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

        state.digestData = data.daily_digest || null;

        renderHeader(data.generated_at);
        renderWidgets(data);
        renderDigest(digestContainer, state.digestData, state.user);
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
