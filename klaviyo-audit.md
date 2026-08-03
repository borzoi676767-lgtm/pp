# Klaviyo Account Audit — Sasquatch Coffee

**Account:** Sasquatch Coffee (`RAzGAN`) · sasquatchcoffee.store
**Audit date:** 2026-08-03
**Timezone:** America/New_York · **Currency:** USD

---

## Headline

The account is **provisioned but not operating**. Data collection is working — Shopify
is connected and firing events, the signup popup is live, segments are built. But there
is **nothing on the sending side at all**: zero flows, zero campaigns, zero templates.

Two findings block revenue today. Everything else is secondary.

---

## Blocking issues

### 1. No flows exist — the live popup collects signups into a void

`GET /api/flows` returns an empty set. There is no welcome series, no abandoned
checkout, no browse abandonment, no post-purchase, no win-back — nothing.

This matters more than "some automation is missing," because the popup **is live** and
the Email List uses **double opt-in**. A visitor subscribes, receives the opt-in
confirmation, and then hears nothing. Every signup captured right now is being spent
for no return.

The Shopify events needed to build the standard flows are already flowing:

| Flow | Trigger metric | Available |
| --- | --- | --- |
| Abandoned Checkout | `Checkout Started` (`SkHKHH`) | Yes |
| Abandoned Cart | `Added to Cart` (`W49rc7`) | Yes |
| Browse Abandonment | `Viewed Product` (`Tw8ABz`) | Yes |
| Post-Purchase / Thank You | `Placed Order` (`SXJNkk`) | Yes |
| Shipping Notification | `Confirmed Shipment` (`TAdtLN`) | Yes |
| Welcome Series | `Subscribed to List` (`TLm2hq`) → Email List `TVS8nT` | Yes |
| Win-Back | Segment `RD5sKG` (Win-Back Opportunities) | Yes |

Nothing is missing on the data side. The flows simply were never built.

### 2. Sending address is a `@gmail.com` account — bulk email will not deliver

The account's default sender is:

```
Sasquatch Coffee <borzoi67.67.67@gmail.com>
```

`gmail.com` publishes `DMARC p=reject`. Since the Google/Yahoo bulk-sender requirements
took effect in February 2024, mail sent through a third party (Klaviyo) with a
`From:` address at `gmail.com` fails DMARC alignment and is rejected or junked — most
aggressively by Gmail itself, which is where a large share of any consumer coffee list
will sit.

**Do not turn on any sending until this is fixed.** Turning flows live against this
sender would burn the domain reputation of the store's first real send.

Fix: authenticate a branded sending domain in Klaviyo (e.g. `send.sasquatchcoffee.store`),
publish the DKIM/SPF/DMARC records Klaviyo generates, and change the default sender to
something like `hello@sasquatchcoffee.store`.

---

## What is working

- **Shopify integration** (`0eMvjm`) — healthy and current. Placed Order, Checkout
  Started, Added to Cart, Viewed Product, Viewed Collection, Fulfilled Order, Confirmed
  Shipment, Refunded Order, Cancelled Order all present, with events as recent as
  2026-07-30.
- **Signup form** — "Email & SMS Popup" (`UYMQHh`) is **live**, capturing both channels.
- **Segments** — 10 segments, all active, none stuck processing. The Shopify-driven
  ones are correctly built against real metric IDs:
  - VIP Customers (>5 orders), Repeat Buyers (>1 order), Potential Purchasers
    (browsed, never ordered), Churn Risks, Win-Back Opportunities (ordered ever, not in 180d)
  - Engaged 30/60/90-day tiers for send-reputation warmup
  - All Text Message Subscribers
- **SMS** — provisioned since 2026-07-25 (sending number active, Text Messaging List
  and SMS metrics present).
- **Lists** — Email List (double opt-in), Text Messaging List (double opt-in),
  Preview List (single opt-in, for internal previews).

## Gaps, non-blocking

| Item | State | Note |
| --- | --- | --- |
| Campaigns (email) | 0 | None ever created or sent |
| Campaigns (SMS) | 0 | None ever created or sent |
| Email templates | 0 | No base template to build from |
| Email List size | **3 profiles** | Effectively empty; popup is live but new |
| Account industry | Not set | Affects Klaviyo benchmark reporting |
| Website URL | `http://sasquatchcoffee.store` | Should be `https://` |
| Webhooks | 0 | Not required; noted for completeness |

---

## Recommended order of work

1. **Authenticate a sending domain and change the default sender off `@gmail.com`.**
   Blocks everything downstream.
2. **Build a base email template** carrying Sasquatch Coffee branding, so flows are not
   each styled from scratch.
3. **Build the flows**, in descending revenue-per-recipient order:
   1. Abandoned Checkout (highest RPR of any ecommerce flow)
   2. Welcome Series — matters most right now, since the popup is already live
   3. Post-Purchase / Thank You
   4. Browse Abandonment
   5. Win-Back, against the existing `RD5sKG` segment
4. **Grow the list before campaigning.** At 3 profiles there is no audience to send a
   campaign to. The popup is live; the constraint is traffic, not capture.
5. **Warm up sending** using the Engaged 30/60/90 segments already built, rather than
   blasting the full list on the first send.

---

## Audit method

Read-only inspection via the Klaviyo API on 2026-08-03. Endpoints covered: accounts,
flows, campaigns (email + SMS), lists, segments, metrics, templates, forms, webhooks.
No configuration was changed and nothing was enabled as part of this audit.
