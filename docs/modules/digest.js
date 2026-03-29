/**
 * 今日脈絡 — 主題深度分析 + 板塊/訊號/風險/轉折 + 試用機制
 */
import { escapeHtml } from './render.js';
import { supabase } from './supabase.js';

const TRIAL_DAYS = 30;
const TRIAL_KEY = 'digest_trial_start';

// --- Trial Logic ---

function getTrialStart() {
    const stored = localStorage.getItem(TRIAL_KEY);
    if (stored) return new Date(stored);
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

// --- Section Renderers ---

function renderMarketSnapshot(digest) {
    const snap = digest.market_snapshot;
    if (!snap || !snap.mood) return '';
    return `<div class="digest-market-snapshot">
        <span class="digest-snapshot-mood">市場氛圍：${escapeHtml(snap.mood)}</span>
        ${snap.key_moves ? `<span class="digest-snapshot-moves">${escapeHtml(snap.key_moves)}</span>` : ''}
    </div>`;
}

function renderDataTable(digest) {
    const table = digest.data_table;
    if (!table || Object.keys(table).length === 0) return '';

    const groupLabels = {
        indices: '📊 指數',
        commodities: '🛢️ 商品',
        forex: '💱 外匯',
        bonds_volatility: '📈 債券 / 波動',
    };

    let html = '<div class="digest-section">';
    html += '<h3 class="digest-section-title">📋 市場數據</h3>';
    html += '<div class="digest-data-table">';

    for (const [groupKey, items] of Object.entries(table)) {
        const label = groupLabels[groupKey] || groupKey;
        html += `<div class="digest-data-group">`;
        html += `<div class="digest-data-group-label">${label}</div>`;
        html += '<div class="digest-data-items">';
        for (const item of items) {
            const chg = item.change_pct;
            const chgStr = chg != null ? `${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%` : '—';
            const chgClass = chg > 0 ? 'up' : chg < 0 ? 'down' : '';
            const statusClass = item.status === 'danger' ? 'digest-data-danger'
                : item.status === 'warn' ? 'digest-data-warn' : '';
            html += `<div class="digest-data-item ${statusClass}">
                <span class="digest-data-name">${escapeHtml(item.name)}</span>
                <span class="digest-data-price">${item.price}</span>
                <span class="digest-data-chg ${chgClass}">${chgStr}</span>
            </div>`;
        }
        html += '</div></div>';
    }
    html += '</div></div>';
    return html;
}

function renderKeyThemes(digest, hasAccess) {
    const themes = digest.key_themes;
    if (!themes || themes.length === 0) return '';

    let html = '<div class="digest-section">';
    html += '<h3 class="digest-section-title">🎯 重點主題</h3>';
    html += '<div class="digest-themes">';
    themes.forEach((theme, i) => {
        const blurred = !hasAccess && i >= 2;
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
    return html;
}

function renderSectorAnalysis(digest, hasAccess) {
    const sectors = digest.sector_analysis;
    if (!sectors || sectors.length === 0) return '';

    const directionColors = {
        '看多': 'digest-signal-bull',
        '看空': 'digest-signal-bear',
        '中性': 'digest-signal-neutral',
        '分歧': 'digest-signal-mixed',
    };

    let html = `<div class="digest-section ${!hasAccess ? 'digest-section-blurred' : ''}">`;
    html += '<h3 class="digest-section-title">🏭 板塊分析</h3>';
    html += '<div class="digest-sectors">';
    sectors.forEach(s => {
        const cls = directionColors[s.direction] || 'digest-signal-neutral';
        html += `<div class="digest-sector-item">
            <div class="digest-sector-header">
                <span class="digest-sector-name">${escapeHtml(s.sector)}</span>
                <span class="digest-direction-badge ${cls}">${escapeHtml(s.direction)}</span>
            </div>
            <div class="digest-sector-detail">${escapeHtml(s.reasoning)}</div>
            ${s.key_ticker ? `<div class="digest-sector-ticker">${escapeHtml(s.key_ticker)}</div>` : ''}
        </div>`;
    });
    html += '</div></div>';
    return html;
}

function renderActionSignals(digest, hasAccess) {
    const signals = digest.action_signals;
    if (!signals || signals.length === 0) return '';

    const signalColors = {
        '短多': 'digest-signal-bull',
        '短空': 'digest-signal-bear',
        '觀望': 'digest-signal-neutral',
        '轉折': 'digest-signal-mixed',
    };
    const confLabels = { '高': '●●●', '中高': '●●○', '中': '●○○', '低': '○○○' };

    let html = `<div class="digest-section ${!hasAccess ? 'digest-section-blurred' : ''}">`;
    html += '<h3 class="digest-section-title">⚡ 操作訊號</h3>';
    html += '<div class="digest-signals">';
    signals.forEach(sig => {
        const cls = signalColors[sig.signal] || 'digest-signal-neutral';
        const conf = confLabels[sig.confidence] || sig.confidence || '';
        html += `<div class="digest-signal-item">
            <div class="digest-signal-header">
                <span class="digest-signal-asset">${escapeHtml(sig.asset)}</span>
                <span class="digest-direction-badge ${cls}">${escapeHtml(sig.signal)}</span>
                <span class="digest-signal-conf" title="信心度">${conf}</span>
            </div>
            <div class="digest-signal-reason">${escapeHtml(sig.reasoning)}</div>
        </div>`;
    });
    html += '</div></div>';
    return html;
}

function renderRiskRadar(digest, hasAccess) {
    const risks = digest.risk_radar;
    if (!risks || risks.length === 0) return '';

    const probColors = { '高': 'digest-risk-high', '中': 'digest-risk-mid', '低': 'digest-risk-low' };

    let html = `<div class="digest-section ${!hasAccess ? 'digest-section-blurred' : ''}">`;
    html += '<h3 class="digest-section-title">🛡️ 風險雷達</h3>';
    html += '<div class="digest-risks">';
    risks.forEach(r => {
        const probCls = probColors[r.probability] || 'digest-risk-low';
        html += `<div class="digest-risk-item">
            <div class="digest-risk-header">
                <span class="digest-risk-event">${escapeHtml(r.event)}</span>
                <span class="digest-risk-badges">
                    <span class="digest-risk-badge ${probCls}">機率 ${escapeHtml(r.probability)}</span>
                    <span class="digest-risk-badge">衝擊 ${escapeHtml(r.impact)}</span>
                    ${r.timeframe ? `<span class="digest-watch-timeframe">${escapeHtml(r.timeframe)}</span>` : ''}
                </span>
            </div>
            ${r.description ? `<div class="digest-risk-desc">${escapeHtml(r.description)}</div>` : ''}
        </div>`;
    });
    html += '</div></div>';
    return html;
}

function renderNarrativeShift(digest, hasAccess) {
    const shift = digest.narrative_shift;
    if (!shift) return '';

    const categories = [
        { key: 'new_themes', label: '🆕 新出現', cls: 'digest-shift-new' },
        { key: 'escalated', label: '🔺 升溫', cls: 'digest-shift-up' },
        { key: 'cooled', label: '🔻 降溫', cls: 'digest-shift-down' },
        { key: 'disappeared', label: '💨 消失', cls: 'digest-shift-gone' },
    ];

    const hasContent = categories.some(c => shift[c.key] && shift[c.key].length > 0);
    if (!hasContent) return '';

    let html = `<div class="digest-section ${!hasAccess ? 'digest-section-blurred' : ''}">`;
    html += '<h3 class="digest-section-title">🔄 敘事轉折</h3>';
    html += '<div class="digest-shifts">';
    categories.forEach(cat => {
        const items = shift[cat.key];
        if (!items || items.length === 0) return;
        html += `<div class="digest-shift-row">
            <span class="digest-shift-label ${cat.cls}">${cat.label}</span>
            <span class="digest-shift-items">${items.map(t => escapeHtml(t)).join('、')}</span>
        </div>`;
    });
    html += '</div></div>';
    return html;
}

function renderWatchNext(digest, hasAccess) {
    const items = digest.watch_next;
    if (!items || items.length === 0) return '';

    let html = `<div class="digest-section ${!hasAccess ? 'digest-section-blurred' : ''}">`;
    html += '<h3 class="digest-section-title">👀 觀察方向</h3>';
    html += '<div class="digest-watch">';
    items.forEach(w => {
        const timeframe = w.timeframe ? `<span class="digest-watch-timeframe">${escapeHtml(w.timeframe)}</span>` : '';
        html += `<div class="digest-watch-item">
            <div class="digest-watch-topic">${escapeHtml(w.topic)}${timeframe}</div>
            <div class="digest-watch-reason">${escapeHtml(w.reason)}</div>
        </div>`;
    });
    html += '</div></div>';
    return html;
}

function renderCrossLinks(digest, hasAccess) {
    const links = digest.cross_links;
    if (!links || links.length === 0) return '';

    let html = `<div class="digest-section ${!hasAccess ? 'digest-section-blurred' : ''}">`;
    html += '<h3 class="digest-section-title">🔗 跨主題關聯</h3>';
    html += '<div class="digest-cross">';
    links.forEach(link => {
        const themes = (link.themes || []).map(t => escapeHtml(t)).join(' ↔ ');
        const explain = link.chain || link.explanation || '';
        html += `<div class="digest-cross-item">
            <div class="digest-cross-themes">${themes}</div>
            <div class="digest-cross-explain">${escapeHtml(explain)}</div>
        </div>`;
    });
    html += '</div></div>';
    return html;
}

// --- Main Render ---

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

    let html = '<div class="digest-container">';
    html += '<h2 class="digest-title">📰 今日脈絡</h2>';

    // Trial badge
    if (loggedIn && trialActive) {
        html += `<span class="digest-trial-badge">免費試用中（剩 ${daysLeft} 天）</span>`;
    }

    // Render all sections in order
    html += renderMarketSnapshot(digest);
    html += renderDataTable(digest);
    html += renderNarrativeShift(digest, hasAccess);
    html += renderKeyThemes(digest, hasAccess);
    html += renderSectorAnalysis(digest, hasAccess);
    html += renderActionSignals(digest, hasAccess);
    html += renderRiskRadar(digest, hasAccess);
    html += renderWatchNext(digest, hasAccess);
    html += renderCrossLinks(digest, hasAccess);

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
