/* ==========================================================================
   MILITES CHRISTI — mc-cinematic.js
   Premium motion engine. Progressive enhancement over the functional mc.js.
   - Lenis smooth scroll + GSAP ScrollTrigger (reveals, parallax, pin, progress)
   - Glass navbar hide/show/shrink
   - Bronze magnetic custom cursor
   - Count-up statistics, 3D tilt, virtue illumination, hero mouse-depth
   Graceful fallbacks: IntersectionObserver if GSAP is missing; everything is
   revealed instantly under prefers-reduced-motion.
   ========================================================================== */
(function () {
  'use strict';
  var root = document.documentElement;
  root.classList.remove('no-js'); root.classList.add('js', 'lx-reveal-ready');

  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var fine = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  var hasGSAP = typeof window.gsap !== 'undefined';
  var hasST = hasGSAP && typeof window.ScrollTrigger !== 'undefined';
  var hasLenis = typeof window.Lenis !== 'undefined';

  function showAll() {
    document.querySelectorAll('.lx-fade,.lx-scale,.lx-blur').forEach(function (e) { e.classList.add('lx-in'); });
    document.querySelectorAll('.lx-words').forEach(function (e) { e.classList.add('is-in'); });
    document.querySelectorAll('.lx-virtue').forEach(function (e) { e.classList.add('is-lit'); });
    document.querySelectorAll('[data-lx-count]').forEach(function (e) { e.textContent = e.getAttribute('data-lx-count') + (e.getAttribute('data-suffix') || ''); });
  }

  /* Split headline text into word masks for reveal */
  function splitWords() {
    document.querySelectorAll('[data-lx-words]').forEach(function (el) {
      if (el.dataset.lxSplit) return; el.dataset.lxSplit = '1';
      var words = el.textContent.trim().split(/\s+/);
      el.textContent = '';
      el.classList.add('lx-words');
      words.forEach(function (w, i) {
        var word = document.createElement('span'); word.className = 'lx-word';
        var inner = document.createElement('span'); inner.textContent = w;
        word.appendChild(inner); el.appendChild(word);
        if (i < words.length - 1) el.appendChild(document.createTextNode(' '));
      });
    });
  }

  /* Count-up */
  function countUp(el) {
    var target = parseFloat(el.getAttribute('data-lx-count')) || 0;
    var suffix = el.getAttribute('data-suffix') || '';
    var dec = (String(target).split('.')[1] || '').length;
    var start = null, dur = 1800;
    function step(ts) {
      if (!start) start = ts;
      var p = Math.min((ts - start) / dur, 1);
      var eased = 1 - Math.pow(1 - p, 3);
      el.textContent = (target * eased).toFixed(dec) + suffix;
      if (p < 1) requestAnimationFrame(step); else el.textContent = target.toFixed(dec) + suffix;
    }
    requestAnimationFrame(step);
  }

  /* ---- Reduced motion: reveal instantly, skip the rest ---- */
  if (reduce) { splitWords(); showAll(); return; }

  splitWords();

  /* ---- Floating particles ---- */
  document.querySelectorAll('.lx-particles').forEach(function (host) {
    var n = 16, html = '';
    for (var i = 0; i < n; i++) {
      var l = Math.random() * 100, d = 8 + Math.random() * 12, delay = Math.random() * 10, s = 2 + Math.random() * 3;
      html += '<i style="left:' + l + '%;bottom:-12px;width:' + s + 'px;height:' + s + 'px;animation-duration:' + d + 's;animation-delay:' + delay + 's"></i>';
    }
    host.innerHTML = html;
  });

  /* ---- Custom cursor + magnetic CTAs ---- */
  if (fine) {
    root.classList.add('lx-cursor');
    var dot = document.createElement('div'); dot.className = 'lx-cursor-dot';
    var ring = document.createElement('div'); ring.className = 'lx-cursor-ring';
    document.body.appendChild(dot); document.body.appendChild(ring);
    var mx = innerWidth / 2, my = innerHeight / 2, rx = mx, ry = my;
    document.addEventListener('mousemove', function (e) { mx = e.clientX; my = e.clientY; dot.style.transform = 'translate(' + mx + 'px,' + my + 'px)'; }, { passive: true });
    (function loop() { rx += (mx - rx) * 0.18; ry += (my - ry) * 0.18; ring.style.transform = 'translate(' + rx + 'px,' + ry + 'px)'; requestAnimationFrame(loop); })();
    var interactive = 'a,button,[data-magnetic],input,select,textarea,summary,.lx-card,.lx-angel';
    document.addEventListener('mouseover', function (e) { if (e.target.closest(interactive)) ring.classList.add('is-active'); });
    document.addEventListener('mouseout', function (e) { if (e.target.closest(interactive)) ring.classList.remove('is-active'); });

    /* Magnetic buttons */
    document.querySelectorAll('.mc-btn, [data-magnetic]').forEach(function (btn) {
      btn.addEventListener('mousemove', function (e) {
        var r = btn.getBoundingClientRect();
        var x = (e.clientX - r.left - r.width / 2) * 0.3, y = (e.clientY - r.top - r.height / 2) * 0.4;
        btn.style.transform = 'translate(' + x + 'px,' + y + 'px)';
      });
      btn.addEventListener('mouseleave', function () { btn.style.transform = ''; });
    });
  }

  /* ---- 3D tilt cards / archangels ---- */
  document.querySelectorAll('[data-lx-tilt]').forEach(function (el) {
    var max = parseFloat(el.getAttribute('data-lx-tilt')) || 8;
    el.addEventListener('mousemove', function (e) {
      var r = el.getBoundingClientRect();
      var px = (e.clientX - r.left) / r.width, py = (e.clientY - r.top) / r.height;
      el.style.transform = 'perspective(1000px) rotateY(' + ((px - 0.5) * max) + 'deg) rotateX(' + ((0.5 - py) * max) + 'deg)';
      el.style.setProperty('--mx', (px * 100) + '%'); el.style.setProperty('--my', (py * 100) + '%');
    });
    el.addEventListener('mouseleave', function () { el.style.transform = ''; });
  });

  /* ---- Hero mouse-depth ---- */
  var depths = document.querySelectorAll('[data-lx-depth]');
  if (depths.length && fine) {
    document.addEventListener('mousemove', function (e) {
      var x = (e.clientX / innerWidth - 0.5), y = (e.clientY / innerHeight - 0.5);
      depths.forEach(function (l) {
        var d = parseFloat(l.getAttribute('data-lx-depth')) || 10;
        l.style.transform = 'translate3d(' + (-x * d) + 'px,' + (-y * d) + 'px,0) scale(1.06)';
      });
    }, { passive: true });
  }

  /* ---- Navbar hide/show/shrink ---- */
  (function () {
    var header = document.querySelector('[data-mc-header]'); if (!header) return;
    var last = 0;
    function onScroll(y) {
      header.classList.toggle('is-scrolled', y > 30);
      if (y > last && y > 240) header.classList.add('lx-hidden'); else header.classList.remove('lx-hidden');
      last = y;
    }
    window.__lxScroll = onScroll;
    window.addEventListener('scroll', function () { onScroll(window.scrollY); }, { passive: true });
  })();

  /* ---- Progress bar element ---- */
  var progress = document.querySelector('.lx-progress');

  /* ================= GSAP + Lenis path ================= */
  if (hasGSAP && hasST) {
    gsap.registerPlugin(ScrollTrigger);

    var lenis = null;
    if (hasLenis && fine) {
      lenis = new Lenis({ duration: 1.1, smoothWheel: true, wheelMultiplier: 1, touchMultiplier: 1.6 });
      lenis.on('scroll', function (e) { ScrollTrigger.update(); if (window.__lxScroll) window.__lxScroll(e.animatedScroll || window.scrollY); if (progress) progress.style.transform = 'scaleX(' + (e.progress || 0) + ')'; });
      gsap.ticker.add(function (t) { lenis.raf(t * 1000); });
      gsap.ticker.lagSmoothing(0);
    } else if (progress) {
      window.addEventListener('scroll', function () {
        var h = document.documentElement.scrollHeight - innerHeight;
        progress.style.transform = 'scaleX(' + (h > 0 ? window.scrollY / h : 0) + ')';
      }, { passive: true });
    }

    /* Reveals */
    gsap.utils.toArray('.lx-fade,.lx-scale,.lx-blur').forEach(function (el) {
      ScrollTrigger.create({ trigger: el, start: 'top 86%', once: true, onEnter: function () { el.classList.add('lx-in'); } });
    });
    /* Word headline reveals */
    gsap.utils.toArray('.lx-words').forEach(function (el) {
      ScrollTrigger.create({ trigger: el, start: 'top 88%', once: true, onEnter: function () { el.classList.add('is-in'); } });
    });
    /* Parallax */
    gsap.utils.toArray('[data-lx-parallax]').forEach(function (el) {
      var speed = parseFloat(el.getAttribute('data-lx-parallax')) || 0.2;
      gsap.to(el, { yPercent: -speed * 100, ease: 'none', scrollTrigger: { trigger: el.parentElement, start: 'top bottom', end: 'bottom top', scrub: true } });
    });
    /* Virtues illuminate */
    gsap.utils.toArray('.lx-virtue').forEach(function (el, i) {
      ScrollTrigger.create({ trigger: el, start: 'top 80%', once: true, onEnter: function () { setTimeout(function () { el.classList.add('is-lit'); }, i * 140); } });
    });
    /* Counters */
    gsap.utils.toArray('[data-lx-count]').forEach(function (el) {
      ScrollTrigger.create({ trigger: el, start: 'top 90%', once: true, onEnter: function () { countUp(el); } });
    });
    /* Optional pinned horizontal track */
    gsap.utils.toArray('[data-lx-horizontal]').forEach(function (track) {
      var inner = track.querySelector('[data-lx-horizontal-inner]'); if (!inner) return;
      var dist = inner.scrollWidth - track.clientWidth; if (dist <= 0) return;
      gsap.to(inner, { x: -dist, ease: 'none', scrollTrigger: { trigger: track, start: 'top top', end: '+=' + dist, scrub: 1, pin: true, anticipatePin: 1 } });
    });

    ScrollTrigger.refresh();
    window.addEventListener('load', function () { ScrollTrigger.refresh(); });
    return;
  }

  /* ================= Fallback: IntersectionObserver ================= */
  if (progress) {
    window.addEventListener('scroll', function () {
      var h = document.documentElement.scrollHeight - innerHeight;
      progress.style.transform = 'scaleX(' + (h > 0 ? window.scrollY / h : 0) + ')';
    }, { passive: true });
  }
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var t = en.target;
        if (t.classList.contains('lx-words')) t.classList.add('is-in');
        else if (t.classList.contains('lx-virtue')) t.classList.add('is-lit');
        else if (t.hasAttribute('data-lx-count')) countUp(t);
        else t.classList.add('lx-in');
        io.unobserve(t);
      });
    }, { rootMargin: '0px 0px -12% 0px' });
    document.querySelectorAll('.lx-fade,.lx-scale,.lx-blur,.lx-words,.lx-virtue,[data-lx-count]').forEach(function (e) { io.observe(e); });
  } else { showAll(); }
})();
