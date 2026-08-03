# Sasquatch Coffee — email template system

Shared design language for all Klaviyo templates in this directory.

## Palette

| Token | Hex | Use |
| --- | --- | --- |
| Forest | `#1F2E23` | Header bar, footer, headings |
| Bark | `#2B2B26` | Body copy |
| Cream | `#F7F3EA` | Page background |
| Card | `#FFFFFF` | Content surface |
| Ember | `#C8752D` | CTA buttons, links, accents |
| Sage | `#7D8C74` | Muted / secondary text |

## Construction rules

- Table-based layout, 600px max width, all CSS inlined — required for Outlook
  and Gmail, which strip `<style>` blocks inconsistently.
- Every template opens with a hidden preheader div so the inbox preview line is
  controlled rather than scraped from the first visible text.
- Buttons are bulletproof (table cell with background colour + padding), not
  styled `<a>` tags, so they render in Outlook.
- `@media (max-width:600px)` collapses the product grid to a single column.
- Images always carry `alt` text and explicit `width`, so a blocked-image render
  still reads as a coherent email.
- CAN-SPAM: physical mailing address and `{% unsubscribe %}` appear in the
  footer of every template. Non-negotiable.

## Klaviyo variables used

- `{{ first_name|default:"there" }}` — personalisation with a safe fallback.
- `{{ organization.name }}`, `{{ organization.full_address }}` — pulled from
  account settings so an address change does not require a template edit.
- `{% unsubscribe %}` — required opt-out link.
- Abandoned checkout uses `{{ event.extra.checkout_url|default:"https://sasquatchcoffee.store/cart" }}`
  so the CTA still lands somewhere useful if the Shopify payload lacks the URL.

## Product links

All product URLs and imagery reference live ACTIVE Shopify products verified on
2026-08-03. Archived products (handles ending `-archived`) are deliberately
avoided — linking to them would 404 or show an unbuyable page.
