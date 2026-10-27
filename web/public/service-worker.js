const CACHE_NAME = 'chemlearn-v2';
const ASSETS_TO_CACHE = [
  '/chem/app/',
  '/chem/app/index.html',
  '/chem/app/manifest.json'
];

// 安装：缓存核心资源
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

// 激活：清理旧缓存
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// 拦截请求：缓存优先，网络回退
self.addEventListener('fetch', (event) => {
  // 只缓存 GET 请求
  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.match(event.request).then((cached) => {
      // 缓存命中，直接返回
      if (cached) return cached;

      // 缓存未命中，走网络
      return fetch(event.request)
        .then((response) => {
          // 缓存静态资源
          if (
            response.status === 200 &&
            (event.request.url.includes('/assets/') ||
              event.request.url.includes('.js') ||
              event.request.url.includes('.css') ||
              event.request.url.includes('.png') ||
              event.request.url.includes('.svg') ||
              event.request.url.includes('.woff2'))
          ) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseClone);
            });
          }
          return response;
        })
        .catch(() => {
          // 离线时返回应用首页
          if (event.request.mode === 'navigate') {
            return caches.match('/chem/app/index.html');
          }
        });
    })
  );
});
