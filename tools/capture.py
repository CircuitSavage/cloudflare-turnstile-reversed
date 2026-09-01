#!/usr/bin/env python3
"""Capture Cloudflare Turnstile challenge parameters from a page.

Static mode (stdlib only): pulls the sitekey and widget params out of the HTML.
The observed live request flow is in docs/01-challenge-flow.md. `--solve` routes
the challenge to the Peak API and prints the token.

    python capture.py https://example.com/
    PEAK_API_KEY=pk_... python capture.py https://example.com/ --solve
"""
import argparse
import json
import os
import re
import sys
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# Endpoints observed live (Turnstile v0), see docs/01-challenge-flow.md.
FLOW = [
    "loader    GET  challenges.cloudflare.com/turnstile/v0/api.js?render=explicit   -> 302",
    "bundle    GET  challenges.cloudflare.com/turnstile/v0/b/<hash>/api.js          -> obfuscated challenge JS",
    "orchestr  POST challenges.cloudflare.com/cdn-cgi/challenge-platform/h/b/turnstile/f/av0/rch/<seg>/<sitekey>",
    "token     ->   submitted as the 'cf-turnstile-response' field",
]


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "replace")


def extract(html: str) -> dict:
    def first(*pats):
        for p in pats:
            m = re.search(p, html)
            if m:
                return m.group(1)
        return None

    return {
        "sitekey": first(r'data-sitekey=["\']([^"\']+)',
                         r'sitekey["\']?\s*[:=]\s*["\']([0-9a-zA-Z_-]+)'),
        "cdata": first(r'data-cdata=["\']([^"\']+)',
                       r'cData["\']?\s*[:=]\s*["\']([^"\']+)'),
        "action": first(r'data-action=["\']([^"\']+)',
                        r'\baction["\']?\s*[:=]\s*["\']([^"\']+)'),
        "chlpagedata": first(r'chlPageData["\']?\s*[:=]\s*["\']([^"\']+)'),
        "loads_turnstile": bool(re.search(r'challenges\.cloudflare\.com/turnstile/v0/api\.js', html)),
        "managed_challenge": bool(re.search(r'cf_chl_opt|__cf_chl|window\._cf_chl_opt|Just a moment', html)),
    }


def solve_with_peak(sitekey: str, url: str, proxy: str | None = None) -> dict:
    key = os.environ.get("PEAK_API_KEY")
    if not key:
        sys.exit("Set PEAK_API_KEY to use --solve. Free key at peak.fo.")
    body = {"task_type": "turnstiletask", "sitekey": sitekey, "url": url}
    if proxy:
        body["proxy"] = proxy
    req = urllib.request.Request(
        "https://api.peak.fo/solve",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-API-Key": key, "User-Agent": UA},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


def main() -> None:
    ap = argparse.ArgumentParser(description="Capture Turnstile challenge params from a page.")
    ap.add_argument("url")
    ap.add_argument("--solve", action="store_true", help="solve via Peak (needs PEAK_API_KEY)")
    ap.add_argument("--proxy", help="proxy forwarded to the solver")
    a = ap.parse_args()

    info = extract(fetch(a.url))
    print(json.dumps(info, indent=2))
    print("\nObserved Turnstile flow:")
    for step in FLOW:
        print("  " + step)

    if a.solve:
        if not info["sitekey"]:
            sys.exit("No sitekey found on the page.")
        print("\nPeak solve:", json.dumps(solve_with_peak(info["sitekey"], a.url, a.proxy)))


if __name__ == "__main__":
    main()
