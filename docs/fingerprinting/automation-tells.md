# Automation tells

The category of fingerprinting signals that answer a single question: *is this browser being
driven by WebDriver / CDP / a headless build rather than a human at a real Chrome?* These are
cheap boolean-ish checks — no canvas, no audio, just reading properties the automation stack
leaks. Claims are tagged **[confirmed by source]** (a fetched citation supports it),
**[observed]** (seen in our own live capture of the Turnstile loader bundle), **(inferred)**.

## The signals

| Tell | What's read | Default automation value | Trivial to spoof? |
|---|---|---|---|
| `navigator.webdriver` | boolean flag | `true` under automation | yes (defineProperty) |
| `window.chrome` / `chrome.runtime` | object presence | missing/incomplete in headless | partly |
| permissions inconsistency | Notification vs Permissions API | contradictory states | yes |
| `navigator.plugins` / `languages` | array length | length `0` in old headless | yes |
| `cdc_*` / CDP artifacts | injected globals, DevTools traffic | ChromeDriver leaves them | needs binary patch |
| native-function tampering | `Function.prototype.toString` | spoofers replace natives | this is the meta-check |

### navigator.webdriver

The one signal browsers hand you for free. It "defines a standard way for co-operating user
agents to inform the document that it is controlled by WebDriver, for example, so that alternate
code paths can be triggered during automation." **[confirmed by source:
https://developer.mozilla.org/en-US/docs/Web/API/Navigator/webdriver]** In Chrome it is `true`
"when the `--enable-automation` or `--headless` flag is used, or the `--remote-debugging-port`
flag specifying port 0 is used." **[confirmed by source: same]** It's read-only per spec but the
value lives on the prototype, so `Object.defineProperty(navigator, 'webdriver', {get:()=>false})`
erases it — which is exactly why a bare check is worthless on its own and why the *meta*-check
below matters more.

### window.chrome, permissions, plugins, languages

Intoli's canonical headless-detection writeup enumerates the classic battery:
`if (!window.chrome || !window.chrome.runtime)` (real Chrome exposes the runtime API);
`if (Notification.permission === 'denied' && permissionStatus.state === 'prompt')` (a
contradiction headless produces); `if (navigator.plugins.length === 0)`; and
`if (!navigator.languages || navigator.languages.length === 0)`. **[confirmed by source:
https://intoli.com/blog/not-possible-to-block-chrome-headless/]** The same article's thesis is the
important part for us — every one of these "is trivial for determined automation tools using
`Object.defineProperty()` and Puppeteer's `evaluateOnNewDocument()`." **[confirmed by source:
same]** So the modern anti-bot posture is not to trust any single reading but to check whether the
*reading mechanism itself* has been tampered with.

### cdc_ and CDP artifacts

ChromeDriver historically injected globals matching `cdc_[a-z0-9]+_` into the document, and the
Chrome DevTools Protocol channel (which Selenium/Puppeteer ride) leaves observable traffic.
`undetected-chromedriver` exists precisely because these are hard to hide from JS alone: its
approach is, "instead of removing and renaming variables, we just keep them, but prevent them from
being injected in the first place," and it patches the ChromeDriver binary before launch, claiming
it "Passes ALL bot mitigation systems (like Distil / Imperva / DataDome / CloudFlare IUAM)."
**[confirmed by source: https://github.com/ultrafunkamsterdam/undetected-chromedriver]** That a
binary patch is required — not a JS override — tells you `cdc_`/CDP is a higher-value tell than
`navigator.webdriver`. (inferred) CDP-attached tabs also perturb timing and event delivery, which
feeds the loader's `isTrusted` + stack-timing telemetry rather than a named property read.

## The meta-check: `ma()` from the loader bundle

The most interesting automation tell in our capture isn't a property — it's the function that
catches you *spoofing* the properties. From the ~84KB versioned loader **[observed]**:

```js
function ma(e){return Function.toString.call(e).indexOf("[native code]")!==-1}
```

This calls `Function.prototype.toString` on an arbitrary function `e` and checks for the
`[native code]` marker. Per spec, "if the `toString()` method is called on built-in function
objects ... `toString()` returns a native function string which looks like
`function someName() { [native code] }`," whereas "for user-defined `Function` objects, the
`toString` method returns a string containing the source text segment which was used to define the
function." **[confirmed by source:
https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Function/toString]**

So `ma(navigator.__lookupGetter__('webdriver'))` — or any API a spoofer replaced — returns `false`
when the getter is a JS shim, because a hand-written override serializes to its own source, not to
`[native code]`. This is the counter to the "trivial to spoof" problem: you can lie about
`webdriver`, `plugins`, `languages`, `chrome`, but the naive lie is itself a JS function, and its
`toString()` betrays it. CreepJS's stated first objective is exactly this class of check — "Detect
and ignore JavaScript tampering (prototype lies)." **[confirmed by source:
https://github.com/abrahamjuliot/creepjs]**

The arms race then goes one level deeper: to beat `ma()` you must also patch
`Function.prototype.toString` to lie about your shims — but that patched `toString` is *itself* a
non-native function, so `ma(Function.prototype.toString)` catches the tamperer. Robustly defeating
this requires a native-level (`Object.defineProperty` on a spoofed `toString` that recursively
whitelists, or a CDP/`Runtime.evaluate` binary approach) fix, not page-context JS. (inferred, but
directly implied by the spec + `ma()` semantics)

---

*Scope: analysis of the fingerprinting surface (which signals are read and how tampering is
caught), not token forgery — Turnstile tokens are single-use and server-validated.*
