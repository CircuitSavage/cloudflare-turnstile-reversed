# Turnstile Fingerprinting Surface: TLS (JA3/JA4) + HTTP/2

Scope: the *server-side transport layer* Cloudflare pairs with Turnstile's JS. Nothing in the 84KB loader bundle computes these — they are derived from the raw ClientHello and HTTP/2 preface at Cloudflare's edge, out of the page's reach. This documents how the transport handshake becomes a stable identity that must *agree* with the browser the JS claims to be.

## Why the transport layer matters to Turnstile

The Turnstile challenge flow rides ordinary HTTPS: `challenges.cloudflare.com/turnstile/v0/api.js` (302) -> `/turnstile/v0/b/<hash>/api.js` -> `POST /cdn-cgi/challenge-platform/.../<sitekey>` [observed]. Every one of those requests carries a TLS ClientHello and an HTTP/2 preface that Cloudflare's edge fingerprints independently of any JavaScript. Cloudflare identifies "TLS clients based on how they initiate connections," and states the fingerprint "acts as a stable identifier across different destination IPs, ports, and certificates" [confirmed by source — https://developers.cloudflare.com/bots/concepts/ja3-ja4-fingerprint/]. The consequence for solvers: the transport identity and the JS-reported navigator identity must match. A ClientHello that hashes to Python/OpenSSL while the JS payload reports Chrome is a cross-layer contradiction the edge can flag before the challenge JS even runs.

## JA3 — the classic ClientHello hash

JA3 concatenates five ClientHello fields, comma-joined, and MD5s the result [confirmed by source — https://lwthiker.com/networks/2022/06/17/tls-fingerprinting.html]:

```
SSLVersion,Cipher,SSLExtension,EllipticCurve,EllipticCurvePointFormat
```

Example Chrome string and its shape [confirmed by source, lwthiker]:

```
771,39578-4865-4866-4867-49195-...-53,23130-0-23-65281-10-11-35-...-21,39578-29-23-24,0
```

The `39578` leading a field is a GREASE value; `771` is TLS 1.2 (0x0303). JA3's known weakness: it "does not take into account all different parameters in the Client Hello," so distinct ClientHellos can collide [confirmed by source, lwthiker].

## JA4 — sorted, structured, harder to spoof loosely

Cloudflare's stated upgrade: "JA4 improves on JA3 by sorting ClientHello extensions, which reduces the number of unique fingerprints for modern browsers and makes grouping easier" [confirmed by source — Cloudflare]. The FoxIO construction is `(proto)(ver)(SNI)(cipher_count)(ext_count)(ALPN)_(cipher_hash)_(ext_hash)`, e.g. `t13d1516h2_8daaf6152771_e5627efa2ab1` [confirmed by source — https://github.com/FoxIO-LLC/ja4/blob/main/technical_details/JA4.md]:

| Segment | Meaning |
|---|---|
| `t` | TLS-over-TCP (`q`=QUIC, `d`=DTLS) |
| `13` | TLS 1.3 |
| `d` | SNI present (domain); `i` = IP/no-SNI |
| `15` | cipher count (zero-padded, GREASE excluded) |
| `16` | extension count (GREASE excluded) |
| `h2` | first+last char of first ALPN value |
| `_8daaf6152771` | 12-char SHA256 of *sorted* cipher hex |
| `_e5627efa2ab1` | 12-char SHA256 of *sorted* extensions (excl. SNI/ALPN) + signature algorithms |

Because ciphers and extensions are sorted before hashing, JA4 is stable against benign reordering but still binds you to the *set* of ciphers, extensions, and sig-algs a given stack emits. GREASE is stripped everywhere ("the program needs to ignore GREASE values anywhere it sees them") while SCSV and other reserved values are kept [confirmed by source — FoxIO].

## TLS-library divergence — the real tell

The fingerprint is really a fingerprint of the *TLS library*, and each browser uses a different one [confirmed by source, lwthiker]:

| Client | Library | Divergent traits |
|---|---|---|
| Chrome | BoringSSL | ~16 cipher suites; ALPS extension; Brotli cert compression; GREASE |
| Firefox | NSS | 11 sig-algs; no ALPS; no cert compression |
| Safari | Secure Transport | Zlib cert compression |
| Python `requests` | OpenSSL | ~43 cipher suites; 20 sig-algs; no GREASE |

So Python offering 43 ciphers vs Chrome's 16 [confirmed by source, lwthiker] is an instant mismatch against a `User-Agent: Chrome`. Cloudflare's own signal set even tracks an `h2h3_ratio` metric [confirmed by source — Cloudflare], implying they cross-check HTTP/2-vs-HTTP/3 behavior per client too.

## HTTP/2 fingerprint (Akamai format)

After TLS, the HTTP/2 preface is fingerprinted as four pipe-separated parts [confirmed by source — https://www.trickster.dev/post/understanding-http2-fingerprinting/]:

```
S[;] | WU | P[,]# | PS[,]
```

- **S** — SETTINGS frame values, in order: `HEADER_TABLE_SIZE`, `ENABLE_PUSH` (0 in modern Chrome), `MAX_CONCURRENT_STREAMS`, `INITIAL_WINDOW_SIZE`, `MAX_FRAME_SIZE`, `MAX_HEADER_LIST_SIZE` [confirmed by source, trickster].
- **WU** — the WINDOW_UPDATE increment, or `0` if none [confirmed by source, trickster].
- **P** — PRIORITY frames as `StreamID:Exclusivity:Dep:Weight` [confirmed by source, trickster].
- **PS** — pseudo-header order of `:method :authority :scheme :path`, abbreviated `m,a,s,p`, which "varies between browsers like Firefox and Chrome" [confirmed by source, trickster].

Pseudo-header order is the cheapest tell: browsers emit a fixed order that most HTTP libraries and language HTTP/2 stacks reorder or omit. A generic `httpx`/Go/Node client rarely reproduces Chrome's exact SETTINGS *values* and header ordering simultaneously.

## Bearing on Turnstile

To present as a real browser to Turnstile you need all three layers coherent: JA4 matching the claimed browser's TLS library, the HTTP/2 SETTINGS+priority+pseudo-header order matching the same browser build, and the JS-runtime signals (the loader's `isTrusted` gates and `ma()` native-code check [observed]) matching that *same* browser. The transport layer is the one a page's JavaScript cannot patch — it is set by whatever socket stack actually dialed the connection — so mismatches here are high-confidence bot signals. Note the exact ciphers/extensions/SETTINGS values are version-specific and rotate with browser releases; treat the tables above as shape, not fixed constants (inferred from the library-divergence and version-churn evidence above).

*Scope caveat: analysis of the fingerprinting surface only — these fingerprints are edge-computed transport metadata, not forgeable challenge tokens (tokens are single-use and server-validated).*
