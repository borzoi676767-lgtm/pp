/* ===========================================================================
   Sasquatch Coffee — Shopify Customer Events custom pixel
   ---------------------------------------------------------------------------
   WHY THIS FILE EXISTS
   Theme code does not run on Shopify's checkout pages (non-Plus), so pixels
   installed in the theme can never see `checkout_completed`. This script runs
   in Shopify's sandboxed Customer Events layer, which DOES fire on checkout —
   so it captures the full funnel, including purchases.

   HOW TO INSTALL
   1. Shopify admin → Settings → Customer events → Add custom pixel
   2. Name it "Sasquatch Tracking", paste this whole file in
   3. Fill in the three IDs below (leave a value as "" to skip that network)
   4. Set Permission = "Not required" only if you have a lawful basis; otherwise
      leave consent required so it respects the customer privacy API
   5. Save, then Connect

   Keep the theme snippet (snippets/tracking-pixels.liquid) as well: it adds
   richer on-site context. Duplicate PageViews between the two are normal and
   Meta/GA de-duplicate most of it; if you'd rather not double-count, clear the
   IDs out of Theme settings and rely on this pixel alone.
   =========================================================================== */

const CONFIG = {
  ga4MeasurementId: "",   // e.g. "G-XXXXXXXXXX"
  metaPixelId:      "",   // e.g. "123456789012345"
  tiktokPixelId:    ""    // e.g. "CXXXXXXXXXXXXXXXXXXX"
};

/* ---------- loaders ------------------------------------------------------ */
if (CONFIG.ga4MeasurementId) {
  const s = document.createElement("script");
  s.async = true;
  s.src = "https://www.googletagmanager.com/gtag/js?id=" + CONFIG.ga4MeasurementId;
  document.head.appendChild(s);
  window.dataLayer = window.dataLayer || [];
  window.gtag = function () { window.dataLayer.push(arguments); };
  gtag("js", new Date());
  gtag("config", CONFIG.ga4MeasurementId, { send_page_view: false });
}

if (CONFIG.metaPixelId) {
  /* eslint-disable */
  !function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
  n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;
  n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
  t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,
  document,'script','https://connect.facebook.net/en_US/fbevents.js');
  /* eslint-enable */
  fbq("init", CONFIG.metaPixelId);
}

if (CONFIG.tiktokPixelId) {
  /* eslint-disable */
  !function(w,d,t){w.TiktokAnalyticsObject=t;var ttq=w[t]=w[t]||[];
  ttq.methods=["page","track","identify","instances","debug","on","off","once","ready","alias","group","enableCookie","disableCookie"];
  ttq.setAndDefer=function(e,n){e[n]=function(){e.push([n].concat(Array.prototype.slice.call(arguments,0)))}};
  for(var i=0;i<ttq.methods.length;i++)ttq.setAndDefer(ttq,ttq.methods[i]);
  ttq.load=function(e,n){var i="https://analytics.tiktok.com/i18n/pixel/events.js";
  ttq._i=ttq._i||{},ttq._i[e]=[],ttq._i[e]._u=i,ttq._t=ttq._t||{},ttq._t[e]=+new Date,ttq._o=ttq._o||{},ttq._o[e]=n||{};
  var o=d.createElement("script");o.type="text/javascript",o.async=!0,o.src=i+"?sdkid="+e+"&lib="+t;
  var a=d.getElementsByTagName("script")[0];a.parentNode.insertBefore(o,a)};
  ttq.load(CONFIG.tiktokPixelId);
  }(window,document,'ttq');
  /* eslint-enable */
}

/* ---------- helpers ------------------------------------------------------ */
const money = (m) => (m && typeof m.amount === "number" ? m.amount : 0);
const cur   = (m) => (m && m.currencyCode) || "USD";

function lineItems(items) {
  return (items || []).map((li) => ({
    item_id: (li.variant && (li.variant.sku || li.variant.id)) || "",
    item_name: (li.variant && li.variant.product && li.variant.product.title) || "",
    item_variant: (li.variant && li.variant.title) || "",
    price: money(li.variant && li.variant.price),
    quantity: li.quantity || 1
  }));
}

/* ---------- events ------------------------------------------------------- */
analytics.subscribe("page_viewed", () => {
  if (CONFIG.ga4MeasurementId) gtag("event", "page_view");
  if (CONFIG.metaPixelId) fbq("track", "PageView");
  if (CONFIG.tiktokPixelId) ttq.page();
});

analytics.subscribe("product_viewed", (event) => {
  const v = event.data.productVariant;
  if (!v) return;
  if (CONFIG.ga4MeasurementId) {
    gtag("event", "view_item", {
      currency: cur(v.price), value: money(v.price),
      items: [{ item_id: v.sku || v.id, item_name: v.product && v.product.title, price: money(v.price) }]
    });
  }
  if (CONFIG.metaPixelId) {
    fbq("track", "ViewContent", {
      content_ids: [v.sku || v.id], content_type: "product",
      content_name: v.product && v.product.title,
      value: money(v.price), currency: cur(v.price)
    });
  }
  if (CONFIG.tiktokPixelId) {
    ttq.track("ViewContent", { content_id: v.sku || v.id, value: money(v.price), currency: cur(v.price) });
  }
});

analytics.subscribe("product_added_to_cart", (event) => {
  const li = event.data.cartLine;
  if (!li) return;
  const v = li.merchandise;
  const value = money(li.cost && li.cost.totalAmount);
  if (CONFIG.ga4MeasurementId) {
    gtag("event", "add_to_cart", {
      currency: cur(li.cost && li.cost.totalAmount), value,
      items: [{ item_id: (v && (v.sku || v.id)) || "", item_name: v && v.product && v.product.title, quantity: li.quantity }]
    });
  }
  if (CONFIG.metaPixelId) {
    fbq("track", "AddToCart", {
      content_ids: [(v && (v.sku || v.id)) || ""], content_type: "product",
      value, currency: cur(li.cost && li.cost.totalAmount)
    });
  }
  if (CONFIG.tiktokPixelId) {
    ttq.track("AddToCart", { content_id: (v && (v.sku || v.id)) || "", value, currency: cur(li.cost && li.cost.totalAmount) });
  }
});

analytics.subscribe("checkout_started", (event) => {
  const c = event.data.checkout;
  if (!c) return;
  const value = money(c.totalPrice);
  if (CONFIG.ga4MeasurementId) {
    gtag("event", "begin_checkout", { currency: cur(c.totalPrice), value, items: lineItems(c.lineItems) });
  }
  if (CONFIG.metaPixelId) {
    fbq("track", "InitiateCheckout", { value, currency: cur(c.totalPrice), num_items: (c.lineItems || []).length });
  }
  if (CONFIG.tiktokPixelId) ttq.track("InitiateCheckout", { value, currency: cur(c.totalPrice) });
});

analytics.subscribe("payment_info_submitted", (event) => {
  const c = event.data.checkout;
  if (!c) return;
  if (CONFIG.ga4MeasurementId) {
    gtag("event", "add_payment_info", { currency: cur(c.totalPrice), value: money(c.totalPrice) });
  }
  if (CONFIG.metaPixelId) fbq("track", "AddPaymentInfo", { value: money(c.totalPrice), currency: cur(c.totalPrice) });
});

/* THE ONE THAT MATTERS — never fires from theme code */
analytics.subscribe("checkout_completed", (event) => {
  const c = event.data.checkout;
  if (!c) return;
  const value = money(c.totalPrice);
  const orderId = (c.order && c.order.id) || c.token;
  if (CONFIG.ga4MeasurementId) {
    gtag("event", "purchase", {
      transaction_id: orderId, currency: cur(c.totalPrice), value,
      shipping: money(c.shippingLine && c.shippingLine.price),
      tax: money(c.totalTax), items: lineItems(c.lineItems)
    });
  }
  if (CONFIG.metaPixelId) {
    fbq("track", "Purchase", {
      value, currency: cur(c.totalPrice),
      content_ids: (c.lineItems || []).map((li) => (li.variant && (li.variant.sku || li.variant.id)) || ""),
      content_type: "product"
    });
  }
  if (CONFIG.tiktokPixelId) {
    ttq.track("CompletePayment", { value, currency: cur(c.totalPrice) });
  }
});
