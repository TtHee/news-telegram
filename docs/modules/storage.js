const STORE_SAVED = 'news_saved';
const STORE_READ = 'news_read';

export function getSavedIds() {
    return JSON.parse(localStorage.getItem(STORE_SAVED) || '[]');
}

export function getReadIds() {
    return JSON.parse(localStorage.getItem(STORE_READ) || '[]');
}

export function toggleSaved(id) {
    let saved = getSavedIds();
    const wasSaved = saved.includes(id);
    if (wasSaved) {
        saved = saved.filter(x => x !== id);
    } else {
        saved.push(id);
    }
    localStorage.setItem(STORE_SAVED, JSON.stringify(saved));
    return !wasSaved;
}

export function toggleRead(id) {
    let read = getReadIds();
    const wasRead = read.includes(id);
    if (wasRead) {
        read = read.filter(x => x !== id);
    } else {
        read.push(id);
    }
    localStorage.setItem(STORE_READ, JSON.stringify(read));
    return !wasRead;
}
