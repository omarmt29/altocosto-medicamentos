"""Cola durable de scrapes por fuente (SQL Server).

La web solo encola; el worker `scrapper/worker_cola.py` ejecuta en otro
contenedor para que un fallo del scraper no tumbe la plataforma.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import text

from db import engine, resumen_config

TABLA = "medicamentos_scrape_jobs"

# Catálogo de fuentes actualizables desde la UI.
# script: módulo con main() | argv extra | farmacia para mapear cards
FUENTES: dict[str, dict[str, Any]] = {
    "farmavalue": {
        "nombre": "FarmaValue",
        "grupo": "farmacia",
        "farmacia": "FarmaValue",
        "pais": "República Dominicana",
        "script": "scrapper/rd_farmavalue.py",
        "argv": ["--fresh"],
        "descripcion": "Catálogo FarmaValue / API 3C",
    },
    "carol": {
        "nombre": "Carol",
        "grupo": "farmacia",
        "farmacia": "Carol",
        "pais": "República Dominicana",
        "script": "scrapper/rd_carol.py",
        "argv": [],
        "descripcion": "Tienda VevoCart Carol",
    },
    "farmacias_do": {
        "nombre": "farmacias.do",
        "grupo": "farmacia",
        "farmacia": "farmacias.do",
        "pais": "República Dominicana",
        "script": "scrapper/rd_farmacias_do.py",
        "argv": [],
        "descripcion": "Agregador farmacias.do (sellers reales: GBC, Hidalgos, Carol, …)",
    },
    "qualipharma": {
        "nombre": "Qualipharma",
        "grupo": "farmacia",
        "farmacia": "Qualipharma",
        "pais": "República Dominicana",
        "script": "scrapper/rd_qualipharma.py",
        "argv": [],
        "descripcion": "WooCommerce Qualipharma",
    },
    "hidalgos": {
        "nombre": "Los Hidalgos",
        "grupo": "farmacia",
        "farmacia": "Los Hidalgos",
        "pais": "República Dominicana",
        "script": "scrapper/rd_hidalgos.py",
        "argv": [],
        "descripcion": "WooCommerce Hidalgos (Playwright/Cloudflare; puede fallar en este worker)",
        "requiere_playwright": True,
    },
    "paguemenos": {
        "nombre": "Pague Menos",
        "grupo": "farmacia",
        "farmacia": "Pague Menos",
        "pais": "Brasil",
        "script": "scrapper/br_paguemenos.py",
        "argv": [],
        "descripcion": "VTEX Pague Menos",
    },
    "drogasil": {
        "nombre": "Drogasil",
        "grupo": "farmacia",
        "farmacia": "Drogasil",
        "pais": "Brasil",
        "script": "scrapper/br_drogasil.py",
        "argv": [],
        "descripcion": "VTEX Drogasil (Akamai puede bloquear el datacenter)",
    },
    "drogaraia": {
        "nombre": "Droga Raia",
        "grupo": "farmacia",
        "farmacia": "Droga Raia",
        "pais": "Brasil",
        "script": "scrapper/br_drogaraia.py",
        "argv": [],
        "descripcion": "VTEX Droga Raia (Akamai puede bloquear el datacenter)",
    },
    "panvel": {
        "nombre": "Panvel",
        "grupo": "farmacia",
        "farmacia": "Panvel",
        "pais": "Brasil",
        "script": "scrapper/br_panvel.py",
        "argv": [],
        "descripcion": "VTEX Panvel (proxy puede bloquear categoría Online Shopping)",
    },
    "macrofarmacias": {
        "nombre": "Macrofarmacias",
        "grupo": "farmacia",
        "farmacia": "Macrofarmacias",
        "pais": "México",
        "script": "scrapper/mx_macrofarmacias.py",
        "argv": [],
        "descripcion": "Catálogo Macrofarmacias",
    },
    "similares": {
        "nombre": "Farmacias Similares",
        "grupo": "farmacia",
        "farmacia": "Farmacias Similares",
        "pais": "México",
        "script": "scrapper/mx_similares.py",
        "argv": [],
        "descripcion": "VTEX Farmacias Similares",
    },
    "fahorro": {
        "nombre": "Farmacias del Ahorro",
        "grupo": "farmacia",
        "farmacia": "Farmacias del Ahorro",
        "pais": "México",
        "script": "scrapper/mx_fahorro.py",
        "argv": [],
        "descripcion": "Magento GraphQL Farmacias del Ahorro",
    },
    "sanpablo": {
        "nombre": "Farmacias San Pablo",
        "grupo": "farmacia",
        "farmacia": "Farmacias San Pablo",
        "pais": "México",
        "script": "scrapper/mx_sanpablo.py",
        "argv": [],
        "descripcion": "San Pablo (Akamai; Magento/VTEX si el WAF deja pasar)",
    },
    "fesa": {
        "nombre": "Farmacias Especializadas",
        "grupo": "farmacia",
        "farmacia": "Farmacias Especializadas",
        "pais": "México",
        "script": "scrapper/mx_fesa.py",
        "argv": [],
        "descripcion": "Magento GraphQL FESA (especialidad: enzimas, oncológicos, biológicos)",
    },
    "locatel": {
        "nombre": "Locatel",
        "grupo": "farmacia",
        "farmacia": "Locatel",
        "pais": "Colombia",
        "script": "scrapper/co_locatel.py",
        "argv": [],
        "descripcion": "VTEX Locatel",
    },
    "farmatodo": {
        "nombre": "Farmatodo",
        "grupo": "farmacia",
        "farmacia": "Farmatodo",
        "pais": "Colombia",
        "script": "scrapper/co_farmatodo.py",
        "argv": [],
        "descripcion": "Algolia Farmatodo Colombia",
    },
    "cruzverde": {
        "nombre": "Cruz Verde",
        "grupo": "farmacia",
        "farmacia": "Cruz Verde",
        "pais": "Colombia",
        "script": "scrapper/co_cruzverde.py",
        "argv": [],
        "descripcion": "VTEX Cruz Verde (proxy puede bloquear Online Shopping)",
    },
    "larebaja": {
        "nombre": "La Rebaja",
        "grupo": "farmacia",
        "farmacia": "La Rebaja",
        "pais": "Colombia",
        "script": "scrapper/co_larebaja.py",
        "argv": [],
        "descripcion": "VTEX La Rebaja (proxy puede bloquear Online Shopping)",
    },
    "cafam": {
        "nombre": "Droguerías Cafam",
        "grupo": "farmacia",
        "farmacia": "Droguerías Cafam",
        "pais": "Colombia",
        "script": "scrapper/co_cafam.py",
        "argv": [],
        "descripcion": "VTEX Cafam (proxy puede bloquear Online Shopping)",
    },
    "carulla": {
        "nombre": "Carulla",
        "grupo": "farmacia",
        "farmacia": "Carulla",
        "pais": "Colombia",
        "script": "scrapper/co_carulla.py",
        "argv": [],
        "descripcion": "VTEX Carulla (droguería en supermercado)",
    },
    "farmacity": {
        "nombre": "Farmacity",
        "grupo": "farmacia",
        "farmacia": "Farmacity",
        "pais": "Argentina",
        "script": "scrapper/ar_farmacity.py",
        "argv": [],
        "descripcion": "VTEX Farmacity",
    },
    "alfabeta": {
        "nombre": "AlfaBeta",
        "grupo": "farmacia",
        "farmacia": "AlfaBeta",
        "pais": "Argentina",
        "script": "scrapper/ar_alfabeta.py",
        "argv": [],
        "descripcion": "Manual Farmacéutico AlfaBeta (PVP de referencia AR; especialidad)",
    },
    "salcobrand": {
        "nombre": "Salcobrand",
        "grupo": "farmacia",
        "farmacia": "Salcobrand",

        "pais": "Chile",
        "script": "scrapper/cl_salcobrand.py",
        "argv": [],
        "descripcion": "Algolia Salcobrand Chile",
    },
    "ahumada": {
        "nombre": "Farmacias Ahumada",
        "grupo": "farmacia",
        "farmacia": "Farmacias Ahumada",
        "pais": "Chile",
        "script": "scrapper/cl_ahumada.py",
        "argv": [],
        "descripcion": "Demandware Farmacias Ahumada Chile",
    },
    "arrocha": {
        "nombre": "Arrocha",
        "grupo": "farmacia",
        "farmacia": "Arrocha",
        "pais": "Panamá",
        "script": "scrapper/pa_arrocha.py",
        "argv": [],
        "descripcion": "Shopify Farmacias Arrocha (cobertura especialidad online limitada)",
    },
    "panamfarma": {
        "nombre": "Pan Am Farma",
        "grupo": "farmacia",
        "farmacia": "Pan Am Farma",
        "pais": "Panamá",
        "script": "scrapper/pa_panamfarma.py",
        "argv": [],
        "descripcion": "WooCommerce Pan Am Farma (especialidad oncológica/biológicos, USD)",
    },
    "julios": {
        "nombre": "Farmacias Julios",
        "grupo": "farmacia",
        "farmacia": "Farmacias Julios",
        "pais": "Panamá",
        "script": "scrapper/pa_julios.py",
        "argv": [],
        "descripcion": "WooCommerce Farmacias Julios Panamá (oncológicos y alto costo)",
    },
    "inkafarma": {
        "nombre": "Inkafarma",
        "grupo": "farmacia",
        "farmacia": "Inkafarma",
        "pais": "Perú",
        "script": "scrapper/pe_inkafarma.py",
        "argv": [],
        "descripcion": "Algolia Inkafarma (web puede estar bloqueada; API Algolia suele responder)",
    },
    "boticasperu": {
        "nombre": "Boticas Perú",
        "grupo": "farmacia",
        "farmacia": "Boticas Perú",
        "pais": "Perú",
        "script": "scrapper/pe_boticasperu.py",
        "argv": [],
        "descripcion": "Demandware Boticas Perú",
    },
    "farmashop": {
        "nombre": "Farmashop",
        "grupo": "farmacia",
        "farmacia": "Farmashop",
        "pais": "Uruguay",
        "script": "scrapper/uy_farmashop.py",
        "argv": [],
        "descripcion": "VTEX Farmashop tienda.farmashop.com.uy (proxy suele bloquear)",
    },
    "pigalle": {
        "nombre": "Pigalle",
        "grupo": "farmacia",
        "farmacia": "Pigalle",
        "pais": "Uruguay",
        "script": "scrapper/uy_pigalle.py",
        "argv": [],
        "descripcion": "Magento suggest Pigalle Uruguay",
    },
    "farmacity_uy": {
        "nombre": "Farmacity UY",
        "grupo": "farmacia",
        "farmacia": "Farmacity UY",
        "pais": "Uruguay",
        "script": "scrapper/uy_farmacity.py",
        "argv": [],
        "descripcion": "VTEX Farmacity Uruguay",
    },
    "antartida": {
        "nombre": "Farmacia Antártida",
        "grupo": "farmacia",
        "farmacia": "Farmacia Antártida",
        "pais": "Uruguay",
        "script": "scrapper/uy_antartida.py",
        "argv": [],
        "descripcion": "Batitienda Farmacia Antártida (Products_Search)",
    },
    "goes": {
        "nombre": "Farmacia Goes",
        "grupo": "farmacia",
        "farmacia": "Farmacia Goes",
        "pais": "Uruguay",
        "script": "scrapper/uy_goes.py",
        "argv": [],
        "descripcion": "HTML Farmacia Goes (/medicamentos?q=)",
    },
    "siman": {
        "nombre": "Siman",
        "grupo": "farmacia",
        "farmacia": "Siman",
        "pais": "El Salvador",
        "script": "scrapper/sv_siman.py",
        "argv": [],
        "descripcion": "VTEX Siman (sección Farmacia, USD)",
    },
    "sv_sannicolas": {
        "nombre": "Farmacias San Nicolás",
        "grupo": "farmacia",
        "farmacia": "Farmacias San Nicolás",
        "pais": "El Salvador",
        "script": "scrapper/sv_sannicolas.py",
        "argv": [],
        "descripcion": "VTEX Farmacias San Nicolás (proxy puede bloquear Online Shopping)",
    },
    "ec_pharmacys": {
        "nombre": "Pharmacy's",
        "grupo": "farmacia",
        "farmacia": "Pharmacy's",
        "pais": "Ecuador",
        "script": "scrapper/ec_pharmacys.py",
        "argv": [],
        "descripcion": "VTEX Pharmacy's Ecuador (grupo DIFARE)",
    },
    "ec_cruzazul": {
        "nombre": "Cruz Azul",
        "grupo": "farmacia",
        "farmacia": "Cruz Azul",
        "pais": "Ecuador",
        "script": "scrapper/ec_cruzazul.py",
        "argv": [],
        "descripcion": "VTEX Cruz Azul Ecuador (grupo DIFARE)",
    },
    "ec_fybeca": {
        "nombre": "Fybeca",
        "grupo": "farmacia",
        "farmacia": "Fybeca",
        "pais": "Ecuador",
        "script": "scrapper/ec_fybeca.py",
        "argv": [],
        "descripcion": "VTEX Fybeca Ecuador (WAF puede bloquear el datacenter)",
    },
    "hn_siman": {
        "nombre": "Siman Honduras",
        "grupo": "farmacia",
        "farmacia": "Siman",
        "pais": "Honduras",
        "script": "scrapper/hn_siman.py",
        "argv": [],
        "descripcion": "VTEX Siman (sección Farmacia, USD)",
    },
    "hn_kielsa": {
        "nombre": "Kielsa Honduras",
        "grupo": "farmacia",
        "farmacia": "Kielsa",
        "pais": "Honduras",
        "script": "scrapper/hn_kielsa.py",
        "argv": [],
        "descripcion": "Buscador buscador.kielsa.com + detalle Meteor DDP",
    },
    "hn_fahorro": {
        "nombre": "Farmacias del Ahorro HN",
        "grupo": "farmacia",
        "farmacia": "Farmacias del Ahorro",
        "pais": "Honduras",
        "script": "scrapper/hn_fahorro.py",
        "argv": [],
        "descripcion": "Tienda farmaciasdelahorro.hn (SPA; sin API pública estable)",
    },
    "hn_mifarmacia": {
        "nombre": "MiFarmacia Honduras",
        "grupo": "farmacia",
        "farmacia": "MiFarmacia",
        "pais": "Honduras",
        "script": "scrapper/hn_mifarmacia.py",
        "argv": [],
        "descripcion": "API /api/search de mifarmacia.hn (catálogo Quimifar digital)",
    },
    "gt_siman": {
        "nombre": "Siman Guatemala",
        "grupo": "farmacia",
        "farmacia": "Siman",
        "pais": "Guatemala",
        "script": "scrapper/gt_siman.py",
        "argv": [],
        "descripcion": "VTEX Siman (sección Farmacia, USD)",
    },
    "gt_batres": {
        "nombre": "Farmacias Batres",
        "grupo": "farmacia",
        "farmacia": "Farmacias Batres",
        "pais": "Guatemala",
        "script": "scrapper/gt_batres.py",
        "argv": [],
        "descripcion": "VTEX Farmacias Batres (WAF puede bloquear el datacenter)",
    },
    "gt_galeno": {
        "nombre": "Farmacias Galeno",
        "grupo": "farmacia",
        "farmacia": "Farmacias Galeno",
        "pais": "Guatemala",
        "script": "scrapper/gt_galeno.py",
        "argv": [],
        "descripcion": "Farmacias Galeno Guatemala (catálogo online limitado)",
    },
    "ni_siman": {
        "nombre": "Siman Nicaragua",
        "grupo": "farmacia",
        "farmacia": "Siman",
        "pais": "Nicaragua",
        "script": "scrapper/ni_siman.py",
        "argv": [],
        "descripcion": "VTEX Siman (sección Farmacia, USD)",
    },
    "ni_kielsa": {
        "nombre": "Kielsa Nicaragua",
        "grupo": "farmacia",
        "farmacia": "Kielsa",
        "pais": "Nicaragua",
        "script": "scrapper/ni_kielsa.py",
        "argv": [],
        "descripcion": "Buscador buscadorni.kielsa.com + detalle Meteor DDP",
    },
    "ni_fahorro": {
        "nombre": "Farmacias del Ahorro NI",
        "grupo": "farmacia",
        "farmacia": "Farmacias del Ahorro",
        "pais": "Nicaragua",
        "script": "scrapper/ni_fahorro.py",
        "argv": [],
        "descripcion": "Cadena regional Farmacias del Ahorro (sin API pública estable)",
    },
    "cr_siman": {
        "nombre": "Siman Costa Rica",
        "grupo": "farmacia",
        "farmacia": "Siman",
        "pais": "Costa Rica",
        "script": "scrapper/cr_siman.py",
        "argv": [],
        "descripcion": "VTEX Siman (sección Farmacia, USD)",
    },
    "cr_kolbi": {
        "nombre": "Kölbi",
        "grupo": "farmacia",
        "farmacia": "Kölbi",
        "pais": "Costa Rica",
        "script": "scrapper/cr_kolbi.py",
        "argv": [],
        "descripcion": "Tienda Kölbi CR (WAF puede bloquear el datacenter)",
    },
    "cr_fischel": {
        "nombre": "Farmacias Fischel",
        "grupo": "farmacia",
        "farmacia": "Farmacias Fischel",
        "pais": "Costa Rica",
        "script": "scrapper/cr_fischel.py",
        "argv": [],
        "descripcion": "Farmacias Fischel Costa Rica (catálogo online limitado)",
    },
    "py_puntofarma": {
        "nombre": "Punto Farma",
        "grupo": "farmacia",
        "farmacia": "Punto Farma",
        "pais": "Paraguay",
        "script": "scrapper/py_puntofarma.py",
        "argv": [],
        "descripcion": "Punto Farma Paraguay (payload SSR de búsqueda con PVP público)",
    },
    "py_prosalud": {
        "nombre": "Prosalud Farma",
        "grupo": "farmacia",
        "farmacia": "Prosalud Farma",
        "pais": "Paraguay",
        "script": "scrapper/py_prosalud.py",
        "argv": [],
        "descripcion": "WooCommerce Store API Prosalud Farma Paraguay",
    },
    "ve_saas": {
        "nombre": "Farmacia SAAS",
        "grupo": "farmacia",
        "farmacia": "Farmacia SAAS",
        "pais": "Venezuela",
        "script": "scrapper/ve_saas.py",
        "argv": [],
        "descripcion": "VTEX Farmacia SAAS Venezuela",
    },
    "gy_pharmax": {
        "nombre": "Pharma-X Online",
        "grupo": "farmacia",
        "farmacia": "Pharma-X Online",
        "pais": "Guyana",
        "script": "scrapper/gy_pharmax.py",
        "argv": [],
        "descripcion": "WooCommerce Store API Pharma-X Online Guyana",
    },
    "gy_poonai": {
        "nombre": "Poonai Pharmacy",
        "grupo": "farmacia",
        "farmacia": "Poonai Pharmacy",
        "pais": "Guyana",
        "script": "scrapper/gy_poonai.py",
        "argv": [],
        "descripcion": "WooCommerce Store API Poonai Pharmacy Guyana (cobertura parcial)",
    },
    "tt_trinipharma": {
        "nombre": "TriniPharma",
        "grupo": "farmacia",
        "farmacia": "TriniPharma",
        "pais": "Trinidad y Tobago",
        "script": "scrapper/tt_trinipharma.py",
        "argv": [],
        "descripcion": "API pública TriniPharma Trinidad y Tobago",
    },
    "bo_fsa": {
        "nombre": "FSA Tienda Online",
        "grupo": "farmacia",
        "farmacia": "FSA Tienda Online",
        "pais": "Bolivia",
        "script": "scrapper/bo_fsa.py",
        "argv": [],
        "descripcion": "API de búsqueda FSA Tienda Online Bolivia",
    },
    "ve_locatel": {
        "nombre": "Locatel Venezuela",
        "grupo": "farmacia",
        "farmacia": "Locatel",
        "pais": "Venezuela",
        "script": "scrapper/ve_locatel.py",
        "argv": [],
        "descripcion": "VTEX Locatel Venezuela (fuente nueva; no altera cron diario)",
    },
    "cl_profar": {
        "nombre": "Profar",
        "grupo": "farmacia",
        "farmacia": "Profar",
        "pais": "Chile",
        "script": "scrapper/cl_profar.py",
        "argv": [],
        "descripcion": "Magento GraphQL Profar Chile (especialidad)",
    },
    "cl_farmex": {
        "nombre": "Farmex",
        "grupo": "farmacia",
        "farmacia": "Farmex",
        "pais": "Chile",
        "script": "scrapper/cl_farmex.py",
        "argv": [],
        "descripcion": "Shopify Farmex Chile",
    },
    "bo_farmacorp": {
        "nombre": "Farmacorp",
        "grupo": "farmacia",
        "farmacia": "Farmacorp",
        "pais": "Bolivia",
        "script": "scrapper/bo_farmacorp.py",
        "argv": [],
        "descripcion": "Shopify Farmacorp Bolivia (API myshopify)",
    },
    "pe_universal": {
        "nombre": "Farmacia Universal",
        "grupo": "farmacia",
        "farmacia": "Farmacia Universal",
        "pais": "Perú",
        "script": "scrapper/pe_universal.py",
        "argv": [],
        "descripcion": "VTEX Farmacia Universal Perú",
    },
    "gt_meykos": {
        "nombre": "Meykos",
        "grupo": "farmacia",
        "farmacia": "Meykos",
        "pais": "Guatemala",
        "script": "scrapper/gt_meykos.py",
        "argv": [],
        "descripcion": "API /api/search Meykos Guatemala",
    },
    "gt_cruzverde": {
        "nombre": "Cruz Verde Guatemala",
        "grupo": "farmacia",
        "farmacia": "Cruz Verde",
        "pais": "Guatemala",
        "script": "scrapper/gt_cruzverde.py",
        "argv": [],
        "descripcion": "API /api/products Cruz Verde Guatemala",
    },
    "sv_elfarmaceutico": {
        "nombre": "El Farmacéutico",
        "grupo": "farmacia",
        "farmacia": "El Farmacéutico",
        "pais": "El Salvador",
        "script": "scrapper/sv_elfarmaceutico.py",
        "argv": [],
        "descripcion": "Woo Store API El Farmacéutico El Salvador",
    },
    "cr_farmavalue": {
        "nombre": "FarmaValue CR",
        "grupo": "farmacia",
        "farmacia": "FarmaValue",
        "pais": "Costa Rica",
        "script": "scrapper/cr_farmavalue.py",
        "argv": [],
        "descripcion": "API cr-app.3c.group FarmaValue Costa Rica",
    },
    "gt_farmavalue": {
        "nombre": "FarmaValue GT",
        "grupo": "farmacia",
        "farmacia": "FarmaValue",
        "pais": "Guatemala",
        "script": "scrapper/gt_farmavalue.py",
        "argv": [],
        "descripcion": "API fg-app.3c.group FarmaValue Guatemala",
    },
    "sv_farmavalue": {
        "nombre": "FarmaValue SV",
        "grupo": "farmacia",
        "farmacia": "FarmaValue",
        "pais": "El Salvador",
        "script": "scrapper/sv_farmavalue.py",
        "argv": [],
        "descripcion": "API fe-app.3c.group FarmaValue El Salvador",
    },

    "pa_farmavalue": {
        "nombre": "FarmaValue PA",
        "grupo": "farmacia",
        "farmacia": "FarmaValue",
        "pais": "Panamá",
        "script": "scrapper/pa_farmavalue.py",
        "argv": [],
        "descripcion": "API fp-app.3c.group FarmaValue Panamá",
    },
    "hn_farmavalue": {
        "nombre": "FarmaValue HN",
        "grupo": "farmacia",
        "farmacia": "FarmaValue",
        "pais": "Honduras",
        "script": "scrapper/hn_farmavalue.py",
        "argv": [],
        "descripcion": "API fa-app.3c.group FarmaValue Honduras",
    },
    "ni_farmavalue": {
        "nombre": "FarmaValue NI",
        "grupo": "farmacia",
        "farmacia": "FarmaValue",
        "pais": "Nicaragua",
        "script": "scrapper/ni_farmavalue.py",
        "argv": [],
        "descripcion": "API fv-app.3c.group FarmaValue Nicaragua",
    },
    "py_biggie": {
        "nombre": "Biggie",
        "grupo": "farmacia",
        "farmacia": "Biggie",
        "pais": "Paraguay",
        "script": "scrapper/py_biggie.py",
        "argv": [],
        "descripcion": "API api.app.biggie.com.py Paraguay",
    },
    "cl_farmavalue": {
        "nombre": "FarmaValue CL",
        "grupo": "farmacia",
        "farmacia": "FarmaValue",
        "pais": "Chile",
        "script": "scrapper/cl_farmavalue.py",
        "argv": [],
        "descripcion": "API cl-app.3c.group FarmaValue Chile",
    },
    "mx_farmavalue": {
        "nombre": "FarmaValue MX",
        "grupo": "farmacia",
        "farmacia": "FarmaValue",
        "pais": "México",
        "script": "scrapper/mx_farmavalue.py",
        "argv": [],
        "descripcion": "API fm-app.3c.group FarmaValue México",
    },
    "tt_cva": {
        "nombre": "CVA Pharmacy",
        "grupo": "farmacia",
        "farmacia": "CVA Pharmacy",
        "pais": "Trinidad y Tobago",
        "script": "scrapper/tt_cva.py",
        "argv": [],
        "descripcion": "Woo Store API cvalimited.com/pharmacy",
    },
    "us_costplus": {
        "nombre": "Cost Plus Drugs",
        "grupo": "farmacia",
        "farmacia": "Cost Plus Drugs",
        "pais": "Estados Unidos",
        "script": "scrapper/us_costplus.py",
        "argv": [],
        "descripcion": "API pública Mark Cuban Cost Plus Drugs (EE.UU.)",
    },
    "us_nadac": {
        "nombre": "NADAC (CMS)",
        "grupo": "farmacia",
        "farmacia": "NADAC (CMS)",
        "pais": "Estados Unidos",
        "script": "scrapper/us_nadac.py",
        "argv": [],
        "descripcion": "NADAC CMS — costo de adquisición promedio (Medicaid open data)",
    },
    "ca_adbl": {
        "nombre": "ADBL Alberta",
        "grupo": "farmacia",
        "farmacia": "ADBL Alberta",
        "pais": "Canadá",
        "script": "scrapper/ca_adbl.py",
        "argv": [],
        "descripcion": "Alberta Drug Benefit List (Excel Blue Cross, CAD)",
    },
    "fda_purple": {
        "nombre": "FDA Purple Book",
        "grupo": "fda",
        "farmacia": None,
        "pais": "Estados Unidos",
        "script": "scrapper/fda_purple_book.py",
        "argv": ["--fresh"],
        "descripcion": "CSV mensual Purple Book por principio activo",
    },
    "fda_info": {
        "nombre": "FDA openFDA / patentes",
        "grupo": "fda",
        "farmacia": None,
        "pais": "Estados Unidos",
        "script": "scrapper/fda_openfda_info.py",
        "argv": [],
        "descripcion": "Indicaciones, TA, patentes Orange/Purple Book",
    },
    "ema_medicines": {
        "nombre": "EMA medicines",
        "grupo": "ema",
        "farmacia": None,
        "pais": "Unión Europea",
        "script": "scrapper/ema_medicines.py",
        "argv": ["--fresh"],
        "descripcion": "Catálogo oficial EMA (XLSX) por principio activo",
    },
}

DDL = """
IF NOT EXISTS (
    SELECT 1
    FROM sys.tables t
    INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
    WHERE t.name = N'{tabla}' AND s.name = N'{schema}'
)
BEGIN
    CREATE TABLE {qschema}.{qtabla} (
        id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        fuente_id NVARCHAR(40) NOT NULL,
        estado NVARCHAR(20) NOT NULL,
        solicitado_por NVARCHAR(80) NULL,
        argv_json NVARCHAR(400) NULL,
        log_path NVARCHAR(500) NULL,
        mensaje NVARCHAR(1000) NULL,
        exit_code INT NULL,
        worker_id NVARCHAR(80) NULL,
        fecha_registro DATETIME NOT NULL CONSTRAINT DF_{df}_reg DEFAULT GETDATE(),
        fecha_inicio DATETIME NULL,
        fecha_fin DATETIME NULL,
        fecha_actualizacion DATETIME NOT NULL CONSTRAINT DF_{df}_upd DEFAULT GETDATE()
    );
    CREATE INDEX IX_{df}_estado ON {qschema}.{qtabla} (estado, id);
    CREATE INDEX IX_{df}_fuente ON {qschema}.{qtabla} (fuente_id, estado);
END
"""


def _ids() -> tuple[str, str, str, str]:
    schema = resumen_config()["schema"]
    return f"[{schema}]", f"[{TABLA}]", f"{schema}.{TABLA}", "mac_job"


def asegurar_tabla() -> str:
    qschema, qtabla, full, df = _ids()
    schema = resumen_config()["schema"]
    sql = (
        DDL.replace("{qschema}", qschema)
        .replace("{qtabla}", qtabla)
        .replace("{schema}", schema)
        .replace("{tabla}", TABLA)
        .replace("{df}", df)
    )
    with engine().begin() as conn:
        conn.execute(text(sql))
    return full


def listar_fuentes() -> list[dict[str, Any]]:
    out = []
    for fid, meta in FUENTES.items():
        out.append(
            {
                "id": fid,
                "nombre": meta["nombre"],
                "grupo": meta["grupo"],
                "farmacia": meta.get("farmacia"),
                "pais": meta.get("pais"),
                "descripcion": meta.get("descripcion"),
                "requiere_playwright": bool(meta.get("requiere_playwright")),
            }
        )
    return out


def fuente_por_farmacia(farmacia: str | None) -> str | None:
    if not farmacia:
        return None
    for fid, meta in FUENTES.items():
        if meta.get("farmacia") and str(meta["farmacia"]).lower() == str(farmacia).lower():
            return fid
    # farmacias.do naming variants
    if "farmacias.do" in str(farmacia).lower() or "farmacias do" in str(farmacia).lower():
        return "farmacias_do"
    return None


def _jsonable(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return v


def _row_to_dict(row: Any) -> dict[str, Any]:
    d = {k: _jsonable(v) for k, v in dict(row).items()}
    fid = d.get("fuente_id")
    meta = FUENTES.get(str(fid) or "", {})
    d["fuente_nombre"] = meta.get("nombre") or fid
    d["fuente_grupo"] = meta.get("grupo")
    return d


def encolar(fuente_id: str, *, solicitado_por: str = "ui", force: bool = False) -> dict[str, Any]:
    asegurar_tabla()
    if fuente_id == "farmacias_do":
        raise ValueError("farmacias.do está excluida en este servidor")
    if fuente_id not in FUENTES:
        raise ValueError(f"Fuente desconocida: {fuente_id}")
    qschema, qtabla, _full, _df = _ids()
    with engine().begin() as conn:
        if not force:
            existente = conn.execute(
                text(
                    f"SELECT TOP 1 * FROM {qschema}.{qtabla} "
                    "WHERE fuente_id = :f AND estado IN (N'queued', N'running') "
                    "ORDER BY id DESC"
                ),
                {"f": fuente_id},
            ).mappings().first()
            if existente:
                out = _row_to_dict(existente)
                out["reutilizado"] = True
                return out
        argv = FUENTES[fuente_id].get("argv") or []
        res = conn.execute(
            text(
                f"INSERT INTO {qschema}.{qtabla} "
                "(fuente_id, estado, solicitado_por, argv_json, fecha_registro, fecha_actualizacion) "
                "OUTPUT INSERTED.* "
                "VALUES (:f, N'queued', :quien, :argv, GETDATE(), GETDATE())"
            ),
            {
                "f": fuente_id,
                "quien": (solicitado_por or "ui")[:80],
                "argv": json.dumps(argv, ensure_ascii=False),
            },
        )
        row = res.mappings().first()
    out = _row_to_dict(row)
    out["reutilizado"] = False
    return out


def obtener(job_id: int) -> dict[str, Any] | None:
    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()
    with engine().connect() as conn:
        row = conn.execute(
            text(f"SELECT TOP 1 * FROM {qschema}.{qtabla} WHERE id = :id"),
            {"id": int(job_id)},
        ).mappings().first()
    return _row_to_dict(row) if row else None


def listar_jobs(*, limite: int = 40, fuente_id: str | None = None) -> list[dict[str, Any]]:
    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()
    params: dict[str, Any] = {"lim": int(limite)}
    where = ""
    if fuente_id:
        where = "WHERE fuente_id = :f"
        params["f"] = fuente_id
    with engine().connect() as conn:
        rows = conn.execute(
            text(
                f"SELECT TOP (:lim) * FROM {qschema}.{qtabla} {where} "
                "ORDER BY id DESC"
            ),
            params,
        ).mappings().all()
    return [_row_to_dict(r) for r in rows]


def estados_por_fuente() -> dict[str, dict[str, Any]]:
    """Último job por fuente_id (para pintar botones)."""
    jobs = listar_jobs(limite=200)
    out: dict[str, dict[str, Any]] = {}
    for j in jobs:
        fid = str(j.get("fuente_id") or "")
        if fid and fid not in out:
            out[fid] = j
    return out


def reclamar_siguiente(worker_id: str) -> dict[str, Any] | None:
    """Toma el job queued más viejo (1 a la vez por worker claim)."""
    from db import es_postgres

    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()
    with engine().begin() as conn:
        if es_postgres():
            sql = f"""
                UPDATE {qschema}.{qtabla} AS t
                SET estado = 'running',
                    worker_id = :w,
                    fecha_inicio = CURRENT_TIMESTAMP,
                    fecha_actualizacion = CURRENT_TIMESTAMP
                WHERE t.id = (
                    SELECT id FROM {qschema}.{qtabla}
                    WHERE estado = 'queued'
                    ORDER BY id ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                RETURNING *
            """
        else:
            sql = f"""
                ;WITH cte AS (
                    SELECT TOP 1 *
                    FROM {qschema}.{qtabla} WITH (UPDLOCK, READPAST, ROWLOCK)
                    WHERE estado = N'queued'
                    ORDER BY id ASC
                )
                UPDATE cte
                SET estado = N'running',
                    worker_id = :w,
                    fecha_inicio = GETDATE(),
                    fecha_actualizacion = GETDATE()
                OUTPUT INSERTED.*;
            """
        row = conn.execute(
            text(sql),
            {"w": (worker_id or "worker")[:80]},
        ).mappings().first()
    return _row_to_dict(row) if row else None


def marcar_fin(
    job_id: int,
    *,
    ok: bool,
    exit_code: int | None,
    mensaje: str | None,
    log_path: str | None,
) -> None:
    qschema, qtabla, _full, _df = _ids()
    with engine().begin() as conn:
        conn.execute(
            text(
                f"UPDATE {qschema}.{qtabla} SET "
                "estado = :est, exit_code = :ec, mensaje = :msg, log_path = :lp, "
                "fecha_fin = GETDATE(), fecha_actualizacion = GETDATE() "
                "WHERE id = :id"
            ),
            {
                "id": int(job_id),
                "est": "done" if ok else "error",
                "ec": exit_code,
                "msg": (mensaje or "")[:1000] or None,
                "lp": (log_path or "")[:500] or None,
            },
        )


def registrar_resultado_cron(
    fuente_id: str,
    *,
    ok: bool,
    exit_code: int | None = None,
    mensaje: str | None = None,
    estado_extra: str | None = None,
) -> dict[str, Any] | None:
    """Inserta un job ya terminado para que la UI de Fuentes vea el cron.

    No encola trabajo: solo deja rastro en ``medicamentos_scrape_jobs``.
    """
    if fuente_id not in FUENTES:
        return None
    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()
    if estado_extra in ("cache", "warn"):
        # La UI solo entiende done/error/queued/running; usamos done + mensaje.
        est = "done"
        ok_flag = True
    else:
        est = "done" if ok else "error"
        ok_flag = ok
    argv = FUENTES[fuente_id].get("argv") or []
    with engine().begin() as conn:
        row = conn.execute(
            text(
                f"INSERT INTO {qschema}.{qtabla} "
                "(fuente_id, estado, solicitado_por, argv_json, mensaje, exit_code, "
                " worker_id, fecha_registro, fecha_inicio, fecha_fin, fecha_actualizacion) "
                "OUTPUT INSERTED.* "
                "VALUES (:f, :est, N'cron', :argv, :msg, :ec, "
                " N'cron-diario', GETDATE(), GETDATE(), GETDATE(), GETDATE())"
            ),
            {
                "f": fuente_id,
                "est": est,
                "argv": json.dumps(argv, ensure_ascii=False),
                "msg": (mensaje or "")[:1000] or None,
                "ec": exit_code if exit_code is not None else (0 if ok_flag else 1),
            },
        ).mappings().first()
    return _row_to_dict(row) if row else None


def recuperar_stale(minutos: int = 180) -> int:
    """Jobs 'running' demasiado viejos → error (worker muerto)."""
    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()
    with engine().begin() as conn:
        res = conn.execute(
            text(
                f"UPDATE {qschema}.{qtabla} SET "
                "estado = N'error', "
                "mensaje = N'Worker interrumpido o timeout; job marcado como error', "
                "fecha_fin = GETDATE(), fecha_actualizacion = GETDATE() "
                "WHERE estado = N'running' "
                "AND fecha_inicio IS NOT NULL "
                "AND fecha_inicio < DATEADD(minute, -:m, GETDATE())"
            ),
            {"m": int(minutos)},
        )
        return res.rowcount or 0
