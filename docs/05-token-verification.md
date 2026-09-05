# Token and server-side verification

What the widget produces and how a server checks it. This is the **documented** side of Turnstile
(the `siteverify` API), included so the picture is complete from challenge to validation. It is not
reverse-engineered, and none of it is a way to forge a token, because validation is server-side and
tokens are single-use.

## The token

The widget writes the token into a hidden input, `cf-turnstile-response` by default, and it is also
handed to your `callback`. Properties that matter in practice:

- **Single-use.** A token validates once. Send it to `siteverify` a second time and you get
  `timeout-or-duplicate`. This is why a solver returns a fresh token per attempt and you submit it
  immediately.
- **Short TTL, ~300 seconds.** After roughly five minutes an unspent token is expired and
  `siteverify` rejects it. The widget's `expired-callback` fires on the client at the same boundary.
- **Bound to the sitekey and hostname.** `siteverify` echoes the `hostname` the token was issued for;
  a mismatch is how server checks catch a token replayed from another origin.
- **Carries `action` and `cData`.** Whatever the page set is returned in the verify response, so the
  server can confirm the token was minted for the flow it expected (for example `action: "login"`).

## siteverify

```
POST https://challenges.cloudflare.com/turnstile/v0/siteverify
Content-Type: application/x-www-form-urlencoded
```

Request fields:

| Field | Required | Notes |
|---|---|---|
| `secret` | yes | The site's secret key (server-side only, never shipped to the browser). |
| `response` | yes | The `cf-turnstile-response` token from the widget. |
| `remoteip` | no | The visitor's IP, if you want Cloudflare to factor it in. |
| `idempotency_key` | no | A UUID you supply so the same token can be re-checked and return the same result instead of `timeout-or-duplicate`. |

Response:

```json
{
  "success": true,
  "challenge_ts": "2026-09-05T12:00:00.000Z",
  "hostname": "example.com",
  "action": "login",
  "cdata": "user-123",
  "error-codes": []
}
```

| Field | Notes |
|---|---|
| `success` | Whether the token is valid and unspent. |
| `challenge_ts` | ISO 8601 timestamp of when the challenge was solved. |
| `hostname` | Hostname the token was issued for. Check this against your own domain. |
| `action` / `cdata` | Echoed back from the widget config. |
| `error-codes` | Populated when `success` is false (see below). |

## Error codes

| Code | Meaning |
|---|---|
| `missing-input-secret` | No `secret` sent. |
| `invalid-input-secret` | `secret` is malformed or wrong. |
| `missing-input-response` | No `response` token sent. |
| `invalid-input-response` | Token is malformed, expired, or already spent. |
| `bad-request` | The request itself is malformed. |
| `timeout-or-duplicate` | Token already validated once, or older than its TTL. |
| `internal-error` | Transient Cloudflare-side failure; safe to retry. |

## Why this bounds what a solver can do

A solver produces a real, single-use `cf-turnstile-response` for a given `sitekey`, and you submit it
inside the TTL. It cannot mint a token that passes `siteverify` for a hostname it was not issued for,
and it cannot reuse one. The token is the deliverable; the verification above is the fence around it.
