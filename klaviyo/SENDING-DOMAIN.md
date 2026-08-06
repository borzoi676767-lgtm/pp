# Sending domain setup — send.sasquatchcoffee.store

Registered 2026-08-06. Klaviyo ID `dyn_ONSW4ZBOONQXG4LVMF2GG2DDN5TGMZLFFZZXI33SMU`.

**Status: `pending`** — awaiting DNS publication. Nothing changes about how mail sends
until this verifies and is activated.

## Why this exists

Every flow message currently sends from `borzoi67.67.67@gmail.com`. `gmail.com` publishes
`DMARC p=reject`, and the 2026-08-03 test send proved the misalignment concretely: the
message was signed by `kocruj.shared.klaviyomail.com` while the visible From domain was
`gmail.com`. SPF/DKIM therefore did not align with the From domain, so DMARC evaluation
fails. Gmail accepted rather than rejected that test, but acceptance is not inbox placement.

Authenticating a subdomain fixes the alignment.

## Configuration choice

`dynamic` (delegated). Four NS records hand the `send.` subdomain to Klaviyo, which then
manages the DKIM/SPF records inside that zone — including future key rotations, without
further DNS work. Only the subdomain is delegated; the root domain, the website, and
existing MX/mail records are untouched.

## DNS records to publish

At the registrar holding `sasquatchcoffee.store`:

| Type | Host | Value |
| --- | --- | --- |
| NS | `send.sasquatchcoffee.store` | `ns1.klaviyo.com` |
| NS | `send.sasquatchcoffee.store` | `ns2.klaviyo.com` |
| NS | `send.sasquatchcoffee.store` | `ns3.klaviyo.com` |
| NS | `send.sasquatchcoffee.store` | `ns4.klaviyo.com` |
| TXT | `@` (root) | `klaviyo-site-verification=RAzGAN` |

All five are required. The TXT sits on the **root** domain, not the subdomain — that one is
easy to misfile.

Some registrars want the host as just `send` rather than the fully-qualified name, and `@`
may be expressed as blank or as the bare domain. Follow the registrar's convention.

## After publishing

1. DNS propagates — usually minutes, occasionally up to a few hours.
2. Run a verification job against the domain.
3. Once verified, activate it.
4. Change the account default sender to an address on the domain, e.g.
   `hello@sasquatchcoffee.store`. Flow messages inherit the account default, so no template
   or flow edits are needed.
5. Re-run a test send and confirm inbox placement rather than acceptance.

Only after step 5 should the five draft flows be switched live.

## Note on future testing

`create_template_preview_send_job` is now available, which sends a template test directly to
named recipients. That is the correct tool for future test sends — it does not require the
recipient to be subscribed and does not touch consent records, unlike the campaign-to-a-list
approach used on 2026-08-03.
