# Klaviyo automation build — Sasquatch Coffee

Built 2026-08-03. Account `RAzGAN`.

**Every flow is in `draft`. Nothing sends until it is manually switched to live.**
That is deliberate — see [Blockers](#blockers).

---

## Flows

| Flow | ID | Trigger | Steps |
| --- | --- | --- | --- |
| Welcome Series — Email | `SwB32x` | Added to `Email List` (`TVS8nT`) | Email → 3d → Email |
| Abandoned Checkout — Email + SMS | `X2JBRJ` | `Checkout Started` (`SkHKHH`) | 4h → Email → 20h → SMS |
| Welcome Series — SMS | `TseQRF` | Added to `Text Messaging List` (`Sevczs`) | SMS → 4d → SMS |
| Browse Abandonment — Email | `TLKSff` | `Viewed Product` (`Tw8ABz`) | 4h → Email |
| Post-Purchase — Thank You | `UjnUxV` | `Placed Order` (`SXJNkk`) | 1d → Email |

### Entry and re-entry rules

- **Welcome (email + SMS)** — `alltime / 1`, so a profile enters once and never again.
- **Abandoned Checkout** — re-entry after 30 days, so a repeat abandoner is not spammed.
- **Browse Abandonment** — re-entry after 7 days.
- **Post-Purchase** — `alltime / 0`, i.e. re-entry allowed, because it should fire on every order.

### Suppression filters

`Browse Abandonment` carries a flow-level profile filter with two condition groups:

1. `Placed Order` count `equals 0` since flow start — anyone who buys between the product
   view and the send drops out rather than receiving a "still thinking it over?" email
   for something they already bought.
2. Email marketing consent required.

SMS actions do not need an equivalent consent filter — Klaviyo only delivers SMS steps to
profiles with SMS consent regardless of flow configuration.

---

## Templates

| Template | ID | Used by |
| --- | --- | --- |
| SQ · Welcome 01 — Glad you found us | `TqkkK9` | Welcome Email, step 1 |
| SQ · Abandoned Checkout 01 — Left at the trailhead | `Ut6V96` | Abandoned Checkout, step 2 |
| SQ · Browse Abandon 01 — Still thinking it over | `SAD3jz` | Browse Abandonment; reused as Welcome step 3 |
| SQ · Post-Purchase 01 — Thank you + brewing | `V46XBc` | Post-Purchase, step 2 |

Source HTML lives in `templates/`. Design rationale is in `templates/_base-notes.md`.

### Render verification

`Ut6V96` was rendered through the template-render API against two contexts:

- **Populated** — `first_name: "Marcus"` and a checkout URL resolved to `Marcus` and the
  real checkout link.
- **Empty** — resolved to `Hey` and fell back to `https://sasquatchcoffee.store/cart`.

So neither a missing name nor a missing checkout URL produces a blank or a dead link.

---

## Blockers

### 1. Sender address fails authentication

Klaviyo auto-populated every flow message with the account default sender,
`borzoi67.67.67@gmail.com`. `gmail.com` publishes `DMARC p=reject`, so bulk mail sent via
Klaviyo from that address fails alignment and is junked or bounced.

Fix: authenticate a sending domain, then change the account default sender. Flow messages
inherit it — no template or flow edits required.

### 2. Test sends cannot run

**Email — resolved 2026-08-03.** The only available test address is the account owner's own
(`borzoi67.67.67@gmail.com`), which was globally suppressed since 2026-07-15.

Inspecting the suppression event showed `suppression_method: BOT_PROTECTION` — Klaviyo's
automated bot filtering caught the signup, it was *not* a deliberate human suppression.
That distinction matters: there was no opt-out intent to override.

With the owner's approval the address was resubscribed via the subscribe endpoint
(`custom_source` records the authorisation), which cleared the suppression:
`consent: SUBSCRIBED`, `suppression: []`, `can_receive_email_marketing: true`.

**SMS — still blocked.** All 13 profiles in the account report `NEVER_SUBSCRIBED` for SMS
marketing. There is no consented number in the account to send a test to, and consent was
not added on anyone's behalf.

Unblock for SMS: opt a real number in via the join keyword or the signup popup, then the
test can run.

---

## Test send record

| | |
| --- | --- |
| Campaign | `01KZ56K3SRTVBAXBHXZWKKWEBD` — "TEST - Welcome template delivery check" |
| Audience | Preview List `TiR5Lg` — 1 profile, the owner's own address |
| Template | `TqkkK9` (Klaviyo clones per-campaign; clone was `XgpgNH`) |
| Smart sending | Disabled, so a recent-send rule could not silently skip the test |
| Sender | `borzoi67.67.67@gmail.com` — the unauthenticated address, deliberately, to observe real-world deliverability |

The send was queued successfully. Because the sender domain is still unauthenticated, the
inbox placement of this test is itself the diagnostic: landing in spam or bouncing confirms
the DMARC problem above rather than indicating a fault in the template.

---

## Known gaps

- The abandoned-checkout **SMS** links to the static `/cart` page rather than the live
  `checkout_url`. The email step uses the dynamic URL. Worth upgrading the SMS to the
  dynamic variable once a real Checkout Started payload can be inspected.
- The discount code `WELCOME10` referenced in the welcome email and welcome SMS was verified
  against Shopify on 2026-08-03: it exists and is **ACTIVE**
  ("WELCOME10 — Email Signup Welcome"). No action needed.
