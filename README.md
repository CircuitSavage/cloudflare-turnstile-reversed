<div align="center">

# cloudflare-turnstile-reversed

Turnstile challenge internals, captured live: the request flow, the challenge bundle, and a capture toolkit. The byte-level teardown is a marked slot, not written from memory.

<p>
<img src="https://img.shields.io/badge/python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+">
<img src="https://img.shields.io/badge/license-MIT-007EC7?style=for-the-badge" alt="MIT">
<a href="https://t.me/jujucodings"><img src="https://img.shields.io/badge/Telegram-%40jujucodings-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram"></a>
</p>

<sub>Need it solved, not reversed? <a href="https://peak.fo/?utm_source=github&utm_medium=readme&utm_campaign=re&utm_content=cloudflare-turnstile-reversed"><strong>Peak</strong></a> solves Cloudflare Turnstile and the 5s challenge via API — pay per success, from $1/1K, free key with code <code>PEAKGH</code>. (reCAPTCHA coming soon.)</sub>

</div>

---

## What's here

- `tools/capture.py` — pull the `sitekey` / `cData` / `action` off a page; `--solve` returns a token.
- `docs/01-challenge-flow.md` — the live request flow (loader → bundle → challenge-platform), captured.
- `docs/02-widget-params.md` — the parameters the bundle reads, taken from the real bundle.

## Quick start

```bash
python tools/capture.py https://example.com/
PEAK_API_KEY=pk_your_key python tools/capture.py https://example.com/ --solve
```

## The flow (captured live, not guessed)

```
loader    GET  challenges.cloudflare.com/turnstile/v0/api.js?render=explicit   -> 302
bundle    GET  challenges.cloudflare.com/turnstile/v0/b/<hash>/api.js          -> obfuscated challenge JS (84 KB)
orchestr  POST challenges.cloudflare.com/cdn-cgi/challenge-platform/h/b/turnstile/f/av0/rch/<seg>/<sitekey>
token     ->   submitted as the cf-turnstile-response field
```

## The reverse

The step-2 bundle is minified and rotates per build; step 3 posts the fingerprint/proof payload. The byte-level teardown of that payload is the gated part — the slot for it is marked in [`docs/01-challenge-flow.md`](docs/01-challenge-flow.md).

## Legitimate use

Research and automation on data you are allowed to access. Respect each site's Terms of Service and `robots.txt`. No credential stuffing.

## License

MIT.
