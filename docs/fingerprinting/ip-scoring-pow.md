# IP reputation, the 1–99 bot score, and proof-of-work

Field specialist note for `ip-scoring-pow`: how Cloudflare turns transport reputation
(residential vs datacenter, ASN) plus in-browser proof-of-work/proof-of-space into the single
1–99 bot score that gates a Turnstile challenge. Tags: **[confirmed by source]** (fetched
citation), **[observed]** (our own live capture), **(inferred)** (reasoning, unsourced).

This is analysis of the scoring *surface*, not token forgery — Turnstile tokens are single-use and
server-validated at `siteverify`, so nothing here bypasses verification.

## 1. The bot score is one number, three engines

Cloudflare's bot-management score runs 1–99: "a score of 1 means Cloudflare is quite certain the
request was automated, while a score of 99 means Cloudflare is quite certain the request came from a
human." **[confirmed: https://developers.cloudflare.com/bots/concepts/bot-score/]** Three engines
feed it:

| Engine | Role | Score behavior | Source |
|---|---|---|---|
| Machine Learning (ML) | primary; billions of req/day, supervised | "most scores between 2 and 99" from headers, session characteristics, browser signals | [confirmed](https://developers.cloudflare.com/bots/concepts/bot-score/) |
| Heuristics | deterministic pattern match | "gives automated requests a score of 1 for high-confidence, deterministic detections"; sometimes 29 while under assessment | [confirmed](https://developers.cloudflare.com/bots/concepts/bot-score/) |
| JS Detections (JSD) | lightweight JS injection | "Catches headless browsers … and other automation tools" — blocks, challenges, or passes | [confirmed](https://developers.cloudflare.com/bots/concepts/bot-score/) |

Score groupings: **Automated** = 1, **Likely automated** = 2–29, **Likely human** = 30–99, **Not
computed** = 0. **[confirmed: same source]** Practical read: a heuristic hit floors you at 1 with no
appeal; the ML engine is where residential-IP + coherent-fingerprint traffic earns its way into the
30–99 band.

## 2. IP reputation and ASN

The bot-score page describes ML inputs as "headers, session characteristics, and browser signals"
and does **not** itself name IP class or ASN as scoring factors. **[confirmed: same source]** The
IP-reputation weighting is documented externally: Cloudflare buckets IPs by origin —

> "Residential: Assigned by ISPs to home networks. These have high trust. Mobile: Assigned by
> cellular towers. Also have high trust and rotate often. Datacenter: IPs from AWS or Google Cloud.
> These have low trust and are often blocked."
> **[confirmed: https://scrapfly.io/blog/posts/how-to-bypass-cloudflare-anti-scraping]**

Same source notes IPv6 reputation is tracked less thoroughly than IPv4. **[confirmed: same source]**
The specific claim that scoring keys on **ASN** (autonomous system number, i.e. which network owns
the block) rather than just per-IP history is **(inferred)** — none of the sources I fetched name ASN
as a Turnstile/bot-score input. Datacenter ASNs being low-trust is the mechanism behind the recurring
"passes on my desktop, fails headless on a cloud IP" outcome: the JS harness can be perfect and the
transport still floors the score.

## 3. Proof-of-work / proof-of-space

Turnstile's JS side is a signal-collection harness, not a visible puzzle. Cloudflare: Turnstile runs
"a series of small non-interactive JavaScript challenges to gather signals about the visitor or
browser environment," including "proof-of-work (computational puzzles), proof-of-space, probing for
web APIs, and various other challenges for detecting browser-quirks and human behavior."
**[confirmed: https://developers.cloudflare.com/turnstile/]** The GA blog frames the same mechanism:
bots are stopped "by running a series of in-browser tests, checking browser characteristics, native
browser APIs, and asking the browser to pass lightweight tests (ex: proof-of-work tests,
proof-of-space tests)," and "the actual act of checking a box isn't important, it's the background
data we're analyzing while the box is checked that matters."
**[confirmed: https://blog.cloudflare.com/turnstile-ga/]**

What PoW/PoS buy the scorer: a browser that completes a compute/memory-bound challenge and returns a
verifiable result proves it ran a real JS engine at real cost, raising the price of high-volume
automation. The exact algorithm, difficulty, and payload schema are in the runtime challenge-platform
bundle, not the loader — **not reproduced here** (gated, byte-level).

## 4. Where the loader corroborates the score inputs

Our capture of the ~84KB versioned loader (`/turnstile/v0/b/<hash>/api.js`) shows the client-side
tells the JSD/ML engines consume, as plaintext host-API names the minifier can't rename **[observed]**:

```js
// trusted-input gate — synthetic dispatch scores as automation
var c = function (s) { s.isTrusted && (U.add(i), t(i)) };
window.addEventListener("keydown", c, true);
window.addEventListener("mousemove", c, true);
window.addEventListener("touchstart", c, true);

// hook / tamper detection — spoofing a getter becomes its own tell
function ma(e){ return Function.toString.call(e).indexOf("[native code]") !== -1 }

// stack + timing telemetry — detects a Proxy/wrapper in the call chain
function ji(e,t){ try { var r = new Error().stack; /* … [e, delta, r, …] */ } }
```

`isTrusted` is `true` only for user-agent-generated events, `false` for `dispatchEvent()`
**[confirmed: https://developer.mozilla.org/en-US/docs/Web/API/Event/isTrusted]**, so scripted input
feeds the "likely automated" band. The `[native code]` check means spoofing `navigator.webdriver`
via a redefined getter is itself detectable — the hook's `.toString()` returns JS source, not
`[native code]`. **[confirmed: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Function/toString]**
Canvas/WebGL/audio probes were **not** in this loader **[observed]** — they load in the runtime
payload a `3x000…` test sitekey doesn't fully serve.

## Scope

Sourced map of the scoring surface (IP reputation, the three bot-score engines, PoW/PoS) — not a
byte-level deobfuscation, payload schema, or any token-forgery method; tokens stay single-use and
server-validated.
