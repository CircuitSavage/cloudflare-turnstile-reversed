# Loader bundle internals

Concrete excerpts from the real versioned bundle (`/turnstile/v0/b/<hash>/api.js`, ~84 KB, minified).
Variable names are the bundle's own (mangled); host-API calls can't be renamed, so the logic is
legible. Short excerpts, quoted for analysis.

## Native-function / hook detection

```js
function ma(e){return Function.toString.call(e).indexOf("[native code]")!==-1}
```

`ma(fn)` is `true` only if the function's source contains `[native code]`. Any anti-detect tool that
redefines a getter (e.g. `navigator.webdriver`) or wraps an API (e.g. `WebGLRenderingContext.getParameter`)
makes `Function.toString` return JS source instead, so `ma()` returns `false` — the patch itself is
the tell. This is the concrete implementation of the tampering check that `docs/03` describes.

## Trusted-interaction gate

```js
var c=function(s){s.isTrusted&&(U.add(i),t(i))};
window.addEventListener("keydown",c,!0);
window.addEventListener("mousemove",c,!0);
window.addEventListener("touchstart",c,!0);
```

A human-interaction signal registers only when `s.isTrusted` is `true`, on keydown/mousemove/touchstart
in the capture phase. Synthetic `dispatchEvent` carries `isTrusted === false`, so scripted input never
registers. The same gate guards inbound postMessages:

```js
function Ko(e){return e.isTrusted&&zo(e.data)}
```

## Stack + timing telemetry

```js
function ji(e,t){try{var r=new Error().stack; ... [e, Math.max(0,Math.floor(X()-t)), r, ...]
```

Captures the call stack (`new Error().stack`) plus a timing delta and tags it. The stack read exposes
whether a Proxy or wrapper sits in the call chain of a probed call; the delta feeds behavioral scoring.

## Challenge-platform endpoint

```js
"/cdn-cgi/challenge-platform/".concat(v,"turnstile/f/av0/rch").concat(n,"/").concat(e,"/")
```

The collected signals are posted here (`e` is the sitekey). Note: the `platform` string in this bundle
is this endpoint path, **not** `navigator.platform` — an earlier note got that wrong, corrected here
and in `docs/03`.

## What's not in this file

No canvas/WebGL/audio probes — those load in the runtime challenge-platform payload (a test sitekey
does not fully serve it). This bundle is the orchestration + interaction/hook-detection layer.
