# Turnstile Fingerprinting Surface: 2D Canvas

Analysis of the **2D canvas text/shape rendering** vector as it applies to Cloudflare Turnstile. This documents the fingerprinting *surface* — how a canvas signature is built, read back, hashed, and why it varies per device — not any token-forgery technique (Turnstile tokens are single-use and server-validated).

## Where it lives in Turnstile

Canvas code is **not** present in the ~84KB loader bundle we captured (`/turnstile/v0/b/<hash>/api.js`). That loader carries hook detection, trusted-interaction gates, and stack/timing telemetry, but no canvas/WebGL/audio calls [observed]. Those readback vectors are served by the **runtime challenge-platform payload** (`/cdn-cgi/challenge-platform/...`), which a test sitekey (`3x000...`) does not fully serve [observed]. So everything below describes a runtime-payload vector, reconstructed from the general canvas-fingerprinting technique rather than from a decompiled Turnstile canvas routine.

## How a canvas fingerprint is built

The standard pipeline is: render a fixed scene into an offscreen `<canvas>`, serialize the pixels, and hash the result. The rendered scene is chosen to maximize rasterization differences — typically a pangram string that exercises many glyphs plus overlaid shapes. Fingerprint.com's canonical example uses **"a string of text that uses all the letters of the alphabet (such as 'Cwm fjordbank glyphs vext quiz') with an image overlaid"** and draws **"colored rectangles, arcs, and text with rotation effects"** [confirmed by source — https://fingerprint.com/blog/canvas-fingerprinting/].

Typical operations a Turnstile-class scene would use:

| Step | Canvas API | Purpose |
|------|-----------|---------|
| Set font | `ctx.font = "..."` | Force a specific font stack → exposes font availability/substitution |
| Draw text | `ctx.fillText` / `strokeText` | Glyph rasterization differs by OS/hinting |
| Draw shapes | `fillRect`, `arc`, `bezierCurveTo` | Anti-aliasing/curve rasterization differs by GPU |
| Blend | `globalCompositeOperation`, emoji | Emoji glyphs + compositing add entropy |
| Read back | `toDataURL()` / `getImageData()` | Extract pixels for hashing |

## Readback and hashing

Two readback paths exist. The common one is `toDataURL()`, which **"returns a base64-encoded string representing the binary image file"** that is then hashed [confirmed by source — https://browserleaks.com/canvas]. Per MDN, `toDataURL()` defaults to `image/png` and returns a string of the form `data:image/png;base64,iVBORw0KGgo...` [confirmed by source — https://developer.mozilla.org/en-US/docs/Web/API/HTMLCanvasElement/toDataURL]. The alternative path, `getImageData()`, returns the raw `Uint8ClampedArray` of RGBA pixels — skipping PNG encoding, which avoids compression/metadata variance and gives a stabler read of the raster.

Hashing collapses the bytes to a compact ID. BrowserLeaks computes an **"MD5 hash of this string"**, or alternatively extracts **"the CRC checksum from the IDAT chunk, which is located 16 to 12 bytes from the end of every PNG file"** [confirmed by source — https://browserleaks.com/canvas]. The property that makes this useful for fingerprinting: **"even tiny differences in pixel output will result in a completely different hash"** [confirmed by source — https://fingerprint.com/blog/canvas-fingerprinting/]. That is also what makes it fragile against noise defenses (below).

Note `toDataURL` requires an **origin-clean** bitmap — a cross-origin image taint throws `SecurityError` [confirmed by source — MDN, above]. Turnstile draws its own primitives, so this is not a constraint for it, but it means any drawn asset must be same-origin or CORS-approved.

## Why output varies per device

The signature is stable per machine but differs across machines because the *same* draw calls rasterize differently down the stack:

- **Font rendering** — **"Anti-aliasing, hinting, and font availability can produce different results depending on your operating system, hardware, and settings"** [confirmed by source — Fingerprint.com]. Different installed fonts also change substitution.
- **GPU / drivers** — **"Differences in GPU or graphics drivers can further differentiate image output"** [confirmed by source — Fingerprint.com]. BrowserLeaks lists **"the web browser, operating system, graphics card, and other factors"** plus **"font rendering settings and anti-aliasing algorithms"** [confirmed by source — BrowserLeaks].
- **Sub-pixel geometry** — curve/arc tessellation and sub-pixel text positioning round differently per rasterizer, so bezier and rotated text add entropy on top of glyph shape (inferred, consistent with the anti-aliasing claims above).
- **Resolution metadata** — encoded PNGs carry **"a resolution of 96dpi"** [confirmed by source — MDN]; DPI/scaling differences can shift encoded bytes even when pixels match (inferred).

## Defenses that break it

Modern browsers randomize or block the readback, which defeats a stable hash. Fingerprint.com concedes **"Browser protections increasingly limit or randomize canvas output, reducing reliability for standalone fingerprinting approaches"** [confirmed by source — Fingerprint.com]. In practice: Brave and Firefox `privacy.resistFingerprinting` perturb `toDataURL`/`getImageData` output per-session, and the Tor Browser prompts/blocks readback (inferred — not established from a fetched source here; flagged). Because the hash is all-or-nothing, even single-LSB noise yields a different ID, so anti-bot systems treat canvas as *one* weak signal cross-checked against many others rather than a sole identifier.

---

*Scope caveat: this documents the canvas fingerprinting surface as a runtime-payload vector reconstructed from public technique sources; no Turnstile-specific canvas routine was recovered from the captured loader, and nothing here forges or bypasses a server-validated token.*
