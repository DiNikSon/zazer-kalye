// Оболочка сайта: вкладки, ленивая загрузка приложений в iframe, адреса вида #app/key.
// Манифест приложений и ключ маскировки подставляет сборка (tools/bundle.mjs).
(function () {
  var M = %MANIFEST%;          // {app: {f: 'a/….bin', t: 'Заголовок', s: 1 — можно скрыть шапку}}
  var K = %KEY%;               // байты для снятия маскировки
  var ORDER = Object.keys(M);
  var DEF = ORDER[0];
  var stage = document.getElementById('stage');
  var ld = document.getElementById('ld');
  var tabs = document.querySelectorAll('#tabs a[data-app]');
  var soloBtn = document.getElementById('soloBtn');
  // ?solo в адресе — без шапки: ссылка для игрока, чтобы не было вкладок
  var SOLO = /[?&]solo(?:[=&]|$)/.test(location.search);
  var frames = {}, pend = {}, last = {}, data = {}, cur = null;

  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }
  function base() { return location.href.split('#')[0]; }
  function hashFor(app, key) { return '#' + app + (key ? '/' + encodeURIComponent(key) : ''); }

  function fetchApp(app) {
    if (!data[app]) data[app] = fetch(M[app].f).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.arrayBuffer();
    }).then(function (buf) {
      var b = new Uint8Array(buf);
      for (var i = 0; i < b.length; i++) b[i] ^= K[i % K.length];
      var s = new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'));
      return new Response(s).text();
    });
    return data[app];
  }

  function busy(text) {
    ld.textContent = text || '';
    ld.hidden = !text;
  }

  function mount(app) {
    var f = frames[app];
    if (f) return f;
    f = frames[app] = { el: document.createElement('iframe'), win: null };
    f.el.title = M[app].t;
    f.el.setAttribute('allow', 'clipboard-read; clipboard-write; fullscreen');
    stage.appendChild(f.el);
    if (typeof DecompressionStream === 'undefined') {
      busy('Браузер слишком старый: обновите его, чтобы открыть сайт.');
      return f;
    }
    fetchApp(app).then(function (html) { f.el.srcdoc = html; }, function () {
      if (cur === app) busy('Не удалось загрузить. Проверьте соединение и обновите страницу.');
      delete data[app];
      delete frames[app];
      f.el.remove();
    });
    return f;
  }

  function activate(app) {
    cur = app;
    var f = mount(app);
    for (var k in frames) frames[k].el.classList.toggle('on', k === app);
    soloBtn.hidden = SOLO || !M[app].s; // до прокрутки вкладок: кнопка сужает их полосу
    for (var i = 0; i < tabs.length; i++) {
      var on = tabs[i].getAttribute('data-app') === app;
      if (on) { tabs[i].setAttribute('aria-current', 'page'); tabs[i].scrollIntoView({ block: 'nearest', inline: 'nearest' }); }
      else tabs[i].removeAttribute('aria-current');
    }
    document.title = M[app].t;
    busy(f.win ? '' : 'Загрузка…');
    if (SOLO) return;
    store('zz-tab', app);
    // пока пользователь смотрит одно, тихо подтягиваем остальное
    setTimeout(function () { ORDER.forEach(function (a) { fetchApp(a).catch(function () {}); }); }, 1500);
  }

  function go(app, key, push) {
    if (!M[app]) return;
    if (key) last[app] = key;
    var h = hashFor(app, last[app]);
    if (h !== location.hash) history[push && app !== cur ? 'pushState' : 'replaceState'](null, '', h);
    activate(app);
    var f = frames[app];
    if (!key) return;
    if (f.win && f.win.__zzNav) f.win.__zzNav(key);
    else pend[app] = key;
  }

  // режим без шапки следует за адресом: «назад» с ?solo на адрес без него возвращает шапку
  function syncSolo() {
    SOLO = /[?&]solo(?:[=&]|$)/.test(location.search);
    document.documentElement.classList.toggle('solo', SOLO);
    if (cur) soloBtn.hidden = SOLO || !M[cur].s;
  }

  function route() {
    syncSolo();
    var h = location.hash.slice(1), i = h.indexOf('/');
    var app = i < 0 ? h : h.slice(0, i), key = i < 0 ? '' : decodeURIComponent(h.slice(i + 1));
    if (!M[app]) { app = store('zz-tab'); if (!M[app]) app = DEF; key = ''; }
    if (app === cur && !key) return;
    go(app, key, false);
  }

  window.__zz = {
    go: go,
    url: function (app, key) { return base() + hashFor(app, key); },
    loc: function (app, key) {
      last[app] = key;
      if (app === cur) history.replaceState(null, '', hashFor(app, key));
    },
    ready: function (app, win) {
      var f = frames[app];
      if (!f) return;
      f.win = win;
      if (cur === app) busy('');
      var k = pend[app];
      delete pend[app];
      if (k && win.__zzNav) win.__zzNav(k);
    }
  };

  for (var i = 0; i < tabs.length; i++) tabs[i].addEventListener('click', function (e) {
    if (e.button || e.ctrlKey || e.metaKey || e.shiftKey) return;
    e.preventDefault();
    var app = this.getAttribute('data-app');
    go(app, '', true);
  });
  document.querySelector('.brand').addEventListener('click', function (e) {
    if (e.button || e.ctrlKey || e.metaKey || e.shiftKey) return;
    e.preventDefault();
    go(DEF, '', true);
  });
  soloBtn.addEventListener('click', function () {
    var q = location.search ? location.search + '&solo' : '?solo';
    history.pushState(null, '', location.pathname + q + location.hash); // «назад» вернёт шапку
    syncSolo();
  });
  addEventListener('popstate', route);
  addEventListener('hashchange', route);
  route();
})();
