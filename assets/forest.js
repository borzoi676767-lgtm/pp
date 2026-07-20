/*============================================================================
  forest.js  ·  The living-world engine
  Dependency-free. Canvas particles, parallax, scroll reveals, characters,
  campfire story, day/night, ambient sound, weather, easter eggs.
  Honors prefers-reduced-motion and pauses when the tab is hidden.
============================================================================*/
(function () {
  "use strict";
  const RM = window.matchMedia("(prefers-reduced-motion: reduce)");
  let reduced = RM.matches;
  RM.addEventListener?.("change", (e) => (reduced = e.matches));
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const rand = (a, b) => a + Math.random() * (b - a);
  const store = {
    get: (k, d) => { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch { return d; } },
    set: (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
  };

  /* =========================================================== Particles */
  class ParticleField {
    constructor(canvas) {
      this.c = canvas;
      this.ctx = canvas.getContext("2d");
      this.type = canvas.dataset.particles || "leaves";
      this.density = Number(canvas.dataset.density || 26);
      this.parts = [];
      this.running = false;
      this.resize = this.resize.bind(this);
      this.tick = this.tick.bind(this);
      this.resize();
      window.addEventListener("resize", this.resize, { passive: true });
      this.io = new IntersectionObserver((ents) => {
        ents[0].isIntersecting ? this.start() : this.stop();
      }, { threshold: 0 });
      this.io.observe(canvas);
    }
    resize() {
      const r = this.c.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      this.w = r.width; this.h = r.height;
      this.c.width = r.width * dpr; this.c.height = r.height * dpr;
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (!this.parts.length) this.seed();
    }
    seed() {
      const n = reduced ? Math.round(this.density * 0.3) : this.density;
      this.parts = Array.from({ length: n }, () => this.make());
    }
    make() {
      const base = { x: rand(0, this.w), y: rand(0, this.h), vx: rand(-0.3, 0.3), vy: rand(0.2, 0.9), r: rand(2, 6), a: rand(0.3, 0.9), spin: rand(-0.02, 0.02), rot: rand(0, 6.28), life: rand(0, 1), phase: rand(0, 6.28) };
      if (this.type === "fireflies") { base.vy = rand(-0.25, 0.25); base.vx = rand(-0.25, 0.25); base.r = rand(1.4, 2.8); }
      if (this.type === "embers") { base.vy = rand(-1.4, -0.5); base.r = rand(1, 2.6); base.y = this.h + 10; }
      return base;
    }
    tick() {
      if (!this.running) return;
      const ctx = this.ctx;
      ctx.clearRect(0, 0, this.w, this.h);
      for (const p of this.parts) {
        p.phase += 0.02;
        if (this.type === "fireflies") {
          p.x += p.vx + Math.sin(p.phase) * 0.3;
          p.y += p.vy + Math.cos(p.phase * 0.7) * 0.3;
          const glow = (Math.sin(p.phase * 1.6) + 1) / 2;
          ctx.beginPath();
          ctx.fillStyle = `rgba(255,${210 + glow * 40},120,${0.25 + glow * 0.6})`;
          ctx.shadowColor = "rgba(255,220,120,0.9)"; ctx.shadowBlur = 8 + glow * 10;
          ctx.arc(p.x, p.y, p.r, 0, 6.283); ctx.fill();
        } else if (this.type === "embers") {
          p.x += p.vx + Math.sin(p.phase) * 0.4; p.y += p.vy; p.a -= 0.006;
          ctx.beginPath();
          ctx.fillStyle = `rgba(255,${140 + Math.random() * 60 | 0},60,${Math.max(0, p.a)})`;
          ctx.shadowColor = "rgba(255,120,40,.8)"; ctx.shadowBlur = 6;
          ctx.arc(p.x, p.y, p.r, 0, 6.283); ctx.fill();
        } else { // leaves
          p.x += p.vx + Math.sin(p.phase) * 0.6; p.y += p.vy; p.rot += p.spin;
          ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.rot);
          ctx.fillStyle = `rgba(${[[122,90,45],[106,127,79],[224,122,60],[46,93,59]][p.life * 4 | 0].join(",")},${p.a})`;
          ctx.beginPath();
          ctx.ellipse(0, 0, p.r * 1.6, p.r * 0.8, 0, 0, 6.283); ctx.fill();
          ctx.restore();
        }
        ctx.shadowBlur = 0;
        if (p.y > this.h + 12 || p.x < -12 || p.x > this.w + 12 || p.a <= 0) {
          Object.assign(p, this.make(), { y: this.type === "embers" ? this.h + 8 : -8, x: rand(0, this.w) });
        }
      }
      this.raf = requestAnimationFrame(this.tick);
    }
    start() { if (this.running || document.hidden) return; this.running = true; this.raf = requestAnimationFrame(this.tick); }
    stop() { this.running = false; cancelAnimationFrame(this.raf); }
  }
  const fields = $$("canvas[data-particles]").map((c) => new ParticleField(c));
  document.addEventListener("visibilitychange", () => fields.forEach((f) => (document.hidden ? f.stop() : f.io && f.start())));

  /* ============================================================ Parallax */
  function initParallax() {
    const layers = $$("[data-parallax]");
    if (!layers.length) return;
    // Scroll parallax
    let ticking = false;
    const onScroll = () => {
      if (ticking || reduced) return;
      ticking = true;
      requestAnimationFrame(() => {
        const y = window.scrollY;
        layers.forEach((l) => {
          const speed = Number(l.dataset.parallax || 0.2);
          l.style.transform = `translate3d(0, ${y * speed}px, 0)`;
        });
        ticking = false;
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    // Mouse parallax on hero
    const hero = $("[data-parallax-scene]");
    if (hero && !reduced) {
      hero.addEventListener("pointermove", (e) => {
        const r = hero.getBoundingClientRect();
        const dx = (e.clientX - r.left) / r.width - 0.5;
        const dy = (e.clientY - r.top) / r.height - 0.5;
        $$("[data-mouse-depth]", hero).forEach((el) => {
          const d = Number(el.dataset.mouseDepth || 10);
          el.style.transform = `translate3d(${dx * d}px, ${dy * d}px, 0)`;
        });
      });
    }
  }

  /* ======================================================= Scroll reveals */
  function initReveals() {
    const items = $$("[data-reveal], [data-reveal-stagger]");
    if (!items.length) return;
    if (reduced) { items.forEach((i) => i.classList.add("in")); return; }
    const io = new IntersectionObserver((ents) => {
      ents.forEach((e) => {
        if (e.isIntersecting) {
          const el = e.target;
          if (el.hasAttribute("data-reveal-stagger")) {
            $$(":scope > *", el).forEach((c, i) => (c.style.transitionDelay = `${i * 80}ms`));
          }
          el.classList.add("in");
          io.unobserve(el);
        }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -8% 0px" });
    items.forEach((i) => io.observe(i));
  }

  /* ========================================================== Characters */
  function initCharacters() {
    $$("[data-character]").forEach((el) => {
      let lines = [];
      try { lines = JSON.parse(el.dataset.lines || "[]"); } catch {}
      // Bubble may live inside the trigger or as a sibling (e.g. Simon float,
      // where the round button clips overflow).
      const bubble = el.querySelector(".speech") || el.parentElement?.querySelector(".speech");
      let i = 0;
      const say = () => {
        if (!bubble || !lines.length) return;
        bubble.textContent = lines[i % lines.length];
        i++;
        el.classList.add("is-talking");
        bubble.classList.add("speech--on");
        clearTimeout(el._t);
        el._t = setTimeout(() => { el.classList.remove("is-talking"); bubble.classList.remove("speech--on"); }, 3200);
        window.theme?.Badges?.earn("storyteller");
      };
      el.addEventListener("click", say);
      el.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); say(); } });
    });
  }

  /* ============================================================ Campfire */
  function initCampfire() {
    const fire = $("[data-campfire]");
    const modal = $("#story-modal");
    if (!modal) return;
    const open = () => { modal.showModal?.() || modal.setAttribute("open", ""); window.theme?.Badges?.earn("storyteller"); };
    fire && fire.addEventListener("click", open);
    $$("[data-story-open]").forEach((b) => b.addEventListener("click", open));
    $$("[data-story-close]", modal).forEach((b) => b.addEventListener("click", () => modal.close?.()));
    modal.addEventListener("click", (e) => { if (e.target === modal) modal.close?.(); });
  }

  /* ====================================================== Enter the shop */
  function initEnterShop() {
    $$("[data-enter-shop]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const target = $(btn.getAttribute("data-enter-shop") || "#shop-interior");
        if (!target) return;
        document.body.classList.add("entering-shop");
        setTimeout(() => {
          target.hidden = false;
          target.classList.add("revealed");
          target.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
          document.body.classList.remove("entering-shop");
          window.theme?.Badges?.earn("first-brew");
        }, reduced ? 0 : 420);
      });
    });
  }

  /* ======================================================= Day / Night */
  const World = {
    initTime() {
      const saved = store.get("sq_time", null);
      const hour = new Date().getHours();
      const auto = hour >= 19 || hour < 6 ? "night" : "day";
      this.setTime(saved || auto, false);
      $$("[data-toggle-time]").forEach((b) => b.addEventListener("click", () => {
        const now = document.documentElement.getAttribute("data-time");
        this.setTime(now === "night" ? "day" : "night", true);
      }));
    },
    setTime(mode, persist) {
      document.documentElement.setAttribute("data-time", mode);
      $$("[data-toggle-time]").forEach((b) => { b.classList.toggle("is-active", mode === "night"); b.setAttribute("aria-pressed", String(mode === "night")); });
      if (persist) store.set("sq_time", mode);
      if (mode === "night") window.theme?.Badges?.earn("night-owl");
      fields.forEach((f) => f.io && (document.hidden || f.start()));
    },
  };

  /* ========================================================= Weather */
  function initWeather() {
    let layer;
    const setWeather = (kind) => {
      store.set("sq_weather", kind);
      layer && layer.remove();
      $$("[data-weather]").forEach((b) => b.classList.toggle("is-active", b.dataset.weather === kind));
      if (kind === "clear" || !kind) { layer = null; return; }
      layer = document.createElement("div");
      layer.className = "weather-layer";
      const n = reduced ? 20 : 70;
      for (let i = 0; i < n; i++) {
        const d = document.createElement("span");
        if (kind === "rain") {
          d.className = "rain-drop";
          d.style.left = rand(0, 100) + "vw";
          d.style.animationDuration = rand(0.5, 1.1) + "s";
          d.style.animationDelay = rand(0, 2) + "s";
          d.style.opacity = rand(0.2, 0.6);
        } else {
          d.className = "snow-flake";
          const s = rand(3, 7);
          d.style.width = d.style.height = s + "px";
          d.style.left = rand(0, 100) + "vw";
          d.style.setProperty("--sx", rand(-60, 60) + "px");
          d.style.animationDuration = rand(6, 13) + "s";
          d.style.animationDelay = rand(0, 6) + "s";
          d.style.opacity = rand(0.4, 0.95);
        }
        layer.appendChild(d);
      }
      document.body.appendChild(layer);
    };
    $$("[data-weather]").forEach((b) => b.addEventListener("click", () => {
      const active = b.classList.contains("is-active");
      setWeather(active ? "clear" : b.dataset.weather);
    }));
    const saved = store.get("sq_weather", null);
    if (saved && saved !== "clear") setWeather(saved);
  }

  /* ===================================================== Ambient sound */
  const Ambient = {
    ctx: null, on: false, nodes: [],
    toggle() { this.on ? this.stop() : this.start(); },
    start() {
      try {
        this.ctx = this.ctx || new (window.AudioContext || window.webkitAudioContext)();
        const ctx = this.ctx;
        // Wind: filtered brown noise
        const buffer = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
        const data = buffer.getChannelData(0);
        let last = 0;
        for (let i = 0; i < data.length; i++) { const w = Math.random() * 2 - 1; data[i] = (last + 0.02 * w) / 1.02; last = data[i]; data[i] *= 3.5; }
        const noise = ctx.createBufferSource(); noise.buffer = buffer; noise.loop = true;
        const lp = ctx.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = 480;
        const gain = ctx.createGain(); gain.gain.value = 0.0; gain.gain.linearRampToValueAtTime(0.14, ctx.currentTime + 1.5);
        noise.connect(lp).connect(gain).connect(ctx.destination);
        noise.start();
        // Gentle LFO on filter for wind swell
        const lfo = ctx.createOscillator(); lfo.frequency.value = 0.08;
        const lfoGain = ctx.createGain(); lfoGain.gain.value = 180;
        lfo.connect(lfoGain).connect(lp.frequency); lfo.start();
        this.nodes = [noise, lfo, gain];
        this.gain = gain;
        this.on = true;
        $$("[data-toggle-sound]").forEach((b) => { b.classList.add("is-active"); b.setAttribute("aria-pressed", "true"); });
      } catch (e) { /* audio unsupported */ }
    },
    stop() {
      try {
        if (this.gain) this.gain.gain.linearRampToValueAtTime(0, this.ctx.currentTime + 0.4);
        setTimeout(() => this.nodes.forEach((n) => n.stop && n.stop()), 500);
      } catch {}
      this.on = false;
      $$("[data-toggle-sound]").forEach((b) => { b.classList.remove("is-active"); b.setAttribute("aria-pressed", "false"); });
    },
  };
  function initSound() { $$("[data-toggle-sound]").forEach((b) => b.addEventListener("click", () => Ambient.toggle())); }

  /* =================================================== Easter-egg beans */
  // The full set of beans hidden across the whole site. Each appears on a
  // different page, so completion is tracked globally (localStorage) rather
  // than per-page. Add an id here when you add a {% render 'hidden-bean' %}.
  const ALL_BEANS = ["world", "reasons", "trail", "faq", "footer", "product", "collection", "cart"];
  const beansFoundCount = () => {
    const f = store.get("sq_beans", []);
    return ALL_BEANS.filter((id) => f.includes(id)).length;
  };
  const beansComplete = () => beansFoundCount() >= ALL_BEANS.length;

  function revealBeanReward() {
    if (!(beansComplete() || store.get("sq_beanhunt_done", false))) return;
    document.querySelectorAll("[data-beanhunt-reward]").forEach((el) => { el.hidden = false; });
  }

  function completeBeanHunt() {
    const first = !store.get("sq_beanhunt_done", false);
    store.set("sq_beanhunt_done", true);
    window.theme?.Badges?.earn("bean-hunter");
    if (first) {
      setTimeout(() => window.theme?.toast?.("🎁 Every hidden bean found! Your code FORESTFIND is waiting on your account page."), 1000);
    }
    revealBeanReward();
  }

  function initBeanHunt() {
    const spots = $$("[data-hidden-bean]");
    const found = store.get("sq_beans", []);
    spots.forEach((bean) => {
      const id = bean.dataset.hiddenBean;
      if (found.includes(id)) { bean.remove(); return; }
      // Reveal softly as it scrolls into view
      const io = new IntersectionObserver((e) => { if (e[0].isIntersecting) bean.classList.add("show"); });
      io.observe(bean);
      bean.addEventListener("click", () => {
        const list = store.get("sq_beans", []);
        if (!list.includes(id)) list.push(id);
        store.set("sq_beans", list);
        bean.classList.remove("show");
        bean.style.transition = ".4s"; bean.style.transform = "scale(0) rotate(90deg)"; bean.style.opacity = "0";
        setTimeout(() => bean.remove(), 400);
        window.theme?.toast?.(`☕ Coffee bean found! (${beansFoundCount()}/${ALL_BEANS.length})`);
        if (beansComplete()) completeBeanHunt();
      });
    });
  }

  /* ======================================================= Boot */
  function boot() {
    World.initTime();
    initParallax();
    initReveals();
    initCharacters();
    initCampfire();
    initEnterShop();
    initWeather();
    initSound();
    initBeanHunt();
    revealBeanReward();
    window.theme = window.theme || {};
    window.theme.World = World;
    window.theme.Ambient = Ambient;
  }
  if (document.readyState !== "loading") boot();
  else document.addEventListener("DOMContentLoaded", boot);
})();
