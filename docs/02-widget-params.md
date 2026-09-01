# Widget parameters

From the real bundle (`/turnstile/v0/b/<hash>/api.js`, 84,236 bytes on capture). Symbol counts in
that file: `sitekey` 17, `chlPageData` 14, `cData` 13, `cf-turnstile-response` 1.

The widget is configured declaratively:

```html
<div class="cf-turnstile" data-sitekey="0x4AAAAAAA..." data-action="login" data-cdata="user-123"></div>
```

or explicitly:

```js
turnstile.render('#box', { sitekey: '0x4AAAAAAA...', action: 'login', cData: 'user-123', callback: onToken });
```

Inputs the bundle reads:

| Field | Source | Notes |
|---|---|---|
| `sitekey` | page | public key. `0x…` in prod; `1x/2x/3x…` are Cloudflare test keys. |
| `action` | page (optional) | free label, echoed into the result and readable at siteverify. |
| `cData` | page (optional) | customer data string, same path as `action`. |
| `chlPageData` | server-rendered page | passed into the widget at runtime; not a static attribute. |

Output:

| Field | Notes |
|---|---|
| `cf-turnstile-response` | the token; submitted with the form, validated server-side via siteverify. |

`tools/capture.py` extracts `sitekey`, `cData`, and `action` from the page HTML. `chlPageData` is
injected at runtime by the bundle, so it only shows up in a browser capture, not a static fetch.
