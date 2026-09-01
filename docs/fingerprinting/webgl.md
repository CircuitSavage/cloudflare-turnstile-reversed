# WebGL Fingerprinting Surface (Cloudflare Turnstile)

Scope: analysis of the WebGL fingerprinting *surface* Turnstile can probe — GPU
identity strings, shader precision, and the software-renderer tell that outs headless
setups. This is not token forgery; tokens are single-use and server-validated.

## Where WebGL sits in the Turnstile flow

The 84KB loader bundle we captured (`/turnstile/v0/b/<hash>/api.js`) contains hook
detection, trusted-interaction gates, and stack/timing telemetry, but **no canvas,
WebGL, or audio probing** [observed]. The heavy device vectors load later, in the
runtime challenge-platform payload delivered after the initial `rch` POST. A `3x000…`
test sitekey never fully serves that payload, so WebGL is analyzed here as a
**runtime-payload vector**, not from loader source [observed].

The loader *does* reference `WebGLRenderingContext.getParameter` — but only inside its
native-code hook check, `function ma(e){return Function.toString.call(e).indexOf("[native code]")!==-1}`
[observed]. That matters for WebGL spoofing: if an anti-detect tool wraps `getParameter`
to lie about the renderer string, calling `.toString()` on that wrapper returns JS source
instead of `function getParameter() { [native code] }`, and the wrapper itself becomes the
tell [confirmed by source: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Function/toString].

## Primary vector: GPU vendor/renderer strings

The high-entropy WebGL signal is the `WEBGL_debug_renderer_info` extension, which "exposes
two constants with information about the graphics driver" — `UNMASKED_VENDOR_WEBGL` (vendor
string) and `UNMASKED_RENDERER_WEBGL` (renderer string) — available in both WebGL1 and
WebGL2, baseline since April 2017 [confirmed by source: https://developer.mozilla.org/en-US/docs/Web/API/WEBGL_debug_renderer_info].

```javascript
const gl = canvas.getContext("webgl");
const dbg = gl.getExtension("WEBGL_debug_renderer_info");
const vendor   = gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL);   // e.g. "Google Inc. (NVIDIA)"
const renderer = gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL); // e.g. "ANGLE (NVIDIA, GeForce RTX 3060 ...)"
```

Without the extension, plain `getParameter(gl.VENDOR)` / `getParameter(gl.RENDERER)` return
generic masked strings (typically `"WebKit"` / `"WebKit WebGL"`); the extension is what
unmasks the real driver identity, which is why it's the fingerprinting target (inferred).

Privacy gating matters for anti-detect detection: extension availability "depends on browser
privacy settings" and in Firefox with `privacy.resistFingerprinting=true` the extension is
**disabled** entirely [confirmed by source: https://developer.mozilla.org/en-US/docs/Web/API/WEBGL_debug_renderer_info].
So the *presence or absence* of `WEBGL_debug_renderer_info` is itself a signal, independent
of the string value it would return (inferred).

## The headless / software-renderer tell

Real browsers on real hardware return driver strings naming a physical GPU through ANGLE
(Direct3D/Metal/GL). Headless and server-side stacks fall back to software rasterizers whose
renderer strings are distinctive:

| Environment | Typical `UNMASKED_RENDERER_WEBGL` fragment |
|---|---|
| Windows GPU (Chrome/ANGLE) | `ANGLE (<vendor>, <GPU model> Direct3D11 ...)` |
| macOS GPU | `ANGLE (Apple, Apple M... , OpenGL ...)` / `Apple GPU` |
| Chrome software fallback | `Google SwiftShader` / `ANGLE (Google, Vulkan ... SwiftShader Device ...)` |
| Linux headless (Mesa) | `llvmpipe (LLVM ...)` / `Mesa ...` |

A `SwiftShader` or `llvmpipe` renderer, or a spoofed string that contradicts the rest of the
profile (e.g. an NVIDIA renderer on a UA claiming macOS), is a strong automation tell (inferred).
This is consistent with the general fingerprinting mechanism Fingerprint documents for the
canvas/WebGL family: rendering output varies with "the graphics card, operating system, browser
versions" and GPU/driver differences, giving a stable per-device identifier
[confirmed by source: https://fingerprint.com/blog/canvas-fingerprinting/].

## Secondary vectors: shader precision and extension set

Beyond the renderer string, `getShaderPrecisionFormat(shaderType, precisionType)` returns a
`WebGLShaderPrecisionFormat` with `rangeMin`, `rangeMax`, and `precision` (bits), for the six
precision types (`LOW/MEDIUM/HIGH` × `FLOAT/INT`) across vertex and fragment shaders — exposing
GPU-specific floating-point capability [confirmed by source: https://developer.mozilla.org/en-US/docs/Web/API/WebGLRenderingContext/getShaderPrecisionFormat].
A desktop GPU typically reports high-float `{rangeMin:127, rangeMax:127, precision:23}`; software
rasterizers and some mobile GPUs report different tuples, so the precision matrix corroborates (or
contradicts) the claimed renderer (inferred).

Additional low-cost, high-entropy WebGL parameters a runtime probe can read via `getParameter`:
`MAX_TEXTURE_SIZE`, `MAX_VIEWPORT_DIMS`, `MAX_VERTEX_UNIFORM_VECTORS`, `MAX_RENDERBUFFER_SIZE`,
`ALIASED_LINE_WIDTH_RANGE`, plus the *sorted list* of `getSupportedExtensions()` — all of which
cluster tightly by GPU/driver family (inferred). A profile whose vendor string says one GPU but
whose extension list or precision tuples match a software renderer is internally inconsistent, and
consistency-cross-checking is the practical detection strategy (inferred).

## Detection summary

1. Extension **presence** (`getExtension("WEBGL_debug_renderer_info") !== null`) — RFP/hardened browsers drop it.
2. **Renderer string** contents — SwiftShader/llvmpipe/Mesa = software = likely headless.
3. **getParameter hook integrity** — a wrapped `getParameter` fails the loader's `[native code]` `.toString` check [observed].
4. **Cross-field consistency** — renderer vs. UA/platform, vs. shader precision, vs. extension list.

Scope caveat: WebGL probing was not present in the captured loader bundle; behavior above is inferred for the runtime challenge-platform payload and from cited vendor documentation, not decompiled from Turnstile's runtime code.
