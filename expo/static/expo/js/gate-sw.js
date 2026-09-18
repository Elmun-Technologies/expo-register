/* Expo Gate Service Worker — offline rejim uchun.
 * Manager telefoni internet uzilganda ham ishlashi uchun
 * yuklangan sahifa va skaner kutubxonasini keshga oladi.
 */

const CACHE = "expo-gate-v1";
const CORE = [
    "/expo/gate/",
    "/static/expo/js/html5-qrcode.min.js",
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE).then((cache) => cache.addAll(CORE))
    );
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener("fetch", (event) => {
    const url = new URL(event.request.url);

    // API so'rovlarni keshlash yo'q — ular offline navbatga tushadi.
    if (url.pathname.includes("/gate/api/")) {
        return;
    }

    if (event.request.method !== "GET") {
        return;
    }

    event.respondWith(
        caches.match(event.request).then((cached) => {
            if (cached) {
                return cached;
            }
            return fetch(event.request)
                .then((response) => {
                    // Faqat bir xil origin static/sahifalarni keshga olish
                    if (response.ok &&
                        (url.origin === self.location.origin) &&
                        (url.pathname.startsWith("/static/") ||
                         url.pathname.startsWith("/expo/"))) {
                        const clone = response.clone();
                        caches.open(CACHE).then((cache) =>
                            cache.put(event.request, clone)
                        );
                    }
                    return response;
                })
                .catch(() => {
                    // Offline: sahifaga qaytish — asosiy gate sahifasi keshda bo'ladi
                    if (event.request.mode === "navigate") {
                        return caches.match("/expo/gate/");
                    }
                    return cached;
                });
        })
    );
});
