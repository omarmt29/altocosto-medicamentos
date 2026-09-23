#!/usr/bin/env python3
"""Probe Biggie PY + PuntoFarma catalog endpoints (local workspace script)."""
from __future__ import annotations

import re
import urllib3
import requests

urllib3.disable_warnings()
s = requests.Session()
s.verify = False
s.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/json,*/*",
    }
)


def main() -> None:
    print("=== BIGGIE HOME ===")
    r = s.get("https://biggie.com.py/", timeout=25)
    html = r.text or ""
    print("status", r.status_code, "len", len(html))
    urls = set(re.findall(r"https?://[^\"'\s<>]+", html))
    interesting = [
        u
        for u in urls
        if any(k in u.lower() for k in ("api", "search", "product", "algolia", "vtex", "graphql", "catalog"))
    ]
    for u in sorted(interesting)[:40]:
        print(" ", u[:130])

    print("\n=== BIGGIE endpoints ===")
    for u in [
        "https://biggie.com.py/api/search?q=letrozol",
        "https://biggie.com.py/api/products?search=letrozol",
        "https://biggie.com.py/buscar?q=letrozol",
        "https://biggie.com.py/search?q=letrozol",
        "https://api.biggie.com.py/products?search=letrozol",
    ]:
        try:
            rr = s.get(u, timeout=15)
            print(rr.status_code, u.split(".py")[-1][:55], (rr.text or "")[:90].replace("\n", " "))
        except Exception as e:
            print("ERR", type(e).__name__, u)

    print("\n=== PuntoFarma ===")
    for path in [
        "/catalogsearch/result/?q=letrozol",
        "/rest/V1/products?searchCriteria[pageSize]=2",
        "/buscar?q=letrozol",
        "/search?q=letrozol",
    ]:
        try:
            rr = s.get("https://www.puntofarma.com.py" + path, timeout=15)
            print(path[:45], rr.status_code, (rr.text or "")[:70].replace("\n", " "))
        except Exception as e:
            print(path, type(e).__name__)
    print("DONE_BIGGIE")


if __name__ == "__main__":
    main()
