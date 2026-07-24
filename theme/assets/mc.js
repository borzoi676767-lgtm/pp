/* ==========================================================================
   MILITES CHRISTI — mc.js
   Progressive enhancement only. The store works without JS.
   - Scroll reveals (IntersectionObserver), reduced-motion aware
   - Header shadow on scroll
   - Mobile menu toggle
   - Ajax cart drawer (open/close, count, add-to-cart)
   - Hero dust particles (skipped under reduced-motion)
   ========================================================================== */
(function () {
  'use strict';
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* --- Scroll reveals --- */
  function initReveals() {
    var els = document.querySelectorAll('.mc-reveal');
    if (!els.length) return;
    if (reduceMotion || !('IntersectionObserver' in window)) {
      els.forEach(function (el) { el.classList.add('is-visible'); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('is-visible'); io.unobserve(e.target); }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });
    els.forEach(function (el) { io.observe(el); });
  }

  /* --- Header scroll state --- */
  function initHeader() {
    var header = document.querySelector('[data-mc-header]');
    if (!header) return;
    var onScroll = function () { header.classList.toggle('is-scrolled', window.scrollY > 24); };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  /* --- Mobile menu --- */
  function initMenu() {
    var toggle = document.querySelector('[data-mc-menu-toggle]');
    var nav = document.querySelector('[data-mc-nav-mobile]');
    if (!toggle || !nav) return;
    toggle.addEventListener('click', function () {
      var open = nav.hasAttribute('hidden');
      if (open) { nav.removeAttribute('hidden'); } else { nav.setAttribute('hidden', ''); }
      toggle.setAttribute('aria-expanded', String(open));
    });
  }

  /* --- Cart drawer --- */
  function initCart() {
    var drawer = document.querySelector('[data-mc-drawer]');
    var openers = document.querySelectorAll('[data-mc-cart-open]');
    if (!drawer) return;
    var panel = drawer.querySelector('.mc-drawer__panel');
    var lastFocus = null;

    function open() {
      lastFocus = document.activeElement;
      drawer.classList.add('is-open');
      drawer.setAttribute('aria-hidden', 'false');
      refresh();
      var f = panel.querySelector('button, a, [tabindex]');
      if (f) f.focus();
      document.addEventListener('keydown', onKey);
    }
    function close() {
      drawer.classList.remove('is-open');
      drawer.setAttribute('aria-hidden', 'true');
      document.removeEventListener('keydown', onKey);
      if (lastFocus) lastFocus.focus();
    }
    function onKey(e) { if (e.key === 'Escape') close(); }

    openers.forEach(function (o) { o.addEventListener('click', function (e) { e.preventDefault(); open(); }); });
    drawer.querySelectorAll('[data-mc-cart-close]').forEach(function (c) { c.addEventListener('click', close); });

    function refresh() {
      fetch('/cart.js', { headers: { 'Accept': 'application/json' } })
        .then(function (r) { return r.json(); })
        .then(renderCart).catch(function () {});
    }
    function renderCart(cart) {
      var body = drawer.querySelector('[data-mc-cart-body]');
      var foot = drawer.querySelector('[data-mc-cart-total]');
      updateCounts(cart.item_count);
      if (!body) return;
      if (!cart.items || !cart.items.length) {
        body.innerHTML = '<p class="mc-lead">Your satchel is empty.</p>';
        if (foot) foot.textContent = '';
        return;
      }
      body.innerHTML = cart.items.map(function (it) {
        return '<div class="mc-cart-line"><a href="' + it.url + '">' + it.product_title + '</a>' +
               '<span>' + it.quantity + ' &times; ' + money(it.final_price) + '</span></div>';
      }).join('');
      if (foot) foot.textContent = money(cart.total_price);
    }
    function updateCounts(n) {
      document.querySelectorAll('[data-mc-cart-count]').forEach(function (el) {
        el.textContent = n; el.hidden = n === 0;
      });
    }
    function money(cents) {
      return (window.Shopify && Shopify.currency ? Shopify.currency.active + ' ' : '$') + (cents / 100).toFixed(2);
    }

    /* Ajax add-to-cart */
    document.addEventListener('submit', function (e) {
      var form = e.target;
      if (!form.matches('[data-mc-add-form]')) return;
      e.preventDefault();
      var btn = form.querySelector('[type="submit"]');
      if (btn) btn.setAttribute('aria-busy', 'true');
      fetch('/cart/add.js', { method: 'POST', body: new FormData(form), headers: { 'Accept': 'application/json' } })
        .then(function (r) { return r.json(); })
        .then(function () { open(); })
        .catch(function () { form.submit(); })
        .finally(function () { if (btn) btn.removeAttribute('aria-busy'); });
    });

    refresh();
  }

  /* --- Hero particles --- */
  function initParticles() {
    if (reduceMotion) return;
    document.querySelectorAll('.mc-particles').forEach(function (host) {
      var n = 14, html = '';
      for (var i = 0; i < n; i++) {
        var left = Math.random() * 100, dur = 9 + Math.random() * 10, delay = Math.random() * 8, s = 2 + Math.random() * 2;
        html += '<span style="left:' + left + '%;bottom:-10px;width:' + s + 'px;height:' + s +
                'px;animation-duration:' + dur + 's;animation-delay:' + delay + 's"></span>';
      }
      host.innerHTML = html;
    });
  }

  function init() { initReveals(); initHeader(); initMenu(); initCart(); initParticles(); }
  if (document.readyState !== 'loading') init();
  else document.addEventListener('DOMContentLoaded', init);
})();
