#!/usr/bin/env python3
"""
browser_downloader.py — Download pages/API responses that block plain curl
(Cloudflare "Just a moment…" challenges), using a real Chrome via Playwright.

Works best on YOUR machine (residential IP): Cloudflare challenges auto-solve in
a real browser. From this sandbox it currently passes for HathiTrust but NOT for
www.loc.gov (datacenter-IP block).

Usage:
  python3 browser_downloader.py --urls "https://...a.json https://...b.json"
  python3 browser_downloader.py --file urls.txt --out ../data/browser_downloads
  python3 browser_downloader.py --url "https://catalog.hathitrust.org/api/volumes/brief/isbn/9780141036144.json"

Behavior per URL:
  - opens in headless Chrome (channel=chrome), waits up to --challenge-wait s
    for the CF challenge to auto-solve, then saves the page/response body to
    --out/<sanitized-name>.
  - prints [OK] or [FAILED: Just a moment] so you can see which hosts pass.
"""

import argparse
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def sanitize(url):
    name = re.sub(r"^https?://", "", url)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name[:120] + ".txt"


def fetch(page, url, challenge_wait):
    resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
    status = resp.status if resp else None
    # let the Cloudflare challenge auto-solve if present
    deadline = time.time() + challenge_wait
    while time.time() < deadline:
        body = page.inner_text("body") if page.query_selector("body") else ""
        if "Just a moment" not in body[:4000] and len(body) > 0:
            return status, body
        page.wait_for_timeout(2000)
    return status, page.inner_text("body") if page.query_selector("body") else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="single URL")
    ap.add_argument("--urls", nargs="*", default=[], help="space-separated URLs")
    ap.add_argument("--file", help="file with one URL per line")
    ap.add_argument("--out", default="data/browser_downloads")
    ap.add_argument("--challenge-wait", type=int, default=20, help="seconds to wait for CF challenge")
    args = ap.parse_args()

    urls = list(args.urls)
    if args.url:
        urls.append(args.url)
    if args.file:
        urls += [l.strip() for l in Path(args.file).read_text().splitlines() if l.strip()]
    if not urls:
        ap.error("provide --url, --urls, or --file")
    urls = list(dict.fromkeys(urls))  # dedupe, keep order

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome", headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        for url in urls:
            try:
                status, body = fetch(page, url, args.challenge_wait)
                if body and "Just a moment" not in body[:4000]:
                    out = out_dir / sanitize(url)
                    out.write_text(body, encoding="utf-8")
                    print(f"[OK]      {status} {url} -> {out} ({len(body)} bytes)")
                else:
                    print(f"[FAILED]  {status} {url}  (challenge not solved here — try on your machine)")
            except Exception as e:
                print(f"[ERROR]   {url} :: {type(e).__name__}: {str(e)[:120]}")
            time.sleep(1.5)
        browser.close()


if __name__ == "__main__":
    main()
