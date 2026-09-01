# Turnstile challenge flow

Captured live from a real Turnstile page (sitekey `3x00000000000000000000FF`, the Cloudflare
test key), Chrome UA. Every URL below is an observed request, not a guess.

```
1  GET   challenges.cloudflare.com/turnstile/v0/api.js?onload=…&render=explicit      302
2  GET   challenges.cloudflare.com/turnstile/v0/b/<hash>/api.js                       200   ← challenge bundle
3  POST  challenges.cloudflare.com/cdn-cgi/challenge-platform/h/b/turnstile/f/av0/rch/<seg>/<sitekey>
4  token submitted as the  cf-turnstile-response  form field
```

Step 1 is a thin loader. The real logic is the versioned bundle in step 2
(`/turnstile/v0/b/e694063b5082/api.js`, 84,236 bytes on capture). Grepping that bundle for the
parameters it reads:

```
sitekey        17×
chlPageData    14×
cData          13×
cf-turnstile-response  1×
```

So the inputs the widget consumes are `sitekey`, `cData`, `action`, and `chlPageData`; the output
is the `cf-turnstile-response` token, which Cloudflare validates server-side via siteverify. Those
are the four fields `tools/capture.py` extracts from a page.

The bundle in step 2 is minified and rotates per build (the `<hash>` changes), and step 3 is where
the fingerprint/proof payload is assembled and posted. A byte-level teardown of that payload is the
gated part.

> **Proprietary teardown — verified findings go here.**
> (bundle deobfuscation, the step-3 payload schema, and the token construction. Left as a marked
> slot, not filled from memory.)

## Reproduce

```
python tools/capture.py https://2captcha.com/demo/cloudflare-turnstile
```

Dynamic capture of steps 1-3 (the bundle + orchestration calls only fire at runtime) needs a real
browser; drive it with Playwright and log requests to `challenges.cloudflare.com`.
