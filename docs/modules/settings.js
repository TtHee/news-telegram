/**
 * User settings — persisted in localStorage.
 */

const SETTINGS_KEY = 'pulse_settings';

const DEFAULTS = {
    twiiFormat: 'percent',   // 'percent' | 'points'
    sortMode: 'breaking',    // 'breaking' | 'time'
    darkMode: false,
};

let _cache = null;

export function getSettings() {
    if (_cache) return _cache;
    try {
        const stored = localStorage.getItem(SETTINGS_KEY);
        _cache = stored ? { ...DEFAULTS, ...JSON.parse(stored) } : { ...DEFAULTS };
    } catch {
        _cache = { ...DEFAULTS };
    }
    return _cache;
}

export function updateSetting(key, value) {
    const settings = getSettings();
    settings[key] = value;
    _cache = settings;
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
}

export function applyDarkMode(enabled) {
    if (enabled) {
        document.documentElement.setAttribute('data-theme', 'dark');
    } else {
        document.documentElement.removeAttribute('data-theme');
    }
}
