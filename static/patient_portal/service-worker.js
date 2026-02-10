// Service Worker - Placeholder for offline PWA support
// This file is intentionally minimal

self.addEventListener('install', function(event) {
    self.skipWaiting();
});

self.addEventListener('activate', function(event) {
    event.waitUntil(clients.claim());
});

self.addEventListener('fetch', function(event) {
    // Pass through all requests (no caching)
    return;
});
