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
│                    final-sanctuary), rich-text, contact-form, main-product (with
│                    provenance/care/heraldry/share blocks), main-collection (facets
│                    + sort), main-list-collections, main-page, main-search, main-blog,
│                    main-article, main-cart, and the customer-account sections
├── snippets/       icon, price, product-card, placeholder, meta-tags (JSON-LD),
│                   cart-drawer, search-panel (predictive search)
└── templates/      index, product, collection, list-collections, page, page.contact,
                    cart, search, blog, article, 404, gift_card.liquid, customers/*
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

## Added in Phase 2

- **Library of Faith** blog + article templates and sections (editorial styling, share links).
- **Customer accounts**: login (with password recovery), register, account + order history,
  order detail, addresses (add/edit/delete with country–province selectors), reset &
  activate password.
- **Predictive search** overlay in the header (live suggestions via `/search/suggest.json`).
- **Faceted filters + sort** on collection pages (`collection.filters`, auto-submit,
  active-filter chips).
- **Richer product page**: reorderable blocks for provenance/materials, care, heraldry
  seal, custom accordions, and share — reading `custom.materials` / `custom.care` metafields.
- **Gift card** page and a **contact** page template (`page.contact`).

## Added in Phase 3

- **Storefront password page** — `layout/password.liquid` + `main-password` section +
  `password.json` (message, email capture, password entry, Shopify attribution).
- **Ambient audio opt-in** — a floating toggle that is **off by default** and remembered
  per visitor; playback only ever starts on a click. Merchant supplies an MP3 URL under
  Theme settings → Ambient audio.
- **3D relic viewer** — the product gallery now renders images, video, and **3D models**
  as slides; Shopify's `model-viewer` feature loads only when a product has a model.

## Roadmap beyond Phase 3

The theme is now feature-complete for a premium storefront. Optional future polish:
Figma-exported token sync, product bundles, and liturgical-calendar merchandising.
See `../milites-christi/BRAND-PROMPT.md` (§10).

> Earthly empires rise and fall, but the Kingdom of Christ endures forever.
