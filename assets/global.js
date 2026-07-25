/*============================================================================
  global.js  ·  Commerce + UI plumbing for Sasquatch Coffee
  Cart drawer, AJAX add-to-cart, variant selection, quick add,
  wishlist, recently viewed, sticky ATC, free-shipping bar.
============================================================================*/
(function () {
  "use strict";

  const money = (cents) =>
    (window.Shopify && Shopify.formatMoney)
      ? Shopify.formatMoney(cents, window.theme?.moneyFormat || "${{amount}}")
      : "$" + (cents / 100).toFixed(2);

  const on = (el, ev, sel, fn) => {
    el.addEventListener(ev, (e) => {
      const t = e.target.closest(sel);
      if (t && el.contains(t)) fn(e, t);
    });
  };
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  /* ------------------------------------------------------------ Cart API */
  const Cart = {
    sections: ["cart-drawer", "cart-icon-bubble"],

    async add(items, extraSections = []) {
      const body = {
        items: Array.isArray(items) ? items : [items],
        sections: [...new Set([...this.sections, ...extraSections])].join(","),
        sections_url: window.location.pathname,
      };
      const res = await fetch("/cart/add.js", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.description || "Could not add to cart");
      }
      const data = await res.json();
      this.render(data.sections);
      document.dispatchEvent(new CustomEvent("cart:updated", { detail: data }));
      return data;
    },

    async change(payload) {
      const res = await fetch("/cart/change.js", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ ...payload, sections: this.sections.join(","), sections_url: window.location.pathname }),
      });
      const data = await res.json();
      this.render(data.sections);
      document.dispatchEvent(new CustomEvent("cart:updated", { detail: data }));
      return data;
    },

    async get() {
      const res = await fetch("/cart.js");
      return res.json();
    },

    render(sections) {
      if (!sections) return;
      for (const id of Object.keys(sections)) {
        const html = sections[id];
        if (html == null) continue;
        // Replace the inner content of every matching section container
        $$(`[data-cart-section="${id}"]`).forEach((node) => {
          const doc = new DOMParser().parseFromString(html, "text/html");
          const fresh = doc.querySelector(`[data-cart-section="${id}"]`) || doc.body;
          node.innerHTML = fresh.innerHTML;
        });
      }
    },

    open() {
      const d = $("#cart-drawer");
      if (!d) return;
      d.classList.add("is-open");
      d.setAttribute("aria-hidden", "false");
      document.documentElement.classList.add("no-scroll");
      const focusable = d.querySelector("button, a, input");
      focusable && focusable.focus();
    },
    close() {
      const d = $("#cart-drawer");
      if (!d) return;
      d.classList.remove("is-open");
      d.setAttribute("aria-hidden", "true");
      document.documentElement.classList.remove("no-scroll");
    },
  };
  window.theme = window.theme || {};
  window.theme.Cart = Cart;

  /* ---------------------------------------------------- Toast / feedback */
  function toast(msg, type = "info") {
    let host = $("#toast-host");
    if (!host) {
      host = document.createElement("div");
      host.id = "toast-host";
      host.style.cssText = "position:fixed;left:50%;top:16px;transform:translateX(-50%);z-index:120;display:flex;flex-direction:column;gap:.5rem;align-items:center;pointer-events:none;";
      document.body.appendChild(host);
    }
    const el = document.createElement("div");
    el.setAttribute("role", "status");
    el.style.cssText =
      "pointer-events:auto;background:var(--forest-800,#16301f);color:var(--cream-100,#faf3e4);padding:.7rem 1.1rem;border-radius:999px;box-shadow:var(--shadow-lg);font-weight:600;opacity:0;transform:translateY(-8px);transition:.3s;max-width:90vw;";
    if (type === "error") el.style.background = "#8a3b2b";
    el.textContent = msg;
    host.appendChild(el);
    requestAnimationFrame(() => { el.style.opacity = "1"; el.style.transform = "none"; });
    setTimeout(() => { el.style.opacity = "0"; el.style.transform = "translateY(-8px)"; setTimeout(() => el.remove(), 350); }, 2600);
  }
  window.theme.toast = toast;

  /* ------------------------------------------------------ Add-to-cart forms */
  on(document, "submit", "form[data-product-form]", async (e, form) => {
    e.preventDefault();
    const btn = form.querySelector('[type="submit"]');
    const idInput = form.querySelector('[name="id"]');
    if (!idInput || !idInput.value) return;
    btn && btn.setAttribute("aria-busy", "true");
    try {
      const fd = new FormData(form);
      const item = { id: Number(fd.get("id")), quantity: Number(fd.get("quantity") || 1) };
      // selling plan (subscriptions)
      const plan = fd.get("selling_plan");
      if (plan) item.selling_plan = Number(plan);
      // line item properties
      fd.forEach((v, k) => {
        const m = k.match(/^properties\[(.+)\]$/);
        if (m && v) { item.properties = item.properties || {}; item.properties[m[1]] = v; }
      });
      await Cart.add(item);
      Cart.open();
      RecentlyViewed.trackAdded(item.id);
      Badges.earn("first-brew");
    } catch (err) {
      toast(err.message, "error");
    } finally {
      btn && btn.removeAttribute("aria-busy");
    }
  });

  /* --------------------------------------------------------- Quick add */
  on(document, "click", "[data-quick-add]", async (e, btn) => {
    e.preventDefault();
    const vid = btn.getAttribute("data-quick-add");
    if (!vid) return;
    btn.setAttribute("aria-busy", "true");
    try {
      await Cart.add({ id: Number(vid), quantity: 1 });
      Cart.open();
      Badges.earn("first-brew");
    } catch (err) { toast(err.message, "error"); }
    finally { btn.removeAttribute("aria-busy"); }
  });

  /* --------------------------------------------------- Cart drawer events */
  on(document, "click", "[data-cart-open]", (e) => { e.preventDefault(); Cart.open(); });
  on(document, "click", "[data-cart-close], .cart-drawer__overlay", (e) => { e.preventDefault(); Cart.close(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") Cart.close(); });

  on(document, "click", "[data-line-change]", async (e, btn) => {
    e.preventDefault();
    const line = Number(btn.getAttribute("data-line"));
    const qty = Number(btn.getAttribute("data-line-change"));
    btn.closest(".cart-line")?.classList.add("is-loading");
    try { await Cart.change({ line, quantity: qty }); } catch (err) { toast(err.message, "error"); }
  });
  on(document, "change", "[data-line-qty]", async (e, input) => {
    const line = Number(input.getAttribute("data-line"));
    const qty = Math.max(0, Number(input.value));
    try { await Cart.change({ line, quantity: qty }); } catch (err) { toast(err.message, "error"); }
  });

  /* -------------------------------------------------- Variant selection */
  class VariantPicker {
    constructor(root) {
      this.root = root;
      this.data = JSON.parse(root.querySelector("[data-variant-json]").textContent);
      this.form = root.closest("[data-product-root]").querySelector("form[data-product-form]");
      this.idInput = this.form.querySelector('[name="id"]');
      root.addEventListener("change", () => this.update());
      this.update(true);
    }
    selectedOptions() {
      return $$("[data-option-index]", this.root).map((el) => {
        if (el.type === "radio" || el.type === "checkbox") return null;
        return el.value;
      });
    }
    optionGroups() {
      return $$(".variant-option-group", this.root).filter((g) => !g.classList.contains("selling-plans"));
    }
    currentOptions() {
      const opts = [];
      this.optionGroups().forEach((group) => {
        const checked = group.querySelector('input[type="radio"]:checked');
        if (checked) opts.push(checked.value);
        const sel = group.querySelector("select");
        if (sel) opts.push(sel.value);
      });
      return opts;
    }
    findVariant(opts) {
      return this.data.find((v) => v.options.every((o, i) => o === opts[i]));
    }
    update(initial) {
      // Single-variant / default products have no option groups: keep server state.
      if (this.optionGroups().length === 0) return;
      const opts = this.currentOptions();
      const variant = this.findVariant(opts) || null;
      const root = this.root.closest("[data-product-root]");
      const btn = this.form.querySelector('[type="submit"] .btn__text') || this.form.querySelector('[type="submit"]');
      const submit = this.form.querySelector('[type="submit"]');
      if (!variant) {
        submit.setAttribute("disabled", "disabled");
        if (btn) btn.textContent = window.theme.strings?.unavailable || "Unavailable";
        return;
      }
      this.idInput.value = variant.id;
      if (!initial && window.history.replaceState) {
        const url = new URL(window.location);
        url.searchParams.set("variant", variant.id);
        window.history.replaceState({}, "", url);
      }
      // price
      const priceEl = root.querySelector("[data-price-target]");
      if (priceEl) {
        priceEl.innerHTML = variant.compare_at_price > variant.price
          ? `<span class="price__was">${money(variant.compare_at_price)}</span><span class="price__now">${money(variant.price)}</span>`
          : `<span>${money(variant.price)}</span>`;
      }
      // availability
      if (variant.available) {
        submit.removeAttribute("disabled");
        if (btn) btn.textContent = window.theme.strings?.addToCart || "Add to Basket";
      } else {
        submit.setAttribute("disabled", "disabled");
        if (btn) btn.textContent = window.theme.strings?.soldOut || "Sold Out";
      }
      // media switch
      if (variant.featured_media && root.querySelector("[data-product-gallery]")) {
        const media = root.querySelector(`[data-media-id="${variant.featured_media.id}"]`);
        media && media.scrollIntoView({ behavior: "smooth", inline: "start", block: "nearest" });
      }
      root.querySelector("[data-inventory]") && this.updateInventory(variant, root);
      document.dispatchEvent(new CustomEvent("variant:change", { detail: { variant } }));
    }
    updateInventory(variant, root) {
      const el = root.querySelector("[data-inventory]");
      if (!el) return;
      const qty = variant.inventory_quantity;
      const mgmt = variant.inventory_management;
      if (mgmt && qty !== null && qty <= 10 && qty > 0) {
        el.textContent = `Only ${qty} left by the fire — order soon`;
        el.hidden = false;
      } else { el.hidden = true; }
    }
  }
  $$("[data-variant-picker]").forEach((el) => new VariantPicker(el));
  window.theme.VariantPicker = VariantPicker;

  /* ------------------------------------------------------- Quantity steppers */
  on(document, "click", "[data-qty-step]", (e, btn) => {
    const wrap = btn.closest("[data-qty]");
    const input = wrap.querySelector("input");
    const step = Number(btn.getAttribute("data-qty-step"));
    input.value = Math.max(1, Number(input.value || 1) + step);
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });

  /* ------------------------------------------------------------ Wishlist */
  const Wishlist = {
    key: "sq_wishlist",
    get() { try { return JSON.parse(localStorage.getItem(this.key)) || []; } catch { return []; } },
    set(v) { localStorage.setItem(this.key, JSON.stringify(v)); this.paint(); document.dispatchEvent(new CustomEvent("wishlist:updated")); },
    toggle(handle) {
      const list = this.get();
      const i = list.indexOf(handle);
      if (i > -1) list.splice(i, 1); else { list.push(handle); Badges.earn("collector"); }
      this.set(list);
      return i === -1;
    },
    paint() {
      const list = this.get();
      $$("[data-wish]").forEach((b) => b.classList.toggle("is-active", list.includes(b.getAttribute("data-wish"))));
      $$("[data-wish-count]").forEach((c) => { c.textContent = list.length; c.hidden = list.length === 0; });
    },
  };
  on(document, "click", "[data-wish]", (e, btn) => {
    e.preventDefault();
    const added = Wishlist.toggle(btn.getAttribute("data-wish"));
    toast(added ? "Saved to your trail pack" : "Removed from trail pack");
  });
  window.theme.Wishlist = Wishlist;

  /* ------------------------------------------------- Recently viewed */
  const RecentlyViewed = {
    key: "sq_recent",
    get() { try { return JSON.parse(localStorage.getItem(this.key)) || []; } catch { return []; } },
    track(handle) {
      if (!handle) return;
      let list = this.get().filter((h) => h !== handle);
      list.unshift(handle);
      list = list.slice(0, 12);
      localStorage.setItem(this.key, JSON.stringify(list));
    },
    trackAdded() { /* hook for future */ },
    async render() {
      const host = $("[data-recently-viewed]");
      if (!host) return;
      const current = host.getAttribute("data-current-handle");
      const list = this.get().filter((h) => h !== current).slice(0, 8);
      if (!list.length) { host.closest("[data-recently-viewed-section]")?.remove(); return; }
      try {
        const cards = await Promise.all(list.map(async (h) => {
          const res = await fetch(`/products/${h}?section_id=recently-viewed-card`);
          if (!res.ok) return "";
          return res.text();
        }));
        const grid = host.querySelector("[data-rv-grid]") || host;
        grid.innerHTML = cards.join("");
        Wishlist.paint();
      } catch { host.closest("[data-recently-viewed-section]")?.remove(); }
    },
  };
  window.theme.RecentlyViewed = RecentlyViewed;

  /* --------------------------------------------- Sticky add-to-cart bar */
  function initStickyATC() {
    const bar = $("[data-sticky-atc]");
    const anchor = $("[data-atc-anchor]");
    if (!bar || !anchor) return;
    const io = new IntersectionObserver(
      ([entry]) => bar.classList.toggle("is-visible", !entry.isIntersecting && entry.boundingClientRect.top < 0),
      { threshold: 0 }
    );
    io.observe(anchor);
  }

  /* ---------------------------------------------------- Predictive search */
  function initSearch() {
    const input = $("[data-predictive-input]");
    const results = $("[data-predictive-results]");
    if (!input || !results) return;
    let ctl;
    let t;
    input.addEventListener("input", () => {
      clearTimeout(t);
      const q = input.value.trim();
      if (q.length < 2) { results.innerHTML = ""; results.hidden = true; return; }
      t = setTimeout(async () => {
        ctl && ctl.abort();
        ctl = new AbortController();
        try {
          const res = await fetch(`/search/suggest?q=${encodeURIComponent(q)}&resources[type]=product,collection&resources[limit]=6&section_id=predictive-search`, { signal: ctl.signal });
          results.innerHTML = await res.text();
          results.hidden = false;
        } catch (e) { /* aborted */ }
      }, 220);
    });
    document.addEventListener("click", (e) => { if (!results.contains(e.target) && e.target !== input) results.hidden = true; });
  }

  /* ------------------------------------------------------ Header behavior */
  function initHeader() {
    const header = $("[data-header]");
    if (!header) return;
    let last = 0;
    const onScroll = () => {
      const y = window.scrollY;
      header.classList.toggle("is-stuck", y > 20);
      header.classList.toggle("is-hidden", y > last && y > 400);
      last = y;
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    // Mobile nav — drawer lives as a sibling of the header, so toggle the
    // drawer element directly (a class on the header can't reach it).
    const mnav = $("[data-mobile-nav]");
    const setNav = (open) => {
      if (mnav) mnav.classList.toggle("is-open", open);
      header.classList.toggle("nav-open", open);
      document.body.classList.toggle("nav-open", open);
      document.documentElement.classList.toggle("no-scroll", open);
      const t = $("[data-nav-toggle]");
      if (t) t.setAttribute("aria-expanded", String(open));
    };
    on(document, "click", "[data-nav-toggle]", () => setNav(!(mnav && mnav.classList.contains("is-open"))));
    on(document, "click", "[data-mobile-nav-backdrop]", () => setNav(false));
    on(document, "click", "[data-mobile-nav] a", () => setNav(false));
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") setNav(false); });
    // Dropdowns keyboard
    $$("[data-has-mega]").forEach((li) => {
      const trigger = li.querySelector("a,button");
      trigger?.addEventListener("focus", () => li.classList.add("focus"));
      li.addEventListener("focusout", (e) => { if (!li.contains(e.relatedTarget)) li.classList.remove("focus"); });
    });
  }

  /* ---------------------------------------------------------- Badges */
  const Badges = {
    key: "sq_badges",
    all: ["first-brew", "collector", "storyteller", "night-owl", "bean-hunter"],
    get() { try { return JSON.parse(localStorage.getItem(this.key)) || []; } catch { return []; } },
    earn(id) {
      const list = this.get();
      if (list.includes(id)) return;
      list.push(id);
      localStorage.setItem(this.key, JSON.stringify(list));
      this.paint();
      const names = { "first-brew": "First Brew", collector: "Trail Collector", storyteller: "Story Seeker", "night-owl": "Night Owl", "bean-hunter": "Bean Hunter" };
      toast(`🏅 Badge earned: ${names[id] || id}`);
      if (list.length === this.all.length) {
        setTimeout(() => toast("🌲 Full Camp Badge set complete — use code TRAILBLAZER for 20% off!"), 1200);
      }
    },
    paint() {
      const earned = this.get();
      $$("[data-badge]").forEach((b) => b.classList.toggle("earned", earned.includes(b.getAttribute("data-badge"))));
    },
  };
  window.theme.Badges = Badges;

  /* ------------------------------------------------------------- Boot */
  document.addEventListener("DOMContentLoaded", () => {
    Wishlist.paint();
    Badges.paint();
    RecentlyViewed.render();
    initStickyATC();
    initSearch();
    initHeader();
    const ph = document.body.getAttribute("data-product-handle");
    if (ph) RecentlyViewed.track(ph);
  });
})();
