/**
 * 今日脈絡 — 主題深度分析 + 試用機制
 */
import { escapeHtml } from './render.js';
import { supabase } from './supabase.js';

const TRIAL_DAYS = 30;
const TRIAL_KEY = 'digest_trial_start';

// --- Trial Logic ---

function getTrialStart() {
    const stored = localStorage.getItem(TRIAL_KEY);
    if (stored) return new Date(stored);
    // 首次訪問，記錄試用開始
    const now = new Date();
    localStorage.setItem(TRIAL_KEY, now.toISOString());
    return now;
}

function getTrialDaysLeft() {
    const start = getTrialStart();
    const elapsed = (Date.now() - start.getTime()) / (1000 * 60 * 60 * 24);
    return Math.max(0, Math.ceil(TRIAL_DAYS - elapsed));
}

function isTrialActive() {
    return getTrialDaysLeft() > 0;
}

// --- Render ---

export function renderDigest(container, digest, user) {
    if (!digest) {
        container.style.display = 'none';
        return;
    }
    container.style.display = 'block';

    const loggedIn = !!user;
    const trialActive = isTrialActive();
    const daysLeft = getTrialDaysLeft();
    const hasAccess = loggedIn && trialActive;
    // Show full content if trial active (logged in), or show partial with blur

    let html = '<div class="digest-container">';
    html += '<h2 class="digest-title">📰 今日脈絡</h2>';

    // Trial badge
    if (loggedIn && trialActive) {
        html += `<span class="digest-trial-badge">免費試用中（剩 ${daysLeft} 天）</span>`;
    }

    // Market Snapshot
    if (digest.market_snapshot && digest.market_snapshot.mood) {
        const snap = digest.market_snapshot;
        html += `<div class="digest-market-snapshot">
            <span class="digest-snapshot-mood">市場氛圍：${escapeHtml(snap.mood)}</span>
            ${snap.key_moves ? `<span class="digest-snapshot-moves">${escapeHtml(snap.key_moves)}</span>` : ''}
        </div>`;
    }

    // Key Themes
    if (digest.key_themes && digest.key_themes.length > 0) {
        html += '<div class="digest-section">';
        html += '<h3 class="digest-section-title">🎯 重點主題</h3>';
        html += '<div class="digest-themes">';
        digest.key_themes.forEach((theme, i) => {
            const blurred = !hasAccess && i >= 2;
            // Support both new 4-layer format and legacy summary format
            const hasLayers = theme.background || theme.development || theme.impact || theme.conclusion;
            let bodyHtml = '';
            if (hasLayers) {
                const layers = [
                    { label: '前因', text: theme.background, icon: '📋' },
                    { label: '經過', text: theme.development, icon: '📰' },
                    { label: '影響', text: theme.impact, icon: '💥' },
                    { label: '結論', text: theme.conclusion, icon: '🔮' },
                ];
                bodyHtml = layers
                    .filter(l => l.text)
                    .map(l => `<div class="digest-theme-layer"><span class="digest-layer-label">${l.icon} ${l.label}</span><span class="digest-layer-text">${escapeHtml(l.text)}</span></div>`)
                    .join('');
            } else {
                bodyHtml = `<div class="digest-theme-summary">${escapeHtml(theme.summary || '').replace(/\n/g, '<br>')}</div>`;
            }
            const regionTag = theme.region ? `<span class="digest-theme-region">${escapeHtml(theme.region)}</span>` : '';
            html += `<div class="digest-theme ${blurred ? 'digest-theme-blurred' : ''}">
                <div class="digest-theme-header"><div class="digest-theme-title">${escapeHtml(theme.title)}</div>${regionTag}</div>
                ${bodyHtml}
            </div>`;
        });
        html += '</div></div>';
    }

    // Watch Next
    if (digest.watch_next && digest.watch_next.length > 0) {
        const watchBlurred = !hasAccess;
        html += `<div class="digest-section ${watchBlurred ? 'digest-section-blurred' : ''}">`;
        html += '<h3 class="digest-section-title">👀 觀察方向</h3>';
        html += '<div class="digest-watch">';
        digest.watch_next.forEach(w => {
            const timeframe = w.timeframe ? `<span class="digest-watch-timeframe">${escapeHtml(w.timeframe)}</span>` : '';
            html += `<div class="digest-watch-item">
                <div class="digest-watch-topic">${escapeHtml(w.topic)}${timeframe}</div>
                <div class="digest-watch-reason">${escapeHtml(w.reason)}</div>
            </div>`;
        });
        html += '</div></div>';
    }

    // Cross Links
    if (digest.cross_links && digest.cross_links.length > 0) {
        const crossBlurred = !hasAccess;
        html += `<div class="digest-section ${crossBlurred ? 'digest-section-blurred' : ''}">`;
        html += '<h3 class="digest-section-title">🔗 跨主題關聯</h3>';
        html += '<div class="digest-cross">';
        digest.cross_links.forEach(link => {
            const themes = (link.themes || []).map(t => escapeHtml(t)).join(' ↔ ');
            const explain = link.chain || link.explanation || '';
            html += `<div class="digest-cross-item">
                <div class="digest-cross-themes">${themes}</div>
                <div class="digest-cross-explain">${escapeHtml(explain)}</div>
            </div>`;
        });
        html += '</div></div>';
    }

    // Paywall CTA
    if (!hasAccess) {
        html += '<div class="digest-paywall">';
        if (!loggedIn) {
            html += '<p>登入即可免費試用 30 天完整脈絡分析</p>';
            html += '<button class="digest-cta-btn" id="digestLoginBtn">登入試用</button>';
        } else {
            html += '<p>試用期已結束，升級方案解鎖完整脈絡分析</p>';
            html += '<button class="digest-cta-btn" disabled>即將推出</button>';
        }
        html += '</div>';
    }

    html += '</div>';
    container.innerHTML = html;

    // Bind login button
    const loginBtn = container.querySelector('#digestLoginBtn');
    if (loginBtn) {
        loginBtn.addEventListener('click', async () => {
            const { signInWithGoogle } = await import('./supabase.js');
            await signInWithGoogle();
        });
    }
}
