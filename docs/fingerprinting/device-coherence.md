# Device coherence: hardwareConcurrency, deviceMemory, UA-CH vs UA vs platform

The device-coherence field is not about any single high-entropy value. It's about whether
the values a browser reports *agree with each other* and with the HTTP headers. Each
individual signal here is deliberately low-entropy and easy to spoof; the scoring signal is
the cross-value contradiction that spoofing introduces. Claims are tagged **[confirmed by
source]** (fetched citation), **[observed]** (our own capture), **(inferred)** (reasoning).

## The values, and why each is coarse by design

| Signal | API | Granularity | Coherence role |
|---|---|---|---|
| logical CPUs | `navigator.hardwareConcurrency` | integer, 1..N, may be clamped | vs deviceMemory, vs platform class |
| RAM bucket | `navigator.deviceMemory` | power-of-2 GiB, clamped | vs CPU count, vs platform class |
| platform / brands / mobile | `navigator.userAgentData` (low-entropy) | strings + bool | vs UA string, vs `navigator.platform` |
| arch / model / platformVersion | `getHighEntropyValues()` (gated) | strings | vs UA, vs maxTouchPoints |
| touch points | `navigator.maxTouchPoints` | integer | vs `mobile`, vs platform |

`navigator.hardwareConcurrency` returns "the number of logical processors available to run
threads," between 1 and N, and the UA "may report a lower number... to reduce fingerprinting"
— MDN says explicitly "don't treat this as an absolute measurement of the number of cores."
**[confirmed by source: https://developer.mozilla.org/en-US/docs/Web/API/Navigator/hardwareConcurrency]**
That clamping matters here: a value is plausible only inside a range, so a *fixed, unusual*
value (e.g. `1`, or an odd non-power-of-two like `7`) is itself a weak tell (inferred).

`navigator.deviceMemory` is rounded to the nearest power of 2 then divided by 1024, and
clamped within implementation-defined bounds — "a browser that doesn't report below `2` or
above `32` returns one of: `2`, `4`, `8`, `16`, or `32`." It is secure-context only (HTTPS).
**[confirmed by source: https://developer.mozilla.org/en-US/docs/Web/API/Navigator/deviceMemory]**
So the field can only ever be one of ~5 buckets — near-zero identifying entropy on its own,
which is exactly why it functions as a *consistency* check, not an identifier.

## UA-CH vs legacy UA vs navigator.platform

The User-Agent Client Hints API gives a second, structured source for the same platform facts
the legacy UA string encodes. Low-entropy hints — `brands`, `mobile`, `platform` — are always
available via `navigator.userAgentData`; high-entropy ones — `architecture`, `model`,
`platformVersion`, `fullVersionList` — require `getHighEntropyValues()` and can be gated by
Permissions-Policy, returning only the low-entropy set when denied.
**[confirmed by source: https://developer.mozilla.org/en-US/docs/Web/API/User-Agent_Client_Hints_API]**

That redundancy is the trap for spoofers. A profile now has to keep **three** platform
sources mutually consistent:

- the legacy `User-Agent` request header (also parsed server-side),
- `navigator.userAgentData.platform` / `.mobile` / `.brands`,
- `navigator.platform` (legacy JS).

A UA claiming Windows Chrome while `userAgentData.platform` says `"Linux"`, or `mobile: true`
paired with `maxTouchPoints: 0`, is the contradiction class the lie-detection layer keys on.
CreepJS formalizes exactly this: "Detect and ignore JavaScript tampering (prototype lies),"
"Fingerprint lie patterns," and "Use large-scale validation and collect inconsistencies."
**[confirmed by source: https://github.com/abrahamjuliot/creepjs]** (The specific
CPU↔RAM↔platform triangulation is inferred — CreepJS confirms the *category*, not this exact
tuple.)

## Where it's read, and the anti-hook gate around it

These are cheap `navigator.*` property reads — they live comfortably in the loader layer, not
in the heavier canvas/WebGL/audio runtime payload **[observed]** (those weren't in the 84KB
loader bundle our test-sitekey capture served). But reading a spoofed value is only useful if
the read can't be silently intercepted, which is why the loader pairs collection with
hook-detection. From the captured bundle **[observed]**:

```js
function ma(e){return Function.toString.call(e).indexOf("[native code]")!==-1}
```

Any accessor or method used to fake `hardwareConcurrency`/`deviceMemory`/`platform` — a
redefined getter, a Proxy trap — fails this native-code check: a genuine built-in stringifies
to `function ... { [native code] }`, while a JS replacement returns "the source text segment
which was used to define the function."
**[confirmed by source: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Function/toString]**
The bundle also captures a stack on probed calls:

```js
function ji(e,t){try{var r=new Error().stack; ... [e, delta, r, ...]}
```

so a wrapper sitting in the call chain shows up as an extra frame (inferred from the `stack`
read). Net effect: the spoof used to make the values *coherent* is itself the tell that makes
them *incoherent* with a clean native environment.

## Practical scoring model (inferred)

The individual fields feed Cloudflare's bot-management score (1–99) derived from "request
features (headers, session characteristics, and browser signals)."
**[confirmed by source: https://developers.cloudflare.com/bots/concepts/bot-score/]** For
device-coherence specifically the useful mental model is: entropy ≈ 0 per field, penalty is
applied for *disagreement* across fields and against the JA3/JA4 + UA header set. Matching a
real device profile end-to-end (CPU, RAM bucket, UA-CH triple, touch points, and the TLS/UA
headers) is far harder than setting any one value.

---

*Scope: this maps the device-coherence fingerprint surface from fetched specs and one loader
capture; it is not a payload schema, a coherence-scoring formula, or a token-forgery method —
tokens are single-use and server-validated.*
