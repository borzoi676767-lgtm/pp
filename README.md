# Sasquatch Coffee — “The Hidden Forest”

An immersive, story-driven **Shopify Online Store 2.0** theme for
[sasquatchcoffee.store](https://sasquatchcoffee.store). Customers wander a
hidden old-growth forest, follow the trail to a cabin coffee shop, meet the
cryptid crew, and shop premium small-batch roasts — all while every standard
Shopify commerce feature keeps working.

> **Nature Calls, Coffee Answers.**

## What's inside

### The living world (home page — ONE interactive block)
The entire landing page is a single full-viewport scene (`forest-world`
section): no scrolling required to use the store on desktop.
- **3D coffee shop cabin** (Draco-compressed GLB, `<model-viewer>`) —
  drag to look around, **click to step inside**. The interior is a
  full-screen overlay with two areas:
  - **The Shelves** — products on wooden shelves, one shelf per
    collection, labeled by collection with quick-add and “view trail”.
  - **Crew Stations** — a themed corner for each crew member
    (Roastery / Flavor Lab / Storeroom / Night Counter / Trail Desk),
    each with a **spinnable 3D model** and clickable dialogue.
- **All five crew members are real 3D models** (Sasquatch, Simon, Yeti,
  Mothman, Jackalope) with 2D-art automatic fallback.
- **Ollie the Camp Mascot** — the 3D spinnable platypus (auto-rotate +
  drag), distinct from Simon the coffee scientist.
- **Campfire → Our Story** modal, clickable crew with speech bubbles,
  quick-nav chips (Shelves / Crew / Story / Search), drifting leaves,
  fireflies at night, god-rays.
- Legacy scroll sections (hero, trailheads, crew, campfire, FAQ …) are
  still in the theme and can be re-added via the Theme Editor.

### World controls (fixed, accessible)
Day/Night toggle · Forest ambient sound (synthesised, no audio file) ·
Rain · Snow. All honour `prefers-reduced-motion` and pause when the tab is
hidden.

### Easter eggs & gamification
Hidden coffee beans to collect, a camp-badge tracker, and unlockable discount
hints (`TRAILBLAZER`, `FORESTFIND`) — all stored client-side.

### Commerce (fully preserved & upgraded)
- AJAX cart **drawer** via the Section Rendering API (open state survives
  quantity edits), free-shipping progress bar, cart upsells.
- Product page: variant picker, quantity stepper, subscriptions
  (selling plans), sticky add-to-cart, low-inventory + delivery notices,
  gallery with thumbnails, trust row, accordion, related products,
  recently-viewed (client-side), dynamic checkout button.
- Collection page: native Shopify **filters**, sorting, pagination, quick-add.
- Predictive search, wishlist, quick-add, search, blog/article, pages,
  full customer account templates, password page, 404.

### Performance & accessibility
- All artwork is optimised **WebP**; all seven 3D models are
  **Draco-compressed GLB** (~350–660 KB each, down from 8–11 MB raw) and
  lazy-loaded via `<model-viewer>` with 2D poster/fallback art.
- Dependency-free UI JS — canvas particle systems are capped,
  `IntersectionObserver`-gated, and paused when off-screen.
- Reduced-motion fully supported, keyboard navigable, skip link, ARIA labels,
  focus-visible styles, semantic landmarks.

### SEO
JSON-LD for Organization, Product (with AggregateOffer + ratings), WebSite
(Sitelinks search box) and FAQ; Open Graph + Twitter cards; canonical URLs;
descriptive alt text.

## Structure
```
layout/       theme.liquid, password.liquid
templates/    index, product, collection, cart, search, list-collections,
              page, blog, article, 404, password + customers/*
sections/     forest-hero, the-coffee-shop, meet-the-crew, campfire-story,
              collection-trailheads, featured-collection, main-*, header,
              footer, announcement-bar, trust-badges, faq, testimonials, …
snippets/     product-card, cart-contents, cart-drawer, meta-tags, price,
              icon, pagination, free-shipping-bar, hidden-bean
assets/       base.css, forest.css, components.css, global.js, forest.js,
              + optimised WebP artwork (hero, shop, campfire, characters…)
config/       settings_schema.json, settings_data.json
locales/      en.default.json
```

## Editability
Everything is driven by section/block **schema settings**, theme settings,
`link_list`s, `collection`/`image_picker` pickers, and product **metafields**
(`custom.tasting_notes`, `custom.brew_guide`, `custom.simon_note`,
`reviews.rating`). No hard-coded content — fully editable in the Theme Editor.

## Installing
1. Zip the theme (or connect this repo via the Shopify GitHub integration).
2. Upload/pull into the store and **Publish** (or preview first).
3. In the Theme Editor, assign the featured collections in *Coffee Shop*,
   *Collection trailheads*, and *Featured collection*, and set the header/footer
   menus.

## Art direction
National-park travel poster × Studio Ghibli warmth. Palette: forest green,
moss, cedar, bark, warm cream, campfire orange, golden light, morning fog,
pine-needle green. Artwork generated with Higgsfield and hand-optimised.
