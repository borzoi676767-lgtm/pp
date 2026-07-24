# Milites Christi — Shopify Theme (Phase 1 foundation)

A premium **Shopify Online Store 2.0** theme for the Milites Christi brand. Late-Roman /
Early-Christian imperial aesthetic: black marble, aged bronze, burgundy, candlelight, and
the **Chi-Rho** as the central motif. Built to the spec in
[`../milites-christi/BRAND-PROMPT.md`](../milites-christi/BRAND-PROMPT.md).

No build step. Vanilla Liquid + CSS custom properties + one small progressive-enhancement
JS module. Accessible (WCAG AA intent), fast, mobile-first, merchant-editable.

## What's here (Phase 1)

```
theme/
├── assets/         base.css (tokens/reset/type/motion), components.css, mc.js, icon set
├── config/         settings_schema.json, settings_data.json  (colors, fonts, motion)
├── layout/         theme.liquid  (head/SEO, font wiring, skip link, header/footer, cart drawer)
├── locales/        en.default.json
├── sections/       header, footer, announcement-bar, the homepage scroll-journey
│                   (hero-basilica → hall-of-virtues → gallery-civilization →
│                    cathedral-marketplace → story-of-endurance → library-of-faith →
│                    final-sanctuary), rich-text, main-product, main-collection,
│                    main-list-collections, main-page, main-search, main-cart
├── snippets/       icon, price, product-card, placeholder, meta-tags (JSON-LD), cart-drawer
└── templates/      index, product, collection, list-collections, page, cart, search, 404
```

Design tokens live in `assets/base.css` (`:root`) and are overridable from the theme editor
(Colors, Typography, Motion). Every section ships with a `{% schema %}`, a preset, and
graceful empty states (stone/parchment placeholders — never a broken image).

## Install

1. Zip the **contents** of this `theme/` folder (so `layout/`, `sections/`, etc. are at the
   zip root), or use the Shopify CLI (`shopify theme push`).
2. Shopify admin → **Online Store → Themes → Add theme → Upload zip**.
3. **Customize** to set the hero image, feature a collection in the Cathedral Marketplace,
   point the Library at a blog, and set the menus (header + footer link lists).
4. Publish when ready. The homepage, collections (The Vestiary, Reliquary, Scriptorium,
   Household, Armory, Pilgrim's Kit), and pages (About, Our Story, Faith & History) already
   exist in the store.

## Not yet built (Phase 2+)

- `blog.json` / `article.json` + sections (Library of Faith editorial)
- Customer account templates (`customers/*`), `password.json`, `gift_card.liquid`
- Predictive-search dropdown, faceted collection filters, product provenance/heraldry blocks
- Optional 3D relic viewer and ambient-audio opt-in

See the roadmap in `../milites-christi/BRAND-PROMPT.md` (§10).

> Earthly empires rise and fall, but the Kingdom of Christ endures forever.
