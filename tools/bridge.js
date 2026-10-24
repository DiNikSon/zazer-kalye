// Мост внутри каждого приложения (iframe). Подставляется сборкой первым скриптом.
// Строку APP сборка заменяет на id приложения.
(function () {
  var APP = '%APP%', P = null;
  try { if (parent !== window && parent.__zz) P = parent.__zz; } catch (e) {}

  // history.replaceState('#id') внутри iframe не работает (about:srcdoc),
  // поэтому сообщаем оболочке, где мы, — она обновит адрес страницы.
  var H = history, rs = H.replaceState;
  H.replaceState = function (s, t, u) {
    if (typeof u === 'string' && u.charAt(0) === '#') {
      if (P) P.loc(APP, decodeURIComponent(u.slice(1)));
      return;
    }
    try { return rs.apply(H, arguments); } catch (e) {}
  };

  // Ссылки вида zz:app?…#key — переходы между приложениями.
  function parse(h) {
    var m = /^zz:([a-z]+)[^#]*(?:#(.*))?$/.exec(h || '');
    return m ? { app: m[1], key: m[2] ? decodeURIComponent(m[2]) : '' } : null;
  }
  // Перед кликом превращаем zz:-ссылку в настоящий адрес — чтобы работали
  // «открыть в новой вкладке» и копирование ссылки.
  function fix(e) {
    var a = e.target && e.target.closest && e.target.closest('a[href^="zz:"]');
    if (!a) return;
    var z = parse(a.getAttribute('href'));
    if (!z) return;
    a.setAttribute('data-zz-app', z.app);
    a.setAttribute('data-zz-key', z.key);
    if (P) a.href = P.url(z.app, z.key);
  }
  ['pointerover', 'focusin', 'mousedown', 'touchstart', 'contextmenu'].forEach(function (t) {
    addEventListener(t, fix, { capture: true, passive: true });
  });

  addEventListener('click', function (e) {
    if (e.defaultPrevented || e.button) return;
    var a = e.target && e.target.closest && e.target.closest('a[href]');
    if (!a) return;
    var h = a.getAttribute('href') || '';
    var z = a.hasAttribute('data-zz-app')
      ? { app: a.getAttribute('data-zz-app'), key: a.getAttribute('data-zz-key') || '' }
      : parse(h);
    if (z) {
      if (e.ctrlKey || e.metaKey || e.shiftKey) return; // откроется настоящая ссылка
      e.preventDefault();
      if (P) P.go(z.app, z.key, true);
      return;
    }
    // Голый #якорь в about:srcdoc увёл бы iframe на адрес сайта — прокручиваем сами.
    if (h.charAt(0) === '#') {
      e.preventDefault();
      var id = decodeURIComponent(h.slice(1));
      var el = id && (document.getElementById(id) || document.getElementsByName(id)[0]);
      if (el) el.scrollIntoView({ block: 'start' });
    }
  });

  document.addEventListener('DOMContentLoaded', function () { if (P) P.ready(APP, window); });
})();
