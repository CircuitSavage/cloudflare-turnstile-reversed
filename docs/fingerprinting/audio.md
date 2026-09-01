# Turnstile Fingerprinting Surface: `audio`

Analysis of the Web Audio fingerprinting vector in Cloudflare Turnstile's runtime
challenge payload. This documents the *surface* — what the collector reads and why
it varies across machines — not token forgery (Turnstile tokens are single-use and
server-validated).

## Where it lives in the flow

The 84KB versioned loader bundle (`/turnstile/v0/b/<hash>/api.js`) does **not**
contain audio, canvas, or WebGL probing. That bundle carries only the environment
gates: native-function hook detection (`Function.toString.call(e).indexOf("[native
code]")`), the trusted-interaction listener (`s.isTrusted&&...`), and stack/timing
telemetry (`new Error().stack`) [observed]. The audio probe is served later, inside
the `challenge-platform` runtime payload requested at
`/cdn-cgi/challenge-platform/h/b/turnstile/f/av0/rch/<seg>/<sitekey>` [observed]. A
test sitekey (`3x000...`) does not serve the full runtime, so the exact minified
audio routine was not captured here — the mechanics below are reconstructed from the
Web Audio primitives it must use (inferred), with behavior confirmed against the
public fingerprinting literature.

## The primitive: OfflineAudioContext render

The standard audio fingerprint builds a short signal-processing graph and renders it
to a buffer *without touching the speakers*. `OfflineAudioContext` "does not render
the audio to the device hardware. Instead, it generates the audio as fast as
possible and saves it into an `AudioBuffer`" [confirmed by source —
https://fingerprint.com/blog/audio-fingerprinting/]. Rendering is asynchronous:
`startRendering()` "returns a Promise that resolves with the rendered `AudioBuffer`"
and generates audio "as fast as possible rather than real-time playback" [confirmed
by source — https://developer.mozilla.org/en-US/docs/Web/API/OfflineAudioContext].

Constructor shape [confirmed by source — MDN OfflineAudioContext]:

```javascript
const ctx = new OfflineAudioContext(numberOfChannels, length, sampleRate);
// canonical fingerprint variant:
const ctx = new OfflineAudioContext(1, 44100, 44100); // 1ch, 1s @ 44.1kHz
```

The graph is oscillator -> compressor -> destination:

```javascript
const osc  = ctx.createOscillator();
osc.type = "triangle";                 // deterministic waveform
osc.frequency.value = 1000;            // 1 kHz test tone
const comp = ctx.createDynamicsCompressor();
comp.threshold.value = -50;  comp.knee.value = 40;
comp.ratio.value = 12;       comp.attack.value = 0; comp.release.value = 0.2;
osc.connect(comp); comp.connect(ctx.destination); osc.start(0);
ctx.startRendering().then(buf => hash(buf.getChannelData(0)));
```

The oscillator emits a mathematical waveform, not a file — Web Audio defaults are
`type: "sine"`, `frequency: 440 Hz` [confirmed by source —
https://developer.mozilla.org/en-US/docs/Web/API/OscillatorNode], so the
fingerprint script overrides both. The specific parameter set — triangle wave at
1000 Hz through a compressor with `threshold -50, knee 40, ratio 12, release 0.2` —
matches the documented reference implementation [confirmed by source —
fingerprint.com].

## Why the DynamicsCompressor matters

The compressor is the variance amplifier. Its params are `AudioParam`s [confirmed by
source — https://developer.mozilla.org/en-US/docs/Web/API/DynamicsCompressorNode]:

| Param | Units | Role |
|-----------|---------|------------------------------------------|
| threshold | dB | level above which compression starts |
| knee | dB | smooth-transition range above threshold |
| ratio | dB:dB | input change per 1 dB output change |
| attack | seconds | time to reduce gain by 10 dB |
| release | seconds | time to raise gain by 10 dB |

The compressor "transforms the signal ... introducing variability across platforms"
[confirmed by source — fingerprint.com]. Its curve is computed in floating-point,
and that is where machines diverge.

## Hashing and per-platform float variance

`getChannelData(0)` yields the Float32 PCM samples; the classic reduction sums their
absolute values into one number — "samples is an array of floating-point values that
represents the uncompressed sound," producing e.g. `101.45647543197447` on Chrome
macOS [confirmed by source — fingerprint.com]. Collectors also slice a sub-range
(often samples 4500–5000) and sum, or take a plain hash of the buffer.

The value is stable per browser+OS+CPU but differs across them because "audio signal
processing uses floating point arithmetic, which ... contributes to discrepancies in
calculations." Blink, WebKit and Gecko each modified originally-shared Google code,
and "Chrome uses a separate fast Fourier transform implementation on macOS ... and
other vector operation implementations on different CPU architectures" [confirmed by
source — fingerprint.com]. So the fingerprint effectively encodes engine + OS math
library + CPU vector path.

Properties relevant to a detector:

- **Stable / deterministic**: identical across sessions and "remains the same in
  incognito mode" [confirmed by source — fingerprint.com]. A value that *drifts*
  between reads on one machine is itself suspicious.
- **Low standalone entropy**: it "contributes only slightly to uniqueness" — a
  supporting signal, cross-checked against UA/platform claims [confirmed by source —
  fingerprint.com].
- **Cheap**: renders in ~5–50 ms off the main thread [confirmed by source —
  fingerprint.com].

## Spoofing tells (inferred)

A forged environment fails when the audio hash is internally inconsistent: a
Chrome/Win32 UA that returns the Firefox/Linux audio constant, a value not matching
*any* known engine, `getChannelData` patched to return constant/zeroed buffers, or
`OfflineAudioContext`/`createDynamicsCompressor` whose `toString` is non-native
(caught by the same `[native code]` gate the loader already runs [observed]). The
render is also timed — a value that arrives implausibly fast or slow, or from a
hooked async path, is a signal.

---
*Scope: fingerprinting-surface analysis of a runtime-payload vector reconstructed
from Web Audio primitives; the exact minified Turnstile audio routine was not in the
captured test-sitekey payload.*
