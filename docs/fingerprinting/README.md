# Turnstile fingerprinting surface

Field-by-field analysis of the signals Cloudflare Turnstile collects to separate a real
browser from an automated one. The scope throughout is the *fingerprinting surface* — what
is read, how it varies, and how tampering is caught — not token forgery. Turnstile tokens are
single-use and server-validated at `siteverify`, so nothing here bypasses verification.

Two layers are distinguished in every doc. The **loader** is the ~84KB versioned bundle we
captured live (`/turnstile/v0/b/<hash>/api.js`): it carries the trusted-interaction gate, the
`ma()` native-code hook check, and stack/timing telemetry. The heavier device vectors
(canvas, WebGL, audio) live in the **runtime challenge-platform payload**
(`/cdn-cgi/challenge-platform/...`), which a `3x000…` test sitekey does not fully serve — so
those docs reconstruct the vector from public technique sources and flag it as such.

Claims are tagged **[confirmed by source]** (fetched citation), **[observed]** (our own loader
capture), or **(inferred)** (reasoning).

## Field docs

| Doc | Layer | Summary |
|---|---|---|
| [behavioral-interaction.md](behavioral-interaction.md) | loader | `Event.isTrusted` capture-phase gate on keydown/mousemove/touchstart; synthetic input is silently dropped, timing deltas feed scoring. |
| [automation-tells.md](automation-tells.md) | loader | Cheap boolean checks (`webdriver`, `window.chrome`, plugins, `cdc_`) and the `ma()` meta-check that catches you spoofing them. |
| [canvas.md](canvas.md) | runtime | 2D text/shape render → `toDataURL`/`getImageData` → hash; per-device variance from fonts, GPU, and rasterization. |
| [webgl.md](webgl.md) | runtime | `WEBGL_debug_renderer_info` GPU strings, shader precision, and the SwiftShader/llvmpipe software-renderer headless tell. |
| [audio.md](audio.md) | runtime | `OfflineAudioContext` oscillator→compressor render; float math diverges by engine/OS/CPU into a stable low-entropy hash. |
| [device-coherence.md](device-coherence.md) | loader | CPU/RAM/UA-CH/platform/touch cross-checks; each value is coarse, the signal is their *disagreement*. |
| [tls-http2.md](tls-http2.md) | transport | JA3/JA4 ClientHello and HTTP/2 fingerprints computed at the edge; must match the browser the JS claims to be. |
| [ip-scoring-pow.md](ip-scoring-pow.md) | scoring | IP reputation (residential vs datacenter), the 1–99 bot score's three engines, and proof-of-work/proof-of-space. |

## Sources

Cloudflare
- https://developers.cloudflare.com/turnstile/
- https://blog.cloudflare.com/turnstile-ga/
- https://developers.cloudflare.com/bots/concepts/bot-score/
- https://developers.cloudflare.com/bots/concepts/ja3-ja4-fingerprint/

Fingerprinting technique writeups
- https://fingerprint.com/blog/canvas-fingerprinting/
- https://fingerprint.com/blog/audio-fingerprinting/
- https://browserleaks.com/canvas
- https://intoli.com/blog/not-possible-to-block-chrome-headless/
- https://scrapfly.io/blog/posts/how-to-bypass-cloudflare-anti-scraping
- https://github.com/abrahamjuliot/creepjs
- https://github.com/ultrafunkamsterdam/undetected-chromedriver

TLS / HTTP/2 fingerprinting
- https://lwthiker.com/networks/2022/06/17/tls-fingerprinting.html
- https://github.com/FoxIO-LLC/ja4/blob/main/technical_details/JA4.md
- https://www.trickster.dev/post/understanding-http2-fingerprinting/

MDN Web Docs
- https://developer.mozilla.org/en-US/docs/Web/API/Event/isTrusted
- https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/addEventListener
- https://developer.mozilla.org/en-US/docs/Web/API/Navigator/webdriver
- https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Function/toString
- https://developer.mozilla.org/en-US/docs/Web/API/HTMLCanvasElement/toDataURL
- https://developer.mozilla.org/en-US/docs/Web/API/WEBGL_debug_renderer_info
- https://developer.mozilla.org/en-US/docs/Web/API/WebGLRenderingContext/getShaderPrecisionFormat
- https://developer.mozilla.org/en-US/docs/Web/API/OfflineAudioContext
- https://developer.mozilla.org/en-US/docs/Web/API/OscillatorNode
- https://developer.mozilla.org/en-US/docs/Web/API/DynamicsCompressorNode
- https://developer.mozilla.org/en-US/docs/Web/API/Navigator/hardwareConcurrency
- https://developer.mozilla.org/en-US/docs/Web/API/Navigator/deviceMemory
- https://developer.mozilla.org/en-US/docs/Web/API/User-Agent_Client_Hints_API
