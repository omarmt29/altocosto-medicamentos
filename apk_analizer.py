#!/usr/bin/env python3
"""
Analizador de APK para extraer información (catálogos, endpoints, datos).
Uso: python apk_analizer.py ruta_al.apk
"""
import os
import sys
import re
import shutil
from datetime import datetime
import zipfile
import json
import sqlite3
import csv
import string
import tempfile
from pathlib import Path
import hashlib


def get_strings_from_bytes(data, min_len=4):
    """Extrae cadenas ASCII/UTF-8 mínimamente legibles."""
    try:
        content = data.decode("utf-8", errors="ignore")
    except Exception:
        content = ""
    return re.findall(r"[ -~]{%d,}" % min_len, content)


def extraer_archivos(apk_path):
    """Devuelve dict de nombre de archivo -> contenido bytes."""
    with zipfile.ZipFile(apk_path, "r") as z:
        return {name: z.read(name) for name in z.namelist()}


def identificar_interesantes(nombres):
    """Filtra nombres de archivo potencialmente relevantes."""
    categorias = [
        (r"\.(json|csv|txt|sqlite|db|xml|yaml|yml)$", "Datos"),
        (r"^assets/", "assets"),
        (r"^res/raw", "raw"),
        (r"^AndroidManifest\.xml$", "Manifest"),
        (r"\.dex$", "Código"),
        (r"\.arsc$", "Recursos"),
        (r"\.properties$|\.conf$|\.cfg$|\.ini$", "Config"),
    ]
    relevantes = {}
    for nombre in nombres:
        for patron, etiqueta in categorias:
            if re.search(patron, nombre):
                relevantes[nombre] = etiqueta
                break
    return relevantes


def buscar_uris(content, keywords):
    """Busca URLs y palabras clave en texto."""
    urls = []
    if not content:
        return urls
    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        return urls
    for m in re.finditer(r"https?://[^\s<>\"']+", text):
        urls.append(m.group(0))
    for keyword in keywords:
        positions = [m.start() for m in re.finditer(keyword, text)]
        if positions:
            print(f"Keyword '{keyword}' encontrado {len(positions)} veces")
    return urls


def procesar_archivo(nombre, contenido):
    """Analiza un archivo según su extensión."""
    if not contenido:
        return None
    ext = nombre.lower().split(".")[-1] if "." in nombre else ""
    if ext == "json":
        try:
            data = json.loads(contenido)
            n = len(data) if hasattr(data, "__len__") else 1
            print(f"[JSON] {nombre} - datos decodificados ({n} elementos)")
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                sample = data[0]
                if any(kw in sample for kw in ["nombre", "producto", "precio", "sku", "description"]):
                    print(f"   >>> Posible catálogo. Ejemplo: {json.dumps(sample, ensure_ascii=False)[:200]}")
        except Exception:
            print(f"[!] JSON inválido: {nombre}")
    elif ext in ("db", "sqlite", "sqlite3"):
        tmp = None
        try:
            fd, tmp = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            with open(tmp, "wb") as f:
                f.write(contenido)
            conn = sqlite3.connect(tmp)
            cur = conn.cursor()
            tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            print(f"[SQLITE] {nombre} tablas: {[t[0] for t in tables]}")
            conn.close()
        except Exception as e:
            print(f" (no se pudo obtener schema por {e})")
        finally:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)
    elif ext == "csv":
        try:
            reader = csv.DictReader(contenido.decode("utf-8", errors="ignore").splitlines())
            rows = list(reader)
            if rows and any(kw in rows[0] for kw in ["producto", "sku", "precio"]):
                print(f"[CSV] {nombre}: {len(rows)} filas, posible catálogo")
        except Exception:
            pass
    if "xml" in nombre.lower():
        try:
            text = contenido.decode("utf-8", errors="ignore")
            if "<manifest" in text:
                print("[XML] AndroidManifest.xml detectado")
                m = re.search(r'package="([^"]+)"', text)
                if m:
                    print(f"   → paquete: {m.group(1)}")
        except Exception:
            pass


def main():
    if len(sys.argv) < 2:
        print("Uso: python apk_analizer.py camino_al.apk")
        sys.exit(1)
    apk_path = sys.argv[1]
    if not os.path.exists(apk_path):
        print(f"Error: {apk_path} no existe")
        sys.exit(1)

    sha = hashlib.sha256()
    with open(apk_path, "rb") as f:
        sha.update(f.read())
    print("=== SHA256:", sha.hexdigest())
    print("=== Fecha:", datetime.now().isoformat(timespec="seconds"))
    print("=== Tamaño:", os.path.getsize(apk_path), "bytes")

    print("Extrayendo APK temporalmente...")
    temp_dir = tempfile.mkdtemp(prefix="apk_analysis_")
    with zipfile.ZipFile(apk_path, "r") as z:
        names = z.namelist()
        z.extractall(temp_dir)

    interesantes = identificar_interesantes(names)
    print(f"\n[Archivos en el ZIP: {len(names)} | relevantes: {len(interesantes)}]")
    por_etiqueta = {}
    for nombre, etiqueta in interesantes.items():
        por_etiqueta.setdefault(etiqueta, []).append(nombre)
    for etiqueta, items in por_etiqueta.items():
        print(f"  [{etiqueta}] {len(items)}")
        for item in items[:40]:
            print(f"    {item}")
        if len(items) > 40:
            print(f"    ... y {len(items) - 40} más")

    keywords = [
        "producto", "catalogo", "catálogo", "sku", "price", "precio",
        "inventario", "stock", "medic", "farmacia", "droguería", "api_key",
    ]

    list_files = []
    for root, dirs, files in os.walk(temp_dir):
        for fname in files:
            list_files.append(os.path.join(root, fname))

    print(f"\n[Total de archivos extraídos: {len(list_files)}]")

    cat_files = []
    for full in list_files:
        relative = os.path.relpath(full, temp_dir)
        if not re.search(r"\.(json|csv|sqlite|db|xml|dat)$", relative.lower()):
            continue
        print(f"  Archivo {relative}...")
        try:
            with open(full, "rb") as f:
                data = f.read()
            procesar_archivo(relative, data)
            if full.lower().endswith(".json"):
                try:
                    json_data = json.loads(data.decode("utf-8", errors="ignore"))
                    if isinstance(json_data, list) and json_data and isinstance(json_data[0], dict):
                        primer = json_data[0]
                        if any(key in primer for key in ["nombre", "producto", "precio", "sku", "titulo", "desc"]):
                            print(f"     >>> Catálogo probable: {relative}")
                            cat_files.append(relative)
                except Exception:
                    pass
        except Exception as e:
            print(f"  Error leyendo {relative}: {e}")

    urls = []
    print("\n=== Buscando URLs en todos los archivos ===")
    url_re = re.compile(rb"https?://[^\x00-\x1f\s\"'<>]+")
    for full in list_files:
        try:
            with open(full, "rb") as f:
                content = f.read()
            if b"http" not in content:
                continue
            for bs in url_re.findall(content):
                urls.append(bs.decode("utf-8", errors="ignore"))
        except Exception:
            pass

    unique_urls = sorted(set(urls))
    print(f"URLs únicas encontradas: {len(unique_urls)}")
    for url in unique_urls:
        print("  URL:", url)

    print("\n=== Búsqueda de keywords en binarios ===")
    found_kw = {}
    for full in list_files:
        try:
            content = open(full, "rb").read()
            for kw in keywords:
                if kw.encode() in content:
                    found_kw[kw] = found_kw.get(kw, 0) + content.count(kw.encode())
        except Exception:
            pass
    for kw, count in found_kw.items():
        print(f"  Keyword '{kw}' aparece {count} veces.")

    try:
        from androguard.core.bytecodes.apk import APK
        a = APK(apk_path)
        print("\n=== Metadatos (androguard) ===")
        print("Package: ", a.get_package())
        print("Main activity: ", a.get_main_activity())
        print("Permissions: ", a.get_permissions())
        print("Target SDK: ", a.get_target_sdk_version())
        print("Min SDK: ", a.get_min_sdk_version())
    except Exception:
        print("\nAndroguard no instalado o error. Instálalo con 'pip install androguard' para el detalle del manifest.")
        manifest = os.path.join(temp_dir, "AndroidManifest.xml")
        if os.path.exists(manifest):
            with open(manifest, "rb") as f:
                raw = f.read()
            strings = get_strings_from_bytes(raw, 4)
            print("=== Cadenas legibles en AndroidManifest.xml ===")
            for s in strings:
                if len(s) >= 4:
                    print(" ", s)

    if shutil.which("jadx"):
        print("\n[jadx detectado] Decompilando código a 'output_jadx/' ")
        os.system(f'jadx -d output_jadx "{apk_path}"')
    else:
        print("\njadx no está en PATH; se omite la decompilación.")

    shutil.rmtree(temp_dir, ignore_errors=True)
    print("\nAnálisis finalizado. Revisa la carpeta 'output_jadx' si jadx estaba disponible.")

    print("\nPosibles archivos de catálogo encontrados: ")
    if not cat_files:
        print("  (ninguno con el heurístico de campos nombre/producto/precio/sku)")
    for f in cat_files:
        print(f"  {f}")


if __name__ == "__main__":
    main()
