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

  /* --- Predictive search --- */
  function initSearch() {
    var panel = document.querySelector('[data-mc-search]');
    if (!panel) return;
    var input = panel.querySelector('[data-mc-search-input]');
    var results = panel.querySelector('[data-mc-search-results]');
    var lastFocus = null, timer = null;

    function open() {
      lastFocus = document.activeElement;
      panel.hidden = false;
      requestAnimationFrame(function () { input.focus(); });
      document.addEventListener('keydown', onKey);
    }
    function close() {
      panel.hidden = true;
      document.removeEventListener('keydown', onKey);
      if (lastFocus) lastFocus.focus();
    }
    function onKey(e) { if (e.key === 'Escape') close(); }

    document.querySelectorAll('[data-mc-search-open]').forEach(function (o) {
      o.addEventListener('click', function (e) { e.preventDefault(); open(); });
    });
    panel.querySelectorAll('[data-mc-search-close]').forEach(function (c) { c.addEventListener('click', close); });

    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

    function render(data) {
      var r = (data.resources && data.resources.results) || {};
      var html = '';
      if (r.products && r.products.length) {
        html += '<div class="mc-search__group">Products</div>';
        r.products.forEach(function (p) {
          var img = p.image ? '<img src="' + esc(p.image) + '" alt="" loading="lazy">' : '<span class="mc-search__ph"></span>';
          var price = p.price ? '<span class="mc-search__p">' + esc(p.price) + '</span>' : '';
          html += '<a href="' + esc(p.url) + '">' + img + '<span class="mc-search__t">' + esc(p.title) + '</span>' + price + '</a>';
        });
      }
      ['collections', 'articles', 'pages'].forEach(function (key) {
        if (r[key] && r[key].length) {
          html += '<div class="mc-search__group">' + key.charAt(0).toUpperCase() + key.slice(1) + '</div>';
          r[key].forEach(function (it) {
            html += '<a href="' + esc(it.url) + '"><span class="mc-search__ph"></span><span class="mc-search__t">' + esc(it.title) + '</span></a>';
          });
        }
      });
      results.innerHTML = html || '<p class="mc-lead" style="padding:16px 0">Nothing found yet.</p>';
    }

    input.addEventListener('input', function () {
      var q = input.value.trim();
      clearTimeout(timer);
      if (q.length < 2) { results.innerHTML = ''; return; }
      timer = setTimeout(function () {
        var url = '/search/suggest.json?q=' + encodeURIComponent(q) +
          '&resources[type]=product,collection,article,page&resources[limit]=6&resources[options][unavailable_products]=last';
        fetch(url, { headers: { 'Accept': 'application/json' } })
          .then(function (res) { return res.json(); })
          .then(render).catch(function () {});
      }, 220);
    });
  }

  /* --- Collection facets: auto-submit on change --- */
  function initFacets() {
    var form = document.querySelector('[data-mc-facets]');
    if (!form) return;
    var t = null;
    form.addEventListener('change', function () {
      clearTimeout(t);
      t = setTimeout(function () { form.submit(); }, 250);
    });
  }

  /* --- Product variant picker: sync hidden id, price, availability --- */
  function initProductForm() {
    document.querySelectorAll('[data-mc-add-form]').forEach(function (form) {
      var dataEl = form.querySelector('[data-mc-variants]');
      var optionSelects = form.querySelectorAll('select[name^="options"]');
      if (!dataEl || !optionSelects.length) return; // single-variant: nothing to sync
      var variants;
      try { variants = JSON.parse(dataEl.textContent); } catch (e) { return; }
      var idField = form.querySelector('select[name="id"]');
      var info = form.closest('.mc-product__info');
      var priceEl = info ? info.querySelector('[data-mc-price-current]') : null;
      var addBtn = form.querySelector('[data-mc-add-btn]');

      function update() {
        var chosen = Array.prototype.map.call(optionSelects, function (s) { return s.value; });
        var match = variants.find(function (v) {
          return v.options.length === chosen.length && v.options.every(function (o, i) { return o === chosen[i]; });
        });
        if (!match) return;
        if (idField) idField.value = match.id;
        if (priceEl && match.price) priceEl.textContent = match.price;
        if (addBtn) {
          addBtn.disabled = !match.available;
          addBtn.textContent = match.available
            ? (addBtn.getAttribute('data-add-label') || 'Add to cart')
            : (addBtn.getAttribute('data-sold-label') || 'Sold out');
        }
      }
      optionSelects.forEach(function (s) { s.addEventListener('change', update); });
      update();
    });
  }

  /* --- Ambient audio (opt-in, remembered) --- */
  function initAudio() {
    var host = document.querySelector('[data-mc-audio]');
    if (!host) return;
    var audio = host.querySelector('[data-mc-audio-el]');
    var btn = host.querySelector('[data-mc-audio-toggle]');
    if (!audio || !btn) return;
    var KEY = 'mc-audio', started = false;

    function setOn(on) { host.classList.toggle('is-on', on); btn.setAttribute('aria-pressed', String(on)); }
    function play() { audio.volume = 0.35; var p = audio.play(); if (p && p.catch) p.catch(function () {}); setOn(true); started = true; }
    function pause() { audio.pause(); setOn(false); }
    function save(v) { try { localStorage.setItem(KEY, v); } catch (e) {} }

    btn.addEventListener('click', function () {
      if (host.classList.contains('is-on')) { pause(); save('off'); }
      else { play(); save('on'); }
    });

    var remembered = null;
    try { remembered = localStorage.getItem(KEY); } catch (e) {}
    if (remembered === 'on') {
      var resume = function () { if (!started) play(); document.removeEventListener('pointerdown', resume); document.removeEventListener('keydown', resume); };
      document.addEventListener('pointerdown', resume, { once: true });
      document.addEventListener('keydown', resume, { once: true });
    }
  }

  /* --- Product media gallery: switch active slide --- */
  function initGallery() {
    document.querySelectorAll('[data-mc-gallery]').forEach(function (gallery) {
      var slides = gallery.querySelectorAll('.mc-media-slide');
      var thumbs = gallery.querySelectorAll('[data-mc-thumb]');
      if (thumbs.length < 2) return;
      thumbs.forEach(function (thumb) {
        thumb.addEventListener('click', function () {
          var idx = thumb.getAttribute('data-mc-thumb');
          slides.forEach(function (s) { s.hidden = s.getAttribute('data-index') !== idx; });
          thumbs.forEach(function (t) { t.setAttribute('aria-current', t === thumb ? 'true' : 'false'); });
          var active = gallery.querySelector('.mc-media-slide[data-index="' + idx + '"]');
          var vid = active && active.querySelector('video');
          if (vid && vid.paused && vid.hasAttribute('data-autoplay')) { vid.play().catch(function () {}); }
        });
      });
    });
  }

  function init() { initReveals(); initHeader(); initMenu(); initCart(); initParticles(); initSearch(); initFacets(); initProductForm(); initAudio(); initGallery(); }
  if (document.readyState !== 'loading') init();
  else document.addEventListener('DOMContentLoaded', init);
})();
