<div align="center">

<a href="https://peak.fo/?utm_source=github&utm_medium=readme&utm_campaign=re&utm_content=cloudflare-turnstile-reversed">
  <img src="./assets/peak-banner.png" alt="Peak — solve Cloudflare Turnstile & the 5s challenge in ~1s" width="100%">
</a>

# cloudflare-turnstile-reversed

A sourced teardown of how Cloudflare Turnstile fingerprints and scores browsers, plus a live capture tool. Every claim is cited or tagged `[observed]` / `(inferred)` — no filler, no memory guesses.

<p>
<img src="https://img.shields.io/badge/python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+">
<img src="https://img.shields.io/badge/license-MIT-007EC7?style=for-the-badge" alt="MIT">
<a href="https://t.me/jujucodings"><img src="https://img.shields.io/badge/Telegram-%40jujucodings-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram"></a>
</p>

<sub>Need it solved, not studied? <a href="https://peak.fo/?utm_source=github&utm_medium=readme&utm_campaign=re&utm_content=cloudflare-turnstile-reversed"><strong>Peak</strong></a> solves Cloudflare Turnstile and the 5s challenge via API — pay per success, from $1/1K, free key, no card. (reCAPTCHA coming soon.)</sub>

</div>

---

## Docs

- **[docs/fingerprinting/](docs/fingerprinting/)** — the deep layer: 8 per-field teardowns (behavioral, automation-tells, canvas, WebGL, audio, device-coherence, TLS/HTTP2, IP/scoring/PoW), each cited and tagged confirmed/observed/inferred. Start at its [index](docs/fingerprinting/README.md).
- [docs/03-fingerprinting.md](docs/03-fingerprinting.md) — the one-page fingerprinting overview (surface map; the `docs/fingerprinting/` set goes deeper per field).
- **[docs/04-loader-internals.md](docs/04-loader-internals.md)** — concrete code from the real bundle: the `[native code]` hook-detection function, the `isTrusted` interaction gate, stack/timing telemetry, the endpoint builder.
- [docs/01-challenge-flow.md](docs/01-challenge-flow.md) — the live request flow (loader → versioned bundle → challenge-platform), captured.
- [docs/02-widget-params.md](docs/02-widget-params.md) — the widget parameters the bundle reads (`sitekey`, `cData`, `action`, `chlPageData`).

## Tool

`tools/capture.py` — pull the `sitekey` / `cData` / `action` off a page; `--solve` returns a token.

```bash
python tools/capture.py https://example.com/
PEAK_API_KEY=pk_your_key python tools/capture.py https://example.com/ --solve
```

## Scope

**Is:** a sourced map of the fingerprinting surface (which signals, collected where) and capture tooling. **Isn't:** a byte-level deobfuscation of the versioned bundle, the challenge-platform payload schema, or token construction — and not a token-forgery method, since tokens are single-use and validated server-side via siteverify.

## Legitimate use

Research and automation on data you are allowed to access. Respect each site's Terms of Service and `robots.txt`. No credential stuffing.

## License

MIT.
