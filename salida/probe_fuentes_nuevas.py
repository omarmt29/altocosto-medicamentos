#!/usr/bin/env python3
"""Probe one-off pharmacy candidates for VTEX/Woo/Shopify APIs."""

from __future__ import annotations

import urllib3

urllib3.disable_warnings()
import requests

UA = {
    "User-Agent": "Mozilla/5.0 Chrome/124.0.0.0",
    "Accept": "application/json,text/html,*/*",
}

SITES = [
    ("CL", "Cruz Verde", "https://www.cruzverde.cl"),
    ("CL", "Dr Simi", "https://www.drsimi.cl"),
    ("CL", "Knop", "https://www.farmaciasknop.cl"),
    ("CL", "Profar", "https://www.profar.cl"),
    ("AR", "Dr Ahorro", "https://www.drahorro.com.ar"),
    ("AR", "Openfarma", "https://www.openfarma.com.ar"),
    ("AR", "Farmaloop", "https://www.farmaloop.com.ar"),
    ("PE", "Mifarma", "https://www.mifarma.com.pe"),
    ("PE", "Farmacia Universal", "https://www.farmaciauniversal.com"),
    ("VE", "Farmatodo", "https://www.farmatodo.com.ve"),
    ("VE", "Locatel", "https://www.locatel.com.ve"),
    ("BO", "Farmacorp", "https://www.farmacorp.com"),
    ("BO", "Hipermaxi", "https://www.hipermaxi.com"),
    ("PY", "Catedral", "https://www.farmaciacatedral.com.py"),
    ("PY", "Catedral alt", "https://www.catedral.com.py"),
    ("PY", "FarmaPatronal", "https://www.farmapatronal.com.py"),
    ("MX", "Guadalajara", "https://www.farmaciasguadalajara.com"),
    ("MX", "Benavides", "https://www.benavides.com.mx"),
    ("EC", "Medicity", "https://www.medicity.com.ec"),
    ("PA", "Metro Farma", "https://www.metrofarma.com.pa"),
    ("PA", "Revilla", "https://www.farmaciasrevilla.com"),
    ("SV", "San Francisco", "https://www.farmaciasanfrancisco.com.sv"),
    ("TT", "SuperPharm", "https://www.superpharmtt.com"),
    ("UY", "Farmaciasur", "https://www.farmaciasur.com.uy"),
    ("RD", "Jones", "https://www.farmaciasjones.com"),
    ("RD", "San Rafael", "https://www.farmaciassanrafael.com.do"),
    ("CO", "Pasteur", "https://www.drogueriaspasteur.com.co"),
    ("CR", "La Bomba", "https://www.farmacialabomba.com"),
    ("GT", "Gallito", "https://www.farmaciasgallito.com"),
    ("HN", "Farmacias del Pueblo", "https://www.farmaciasdelpueblo.hn"),
    ("NI", "Prevenir", "https://www.farmaciaprevenir.com"),
    ("BR", "Pague Menos check", "https://www.paguemenos.com.br"),
    ("GY", "Medicine Chest", "https://www.medicinechestgy.com"),
]


def probe(base: str) -> str:
    s = requests.Session()
    s.headers.update(UA)
    s.verify = False
    try:
        r = s.get(base, timeout=18, allow_redirects=True)
    except Exception as e:
        return f"ERR|{e}"
    html = r.text[:70000].lower()
    flags = []
    if "vtex" in html:
        flags.append("vtex")
    if "woocommerce" in html or "wp-content" in html:
        flags.append("woo")
    if "cdn.shopify.com" in html:
        flags.append("shopify")
    if "magento" in html or "mage/" in html:
        flags.append("magento")
    apis = []
    for kind, url in [
        ("vtex", f"{base.rstrip('/')}/api/catalog_system/pub/products/search?ft=adalimumab&_from=0&_to=1"),
        ("woo", f"{base.rstrip('/')}/wp-json/wc/store/v1/products?search=adalimumab&per_page=1"),
        ("shopify", f"{base.rstrip('/')}/search/suggest.json?q=adalimumab&resources[type]=product"),
    ]:
        try:
            rr = s.get(url, timeout=12)
            body = rr.text[:90].replace("\n", " ")
            if rr.status_code == 200 and body.strip()[:1] in "[{":
                apis.append(f"{kind}:OK:{body[:50]}")
            else:
                apis.append(f"{kind}:{rr.status_code}")
        except Exception:
            apis.append(f"{kind}:ERR")
    return f"{r.status_code}|{r.url}|{','.join(flags)}|{' ; '.join(apis)}"


def main() -> None:
    for pais, nom, base in SITES:
        print(f"{pais}|{nom}|{probe(base)}", flush=True)


if __name__ == "__main__":
    main()
