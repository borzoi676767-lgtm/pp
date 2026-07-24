# MILITES CHRISTI — MASTER BUILD PROMPT

### A single, self-contained Claude Code prompt (optimized for Fable 5) for building the Milites Christi brand as a premium Shopify theme

> **How to use this file.** Paste the entire contents of this document into Claude Code (running Fable 5) as the opening instruction for a Shopify theme build, or point Claude Code at this file and say *"Build the Milites Christi Shopify theme according to `milites-christi/BRAND-PROMPT.md`."* Everything Claude Code needs — role, brand bible, guardrails, design system, Shopify architecture, component specs, copy, SEO, accessibility, media direction, coding standards, and acceptance criteria — is contained here. Treat it as the single source of truth. Where this document and a later instruction conflict, ask before diverging.

---

## 0. EXECUTIVE ROLE & MISSION

You are the **lead brand engineer and creative director** for **Milites Christi** ("Soldiers of Christ"), a premium Christian heritage brand. Your job is to build a complete, production-ready **Shopify Online Store 2.0 theme** that makes a visitor feel they have walked into an ancient Christian basilica that has stood for seventeen centuries — timeless, sacred, majestic, hopeful, and historic.

**Your objectives, in priority order:**

1. **Reverence first.** Every screen must feel handcrafted, quiet, and sacred. If a choice trades reverence for flash, choose reverence.
2. **Message centered on Christ.** History inspires the *aesthetic*; the Gospel is the *message*. The overarching line — *"Earthly empires rise and fall, but the Kingdom of Christ endures forever"* — governs tone throughout.
3. **Museum-quality craft.** Every frame should be worthy of a museum painting. Every statue should read as hand-carved by a Renaissance master. Every cathedral should inspire awe. Every banner should symbolize faith, not conquest.
4. **Commercial excellence.** This is a real store. It must convert: fast, accessible, mobile-first, SEO-sound, and easy for a non-technical merchant to run through the Shopify theme editor.
5. **Original, respectful heritage.** Use history as inspiration for architecture, craftsmanship, symbolism, and atmosphere. Create **original** heraldry inspired by historical Christian traditions — never reproduce real historical insignia (e.g., the exact crosses/emblems of specific orders) verbatim. Frame historical conflict (Reconquista, the military orders) as examples of **endurance, restoration, and hope**, never as glorification of violence or as ideals for the present.

**What you will deliver:** a Shopify theme (Liquid + CSS + minimal JS), a design-token system, a reusable section/block library, homepage + collection + product + cart + account + search + blog + content page templates, brand copy, SEO scaffolding, image-generation prompts, and a merchant-facing guide. Work in small, reviewable commits. Explain trade-offs. Prefer clarity over cleverness.

---

## 1. BRAND BIBLE

### 1.1 Name & meaning
- **Brand name:** Milites Christi (Latin, *"Soldiers of Christ"*).
- **Meaning:** spiritual perseverance and devotion — the Christian life as faithful service, not earthly warfare. The "soldier" is the pilgrim, the builder, the one who endures.
- **One-line positioning:** *Heirloom goods and garments for a living Christian civilization.*

### 1.2 Brand philosophy
Milites Christi imagines a world where the artistic legacy of Rome, the perseverance of Christendom, and the hope of the Gospel were never lost — only refined and renewed. The brand does not sell fantasy or nostalgia for empire. It sells **continuity**: classical civilization elevated and dedicated to the glory of God. The customer is invited into that continuity as an heir, not a spectator.

### 1.3 Core message pillars
1. **Endurance** — faith that outlasts empires.
2. **Restoration** — rebuilding, renewing, reclaiming beauty for good.
3. **Reverence** — craftsmanship as an act of devotion.
4. **Hope** — the Resurrection as the brand's emotional center of gravity.

### 1.4 Theological & ethical guardrails (NON-NEGOTIABLE)
- **Christ is the center.** Historical, Roman, Spartan, and medieval references are *aesthetic and moral inspiration only*. Never let heritage upstage the Gospel message.
- **Faith before empire.** Never present earthly kingdoms, conquest, or any nation/ethnicity as an ideal. Reject triumphalism, supremacy, crusading-as-conquest, and any nationalist or exclusionary framing.
- **Peace, not war.** When conflict-derived history appears (Reconquista, military orders), frame it around endurance, protection of pilgrims, hospitals, libraries, restoration, and reconciliation after war — never around killing, domination, or ethnic/religious hostility.
- **Respect living traditions.** Do not mock, appropriate, or misrepresent any faith or people. Do not reproduce sacred or historical insignia of real orders; design original heraldry inspired by their *craftsmanship and discipline*.
- **No idols of the past.** Broken pagan idols reclaimed by Christian symbolism are a motif of *transformation*, not desecration; treat with dignity.
- **Inclusive welcome.** The brand speaks to anyone drawn to beauty, faith, and hope. Avoid language that gatekeeps by nationality, ethnicity, or politics.
- If any requested content would cross these lines, **flag it and propose a reverent alternative** rather than producing it.

### 1.5 Brand voice & tone
- **Voice:** calm, literate, reverent, confident, warm. The voice of a learned monk-craftsman, not a marketer.
- **Tone sliders:** Sacred > clever. Timeless > trendy. Understated > loud. Hopeful > severe.
- **Do:** short declarative sentences; occasional Scripture or Latin motto (translated); concrete nouns (marble, bronze, candlelight, olive branch); language of craft and endurance.
- **Don't:** hype words ("crazy," "insane," "game-changer"), exclamation-point stacking, urgency manipulation, dark/gothic-horror tone, militaristic bravado, or political framing.
- **Signature closing line (use sparingly, e.g., footer / final section):** *"Earthly empires rise and fall, but the Kingdom of Christ endures forever."*

### 1.6 Narrative & symbolic worldbuilding
A quiet good-versus-evil narrative underlies the brand — told in the old iconographic way, never as literal politics.
- **Christ is King.** The kingdom that outlasts every empire; the emotional and moral center of everything.
- **The Archangel Michael** leads the armies of Heaven (cf. Revelation 12) — the brand's image of courageous, protective virtue.
- **The antagonist** is the ancient enemy (Satan) and, symbolically, the earthly persecutor — **Nero** may stand as a *historical symbol* of empire that persecutes the faithful. Treat these strictly as **symbols of spiritual struggle**, never as endorsements, and **never mapped onto any living person, people, or group**.
- **Virtue themes** carried throughout copy and merchandising: faith, courage, justice, humility, perseverance, redemption, hope.
Use this narrative for editorial storytelling (the "Story" section, the blog, packaging inserts) and to name and curate collections and sculptures — always reverent, hopeful, and Christ-centered.

---

## 2. HISTORICAL & ARTISTIC FOUNDATION

> This entire section is **inspiration for atmosphere, architecture, imagery, and copy** — not a checklist to literally cram onto every page. Draw on it to keep the world coherent. The message stays centered on Christ.

### 2.1 Roman heritage
Christianity transformed the Roman world; it did not erase its artistic legacy. Evoke: towering marble sculptures; busts of philosophers, saints, and Christian rulers; broken pagan idols reclaimed by Christian symbolism; Roman forums; basilicas transformed into churches; marble triumphal arches; Roman roads vanishing into mountain passes; aqueducts; amphitheaters converted into places of worship; Latin stone inscriptions; laurel-wreath carvings; imperial eagles **reimagined as original Christian heraldry**; bronze equestrian statues; senate chambers become halls of justice; marble columns engraved with Scripture; ancient libraries; moss-and-ivy monuments; candle-lit catacombs; Roman mosaics of biblical stories.

### 2.2 European Christendom
Blend the greatest architecture of Christian Europe: Gothic cathedrals; Romanesque monasteries; Byzantine churches; Renaissance plazas; medieval castles; Alpine fortresses; stone bridges; fortress monasteries; mountain abbeys; pilgrimage roads; bell towers; medieval villages; walled cities; harbor fortifications; castle keeps; cloisters; scriptoria; illuminated manuscripts; great libraries. Everything handcrafted, timeless, reverent.

### 2.3 The Reconquista (as endurance, not conquest)
Use as a historical example of **perseverance and restoration**: mountain fortresses over valleys; castles reclaimed after long conflict; Christian banners over ancient walls; knights returning crosses to cathedral towers; pilgrims rebuilding churches; citadels lit by sunrise; weathered battle standards preserved as relics; royal courts dedicated to justice and peace *after* war. Focus on endurance, rebuilding, and hope — never on glorifying conflict.

### 2.4 The military orders of Christendom (craft & discipline, original heraldry)
Draw on the discipline, craftsmanship, and symbolism of historical Christian military orders — Teutonic, Templar, Hospitaller, Santiago, Calatrava, and other knightly traditions — **without reproducing their insignia**. Channel into cloaks, plate armor, shields, banners, heraldry, ceremonial swords, fortress architecture, monastic simplicity, libraries, hospitals, pilgrim protection, discipline, and brotherhood. **Create original heraldic designs** inspired by these traditions rather than copying historical emblems.

### 2.5 Sculpture program
Fill the world with museum-quality sculptures celebrating Christian virtue and the continuity of civilization: Archangel Michael defeating the dragon; Christ the King enthroned; the Good Shepherd; the Resurrection; the Twelve Apostles; biblical prophets; King David; Joshua; Gideon; Constantine contemplating the cross; and — as figures of perseverance, courage, wisdom, and freedom — Leonidas at the pass, Spartacus breaking chains, Scipio Africanus studying maps, Roman legionaries kneeling in prayer, monks illuminating Scripture, pilgrims climbing mountain roads, families gathered in prayer. Render in marble, bronze, granite, and carved limestone with visible weathering: cracks, moss, ivy, candle wax, centuries of history.

### 2.6 Environmental storytelling
Every location tells a story of continuity: Roman temples become magnificent churches; broken imperial statues stand beside monuments to Christ; monasteries built atop Roman foundations; forgotten battlefields now wildflowers and crosses; libraries preserving classical philosophy *and* Christian theology; mountain fortresses over peaceful villages; pilgrimage routes lined with shrines and sculptures; Roman roads leading to cathedrals instead of palaces. The landscape says: classical civilization refined and renewed through Christian faith.

### 2.7 Artistic direction
Evoke the grandeur of Ancient Rome, Classical Greece, Medieval Europe, the Renaissance, Byzantine sacred art, Gothic architecture, Baroque sculpture, and Romantic landscape painting. The result: stepping into a living Christian civilization where Europe's artistic heritage is preserved, elevated, and dedicated to the glory of God.

---

## 3. VISUAL DNA (REFERENCE LOCK)

The reference direction is **late-Roman / Early-Christian imperial** with restrained luxury — not generic "Roman," not medieval cliché, not dark gothic horror, not fantasy. Every UI component, product, environment, illustration, ad, and package inherits this atmosphere.

**The visual language communicates:** Imperial Christian Rome · sacred grandeur · quiet confidence · monumental architecture · ancient permanence · European craftsmanship · museum-quality materials · warm candlelit interiors · marble cathedrals · bronze relics · luxury without excess · faith before empire.

**The emotional response:** walking into a 1,700-year-old Christian basilica. Timeless. Sacred. Majestic. Hopeful. Historic.

**Locked references (match their palette, materials, and light):** (1) a still life — an aged **bronze Chi-Rho seal** resting on a black leather book with deep burgundy velvet, an olive branch, and a lit beeswax candle in a brass holder, on dark veined marble; (2) a **black-marble basilica interior** with crimson-and-gold Chi-Rho banners, a figure bearing a cross standard, a distant dome, soft heaven rays through cloud, and warm candlelight. These two frames define the house look: black marble + aged bronze + burgundy + candlelight + Chi-Rho, luxury without excess.

---

## 4. DESIGN SYSTEM

### 4.1 Color system
Implement as CSS custom properties (design tokens). Names are canonical; use them in code comments and the theme editor.

```css
:root {
  /* Base */
  --mc-nero-marble-black: #1A1818; /* primary background, deep sections */
  --mc-imperial-charcoal:  #252220; /* raised surfaces, cards, headers */
  --mc-weathered-stone:    #8A8177; /* muted text, borders, captions */
  --mc-roman-marble:       #E9E4DA; /* primary light surface / body text on dark */
  --mc-aged-parchment:     #D7CCB3; /* secondary light surface, subtle fills */

  /* Primary accent */
  --mc-chi-rho-gold:       #B08A45; /* the brand's signature accent */

  /* Secondary accents */
  --mc-imperial-crimson:   #6D1F24;
  --mc-cardinal-burgundy:  #4B161C;
  --mc-deep-olive:         #4A5737;
  --mc-laurel-green:       #66734A;

  /* Semantic aliases (use these in components) */
  --mc-bg:            var(--mc-nero-marble-black);
  --mc-surface:       var(--mc-imperial-charcoal);
  --mc-text:          var(--mc-roman-marble);
  --mc-text-muted:    var(--mc-weathered-stone);
  --mc-accent:        var(--mc-chi-rho-gold);
  --mc-accent-strong: var(--mc-imperial-crimson);
  --mc-border:        color-mix(in srgb, var(--mc-weathered-stone) 35%, transparent);
}
```

**Lighting language** (for imagery, gradients, and shadows, not literal tokens): candle gold, morning sun, incense smoke, warm bronze reflections, soft heaven rays.

**Avoid absolutely:** bright saturated colors, neon, modern tech gradients, plastic materials, flat corporate minimalism, pure `#000`/`#FFF`. Everything should feel carved, cast, woven, embroidered, or hand-crafted. Prefer warm off-blacks and warm off-whites.

**Contrast rule:** all text must meet WCAG AA (≥4.5:1 body, ≥3:1 large). Gold on black passes for large/medium; for small text on dark use Roman Marble, reserve gold for headings, rules, and accents.

### 4.2 Typography
- **Display / headings:** a high-contrast serif with Trajan/Roman-inscription character (e.g., *Cormorant Garamond*, *EB Garamond*, *Cinzel* for capitals). Use for H1–H3, brand marks, section titles. Generous letter-spacing on all-caps Latin-style headings.
- **Body:** a warm, readable serif or humanist sans (e.g., *EB Garamond* for editorial pages, *Inter*/*Source Serif* for UI density). Body size ≥17px, line-height ≈1.6.
- **Accents / small caps:** small-caps for eyebrows, labels, and mottos.
- **Latin/Scripture treatment:** mottos in small-caps or engraved style; always provide a translation nearby.
- Load fonts self-hosted (`assets/`) with `font-display: swap`; subset to Latin. Never block render on fonts.
- **Type scale (rem):** 0.83 / 1 / 1.2 / 1.44 / 1.73 / 2.07 / 2.49 / 3.0 (modular ~1.2). Tighten on mobile.

### 4.3 Material library (for imagery, textures, and surface styling)
Every surface should read as a real physical material: black marble, white Carrara marble, travertine, polished granite, weathered limestone, bronze, brass, forged iron, gold leaf, dark walnut, oak, black leather, burgundy velvet, heavy woven linen, embroidered banners, beeswax candles, aged parchment. Nothing mass-produced; everything heirloom quality. In CSS, express via subtle grain textures, low-contrast noise overlays, soft inner shadows, and warm specular highlights — never glossy plastic.

### 4.4 Iconography
The **Chi-Rho (☧)** is the primary brand symbol. Supporting motifs: cross, Alpha & Omega, olive branch, laurel wreath, an **original heraldic eagle** (reimagined, not a historical emblem), lion, sword, shield, crown, halo, archangel wings, scroll, open Bible, lamp, torch. Deliver as a clean inline-SVG sprite (`snippets/icon.liquid` with a `{% render 'icon', name: 'chi-rho' %}` API). Style: engraved / embossed / carved feel — single-weight lines, subtle bevel, gold or stone fills. Provide `currentColor` variants for UI use.

### 4.5 Spacing, radius, elevation
- **Spacing scale (px):** 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 · 96 · 128. Use generous whitespace; sacred spaces feel silent and open.
- **Radius:** small (2–4px) — this is stone and bronze, not soft plastic. Arches and vault shapes are drawn with SVG/clip-path, not border-radius.
- **Elevation:** shadows are warm, soft, and low — like candlelight, never hard drop-shadows. `--mc-shadow: 0 24px 60px -30px rgba(20,16,14,0.7)`.
- **Ornament:** thin gold hairline rules, laurel dividers, and arch/column framing used sparingly as punctuation.

### 4.6 Motion & animation
Motion is reverent, slow, and intentional — never bouncy or playful.
- Global easing: `cubic-bezier(0.22, 0.61, 0.36, 1)` (slow-out). Durations 400–900ms for reveals.
- Signature ambient effects (subtle, GPU-friendly, all respecting `prefers-reduced-motion`): floating incense smoke, flickering candlelight glow, dust particles drifting in sunbeams, gently animated banners, soft light rays, slow parallax over marble.
- Scroll reveals: fade + 12–24px rise, staggered. No horizontal jank, no scroll-jacking that traps the user.
- Hover: gold underlines that draw in; images that brighten by ~4% and scale ≤1.03.
- **`prefers-reduced-motion: reduce` must disable parallax, particles, and large transforms**, leaving instant, legible states.

---

## 5. SHOPIFY THEME ARCHITECTURE

### 5.1 Stack & principles
- **Shopify Online Store 2.0** theme, JSON templates, sections everywhere, app-block ready.
- **Liquid** for markup; **vanilla CSS** with custom properties (no build step required); progressive-enhancement **vanilla JS** in small ES modules. (If a Tailwind/PostCSS pipeline is explicitly desired later, mirror the tokens in §4 as Tailwind theme values — but do not require a build step to ship.)
- **No heavy frameworks.** No React/Vue for the storefront. Keep JS < 50KB gzipped for the critical path.
- **Accessibility, performance, and merchant-editability are acceptance criteria, not afterthoughts.**

### 5.2 Folder structure (standard OS 2.0)
```
theme/
├── assets/            # css, js modules, fonts, svg sprite, textures
│   ├── base.css               # reset + tokens (§4) + primitives
│   ├── components.css         # component styles
│   ├── mc.js                  # entry: imports modules below
│   ├── mc-motion.js           # scroll reveals, parallax, particles (reduced-motion aware)
│   ├── mc-cart.js             # ajax cart drawer
│   ├── fonts/                 # self-hosted, subset
│   └── icons.svg              # sprite
├── config/
│   ├── settings_schema.json   # theme settings: colors, fonts, toggles (see §5.6)
│   └── settings_data.json
├── layout/
│   └── theme.liquid           # <head>, tokens, skip-link, header/footer includes
├── locales/
│   └── en.default.json        # all UI strings (translatable)
├── sections/          # every section listed in §5.4
├── snippets/          # icon, product-card, price, arch-frame, meta tags, etc.
├── blocks/            # theme blocks (OS 2.0) where useful
└── templates/         # *.json templates composing sections
    ├── index.json
    ├── collection.json
    ├── product.json
    ├── cart.json
    ├── page.json / page.about.json / page.faith.json
    ├── blog.json / article.json
    ├── search.json
    ├── list-collections.json
    └── customers/*.json
```

### 5.3 Design tokens & theming
- All tokens from §4 live in `base.css` under `:root`, plus a mapping from **theme settings** (§5.6) so a merchant can nudge accent colors and fonts without editing code.
- Provide a **light "parchment" section scheme** and a **dark "basilica" section scheme** as Shopify `color_scheme` presets, both AA-compliant. Sections accept a `color_scheme` setting.

### 5.4 Section & block library
Build these as configurable sections (each with sensible `presets` and `settings`, translatable labels, and a `{% schema %}`). Every section must degrade gracefully with empty content.

**Global**
- `header` — sticky, translucent-over-hero → solid on scroll; Chi-Rho brand mark; mega-menu with arch framing; search + cart-count; announcement bar slot.
- `footer` — multi-column (Shop, Faith & History, Help, Newsletter), Latin motto + translation, the signature closing line, payment icons in muted stone.
- `announcement-bar` — quiet, rotating, dismissible.

**Homepage — the scroll journey (§5.5)**
- `hero-basilica` — full-viewport marble entrance hall; slow parallax; incense/dust particles; single reverent headline + one CTA.
- `hall-of-virtues` — monumental sculpture showcase (image + short virtue statements: Endurance, Restoration, Reverence, Hope).
- `gallery-civilization` — editorial image grid / horizontal gallery of "Christian civilization" scenes with captions (environmental storytelling).
- `cathedral-marketplace` — featured collections/products presented as heirloom artifacts (large imagery, restrained copy, gold hairline framing).
- `library-of-faith` — content/blog teaser: Scripture, history, craft notes.
- `story-of-endurance` — the brand narrative (§1.6): Christ the King, Michael and the armies of Heaven, and the endurance of the faithful; reverent editorial with sculpture imagery. (This is the brief's **Story** step.)
- `final-sanctuary` — closing section centered on Christ (Resurrection / Christ the King imagery), the motto, newsletter, and gentle CTA.

**Reusable content sections**
- `image-with-text`, `rich-text`, `quote-scripture` (with translation + attribution), `collection-list`, `featured-collection`, `featured-product`, `sculpture-spotlight`, `heraldry-showcase` (original crests), `timeline` (continuity of history), `testimonial`, `newsletter`, `faq`, `logo-of-materials` (material library strip), `map-pilgrimage` (optional).

**Commerce sections**
- `main-product` — gallery + info + variant picker + add-to-cart; "provenance" tab (materials, craft story), care, and a small heraldic seal.
- `product-recommendations` — "From the same workshop."
- `main-collection` — filters, sort, grid/list toggle, collection banner with arch framing.
- `cart` + `cart-drawer` — ajax; parchment receipt aesthetic; free-shipping/threshold meter styled as a filling vessel; upsell block.
- `search` — predictive search dropdown + results page.
- `main-account`, `main-login`, `main-register`, `main-order`, `main-addresses` — styled to match, fully accessible.

### 5.5 Website experience (scroll journey)
The site should feel like entering a sacred imperial basilica. As the user scrolls the homepage they move through: **(1)** a grand marble entrance hall → **(2)** a Hall of Virtues with monumental sculptures → **(3)** a Gallery of Christian Civilization → **(4)** a Cathedral marketplace showcasing products as heirloom artifacts → **(5)** a Library of faith and history → **(6)** the brand's Story of endurance → **(7)** a final Sanctuary centered on Christ. (This maps to the creative brief's journey: **Hero Hall → Hall of Virtues → Collections → Library → Story → Sanctuary**.) Use subtle motion (incense smoke, flickering candlelight, dust in sunbeams, animated banners, soft light rays, slow parallax) and, if audio is ever enabled, reverent orchestral ambience behind an explicit, default-off, remembered opt-in. Every interaction feels intentional, quiet, refined.

### 5.6 Theme settings (`settings_schema.json`)
Expose, at minimum: brand colors (mapped to tokens, with the §4 palette as defaults), font pickers (display/body), logo + Chi-Rho mark, announcement bar, social links, newsletter, motion intensity (Full / Subtle / Off), enable-parallax toggle, enable-particles toggle, section color-scheme presets ("Basilica" dark, "Parchment" light), and an optional ambient-audio toggle (default off). Group settings logically with helpful info text so the merchant understands the reverent intent.

---

## 6. CONTENT, COMMERCE & COPY

### 6.1 Product collections (suggested taxonomy — adapt to real catalog)
- **The Vestiary** — garments: cloaks, tunics, heavy linen shirts, embroidered pieces.
- **The Armory** *(ceremonial / decorative only)* — heraldic pins, seals, ceremonial letter-openers, shields as wall art. No functional weapons framing; presented as craft and symbol.
- **The Reliquary** — jewelry & devotional objects: Chi-Rho pendants, crosses, signet rings, medals (original heraldry).
- **The Scriptorium** — books, journals, prints, illuminated-style stationery, maps, iconography prints.
- **The Household** — home goods: candles (beeswax), linens, ceramics, bronze/brass objects, banners.
- **Pilgrim's Kit** — travel & everyday carry with restrained heraldic detailing.

**Product types from the brief map in as:** luxury **apparel** → Vestiary; **jewelry** and **challenge coins / devotional medals** → Reliquary; **journals**, **art prints**, and stationery → Scriptorium; **coffee accessories**, **home décor**, candles, and ceramics → Household; heraldic **collectibles** and ceremonial pieces → Armory; **leather goods** and everyday carry → Pilgrim's Kit. Present every item with heirloom framing (materials, craft story, original heraldic seal).

Each collection gets: a reverent one-paragraph intro, an arch-framed banner, and a short "why this exists" line tied to a virtue. Product descriptions follow §6.2.

### 6.2 Copywriting rules
- **Product titles:** noun-forward, dignified (e.g., "Chi-Rho Signet Ring — Bronze"). Avoid gimmicky adjectives.
- **Product body:** 3 short movements — (1) what it is and the material/craft; (2) the meaning/heritage in one or two sentences; (3) practical details (size, care). Include a one-line Scripture or motto only where it fits naturally.
- **Microcopy:** buttons say plain, calm things ("Add to cart," "Enter the collection," "Read the history"). No fake urgency, no manipulative scarcity. Real stock/shipping info only.
- **Alt text:** describe the scene and material for accessibility and SEO ("Bronze Chi-Rho signet ring resting on aged parchment in candlelight").
- **Reading level:** literate but clear. Translate every Latin phrase.

### 6.3 SEO
- Semantic HTML5 landmarks (`header/nav/main/section/article/footer`), one `h1` per page, logical heading order.
- Per-template `<title>` and meta description patterns; Open Graph + Twitter cards with brand imagery; canonical URLs; `JSON-LD` structured data for `Product` (with `offers`, `AggregateRating` when present), `BreadcrumbList`, `Organization`, `WebSite` + `SearchAction`, and `Article` for the blog.
- Fast, crawlable, accessible pages (Core Web Vitals are an SEO input — see §7).
- Descriptive, keyword-aware but non-spammy copy grounded in the brand's real vocabulary (heirloom, bronze, Chi-Rho, marble, devotional, Christian craftsmanship).
- Clean handles, breadcrumb nav, XML sitemap (Shopify-generated), and internal linking between collections, products, and the Library/blog.

### 6.4 Brand voice quick-reference
Reverent, literate, warm, unhurried. Concrete over abstract. Faith over hype. When in doubt, write as if inscribing the line into marble — would it still feel right in a thousand years?

---

## 7. ACCESSIBILITY, PERFORMANCE, MOBILE

### 7.1 Accessibility (WCAG 2.1 AA target)
- Keyboard-operable everything; visible gold focus rings (never remove outlines without a replacement). Skip-to-content link.
- Correct semantics/ARIA for menus, dialogs (cart drawer, modals), tabs, accordions, carousels; manage focus traps and return focus on close.
- Color is never the only signal; all text meets AA contrast; form fields have real `<label>`s and error messaging.
- Respect `prefers-reduced-motion` (disable parallax/particles/large transforms). Provide reduced-transparency fallbacks.
- Images have meaningful `alt`; decorative images use empty `alt=""`.

### 7.2 Performance (Core Web Vitals budgets)
- **LCP < 2.5s**, **CLS < 0.1**, **INP < 200ms** on a mid-tier phone / 4G.
- Responsive images via Shopify `image_url` + `srcset`/`sizes`; explicit width/height to prevent CLS; lazy-load below the fold; eager-load the hero.
- Critical CSS inline-ish and small; defer non-critical JS (`type="module"`, `defer`); no render-blocking third parties.
- Self-hosted subset fonts, `font-display: swap`, preconnect only where needed.
- Textures/particles are lightweight (small tiled PNG/WebP or CSS/Canvas), never large video backgrounds on mobile.
- JS is progressive enhancement: the store works (browse, add to cart) with JS disabled where Shopify allows.

### 7.3 Mobile-first
- Design at 375px first; scale up. Touch targets ≥44px. Sticky, thumb-reachable add-to-cart on product pages.
- Simplify parallax/particles on mobile for battery and jank; keep the reverent atmosphere through type, color, and imagery instead.

---

## 8. MEDIA DIRECTION

### 8.1 AI image-generation prompts (house style)
When generating illustrations/backgrounds, prepend this **style stem** and forbid the anti-patterns:

> *"Late-Roman / Early-Christian imperial atmosphere, museum-quality, warm candlelit interior, black and Carrara marble, aged bronze, deep burgundy and olive accents, gold-leaf Chi-Rho motif, soft heaven rays and incense haze, hand-carved Renaissance-master sculpture, monumental basilica architecture, reverent and hopeful mood, cinematic soft light, fine grain, no text, no logos. Avoid: neon, saturated colors, plastic, modern minimalism, gothic horror, fantasy, cartoon."*

Provide ready-to-use prompts for: hero basilica interior; Hall of Virtues sculptures (Christ the King, Good Shepherd, Archangel Michael, the Resurrection); gallery scenes (Roman temple become church, monastery on Roman foundations, pilgrimage road with crosses and olive trees, candle-lit library/scriptorium); collection banners; and product-context backdrops (parchment, marble ledge, bronze, candlelight). Always request weathering — cracks, moss, ivy, candle soot — for authenticity. Keep sculptures dignified and non-graphic.

### 8.2 Product photography direction
Warm, low-key, single soft key light like a clerestory window; props of marble, parchment, linen, olive branches, beeswax candles; shallow depth; no harsh reflections. Consistent 4:5 and 1:1 crops. Every product also gets a clean, evenly-lit catalog shot for clarity.

### 8.3 Motion / 3D
Motion graphics are slow and reverent (see §4.6). Any 3D (e.g., a rotating relic/coin) is optional, lazy-loaded, `prefers-reduced-motion`-aware, and never blocks the critical path. Banners animate as if stirred by a faint breeze.

---

## 9. IMPLEMENTATION RULES FOR CLAUDE CODE (FABLE 5)

### 9.1 Working method
1. **Plan before building.** Produce a short build plan and a task list; confirm the catalog/collections mapping with the merchant before deep work.
2. **Ship in small, reviewable commits**, each doing one coherent thing, with clear messages. Never bundle unrelated changes.
3. **Tokens first, then primitives, then components, then sections, then templates.** Don't hard-code a color or size that belongs in a token.
4. **Every section is self-contained**: schema + styles + graceful empty state + translatable strings + a preset.
5. **Test as you go** in the theme editor mindset: does it work with no image? long text? no products? RTL-safe structure? keyboard only?
6. **Explain trade-offs** in commit messages / notes; surface anything that touches the guardrails in §1.4 for human review.

### 9.2 Coding standards
- **Liquid:** readable, commented where non-obvious; no logic-heavy templates; use snippets for reuse; guard against `nil`.
- **CSS:** token-driven; BEM-ish or utility-lite naming; no `!important` except documented resets; logical properties for i18n; `prefers-color-scheme`/scheme classes respected.
- **JS:** small ES modules, no jQuery, no framework; feature-detect; fail safe; never block the main thread; all interactive widgets keyboard-accessible.
- **Accessibility & performance are review-blockers**, not nice-to-haves.
- **No secrets in the repo.** No API tokens, no private endpoints, no internal hostnames.

### 9.3 Fallback rules
- Missing image → tasteful marble/parchment placeholder, never a broken image.
- Missing setting/section content → hide gracefully or show reverent default copy.
- JS disabled → core browse + add-to-cart still function where Shopify permits; drawer degrades to the `/cart` page.
- Slow network → skeletons in stone tones, not spinners; text remains readable before fonts load.
- Reduced motion / reduced data → static, calm equivalents.

### 9.4 Definition of done / acceptance criteria
A section or template is "done" only when **all** are true:
- [ ] Matches the Visual DNA (§3) and design system (§4); uses tokens, not hard-coded values.
- [ ] Fully responsive 320px → 1440px+; no layout shift (CLS < 0.1).
- [ ] Keyboard-accessible; visible focus; AA contrast; correct semantics/ARIA; `prefers-reduced-motion` honored.
- [ ] Graceful empty/edge states; works with no image and with very long/short content.
- [ ] Merchant-editable via schema with clear labels/help text and a working preset.
- [ ] Meets performance budgets (§7.2); images responsive with width/height.
- [ ] Copy follows §6.2 voice; Latin translated; no guardrail violations (§1.4).
- [ ] Committed in a focused commit with a clear message.

---

## 10. EXPANSION ROADMAP

- **Phase 1 — Foundations:** tokens, base/components CSS, icon sprite, header/footer, homepage scroll journey, one collection + product template, cart drawer, core content pages (About, Faith & History, FAQ, Contact). Ship a coherent, reverent MVP.
- **Phase 2 — Commerce depth:** full collection taxonomy (§6.1), predictive search, product provenance/heraldry modules, recommendations, reviews (respectful), account pages, blog "Library of Faith."
- **Phase 3 — Craft & atmosphere:** refined motion/particles, optional 3D relic viewer, ambient-audio opt-in, illuminated-manuscript editorial pieces, pilgrimage-map storytelling.
- **Phase 4 — Growth:** SEO content hub, structured data coverage, email capture flows, seasonal/liturgical-calendar merchandising (Advent, Lent, Easter, feast days) framed reverently, bundles ("The Pilgrim's Kit").
- **Phase 5 — Scale:** internationalization/translations, multi-currency, performance hardening, accessibility audit, and a documented design system others can extend.

Throughout every phase, hold the line: **history inspires the aesthetic; Christ remains the message.**
*Earthly empires rise and fall, but the Kingdom of Christ endures forever.*

---

### APPENDIX A — One-paragraph "elevator" version of this prompt
> Build a premium Shopify OS 2.0 theme for **Milites Christi** ("Soldiers of Christ"), a Christian heritage brand whose look is late-Roman / Early-Christian imperial: black and Carrara marble, aged bronze, deep burgundy and olive, warm candlelight, and the **Chi-Rho** as the central motif. It should feel like entering a 1,700-year-old basilica — timeless, sacred, majestic, hopeful. Use history (Rome, Byzantium, Christian Europe, the Reconquista, the military orders, classical figures of courage and endurance) purely as **aesthetic and moral inspiration**, with **original heraldry** rather than copied insignia, and always frame conflict as endurance and restoration, never conquest. Deliver a token-driven, accessible (WCAG AA), fast (good Core Web Vitals), mobile-first theme with a homepage scroll-journey (entrance hall → Hall of Virtues → Gallery of Civilization → Cathedral marketplace → Library of faith → final Sanctuary centered on Christ), a reusable section/block library, reverent copy, SEO structured data, and merchant-friendly theme settings. History inspires the aesthetic; Christ remains the message.

### APPENDIX B — Guardrail checklist (run before publishing any asset)
- [ ] Christ/the Gospel remains the message; heritage stays inspiration.
- [ ] No glorification of conquest, war, supremacy, or nationalism.
- [ ] Heraldry is original; no real historical insignia reproduced.
- [ ] Reverent, inclusive welcome; no gatekeeping by ethnicity/nationality/politics.
- [ ] Any conflict-derived imagery framed as endurance/restoration/hope.
- [ ] Accessibility, performance, and merchant-editability met.
