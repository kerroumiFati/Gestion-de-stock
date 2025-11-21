/**
 * Service Worker for Progressive Web App
 * Provides offline functionality and caching
 */

const CACHE_NAME = 'gestion-stock-v1.0.0';
const STATIC_CACHE = 'static-v1.0.0';
const DYNAMIC_CACHE = 'dynamic-v1.0.0';

// Files to cache immediately
const STATIC_FILES = [
    '/',
    '/static/style/modern-theme.css',
    '/static/js/modern-ui.js',
    '/static/js/main.js',
    '/static/img/no-photo.png',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://code.jquery.com/jquery-3.7.0.min.js'
];

// Files to cache on demand
const DYNAMIC_FILES = [
    '/api/',
    '/frontoffice/'
];

// Install event - cache static files
self.addEventListener('install', (event) => {
    console.log('Service Worker installing...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => {
                console.log('Caching static files...');
                return cache.addAll(STATIC_FILES);
            })
            .catch((error) => {
                console.error('Failed to cache static files:', error);
            })
    );
    
    // Force activation
    self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('Service Worker activating...');
    
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cacheName) => {
                        if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
                            console.log('Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('Service Worker activated');
                return self.clients.claim();
            })
    );
});

// Fetch event - serve cached files or fetch from network
self.addEventListener('fetch', (event) => {
    const request = event.request;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }
    
    // Skip Chrome extension requests
    if (url.protocol === 'chrome-extension:') {
        return;
    }
    
    event.respondWith(
        caches.match(request)
            .then((cachedResponse) => {
                if (cachedResponse) {
                    // Return cached version
                    return cachedResponse;
                }
                
                // Fetch from network
                return fetch(request)
                    .then((response) => {
                        // Check if response is valid
                        if (!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }
                        
                        // Clone response for caching
                        const responseToCache = response.clone();
                        
                        // Cache dynamic content
                        if (shouldCacheDynamically(request.url)) {
                            caches.open(DYNAMIC_CACHE)
                                .then((cache) => {
                                    cache.put(request, responseToCache);
                                });
                        }
                        
                        return response;
                    })
                    .catch((error) => {
                        console.error('Fetch failed:', error);
                        
                        // Return offline page for navigation requests
                        if (request.destination === 'document') {
                            return caches.match('/offline.html');
                        }
                        
                        // Return placeholder for images
                        if (request.destination === 'image') {
                            return caches.match('/static/img/offline-placeholder.png');
                        }
                        
                        throw error;
                    });
            })
    );
});

// Background sync for offline actions
self.addEventListener('sync', (event) => {
    console.log('Background sync triggered:', event.tag);
    
    if (event.tag === 'background-sync') {
        event.waitUntil(syncOfflineActions());
    }
});

// Push notifications
self.addEventListener('push', (event) => {
    if (!event.data) return;
    
    const data = event.data.json();
    const options = {
        body: data.body,
        icon: '/static/img/icon-192x192.png',
        badge: '/static/img/badge-72x72.png',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: data.primaryKey || 1
        },
        actions: [
            {
                action: 'explore',
                title: 'View Details',
                icon: '/static/img/checkmark.png'
            },
            {
                action: 'close',
                title: 'Close',
                icon: '/static/img/xmark.png'
            }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// Notification click handling
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    
    if (event.action === 'close') {
        return;
    }
    
    // Open app when notification is clicked
    event.waitUntil(
        clients.openWindow('/')
    );
});

// Helper functions
function shouldCacheDynamically(url) {
    return DYNAMIC_FILES.some(pattern => url.includes(pattern));
}

async function syncOfflineActions() {
    try {
        // Get offline actions from IndexedDB
        const offlineActions = await getOfflineActions();
        
        for (const action of offlineActions) {
            try {
                // Attempt to sync action
                await fetch(action.url, {
                    method: action.method,
                    headers: action.headers,
                    body: action.body
                });
                
                // Remove from offline storage if successful
                await removeOfflineAction(action.id);
                
                console.log('Synced offline action:', action.id);
            } catch (error) {
                console.error('Failed to sync action:', action.id, error);
            }
        }
    } catch (error) {
        console.error('Background sync failed:', error);
    }
}

// IndexedDB helpers for offline storage
function openDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('OfflineActions', 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('actions')) {
                const store = db.createObjectStore('actions', { keyPath: 'id', autoIncrement: true });
                store.createIndex('timestamp', 'timestamp', { unique: false });
            }
        };
    });
}

async function getOfflineActions() {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['actions'], 'readonly');
        const store = transaction.objectStore('actions');
        const request = store.getAll();
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
    });
}

async function removeOfflineAction(id) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['actions'], 'readwrite');
        const store = transaction.objectStore('actions');
        const request = store.delete(id);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
    });
}

// Cache management utilities
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'CACHE_UPDATE') {
        event.waitUntil(updateCache());
    }
    
    if (event.data && event.data.type === 'GET_CACHE_SIZE') {
        event.waitUntil(getCacheSize().then(size => {
            event.ports[0].postMessage({ size });
        }));
    }
});

async function updateCache() {
    const cache = await caches.open(STATIC_CACHE);
    const requests = await cache.keys();
    
    return Promise.all(
        requests.map(async (request) => {
            try {
                const response = await fetch(request);
                if (response.status === 200) {
                    await cache.put(request, response);
                }
            } catch (error) {
                console.error('Failed to update cache for:', request.url);
            }
        })
    );
}

async function getCacheSize() {
    const cacheNames = await caches.keys();
    let totalSize = 0;
    
    for (const cacheName of cacheNames) {
        const cache = await caches.open(cacheName);
        const requests = await cache.keys();
        
        for (const request of requests) {
            const response = await cache.match(request);
            if (response) {
                const blob = await response.blob();
                totalSize += blob.size;
            }
        }
    }
    
    return totalSize;
}