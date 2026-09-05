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

## Full render parameter reference (documented API)

The four fields above are what the bundle reads off the page for the challenge itself. The widget
also takes a wider set of configuration options through `turnstile.render()` (JS) or `data-*`
attributes (implicit). These are the **documented** render options, not reverse-engineered internals,
included here so the reference is complete. Every JS option has a `data-` attribute equivalent
(camelCase becomes kebab-case: `responseField` → `data-response-field`).

| JS option | `data-*` attribute | Values | Default | Purpose |
|---|---|---|---|---|
| `sitekey` | `data-sitekey` | `0x…` (test: `1x/2x/3x…`) | — | Required. Public site key. |
| `action` | `data-action` | ≤32 chars, `[a-zA-Z0-9_-]` | — | Label echoed back at siteverify. |
| `cData` | `data-cdata` | ≤255 chars | — | Customer payload, echoed at siteverify. |
| `callback` | `data-callback` | fn(token) | — | Fired with the token on success. |
| `error-callback` | `data-error-callback` | fn(code) | — | Fired on error; return `true` to suppress the default UI. |
| `expired-callback` | `data-expired-callback` | fn() | — | Token expired (past its ~300s TTL). |
| `timeout-callback` | `data-timeout-callback` | fn() | — | Interactive challenge not completed in time. |
| `before-interactive-callback` | `data-before-interactive-callback` | fn() | — | Just before an interactive challenge shows. |
| `after-interactive-callback` | `data-after-interactive-callback` | fn() | — | Just after it finishes. |
| `unsupported-callback` | `data-unsupported-callback` | fn() | — | Browser unsupported. |
| `theme` | `data-theme` | `auto` \| `light` \| `dark` | `auto` | Widget colour theme. |
| `size` | `data-size` | `normal` \| `flexible` \| `compact` | `normal` | Widget footprint. |
| `appearance` | `data-appearance` | `always` \| `execute` \| `interaction-only` | `always` | When the widget is visible. |
| `execution` | `data-execution` | `render` \| `execute` | `render` | Whether the challenge runs on render or waits for `turnstile.execute()`. |
| `language` | `data-language` | `auto` or ISO 639-1 | `auto` | UI language. |
| `tabindex` | `data-tabindex` | integer | `0` | Tab order of the widget. |
| `retry` | `data-retry` | `auto` \| `never` | `auto` | Auto-retry on challenge failure. |
| `retry-interval` | `data-retry-interval` | ms (0–900000) | `8000` | Delay between retries. |
| `refresh-expired` | `data-refresh-expired` | `auto` \| `manual` \| `never` | `auto` | Behaviour when a token expires. |
| `refresh-timeout` | `data-refresh-timeout` | `auto` \| `manual` \| `never` | `auto` | Behaviour when an interactive challenge times out. |
| `response-field` | `data-response-field` | bool | `true` | Insert the hidden `<input>` with the token. |
| `response-field-name` | `data-response-field-name` | string | `cf-turnstile-response` | Name of that hidden input. |

The two that matter most for automation:

- **`execution`** decides *when* the challenge runs. `render` (default) starts it as soon as the
  widget mounts; `execute` holds off until the page calls `turnstile.execute()`, so a token is only
  minted on demand. If a token appears without any visible widget, `execution: 'execute'` paired with
  an `appearance` that hides the box is usually why.
- **`appearance`** decides *whether you see it*. `interaction-only` renders nothing unless Cloudflare
  decides interaction is needed, `execute` shows it only while the challenge runs, `always` keeps the
  box on the page. None of these change how the token is scored; they only change the visible surface.

Neither field is part of the token. They configure the widget lifecycle on the page, which is why a
solver only needs `sitekey`, `action`, and `cData` to reproduce a valid solve — the rest is display.
