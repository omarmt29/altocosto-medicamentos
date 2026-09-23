const D = window.ALTO_COSTO;
const VIEWS = {
  tablero: { crumb: "Panorama", title: "Tablero" },
  comparativo: { crumb: "Precios", title: "Comparativo" },
  detalle: { crumb: "Coincidencias", title: "Detalle" },
  tendencias: { crumb: "Histórico", title: "Tendencias" },
  fuentes: { crumb: "Origen", title: "Fuentes" },
  metodologia: { crumb: "Criterios", title: "Metodología" },
  documentacion: { crumb: "Guía", title: "Documentación" },
};

const PAIS_UI = {
  do: { flag: "🇩🇴", corto: "RD", nombre: "Rep. Dominicana", full: "República Dominicana" },
  ar: { flag: "🇦🇷", corto: "AR", nombre: "Argentina", full: "Argentina" },
  br: { flag: "🇧🇷", corto: "BR", nombre: "Brasil", full: "Brasil" },
  co: { flag: "🇨🇴", corto: "CO", nombre: "Colombia", full: "Colombia" },
  pe: { flag: "🇵🇪", corto: "PE", nombre: "Perú", full: "Perú" },
  cl: { flag: "🇨🇱", corto: "CL", nombre: "Chile", full: "Chile" },
  mx: { flag: "🇲🇽", corto: "MX", nombre: "México", full: "México" },
  cr: { flag: "🇨🇷", corto: "CR", nombre: "Costa Rica", full: "Costa Rica" },
  ec: { flag: "🇪🇨", corto: "EC", nombre: "Ecuador", full: "Ecuador" },
  hn: { flag: "🇭🇳", corto: "HN", nombre: "Honduras", full: "Honduras" },
  gt: { flag: "🇬🇹", corto: "GT", nombre: "Guatemala", full: "Guatemala" },
  ni: { flag: "🇳🇮", corto: "NI", nombre: "Nicaragua", full: "Nicaragua" },
  pa: { flag: "🇵🇦", corto: "PA", nombre: "Panamá", full: "Panamá" },
  uy: { flag: "🇺🇾", corto: "UY", nombre: "Uruguay", full: "Uruguay" },
  sv: { flag: "🇸🇻", corto: "SV", nombre: "El Salvador", full: "El Salvador" },
};

/** Países ocultos en la plataforma (datos en BD; no mostrar ni comparar). */
const PAISES_DESACTIVADOS = new Set([]);

function paisActivo(id) {
  return Boolean(id) && !PAISES_DESACTIVADOS.has(id);
}

function filaPaisActivo(f) {
  return paisActivo(idPaisPorTexto(f?.pais));
}

function sanitizarPaisesDesactivados() {
  if (!paisActivo(state.paisFiltro)) state.paisFiltro = "todos";
  if (state.dpais !== "todos" && !filaPaisActivo({ pais: state.dpais })) state.dpais = "todos";
  if (state.coverPais && !paisActivo(state.coverPais)) state.coverPais = null;
  if (Array.isArray(state.tendPaises)) {
    state.tendPaises = state.tendPaises.filter((p) => paisActivo(idPaisPorTexto(p)));
  }
}

const state = {
  view: "tablero",
  q: "",
  programa: "todos",
  conDato: "todos",
  paisFiltro: "todos",
  conc: "todas",
  pres: "todas",
  alcance: "todos",
  sort: "programa",
  dir: 1,
  page: 1,
  size: 12,
  dq: "",
  dpais: "todos",
  dpage: 1,
  dsize: 12,
  selected: null,
  coverPais: null,
  coverVista: "principios",
  cq: "",
  csort: "medicamento",
  cdir: 1,
  cpage: 1,
  csize: 50,
  tendenciaN: null,
  tendenciaProductoKey: null,
  tendPaises: null,
  tendSoloMulti: false,
  tendSearchQ: "",
  tendPickerOpen: false,
  tendPaisFiltro: "todos",
};

let TABLA = [];
let SNAPSHOT_FECHA = null;
let BASE_COMP = null;
let LIVE_OK = false;
let LIVE_LOADED = false;
let COVER_LIST_CACHE = {
  paisId: null,
  todos: [],
  encontrados: [],
  faltan: [],
  tipo: "todos",
  cobertura: "todos", // todos | en | sin
  q: "",
  emptyText: "",
};
let REG_CHOOSER = { n: null, paisId: null, from: null };
let EMA_CACHE = {};
let REG_COMPARE_ROWS = [];
let TRAD_CACHE = {};
let COVER_DETAIL_CACHE = [];
let SKU_TABLE_STATE = {};
let SKU_DETAIL_CACHE = {};
let PURPLE_CACHE = {};
let TEND_DATA = null;
let TEND_CATALOG = { medicamentos: [], indicadores: null, fechas: [] };

const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
const dop = new Intl.NumberFormat("es-DO", { style: "currency", currency: "DOP", maximumFractionDigits: 0 });
const $ = (id) => document.getElementById(id);

function viewFromLocation(pathname = window.location.pathname) {
  const raw = String(pathname || "").replace(/^\/+|\/+$/g, "").trim().toLowerCase();
  if (!raw) return "tablero";
  return VIEWS[raw] ? raw : "tablero";
}

function syncRoute(view, replace = false) {
  const next = `/${view}`;
  if (window.location.pathname !== next) {
    const method = replace ? "replaceState" : "pushState";
    window.history[method]({}, "", next);
  }
}

function fmtFecha(iso) {
  const s = String(iso || "").slice(0, 10);
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : s;
}

/** Enlace público de la ficha del producto (nunca API JSON ni evidencia interna). */
function esUrlApiFarmacia(url) {
  const u = String(url || "").trim().toLowerCase();
  if (!u) return false;
  if (u.startsWith("datos/") || u.endsWith(".json")) return true;
  if (u.includes("algolia.net")) return true;
  return u.includes("/api/catalog_system/");
}

const VTEX_BASE_POR_FARMACIA = [
  ["siman", "https://www.siman.com"],
  ["farmacity", "https://www.farmacity.com"],
  ["paguemenos", "https://www.paguemenos.com.br"],
  ["locatel", "https://www.locatelcolombia.com"],
  ["farmashop", "https://www.farmashop.com.uy"],
  ["cruz azul", "https://www.farmaciascruzazul.ec"],
  ["pharmacy", "https://www.pharmacys.com.ec"],
  ["batres", "https://www.farmaciasbatres.com.gt"],
  ["galeno", "https://www.farmaciasgaleno.com.gt"],
  ["fischel", "https://www.farmaciasfischel.com"],
  ["kolbi", "https://www.kolbi.cr"],
  ["san pablo", "https://www.farmaciasanpablo.com.mx"],
  ["similares", "https://www.farmaciasdesimilares.com"],
  ["carulla", "https://www.carulla.com"],
  ["cafam", "https://www.cafam.com.co"],
  ["la rebaja", "https://www.larebajavirtual.com"],
  ["droga raia", "https://www.drogaraia.com.br"],
  ["drogasil", "https://www.drogasil.com.br"],
  ["panvel", "https://www.panvel.com"],
];

/** www.siman.com es selector de país; la tienda usa {cc}.siman.com */
const SIMAN_CC_POR_PAIS = {
  "el salvador": "sv",
  guatemala: "gt",
  nicaragua: "ni",
  "costa rica": "cr",
  honduras: "gt",
};

function simanCcPais(pais) {
  const p = asciiNorm(String(pais || "")).toLowerCase();
  for (const [needle, cc] of Object.entries(SIMAN_CC_POR_PAIS)) {
    if (p.includes(needle)) return cc;
  }
  return "";
}

function productIdDesdeSlugPdp(url) {
  const m = String(url || "").match(/-(\d+)\/p(?:\?|#|$)/i);
  return m ? m[1] : "";
}

function corregirUrlSiman(url, pais, farmacia) {
  const u = String(url || "").trim();
  if (!u || !/siman\.com/i.test(u)) return u;
  if (/https?:\/\/[a-z]{2}\.siman\.com/i.test(u)) return u;
  let cc = simanCcPais(pais);
  if (!cc && /siman/i.test(String(farmacia || ""))) cc = "sv";
  if (!cc) return u;
  return u.replace(/https?:\/\/(?:www\.)?siman\.com/i, `https://${cc}.siman.com`);
}

function baseVtexPorFila(f) {
  const blob = `${f?.farmacia || ""} ${f?.pais || ""}`.toLowerCase();
  if (/siman/.test(blob)) {
    const cc = simanCcPais(f?.pais);
    if (cc) return `https://${cc}.siman.com`;
  }
  for (const [needle, base] of VTEX_BASE_POR_FARMACIA) {
    if (blob.includes(needle)) return base;
  }
  return "";
}

function slugVtexDesdeApi(url) {
  try {
    const m = String(url || "").match(/\/products\/search\/([^/]+)\/p\/?$/i);
    return m ? decodeURIComponent(m[1]) : "";
  } catch (_) {
    return "";
  }
}

function productIdDesdeApiVtex(url) {
  try {
    const u = new URL(url, "https://local.invalid");
    for (const fq of u.searchParams.getAll("fq")) {
      const m = String(fq).match(/productId:(\d+)/i);
      if (m) return m[1];
    }
  } catch (_) { /* ignore */ }
  return "";
}

function pdpVtexDesdeFila(f, url) {
  let base = "";
  try {
    if (url && /^https?:\/\//i.test(url)) base = new URL(url).origin;
  } catch (_) { /* ignore */ }
  if (!base) base = baseVtexPorFila(f);
  if (!base) return "";

  const slug = slugVtexDesdeApi(url);
  if (slug) return `${base.replace(/\/$/, "")}/${slug}/p`;

  const pid = productIdDesdeApiVtex(url) || String(f?.id_producto_farmacia || "").trim();
  if (pid && /^\d+$/.test(pid)) {
    // Sin slug: búsqueda en la tienda (HTML), no el endpoint JSON de catálogo.
    const nombre = String(f?.nombre_comercial || f?.medicamento_lista || "").trim();
    if (nombre.length >= 4) {
      return `${base.replace(/\/$/, "")}/s?ft=${encodeURIComponent(nombre)}`;
    }
  }
  return "";
}

function fuenteUrlVisible(f) {
  let url = String(f?.fuente_url || f?.fuente || "").trim();
  if (!url) return "";

  if (esUrlApiFarmacia(url) || /^datos\//i.test(url)) {
    const alt = pdpVtexDesdeFila(f, url);
    if (alt) return corregirUrlSiman(alt, f?.pais, f?.farmacia);
    const soloHttp = String(f?.fuente_url || "").trim();
    if (soloHttp && /^https?:\/\//i.test(soloHttp) && !esUrlApiFarmacia(soloHttp)) {
      return corregirUrlSiman(soloHttp, f?.pais, f?.farmacia);
    }
    return "";
  }

  if (!/^https?:\/\//i.test(url)) return "";
  // /s?ft= ya viene normalizado desde la API cuando el SKU no existe en esa tienda regional.
  if (/\/s\?ft=/i.test(url)) return url;
  return corregirUrlSiman(url, f?.pais, f?.farmacia);
}

function linkDato(url, fecha, opts = {}) {
  const compact = !!opts.compact;
  const titulo = fecha ? `Dato del ${fmtFecha(fecha)}` : "Ver fuente";
  if (!url) {
    if (compact) {
      return fecha
        ? `<span class="dato-link is-off" title="${escapeHtml(titulo)}">—</span>`
        : `<span class="empty">—</span>`;
    }
    return fecha ? `<span class="muted">Dato del ${fmtFecha(fecha)}</span>` : "";
  }
  if (compact) {
    return `<a class="dato-link" href="${escapeHtml(url)}" target="_blank" rel="noreferrer" title="${escapeHtml(titulo)}" aria-label="${escapeHtml(titulo)}">↗</a>`;
  }
  const cuando = fecha ? ` · ${fmtFecha(fecha)}` : "";
  return `<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">Ver dato</a><span class="muted">${cuando}</span>`;
}

function campo(obj, ...pistas) {
  const keys = Object.keys(obj);
  for (const pista of pistas) {
    const hit = keys.find((k) => k.toLowerCase().includes(pista.toLowerCase()));
    if (hit) return obj[hit];
  }
  return "";
}

function badge(programa) {
  const cls =
    programa === "FOMAC" ? "fomac" :
    programa === "FOMAC*" ? "fomac-star" :
    String(programa).includes("FOMAC") ? "mix" : "damac";
  return `<span class="badge ${cls}">${escapeHtml(programa)}</span>`;
}

function escapeRegExp(s) {
  return String(s || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

const EMA_IND_HEADERS = [
  "Polyarticular juvenile idiopathic arthritis",
  "Enthesitis-related arthritis",
  "Axial spondyloarthritis",
  "Ankylosing spondylitis",
  "Juvenile idiopathic arthritis",
  "Rheumatoid arthritis",
  "Psoriatic arthritis",
  "Plaque psoriasis",
  "Hidradenitis suppurativa",
  "Crohn's disease",
  "Ulcerative colitis",
  "Paediatric uveitis",
  "Pediatric uveitis",
  "Uveitis",
  "Psoriasis",
  "Artritis idiopática juvenil poliarticular",
  "Artritis relacionada con entesitis",
  "Espondiloartritis axial",
  "Espondilitis anquilosante",
  "Artritis idiopática juvenil",
  "Artritis reumatoide",
  "Artritis psoriásica",
  "Psoriasis en placas",
  "Hidradenitis supurativa",
  "Enfermedad de Crohn",
  "Colitis ulcerosa",
  "Uveítis pediátrica",
  "Uveítis",
  "Psoriasis",
].sort((a, b) => b.length - a.length);

function indicacionesEmaDetalle(filas, info) {
  const auth = (filas || []).filter((f) => String(f.medicine_status || "").toLowerCase() === "authorised");
  const base = auth.length ? auth : (filas || []);
  const out = [];
  const seen = new Set();
  for (const f of base) {
    const texto = String(f.therapeutic_indication || "").trim();
    const ov = f.overview_es || null;
    const textoEs = String(f.therapeutic_indication_es || ov?.indicaciones || "").trim();
    const key = texto || textoEs || String(f.nombre_medicamento || "");
    if (!key || seen.has(key)) continue;
    seen.add(key);
    out.push({
      nombre: f.nombre_medicamento || "Medicamento",
      texto,
      texto_es: textoEs,
      url: f.medicine_url || "",
      pdf_es: f.overview_pdf_es || ov?.pdf_url || "",
      overview: ov,
      fuente_es: f.therapeutic_indication_es_fuente || (ov?.indicaciones ? "epar_overview_es" : ""),
    });
  }
  if (!out.length && Array.isArray(info?.indicaciones)) {
    info.indicaciones.forEach((t, i) => {
      const texto = String(t || "").trim();
      if (!texto) return;
      out.push({
        nombre: `Indicación ${i + 1}`,
        texto,
        texto_es: Array.isArray(info?.indicaciones_es) ? String(info.indicaciones_es[i] || "") : "",
        url: "",
        pdf_es: "",
        overview: null,
        fuente_es: info?.indicaciones_es_fuente || "",
      });
    });
  }
  return out.slice(0, 12);
}

function htmlSeccionesOverviewEma(ov) {
  if (!ov || !ov.secciones) return "";
  const order = [
    ["como_se_usa", "Cómo se usa"],
    ["como_actua", "Cómo actúa"],
    ["beneficios", "Beneficios en los estudios"],
    ["riesgos", "Riesgos"],
    ["autorizacion", "Por qué se autorizó en la UE"],
    ["medidas", "Medidas de uso seguro"],
    ["otra_info", "Otra información"],
  ];
  const titulos = ov.titulos || {};
  const bits = [];
  for (const [key, fallback] of order) {
    const txt = String(ov.secciones[key] || "").trim();
    if (!txt) continue;
    const title = String(titulos[key] || fallback).replace(/^¿/, "").replace(/\?$/, "");
    bits.push(`
      <details class="ema-ov-sec">
        <summary>${escapeHtml(title)}</summary>
        <div class="ema-ov-sec-body">${formatearIndicacionEmaHtml(txt)}</div>
      </details>`);
  }
  return bits.length ? `<div class="ema-ov-secs">${bits.join("")}</div>` : "";
}

function htmlIndicacionesEma(n, detalle, textosEs) {
  if (!detalle.length) return "";
  return detalle.map((d, i) => {
    const texto = (textosEs && textosEs[i]) || d.texto_es || d.texto;
    const okEs = texto && !pareceInglesUi(texto);
    const oficial = d.fuente_es === "epar_overview_es" || !!d.overview?.indicaciones;
    return `
      <details class="fda-ind" id="emaInd-${n}-${i}" ${i === 0 ? "open" : ""}>
        <summary class="fda-ind-sum">
          ${escapeHtml(d.nombre)}
          <span class="ema-ind-lang ${okEs ? "" : "is-en"} ${oficial ? "is-oficial" : ""}" data-ema-lang="${i}" title="${oficial ? "Medicine overview EPAR (ES)" : ""}">${oficial ? "ES · EPAR" : (okEs ? "ES" : "EN")}</span>
        </summary>
        <div class="fda-ind-body">
          <div class="fda-ind-text fda-ind-text--rich" data-ema-ind-body="${i}">
            ${formatearIndicacionEmaHtml(texto)}
          </div>
          ${htmlSeccionesOverviewEma(d.overview)}
          <p class="muted sku-note ema-ind-links src-links">
            ${d.pdf_es ? linkFuenteChip(d.pdf_es, "Medicine overview (ES · PDF)", "fda") : ""}
            ${d.url ? linkFuenteChip(d.url, "Ficha EPAR", "ema") : ""}
          </p>
        </div>
      </details>`;
  }).join("");
}

function formatearIndicacionEmaHtml(texto) {
  let raw = String(texto || "").trim();
  if (!raw) return `<p class="muted">—</p>`;
  if (/please refer to the product information/i.test(raw)
    || /consulte (el|la) (documento|información)/i.test(raw)) {
    return `<p class="ema-ind-note">${escapeHtml(raw)}</p>`;
  }

  // Marcar encabezados de área solo si van seguidos de un nombre propio (marca u otra área).
  const marks = [];
  for (const h of EMA_IND_HEADERS) {
    const re = new RegExp(`(${escapeRegExp(h)})(?=\\s+[A-ZÁÉÍÓÚÜ][A-Za-zÁÉÍÓÚáéíóúüñ0-9-]{2,}\\b)`, "gi");
    let m;
    while ((m = re.exec(raw)) !== null) {
      const start = m.index;
      if (start > 0) {
        const prev = raw[start - 1];
        if (!/[\s.!?…]/.test(prev)) continue;
      }
      marks.push({ start, end: start + m[0].length, text: m[0] });
    }
  }
  marks.sort((a, b) => a.start - b.start || (b.end - b.start) - (a.end - a.start));
  const picked = [];
  for (const m of marks) {
    if (picked.some((p) => !(m.end <= p.start || m.start >= p.end))) continue;
    picked.push(m);
  }
  picked.sort((a, b) => b.start - a.start);
  for (const m of picked) {
    const prefix = m.start === 0 ? "" : "\n\n";
    raw = `${raw.slice(0, m.start)}${prefix}§§${m.text}§§\n${raw.slice(m.end)}`;
  }
  raw = raw.replace(/^\n+/, "");

  // Separar “is indicated for:” / “está indicado para:”
  raw = raw.replace(
    /\b((?:is|are)\s+indicated\s+for|est[aá]\s+indicad[oa]s?\s+para)\s*:?\s*/gi,
    "\n«IND»\n",
  );

  // Cláusulas “the treatment of / el tratamiento de” → bullets
  raw = raw.replace(
    /(?:^|[.\n])\s*((?:el\s+tratamiento\s+de|the\s+treatment\s+of))\s+/gi,
    "\n• ",
  );

  const blocks = raw.split(/\n\n+/).map((b) => b.trim()).filter(Boolean);
  const parts = [];
  for (const block of blocks) {
    const titleMatch = block.match(/^§§(.+?)§§\s*([\s\S]*)$/);
    let title = "";
    let body = block;
    if (titleMatch) {
      title = titleMatch[1].trim();
      body = (titleMatch[2] || "").trim();
    }
    if (title) {
      parts.push(`<h4 class="ema-ind-h">${escapeHtml(title)}</h4>`);
    }
    if (!body) continue;

    const lines = body.split("\n").map((l) => l.trim()).filter(Boolean);
    let intro = [];
    let bullets = [];
    const flushIntro = () => {
      if (!intro.length) return;
      parts.push(`<p class="ema-ind-p">${escapeHtml(intro.join(" "))}</p>`);
      intro = [];
    };
    const flushBullets = () => {
      if (!bullets.length) return;
      parts.push(`<ul class="ema-ind-ul">${bullets.map((b) => `<li>${escapeHtml(b)}</li>`).join("")}</ul>`);
      bullets = [];
    };
    for (const line of lines) {
      if (line === "«IND»") {
        flushIntro();
        flushBullets();
        parts.push(`<p class="ema-ind-lead">Está indicado para:</p>`);
        continue;
      }
      if (line.startsWith("• ")) {
        flushIntro();
        let item = line.slice(2).trim();
        item = item.replace(/\s+/g, " ").replace(/\.\s*$/, "");
        if (item) bullets.push(item);
        continue;
      }
      flushBullets();
      intro.push(line.replace(/\s+/g, " "));
    }
    flushIntro();
    flushBullets();
  }
  return `<div class="ema-ind-rich">${parts.join("") || `<p class="ema-ind-p">${escapeHtml(String(texto).replace(/\s+/g, " "))}</p>`}</div>`;
}

function pareceInglesUi(texto) {
  const t = String(texto || "");
  if (t.length < 28) return false;
  return /\b(is indicated for|are indicated for|the treatment of|in combination with|Please refer to|INDICATIONS AND USAGE)\b/i.test(t);
}

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Homologa MAYÚSCULAS forzadas a Title Case; deja el resto igual. */
function textoUi(s) {
  const t = String(s ?? "").replace(/\s+/g, " ").trim();
  if (!t || t === "—") return t;
  const letters = t.replace(/[^A-Za-zÀ-ÿ]/g, "");
  if (letters.length >= 4) {
    const upper = (letters.match(/[A-ZÁÉÍÓÚÜÑ]/g) || []).length;
    if (upper / letters.length >= 0.7) {
      return t
        .toLocaleLowerCase("es")
        .replace(/(^|[^\p{L}])(\p{L})/gu, (_, sep, ch) => sep + ch.toLocaleUpperCase("es"));
    }
  }
  return t;
}

function cellTxt(s, fallback = "—") {
  const t = textoUi(s);
  return escapeHtml(t || fallback);
}

function money(n, kind = "usd") {
  if (n == null || Number.isNaN(Number(n))) return `<span class="empty">—</span>`;
  if (kind === "usd") {
    const num = Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return `<span class="money"><span class="money-cur">USD</span> ${num}</span>`;
  }
  return `<span class="money">${dop.format(n)}</span>`;
}

function ventaBcrd() {
  const row = (D.tasas || []).find((t) => {
    const blob = Object.values(t).map((v) => String(v || "")).join(" ").toLowerCase();
    return blob.includes("dominicana") || (blob.includes("dop") && blob.includes("bcrd"));
  });
  if (!row) return null;
  const v = row["USD en moneda local"] ?? row.Valor;
  return v == null || v === "" ? null : Number(v);
}

function mapaTasas() {
  const out = {};
  for (const t of D.tasas || []) {
    const etiqueta = String(campo(t, "país", "pais", "moneda") || "");
    const m = etiqueta.match(/\(([A-Z]{3})\)/);
    if (!m) continue;
    const v = t["USD en moneda local"] ?? t.Valor;
    if (v == null || v === "") continue;
    out[m[1]] = Number(v);
  }
  return out;
}

function aUsd(precio, moneda) {
  if (precio == null || precio === "") return null;
  const n = Number(precio);
  if (Number.isNaN(n)) return null;
  const m = String(moneda || "").toUpperCase();
  if (m === "USD") return n;
  const t = mapaTasas()[m];
  if (!t) return null;
  return n / t;
}

function aDop(precioUsd) {
  if (precioUsd == null) return null;
  const t = mapaTasas().DOP;
  return t ? precioUsd * t : null;
}

function paisUi(p) {
  const extra = PAIS_UI[p.id] || {};
  return {
    id: p.id,
    flag: extra.flag || "🏳️",
    corto: extra.corto || p.corto,
    nombre: extra.nombre || p.nombre,
    full: extra.full || p.nombre,
  };
}

const FLAG_SVG = new Set(["do", "br", "mx", "ar", "co", "pe", "cl", "cr", "ec", "hn", "gt", "ni", "pa", "uy", "sv"]);

function flagImg(id, cls) {
  if (!FLAG_SVG.has(id)) {
    const emoji = (PAIS_UI[id] && PAIS_UI[id].flag) || "🏳️";
    return `<span class="${cls} is-emoji">${emoji}</span>`;
  }
  return `<img class="${cls}" src="/flags/${id}.svg" alt="" width="48" height="36" />`;
}

function paisesVivos() {
  const ids = new Set();
  for (const f of TABLA) {
    const id = idPaisPorTexto(f.pais);
    if (paisActivo(id)) ids.add(id);
  }
  return ids;
}

/** Países con dato en snapshot, historial o catálogo (para tablero / panorama). */
function paisesIdsPanorama() {
  const ids = new Set(paisesVivos());
  for (const p of (D.paises || [])) {
    if (paisActivo(p.id)) ids.add(p.id);
  }
  for (const row of (TEND_CATALOG.indicadores?.por_pais || [])) {
    const id = idPaisPorTexto(row.pais);
    if (paisActivo(id)) ids.add(id);
  }
  return ids;
}

function paisesUi() {
  const orden = ["do", "br", "mx", "ec", "hn", "gt", "ni", "cr", "pa", "ar", "co", "pe", "cl", "uy", "sv"];
  const vivos = paisesVivos();
  const ids = (vivos.size ? [...orden.filter((id) => vivos.has(id))] : (D.paises || []).map((p) => p.id))
    .filter(paisActivo);
  return ids.map((id) => {
    const fromData = (D.paises || []).find((p) => p.id === id) || { id, nombre: PAIS_UI[id]?.full || id, corto: (id || "").toUpperCase() };
    return paisUi(fromData);
  });
}

/** Tablero: todos los países del catálogo + historial, aunque el snapshot de hoy no tenga filas. */
function paisesUiPanorama() {
  const orden = ["do", "br", "mx", "ec", "hn", "gt", "ni", "cr", "pa", "ar", "co", "pe", "cl", "uy", "sv"];
  const ids = [...orden.filter((id) => paisesIdsPanorama().has(id))];
  return ids.map((id) => {
    const fromData = (D.paises || []).find((p) => p.id === id) || { id, nombre: PAIS_UI[id]?.full || id, corto: (id || "").toUpperCase() };
    return paisUi(fromData);
  });
}

function idPaisPorTexto(nombre) {
  const s = String(nombre || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
  const mapa = [
    ["dominicana", "do"],
    ["dominican", "do"],
    ["argentin", "ar"],
    ["brasil", "br"],
    ["brazil", "br"],
    ["colombia", "co"],
    ["peru", "pe"],
    ["chile", "cl"],
    ["mexico", "mx"],
    ["méxico", "mx"],
    ["costa rica", "cr"],
    ["costarica", "cr"],
    ["ecuador", "ec"],
    ["honduras", "hn"],
    ["guatemala", "gt"],
    ["nicaragua", "ni"],
    ["panama", "pa"],
    ["panamá", "pa"],
    ["uruguay", "uy"],
    ["el salvador", "sv"],
    ["salvador", "sv"],
  ];
  for (const [pista, id] of mapa) {
    if (s.includes(pista)) return id;
  }
  return null;
}

function metaPaisPorTexto(nombre) {
  const id = idPaisPorTexto(nombre);
  if (id) return PAIS_UI[id];
  return { flag: "🏳️", nombre: String(nombre || "—"), full: String(nombre || "—"), corto: "" };
}

function monedaDeEtiqueta(texto) {
  const m = String(texto || "").match(/\(([A-Z]{3})\)/);
  return m ? m[1] : "";
}

function esFuenteCambio(f) {
  const pais = String(campo(f, "país", "pais")).toLowerCase();
  return pais.includes("(fx)") || pais.includes("cambio") || pais.includes(" fx");
}

function mejorPaisId(row) {
  if (!row?.par_comparable) return null;
  let best = null;
  let val = Infinity;
  for (const p of paisesUi()) {
    const n = row.paises[p.id]?.min_usd;
    if (n != null && Number(n) < val) {
      val = Number(n);
      best = p.id;
    }
  }
  return best;
}

function sortMark(key) {
  if (state.sort !== key) return `<span class="ord">↕</span>`;
  return `<span class="ord">${state.dir === 1 ? "↑" : "↓"}</span>`;
}

function thSortClass(key) {
  return state.sort === key ? "sortable is-sorted" : "sortable";
}

function filasVivas() {
  return TABLA.filter((f) => {
    if (!filaPaisActivo(f)) return false;
    if (!filaOfertable(f)) return false;
    if (state.conc !== "todas" && concentracionClave(f) !== state.conc) return false;
    if (state.pres !== "todas" && presentacionClave(f) !== state.pres) return false;
    if (state.alcance !== "todos" && alcanceDe(f) !== state.alcance) return false;
    return true;
  });
}

/** Con precio numérico > 0 (sin filtrar agotado; alineado con historial de tendencias). */
function filaConPrecio(f) {
  if (!f) return false;
  const precio = f.precio;
  return precio != null && precio !== "" && Number(precio) > 0 && !Number.isNaN(Number(precio));
}

/** Con precio usable y no marcado como agotado / sin stock. */
function filaOfertable(f) {
  if (!f) return false;
  const precio = f.precio;
  if (precio == null || precio === "" || Number(precio) <= 0 || Number.isNaN(Number(precio))) return false;
  const d = String(f.disponibilidad || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
  if (!d) return true;
  if (d.includes("agotado") || d.includes("sin stock") || d.includes("out of stock") || d.includes("outofstock")) {
    return false;
  }
  return true;
}

function filasTablaBase() {
  return TABLA.filter((f) => filaPaisActivo(f) && filaOfertable(f));
}

function opcionesCampo(campoNombre) {
  const set = new Set();
  for (const f of TABLA) {
    let v = "";
    if (campoNombre === "concentracion") v = concentracionClave(f);
    else if (campoNombre === "presentacion") v = presentacionClave(f);
    else if (campoNombre === "alcance") v = alcanceDe(f);
    else v = String(f[campoNombre] || "").trim();
    if (v && v !== "desconocido") set.add(v);
  }
  return [...set].sort((a, b) => a.localeCompare(b, "es", { numeric: true }));
}

function asciiNorm(s) {
  return String(s || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/,/g, ".")
    .replace(/\s+/g, " ")
    .trim();
}

function stripNum(n) {
  const x = Number(n);
  if (Number.isNaN(x)) return String(n);
  if (Math.abs(x - Math.round(x)) < 1e-9) return String(Math.round(x));
  return String(x);
}

function normConcentracion(s) {
  const t = asciiNorm(s);
  if (!t) return "";
  const m = t.match(/(\d+(?:\.\d+)?)\s*(mg|mcg|ug|µg|ui|iu|g)(?:\s*\/\s*(\d+(?:\.\d+)?)\s*(ml|mg))?/);
  if (!m) return "";
  const uni = m[2].replace("ug", "mcg").replace("µg", "mcg").replace("iu", "ui");
  if (m[3]) return `${stripNum(m[1])} ${uni}/${stripNum(m[3])} ${m[4]}`;
  return `${stripNum(m[1])} ${uni}`;
}

function concentracionClave(f) {
  const cant = String(f.cantidad_concentracion || "").trim();
  const uni = String(f.unidad_concentracion || "").trim();
  if (cant && uni) return `${cant} ${uni}`;
  return normConcentracion(f.concentracion) || normConcentracion(f.nombre_comercial) || "";
}

function alcanceDe(f) {
  const a = String(f.alcance_presentacion || "").trim().toLowerCase();
  if (a && a !== "desconocido") return a;
  // Respaldo si la API aún no trae el campo estructurado.
  const blob = asciiNorm(`${f.presentacion || ""} ${f.nombre_comercial || ""}`);
  if (/\bkit\b/.test(blob)) return "kit";
  if (/\bcaja\b/.test(blob)) return "caja";
  const pack = blob.match(/\b(?:x|c)\s*(\d+)(?!\s*(?:ml|mg|mcg|ug|g|ui|iu)\b)/);
  if (pack) {
    const n = Number(pack[1]);
    if (Number.isFinite(n) && n > 1) return "lote";
    if (n === 1) return "unidad";
  }
  if (/\b(ampolla|vial|jeringa|pluma|frasco|comprimido|capsula|tableta)\b/.test(blob)) return "unidad";
  return a || "desconocido";
}

function cantidadPresentacionDe(f) {
  const raw = String(f.cantidad_presentacion || "").trim();
  if (raw) return stripNum(raw);
  const fromPres = presentacionComparable(f);
  const m = String(fromPres).match(/\bx\s*(\d+)\b/i);
  return m ? m[1] : "";
}

function tipoPresentacionDe(f) {
  let tipo = String(f.tipo_presentacion || "").trim();
  if (!tipo) {
    const fromPres = presentacionComparable(f);
    if (!fromPres) return "";
    tipo = fromPres.replace(/\s*x\s*\d+\s*$/i, "").trim();
  }
  const n = asciiNorm(tipo);
  if (n.includes("tableta") || n === "tabs" || n === "tab") return "Comprimidos";
  if (n.includes("comprimido") || n === "comp") return "Comprimidos";
  if (n.includes("capsula") || n === "caps" || n === "cap") return "Cápsulas";
  if (n.includes("jeringa")) return "Jeringa prellenada";
  if (n.includes("ampolla") || n.includes("vial") || n.includes("frasco")) return "Ampolla";
  if (n.includes("polvo")) return "Polvo";
  return tipo;
}

/* --- Equivalencia farmacológica (ver scrapper/equivalencia.py) --- */
const FORMAS_EQUIV = {
  comprimidos: "comprimido",
  comprimido: "comprimido",
  comp: "comprimido",
  tabletas: "comprimido",
  tableta: "comprimido",
  tabs: "comprimido",
  tab: "comprimido",
  capsulas: "capsula",
  capsula: "capsula",
  caps: "capsula",
  cap: "capsula",
  "solucion inyectable": "inyectable",
  inyectable: "inyectable",
  ampolla: "inyectable",
  vial: "inyectable",
  "frasco ampolla": "inyectable",
  "frasco-ampolla": "inyectable",
  "jeringa prellenada": "inyectable",
  jeringa: "inyectable",
  pluma: "inyectable",
  "polvo liofilizado": "polvo_liofilizado",
  polvo: "polvo",
};

function formaCanonica(tipo, nombre = "") {
  const blob = `${asciiNorm(tipo)} ${asciiNorm(nombre)}`;
  if (/\b(revestid|recubiert)/.test(blob)) return "comprimido_revestido";
  const t = asciiNorm(tipo);
  if (!t) return null;
  if (FORMAS_EQUIV[t]) return FORMAS_EQUIV[t];
  for (const [pista, canon] of Object.entries(FORMAS_EQUIV)) {
    if (t.includes(pista)) return canon;
  }
  return t || null;
}

/** Agrupa variantes farmacéuticamente equivalentes para el match del comparador. */
function formaComparacion(forma) {
  if (forma === "comprimido_revestido") return "comprimido";
  return forma;
}

function etiquetaFormaComparacion(forma) {
  const map = {
    comprimido: "comprimido (± recubierto)",
    capsula: "cápsula",
    tableta: "comprimido (± recubierto)",
  };
  return map[forma] || String(forma || "").replace(/_/g, " ");
}

function precioUsdUnidadDe(f, usdVal = null) {
  const usd = usdVal != null ? usdVal : aUsd(f?.precio, f?.moneda);
  if (usd == null) return null;
  const cant = cantidadUnidadesDe(f);
  if (!cant || cant <= 0) return null;
  return usd / cant;
}

function abreviarTexto(s, max = 32) {
  const t = String(s || "").trim();
  if (!t) return "";
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}

function liberacionDe(f) {
  const blob = asciiNorm(`${f.nombre_comercial || ""} ${f.presentacion || ""} ${f.tipo_presentacion || ""}`);
  if (/\b(xr|sr|cr|er|mr|pr|la|lp|retard|prolongad)/.test(blob)) return "modificada";
  return "inmediata";
}

function viaDe(f) {
  const blob = asciiNorm(`${f.nombre_comercial || ""} ${f.presentacion || ""} ${f.tipo_presentacion || ""}`);
  if (/\b(inyect|ampolla|vial|jeringa|pluma|solucion inyect|subcut|intraven)/.test(blob)) return "parenteral";
  if (/\b(unguento|pomada|crema|gel|topico|oftalm|nasal)/.test(blob)) return "topica";
  if (/\b(comprimid|tableta|capsula|caplet|oral|suspension oral)/.test(blob)) return "oral";
  return null;
}

function cantidadUnidadesDe(f) {
  const raw = String(f.cantidad_presentacion || "").trim();
  if (raw) {
    const n = Number(raw.replace(",", "."));
    if (Number.isFinite(n) && n > 0) return n;
  }
  const alc = alcanceDe(f);
  if (alc === "unidad" || esPrecioUnidad(f)) return 1;
  return null;
}

function perfilDeFila(f) {
  if (esDatoAmbiguo(f)) return null;
  if (f.calidad && f.calidad !== "ok") {
    return { reviewRequired: true, incompleto: true };
  }
  const conc = concentracionClave(f);
  const formaRaw = formaCanonica(tipoPresentacionDe(f), f.nombre_comercial);
  const forma = formaComparacion(formaRaw);
  const cant = cantidadUnidadesDe(f);
  const lib = liberacionDe(f);
  const via = viaDe(f) || "?";
  const incompleto = !conc || !forma || !cant;
  const claveMedicina = incompleto ? null : `${f.n_lista}|${conc}|${forma}|${lib}|${via}`;
  const clavePresentacion = claveMedicina && cant ? `${claveMedicina}|${cant}` : null;
  return {
    n_lista: f.n_lista,
    concentracion: conc,
    forma,
    formaRaw,
    cantidad: cant,
    liberacion: lib,
    via,
    marca: String(f.nombre_comercial || "").split(/\s+/)[0] || null,
    laboratorio: f.laboratorio || null,
    incompleto,
    reviewRequired: incompleto,
    claveMedicina,
    clavePresentacion,
  };
}

function presentacionClave(f) {
  const tipo = tipoPresentacionDe(f);
  const cant = cantidadPresentacionDe(f);
  const alcance = alcanceDe(f);
  if (!tipo && !cant) return presentacionComparable(f) || String(f.presentacion || "").trim();
  const base = cant ? `${tipo || "Presentación"} x ${cant}` : (tipo || "Presentación");
  return alcance && alcance !== "desconocido" ? `${base} · ${alcance}` : base;
}

function etiquetaAlcance(alcance) {
  const map = {
    unidad: "unidad",
    lote: "lote / paquete",
    caja: "caja",
    kit: "kit",
    desconocido: "sin alcance",
  };
  return map[alcance] || alcance;
}

function normPresentacion(s) {
  let t = asciiNorm(s).replace(/\(detalle\)/g, " ").replace(/\*+/g, " ").replace(/\s+/g, " ").trim();
  if (!t) return "";
  t = t.replace(/\btabletas?\b/g, "comprimidos");
  t = t.replace(/\btabs?\b/g, "comprimidos");
  t = t.replace(/\bcomp\b/g, "comprimidos");
  t = t.replace(/\bcaps?\b/g, "capsulas");
  t = t.replace(/\bcapsulas?\b/g, "capsulas");
  t = t.replace(/\bjeringa(?:s)?(?:\s+prellenada|\s+precargada)?\b/g, "jeringa");
  t = t.replace(/\bseringas?\b/g, "jeringa");
  t = t.replace(/\bfrasco[- ]ampolla\b/g, "ampolla");
  t = t.replace(/\bfrasco[- ]ampula\b/g, "ampolla");
  t = t.replace(/\bampollas?\b/g, "ampolla");
  t = t.replace(/\bviales?\b/g, "ampolla");
  t = t.replace(/\binyectable\b/g, "ampolla");
  t = t.replace(/\bcanetas?\b/g, "pluma");
  // No tomar "x 100 ml" como cantidad de empaque.
  const pack = t.match(/\b(?:x|c)\s*(\d+)(?!\s*(?:ml|mg|mcg|ug|g|ui|iu)\b)/);
  let n = pack ? pack[1] : "";
  let forma = t.replace(/\s*(?:x|c)\s*\d+(?!\s*(?:ml|mg|mcg|ug|g|ui|iu)\b)\b/g, "").trim();
  if (forma.includes("comprimido")) forma = "Comprimidos";
  else if (forma.includes("capsula")) forma = "Cápsulas";
  else if (forma.includes("jeringa")) forma = "Jeringa";
  else if (forma.includes("ampolla")) forma = "Ampolla";
  else if (forma.includes("vial")) forma = "Ampolla";
  else if (forma.includes("frasco")) forma = "Ampolla";
  else if (forma.includes("pluma")) forma = "Pluma";
  else if (forma.includes("solucion")) forma = "Solución inyectable";
  else if (!forma) return "";
  else forma = forma.charAt(0).toUpperCase() + forma.slice(1);
  if (!n && ["Jeringa", "Ampolla", "Pluma"].includes(forma)) {
    n = "1";
  }
  return n ? `${forma} x ${n}` : forma;
}

function esPrecioUnidad(f) {
  // PVP al detalle / no caja (slug …det, ***DET, observación).
  const blob = `${f.observacion || ""} ${f.presentacion || ""} ${f.nombre_comercial || ""} ${f.fuente_url || ""} ${f.id_producto_farmacia || ""} ${f.sku || ""}`.toLowerCase();
  if (blob.includes("detalle") || blob.includes("no caja") || blob.includes("por unidad") || blob.includes("***det")) return true;
  if (String(f.id_producto_farmacia || "").toLowerCase().endsWith("det")) return true;
  if (String(f.fuente_url || "").toLowerCase().replace(/\/+$/, "").endsWith("det")) return true;
  if (/(^|[^a-z0-9])[a-z0-9_-]*det(\b|\/|$)/i.test(blob)) return true;
  return false;
}

function esDatoAmbiguo(f) {
  const pres = asciiNorm(f.presentacion);
  const nombre = asciiNorm(f.nombre_comercial);
  if (!pres && !nombre) return false;
  const genericoSolo = (txt) =>
    /\b(frasco|caja|unidad|tratamiento)\b/.test(txt) &&
    !/\b(tableta|tabletas|tab|tabs|comp|comprimido|comprimidos|capsula|capsulas|cap|caps)\b/.test(txt);
  const oralConPack = (txt) =>
    /\b(tableta|tabletas|tab|tabs|comp|comprimido|comprimidos|capsula|capsulas|cap|caps)\b/.test(txt) &&
    /\b(?:x|c)?\s*\d+\b/.test(txt);

  return (genericoSolo(pres) && oralConPack(nombre)) || (genericoSolo(nombre) && oralConPack(pres));
}

let _aliasesMedCache = null;
function aliasesMedicamento(n) {
  if (!_aliasesMedCache) {
    _aliasesMedCache = new Map(
      (D?.medicamentos || []).map((m) => [Number(m.n), Array.isArray(m.aliases) ? m.aliases : []])
    );
  }
  return _aliasesMedCache.get(Number(n)) || [];
}

function tokenPrincipioActivo(f) {
  const raw = asciiNorm(f.medicamento_lista || "");
  const parts = raw.split(/\s+/).filter(Boolean);
  return parts[parts.length - 1] || raw;
}

/** Marca comercial de referencia (p. ej. Casodex) — no mezclar con genéricos en el comparativo. */
function esMarcaComercialReferencia(f) {
  const aliases = aliasesMedicamento(f.n_lista);
  if (!aliases.length) return false;
  const nombre = asciiNorm(f.nombre_comercial || "");
  const tokens = nombre.split(/\s+/).filter(Boolean);
  if (!tokens.length) return false;
  if (/\b(generico|generica|equivalente|similar|biosimilar)\b/.test(nombre)) return false;
  const principio = tokenPrincipioActivo(f);
  for (const a of aliases) {
    const an = asciiNorm(a);
    if (!an || an.length < 4) continue;
    if (principio && (an === principio || principio.includes(an) || an.includes(principio))) continue;
    if (tokens[0] === an || tokens.slice(0, 2).join(" ").startsWith(`${an} `)) return true;
  }
  return false;
}

/** Combinación de dos principios (p. ej. "50 mg + otro activo"). */
function esComboMultiprincipio(f) {
  const n = String(f.nombre_comercial || "");
  const m = n.match(/^(.+?)\s*\+\s*(.+)$/i);
  if (!m) return false;
  const izq = asciiNorm(m[1]);
  const der = asciiNorm(m[2]);
  const principio = tokenPrincipioActivo(f);
  if (principio && der.includes(principio)) return false;
  return /\d+\s*mg/.test(izq) && /\d+\s*mg/.test(der);
}

function motivoExclusionComparable(f) {
  if (esMarcaComercialReferencia(f)) return "marca de referencia";
  if (esComboMultiprincipio(f)) return "combinación de principios";
  return "";
}

function mediana(nums) {
  const arr = nums.filter((v) => v != null && Number.isFinite(v)).sort((a, b) => a - b);
  if (!arr.length) return null;
  const mid = Math.floor(arr.length / 2);
  return arr.length % 2 ? arr[mid] : (arr[mid - 1] + arr[mid]) / 2;
}

function refinarFilasComparables(filas) {
  let pool = filas.filter((f) => !motivoExclusionComparable(f));
  if (!pool.length) pool = [...filas];
  const pus = pool.map((f) => precioUsdUnidadDe(f)).filter((v) => v != null && v > 0);
  if (pus.length >= 5) {
    const med = mediana(pus);
    if (med != null && med > 0) {
      const hi = med * 2.5;
      const lo = med / 4;
      const filtrado = pool.filter((f) => {
        const pu = precioUsdUnidadDe(f);
        if (pu == null) return true;
        if (pu > hi) return false;
        const cant = cantidadUnidadesDe(f);
        if (pu < lo && cant != null && cant >= 10) return false;
        return true;
      });
      if (filtrado.length >= 2) pool = filtrado;
    }
  }
  return pool;
}

function filasEnClave(filas, clave) {
  return filas.filter((f) => claveDeFila(f) === clave);
}

function filasComparablesClave(filas, clave) {
  return refinarFilasComparables(filasEnClave(filas, clave));
}

function elegirFilaRepresentativaPais(filasPais) {
  const ordenadas = filasPais
    .map((f) => ({ f, u: aUsd(f.precio, f.moneda) }))
    .filter((x) => x.u != null)
    .sort((a, b) => a.u - b.u);
  if (!ordenadas.length) return filasPais[0] || null;
  if (ordenadas.length <= 2) return ordenadas[0].f;
  const mid = Math.floor(ordenadas.length / 2);
  return ordenadas[mid].f;
}

function aplicarFilaACeldaComparativo(cel, f) {
  const usdVal = aUsd(f.precio, f.moneda);
  if (usdVal == null) return;
  const cant = cantidadUnidadesDe(f);
  cel.min_usd = usdVal;
  cel.min_dop = aDop(usdVal);
  cel.min_usd_unidad = precioUsdUnidadDe(f, usdVal);
  cel.cantidad = cant;
  cel.ejemplo = f.nombre_comercial || f.producto || "";
  cel.tipo = f.farmacia;
  cel.laboratorio = f.laboratorio;
  cel.fuente = fuenteUrlVisible(f);
  cel.fecha = f.fecha_dato;
}

function presentacionComparable(f) {
  const desdePresentacion = normPresentacion(f.presentacion);
  const desdeNombre = normPresentacion(f.nombre_comercial);
  if (desdePresentacion && desdeNombre) {
    const pTienePack = /\bx\s*\d+\b/i.test(desdePresentacion);
    const nTienePack = /\bx\s*\d+\b/i.test(desdeNombre);
    if (nTienePack && !pTienePack) return desdeNombre;
    if (pTienePack && !nTienePack) return desdePresentacion;
    if (desdeNombre.length > desdePresentacion.length) return desdeNombre;
    return desdePresentacion;
  }
  return desdePresentacion || desdeNombre || "";
}

function claveDeFila(f) {
  const p = perfilDeFila(f);
  if (!p || p.reviewRequired) return null;
  if (esPrecioUnidad(f) && p.claveMedicina) {
    return `${p.claveMedicina}|1`;
  }
  return p.clavePresentacion;
}

function etiquetaClave(clave) {
  if (!clave) return "";
  const parts = String(clave).split("|");
  if (parts.length < 5) {
    const legacy = String(clave).split("||");
    if (legacy.length >= 3) {
      const [c, tipo, cant, alcance] = legacy;
      const base = cant ? `${c} · ${tipo} x ${cant}` : `${c} · ${tipo}`;
      return alcance ? `${base} · ${etiquetaAlcance(alcance)}` : base;
    }
    return clave;
  }
  const cant = parts[parts.length - 1];
  const conc = parts[1];
  const forma = parts[2];
  const lib = parts[3];
  let base = `${conc} · ${etiquetaFormaComparacion(forma)} x ${cant}`;
  if (lib === "modificada") base += " · liberación modificada";
  return base;
}

function dispersionComparativo(row) {
  const precios = paisesUi()
    .map((p) => row.paises?.[p.id]?.min_usd)
    .filter((v) => v != null);
  if (precios.length < 2) return { ratio: null, alerta: false };
  const pmin = Math.min(...precios);
  const pmax = Math.max(...precios);
  const ratio = pmin > 0 ? pmax / pmin : null;
  return { ratio, alerta: ratio != null && ratio >= 3 };
}

function htmlCeldaComparativo(row, paisMeta, bestId) {
  const cel = row.paises?.[paisMeta.id];
  const v = cel?.min_usd;
  const cls = v == null ? "is-void" : (paisMeta.id === bestId ? "is-best" : "");
  if (v == null) {
    return `<td class="td-precio ${cls}" title="${escapeHtml(paisMeta.full)}: sin la misma concentración/presentación"><span class="empty">—</span></td>`;
  }
  const pu = cel.min_usd_unidad;
  const cant = cel.cantidad;
  const prod = cel.ejemplo || "";
  const farm = cel.tipo || cel.farmacia || "";
  const title = [
    `${paisMeta.full}: ${usd.format(v)}`,
    pu != null && cant > 1 ? `${usd.format(pu)} por unidad (${cant} uds.)` : "",
    prod ? `Producto: ${prod}` : "",
    farm ? `Farmacia: ${farm}` : "",
    paisMeta.id === bestId ? "Más barato en este grupo" : "",
  ].filter(Boolean).join(" · ");
  return `<td class="td-precio td-precio--comp ${cls}" title="${escapeHtml(title)}">
    <div class="comp-price-main">${money(v)}</div>
    ${pu != null && cant > 1 ? `<div class="comp-pu muted">${money(pu)}/ud</div>` : ""}
  </td>`;
}

function elegirClave(filas) {
  const votos = new Map();
  for (const f of filas) {
    const k = claveDeFila(f);
    if (!k) continue;
    const id = idPaisPorTexto(f.pais);
    if (!id) continue;
    if (!votos.has(k)) votos.set(k, { paises: new Set(), n: 0 });
    votos.get(k).paises.add(id);
    votos.get(k).n += 1;
  }
  let mejor = null;
  let score = [-1, -1];
  for (const [k, v] of votos) {
    const s = [v.paises.size, v.n];
    if (s[0] > score[0] || (s[0] === score[0] && s[1] > score[1])) {
      score = s;
      mejor = k;
    }
  }
  return { clave: mejor, paises: score[0] };
}

function gruposComparables(filas) {
  const grupos = new Map();
  for (const f of filas) {
    const clave = claveDeFila(f);
    if (!clave) continue;
    const paisId = idPaisPorTexto(f.pais);
    if (!grupos.has(clave)) grupos.set(clave, { clave, filas: [], paises: new Set() });
    const g = grupos.get(clave);
    g.filas.push(f);
    if (paisId) g.paises.add(paisId);
  }
  return [...grupos.values()]
    .filter((g) => g.paises.size >= 2)
    .sort((a, b) => (b.paises.size - a.paises.size) || (b.filas.length - a.filas.length) || a.clave.localeCompare(b.clave, "es"));
}

function overlayComparativo() {
  if (!BASE_COMP) BASE_COMP = JSON.parse(JSON.stringify(D.comparativo || []));
  const rows = JSON.parse(JSON.stringify(BASE_COMP));
  for (const r of rows) {
    r.paises = r.paises || {};
    for (const p of paisesUi()) {
      r.paises[p.id] = {
        hits: 0,
        min_usd: null,
        med_usd: null,
        min_dop: null,
        ejemplo: null,
        tipo: null,
        fuente: null,
        fecha: null,
        laboratorio: null,
        nombre: p.full,
      };
    }
    r.paises_con_dato = 0;
    r.min_usd = null;
    r.min_dop = null;
    r.presentacion_comparada = null;
    r.clave_comparada = null;
    r.par_comparable = false;
  }
  const vivas = filasVivas();
  const porMed = new Map();
  for (const f of vivas) {
    if (!porMed.has(f.n_lista)) porMed.set(f.n_lista, []);
    porMed.get(f.n_lista).push(f);
  }
  for (const r of rows) {
    const filas = porMed.get(r.n) || [];
    const elec = elegirClave(filas);
    r.clave_comparada = elec.clave;
    r.par_comparable = Boolean(elec.clave && elec.paises >= 2);
    r.presentacion_comparada = elec.clave
      ? etiquetaClave(elec.clave)
      : (filas.length ? "Sin concentración/presentación comparable" : "");
    if (!elec.clave) continue;
    const pool = filasComparablesClave(filas, elec.clave);
    const porPais = new Map();
    for (const f of pool) {
      const id = idPaisPorTexto(f.pais);
      if (!id) continue;
      if (!porPais.has(id)) porPais.set(id, []);
      porPais.get(id).push(f);
    }
    for (const [id, fps] of porPais) {
      const f = elegirFilaRepresentativaPais(fps);
      if (!f || !r.paises[id]) continue;
      const cel = r.paises[id];
      cel.hits = fps.length;
      aplicarFilaACeldaComparativo(cel, f);
    }
    let min = Infinity;
    let hitsPais = 0;
    for (const p of paisesUi()) {
      const n = r.paises[p.id]?.min_usd;
      if (n != null) {
        hitsPais += 1;
        if (n < min) min = n;
      }
    }
    r.paises_con_dato = hitsPais;
    const disp = dispersionComparativo(r);
    r.ratio_dispersion = disp.ratio;
    r.alerta_dispersion = disp.alerta;
    if (r.par_comparable) {
      r.min_usd = min === Infinity ? null : min;
      r.min_dop = aDop(r.min_usd);
    } else {
      r.min_usd = null;
      r.min_dop = null;
    }
  }
  return rows;
}

function filtrarComparativo() {
  const q = state.q.trim().toLowerCase();
  let rows = overlayComparativo();
  if (state.programa === "fomac") rows = rows.filter((r) => String(r.programa).includes("FOMAC"));
  else if (state.programa !== "todos") rows = rows.filter((r) => r.programa === state.programa);
  if (state.conDato === "con") rows = rows.filter((r) => r.par_comparable);
  else if (state.conDato === "sin") rows = rows.filter((r) => !r.par_comparable);
  if (state.paisFiltro !== "todos") {
    rows = rows.filter((r) => (r.paises[state.paisFiltro]?.min_usd ?? null) != null);
  }
  if (state.conc !== "todas" || state.pres !== "todas" || state.alcance !== "todos") {
    rows = rows.filter((r) => r.paises_con_dato > 0);
  }
  if (q) {
    rows = rows.filter((r) => {
      const extra = filasTablaBase().filter((f) => f.n_lista === r.n).map((f) =>
        [f.nombre_comercial, f.concentracion, f.presentacion, f.farmacia].join(" ")
      );
      const blob = [
        r.medicamento,
        r.programa,
        r.presentacion_comparada || "",
        ...extra,
        ...Object.entries(r.paises).flatMap(([id, p]) => [
          p.ejemplo || "",
          p.nombre || "",
          (PAIS_UI[id] || {}).nombre || "",
          (PAIS_UI[id] || {}).full || "",
        ]),
      ].join(" ").toLowerCase();
      return blob.includes(q);
    });
  }
  const pri = { FOMAC: 0, "FOMAC*": 1, "DAMAC-FOMAC": 2, DAMAC: 3 };
  rows.sort((a, b) => {
    const key = state.sort;
    let va;
    let vb;
    if (key === "programa") {
      va = pri[a.programa] ?? 9;
      vb = pri[b.programa] ?? 9;
    } else if (key === "medicamento") {
      va = a.medicamento.toLowerCase();
      vb = b.medicamento.toLowerCase();
    } else if (key === "min_usd") {
      va = a.min_usd ?? 1e12;
      vb = b.min_usd ?? 1e12;
    } else if (key === "paises") {
      va = a.paises_con_dato;
      vb = b.paises_con_dato;
    } else if (String(key).startsWith("pais:")) {
      const id = key.slice(5);
      va = a.paises[id]?.min_usd ?? 1e12;
      vb = b.paises[id]?.min_usd ?? 1e12;
    } else {
      va = a.n;
      vb = b.n;
    }
    if (va < vb) return -1 * state.dir;
    if (va > vb) return 1 * state.dir;
    return a.n - b.n;
  });
  return rows;
}

function detalleDeTabla() {
  return filasVivas().map((f) => {
    const usdVal = aUsd(f.precio, f.moneda);
    return {
      n: f.n_lista,
      medicamento: f.medicamento_lista,
      programa: f.programa,
      pais: f.pais,
      farmacia: f.farmacia,
      producto: f.nombre_comercial,
      presentacion: f.presentacion,
      dosis: f.concentracion,
      precio_local: f.precio,
      moneda: f.moneda,
      precio_usd: usdVal,
      precio_dop: aDop(usdVal),
      fuente: fuenteUrlVisible(f),
      fecha_dato: f.fecha_dato,
      calidad: f.calidad,
      laboratorio: f.laboratorio,
      disponibilidad: f.disponibilidad,
      id_producto_farmacia: f.id_producto_farmacia,
    };
  });
}

function filtrarDetalle() {
  const q = state.dq.trim().toLowerCase();
  let rows = detalleDeTabla();
  if (state.dpais !== "todos") rows = rows.filter((r) => r.pais === state.dpais);
  if (state.programa === "fomac") rows = rows.filter((r) => String(r.programa).includes("FOMAC"));
  if (q) {
    rows = rows.filter((r) =>
      `${r.medicamento} ${r.producto} ${r.presentacion} ${r.dosis} ${r.programa} ${r.farmacia}`.toLowerCase().includes(q)
    );
  }
  return rows;
}

function paginate(rows, page, size) {
  const pages = Math.max(1, Math.ceil(rows.length / size));
  const p = Math.min(page, pages);
  const start = (p - 1) * size;
  return { rows: rows.slice(start, start + size), page: p, pages, total: rows.length, start };
}

function pager(idPrefix, page, pages, total, start, size) {
  const from = total ? start + 1 : 0;
  const to = Math.min(start + size, total);
  return `
    <div class="pager">
      <span>${from}–${to} de ${total}</span>
      <div class="pager-btns">
        <select class="selectish" data-size="${idPrefix}">
          ${[12, 25, 50, 100].map((n) => `<option ${n === size ? "selected" : ""}>${n}</option>`).join("")}
        </select>
        <button data-nav="${idPrefix}-prev" ${page <= 1 ? "disabled" : ""}>Anterior</button>
        <button data-nav="${idPrefix}-next" ${page >= pages ? "disabled" : ""}>Siguiente</button>
      </div>
    </div>`;
}

function coverSortMark(key) {
  if (state.csort !== key) return `<span class="ord">↕</span>`;
  return `<span class="ord">${state.cdir === 1 ? "↑" : "↓"}</span>`;
}

function skuTableState(group) {
  if (!SKU_TABLE_STATE[group]) {
    SKU_TABLE_STATE[group] = { q: "", sort: "precio_usd", dir: 1, page: 1, size: 12 };
  }
  return SKU_TABLE_STATE[group];
}

function skuSortMark(group, key) {
  const st = skuTableState(group);
  if (st.sort !== key) return `<span class="ord">↕</span>`;
  return `<span class="ord">${st.dir === 1 ? "↑" : "↓"}</span>`;
}

function skuPager(group, page, pages, total, start, size) {
  const from = total ? start + 1 : 0;
  const to = Math.min(start + size, total);
  return `
    <div class="pager pager--compact">
      <span>${from}–${to} de ${total}</span>
      <div class="pager-btns">
        <select class="selectish" data-sku-size="${escapeHtml(group)}">
          ${[12, 25, 50].map((n) => `<option ${n === size ? "selected" : ""}>${n}</option>`).join("")}
        </select>
        <button type="button" data-sku-nav="prev" data-sku-group="${escapeHtml(group)}" ${page <= 1 ? "disabled" : ""}>Anterior</button>
        <button type="button" data-sku-nav="next" data-sku-group="${escapeHtml(group)}" ${page >= pages ? "disabled" : ""}>Siguiente</button>
      </div>
    </div>`;
}

function filasCoberturaPaisView(filas) {
  const q = state.cq.trim().toLowerCase();
  let rows = [...filas].filter(filaOfertable).map((f) => ({
    ...f,
    precio_usd: aUsd(f.precio, f.moneda),
    presentacion_norm: presentacionComparable(f) || f.presentacion || "",
  }));
  if (q) {
    rows = rows.filter((f) =>
      `${f.medicamento_lista} ${f.farmacia} ${f.laboratorio} ${f.nombre_comercial} ${f.concentracion} ${f.presentacion_norm}`
        .toLowerCase()
        .includes(q)
    );
  }
  rows.sort((a, b) => {
    const key = state.csort;
    let va;
    let vb;
    if (key === "precio_usd") {
      va = a.precio_usd ?? 1e12;
      vb = b.precio_usd ?? 1e12;
    } else {
      va = String(
        key === "medicamento" ? a.medicamento_lista :
        key === "farmacia" ? a.farmacia :
        key === "laboratorio" ? a.laboratorio :
        key === "producto" ? a.nombre_comercial :
        key === "concentracion" ? a.concentracion :
        key === "presentacion" ? a.presentacion_norm :
        ""
      ).toLowerCase();
      vb = String(
        key === "medicamento" ? b.medicamento_lista :
        key === "farmacia" ? b.farmacia :
        key === "laboratorio" ? b.laboratorio :
        key === "producto" ? b.nombre_comercial :
        key === "concentracion" ? b.concentracion :
        key === "presentacion" ? b.presentacion_norm :
        ""
      ).toLowerCase();
    }
    if (va < vb) return -1 * state.cdir;
    if (va > vb) return 1 * state.cdir;
    return String(a.nombre_comercial || "").localeCompare(String(b.nombre_comercial || ""), "es");
  });
  return rows;
}

function panelFiltros({ buscaId, buscaVal, placeholder, extra = "" }) {
  const concs = opcionesCampo("concentracion");
  const press = opcionesCampo("presentacion");
  const alcances = opcionesCampo("alcance");
  return `
    <div class="filter-panel">
      <label class="filter-field">
        <span>Buscar</span>
        <input class="search" id="${buscaId}" placeholder="${escapeHtml(placeholder)}" value="${escapeHtml(buscaVal)}" />
      </label>
      <label class="filter-field">
        <span>Concentración</span>
        <select class="selectish" id="filtroConc">
          <option value="todas" ${state.conc === "todas" ? "selected" : ""}>Todas</option>
          ${concs.map((c) => `<option value="${escapeHtml(c)}" ${state.conc === c ? "selected" : ""}>${escapeHtml(c)}</option>`).join("")}
        </select>
      </label>
      <label class="filter-field">
        <span>Presentación</span>
        <select class="selectish" id="filtroPres">
          <option value="todas" ${state.pres === "todas" ? "selected" : ""}>Todas</option>
          ${press.map((c) => `<option value="${escapeHtml(c)}" ${state.pres === c ? "selected" : ""}>${escapeHtml(c)}</option>`).join("")}
        </select>
      </label>
      <label class="filter-field">
        <span>Alcance</span>
        <select class="selectish" id="filtroAlcance">
          <option value="todos" ${state.alcance === "todos" ? "selected" : ""}>Todos</option>
          ${alcances.map((c) => `<option value="${escapeHtml(c)}" ${state.alcance === c ? "selected" : ""}>${escapeHtml(etiquetaAlcance(c))}</option>`).join("")}
        </select>
      </label>
      ${extra}
    </div>`;
}

async function asegurarIndicadoresTendencias() {
  if (TEND_CATALOG.indicadores?.por_pais?.length) return TEND_CATALOG.indicadores;
  try {
    const r = await fetch("/api/tendencias/indicadores", { cache: "no-store" });
    const d = await r.json();
    if (d?.ok && d.indicadores) {
      TEND_CATALOG.indicadores = d.indicadores;
      return d.indicadores;
    }
  } catch (err) {
    console.warn("indicadores panorama", err);
  }
  return TEND_CATALOG.indicadores;
}

function histPaisRow(paisId) {
  const rows = TEND_CATALOG.indicadores?.por_pais || [];
  return rows.find((r) => idPaisPorTexto(r.pais) === paisId) || null;
}

/** Principios con precio en un país — misma métrica que «Principios activos por país» en Tendencias. */
function principiosActivosPorPaisId(paisId) {
  const histN = Number(histPaisRow(paisId)?.principios || 0);
  if (histN > 0) return histN;
  return new Set(
    TABLA.filter((f) => filaPaisActivo(f) && idPaisPorTexto(f.pais) === paisId && filaConPrecio(f))
      .map((f) => f.n_lista)
      .filter((n) => n != null),
  ).size;
}

function snapPrincipiosPorPaisId(paisId) {
  return new Set(
    TABLA.filter((f) => filaPaisActivo(f) && idPaisPorTexto(f.pais) === paisId && filaConPrecio(f))
      .map((f) => f.n_lista)
      .filter((n) => n != null),
  ).size;
}

function renderTablero() {
  const paises = paisesUiPanorama();
  const base = TABLA.filter((f) => filaPaisActivo(f) && filaConPrecio(f));
  const porPais = paises.map((p) => {
    const hist = histPaisRow(p.id);
    const histPrincipios = Number(hist?.principios || 0);
    const histMeds = Number(hist?.medicamentos || 0);
    const snapPrincipios = snapPrincipiosPorPaisId(p.id);
    const conHits = principiosActivosPorPaisId(p.id);
    const farms = [...new Set(base.filter((f) => idPaisPorTexto(f.pais) === p.id).map((f) => f.farmacia).filter(Boolean))];
    const soloHistorial = histPrincipios > 0 && snapPrincipios === 0;
    return { ...p, conHits, snapPrincipios, histPrincipios, histMeds, farms, soloHistorial };
  }).sort((a, b) => b.conHits - a.conHits || a.nombre.localeCompare(b.nombre, "es"));
  $("stage").innerHTML = `
    <article class="card cover-card">
      <div class="card-head cover-card-head">
        <div>
          <h2>Principios activos por país</h2>
          <p class="muted cover-card-note">Principios activos con precio en la última fecha del historial (misma cifra que en Tendencias). Si aún no hay historial para el país, se usa el snapshot en vivo.</p>
        </div>
      </div>
      <div class="cover-countries">
        ${porPais.map((p) => {
          const nFarms = p.farms.length;
          const pieTexto = nFarms
            ? `${nFarms} ${nFarms === 1 ? "farmacia consultada" : "farmacias consultadas"}`
            : p.soloHistorial
              ? "Sin datos nuevos hoy"
              : "Sin farmacias registradas";
          return `
          <div class="cover-country cover-country--${p.id}${p.soloHistorial ? " is-historial" : ""}" data-cover-pais="${p.id}" role="button" tabindex="0" title="${escapeHtml(nFarms ? p.farms.join(", ") : p.full)}">
            <div class="cover-country-head">
              ${flagImg(p.id, "cover-flag")}
              <h3 class="cover-country-name">${escapeHtml(p.nombre)}</h3>
            </div>
            <div class="cover-country-body">
              <p class="cover-num">${p.conHits}</p>
              <p class="cover-num-caption">principios activos</p>
            </div>
            <div class="cover-country-foot">
              <span class="cover-foot-text">${escapeHtml(pieTexto)}</span>
              ${p.soloHistorial && p.histMeds ? `<span class="cover-foot-hist">${p.histMeds} presentaciones en el historial</span>` : ""}
            </div>
          </div>`;
        }).join("")}
      </div>
    </article>
  `;
}

function renderComparativo() {
  const all = filtrarComparativo();
  const pg = paginate(all, state.page, state.size);
  state.page = pg.page;
  const paises = paisesUi();
  const extra = `
    <label class="filter-field">
      <span>Cantidad de países</span>
      <select class="selectish" id="filtroDato" title="Cantidad de países">
        <option value="todos" ${state.conDato === "todos" ? "selected" : ""}>Con o sin precio</option>
        <option value="con" ${state.conDato === "con" ? "selected" : ""}>Par comparable (2+ países)</option>
        <option value="sin" ${state.conDato === "sin" ? "selected" : ""}>Sin par comparable</option>
      </select>
    </label>
    <label class="filter-field">
      <span>País</span>
      <select class="selectish" id="filtroPais" title="País con dato">
        <option value="todos" ${state.paisFiltro === "todos" ? "selected" : ""}>Cualquier país</option>
        ${paises.map((p) => `
          <option value="${p.id}" ${state.paisFiltro === p.id ? "selected" : ""}>${p.flag} ${escapeHtml(p.nombre)}</option>
        `).join("")}
      </select>
    </label>
    <label class="filter-field filter-field--chips">
      <span>Programa</span>
      <div class="filter-chips">
        <button class="chip ${state.programa === "todos" ? "is-on" : ""}" data-prog="todos">Todos</button>
        <button class="chip ${state.programa === "fomac" ? "is-on" : ""}" data-prog="fomac">FOMAC</button>
        <button class="chip ${state.programa === "DAMAC" ? "is-on" : ""}" data-prog="DAMAC">DAMAC</button>
      </div>
    </label>`;
  $("stage").innerHTML = `
    <article class="card card--flow">
      <div class="card-head">
        <div>
          <h2>Precio más bajo por país</h2>
          <p class="muted" style="margin:6px 0 0">Compara el <strong>PVP representativo por país</strong> (mediana si hay varios genéricos; si no, el más barato). Misma concentración, forma (± recubierto) y empaque. Se excluyen marcas de referencia y precios atípicos.</p>
        </div>
      </div>
      <div class="comp-sticky-stack">
        ${panelFiltros({ buscaId: "q", buscaVal: state.q, placeholder: "Buscar medicamento, concentración o país…", extra })}
        <div class="comp-head-scroll" id="compHeadScroll">
          <table class="data data-comp">
            <thead>
              <tr>
                <th class="sticky-l ${thSortClass("medicamento")}" data-sort="medicamento">Medicamento ${sortMark("medicamento")}</th>
                <th class="${thSortClass("programa")}" data-sort="programa">Programa ${sortMark("programa")}</th>
                ${paises.map((p) => `
                  <th class="th-pais ${thSortClass("pais:" + p.id)}" data-sort="pais:${p.id}" title="${escapeHtml(p.full)} — ordenar por PVP">
                    ${flagImg(p.id, "th-flag-img")}
                  </th>`).join("")}
                <th class="${thSortClass("min_usd")}" data-sort="min_usd" title="Mínimo global">Mín. ${sortMark("min_usd")}</th>
              </tr>
            </thead>
          </table>
        </div>
      </div>
      <div class="table-wrap table-wrap--flow" id="compBodyScroll">
        <table class="data data-comp">
          <thead class="comp-thead-spacer" aria-hidden="true">
            <tr>
              <th class="sticky-l">Medicamento</th>
              <th>Programa</th>
              ${paises.map((p) => `<th class="th-pais">${flagImg(p.id, "th-flag-img")}</th>`).join("")}
              <th>Mín.</th>
            </tr>
          </thead>
          <tbody>
            ${pg.rows.map((r) => {
              const best = mejorPaisId(r);
              const bestCel = best ? r.paises[best] : null;
              return `
              <tr data-open="${r.n}">
                <td class="med sticky-l">${escapeHtml(r.medicamento)}<div class="muted">${escapeHtml(r.presentacion_comparada || "")}${r.par_comparable ? "" : (r.presentacion_comparada ? " · no comparable entre países" : "")}</div></td>
                <td>${badge(r.programa)}</td>
                ${paises.map((p) => htmlCeldaComparativo(r, p, best)).join("")}
                <td class="td-precio">${r.par_comparable ? `<div class="comp-price-main">${money(r.min_usd)}</div>${bestCel?.min_usd_unidad != null && bestCel.cantidad > 1 ? `<div class="comp-pu muted">${money(bestCel.min_usd_unidad)}/ud</div>` : ""}<div class="muted">${r.min_dop != null ? dop.format(r.min_dop) : ""}</div>` : `<span class="empty">—</span><div class="muted">sin par</div>`}</td>
              </tr>`;
            }).join("")}
          </tbody>
        </table>
      </div>
      ${pager("c", pg.page, pg.pages, pg.total, pg.start, state.size)}
    </article>
  `;
  bindCompScrollSync();
}

function bindCompScrollSync() {
  const head = $("compHeadScroll");
  const body = $("compBodyScroll");
  if (!head || !body) return;

  const syncWidths = () => {
    const headTh = head.querySelectorAll("thead th");
    const bodyTh = body.querySelectorAll("thead th");
    const bodyTd = body.querySelector("tbody tr")?.children || [];
    const n = headTh.length;
    for (let i = 0; i < n; i++) {
      const td = bodyTd[i];
      const floor = i === 1 ? 118 : (i >= 2 && i < n - 1 ? 118 : 48);
      const w = Math.ceil(Math.max(
        headTh[i]?.getBoundingClientRect().width || 0,
        bodyTh[i]?.getBoundingClientRect().width || 0,
        td?.getBoundingClientRect().width || 0,
        td?.scrollWidth || 0,
        floor,
      ));
      if (headTh[i]) {
        headTh[i].style.width = `${w}px`;
        headTh[i].style.minWidth = `${w}px`;
      }
      if (bodyTh[i]) {
        bodyTh[i].style.width = `${w}px`;
        bodyTh[i].style.minWidth = `${w}px`;
      }
    }
  };

  let lock = false;
  const sync = (from, to) => {
    if (lock) return;
    lock = true;
    to.scrollLeft = from.scrollLeft;
    requestAnimationFrame(() => { lock = false; });
  };
  head.addEventListener("scroll", () => sync(head, body), { passive: true });
  body.addEventListener("scroll", () => sync(body, head), { passive: true });

  syncWidths();
  requestAnimationFrame(syncWidths);
  window.addEventListener("resize", syncWidths, { passive: true });
}

function syncFlowSticky() {
  const card = document.querySelector(".card--flow");
  if (!card) return;
  // Comparativo usa .comp-sticky-stack; detalle mantiene thead sticky simple.
  if (card.querySelector(".comp-sticky-stack")) return;
  const panel = card.querySelector(".filter-panel");
  if (!panel) return;
  card.style.setProperty("--comp-sticky-top", `${Math.ceil(panel.getBoundingClientRect().height)}px`);
}

function renderDetalle() {
  const all = filtrarDetalle();
  const pg = paginate(all, state.dpage, state.dsize);
  state.dpage = pg.page;
  const paises = ["todos", ...[...new Set(filasTablaBase().map((r) => r.pais).filter(Boolean))]];
  const headCols = `
    <th class="sticky-l">Medicamento</th>
    <th>País</th>
    <th>Farmacia</th>
    <th>Producto</th>
    <th>Concentración</th>
    <th>Presentación</th>
    <th>USD</th>
    <th>DOP</th>
    <th>Local</th>
    <th>Dato</th>`;
  $("stage").innerHTML = `
    <article class="card card--flow">
      <div class="card-head">
        <div>
          <h2>Presentaciones encontradas</h2>
          <p class="muted" style="margin:6px 0 0">Una fila por producto encontrado en farmacia, con precio y enlace al dato.</p>
        </div>
      </div>
      <div class="comp-sticky-stack">
        ${panelFiltros({
          buscaId: "dq",
          buscaVal: state.dq,
          placeholder: "Buscar producto, concentración o molécula…",
          extra: `
            <label class="filter-field">
              <span>País</span>
              <select class="selectish" id="dpais">
                ${paises.map((p) => `<option ${p === state.dpais ? "selected" : ""}>${escapeHtml(p)}</option>`).join("")}
              </select>
            </label>`,
        })}
        <div class="comp-head-scroll" id="compHeadScroll">
          <table class="data data-comp data-detalle">
            <thead>
              <tr>${headCols}</tr>
            </thead>
          </table>
        </div>
      </div>
      <div class="table-wrap table-wrap--flow" id="compBodyScroll">
        <table class="data data-comp data-detalle">
          <thead class="comp-thead-spacer" aria-hidden="true">
            <tr>${headCols}</tr>
          </thead>
          <tbody>
            ${pg.rows.map((r) => `
              <tr data-open="${r.n}">
                <td class="med sticky-l">${escapeHtml(r.medicamento)}<div class="muted">${badge(r.programa)} ${r.calidad === "revisar" ? `<span class="badge revisar">revisar</span>` : ""}</div></td>
                <td>${escapeHtml(r.pais)}</td>
                <td>${escapeHtml(r.farmacia || "")}</td>
                <td class="med">${escapeHtml(r.producto || "—")}${esDatoAmbiguo(r) ? `<div class="muted"><span class="badge revisar">dato ambiguo</span></div>` : ""}</td>
                <td>${escapeHtml(r.dosis || "—")}</td>
                <td>${escapeHtml(r.presentacion || "—")}</td>
                <td class="td-precio">${money(r.precio_usd)}</td>
                <td class="td-precio">${money(r.precio_dop, "dop")}</td>
                <td class="td-precio">${r.precio_local != null ? `${Number(r.precio_local).toLocaleString("en-US")} ${escapeHtml(r.moneda || "")}` : "—"}</td>
                <td>${linkDato(r.fuente, r.fecha_dato, { compact: true })}</td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>
      ${pager("d", pg.page, pg.pages, pg.total, pg.start, state.dsize)}
    </article>
  `;
  bindCompScrollSync();
}

function totalMedicamentos() {
  const nLista = (D.comparativo || []).length;
  if (nLista) return nLista;
  return new Set(filasTablaBase().map((f) => f.n_lista).filter((n) => n != null)).size;
}

function monedasVivas() {
  const set = new Set(filasTablaBase().map((f) => String(f.moneda || "").toUpperCase()).filter(Boolean));
  set.add("DOP");
  return set;
}

const FUENTES_FARMACIA = {
  FarmaValue: {
    link: "https://www.farmavalue.com.do/",
    que: "PVP de góndola del catálogo retail (DOP)",
    metodo: "Catálogo FarmaValue / API 3C, cruce con lista DAMAC-FOMAC",
  },
  "Los Hidalgos": {
    link: "https://farmaciasloshidalgos.com.do/",
    que: "PVP publicado en la tienda online (DOP)",
    metodo: "Búsqueda pública WooCommerce de la farmacia",
  },
  Carol: {
    link: "https://tienda.farmaciacarol.com/",
    que: "PVP de góndola de la tienda online (DOP)",
    metodo: "Búsqueda pública VevoCart de Farmacia Carol",
  },
  Qualipharma: {
    link: "https://qualipharma.com.do/",
    que: "PVP de especialidad / oncológicos (DOP)",
    metodo: "Catálogo público WooCommerce de la farmacia",
  },
  GBC: {
    link: "https://farmaciamedicargbc.com/",
    que: "PVP publicado vía farmacias.do (seller Farmacia Medicar GBC)",
    metodo: "Oferta del seller GBC en el agregador farmacias.do",
  },
  "Pague Menos": {
    link: "https://www.paguemenos.com.br/",
    que: "Precio de venta al público en la tienda online (BRL)",
    metodo: "API pública VTEX de búsqueda de productos",
    pais: "Brasil",
  },
  Drogasil: {
    link: "https://www.drogasil.com.br/",
    que: "Precio de venta al público en la tienda online (BRL)",
    metodo: "API pública VTEX (Akamai puede bloquear el datacenter)",
    pais: "Brasil",
  },
  "Droga Raia": {
    link: "https://www.drogaraia.com.br/",
    que: "Precio de venta al público en la tienda online (BRL)",
    metodo: "API pública VTEX (Akamai puede bloquear el datacenter)",
    pais: "Brasil",
  },
  Panvel: {
    link: "https://www.panvel.com/",
    que: "Precio de venta al público en la tienda online (BRL)",
    metodo: "API pública VTEX (proxy puede bloquear Online Shopping)",
    pais: "Brasil",
  },
  Macrofarmacias: {
    link: "https://macrofarmacias.com/",
    que: "PVP referencial de especialidad en la tienda (MXN)",
    metodo: "Catálogo público catalogo.php",
  },
  "Farmacias Similares": {
    link: "https://www.farmaciasdesimilares.com/",
    que: "PVP de góndola en la tienda online (MXN)",
    metodo: "API pública VTEX de búsqueda de productos",
  },
  "Farmacias del Ahorro": {
    link: "https://www.fahorro.com/",
    que: "PVP publicado en la tienda online (MXN)",
    metodo: "GraphQL Magento de búsqueda de productos",
  },
  "Farmacias San Pablo": {
    link: "https://www.farmaciasanpablo.com.mx/",
    que: "PVP publicado en la tienda online (MXN)",
    metodo: "Búsqueda pública (Akamai puede bloquear el datacenter)",
  },
  Locatel: {
    link: "https://www.locatelcolombia.com/",
    que: "PVP publicado en la tienda online (COP)",
    metodo: "API pública VTEX de búsqueda de productos",
    pais: "Colombia",
  },
  Farmatodo: {
    link: "https://www.farmatodo.com.co/",
    que: "PVP publicado en la tienda online (COP)",
    metodo: "Búsqueda Algolia pública de Farmatodo",
    pais: "Colombia",
  },
  "Cruz Verde": {
    link: "https://www.cruzverde.com.co/",
    que: "PVP publicado en la tienda online (COP)",
    metodo: "API pública VTEX (proxy puede bloquear Online Shopping)",
    pais: "Colombia",
  },
  "La Rebaja": {
    link: "https://www.larebajavirtual.com/",
    que: "PVP publicado en la tienda online (COP)",
    metodo: "API pública VTEX (proxy puede bloquear Online Shopping)",
    pais: "Colombia",
  },
  "Droguerías Cafam": {
    link: "https://www.drogueriascafam.com.co/",
    que: "PVP publicado en la tienda online (COP)",
    metodo: "API pública VTEX (proxy puede bloquear Online Shopping)",
    pais: "Colombia",
  },
  Carulla: {
    link: "https://www.carulla.com/",
    que: "PVP de droguería en la tienda online (COP)",
    metodo: "API pública VTEX de búsqueda de productos",
    pais: "Colombia",
  },
  Farmacity: {
    link: "https://www.farmacity.com/",
    que: "PVP publicado en la tienda online (ARS)",
    metodo: "API pública VTEX de búsqueda de productos",
    pais: "Argentina",
  },
  Salcobrand: {
    link: "https://salcobrand.cl/",
    que: "PVP publicado en la tienda online (CLP)",
    metodo: "Búsqueda Algolia pública de Salcobrand",
    pais: "Chile",
  },
  "Farmacias Ahumada": {
    link: "https://www.farmaciasahumada.cl/",
    que: "PVP publicado en la tienda online (CLP)",
    metodo: "Búsqueda Demandware (Search-UpdateGrid) de Farmacias Ahumada",
    pais: "Chile",
  },
  Arrocha: {
    link: "https://www.arrocha.com/",
    que: "PVP publicado en la tienda online (USD/PAB)",
    metodo: "Shopify suggest + ficha de producto (especialidad online limitada)",
    pais: "Panamá",
  },
  Inkafarma: {
    link: "https://inkafarma.pe/",
    que: "PVP publicado en la tienda online (PEN)",
    metodo: "Búsqueda Algolia pública de Inkafarma",
    pais: "Perú",
  },
  "Boticas Perú": {
    link: "https://www.boticasperu.pe/",
    que: "PVP publicado en la tienda online (PEN)",
    metodo: "Búsqueda Demandware (Search-UpdateGrid) de Boticas Perú",
    pais: "Perú",
  },
  Farmashop: {
    link: "https://www.farmashop.com.uy/",
    que: "PVP publicado en la tienda online (UYU)",
    metodo: "API pública VTEX (proxy puede bloquear Online Shopping)",
    pais: "Uruguay",
  },
  Siman: {
    link: "https://sv.siman.com/",
    que: "PVP de la sección Farmacia en la tienda online (USD)",
    metodo: "Ficha de producto en siman.com (VTEX)",
    pais: "El Salvador",
  },
  "Farmacias San Nicolás": {
    link: "https://www.farmaciasannicolas.com/",
    que: "PVP publicado en la tienda online (USD)",
    metodo: "API pública VTEX (proxy puede bloquear Online Shopping)",
    pais: "El Salvador",
  },
  "Pharmacy's": {
    link: "https://www.pharmacys.com.ec/",
    que: "PVP publicado en la tienda online (USD)",
    metodo: "API pública VTEX de Pharmacy's (grupo DIFARE)",
    pais: "Ecuador",
  },
  "Cruz Azul": {
    link: "https://www.farmaciascruzazul.ec/",
    que: "PVP publicado en la tienda online (USD)",
    metodo: "API pública VTEX de Cruz Azul (grupo DIFARE)",
    pais: "Ecuador",
  },
  Fybeca: {
    link: "https://www.fybeca.com/",
    que: "PVP publicado en la tienda online (USD)",
    metodo: "API pública VTEX de Fybeca (WAF puede bloquear el datacenter)",
    pais: "Ecuador",
  },
  Kielsa: {
    link: "https://kielsa.com/",
    que: "PVP publicado en la tienda online (moneda local)",
    metodo: "Buscador regional Kielsa + detalle de producto vía Meteor DDP",
  },
  "Farmacias Batres": {
    link: "https://www.farmaciasbatres.com.gt/",
    que: "PVP publicado en la tienda online (GTQ)",
    metodo: "API pública VTEX (WAF puede bloquear el datacenter)",
    pais: "Guatemala",
  },
  "Farmacias Galeno": {
    link: "https://www.farmaciasgaleno.com.gt/",
    que: "PVP publicado en la tienda online (GTQ)",
    metodo: "Catálogo online de la cadena",
    pais: "Guatemala",
  },
  Kölbi: {
    link: "https://www.kolbi.cr/",
    que: "PVP publicado en la tienda online (CRC)",
    metodo: "API pública VTEX (WAF puede bloquear el datacenter)",
    pais: "Costa Rica",
  },
  "Farmacias Fischel": {
    link: "https://www.farmaciasfischel.com/",
    que: "PVP publicado en la tienda online (CRC)",
    metodo: "Catálogo online de la cadena",
    pais: "Costa Rica",
  },
  "Siman · Honduras": {
    farmacia: "Siman",
    link: "https://gt.siman.com/",
    que: "PVP de la sección Farmacia en la tienda online (USD)",
    metodo: "Ficha de producto en siman.com (VTEX)",
    pais: "Honduras",
  },
  "Siman · Guatemala": {
    farmacia: "Siman",
    link: "https://gt.siman.com/",
    que: "PVP de la sección Farmacia en la tienda online (USD)",
    metodo: "Ficha de producto en siman.com (VTEX)",
    pais: "Guatemala",
  },
  "Siman · Nicaragua": {
    farmacia: "Siman",
    link: "https://ni.siman.com/",
    que: "PVP de la sección Farmacia en la tienda online (USD)",
    metodo: "Ficha de producto en siman.com (VTEX)",
    pais: "Nicaragua",
  },
  "Siman · Costa Rica": {
    farmacia: "Siman",
    link: "https://cr.siman.com/",
    que: "PVP de la sección Farmacia en la tienda online (USD)",
    metodo: "Ficha de producto en siman.com (VTEX)",
    pais: "Costa Rica",
  },
  "Kielsa · Honduras": {
    farmacia: "Kielsa",
    link: "https://kielsa.com/",
    que: "PVP publicado en la tienda online (HNL)",
    metodo: "Buscador buscador.kielsa.com + detalle Meteor DDP",
    pais: "Honduras",
  },
  "Kielsa · Nicaragua": {
    farmacia: "Kielsa",
    link: "https://www.kielsa.com.ni/",
    que: "PVP publicado en la tienda online (NIO)",
    metodo: "Buscador buscadorni.kielsa.com + detalle Meteor DDP",
    pais: "Nicaragua",
  },
  "Farmacias del Ahorro · Honduras": {
    farmacia: "Farmacias del Ahorro",
    link: "https://www.farmaciasdelahorro.hn/",
    que: "PVP publicado en la tienda online (HNL)",
    metodo: "Tienda regional Farmacias del Ahorro (SPA)",
    pais: "Honduras",
  },
  "MiFarmacia · Honduras": {
    farmacia: "MiFarmacia",
    link: "https://mifarmacia.hn/",
    que: "PVP publicado en la farmacia digital Quimifar (HNL)",
    metodo: "API /api/search de mifarmacia.hn",
    pais: "Honduras",
  },
  "Farmacias del Ahorro · Nicaragua": {
    farmacia: "Farmacias del Ahorro",
    link: "https://www.farmaciasdelahorro.hn/",
    que: "PVP publicado en la tienda online (NIO)",
    metodo: "Cadena regional Farmacias del Ahorro (SPA)",
    pais: "Nicaragua",
  },
};

function fuentesFarmaciasVivas() {
  const vistos = new Set();
  const out = [];
  for (const f of TABLA) {
    if (!filaPaisActivo(f)) continue;
    const clave = `${f.pais}|${f.farmacia}`;
    if (!f.farmacia || vistos.has(clave)) continue;
    vistos.add(clave);
    const meta = metaFuenteFarmacia(f.farmacia, f.pais);
    const n = TABLA.filter((x) => x.pais === f.pais && x.farmacia === f.farmacia).length;
    const fuenteId = fuenteIdPorFarmacia(f.farmacia, f.pais);
    out.push({
      pais: f.pais,
      farmacia: f.farmacia,
      fuente_id: fuenteId,
      link: meta.link || f.fuente_url || "",
      que: meta.que || `PVP publicado en ${f.farmacia} (${f.moneda || "moneda local"})`,
      metodo: meta.metodo || "Precio de la ficha de producto de la farmacia",
      skus: n,
    });
  }
  // Fuentes configuradas sin filas aún (p. ej. bloqueadas por WAF): igual aparecen para encolar.
  for (const [nombre, meta] of Object.entries(FUENTES_FARMACIA)) {
    const pais = meta.pais;
    if (!pais || !paisActivo(idPaisPorTexto(pais))) continue;
    const farmacia = meta.farmacia || nombre;
    const clave = `${pais}|${farmacia}`;
    if (vistos.has(clave)) continue;
    vistos.add(clave);
    out.push({
      pais,
      farmacia,
      fuente_id: fuenteIdPorFarmacia(farmacia, pais),
      link: meta.link || "",
      que: meta.que || `PVP publicado en ${nombre}`,
      metodo: meta.metodo || "Precio de la ficha de producto de la farmacia",
      skus: 0,
    });
  }
  return out.sort((a, b) => String(a.pais).localeCompare(b.pais, "es") || String(a.farmacia).localeCompare(b.farmacia, "es"));
}

function metaFuenteFarmacia(farmacia, pais) {
  const base = FUENTES_FARMACIA[farmacia] || {};
  const p = String(pais || "");
  if (base.pais && p && base.pais !== p) {
    const regional = FUENTES_FARMACIA_REGIONAL[`${farmacia}|${p}`];
    if (regional) return { ...base, ...regional };
    return { ...base, pais: p };
  }
  const regional = FUENTES_FARMACIA_REGIONAL[`${farmacia}|${p}`];
  return regional ? { ...base, ...regional } : base;
}

const FUENTES_FARMACIA_REGIONAL = {
  "Siman|Honduras": {
    link: "https://gt.siman.com/",
    que: "PVP de la sección Farmacia en la tienda online (USD)",
    metodo: "Ficha de producto en siman.com (VTEX)",
    pais: "Honduras",
  },
  "Siman|Guatemala": {
    link: "https://gt.siman.com/",
    que: "PVP de la sección Farmacia en la tienda online (USD)",
    metodo: "Ficha de producto en siman.com (VTEX)",
    pais: "Guatemala",
  },
  "Siman|Nicaragua": {
    link: "https://ni.siman.com/",
    que: "PVP de la sección Farmacia en la tienda online (USD)",
    metodo: "Ficha de producto en siman.com (VTEX)",
    pais: "Nicaragua",
  },
  "Siman|Costa Rica": {
    link: "https://cr.siman.com/",
    que: "PVP de la sección Farmacia en la tienda online (USD)",
    metodo: "Ficha de producto en siman.com (VTEX)",
    pais: "Costa Rica",
  },
  "Kielsa|Honduras": {
    link: "https://kielsa.com/",
    que: "PVP publicado en la tienda online (HNL)",
    metodo: "Buscador buscador.kielsa.com + detalle Meteor DDP",
    pais: "Honduras",
  },
  "Kielsa|Nicaragua": {
    link: "https://www.kielsa.com.ni/",
    que: "PVP publicado en la tienda online (NIO)",
    metodo: "Buscador buscadorni.kielsa.com + detalle Meteor DDP",
    pais: "Nicaragua",
  },
  "Farmacias del Ahorro|Honduras": {
    link: "https://www.farmaciasdelahorro.hn/",
    que: "PVP publicado en la tienda online (HNL)",
    metodo: "Tienda regional Farmacias del Ahorro (SPA)",
    pais: "Honduras",
  },
  "MiFarmacia|Honduras": {
    link: "https://mifarmacia.hn/",
    que: "PVP publicado en la farmacia digital Quimifar (HNL)",
    metodo: "API /api/search de mifarmacia.hn",
    pais: "Honduras",
  },
  "Farmacias del Ahorro|Nicaragua": {
    link: "https://www.farmaciasdelahorro.hn/",
    que: "PVP publicado en la tienda online (NIO)",
    metodo: "Cadena regional Farmacias del Ahorro (SPA)",
    pais: "Nicaragua",
  },
};

function fuenteIdPorFarmacia(farmacia, pais) {
  const p = String(pais || "").toLowerCase();
  if (farmacia === "Siman") {
    if (p.includes("honduras")) return "hn_siman";
    if (p.includes("guatemala")) return "gt_siman";
    if (p.includes("nicaragua")) return "ni_siman";
    if (p.includes("costa rica") || p.includes("costarica")) return "cr_siman";
    if (p.includes("salvador")) return "siman";
  }
  if (farmacia === "Kielsa") {
    if (p.includes("honduras")) return "hn_kielsa";
    if (p.includes("nicaragua")) return "ni_kielsa";
  }
  if (farmacia === "Farmacias del Ahorro") {
    if (p.includes("honduras")) return "hn_fahorro";
    if (p.includes("nicaragua")) return "ni_fahorro";
    if (p.includes("méxico") || p.includes("mexico")) return "fahorro";
  }
  if (farmacia === "MiFarmacia" && p.includes("honduras")) return "hn_mifarmacia";
  const map = {
    FarmaValue: "farmavalue",
    Carol: "carol",
    Qualipharma: "qualipharma",
    "Los Hidalgos": "hidalgos",
    GBC: "farmacias_do",
    "farmacias.do": "farmacias_do",
    "Pague Menos": "paguemenos",
    Drogasil: "drogasil",
    "Droga Raia": "drogaraia",
    Panvel: "panvel",
    Macrofarmacias: "macrofarmacias",
    "Farmacias Similares": "similares",
    "Farmacias del Ahorro": "fahorro",
    "Farmacias San Pablo": "sanpablo",
    Locatel: "locatel",
    Farmatodo: "farmatodo",
    "Cruz Verde": "cruzverde",
    "La Rebaja": "larebaja",
    "Droguerías Cafam": "cafam",
    Carulla: "carulla",
    Farmacity: "farmacity",
    Salcobrand: "salcobrand",
    "Farmacias Ahumada": "ahumada",
    Arrocha: "arrocha",
    Inkafarma: "inkafarma",
    "Boticas Perú": "boticasperu",
    Farmashop: "farmashop",
    Siman: "siman",
    "Farmacias San Nicolás": "sv_sannicolas",
    "Pharmacy's": "ec_pharmacys",
    "Cruz Azul": "ec_cruzazul",
    Fybeca: "ec_fybeca",
    Kielsa: "hn_kielsa",
    MiFarmacia: "hn_mifarmacia",
    "Farmacias Batres": "gt_batres",
    "Farmacias Galeno": "gt_galeno",
    Kölbi: "cr_kolbi",
    "Farmacias Fischel": "cr_fischel",
  };
  return map[farmacia] || null;
}

function tasasPaisesVivos() {
  const monedas = monedasVivas();
  return (D.tasas || []).filter((t) => {
    const etiqueta = String(campo(t, "país", "pais", "moneda"));
    const s = etiqueta.toLowerCase();
    if (s.includes("compra") || s.includes("equivalente")) return false;
    const mon = monedaDeEtiqueta(etiqueta);
    if (mon) return monedas.has(mon);
    return Boolean(idPaisPorTexto(etiqueta) && paisesVivos().has(idPaisPorTexto(etiqueta)));
  });
}

function etiquetaEstadoJob(est) {
  const e = String(est || "").toLowerCase();
  if (e === "queued") return `<span class="job-pill is-queued">En cola</span>`;
  if (e === "running") return `<span class="job-pill is-running">Actualizando…</span>`;
  if (e === "done") return `<span class="job-pill is-done">Actualizado</span>`;
  if (e === "error") return `<span class="job-pill is-error">Error</span>`;
  return "";
}

async function encolarFuente(fuenteId, btn) {
  if (!fuenteId) return;
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Encolando…";
  }
  try {
    const r = await fetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fuente: fuenteId }),
    });
    const data = await r.json();
    if (!data.ok) throw new Error(data.error || "No se pudo encolar");
    const job = data.job || {};
    if (JOBS_ESTADOS) JOBS_ESTADOS[fuenteId] = job;
    if (btn) {
      btn.disabled = false;
      btn.textContent = job.reutilizado ? "Ya en cola" : "En cola";
    }
    renderFuentes();
    startJobsPolling();
  } catch (err) {
    console.error(err);
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Reintentar";
    }
    alert(`No se pudo encolar: ${err.message || err}`);
  }
}

let JOBS_ESTADOS = {};
let JOBS_TIMER = null;

async function cargarEstadosJobs() {
  try {
    const r = await fetch("/api/fuentes-jobs", { cache: "no-store" });
    const data = await r.json();
    if (!data.ok) return null;
    JOBS_ESTADOS = data.estados || {};
    return data;
  } catch (err) {
    console.error(err);
    return null;
  }
}

function startJobsPolling() {
  if (JOBS_TIMER) return;
  JOBS_TIMER = setInterval(async () => {
    if (state.view !== "fuentes") return;
    const data = await cargarEstadosJobs();
    if (!data) return;
    const activos = Object.values(JOBS_ESTADOS).some((j) => ["queued", "running"].includes(j?.estado));
    renderFuentes();
    if (!activos && JOBS_TIMER) {
      clearInterval(JOBS_TIMER);
      JOBS_TIMER = null;
    }
  }, 4000);
}

function tendOptionValue(m) {
  const n = Number(m?.n_lista);
  const pk = String(m?.producto_key || "");
  return `${n}::${encodeURIComponent(pk)}`;
}

function parseTendOptionValue(raw) {
  const s = String(raw || "");
  const i = s.indexOf("::");
  if (i < 0) return { n: s ? Number(s) : null, producto_key: "" };
  return {
    n: Number(s.slice(0, i)),
    producto_key: decodeURIComponent(s.slice(i + 2)),
  };
}

function tendMedLabel(m) {
  return m.producto_label
    || [m.nombre_comercial, m.concentracion, m.presentacion].filter(Boolean).join(" · ")
    || m.medicamento_lista
    || `Medicamento #${m.n_lista}`;
}

function tendMedHaystack(m) {
  return [
    tendMedLabel(m),
    m.medicamento_lista,
    m.nombre_comercial,
    m.concentracion,
    m.presentacion,
    m.producto_key,
    m.n_lista,
  ].filter(Boolean).join(" ").toLowerCase();
}

function tendMedPaises(m) {
  const raw = String(m?.paises_list || "").trim();
  if (raw) return raw.split("|").map((p) => p.trim()).filter(Boolean);
  return [];
}

function tendMedEnPais(m, paisId) {
  if (!paisId || paisId === "todos") return true;
  return tendMedPaises(m).some((p) => idPaisPorTexto(p) === paisId);
}

function tendPaisesHistorialOpts() {
  const idSet = new Set();
  for (const r of (TEND_CATALOG.indicadores?.por_pais || [])) {
    const id = idPaisPorTexto(r.pais);
    if (paisActivo(id)) idSet.add(id);
  }
  for (const m of TEND_CATALOG.medicamentos || []) {
    for (const p of tendMedPaises(m)) {
      const id = idPaisPorTexto(p);
      if (paisActivo(id)) idSet.add(id);
    }
  }
  const orden = ["do", "br", "mx", "ec", "hn", "gt", "ni", "cr", "pa", "ar", "co", "pe", "cl", "uy", "sv"];
  return orden.filter((id) => idSet.has(id)).map((id) => {
    const fromData = (D.paises || []).find((p) => p.id === id);
    return paisUi(fromData || { id, nombre: PAIS_UI[id]?.full || id });
  });
}

function tendFiltrarMedicamentos(meds, q) {
  const needle = String(q || "").trim().toLowerCase();
  if (!needle) return meds;
  return meds.filter((m) => tendMedHaystack(m).includes(needle));
}

function tendMedicamentosVisibles() {
  let meds = Array.isArray(TEND_CATALOG.medicamentos) ? [...TEND_CATALOG.medicamentos] : [];
  if (state.tendSoloMulti) meds = meds.filter((m) => Number(m.fechas || 0) >= 2);
  if (state.tendPaisFiltro && state.tendPaisFiltro !== "todos") {
    meds = meds.filter((m) => tendMedEnPais(m, state.tendPaisFiltro));
  }
  return tendFiltrarMedicamentos(meds, state.tendSearchQ);
}

function tendSelectedValue() {
  if (!state.tendenciaN || !state.tendenciaProductoKey) return "";
  return tendOptionValue({ n_lista: state.tendenciaN, producto_key: state.tendenciaProductoKey });
}

function renderTendPickerList() {
  const list = $("tendPickerList");
  const count = $("tendPickerCount");
  if (!list) return;
  const opts = tendMedicamentosVisibles();
  const selectedVal = tendSelectedValue();
  if (count) {
    count.textContent = opts.length
      ? `${opts.length} resultado${opts.length === 1 ? "" : "s"}`
      : "Sin coincidencias";
  }
  list.innerHTML = opts.length
    ? opts.slice(0, 120).map((m) => {
        const val = tendOptionValue(m);
        const label = tendMedLabel(m);
        const sub = m.medicamento_lista && normRegKey(m.medicamento_lista) !== normRegKey(label)
          ? m.medicamento_lista
          : "";
        return `
          <button type="button" class="tend-picker-item${val === selectedVal ? " is-active" : ""}"
            data-tend-pick="${escapeHtml(val)}" role="option" aria-selected="${val === selectedVal}">
            <span class="tend-picker-item-label">${escapeHtml(label)}</span>
            ${sub ? `<span class="tend-picker-item-sub">${escapeHtml(sub)}</span>` : ""}
            <span class="tend-picker-item-meta">${m.fechas ? `${m.fechas} fechas` : ""}${m.paises ? ` · ${m.paises} países` : ""}</span>
          </button>`;
      }).join("") + (opts.length > 120 ? `<p class="muted tend-picker-more">+${opts.length - 120} más; afina la búsqueda</p>` : "")
    : `<p class="muted tend-picker-empty">Ningún medicamento coincide.</p>`;
  list.hidden = !state.tendPickerOpen;
}

function abrirTendPicker() {
  state.tendPickerOpen = true;
  renderTendPickerList();
}

function cerrarTendPicker() {
  state.tendPickerOpen = false;
  const list = $("tendPickerList");
  if (list) list.hidden = true;
}

async function seleccionarTendMedicamento(val) {
  const parsed = parseTendOptionValue(val);
  if (!parsed.n || !parsed.producto_key) return;
  state.tendenciaN = parsed.n;
  state.tendenciaProductoKey = parsed.producto_key;
  const m = (TEND_CATALOG.medicamentos || []).find((x) => tendOptionValue(x) === val);
  const input = $("tendSearch");
  if (input && m) input.value = tendMedLabel(m);
  state.tendSearchQ = "";
  cerrarTendPicker();
  renderTendPickerList();
  await pintarTendenciaMedicamento(parsed.n, parsed.producto_key);
}

function renderTendHorizBars({ title, note, rows, max = 14, color = "#003eab", chartId = "bars" }) {
  const items = (rows || [])
    .map((r, idx) => ({
      label: String(r.label || r.pais || "—"),
      value: Number(r.valor ?? r.value ?? r.medicamentos ?? r.principios ?? 0),
      n_lista: r.n_lista ?? null,
      pais: r.pais ?? null,
      fecha: r.fecha ?? null,
      idx,
    }))
    .filter((r) => r.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, max);
  if (!items.length) {
    return `<article class="tend-insight-card"><h3>${escapeHtml(title)}</h3><p class="muted">Sin datos.</p></article>`;
  }
  const vmax = Math.max(...items.map((i) => i.value), 1);
  const barH = 22;
  const gap = 8;
  const labelW = 168;
  const chartW = 380;
  const valueW = 44;
  const totalW = labelW + chartW + valueW + 20;
  const h = items.length * (barH + gap) + 6;
  const bars = items.map((item, i) => {
    const y = i * (barH + gap);
    const w = Math.max(4, (item.value / vmax) * chartW);
    const short = item.label.length > 28 ? `${item.label.slice(0, 26)}…` : item.label;
    const insightKey = item.n_lista != null && String(item.n_lista).trim() !== ""
      ? String(item.n_lista)
      : item.pais ?? item.fecha ?? item.label;
    return `
      <g class="tend-bar-row tend-bar-hit" role="button" tabindex="0"
        data-tend-insight-chart="${escapeHtml(chartId)}"
        data-tend-insight-key="${escapeHtml(String(insightKey))}"
        data-tend-insight-label="${escapeHtml(item.label)}"
        data-tend-insight-value="${item.value}"
        aria-label="${escapeHtml(item.label)}: ${item.value}. Ver detalle">
        <rect x="0" y="${y - 2}" width="${totalW}" height="${barH + 4}" fill="transparent"/>
        <text x="0" y="${y + barH - 5}" class="tend-bar-label">${escapeHtml(short)}</text>
        <rect x="${labelW}" y="${y}" width="${w.toFixed(1)}" height="${barH}" rx="4" fill="${color}" opacity="0.88"/>
        <text x="${labelW + chartW + 8}" y="${y + barH - 5}" class="tend-bar-value">${item.value}</text>
      </g>`;
  }).join("");
  return `
    <article class="tend-insight-card">
      <h3>${escapeHtml(title)}</h3>
      ${note ? `<p class="muted tend-insight-note">${note}</p>` : ""}
      <p class="muted tend-insight-hint">Clic en una barra para ver el detalle.</p>
      <svg viewBox="0 0 ${totalW} ${h}" class="tend-bar-svg" role="img" aria-label="${escapeHtml(title)}">
        ${bars}
      </svg>
    </article>`;
}

function renderTendFechaTable({ title, note, rows }) {
  const items = (rows || []).map((r) => ({
    fecha: String(r.fecha || "").slice(0, 10),
    label: fmtFecha(r.fecha),
    medicamentos: Number(r.medicamentos || 0),
    principios: Number(r.principios || 0),
    paises: Number(r.paises || 0),
    puntos: Number(r.puntos || 0),
  })).filter((r) => r.fecha && (r.medicamentos > 0 || r.puntos > 0));
  if (!items.length) {
    return `<article class="tend-insight-card tend-insight-card--wide"><h3>${escapeHtml(title)}</h3><p class="muted">Sin datos.</p></article>`;
  }
  return `
    <article class="tend-insight-card tend-insight-card--wide">
      <h3>${escapeHtml(title)}</h3>
      ${note ? `<p class="muted tend-insight-note">${note}</p>` : ""}
      <p class="muted tend-insight-hint">Clic en una fila para ver el detalle del día.</p>
      <div class="table-wrap tend-fecha-table-wrap">
        <table class="data data-static tend-fecha-table">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Medicamentos</th>
              <th>Principios</th>
              <th>Países</th>
              <th>Registros</th>
            </tr>
          </thead>
          <tbody>
            ${items.map((item) => `
              <tr class="tend-bar-hit" role="button" tabindex="0"
                data-tend-insight-chart="fecha"
                data-tend-insight-key="${escapeHtml(item.fecha)}"
                data-tend-insight-label="${escapeHtml(item.label)}"
                data-tend-insight-value="${item.medicamentos}"
                aria-label="${escapeHtml(item.label)}: ${item.medicamentos} medicamentos. Ver detalle">
                <td><strong>${escapeHtml(item.label)}</strong></td>
                <td>${item.medicamentos}</td>
                <td>${item.principios}</td>
                <td>${item.paises}</td>
                <td>${item.puntos}</td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>
    </article>`;
}

function tendProgramaSlices() {
  const comp = D?.comparativo || [];
  const progMap = new Map(comp.map((r) => [Number(r.n), r.programa]));
  const meds = TEND_CATALOG.medicamentos || [];
  const counts = { DAMAC: 0, FOMAC: 0, Otros: 0 };
  for (const m of meds) {
    const p = String(progMap.get(Number(m.n_lista)) || "");
    if (p.includes("FOMAC")) counts.FOMAC += 1;
    else if (p === "DAMAC") counts.DAMAC += 1;
    else counts.Otros += 1;
  }
  return [
    { label: "DAMAC", value: counts.DAMAC, color: "#003eab" },
    { label: "FOMAC", value: counts.FOMAC, color: "#0f766e" },
    { label: "Sin programa", value: counts.Otros, color: "#94a3b8" },
  ].filter((s) => s.value > 0);
}

function renderTendPieChart({ title, note, slices, hero = false }) {
  const items = (slices || []).filter((s) => Number(s.value) > 0);
  const total = items.reduce((n, s) => n + Number(s.value), 0);
  const cardCls = hero
    ? "tend-insight-card tend-insight-card--pie tend-insight-card--pie-hero"
    : "tend-insight-card tend-insight-card--pie";
  if (!total) {
    return `<article class="${cardCls}"><h3>${escapeHtml(title)}</h3><p class="muted">Sin datos.</p></article>`;
  }
  const cx = 92;
  const cy = 92;
  const r = 68;
  const ir = 38;
  let angle = -Math.PI / 2;
  const arcs = items.map((slice) => {
    const frac = Number(slice.value) / total;
    const a1 = angle;
    const a2 = angle + frac * Math.PI * 2;
    angle = a2;
    const x1 = cx + r * Math.cos(a1);
    const y1 = cy + r * Math.sin(a1);
    const x2 = cx + r * Math.cos(a2);
    const y2 = cy + r * Math.sin(a2);
    const xi1 = cx + ir * Math.cos(a1);
    const yi1 = cy + ir * Math.sin(a1);
    const xi2 = cx + ir * Math.cos(a2);
    const yi2 = cy + ir * Math.sin(a2);
    const large = frac > 0.5 ? 1 : 0;
    const d = `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} L ${xi2} ${yi2} A ${ir} ${ir} 0 ${large} 0 ${xi1} ${yi1} Z`;
    const pct = (frac * 100).toFixed(1);
    return { d, color: slice.color || "#003eab", label: slice.label, value: slice.value, pct };
  });
  const legend = arcs.map((a) => `
    <li><span class="tend-pie-swatch" style="background:${a.color}"></span>
      <strong>${escapeHtml(a.label)}</strong>
      <span class="muted">${a.value} · ${a.pct}%</span>
    </li>`).join("");
  return `
    <article class="${cardCls}">
      <h3>${escapeHtml(title)}</h3>
      ${note ? `<p class="muted tend-insight-note">${note}</p>` : ""}
      <div class="tend-pie-wrap">
        <svg viewBox="0 0 184 184" class="tend-pie-svg" role="img" aria-label="${escapeHtml(title)}">
          ${arcs.map((a) => `<path d="${a.d}" fill="${a.color}" opacity="0.92"><title>${escapeHtml(a.label)}: ${a.value} (${a.pct}%)</title></path>`).join("")}
          <text x="${cx}" y="${cy - 2}" text-anchor="middle" class="tend-pie-center">${items.length}</text>
          <text x="${cx}" y="${cy + 14}" text-anchor="middle" class="tend-pie-center-sub">programas</text>
        </svg>
        <ul class="tend-pie-legend">${legend}</ul>
      </div>
    </article>`;
}

async function fetchTendenciasDetalle(params) {
  const q = new URLSearchParams();
  q.set("detalle", params.tipo);
  if (params.n_lista != null) q.set("n_lista", String(params.n_lista));
  if (params.pais) q.set("pais", params.pais);
  if (params.fecha) q.set("fecha", params.fecha);
  const urls = [
    `/api/tendencias?${q}`,
    `/api/tendencias/detalle?tipo=${encodeURIComponent(params.tipo)}${params.n_lista != null ? `&n_lista=${encodeURIComponent(params.n_lista)}` : ""}${params.pais ? `&pais=${encodeURIComponent(params.pais)}` : ""}${params.fecha ? `&fecha=${encodeURIComponent(params.fecha)}` : ""}`,
  ];
  let lastErr = null;
  for (const url of urls) {
    try {
      const r = await fetch(url, { cache: "no-store" });
      const text = await r.text();
      if (text.trimStart().startsWith("<")) {
        lastErr = new Error("La API devolvió HTML en lugar de JSON. Reinicie el servidor (servir.py).");
        continue;
      }
      const d = JSON.parse(text);
      if (!d?.ok) throw new Error(d?.error || `Error API (${r.status})`);
      return d;
    } catch (err) {
      lastErr = err;
    }
  }
  throw lastErr || new Error("No se pudo cargar el detalle");
}

function tendInsightPrincipioN(key, label) {
  const n = Number(key);
  if (!Number.isNaN(n) && n > 0) return n;
  const ind = TEND_CATALOG.indicadores || {};
  const lbl = String(label || "").trim().toLowerCase();
  const hit = (ind.meds_por_principio || []).find(
    (r) => String(r.label || "").trim().toLowerCase() === lbl,
  );
  if (hit?.n_lista != null) return Number(hit.n_lista);
  return null;
}

function tendInsightModalLoading(title) {
  return `
    <div class="tend-insight-modal-head">
      <h2 id="tendInsightTitle">${escapeHtml(title || "Detalle")}</h2>
    </div>
    <p class="muted tend-insight-modal-loading">Cargando datos…</p>`;
}

function tendInsightModalError(msg) {
  return `<p class="muted tend-insight-modal-error">${escapeHtml(msg)}</p>`;
}

function tendInsightMedRows(meds, { showPais = false, showPrecio = false } = {}) {
  const rows = Array.isArray(meds) ? meds : [];
  if (!rows.length) {
    return `<p class="muted">No hay presentaciones en el historial para este criterio.</p>`;
  }
  return `
    <div class="table-wrap tend-insight-table-wrap">
      <table class="data data-static data-detalle">
        <thead>
          <tr>
            <th>Producto</th>
            <th>Concentración</th>
            <th>Presentación</th>
            ${showPais ? "<th>País</th>" : ""}
            ${showPrecio ? "<th>PVP min (USD)</th>" : "<th>Fechas</th><th>Países</th>"}
          </tr>
        </thead>
        <tbody>
          ${rows.map((m) => {
            const pickVal = tendOptionValue({ n_lista: m.n_lista, producto_key: m.producto_key });
            const precio = m.min_precio_usd != null ? usd.format(Number(m.min_precio_usd)) : "—";
            return `
              <tr class="tend-insight-row" data-tend-pick="${escapeHtml(pickVal)}" title="Ver tendencia de este producto">
                <td class="med">${escapeHtml(m.producto_label || m.nombre_comercial || "—")}</td>
                <td>${escapeHtml(m.concentracion || "—")}</td>
                <td>${escapeHtml(m.presentacion || "—")}</td>
                ${showPais ? `<td>${escapeHtml(m.pais || "—")}</td>` : ""}
                ${showPrecio
                  ? `<td>${precio}${m.farmacia ? `<div class="muted" style="font-size:11px">${escapeHtml(m.farmacia)}</div>` : ""}</td>`
                  : `<td>${Number(m.fechas || 0)}</td><td>${Number(m.paises || 0)}</td>`}
              </tr>`;
          }).join("")}
        </tbody>
      </table>
    </div>
    <p class="muted tend-insight-modal-foot">${rows.length} presentación${rows.length === 1 ? "" : "es"}. Clic en una fila para abrir su gráfico.</p>`;
}

function tendInsightStatsHtml(items) {
  const rows = Array.isArray(items) ? items.filter((x) => x) : [];
  if (!rows.length) return "";
  return `
    <div class="tend-insight-stats tend-insight-stats--modal">
      ${rows.map((it) => `
        <article>
          <span>${escapeHtml(it.label)}</span>
          <strong>${escapeHtml(String(it.value))}</strong>
        </article>`).join("")}
    </div>`;
}

async function openTendInsightModal(chartId, key, label, value) {
  const modal = $("tendInsightModal");
  const body = $("tendInsightBody");
  if (!modal || !body) return;
  body.innerHTML = tendInsightModalLoading(label);
  openModalEl(modal);
  const ind = TEND_CATALOG.indicadores || {};
  try {
    if (chartId === "principio") {
      const n = tendInsightPrincipioN(key, label);
      if (!n) throw new Error("No se identificó el principio activo.");
      const d = await fetchTendenciasDetalle({ tipo: "principio", n_lista: n });
      const meds = d.medicamentos || [];
      body.innerHTML = `
        <div class="tend-insight-modal-head">
          <h2 id="tendInsightTitle">${escapeHtml(label)}</h2>
          <p class="muted">Principio activo · <strong>${meds.length}</strong> presentación${meds.length === 1 ? "" : "es"} en el historial (marca + dosis + forma).</p>
        </div>
        ${tendInsightStatsHtml([
          { label: "Presentaciones", value: meds.length },
          { label: "Nº lista", value: n },
          { label: "En catálogo visible", value: (TEND_CATALOG.medicamentos || []).filter((m) => Number(m.n_lista) === n).length || "—" },
        ])}
        ${tendInsightMedRows(meds)}`;
      return;
    }
    if (chartId === "pais-principios" || chartId === "pais-meds" || chartId === "pais-farm") {
      const pais = String(key || label || "").trim();
      const d = await fetchTendenciasDetalle({ tipo: "pais", pais });
      const row = d.resumen || (ind.por_pais || []).find((x) => String(x.pais) === pais) || {};
      const fd = d.fecha ? fmtFecha(d.fecha) : "—";
      const meds = d.medicamentos || [];
      body.innerHTML = `
        <div class="tend-insight-modal-head">
          <h2 id="tendInsightTitle">${escapeHtml(label)}</h2>
          <p class="muted">Snapshot del <strong>${escapeHtml(fd)}</strong> · ${meds.length} presentación${meds.length === 1 ? "" : "es"} con precio.</p>
        </div>
        ${tendInsightStatsHtml([
          { label: "Principios activos", value: Number(row.principios || 0) },
          { label: "Medicamentos", value: Number(row.medicamentos || 0) },
          { label: "Farmacias", value: Number(row.farmacias || 0) },
        ])}
        ${tendInsightMedRows(meds, { showPrecio: true })}`;
      return;
    }
    if (chartId === "fecha") {
      const fd = String(key || "").slice(0, 10);
      const d = await fetchTendenciasDetalle({ tipo: "fecha", fecha: fd });
      const row = d.resumen || {};
      const meds = d.medicamentos || [];
      body.innerHTML = `
        <div class="tend-insight-modal-head">
          <h2 id="tendInsightTitle">${escapeHtml(label)}</h2>
          <p class="muted">Cobertura del historial en esa fecha de scrape.</p>
        </div>
        ${tendInsightStatsHtml([
          { label: "Medicamentos", value: Number(row.medicamentos || value || 0) },
          { label: "Principios activos", value: Number(row.principios || 0) },
          { label: "Países", value: Number(row.paises || 0) },
          { label: "Puntos guardados", value: Number(row.puntos || 0) },
        ])}
        ${tendInsightMedRows(meds, { showPais: true, showPrecio: true })}`;
      return;
    }
    body.innerHTML = `
      <div class="tend-insight-modal-head">
        <h2 id="tendInsightTitle">${escapeHtml(label)}</h2>
        <p class="muted">Total: <strong>${Number(value || 0)}</strong></p>
      </div>`;
  } catch (err) {
    console.error("tend insight modal", err);
    body.innerHTML = `
      <div class="tend-insight-modal-head">
        <h2 id="tendInsightTitle">${escapeHtml(label)}</h2>
      </div>
      ${tendInsightModalError(String(err.message || err))}`;
  }
}

function closeTendInsightModal() {
  const modal = $("tendInsightModal");
  if (!modal) return;
  modal.classList.remove("is-open");
  modal.hidden = true;
}

function buildTendIndicadoresLocal(medicamentos, principios, fechas) {
  const meds = Array.isArray(medicamentos) ? medicamentos : [];
  const prs = Array.isArray(principios) ? principios : [];
  const medsPorPrincipio = prs.length
    ? prs.map((p) => ({
        label: p.medicamento_lista || `Principio #${p.n_lista}`,
        valor: Number(p.medicamentos || 0),
        n_lista: p.n_lista,
      })).filter((r) => r.valor > 0)
    : Object.values(meds.reduce((acc, m) => {
        const n = Number(m.n_lista);
        if (!acc[n]) acc[n] = { label: m.medicamento_lista || `Principio #${n}`, valor: 0, n_lista: n };
        acc[n].valor += 1;
        return acc;
      }, {}));
  const paisesSet = new Set();
  meds.forEach((m) => { if (m.paises) paisesSet.add(String(m.paises)); });
  return {
    ultima_fecha: fechas?.length ? fechas[fechas.length - 1] : null,
    totales: {
      medicamentos: meds.length,
      principios: new Set(meds.map((m) => m.n_lista)).size,
      paises: Math.max(0, ...meds.map((m) => Number(m.paises || 0)), 0),
      fechas: fechas?.length || 0,
      puntos: meds.reduce((s, m) => s + Number(m.fechas || 0), 0),
    },
    meds_por_principio: medsPorPrincipio.sort((a, b) => b.valor - a.valor),
    por_pais: [],
    puntos_por_fecha: (fechas || []).map((f) => ({ fecha: f, medicamentos: 0, puntos: 0, principios: 0, paises: 0 })),
    parcial: true,
  };
}

async function cargarTendIndicadores(fallback = {}) {
  const el = $("tendInsights");
  if (!el) return;
  el.innerHTML = `<p class="muted tend-insights-loading">Cargando panorama del historial…</p>`;
  let ind = TEND_CATALOG.indicadores;
  if (!ind) {
    try {
      const r = await fetch("/api/tendencias/indicadores", { cache: "no-store" });
      const d = await r.json();
      if (d?.ok && d.indicadores) ind = d.indicadores;
    } catch (err) {
      console.warn("indicadores API", err);
    }
  }
  if (!ind || !ind.meds_por_principio?.length) {
    ind = buildTendIndicadoresLocal(
      fallback.medicamentos || TEND_CATALOG.medicamentos,
      fallback.principios || [],
      fallback.fechas || TEND_CATALOG.fechas,
    );
  }
  TEND_CATALOG.indicadores = ind;
  renderTendIndicadores(ind);
}

function renderTendIndicadores(ind) {
  const el = $("tendInsights");
  if (!el) return;
  if (!ind) {
    el.innerHTML = `<p class="muted">No hay datos de panorama todavía.</p>`;
    return;
  }
  const t = ind.totales || {};
  const ultima = ind.ultima_fecha ? fmtFecha(ind.ultima_fecha) : "—";
  const medsPrincipio = (ind.meds_por_principio || []).map((r) => ({
    label: r.label,
    valor: r.valor,
    n_lista: r.n_lista,
  }));
  const principiosPais = (ind.por_pais || [])
    .filter((r) => paisActivo(idPaisPorTexto(r.pais)))
    .map((r) => ({
    label: r.pais,
    valor: r.principios,
    pais: r.pais,
  }));
  const medsPais = (ind.por_pais || [])
    .filter((r) => paisActivo(idPaisPorTexto(r.pais)))
    .map((r) => ({
    label: r.pais,
    valor: r.medicamentos,
    pais: r.pais,
  }));
  const farmPais = (ind.por_pais || [])
    .filter((r) => paisActivo(idPaisPorTexto(r.pais)))
    .map((r) => ({
    label: r.pais,
    valor: r.farmacias,
    pais: r.pais,
  }));
  el.innerHTML = `
    <div class="tend-insights-head">
      <h2>Panorama del historial</h2>
      <p class="muted">Agregados del snapshot diario. Última fecha: <strong>${escapeHtml(ultima)}</strong>. Haz clic en las barras para ver el detalle.</p>
    </div>
    <div class="tend-insights-kpis tend-insights-kpis--top">
      <article class="tend-insight-kpi"><span>Medicamentos</span><strong>${Number(t.medicamentos || 0)}</strong></article>
      <article class="tend-insight-kpi"><span>Principios activos</span><strong>${Number(t.principios || 0)}</strong></article>
      <article class="tend-insight-kpi"><span>Países</span><strong>${Number(t.pais || t.paises || 0)}</strong></article>
      <article class="tend-insight-kpi"><span>Fechas en historial</span><strong>${Number(t.fechas || 0)}</strong></article>
    </div>
    <div class="tend-insights-grid">
      ${renderTendHorizBars({
        title: "Medicamentos por principio activo",
        note: "Presentaciones distintas (marca + dosis + forma) en todo el historial.",
        rows: medsPrincipio,
        max: 12,
        color: "#003eab",
        chartId: "principio",
      })}
      ${principiosPais.length ? renderTendHorizBars({
        title: "Principios activos por país",
        note: `Última fecha: ${ultima}. Misma cifra que en el tablero.`,
        rows: principiosPais,
        color: "#0f766e",
        chartId: "pais-principios",
      }) : ""}
      ${medsPais.length ? renderTendHorizBars({
        title: "Medicamentos por país",
        note: "Presentaciones con precio en la última fecha.",
        rows: medsPais,
        color: "#c45c26",
        chartId: "pais-meds",
      }) : ""}
      ${farmPais.length ? renderTendHorizBars({
        title: "Farmacias con dato por país",
        note: "Fuentes distintas que aportaron precio en la última fecha.",
        rows: farmPais,
        color: "#6b21a8",
        chartId: "pais-farm",
      }) : ""}
      ${(ind.puntos_por_fecha || []).some((r) => Number(r.medicamentos || r.puntos) > 0) ? renderTendFechaTable({
        title: "Medicamentos en el historial por fecha",
        note: "Evolución de cobertura (presentaciones con al menos un precio guardado).",
        rows: ind.puntos_por_fecha || [],
      }) : ""}
    </div>`;
}

function renderTendencias() {
  $("stage").innerHTML = `
    <article class="card tend-card">
      <div class="card-head">
        <div>
          <h2>Tendencias de precios</h2>
          <p class="muted" style="margin:6px 0 0">PVP mínimo por país según <strong>fecha_dato</strong>. Un país solo aparece en las fechas en que hubo scrape.</p>
        </div>
      </div>
      <div class="tend-toolbar">
        <label class="filter-field tend-pais-field">
          <span>País</span>
          <select class="selectish" id="tendPaisSelect" aria-label="Filtrar por país">
            <option value="todos">Todos los países</option>
          </select>
        </label>
        <label class="filter-field tend-picker-wrap">
          <span>Medicamento</span>
          <input type="search" class="search" id="tendSearch" placeholder="Buscar en el país seleccionado…" autocomplete="off" aria-autocomplete="list" aria-controls="tendPickerList" />
         
          <div class="tend-picker-list" id="tendPickerList" role="listbox" hidden></div>
        </label>
        <label class="tend-check tend-check--inline">
          <input type="checkbox" id="tendSoloMulti" ${state.tendSoloMulti ? "checked" : ""} />
          <span>Solo ≥2 fechas</span>
        </label>
        <p class="muted tend-note" id="tendMeta">Se actualiza con cada scrape diario.</p>
      </div>
      <div class="tend-chart-panel">
        <div class="tend-chart-meta" id="tendChartMeta">
          <div class="tend-kpis tend-kpis--compact" id="tendKpis"></div>
        </div>
        <div id="tendGaps" class="tend-gaps-inline"></div>
        <div class="tend-table-block">
          <h3 class="tend-table-title">Precios por fecha</h3>
          <div id="tendTable" class="tend-table"></div>
        </div>
      </div>
      <section class="tend-panorama" id="tendInsights" aria-label="Panorama del historial">
        <p class="muted tend-insights-loading">Cargando panorama del historial…</p>
      </section>
    </article>
  `;
  cargarTendenciasUI();
}

async function cargarTendenciasUI() {
  const table = $("tendTable");
  const meta = $("tendMeta");
  const input = $("tendSearch");
  const insights = $("tendInsights");
  if (!table) return;
  try {
    const r = await fetch("/api/tendencias", { cache: "no-store" });
    const d = await r.json();
    if (!d?.ok) throw new Error(d?.error || "API tendencias");
    const medicamentos = Array.isArray(d.medicamentos) ? d.medicamentos : [];
    const fechas = Array.isArray(d.fechas) ? d.fechas : [];
    TEND_CATALOG = {
      medicamentos,
      indicadores: d.indicadores || null,
      fechas,
    };
    actualizarTendPaisSelect();
    await cargarTendIndicadores({ medicamentos, principios: d.principios, fechas });
    let opts = tendMedicamentosVisibles();
    if (meta) {
      const vis = opts.length;
      const total = medicamentos.length;
      meta.textContent = fechas.length
        ? `${fechas.length} fecha${fechas.length === 1 ? "" : "s"} · ${vis}${vis !== total ? `/${total}` : ""} medicamento${vis === 1 ? "" : "s"} visibles`
        : "Aún no hay historial. Se creará con el próximo scrape / snapshot.";
    }
    if (!medicamentos.length) {
      const madre = overlayComparativo();
      TEND_CATALOG.medicamentos = madre.map((x) => ({
        n_lista: x.n,
        medicamento_lista: x.medicamento,
        producto_key: "sin_identificar",
        producto_label: x.medicamento,
        fechas: 0,
        paises: 0,
      }));
      opts = tendMedicamentosVisibles();
    }
    const selectedVal = tendSelectedValue();
    if (selectedVal && !opts.some((m) => tendOptionValue(m) === selectedVal)) {
      const first = opts[0];
      state.tendenciaN = first ? Number(first.n_lista) : null;
      state.tendenciaProductoKey = first ? String(first.producto_key || "") : null;
    } else if (!selectedVal && opts[0]) {
      state.tendenciaN = Number(opts[0].n_lista);
      state.tendenciaProductoKey = String(opts[0].producto_key || "");
    }
    const active = opts.find((m) => tendOptionValue(m) === tendSelectedValue()) || opts[0];
    if (input && active) input.value = tendMedLabel(active);
    renderTendPickerList();
    if (state.tendenciaN && state.tendenciaProductoKey) {
      await pintarTendenciaMedicamento(state.tendenciaN, state.tendenciaProductoKey);
    } else {
      table.innerHTML = `<p class="muted">Selecciona un medicamento del país elegido.</p>`;
      const kpis = $("tendKpis");
      const gapsEl = $("tendGaps");
      if (kpis) kpis.innerHTML = "";
      if (gapsEl) gapsEl.innerHTML = "";
    }
  } catch (err) {
    console.error(err);
    const msg = `No se pudo cargar tendencias (${escapeHtml(String(err.message || err))}).`;
    table.innerHTML = `<p class="muted">${msg}</p>`;
    if (insights) insights.innerHTML = `<p class="muted">${msg}</p>`;
  }
}

function actualizarTendPaisSelect() {
  const sel = $("tendPaisSelect");
  if (!sel) return;
  const cur = state.tendPaisFiltro || "todos";
  const opts = tendPaisesHistorialOpts();
  sel.innerHTML = `<option value="todos">Todos los países</option>${
    opts.map((p) => `<option value="${escapeHtml(p.id)}"${cur === p.id ? " selected" : ""}>${escapeHtml(p.nombre)}</option>`).join("")
  }`;
  if (cur !== "todos" && !opts.some((p) => p.id === cur)) {
    state.tendPaisFiltro = "todos";
    sel.value = "todos";
  }
}

function tendSeriesFiltradas(series) {
  const all = (Array.isArray(series) ? series : []).filter((s) => paisActivo(idPaisPorTexto(s.pais)));
  if (state.tendPaisFiltro && state.tendPaisFiltro !== "todos") {
    return all.filter((s) => idPaisPorTexto(s.pais) === state.tendPaisFiltro);
  }
  if (!state.tendPaises || !state.tendPaises.length) return all;
  const set = new Set(state.tendPaises);
  return all.filter((s) => set.has(s.pais));
}

function tendVal(pt) {
  if (!pt) return null;
  const v = pt.precio_usd ?? pt.precio;
  if (v == null || Number.isNaN(Number(v))) return null;
  return Number(v);
}

/**
 * El historial solo guarda una fila cuando el precio cambia: cada punto cubre el
 * rango [fecha, vigente_hasta]. Buscar por fecha exacta dejaría huecos falsos.
 */
function tendPuntoEnFecha(serie, fd) {
  const dia = String(fd).slice(0, 10);
  const puntos = serie?.puntos || [];
  return puntos.find((p) => {
    const desde = String(p.fecha).slice(0, 10);
    const hasta = String(p.vigente_hasta || p.fecha).slice(0, 10);
    return desde <= dia && dia <= hasta;
  }) || null;
}

function tendGapsHtml(fechas, series) {
  const gaps = [];
  for (const s of series) {
    const missing = fechas.filter((fd) => tendVal(tendPuntoEnFecha(s, fd)) == null);
    if (missing.length && missing.length < fechas.length) {
      gaps.push(`<li><strong>${escapeHtml(s.pais)}</strong> sin dato: ${missing.map((f) => escapeHtml(fmtFecha(f))).join(", ")}</li>`);
    } else if (missing.length === fechas.length) {
      gaps.push(`<li><strong>${escapeHtml(s.pais)}</strong> sin puntos en el historial</li>`);
    }
  }
  if (!gaps.length) return "";
  return `<div class="tend-gaps"><p class="tend-gaps-title">Huecos en la serie</p><ul>${gaps.join("")}</ul></div>`;
}

function tendKpisHtml(titulo, subtitulo, fechas, series) {
  const last = fechas[fechas.length - 1];
  const first = fechas[0];
  let best = null;
  let worstDelta = null;
  series.forEach((s) => {
    const pts = fechas.map((fd) => tendVal(tendPuntoEnFecha(s, fd)));
    const lastV = pts[pts.length - 1];
    if (lastV != null && (!best || lastV < best.v)) best = { pais: s.pais, v: lastV };
    const firstV = pts.find((v) => v != null);
    const lastOk = [...pts].reverse().find((v) => v != null);
    if (firstV != null && lastOk != null && firstV > 0) {
      const pct = ((lastOk - firstV) / firstV) * 100;
      if (!worstDelta || Math.abs(pct) > Math.abs(worstDelta.pct)) {
        worstDelta = { pais: s.pais, pct, first: firstV, last: lastOk };
      }
    }
  });
  return `
    <article class="tend-kpi"><span>Medicamento</span><strong>${escapeHtml(titulo)}</strong>${subtitulo ? `<em>${escapeHtml(subtitulo)}</em>` : ""}</article>
    <article class="tend-kpi"><span>Fechas</span><strong>${fechas.length}</strong><em>${escapeHtml(fmtFecha(first))} → ${escapeHtml(fmtFecha(last))}</em></article>
    <article class="tend-kpi"><span>Más barato (última fecha)</span><strong>${best ? usd.format(best.v) : "—"}</strong><em>${best ? escapeHtml(best.pais) : ""}</em></article>
    <article class="tend-kpi"><span>Mayor variación</span><strong>${worstDelta ? `${worstDelta.pct >= 0 ? "+" : ""}${worstDelta.pct.toFixed(1)}%` : "—"}</strong><em>${worstDelta ? escapeHtml(worstDelta.pais) : "hace falta ≥2 puntos"}</em></article>
  `;
}

function tendPrecioLocal(pt) {
  if (!pt) return "—";
  const p = pt.precio;
  if (p == null || Number.isNaN(Number(p))) return "—";
  const n = Number(p);
  const m = String(pt.moneda || "").trim().toUpperCase();
  if (m === "USD") return usd.format(n);
  if (m === "DOP") return dop.format(n);
  return `${n.toLocaleString("es")}${m ? ` ${m}` : ""}`;
}

function tendDeltaHtml(prev, curr) {
  if (prev == null || curr == null || prev <= 0) return "—";
  const pct = ((curr - prev) / prev) * 100;
  if (Math.abs(pct) < 0.05) return `<span class="tend-delta">0.0%</span>`;
  const cls = pct > 0 ? "is-up" : "is-down";
  return `<span class="tend-delta ${cls}">${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%</span>`;
}

function renderTendenciaPreciosTable(fechas, series) {
  const prevByPais = {};
  const rows = [];
  for (const fd of fechas) {
    for (const s of series) {
      const pt = tendPuntoEnFecha(s, fd);
      const v = tendVal(pt);
      const prev = prevByPais[s.pais];
      rows.push({
        fd,
        pais: s.pais,
        pt,
        usd: v,
        delta: tendDeltaHtml(prev, v),
      });
      if (v != null) prevByPais[s.pais] = v;
    }
  }
  const showPais = series.length > 1;
  return `
    <div class="table-wrap">
      <table class="data data-static data-detalle tend-precios-table">
        <thead>
          <tr>
            <th>Fecha</th>
            ${showPais ? "<th>País</th>" : ""}
            <th>PVP local</th>
            <th>PVP (USD)</th>
            <th>Farmacia</th>
            <th>Variación</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((row) => `
            <tr>
              <td>${escapeHtml(fmtFecha(row.fd))}</td>
              ${showPais ? `<td>${escapeHtml(row.pais)}</td>` : ""}
              <td>${escapeHtml(tendPrecioLocal(row.pt))}</td>
              <td>${row.usd == null ? `<span class="muted" title="Sin scrape ese día">—</span>` : usd.format(row.usd)}</td>
              <td class="muted">${escapeHtml(row.pt?.farmacia || "—")}</td>
              <td>${row.delta}</td>
            </tr>`).join("")}
        </tbody>
      </table>
    </div>`;
}

function aplicarVistaTendencia() {
  const table = $("tendTable");
  const kpis = $("tendKpis");
  const gapsEl = $("tendGaps");
  if (!table || !TEND_DATA) return;
  const d = TEND_DATA;
  const seriesAll = (Array.isArray(d.series) ? d.series : []).filter((s) => paisActivo(idPaisPorTexto(s.pais)));
  const fechas = Array.isArray(d.fechas) ? d.fechas : [];
  const n = d.n_lista ?? state.tendenciaN;
  const titulo = d.producto_label || d.nombre_comercial || d.medicamento_lista || `Medicamento #${n}`;
  const subtitulo = d.medicamento_lista && normRegKey(d.medicamento_lista) !== normRegKey(titulo)
    ? `Principio: ${d.medicamento_lista}`
    : [d.concentracion, d.presentacion].filter(Boolean).join(" · ");

  const series = tendSeriesFiltradas(seriesAll);
  if (!fechas.length || !seriesAll.length) {
    table.innerHTML = `
      <div class="tend-empty">
        <h3>${escapeHtml(titulo)}</h3>
        <p class="muted">Todavía no hay puntos históricos.</p>
      </div>`;
    if (kpis) kpis.innerHTML = "";
    if (gapsEl) gapsEl.innerHTML = "";
    return;
  }
  if (kpis) kpis.innerHTML = tendKpisHtml(titulo, subtitulo, fechas, series);
  if (gapsEl) gapsEl.innerHTML = tendGapsHtml(fechas, seriesAll);
  table.innerHTML = series.length
    ? renderTendenciaPreciosTable(fechas, series)
    : `<p class="muted">Sin datos para el país seleccionado.</p>`;
}

async function pintarTendenciaMedicamento(n, productoKey) {
  const table = $("tendTable");
  if (!table) return;
  table.innerHTML = `<p class="muted">Cargando serie…</p>`;
  try {
    const qs = new URLSearchParams({
      n_lista: String(n),
      producto_key: String(productoKey || ""),
    });
    const r = await fetch(`/api/tendencias?${qs}`, { cache: "no-store" });
    const d = await r.json();
    if (!d?.ok) throw new Error(d?.error || "API");
    TEND_DATA = d;
    aplicarVistaTendencia();
  } catch (err) {
    console.error(err);
    table.innerHTML = `<p class="muted">Error al cargar serie (${escapeHtml(String(err.message || err))}).</p>`;
  }
}

function renderTendChartSvg(titulo, fechas, series, opts = {}) {
  const fullWidth = !!opts.fullWidth;
  const w = fullWidth ? 1100 : 920;
  const h = fullWidth ? 320 : 360;
  const pad = fullWidth ? { t: 20, r: 18, b: 44, l: 58 } : { t: 28, r: 24, b: 48, l: 56 };
  const iw = w - pad.l - pad.r;
  const ih = h - pad.t - pad.b;
  const vals = [];
  series.forEach((s) => (s.puntos || []).forEach((p) => {
    const v = tendVal(p);
    if (v != null) vals.push(v);
  }));
  if (!vals.length) {
    return `<div class="tend-chart-head"><h3>Comparativo</h3></div><p class="muted">Sin puntos para comparar.</p>`;
  }
  const ymin = 0;
  // Escala compacta: evita que un outlier aplaste el resto
  const sorted = [...vals].sort((a, b) => a - b);
  const p90 = sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * 0.9))];
  const rawMax = Math.max(...vals);
  const ymax = rawMax > p90 * 2.4 ? p90 * 1.35 : rawMax * 1.08;
  const y0 = ymin;
  const y1 = Math.max(ymax, 1);
  const xAt = (i) => pad.l + (fechas.length <= 1 ? iw / 2 : (i / (fechas.length - 1)) * iw);
  const yAt = (v) => {
    const capped = Math.min(Number(v), y1);
    return pad.t + ih - ((capped - y0) / (y1 - y0)) * ih;
  };
  const colors = ["#003eab", "#007eb8", "#0f766e", "#c45c26", "#6b21a8", "#1b7a45", "#9a5b00"];
  const paths = series.map((s, si) => {
    const pts = fechas.map((fd, i) => {
      const v = tendVal(tendPuntoEnFecha(s, fd));
      if (v == null) return null;
      return { x: xAt(i), y: yAt(v), v, fd, pais: s.pais, clipped: v > y1 };
    }).filter(Boolean);
    if (pts.length < 1) return "";
    // No unir huecos: tramos separados
    let d = "";
    let penUp = true;
    fechas.forEach((fd, i) => {
      const key = String(fd).slice(0, 10);
      const pt = pts.find((p) => String(p.fd).slice(0, 10) === key);
      if (!pt) {
        penUp = true;
        return;
      }
      d += `${penUp ? "M" : "L"}${pt.x.toFixed(1)},${pt.y.toFixed(1)} `;
      penUp = false;
    });
    const dots = pts.map((p) => `
      <circle class="tend-dot" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${fullWidth ? 4.5 : 4.5}"
        data-tip="${escapeHtml(p.pais)} · ${escapeHtml(fmtFecha(p.fd))} · ${usd.format(p.v)}${p.clipped ? " (fuera de escala)" : ""}"
        fill="${colors[si % colors.length]}"></circle>`).join("");
    return `<path d="${d.trim()}" fill="none" stroke="${colors[si % colors.length]}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>${dots}`;
  }).join("");
  const xLabels = fechas.map((fd, i) => {
    if (fechas.length > 8 && i % Math.ceil(fechas.length / 6) !== 0 && i !== fechas.length - 1) return "";
    return `<text x="${xAt(i)}" y="${h - 12}" text-anchor="middle" class="tend-axis">${escapeHtml(fmtFecha(fd))}</text>`;
  }).join("");
  const yTicks = 3;
  const yLabels = Array.from({ length: yTicks + 1 }, (_, i) => {
    const v = y0 + ((y1 - y0) * i) / yTicks;
    const y = yAt(v);
    return `
      <line x1="${pad.l}" x2="${w - pad.r}" y1="${y}" y2="${y}" class="tend-grid"/>
      <text x="${pad.l - 6}" y="${y + 3}" text-anchor="end" class="tend-axis">${usd.format(v)}</text>`;
  }).join("");
  const legend = series.map((s, i) => `
    <span class="tend-leg"><i style="background:${colors[i % colors.length]}"></i>${escapeHtml(s.pais)}</span>
  `).join("");
  return `
    <div class="tend-chart-head">
      <h3>Comparativo${rawMax > y1 ? " · escala compacta" : ""}</h3>
      <div class="tend-legend">${legend}</div>
    </div>
    <svg viewBox="0 0 ${w} ${h}" class="tend-svg${fullWidth ? " tend-svg--full" : ""}" role="img" preserveAspectRatio="xMidYMid meet">
      ${yLabels}
      ${paths}
      ${xLabels}
    </svg>
    <p class="muted sku-note" id="tendTip">${rawMax > y1 ? "Un valor alto quedó fuera de escala para no aplastar el resto. " : ""}Pasa el cursor sobre un punto para el detalle.</p>
  `;
}

function renderFuentes() {
  const datos = fuentesFarmaciasVivas();
  const tasasPais = tasasPaisesVivos();

  const tarjetaDato = (f) => {
    const meta = metaPaisPorTexto(f.pais);
    const fuenteId = f.fuente_id || null;
    const job = fuenteId ? JOBS_ESTADOS[fuenteId] : null;
    const busy = job && ["queued", "running"].includes(job.estado);
    return `
      <article class="source">
        <div class="source-top">
          <span class="source-flag">${meta.flag}</span>
          <span class="source-kicker">${escapeHtml(meta.full || f.pais)}</span>
        </div>
        <h3>${escapeHtml(f.farmacia)}</h3>
        ${f.que ? `<p>${escapeHtml(f.que)}</p>` : ""}
        <p class="source-meta">${escapeHtml(f.metodo)}${f.skus ? ` · ${f.skus} SKU en tabla` : ""}</p>
        <div class="source-actions">
          ${fuenteId ? `
            <button type="button" class="btn-refresh" data-enqueue="${escapeHtml(fuenteId)}" ${busy ? "disabled" : ""}>
              ${busy ? (job.estado === "running" ? "Actualizando…" : "En cola") : "Actualizar ahora"}
            </button>
            ${job ? etiquetaEstadoJob(job.estado) : ""}
            ${job?.mensaje && job.estado === "error" ? `<span class="muted source-job-msg">${escapeHtml(job.mensaje)}</span>` : ""}
            ${job?.fecha_fin && job.estado === "done" ? `<span class="muted source-job-msg">${escapeHtml(fmtFecha(job.fecha_fin))}</span>` : ""}
          ` : `<span class="muted">Sin scraper asociado</span>`}
        </div>
        ${f.link ? `<a href="${escapeHtml(f.link)}" target="_blank" rel="noreferrer">Abrir catálogo</a>` : ""}
      </article>`;
  };

  const tarjetaFx = (t) => {
    const etiqueta = campo(t, "país", "pais", "moneda") || "";
    const meta = metaPaisPorTexto(etiqueta);
    const valor = t["USD en moneda local"] ?? t.Valor ?? null;
    const que = campo(t, "qué tasa", "que tasa");
    const fecha = campo(t, "fecha");
    const banco = campo(t, "fuente");
    const link = campo(t, "link");
    const moneda = monedaDeEtiqueta(etiqueta) || "moneda local";
    const num = valor == null || valor === "" ? null : Number(valor);
    return `
      <article class="source">
        <div class="source-top">
          <span class="source-flag">${meta.flag}</span>
          <span class="source-kicker">${escapeHtml(meta.full || etiqueta)}</span>
        </div>
        <h3>${escapeHtml(banco || etiqueta)}</h3>
        <div class="source-rate">
          ${num == null || Number.isNaN(num) ? "—" : num.toLocaleString("es-DO", { maximumFractionDigits: 4 })}
          <small>${escapeHtml(moneda)} por 1 USD${fecha ? ` · ${escapeHtml(fmtFecha(fecha))}` : ""}</small>
        </div>
        ${que ? `<p>${escapeHtml(que)}</p>` : ""}
        ${link ? `<a href="${escapeHtml(link)}" target="_blank" rel="noreferrer">Ver fuente oficial</a>` : ""}
      </article>`;
  };

  const regFuenteCards = [
    {
      id: "fda_purple",
      kicker: "Estados Unidos · FDA",
      titulo: "FDA Purple Book",
      desc: "Productos biológicos licenciados (BLA, biosimilar, intercambiable).",
      link: "https://purplebooksearch.fda.gov/index.cfm?event=downloads",
    },
    {
      id: "fda_info",
      kicker: "Estados Unidos · FDA",
      titulo: "FDA openFDA / patentes",
      desc: "Indicaciones, Tentative Approvals, patentes Orange Book y Purple Book.",
      link: "https://open.fda.gov/",
    },
    {
      id: "ema_medicines",
      kicker: "Unión Europea · EMA",
      titulo: "EMA medicines",
      desc: "Catálogo oficial de medicamentos (INN, ATC, biosimilar, indicaciones).",
      link: "https://www.ema.europa.eu/en/medicines/download-medicine-data",
    },
  ].map((f) => {
    const job = JOBS_ESTADOS[f.id];
    const busy = job && ["queued", "running"].includes(job.estado);
    return `
      <article class="source">
        <div class="source-top">
          <span class="source-kicker">${escapeHtml(f.kicker)}</span>
        </div>
        <h3>${escapeHtml(f.titulo)}</h3>
        <p>${escapeHtml(f.desc)}</p>
        <div class="source-actions">
          <button type="button" class="btn-refresh" data-enqueue="${escapeHtml(f.id)}" ${busy ? "disabled" : ""}>
            ${busy ? (job.estado === "running" ? "Actualizando…" : "En cola") : "Actualizar ahora"}
          </button>
          ${job ? etiquetaEstadoJob(job.estado) : ""}
          ${job?.mensaje && job.estado === "error" ? `<span class="muted source-job-msg">${escapeHtml(job.mensaje)}</span>` : ""}
          ${job?.fecha_fin && job.estado === "done" ? `<span class="muted source-job-msg">${escapeHtml(fmtFecha(job.fecha_fin))}</span>` : ""}
        </div>
        <a href="${escapeHtml(f.link)}" target="_blank" rel="noreferrer">Abrir fuente</a>
      </article>`;
  }).join("");

  $("stage").innerHTML = `
    <div class="source-sections">
      <article class="card">
        <div class="card-head">
          <div>
            <h2>Fuentes de datos</h2>
            <p class="muted" style="margin:6px 0 0">PVP publicado en las farmacias. «Actualizar ahora» encola el scrape en el worker (sigue aunque recargues o cierres).</p>
          </div>
        </div>
        <div class="source-grid">
          ${datos.map(tarjetaDato).join("") || `<p class="muted" style="padding:18px">No hay fuentes de datos.</p>`}
        </div>
      </article>
      <article class="card">
        <div class="card-head">
          <div>
            <h2>Fuentes regulatorias</h2>
            <p class="muted" style="margin:6px 0 0">FDA (Purple Book / openFDA) y EMA (medicines XLSX). Misma cola durable en backend.</p>
          </div>
        </div>
        <div class="source-grid">${regFuenteCards}</div>
      </article>
      <article class="card">
        <div class="card-head">
          <div>
            <h2>Fuentes de tasa de cambio</h2>
            <p class="muted" style="margin:6px 0 0">Cuánto vale 1 dólar en DOP, ARS, BRL, COP y MXN. Con esa tasa se pasa el PVP a USD y a pesos dominicanos (BCRD venta).</p>
          </div>
        </div>
        <div class="source-grid">
          ${tasasPais.map(tarjetaFx).join("") || `<p class="muted" style="padding:18px">No hay tasas cargadas.</p>`}
        </div>
      </article>
    </div>
  `;
}

function renderMetodologia() {
  const tasas = tasasPaisesVivos();
  const cols = tasas.length ? Object.keys(tasas[0]) : ["País / moneda", "USD en moneda local", "Fuente"];
  $("stage").innerHTML = `
    <article class="card">
      <div class="card-head"><h2>Tasas locales del dólar</h2></div>
      <div class="table-wrap">
        <table class="data data-static">
          <thead><tr>${cols.map((c) => `<th>${escapeHtml(c)}</th>`).join("")}</tr></thead>
          <tbody>
            ${tasas.map((t) => `
              <tr>
                ${cols.map((c) => {
                  const v = t[c];
                  const s = v == null ? "" : String(v);
                  if (String(c).toLowerCase().includes("link") && s.startsWith("http")) {
                    return `<td class="med"><a href="${escapeHtml(s)}" target="_blank" rel="noreferrer">${escapeHtml(s)}</a></td>`;
                  }
                  return `<td class="med">${escapeHtml(s)}</td>`;
                }).join("")}
              </tr>`).join("")}
          </tbody>
        </table>
      </div>
    </article>
    <article class="card" style="margin-top:14px">
      <div class="card-head"><h2>Límites</h2></div>
      <div style="padding:8px 22px 20px">
        ${(D.notas || []).map((n) => `<p class="note">${escapeHtml(n)}</p>`).join("")}
      </div>
    </article>
  `;
}

const DOC_MODULOS = [
  {
    id: "tablero",
    titulo: "Tablero",
    resumen: "Vista de entrada al observatorio: panorama de cobertura por país antes de profundizar en precios o histórico.",
    secciones: [
      {
        titulo: "Qué muestra",
        parrafos: [
          "Tarjetas por país con el número de principios activos que tienen al menos un precio en la última fecha del historial (alineado con el módulo Tendencias).",
          "En cada tarjeta aparece la bandera, el nombre del país, las farmacias que aportaron datos en el snapshot vigente y el contador de principios activos.",
          "Si un país no tiene scrape en el día actual pero sí datos históricos, la tarjeta se marca con borde punteado y muestra cuántas presentaciones hay en el historial.",
        ],
      },
      {
        titulo: "Cómo usarlo",
        lista: [
          "Haz clic en una tarjeta de país para abrir el listado de principios activos con precio en ese mercado.",
          "Desde ese listado puedes filtrar por cobertura DAMAC/FOMAC y abrir la ficha de un medicamento.",
          "Usa el tablero para ver rápidamente qué países tienen cobertura y cuántos principios están monitoreados.",
        ],
      },
      {
        titulo: "Relación con otros módulos",
        lista: [
          "Los contadores de principios activos coinciden con el panorama del módulo Tendencias.",
          "La ficha que se abre desde un país conecta con Comparativo, Detalle e información regulatoria FDA/EMA.",
        ],
      },
    ],
  },
  {
    id: "comparativo",
    titulo: "Comparativo",
    resumen: "Tabla matriz de precios: un medicamento por fila y columnas por país con el PVP representativo en USD.",
    secciones: [
      {
        titulo: "Qué muestra",
        parrafos: [
          "Para cada principio activo (DAMAC/FOMAC) muestra el precio mínimo representativo por país en la misma presentación comparable.",
          "El PVP representativo usa la mediana cuando hay varios genéricos en un país; si solo hay uno, se toma el más barato.",
          "Solo se comparan presentaciones con la misma concentración, forma (± recubierto) y cantidad por empaque.",
        ],
      },
      {
        titulo: "Filtros disponibles",
        lista: [
          "Búsqueda por medicamento, concentración o país.",
          "Programa: DAMAC, FOMAC o todos.",
          "País con dato: cualquier país o uno específico.",
          "Cantidad de países: con par comparable (2+ países), sin par o todos.",
          "Orden por columna (medicamento, programa o PVP de un país).",
        ],
      },
      {
        titulo: "Cómo interpretar",
        lista: [
          "Celdas vacías o «—» indican que no hay precio comparable ese día en ese país.",
          "El equivalente en DOP en la ficha usa la tasa de venta del Banco Central de República Dominicana.",
          "Haz clic en una fila para abrir la ficha del medicamento con detalle por país y productos usados en la comparación.",
        ],
      },
    ],
  },
  {
    id: "detalle",
    titulo: "Detalle",
    resumen: "Listado granular de cada presentación encontrada en farmacia, sin agregación por principio.",
    secciones: [
      {
        titulo: "Qué muestra",
        parrafos: [
          "Una fila por producto scrapeado: marca comercial, farmacia, concentración, presentación y precios en USD, DOP y moneda local.",
          "Incluye enlace al dato original (página del producto en la farmacia cuando está disponible).",
        ],
      },
      {
        titulo: "Filtros y columnas",
        lista: [
          "Búsqueda por producto, concentración o molécula.",
          "Filtro por país.",
          "Columnas: medicamento, país, farmacia, producto, concentración, presentación, USD, DOP, precio local y fecha del dato.",
        ],
      },
      {
        titulo: "Cuándo usarlo",
        lista: [
          "Auditar un precio concreto o ver todas las variantes comerciales de un principio.",
          "Verificar la fuente web del scrape antes de tomar decisiones.",
          "Contrastar con el Comparativo, que resume un solo valor representativo por país.",
        ],
      },
    ],
  },
  {
    id: "tendencias",
    titulo: "Tendencias",
    resumen: "Evolución histórica de precios por medicamento y país según las fechas de scrape guardadas.",
    secciones: [
      {
        titulo: "Qué muestra",
        parrafos: [
          "Serie temporal del PVP mínimo por país para una presentación concreta (medicamento + dosis + forma + empaque).",
          "Tabla de precios por fecha con PVP local, USD, farmacia y variación porcentual respecto al punto anterior.",
          "Panorama del historial: agregados por principio, país y fecha de scrape.",
        ],
      },
      {
        titulo: "Filtros",
        lista: [
          "País: limita el buscador de medicamentos y las series mostradas.",
          "Medicamento: selector con todas las presentaciones del principio en el país elegido.",
          "Solo ≥2 fechas: oculta productos con un único punto histórico.",
        ],
      },
      {
        titulo: "Panorama del historial",
        lista: [
          "KPIs: medicamentos, principios, países y fechas en el repositorio.",
          "Gráficos horizontales por principio y por país (clic para ver detalle en modal).",
          "Tabla «Medicamentos en el historial por fecha» con cobertura por día de scrape.",
        ],
      },
      {
        titulo: "Huecos en la serie",
        parrafos: [
          "Si un país no aparece en una fecha, ese día no hubo scrape con precio para esa presentación. Los huecos no se interpolan.",
        ],
      },
    ],
  },
  {
    id: "fuentes",
    titulo: "Fuentes",
    resumen: "Origen de los datos de precios, tasas de cambio y jobs de actualización regulatoria.",
    secciones: [
      {
        titulo: "Farmacias y scrapers",
        parrafos: [
          "Cada tarjeta describe una fuente de precios: país, farmacia, método de extracción y cantidad de SKU en tabla.",
        ],
        lista: [
          "Botón «Actualizar ahora» encola un scrape inmediato (estado: en cola, ejecutando, listo o error).",
          "Enlace al catálogo público de la farmacia cuando existe.",
        ],
      },
      {
        titulo: "Tasas de cambio",
        parrafos: [
          "Tasas USD → moneda local usadas para convertir precios a dólares. República Dominicana usa la venta del BCRD para el equivalente en DOP.",
        ],
      },
      {
        titulo: "Fuentes regulatorias",
        lista: [
          "FDA Purple Book — biológicos BLA, biosimilares e intercambiables.",
          "FDA openFDA / patentes — indicaciones, Tentative Approvals, Orange Book y Purple Book.",
          "EMA medicines — catálogo europeo, EPAR, indicaciones en español cuando están disponibles.",
        ],
      },
    ],
  },
  {
    id: "ficha",
    titulo: "Ficha de medicamento (modal)",
    resumen: "Se abre desde el Tablero, el Comparativo o los enlaces regulatorios. No es un ítem del menú lateral, pero es parte central del flujo.",
    secciones: [
      {
        titulo: "Contenido",
        lista: [
          "Resumen del principio: programa DAMAC/FOMAC, presentación comparada y precios por país.",
          "Tabla de productos comparables que alimentan el comparador y lista de excluidos (marcas innovadoras, combinaciones, precios atípicos).",
          "Selector de información regulatoria: ficha FDA, ficha EMA o comparación FDA · EMA.",
        ],
      },
      {
        titulo: "FDA",
        lista: [
          "Purple Book / Orange Book según biológico o molécula pequeña.",
          "Indicaciones con enlaces a PDF DailyMed y Drugs@FDA.",
          "Patentes, exclusividades, tentativas y productos licenciados.",
        ],
      },
      {
        titulo: "EMA",
        lista: [
          "Medicamentos autorizados con INN, ATC, clase (Innovador, biosimilar, genérico, huérfano).",
          "Indicaciones desde EPAR en español (PDF oficial o traducción).",
        ],
      },
    ],
  },
];

function docGeneradoTexto() {
  const g = D?.generado || "";
  if (!g) return "Observatorio de medicamentos de alto costo · SISALRIL";
  try {
    const d = new Date(g);
    if (!Number.isNaN(d.getTime())) {
      return `Generado ${d.toLocaleDateString("es-DO", { dateStyle: "long" })} · Observatorio DAMAC/FOMAC · SISALRIL`;
    }
  } catch { /* ignore */ }
  return `Datos al ${String(g).slice(0, 10)} · Observatorio DAMAC/FOMAC · SISALRIL`;
}

function htmlDocSeccion(sec) {
  const parrafos = (sec.parrafos || []).map((p) => `<p>${escapeHtml(p)}</p>`).join("");
  const lista = sec.lista?.length
    ? `<ul>${sec.lista.map((it) => `<li>${escapeHtml(it)}</li>`).join("")}</ul>`
    : "";
  return `
    <section class="doc-block">
      <h3>${escapeHtml(sec.titulo)}</h3>
      ${parrafos}
      ${lista}
    </section>`;
}

function htmlDocModulo(mod, { exportMode = false } = {}) {
  const anchor = exportMode ? "" : ` id="doc-${mod.id}"`;
  return `
    <article class="doc-module"${anchor}>
      <header class="doc-module-head">
        <h2>${escapeHtml(mod.titulo)}</h2>
        <p class="doc-module-lead">${escapeHtml(mod.resumen)}</p>
      </header>
      ${(mod.secciones || []).map((s) => htmlDocSeccion(s)).join("")}
    </article>`;
}

function htmlDocumentacionBody({ exportMode = false, toc = false } = {}) {
  const tocHtml = toc
    ? `<nav class="doc-toc" aria-label="Índice">
        <h2>Índice</h2>
        <ol>
          ${DOC_MODULOS.map((m) => `<li><a href="#doc-${m.id}">${escapeHtml(m.titulo)}</a></li>`).join("")}
        </ol>
      </nav>`
    : "";
  return `
    <header class="doc-hero">
      <h1>Documentación del observatorio</h1>
      <p class="doc-hero-sub">${escapeHtml(docGeneradoTexto())}</p>
      <p class="muted">Guía de los módulos de la plataforma (excepto Metodología). Los precios son PVP al consumidor; la conversión a USD usa la tasa vigente de cada país.</p>
    </header>
    ${tocHtml}
    <div class="doc-modules">
      ${DOC_MODULOS.map((m) => htmlDocModulo(m, { exportMode })).join("")}
    </div>`;
}

function renderDocumentacion() {
  $("stage").innerHTML = `
    <article class="card doc-card">
      <div class="card-head doc-card-head">
        <div>
          <h2>Guía de módulos</h2>
          <p class="muted" style="margin:6px 0 0">Descripción de Tablero, Comparativo, Detalle, Tendencias, Fuentes y la ficha de medicamento.</p>
        </div>
        <div class="doc-export-actions">
          <button type="button" class="btn-doc-export" id="btnDocPdf" title="Exportar documentación en PDF">
            <span>Exportar PDF</span>
          </button>
          <button type="button" class="btn-doc-export btn-doc-export--word" id="btnDocWord" title="Exportar documentación en Word">
            <span>Exportar Word</span>
          </button>
        </div>
      </div>
      <div class="doc-body" id="docBody">
        ${htmlDocumentacionBody({ toc: true })}
      </div>
      <div id="docExportRoot" class="doc-export-root" hidden aria-hidden="true">
        ${htmlDocumentacionBody({ exportMode: true })}
      </div>
    </article>`;
}

function downloadBlob(blob, filename) {
  const a = document.createElement("a");
  const url = URL.createObjectURL(blob);
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}

function buildDocumentacionExportHtml() {
  const inner = htmlDocumentacionBody({ exportMode: true });
  return `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <title>Documentación · Observatorio alto costo</title>
  <style>
    body { font-family: "IBM Plex Sans", Arial, sans-serif; color: #1a2b3c; line-height: 1.5; margin: 24px 32px; font-size: 11pt; }
    h1 { color: #003eab; font-size: 22pt; margin: 0 0 8px; }
    h2 { color: #003eab; font-size: 14pt; margin: 24px 0 8px; border-bottom: 1px solid #d7e2ef; padding-bottom: 4px; }
    h3 { font-size: 11pt; margin: 14px 0 6px; color: #334455; }
    p { margin: 0 0 8px; }
    ul { margin: 0 0 10px; padding-left: 20px; }
    li { margin-bottom: 4px; }
    .doc-hero-sub { color: #5a6b7c; font-size: 10pt; }
    .doc-module { margin-bottom: 20px; page-break-inside: avoid; }
    .doc-module-lead { color: #445566; margin: 0 0 10px; }
    .muted { color: #6b7c8d; font-size: 10pt; }
  </style>
</head>
<body>
  ${inner}
</body>
</html>`;
}

function exportDocumentacionWord() {
  const html = buildDocumentacionExportHtml();
  const blob = new Blob(["\ufeff", html], { type: "application/msword;charset=utf-8" });
  const stamp = new Date().toISOString().slice(0, 10);
  downloadBlob(blob, `documentacion-observatorio-alto-costo-${stamp}.doc`);
}

async function loadHtml2Pdf() {
  const src = "https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js";
  if (window.html2pdf) return window.html2pdf;
  await new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`);
    if (existing) {
      existing.addEventListener("load", () => resolve());
      if (window.html2pdf) resolve();
      return;
    }
    const s = document.createElement("script");
    s.src = src;
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("No se pudo cargar la librería PDF"));
    document.head.appendChild(s);
  });
  return window.html2pdf;
}

async function exportDocumentacionPdf() {
  const btn = $("btnDocPdf");
  const root = $("docExportRoot");
  if (!root) return;
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Generando PDF…";
  }
  try {
    const html2pdf = await loadHtml2Pdf();
    root.hidden = false;
    const stamp = new Date().toISOString().slice(0, 10);
    await html2pdf()
      .set({
        margin: [12, 14, 14, 14],
        filename: `documentacion-observatorio-alto-costo-${stamp}.pdf`,
        image: { type: "jpeg", quality: 0.95 },
        html2canvas: { scale: 2, useCORS: true, logging: false },
        jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
        pagebreak: { mode: ["avoid-all", "css", "legacy"] },
      })
      .from(root)
      .save();
  } catch (err) {
    console.error(err);
    alert(`No se pudo generar el PDF: ${err.message || err}`);
  } finally {
    if (root) root.hidden = true;
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = "<span>Exportar PDF</span>";
    }
  }
}

function filasTablaSku(filas, normalizarPresentacion = false, group = "sku") {
  if (!filas.length) return `<p class="muted">Ninguna en este grupo.</p>`;
  const st = skuTableState(group);
  const q = String(st.q || "").trim().toLowerCase();
  let rows = filas.map((f) => {
    const paisId = idPaisPorTexto(f.pais);
    const meta = paisId ? (PAIS_UI[paisId] || {}) : {};
    const presentacion = normalizarPresentacion
      ? (presentacionClave(f) || presentacionComparable(f) || f.presentacion || "—")
      : (presentacionClave(f) || f.presentacion || "—");
    const precioUsd = aUsd(f.precio, f.moneda);
    const cant = cantidadUnidadesDe(f);
    return {
      ...f,
      _paisId: paisId,
      _paisNombre: meta.nombre || meta.full || f.pais || "",
      _presentacion: presentacion,
      _concentracion: concentracionClave(f) || f.concentracion || "",
      _precio_usd: precioUsd,
      _precio_usd_unidad: precioUsd != null && cant > 0 ? precioUsd / cant : null,
      _cantidad: cant,
    };
  });
  if (q) {
    rows = rows.filter((f) =>
      [
        f._paisNombre,
        f.pais,
        f.farmacia,
        f.laboratorio,
        f.nombre_comercial,
        f._concentracion,
        f._presentacion,
        f.observacion,
        f.moneda,
      ]
        .join(" ")
        .toLowerCase()
        .includes(q)
    );
  }
  rows.sort((a, b) => {
    const key = st.sort;
    let va;
    let vb;
    if (key === "precio_usd") {
      va = a._precio_usd ?? 1e12;
      vb = b._precio_usd ?? 1e12;
    } else if (key === "precio_local") {
      va = a.precio ?? 1e12;
      vb = b.precio ?? 1e12;
    } else if (key === "precio_unidad") {
      va = a._precio_usd_unidad ?? 1e12;
      vb = b._precio_usd_unidad ?? 1e12;
    } else if (key === "pais") {
      va = String(a._paisNombre || "").toLowerCase();
      vb = String(b._paisNombre || "").toLowerCase();
    } else if (key === "farmacia") {
      va = String(a.farmacia || "").toLowerCase();
      vb = String(b.farmacia || "").toLowerCase();
    } else if (key === "laboratorio") {
      va = String(a.laboratorio || "").toLowerCase();
      vb = String(b.laboratorio || "").toLowerCase();
    } else if (key === "producto") {
      va = String(a.nombre_comercial || "").toLowerCase();
      vb = String(b.nombre_comercial || "").toLowerCase();
    } else if (key === "concentracion") {
      va = String(a._concentracion || "").toLowerCase();
      vb = String(b._concentracion || "").toLowerCase();
    } else if (key === "presentacion") {
      va = String(a._presentacion || "").toLowerCase();
      vb = String(b._presentacion || "").toLowerCase();
    } else {
      va = 0;
      vb = 0;
    }
    if (va < vb) return -1 * st.dir;
    if (va > vb) return 1 * st.dir;
    return String(a.nombre_comercial || "").localeCompare(String(b.nombre_comercial || ""), "es");
  });
  const pg = paginate(rows, st.page, st.size);
  st.page = pg.page;
  SKU_DETAIL_CACHE[group] = pg.rows;
  const th = (key, label) =>
    `<th class="sortable ${st.sort === key ? "is-sorted" : ""}" data-sku-sort="${key}" data-sku-group="${escapeHtml(group)}">${label} ${skuSortMark(group, key)}</th>`;
  return `
    <div class="sku-table-head">
      <label class="filter-field">
        <span>Buscar</span>
        <input class="search search--compact" data-sku-q="${escapeHtml(group)}" placeholder="País, farmacia, producto…" value="${escapeHtml(st.q)}" />
      </label>
      ${skuPager(group, pg.page, pg.pages, pg.total, pg.start, st.size)}
    </div>
    <div class="table-wrap table-wrap--modal-flow">
      <table class="data data-static sku-grid">
        <thead>
          <tr>
            ${th("pais", "País")}
            ${th("farmacia", "Farmacia")}
            ${th("laboratorio", "Laboratorio")}
            ${th("producto", "Producto")}
            ${th("concentracion", "Concentración")}
            ${th("presentacion", "Presentación")}
            ${th("precio_usd", "USD")}
            ${normalizarPresentacion ? th("precio_unidad", "USD/ud") : ""}
            ${th("precio_local", "Local")}
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          ${pg.rows.map((f, idx) => {
            const ambiguo = esDatoAmbiguo(f);
            const paisCell = f._paisId
              ? `<span class="td-pais">${flagImg(f._paisId, "cover-flag td-flag")}<span class="td-pais-name">${cellTxt(f._paisNombre || f.pais)}</span></span>`
              : cellTxt(f.pais);
            return `
            <tr>
              <td>${paisCell}</td>
              <td>${cellTxt(f.farmacia)}</td>
              <td>${cellTxt(f.laboratorio)}</td>
              <td class="med">${cellTxt(f.nombre_comercial)}${ambiguo ? `<div class="cell-meta"><span class="badge badge--table revisar">dato ambiguo</span></div>` : ""}${group === "excluidos" && motivoExclusionComparable(f) ? `<div class="cell-meta"><span class="badge badge--table revisar">${escapeHtml(motivoExclusionComparable(f))}</span></div>` : ""}${f.observacion ? `<div class="cell-meta">${cellTxt(f.observacion, "")}</div>` : ""}</td>
              <td>${cellTxt(f._concentracion)}</td>
              <td>${cellTxt(f._presentacion)}</td>
              <td>${money(f._precio_usd)}</td>
              ${normalizarPresentacion ? `<td>${f._precio_usd_unidad != null ? money(f._precio_usd_unidad) : "—"}</td>` : ""}
              <td>${f.precio != null ? `${Number(f.precio).toLocaleString("en-US")} ${escapeHtml(f.moneda || "")}` : "—"}</td>
              <td>
                <div class="action-icons">
                  ${fuenteUrlVisible(f)
                    ? `<a class="icon-action" href="${escapeHtml(fuenteUrlVisible(f))}" target="_blank" rel="noreferrer" data-tooltip="Ver fuente" aria-label="Ver fuente">↗</a>`
                    : `<span class="icon-action is-disabled" data-tooltip="Sin fuente" aria-hidden="true">↗</span>`}
                  <button type="button" class="icon-action" data-sku-detail="${idx}" data-sku-group="${escapeHtml(group)}" data-tooltip="Ver detalle" aria-label="Ver detalle">i</button>
                </div>
              </td>
            </tr>`;
          }).join("") || `<tr><td colspan="${normalizarPresentacion ? 10 : 9}" class="muted">Sin resultados para “${escapeHtml(st.q)}”.</td></tr>`}
        </tbody>
      </table>
    </div>`;
}

function filasTablaCoberturaPais(filas) {
  if (!filas.length) return `<p class="muted">Ningún producto encontrado en este país.</p>`;
  const all = filasCoberturaPaisView(filas);
  const pg = paginate(all, state.cpage, state.csize);
  state.cpage = pg.page;
  COVER_DETAIL_CACHE = pg.rows;
  const pagerTop = pager("cover", pg.page, pg.pages, pg.total, pg.start, state.csize).replace('class="pager"', 'class="pager pager--compact"');
  return `
    <div class="cover-table-sticky">
    <div class="cover-table-topbar">
      <label class="filter-field">
        <span>Buscar</span>
        <input class="search search--compact" id="coverQ" placeholder="Buscar medicamento, farmacia, producto…" value="${escapeHtml(state.cq)}" />
      </label>
      ${pagerTop}
    </div>
    <div class="table-wrap table-wrap--cover">
      <table class="data data-static sku-grid sku-grid--cover">
        <thead>
          <tr>
            <th class="sortable ${state.csort === "medicamento" ? "is-sorted" : ""}" data-cover-sort="medicamento">Medicamento ${coverSortMark("medicamento")}</th>
            <th class="sortable ${state.csort === "farmacia" ? "is-sorted" : ""}" data-cover-sort="farmacia">Farmacia ${coverSortMark("farmacia")}</th>
            <th class="sortable ${state.csort === "laboratorio" ? "is-sorted" : ""}" data-cover-sort="laboratorio">Laboratorio ${coverSortMark("laboratorio")}</th>
            <th class="sortable ${state.csort === "producto" ? "is-sorted" : ""}" data-cover-sort="producto">Producto ${coverSortMark("producto")}</th>
            <th class="sortable ${state.csort === "concentracion" ? "is-sorted" : ""}" data-cover-sort="concentracion">Concentración ${coverSortMark("concentracion")}</th>
            <th class="sortable ${state.csort === "presentacion" ? "is-sorted" : ""}" data-cover-sort="presentacion">Presentación ${coverSortMark("presentacion")}</th>
            <th class="sortable ${state.csort === "precio_usd" ? "is-sorted" : ""}" data-cover-sort="precio_usd">USD ${coverSortMark("precio_usd")}</th>
            <th>Local</th>
            <th class="th-actions">Acciones</th>
          </tr>
        </thead>
        <tbody>
          ${pg.rows.map((f, idx) => {
            const u = f.precio_usd;
            return `
            <tr>
              <td class="med col-med"><div class="cell-clip">${cellTxt(f.medicamento_lista)}<div class="cell-meta">${badge(f.programa || "")}</div></div></td>
              <td class="col-farm"><div class="cell-clip">${cellTxt(f.farmacia)}</div></td>
              <td class="col-lab"><div class="cell-clip">${cellTxt(f.laboratorio)}</div></td>
              <td class="med col-prod"><div class="cell-clip">${cellTxt(f.nombre_comercial)}${esDatoAmbiguo(f) ? `<div class="cell-meta"><span class="badge badge--table revisar">dato ambiguo</span></div>` : ""}</div></td>
              <td class="col-conc"><div class="cell-clip">${cellTxt(f.concentracion)}</div></td>
              <td class="col-pres"><div class="cell-clip">${cellTxt(f.presentacion_norm)}</div></td>
              <td class="col-usd">${money(u)}</td>
              <td class="col-local">${f.precio != null ? `${Number(f.precio).toLocaleString("en-US")} ${escapeHtml(f.moneda || "")}` : "—"}</td>
              <td class="td-actions">
                <div class="action-icons">
                  ${fuenteUrlVisible(f) ? `<a class="icon-action" href="${escapeHtml(fuenteUrlVisible(f))}" target="_blank" rel="noreferrer" data-tooltip="Ver fuente" aria-label="Ver fuente">↗</a>` : `<span class="icon-action is-disabled" data-tooltip="Sin fuente" aria-hidden="true">↗</span>`}
                  <button type="button" class="icon-action" data-open="${Number(f.n_lista)}" data-tooltip="Ver comparación" aria-label="Ver comparación">⇄</button>
                  <button type="button" class="icon-action" data-cover-detail="${idx}" data-tooltip="Ver detalle" aria-label="Ver detalle">i</button>
                </div>
              </td>
            </tr>`;
          }).join("")}
        </tbody>
      </table>
    </div>
    </div>`;
}

function closeCoverListModal() {
  const el = $("coverListModal");
  if (!el) return;
  el.classList.remove("is-open");
  el.classList.remove("modal--fda");
  el.classList.remove("modal--reg");
  el.classList.remove("modal--cover-pa");
  el.hidden = true;
  closeRegCompareModal();
}

function openModalEl(modal) {
  if (!modal) return;
  modal.hidden = false;
  modal.classList.add("is-open");
  modal.scrollTop = 0;
}

function coverPaCardHtml(item, _tipo) {
  const enFarm = !!item.enFarmacia;
  const paisId = item.paisId || COVER_LIST_CACHE.paisId || "";
  return `
    <button type="button" class="cover-pa-card ${enFarm ? "is-on" : "is-off"}" data-open-reg="${item.n}" data-cover-pais="${escapeHtml(paisId)}" data-reg-from="cover"
      data-cover-pa-name="${escapeHtml((item.medicamento || "").toLowerCase())}"
      data-cover-pa-prog="${escapeHtml((item.programa || "").toLowerCase())}"
      data-cover-pa-ex="${escapeHtml((item.ejemplo || "").toLowerCase())}"
      data-cover-pa-farms="${escapeHtml((item.farms || []).join(" ").toLowerCase())}"
      data-cover-pa-status="${enFarm ? "en" : "sin"}">
      <div class="cover-pa-card-top">
        ${badge(item.programa)}
        ${enFarm
          ? `<span class="cover-pa-sku">${item.skus || 0} SKU</span>`
          : `<span class="cover-pa-miss">Sin cobertura</span>`}
      </div>
      <h3 class="cover-pa-name">${escapeHtml(item.medicamento)}</h3>
      ${enFarm && item.ejemplo ? `<p class="cover-pa-ex">${escapeHtml(item.ejemplo)}</p>` : ""}
      <p class="cover-pa-meta">${enFarm
        ? escapeHtml((item.farms || []).join(" · ") || "Sin farmacia")
        : `No está en ${escapeHtml(item.paisCorto || "este país")} · FDA / EMA disponible`}</p>
      <span class="cover-pa-cta">FDA / EMA →</span>
    </button>`;
}

function itemsCoverListActual() {
  const all = Array.isArray(COVER_LIST_CACHE.todos) && COVER_LIST_CACHE.todos.length
    ? COVER_LIST_CACHE.todos
    : [
        ...(COVER_LIST_CACHE.encontrados || []).map((x) => ({ ...x, enFarmacia: true })),
        ...(COVER_LIST_CACHE.faltan || []).map((x) => ({ ...x, enFarmacia: false })),
      ];
  const cov = COVER_LIST_CACHE.cobertura || "todos";
  if (cov === "en") return all.filter((x) => x.enFarmacia);
  if (cov === "sin") return all.filter((x) => !x.enFarmacia);
  return all;
}

function coverPaTabsHtml({ nEn, nSin, nMeds = null, cobertura = "todos", vista = "principios" }) {
  const enPrincipios = vista !== "medicamentos";
  const activa = (cov) => (enPrincipios && cobertura === cov ? " is-on" : "");
  return `
    <div class="filter-chips cover-pa-cov-chips" role="group" aria-label="Vista del país">
      <button type="button" class="chip${activa("todos")}" data-cover-pa-cov="todos">Todos (${nEn + nSin})</button>
      <button type="button" class="chip${activa("en")}" data-cover-pa-cov="en">En farmacia (${nEn})</button>
      <button type="button" class="chip${activa("sin")}" data-cover-pa-cov="sin">Sin cobertura (${nSin})</button>
      ${nMeds == null ? "" : `<button type="button" class="chip chip--meds${enPrincipios ? "" : " is-on"}" data-cover-pa-cov="medicamentos">Medicamentos (${nMeds})</button>`}
    </div>`;
}

function renderCoverPaGrid(items, tipo, emptyText) {
  if (!items.length) return `<p class="muted cover-pa-empty">${escapeHtml(emptyText || "Sin resultados.")}</p>`;
  return `<div class="cover-pa-grid" id="coverPaGrid">${items.map((it) => coverPaCardHtml(it, tipo)).join("")}</div>`;
}

function filtrarCoverPaCards(qRaw) {
  const q = String(qRaw || "").trim().toLowerCase();
  COVER_LIST_CACHE.q = q;
  const tipo = COVER_LIST_CACHE.tipo || "todos";
  const all = itemsCoverListActual();
  const filtered = !q
    ? all
    : all.filter((item) => {
        const blob = [
          item.medicamento,
          item.programa,
          item.ejemplo,
          ...(item.farms || []),
          item.paisCorto,
          item.enFarmacia ? "en farmacia catalogo" : "sin cobertura proximos",
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return blob.includes(q);
      });

  const countEl = $("coverPaCount");
  const emptyEl = $("coverPaFilterEmpty");
  const scroll = document.querySelector(".cover-pa-scroll");
  if (!scroll) return;

  const paint = () => {
    const prev = $("coverPaGrid");
    const emptyPrev = scroll.querySelector(".cover-pa-empty:not(#coverPaFilterEmpty)");
    if (prev) prev.remove();
    if (emptyPrev) emptyPrev.remove();

    if (!filtered.length) {
      const p = document.createElement("p");
      p.className = "muted cover-pa-empty";
      p.textContent = q
        ? "Ningún principio coincide con el filtro."
        : (COVER_LIST_CACHE.emptyText || "Sin resultados.");
      scroll.insertBefore(p, emptyEl || null);
    } else {
      const wrap = document.createElement("div");
      wrap.className = "cover-pa-grid";
      wrap.id = "coverPaGrid";
      wrap.innerHTML = filtered
        .map((it, i) => coverPaCardHtml(it, tipo).replace(
          'class="cover-pa-card',
          `style="--pa-i:${i % 12}" class="cover-pa-card`,
        ))
        .join("");
      scroll.insertBefore(wrap, emptyEl || null);
    }

    if (countEl) {
      const total = all.length;
      const shown = filtered.length;
      countEl.textContent = q || (COVER_LIST_CACHE.cobertura || "todos") !== "todos"
        ? `${shown} de ${total} principio${total === 1 ? "" : "s"}`
        : `${total} principio${total === 1 ? "" : "s"}`;
    }
    if (emptyEl) emptyEl.hidden = true;
  };

  if (typeof document.startViewTransition === "function") {
    document.startViewTransition(paint);
  } else {
    paint();
  }
}

function openCoverListModal({ pais, titulo, badgeTexto, items, emptyText, tipo, cobertura }) {
  const modal = $("coverListModal");
  const body = $("coverListBody");
  if (!modal || !body) return;
  modal.classList.remove("modal--fda");
  modal.classList.remove("modal--reg");
  modal.classList.add("modal--cover-pa");
  const listTipo = tipo || "todos";
  COVER_LIST_CACHE.tipo = listTipo;
  COVER_LIST_CACHE.cobertura = cobertura || "todos";
  COVER_LIST_CACHE.q = "";
  COVER_LIST_CACHE.emptyText = emptyText || "";
  if (Array.isArray(items) && items.length) {
    COVER_LIST_CACHE.todos = items;
  }
  const nEn = (COVER_LIST_CACHE.todos || []).filter((x) => x.enFarmacia).length;
  const nSin = (COVER_LIST_CACHE.todos || []).length - nEn;
  const cov = COVER_LIST_CACHE.cobertura;
  const rows = itemsCoverListActual();
  body.innerHTML = `
    <div class="modal-hero">
      <p class="crumb">Principios activos · lista completa</p>
      <h1 id="coverListTitle" class="modal-title-flag">${flagImg(pais.id, "cover-flag")} ${escapeHtml(titulo)}</h1>
      <div class="modal-hero-meta">
        <span class="badge ${badgeTexto.cls}">${escapeHtml(badgeTexto.label)}</span>
        <span id="coverPaCount">${rows.length} principio${rows.length === 1 ? "" : "s"}</span>
        <span>${nEn} en farmacia · ${nSin} sin cobertura</span>
        <span>${escapeHtml(pais.full)}</span>
      </div>
    </div>
    <div class="modal-body modal-body--cover modal-body--cover-pa">
      <div class="cover-pa-toolbar">
        <label class="filter-field cover-pa-search">
          <span>Filtrar principios</span>
          <input type="search" class="search" id="coverPaFilter" placeholder="Nombre, programa, farmacia o ejemplo…" autocomplete="off" />
        </label>
        ${coverPaTabsHtml({ nEn, nSin, cobertura: cov })}
        <p class="muted cover-pa-hint">Haz clic en cualquier principio para comparar FDA / EMA (con o sin precio de farmacia).</p>
      </div>
      <div class="cover-pa-scroll">
        ${renderCoverPaGrid(rows, listTipo, emptyText)}
        <p class="muted cover-pa-empty" id="coverPaFilterEmpty" hidden>Ningún principio coincide con el filtro.</p>
      </div>
    </div>
  `;
  modal.hidden = false;
  modal.classList.add("is-open");
  const input = $("coverPaFilter");
  if (input) {
    window.setTimeout(() => input.focus(), 40);
  }
}

function openCoverDetailModal(f) {
  const modal = $("coverListModal");
  const body = $("coverListBody");
  if (!modal || !body || !f) return;
  const usdVal = aUsd(f.precio, f.moneda);
  const paisId = idPaisPorTexto(f.pais);
  const meta = paisId ? paisUi({ id: paisId, nombre: f.pais }) : null;
  const alcance = alcanceDe(f);
  body.innerHTML = `
    <div class="modal-hero">
      <p class="crumb">Detalle del producto</p>
      <h1 id="coverListTitle">${escapeHtml(f.nombre_comercial || "Producto")}</h1>
      <div class="modal-hero-meta">
        <span>${escapeHtml(f.medicamento_lista || "—")}</span>
        <span>${escapeHtml(f.farmacia || "—")}</span>
        <span class="modal-title-flag" style="display:inline-flex;align-items:center;gap:8px">
          ${meta ? flagImg(paisId, "cover-flag") : ""} ${escapeHtml(meta?.full || f.pais || "—")}
        </span>
      </div>
    </div>
    <div class="modal-body">
      <div class="modal-grid">
        <article class="country-card"><h4>Laboratorio</h4><div class="price-lg" style="font-size:18px">${escapeHtml(f.laboratorio || "—")}</div></article>
        <article class="country-card"><h4>Concentración</h4><div class="price-lg" style="font-size:18px">${escapeHtml(concentracionClave(f) || f.concentracion || "—")}</div></article>
        <article class="country-card"><h4>Presentación</h4><div class="price-lg" style="font-size:18px">${escapeHtml(presentacionClave(f) || presentacionComparable(f) || f.presentacion || "—")}</div></article>
        <article class="country-card"><h4>Alcance</h4><div class="price-lg" style="font-size:18px">${escapeHtml(etiquetaAlcance(alcance))}</div></article>
        <article class="country-card"><h4>USD</h4><div class="price-lg">${usdVal != null ? usd.format(usdVal) : "—"}</div></article>
        <article class="country-card"><h4>Local</h4><div class="price-lg" style="font-size:18px">${f.precio != null ? `${Number(f.precio).toLocaleString("en-US")} ${escapeHtml(f.moneda || "")}` : "—"}</div></article>
        <article class="country-card"><h4>Fuente</h4><div class="price-lg" style="font-size:18px">${fuenteUrlVisible(f) ? `<a href="${escapeHtml(fuenteUrlVisible(f))}" target="_blank" rel="noreferrer">Abrir enlace</a>` : "Sin enlace"}</div></article>
        <article class="country-card"><h4>Calidad</h4><div class="price-lg" style="font-size:18px">${escapeHtml(f.calidad || "—")}</div></article>
      </div>
      ${f.observacion ? `<p class="modal-rule" style="margin-top:16px">${escapeHtml(f.observacion)}</p>` : ""}
      ${esDatoAmbiguo(f) ? `<p class="modal-rule" style="margin-top:16px"><span class="badge revisar">dato ambiguo</span> Este producto tiene señales de presentación ambigua y conviene revisarlo manualmente.</p>` : ""}
    </div>
  `;
  modal.hidden = false;
  modal.classList.add("is-open");
}

function openCoverModal(paisId) {
  const p = paisesUi().find((x) => x.id === paisId);
  if (!p) return;
  const changingPais = state.coverPais !== paisId;
  state.coverPais = paisId;
  state.selected = null;
  if (changingPais) state.cpage = 1;
  const madre = overlayComparativo();
  const base = filasTablaBase();
  const tiene = (n) => base.some((f) => f.n_lista === n && idPaisPorTexto(f.pais) === paisId);
  const encontrados = madre.filter((r) => tiene(r.n));
  const faltan = madre.filter((r) => !tiene(r.n));
  const filasPais = base.filter((f) => idPaisPorTexto(f.pais) === paisId);
  const farms = [...new Set(filasPais.map((f) => f.farmacia).filter(Boolean))];
  const itemEncontrado = (r) => {
    const skus = filasPais.filter((f) => f.n_lista === r.n);
    const farmsMed = [...new Set(skus.map((f) => f.farmacia).filter(Boolean))];
    const ej = skus[0]?.nombre_comercial || "";
    return {
      n: r.n,
      medicamento: r.medicamento,
      programa: r.programa,
      skus: skus.length,
      farms: farmsMed,
      ejemplo: ej,
      paisId: p.id,
    };
  };
  const itemFalta = (r) => ({
    n: r.n,
    medicamento: r.medicamento,
    programa: r.programa,
    paisCorto: p.corto,
  });
  const encontradosItems = encontrados.map((r) => ({ ...itemEncontrado(r), enFarmacia: true }));
  const faltanItems = faltan.map((r) => ({ ...itemFalta(r), enFarmacia: false, paisId: p.id }));
  const coberturaPrev = changingPais ? "todos" : (COVER_LIST_CACHE.cobertura || "todos");
  COVER_LIST_CACHE = {
    paisId: p.id,
    encontrados: encontradosItems,
    faltan: faltanItems,
    todos: [...encontradosItems, ...faltanItems],
    tipo: "todos",
    cobertura: coberturaPrev,
    q: "",
    emptyText: "No hay principios activos en la lista.",
  };
  if (changingPais) state.coverVista = "principios";
  const vista = state.coverVista === "medicamentos" ? "medicamentos" : "principios";
  const rows = itemsCoverListActual();

  const modal = $("fichaModal");
  modal?.classList.add("modal--cover-pa");
  $("modalBody").innerHTML = `
    <div class="modal-hero">
      <p class="crumb">Principios activos · lista DAMAC/FOMAC</p>
      <h1 id="modalTitle" class="modal-title-flag">${flagImg(p.id, "cover-flag")} ${escapeHtml(p.full)}</h1>
      <div class="modal-hero-row">
        <div class="modal-hero-meta">
          <span id="coverPaCount">${madre.length} principios activos</span>
          <span>${encontrados.length} en farmacia · ${faltan.length} sin cobertura</span>
          <span>${escapeHtml(farms.join(" · ") || "Sin farmacia")}</span>
        </div>
      </div>
    </div>
    <div class="modal-body modal-body--cover modal-body--cover-pa">
      <div class="cover-pa-toolbar${vista === "medicamentos" ? " cover-pa-toolbar--meds" : ""}">
        ${vista === "principios" ? `
        <label class="filter-field cover-pa-search">
          <span>Filtrar principios</span>
          <input type="search" class="search" id="coverPaFilter" placeholder="Nombre, programa, farmacia o ejemplo…" autocomplete="off" />
        </label>` : ""}
        ${coverPaTabsHtml({ nEn: encontrados.length, nSin: faltan.length, nMeds: filasPais.length, cobertura: COVER_LIST_CACHE.cobertura, vista })}
     
      </div>
      ${vista === "principios"
        ? `<div class="cover-pa-scroll">
            ${renderCoverPaGrid(rows, "todos", COVER_LIST_CACHE.emptyText)}
            <p class="muted cover-pa-empty" id="coverPaFilterEmpty" hidden>Ningún principio coincide con el filtro.</p>
          </div>`
        : `<div class="sku-table">${filasTablaCoberturaPais(filasPais)}</div>`}
    </div>
  `;
  modal.hidden = false;
  modal.classList.add("is-open");
}

function openModal(n) {
  const nNum = Number(n);
  const row = overlayComparativo().find((r) => Number(r.n) === nNum);
  if (!row || Number.isNaN(nNum)) return;
  if (state.selected !== nNum) {
    SKU_TABLE_STATE = {};
    SKU_DETAIL_CACHE = {};
  }
  state.selected = nNum;
  const fromCover = state.coverPais;
  const coverMeta = fromCover ? paisesUi().find((x) => x.id === fromCover) : null;
  const todas = filasVivas().filter((f) => Number(f.n_lista) === nNum);
  const grupos = gruposComparables(todas);
  const grupoPrincipal = row.clave_comparada
    ? (grupos.find((g) => g.clave === row.clave_comparada) || null)
    : (grupos[0] || null);
  const comparadasBrutas = row.clave_comparada ? filasEnClave(todas, row.clave_comparada) : (grupoPrincipal ? grupoPrincipal.filas : []);
  const comparadas = row.clave_comparada ? filasComparablesClave(todas, row.clave_comparada) : comparadasBrutas;
  const excluidasComparativo = comparadasBrutas.filter((f) => !comparadas.includes(f));
  const comparadasExtra = grupos.filter((g) => !grupoPrincipal || g.clave !== grupoPrincipal.clave);
  const clavesComparadas = new Set(grupos.map((g) => g.clave));
  const alcancePrincipal = grupoPrincipal ? String(grupoPrincipal.clave).split("||")[3] : "";
  const porUnidad = todas.filter((f) => {
    if (alcanceDe(f) !== "unidad" && !esPrecioUnidad(f)) return false;
    if (alcancePrincipal === "unidad" && claveDeFila(f) && clavesComparadas.has(claveDeFila(f))) return false;
    return !clavesComparadas.has(claveDeFila(f));
  });
  const otras = todas.filter((f) => {
    const k = claveDeFila(f);
    if (k && clavesComparadas.has(k)) return false;
    if (porUnidad.includes(f)) return false;
    return true;
  });
  const modal = $("fichaModal");
  modal?.classList.remove("modal--cover-pa");
  const heroMeta = `
        ${badge(row.programa)}
        ${row.par_comparable
          ? `<span>Comparando ${escapeHtml(row.presentacion_comparada)} · mínimo ${usd.format(row.min_usd)}</span>`
          : `<span>Sin par comparable (misma concentración y presentación) entre países</span>`}
        ${row.min_dop != null ? `<span>${dop.format(row.min_dop)}</span>` : ""}`;
  const bodyRest = `
      <div id="fichaRegChooser" class="ficha-reg-chooser"><p class="muted">Cargando información regulatoria…</p></div>
      <div class="sku-table">
        <h3>Comparables · ${escapeHtml(row.presentacion_comparada || "—")}</h3>
        <p class="muted sku-note">Productos que alimentan el comparador tras el filtro de calidad.</p>
        ${filasTablaSku(comparadas, true, "comparables")}
      </div>
      ${excluidasComparativo.length ? `
      <div class="sku-table sku-excluidos">
        <h3>No usados en el comparador <span class="badge revisar">${excluidasComparativo.length}</span></h3>
        <p class="muted sku-note">Marcas de referencia, combinaciones o precios atípicos respecto al resto del grupo.</p>
        ${filasTablaSku(excluidasComparativo, true, "excluidos")}
      </div>` : ""}
      ${comparadasExtra.map((g, i) => `
      <div class="sku-table">
        <h3>Otro grupo comparable · ${escapeHtml(etiquetaClave(g.clave))}</h3>
        ${filasTablaSku(g.filas, true, `extra-${i}`)}
      </div>`).join("")}
      ${porUnidad.length ? `
      <div class="sku-table sku-unidad">
        <h3>Precio por unidad <span class="badge revisar">no lote/caja</span></h3>
        <p class="muted sku-note">Estos PVP son por unidad. No se mezclan con precios de lote, caja o kit en la comparación principal.</p>
        ${filasTablaSku(porUnidad, false, "unidad")}
      </div>` : ""}
      ${otras.length ? `
      <div class="sku-table">
        <h3>Otras presentaciones / alcance desconocido (no comparadas)</h3>
        ${filasTablaSku(otras, false, "otras")}
      </div>` : ""}`;
  $("modalBody").innerHTML = `
    <div class="modal-hero">
      ${coverMeta ? `
        <button type="button" class="modal-back" data-back-cover="${coverMeta.id}">
          ← Principios activos · ${escapeHtml(coverMeta.nombre)}
        </button>
      ` : `<p class="crumb">Ficha comparativa</p>`}
      <h1 id="modalTitle">${escapeHtml(row.medicamento)}</h1>
      <div class="modal-hero-meta" id="fichaRegMeta">${heroMeta}</div>
    </div>
    <div class="modal-body">${bodyRest}</div>
  `;
  modal.hidden = false;
  modal.classList.add("is-open");
  emaDisponiblePara(nNum).then((tieneEma) => {
    if (state.selected !== nNum) return;
    const chooser = $("fichaRegChooser");
    if (chooser) {
      chooser.outerHTML = htmlRegulatorChooserCards(nNum, fromCover || "", "ficha", tieneEma);
    }
  });
}

const REG_LABEL_INNOVADOR = "Innovador";

function badgeInnovador() {
  return `<span class="badge is-fda-ref">${REG_LABEL_INNOVADOR}</span>`;
}

function regChipInnovador() {
  return `<span class="reg-chip is-ref">${REG_LABEL_INNOVADOR}</span>`;
}

function regClaseDisplay(text) {
  return String(text || "").replace(/\breferencia\b/gi, REG_LABEL_INNOVADOR);
}

function esEmaInnovador(ema) {
  return !ema?.es_biosimilar && !ema?.es_generic;
}

function badgeClaseFda(clase) {
  const c = String(clase || "").toLowerCase();
  if (c === "intercambiable") return `<span class="badge is-fda-inter">Intercambiable</span>`;
  if (c === "biosimilar") return `<span class="badge is-fda-bio">Biosimilar</span>`;
  if (c === "referencia" || c.includes("referencia")) return badgeInnovador();
  if (c === "generico" || c.includes("genéric")) return `<span class="badge is-fda-gen">Genérico</span>`;
  return clase ? `<span class="badge">${escapeHtml(regClaseDisplay(clase))}</span>` : "";
}

function htmlRegulatorChooserCards(n, paisId = "", from = "ficha", tieneEma = true) {
  const gridCls = tieneEma ? "reg-chooser-grid" : "reg-chooser-grid reg-chooser-grid--solo-fda";
  return `
    <div class="reg-chooser">
      <h3 class="reg-chooser-title">Información regulatoria</h3>
      <p class="muted sku-note">${tieneEma
        ? "Elige la agencia o la comparación general FDA · EMA de este principio."
        : "Sin registro EMA para este principio; solo ficha FDA."}</p>
      <div class="${gridCls}">
        <button type="button" class="reg-card reg-card--fda" data-open-fda="${n}" data-cover-pais="${escapeHtml(paisId || "")}" data-reg-from="${escapeHtml(from)}">
          <span class="reg-card-kicker">Estados Unidos</span>
          <span class="reg-card-name">FDA</span>
          <span class="reg-card-desc">Indicaciones, patentes y exclusividades.</span>
          <span class="reg-card-cta">Abrir ficha FDA →</span>
        </button>
        ${tieneEma ? `
        <button type="button" class="reg-card reg-card--ema" data-open-ema="${n}" data-cover-pais="${escapeHtml(paisId || "")}" data-reg-from="${escapeHtml(from)}">
          <span class="reg-card-kicker">Unión Europea</span>
          <span class="reg-card-name">EMA</span>
          <span class="reg-card-desc">Medicamentos autorizados, INN, ATC, indicaciones terapéuticas.</span>
          <span class="reg-card-cta">Abrir ficha EMA →</span>
        </button>
        <button type="button" class="reg-card reg-card--compare" data-open-reg-compare-general="${n}" data-cover-pais="${escapeHtml(paisId || "")}" data-reg-from="${escapeHtml(from)}">
          <span class="reg-card-kicker">FDA · EMA</span>
          <span class="reg-card-name">Comparar</span>
          <span class="reg-card-desc">Tabla comparativa del principio activo entre ambas agencias (clasificación, cobertura, fechas y más).</span>
          <span class="reg-card-cta">Abrir comparación →</span>
        </button>` : ""}
      </div>
    </div>`;
}

async function openRegulatorChooserModal(n, paisId, from = "cover") {
  const row = overlayComparativo().find((r) => r.n === Number(n));
  const pais = paisesUi().find((x) => x.id === paisId) || paisesUi().find((x) => x.id === state.coverPais);
  const modal = $("coverListModal");
  const body = $("coverListBody");
  if (!modal || !body) return;
  REG_CHOOSER = { n: Number(n), paisId: pais?.id || paisId || null, from };
  modal.classList.remove("modal--fda");
  modal.classList.add("modal--reg");
  modal.classList.remove("modal--cover-pa");
  const backHtml = from === "cover" && pais
    ? `<button type="button" class="modal-back" data-back-cover-list="${pais.id}">
        ← Principios activos · ${escapeHtml(pais.nombre)}
      </button>`
    : `<p class="crumb">Información regulatoria</p>`;
  body.innerHTML = `
    <div class="modal-hero">
      ${backHtml}
      <h1 id="coverListTitle">${escapeHtml(row?.medicamento || `Principio #${n}`)}</h1>
      <div class="modal-hero-meta">
        ${row ? badge(row.programa) : ""}
        <span>Cargando agencias…</span>
      </div>
    </div>
    <div class="modal-body">
      <p class="muted">Consultando cobertura EMA…</p>
    </div>
  `;
  modal.hidden = false;
  modal.classList.add("is-open");
  const tieneEma = await emaDisponiblePara(n);
  body.innerHTML = `
    <div class="modal-hero">
      ${backHtml}
      <h1 id="coverListTitle">${escapeHtml(row?.medicamento || `Principio #${n}`)}</h1>
      <div class="modal-hero-meta">
        ${row ? badge(row.programa) : ""}
        <span>${tieneEma ? "FDA · EMA" : "FDA"}</span>
      </div>
    </div>
    <div class="modal-body">
      ${htmlRegulatorChooserCards(n, pais?.id || paisId || "", from, tieneEma)}
    </div>
  `;
}

function badgeEstadoPat(estado) {
  const e = String(estado || "").toLowerCase();
  if (e === "vigente") return `<span class="badge is-fda-inter">Vigente</span>`;
  if (e === "expirada") return `<span class="badge revisar">Expirada</span>`;
  if (e === "vence_hoy") return `<span class="badge is-fda-ref">Vence hoy</span>`;
  return `<span class="badge">${escapeHtml(estado || "—")}</span>`;
}

const OB_SEARCH = "https://www.accessdata.fda.gov/scripts/cder/ob/";
const OB_INDEX = "https://www.accessdata.fda.gov/scripts/cder/ob/index.cfm";
const DRUGS_AT_FDA = "https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm";
const OB_DATA_FILES = "https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files";
const PURPLE_PATENT_LIST_URL = "https://purplebooksearch.fda.gov/index.cfm?event=patentlist";

function padObApplNo(applNo) {
  const an = String(applNo || "").trim();
  return /^\d+$/.test(an) ? an.padStart(6, "0") : an;
}

function padObProductNo(productNo) {
  const pn = String(productNo || "").trim() || "001";
  return /^\d+$/.test(pn) ? pn.padStart(3, "0") : pn;
}

function urlOrangeProducto(applType, applNo) {
  const at = String(applType || "").trim().toUpperCase();
  const an = padObApplNo(applNo);
  if (!at || !an) return "";
  return `${OB_SEARCH}results_product.cfm?Appl_Type=${encodeURIComponent(at)}&Appl_No=${encodeURIComponent(an)}`;
}

function urlOrangeProductoAncla(applType, applNo, productNo, obAnchor) {
  const base = urlOrangeProducto(applType, applNo);
  if (!base) return "";
  const anchor = String(obAnchor || "").trim();
  if (anchor) return `${base}#${anchor}`;
  const pn = String(productNo || "").trim();
  if (!pn) return base;
  const fallback = pn.replace(/^0+/, "") || pn;
  return `${base}#${fallback}`;
}

function urlOrangePatentInfo(applType, applNo, productNo) {
  const at = String(applType || "").trim().toUpperCase();
  const an = padObApplNo(applNo);
  const pn = padObProductNo(productNo);
  if (!at || !an) return "";
  return `${OB_SEARCH}patent_info.cfm?Product_No=${encodeURIComponent(pn)}&Appl_No=${encodeURIComponent(an)}&Appl_type=${encodeURIComponent(at)}`;
}

function urlOrangeIngrediente(nombre) {
  const ing = String(nombre || "").trim().toUpperCase();
  if (!ing) return `${OB_SEARCH}search_product.cfm`;
  return `${OB_SEARCH}results_product.cfm?Appl_Type=&Appl_No=&Ingredient=${encodeURIComponent(ing)}&Applicant=&Product_Name=&Search=Search`;
}

function urlPurpleProducto(blaNumber) {
  const bla = String(blaNumber || "").trim();
  if (!bla) return "";
  return `https://purplebooksearch.fda.gov/index.cfm?event=productdetails&blaNo=${encodeURIComponent(bla)}`;
}

/** Formato US con comas como en Purple Book Patent List (8,398,980). */
function formatPatentNoUsComma(patentNo) {
  const raw = String(patentNo || "").replace(/,/g, "").trim().replace(/\*PED$/i, "");
  if (!raw) return "";
  if (!/^\d+$/.test(raw)) return String(patentNo || "").trim();
  return raw.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/** Patent List con fragmento de texto (resalta el nº en la tabla, como Ctrl+F en Chrome/Edge). */
function urlPurplePatentListPatente(patentNo) {
  const display = formatPatentNoUsComma(patentNo);
  if (!display) return "";
  return `${PURPLE_PATENT_LIST_URL}#:~:text=${encodeURIComponent(display)}`;
}

/** Enlace oficial según fuente: Purple Book (BLA) u Orange Book (NDA/ANDA). */
function urlPatenteFda(p) {
  if (!p) return OB_INDEX;
  const fuente = String(p.fuente || "").toLowerCase();
  if (fuente === "purple_book" || p.bla_number) {
    const listPat = urlPurplePatentListPatente(p.patent_no);
    if (listPat) return listPat;
    const purple = urlPurpleProducto(p.bla_number);
    return purple || PURPLE_PATENT_LIST_URL;
  }
  if (fuente === "orange_book" && p.appl_type && p.appl_no) {
    return urlOrangeProductoAncla(p.appl_type, p.appl_no, p.product_no, p.ob_anchor)
      || urlOrangeProducto(p.appl_type, p.appl_no)
      || OB_INDEX;
  }
  for (const key of ["patent_url", "patent_info_url", "fuente_url", "detalle_producto_url"]) {
    const u = String(p[key] || "").trim();
    if (u) return u;
  }
  const google = String(p.google_patent_url || "").trim() || urlGooglePatenteUs(p.patent_no);
  return google || OB_INDEX;
}

function urlGooglePatenteUs(patentNo) {
  const raw = String(patentNo || "").replace(/,/g, "").trim();
  if (!raw) return "";
  const base = raw.replace(/\*PED$/i, "");
  if (/^\d+$/.test(base)) return `https://patents.google.com/patent/US${base}`;
  if (/^RE\d+$/i.test(base)) return `https://patents.google.com/patent/US${base.toUpperCase()}E1`;
  return `https://patents.google.com/?q=${encodeURIComponent(base)}+US+patent`;
}

function resumenPatentesOb(patentes, productosFda = []) {
  const pats = Array.isArray(patentes) ? patentes : [];
  const prods = Array.isArray(productosFda) ? productosFda : [];
  const nums = new Set(pats.map((p) => String(p.patent_no || "").trim()).filter(Boolean));
  const bases = new Set(
    [...nums].map((n) => n.replace(/\*PED$/i, "")).filter(Boolean)
  );
  return {
    productos: prods.length,
    entradas: pats.length,
    patentesUnicas: nums.size,
    patentesBase: bases.size,
    vigentes: pats.filter((p) => p.estado === "vigente").length,
    expiradas: pats.filter((p) => p.estado === "expirada").length,
  };
}

// function htmlResumenOrangeBook(info, patentes, productosFda) {
//   const res = resumenPatentesOb(patentes, productosFda);
//   const pats = Array.isArray(patentes) ? patentes : [];
//   const nPb = pats.filter((p) => String(p.fuente || "").toLowerCase() === "purple_book").length;
//   const nOb = pats.filter((p) => String(p.fuente || "").toLowerCase() === "orange_book").length;
//   const ing = String(info?.medicamento_lista || "").trim();
//   const bits = [];
//   if (res.patentesUnicas) {
//     bits.push(`<strong>${res.patentesUnicas}</strong> patente(s) distintas`);
//     if (res.entradas && res.entradas !== res.patentesUnicas) {
//       bits.push(`<strong>${res.entradas}</strong> entrada(s) en tabla`);
//     }
//   } else if (res.entradas) {
//     bits.push(`<strong>${res.entradas}</strong> entrada(s) de patente`);
//   }
//   const cuenta = bits.length ? bits.join(" · ") : "Sin patentes en FDA";
//   const fuenteLinks = [];
//   if (nPb) fuenteLinks.push(linkFuente(PURPLE_PATENT_LIST_URL, "Purple Book · Patent List"));
//   if (nOb) {
//     fuenteLinks.push(linkFuente(OB_INDEX, "Orange Book"));
//     if (ing) fuenteLinks.push(linkFuente(urlOrangeIngrediente(ing), "Búsqueda por ingrediente"));
//   }
//   if (!fuenteLinks.length) {
//     fuenteLinks.push(linkFuente(PURPLE_PATENT_LIST_URL, "Purple Book"));
//     fuenteLinks.push(linkFuente(OB_INDEX, "Orange Book"));
//   }
//   const fuentes = fuenteLinks.join(" · ");
//   return `<p class="muted sku-note">${cuenta}. Una entrada = patente + aplicación (+ variante <code>*PED</code> si aplica). Fuentes: ${fuentes} · ${btnFdaPatentesHelp()}</p>`;
// }

function btnFdaPatentesHelp(texto = "¿patentes?") {
  return `<button type="button" class="fda-src-help" data-open-fda-patentes-help title="Origen y significado de las patentes" aria-label="Explicar patentes FDA">${texto}</button>`;
}

function badgeClaseObProducto(p) {
  const c = String(p?.clase || "").toLowerCase();
  if (c.includes("generico") || c.includes("anda")) return `<span class="badge is-fda-gen">Genérico ANDA</span>`;
  if (c.includes("marca") || c.includes("nda")) return `<span class="badge is-fda-ref">Marca NDA</span>`;
  return `<span class="badge">${escapeHtml(p?.clase || p?.type || "—")}</span>`;
}

function datosProductoPatenteOb(p, productosFda = []) {
  const out = {
    ingredient: p?.ingredient || p?.active_ingredient || "",
    proprietary_name: p?.proprietary_name || p?.trade_name || "",
    df_route: p?.df_route || "",
    strength: p?.strength || "",
  };
  if (out.ingredient && out.proprietary_name) return out;
  const at = String(p?.appl_type || "").trim().toUpperCase();
  const an = padObApplNo(p?.appl_no);
  const pn = String(p?.product_no || "").trim();
  const match = (productosFda || []).find((pr) => {
    if (String(pr.appl_type || "").trim().toUpperCase() !== at) return false;
    if (padObApplNo(pr.appl_no) !== an) return false;
    if (pn && String(pr.product_no || "").trim() && String(pr.product_no).trim() !== pn) return false;
    return true;
  });
  if (match) {
    out.ingredient = out.ingredient || match.ingredient || match.substance || "";
    out.proprietary_name = out.proprietary_name || match.trade_name || "";
    out.df_route = out.df_route || match.df_route || "";
    out.strength = out.strength || match.strength || "";
  }
  if (String(p?.fuente || "").toLowerCase() === "purple_book") {
    out.ingredient = out.ingredient || p?.proper_name || "";
    out.proprietary_name = out.proprietary_name || p?.proprietary_name || "";
  }
  return out;
}

function htmlPatenteFdaLink(p) {
  const no = String(p?.patent_no || "").trim();
  if (!no) return "—";
  const url = urlPatenteFda(p);
  const fuente = String(p?.fuente || "").toLowerCase();
  const tip = fuente === "purple_book"
    ? "Ver en Purple Book · Patent List (resaltado del número)"
    : fuente === "orange_book"
      ? "Ver producto en Orange Book (FDA)"
      : "Ver fuente FDA de esta patente";
  return `<a href="${escapeHtml(url)}" target="_blank" rel="noopener" title="${escapeHtml(tip)}">${escapeHtml(no)}</a>`;
}

function urlFuenteDrugsAtFda(info) {
  const products = Array.isArray(info?.productos_fda) ? info.productos_fda : [];
  for (const p of products) {
    const at = String(p.appl_type || "").trim().toUpperCase();
    const an = padObApplNo(p.appl_no);
    if (at && an) {
      return `${DRUGS_AT_FDA}?event=overview.process&ApplNo=${encodeURIComponent(an)}`;
    }
    const bla = String(p.bla_number || "").trim();
    const blaNo = bla.match(/(\d+)/);
    if (blaNo) {
      return `${DRUGS_AT_FDA}?event=overview.process&ApplNo=${encodeURIComponent(blaNo[1])}`;
    }
  }
  const tentative = Array.isArray(info?.tentative) ? info.tentative : [];
  for (const t of tentative) {
    const appNo = String(t.application_number || "").trim();
    const m = appNo.match(/(\d+)/);
    if (m) return `${DRUGS_AT_FDA}?event=overview.process&ApplNo=${encodeURIComponent(m[1])}`;
  }
  const med = String(info?.medicamento_lista || "").trim();
  if (med) {
    return `${DRUGS_AT_FDA}?event=BasicSearch.process&searchTerm=${encodeURIComponent(med)}`;
  }
  return DRUGS_AT_FDA;
}

function urlPdfIndicacionesFda(info) {
  const pdf = String(info?.fuente_indicaciones_pdf || "").trim();
  if (pdf) return pdf;
  if (Array.isArray(info?.fuentes)) {
    for (const f of info.fuentes) {
      const url = String(f?.url || "").trim();
      const nombre = String(f?.nombre || "").toLowerCase();
      if (url && (/pdf/i.test(nombre) || /type=pdf/i.test(url))) return url;
    }
  }
  const dailymed = String(info?.fuente_indicaciones || "").trim();
  const m = dailymed.match(/setid=([0-9a-fA-F-]{36})/i)
    || String(info?.fuente_indicaciones_setid || "").match(/([0-9a-fA-F-]{36})/);
  if (m) {
    return `https://dailymed.nlm.nih.gov/dailymed/getFile.cfm?setid=${m[1]}&type=pdf&name=label.pdf`;
  }
  return "";
}

function htmlIndicacionesFda(info) {
  const pdfUrl = urlPdfIndicacionesFda(info);
  const drugsUrl = urlFuenteDrugsAtFda(info);
  const pdfChip = pdfUrl
    ? linkFuenteChip(pdfUrl, "PDF etiqueta FDA (inglés · DailyMed)", "fda")
    : "";
  if (!pdfUrl && !drugsUrl) {
    return `<p class="fda-ind-guide-missing muted">PDF de etiqueta no disponible en este snapshot.</p>`;
  }
  return `
    <div class="src-links fda-ind-guide-actions">
      ${pdfChip}
      ${linkFuenteChip(drugsUrl, "Drugs@FDA (accessdata.fda.gov)", "fda")}
      <button type="button" class="fda-src-help" data-open-fda-src-help title="¿De dónde sale este PDF?" aria-label="Explicar origen del PDF">¿origen?</button>
    </div>`;
}

function openFdaSrcHelpModal() {
  const el = $("fdaSrcHelpModal");
  if (!el) return;
  el.hidden = false;
  el.classList.add("is-open");
}

function closeFdaSrcHelpModal() {
  const el = $("fdaSrcHelpModal");
  if (!el) return;
  el.classList.remove("is-open");
  el.hidden = true;
}

function openFdaPatentesHelpModal() {
  const el = $("fdaPatentesHelpModal");
  if (!el) return;
  el.hidden = false;
  el.classList.add("is-open");
}

function closeFdaPatentesHelpModal() {
  const el = $("fdaPatentesHelpModal");
  if (!el) return;
  el.classList.remove("is-open");
  el.hidden = true;
}

const EMA_XLSX_URL = "https://www.ema.europa.eu/en/documents/report/medicines-output-medicines-report_en.xlsx";
const EMA_DATA_URL = "https://www.ema.europa.eu/en/medicines/download-medicine-data";

const SRC_LINK_ICON = `<svg class="src-link-chip-icon" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path fill="currentColor" d="M10 6.5v3.5a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1h3.5a.5.5 0 0 1 0 1H2v7h7V6.5a.5.5 0 0 1 1 0z"/><path fill="currentColor" d="M11 1.5a.5.5 0 0 0-.5-.5H7a.5.5 0 0 0 0 1h2.79L6.04 8.75a.5.5 0 0 0 .71.71L11 2.21V5a.5.5 0 0 0 1 0V1.5z"/></svg>`;

function btnEmaSrcHelp(texto = "¿origen?") {
  return `<button type="button" class="fda-src-help" data-open-ema-src-help title="Origen de los datos EMA" aria-label="Explicar origen de datos EMA">${texto}</button>`;
}

function fuentesEmaHtml() {
  return `
    <div class="src-links">
      ${linkFuenteChip(EMA_DATA_URL, "Datos de medicamentos EMA", "ema")}
      ${linkFuenteChip(EMA_XLSX_URL, "Excel de medicamentos", "xlsx")}
      ${btnEmaSrcHelp()}
    </div>`;
}

function openEmaSrcHelpModal() {
  const el = $("emaSrcHelpModal");
  if (!el) return;
  el.hidden = false;
  el.classList.add("is-open");
}

function closeEmaSrcHelpModal() {
  const el = $("emaSrcHelpModal");
  if (!el) return;
  el.classList.remove("is-open");
  el.hidden = true;
}

function linkFuente(url, label = "fuente") {
  if (!url) return "";
  return `<a href="${escapeHtml(url)}" target="_blank" rel="noopener">${escapeHtml(label)}</a>`;
}

function linkFuenteChip(url, label, kind = "default") {
  if (!url) return "";
  const cls = kind && kind !== "default" ? `src-link-chip src-link-chip--${kind}` : "src-link-chip";
  return `<a class="${cls}" href="${escapeHtml(url)}" target="_blank" rel="noopener">${SRC_LINK_ICON}<span>${escapeHtml(label)}</span></a>`;
}

function normRegKey(s) {
  return String(s || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}

function estadoEmaEs(status) {
  const m = {
    authorised: "Autorizado",
    withdrawn: "Retirado",
    "application withdrawn": "Solicitud retirada",
    refused: "Rechazado",
    opinion: "Opinión",
    lapsed: "Caducado",
    expired: "Expirado",
    revoked: "Revocado",
    suspended: "Suspendido",
    "opinion under re-examination": "Opinión en reexamen",
  };
  const k = String(status || "").trim().toLowerCase();
  return m[k] || status || "—";
}

async function traducirAes(texto, { timeoutMs = 120000 } = {}) {
  const raw = String(texto || "").trim();
  if (!raw) return "";
  if (TRAD_CACHE[raw] && !pareceInglesUi(TRAD_CACHE[raw])) return TRAD_CACHE[raw];
  const ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
  const timer = ctrl ? setTimeout(() => ctrl.abort(), timeoutMs) : null;
  try {
    const r = await fetch("/api/traducir", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto: raw, fuente: "en", destino: "es" }),
      signal: ctrl?.signal,
    });
    const d = await r.json();
    const out = (d?.ok && d.texto) ? d.texto : raw;
    if (out && !pareceInglesUi(out)) TRAD_CACHE[raw] = out;
    else delete TRAD_CACHE[raw];
    return out;
  } catch {
    return raw;
  } finally {
    if (timer) clearTimeout(timer);
  }
}

async function traducirListaAes(textos, { timeoutMs = 180000 } = {}) {
  const list = (textos || []).map((t) => String(t || "").trim()).filter(Boolean);
  if (!list.length) return [];
  const missing = list.filter((t) => !(TRAD_CACHE[t] && !pareceInglesUi(TRAD_CACHE[t])));
  if (missing.length) {
    const ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
    const timer = ctrl ? setTimeout(() => ctrl.abort(), timeoutMs) : null;
    try {
      const r = await fetch("/api/traducir", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ textos: missing, fuente: "en", destino: "es" }),
        signal: ctrl?.signal,
      });
      const d = await r.json();
      const outs = Array.isArray(d?.textos) ? d.textos : [];
      missing.forEach((t, i) => {
        const out = outs[i] || t;
        if (out && !pareceInglesUi(out)) TRAD_CACHE[t] = out;
      });
    } catch {
      /* reintento individual abajo */
    } finally {
      if (timer) clearTimeout(timer);
    }
  }
  const out = [];
  for (const t of list) {
    if (TRAD_CACHE[t] && !pareceInglesUi(TRAD_CACHE[t])) {
      out.push(TRAD_CACHE[t]);
      continue;
    }
    out.push(await traducirAes(t, { timeoutMs: Math.min(timeoutMs, 120000) }));
  }
  return out;
}

function keysProductoFda(f) {
  return [f?.nombre_comercial, f?.nombre_propio, f?.ref_nombre_comercial, f?.ref_nombre_propio]
    .map(normRegKey)
    .filter((x) => x && x.length >= 4);
}

function keysProductoEma(f) {
  return [f?.nombre_medicamento, f?.inn, f?.active_substance]
    .map(normRegKey)
    .filter((x) => x && x.length >= 4);
}

function matchFdaEmaProducto(fda, ema) {
  const a = keysProductoFda(fda);
  const b = keysProductoEma(ema);
  for (const x of a) {
    for (const y of b) {
      if (x === y) return true;
      if (x.length >= 6 && y.length >= 6 && (x.includes(y) || y.includes(x))) return true;
    }
  }
  return false;
}

function registrarComparePair(fda, ema) {
  const id = REG_COMPARE_ROWS.length;
  REG_COMPARE_ROWS.push({ fda, ema });
  return id;
}

function btnCompararReg(id) {
  return `<button type="button" class="btn-reg-compare" data-reg-compare="${id}" title="Comparar FDA y EMA">Comparar</button>`;
}

function fdaSection(titulo, cuerpoHtml, abierta = false) {
  return `
    <details class="fda-ind" ${abierta ? "open" : ""}>
      <summary class="fda-ind-sum">${escapeHtml(titulo)}</summary>
      <div class="fda-ind-body">${cuerpoHtml}</div>
    </details>`;
}

function fdaSectionsBuild(items) {
  let n = 0;
  return items
    .filter((it) => it && it.ok && it.html)
    .map((it) => {
      n += 1;
      return fdaSection(`${n} · ${it.titulo}`, it.html, !!it.abierta);
    })
    .join("");
}

function esFilaIntercambiable(f) {
  if (!f) return false;
  if (f.es_intercambiable) return true;
  const t = `${f.tipo_licencia || ""} ${f.clase_producto || ""}`.toLowerCase();
  return t.includes("interchange") || t.includes("intercambiable");
}

function htmlPurpleBook(n, data, emaData = null) {
  REG_COMPARE_ROWS = [];
  const filas = Array.isArray(data?.filas) ? data.filas : [];
  const info = data?.info || null;
  const periodos = Array.isArray(data?.periodos) ? data.periodos : [];
  const periodo = filas[0]?.periodo_etiqueta || info?.periodo_etiqueta || periodos[0]?.periodo_etiqueta || "—";
  const fechaDato = filas[0]?.fecha_dato || info?.fecha_dato || periodos[0]?.fecha_dato || "";
  const tentative = Array.isArray(info?.tentative) ? info.tentative : [];
  const patentes = Array.isArray(info?.patentes) ? info.patentes : [];
  const productosOb = Array.isArray(info?.productos_fda) ? info.productos_fda : [];
  const ind = !!(info?.indicaciones_uso || urlPdfIndicacionesFda(info) || urlFuenteDrugsAtFda(info));
  const patsVig = patentes.filter((p) => p.estado === "vigente");
  const patsExp = patentes.filter((p) => p.estado === "expirada");
  const resumenOb = htmlResumenOrangeBook(info, patentes, productosOb);
  const taActivas = tentative.filter((t) => t.sigue_tentative);
  const taOtras = tentative.filter((t) => !t.sigue_tentative);
  const emaAuth = (Array.isArray(emaData?.filas) ? emaData.filas : [])
    .filter((f) => String(f.medicine_status || "").toLowerCase() === "authorised");

  const chips = [];
  if (info?.es_biologico) chips.push(`<span class="reg-chip">Biológico</span>`);
  if (info?.tiene_referencia) chips.push(regChipInnovador());
  if (info?.tiene_biosimilar) chips.push(`<span class="reg-chip is-bio">Biosimilar</span>`);
  if (info?.tiene_intercambiable) chips.push(`<span class="reg-chip is-inter">Intercambiable</span>`);
  if (info?.tiene_generico) chips.push(`<span class="reg-chip is-gen">Genérico</span>`);
  const resumenClase = String(info?.resumen_clase || "").trim();
  const headChips = (chips.length || resumenClase)
    ? `<div class="fda-head-class" title="${escapeHtml(resumenClase || "Clasificación FDA")}">
         <div class="fda-head-chips">${chips.join("")}</div>
         ${resumenClase ? `<span class="fda-head-class-note">${escapeHtml(regClaseDisplay(resumenClase))}</span>` : ""}
       </div>`
    : "";

  const tablaPat = (lista, titulo) => {
    if (!lista.length) return `<p class="muted">${escapeHtml(titulo)}: ninguna.</p>`;
    return `
      <p><strong>${escapeHtml(titulo)}</strong> · ${lista.length}</p>
      <div class="table-wrap">
        <table class="data sku-grid purple-grid purple-grid--patentes">
          <thead>
            <tr>
              <th>Patente <span class="th-help">${btnFdaPatentesHelp("?")}</span></th>
              <th>Ingrediente activo</th>
              <th>Nombre propietario</th>
              <th>Forma; vía</th>
              <th>Concentración</th>
              <th>Estado</th>
              <th>Expira</th>
            </tr>
          </thead>
          <tbody>
            ${lista.map((p) => {
              const prod = datosProductoPatenteOb(p, productosOb);
              return `
              <tr>
                <td class="med">
                  ${htmlPatenteFdaLink(p)}
                  ${p.use_code ? `<div class="muted">${escapeHtml(p.use_code)}</div>` : ""}
                  ${p.drug_substance ? `<div class="muted">sustancia</div>` : ""}
                  ${p.drug_product ? `<div class="muted">producto</div>` : ""}
                </td>
                <td>${escapeHtml(prod.ingredient || "—")}</td>
                <td>${escapeHtml(prod.proprietary_name || "—")}</td>
                <td>${escapeHtml(prod.df_route || "—")}</td>
                <td>${escapeHtml(prod.strength || "—")}</td>
                <td>${badgeEstadoPat(p.estado)}</td>
                <td>${escapeHtml(p.expiration_text || p.expiration_date || "—")}</td>
              </tr>`;
            }).join("")}
          </tbody>
        </table>
      </div>`;
  };

  const filasOrd = [...filas].sort((a, b) => Number(esFilaIntercambiable(b)) - Number(esFilaIntercambiable(a)));
  const interFilas = filasOrd.filter(esFilaIntercambiable);
  const interUnicos = [];
  const seenInter = new Set();
  for (const f of interFilas) {
    const key = `${f.nombre_comercial || ""}|${f.bla_number || ""}|${f.concentracion || ""}`;
    if (seenInter.has(key)) continue;
    seenInter.add(key);
    interUnicos.push(f);
  }

  const sec1 = ind ? htmlIndicacionesFda(info) : "";

  const sec3 = interUnicos.length
    ? `
      <p><span class="badge is-fda-inter">Sí</span> <strong>${interUnicos.length}</strong> producto(s) intercambiables en Purple Book.</p>
      <div class="table-wrap">
        <table class="data sku-grid purple-grid">
          <thead>
            <tr>
              <th>Marca</th>
              <th>Nombre propio</th>
              <th>BLA</th>
              <th>Fecha intercambio</th>
              <th>Concentración</th>
              <th>Presentación</th>
              <th>Solicitante</th>
            </tr>
          </thead>
          <tbody>
            ${interUnicos.map((f) => `
              <tr>
                <td class="med">${escapeHtml(f.nombre_comercial || "—")}</td>
                <td>${escapeHtml(f.nombre_propio || "—")}</td>
                <td>${escapeHtml(f.bla_number || "—")}</td>
                <td>${escapeHtml(f.fecha_intercambio || "—")}</td>
                <td>${escapeHtml(f.concentracion || "—")}</td>
                <td>${escapeHtml([f.presentacion, f.forma_dosificacion].filter(Boolean).join(" · ") || "—")}</td>
                <td class="muted">${escapeHtml(f.solicitante || "—")}</td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>`
    : (info?.es_biologico
      ? `<p><span class="badge">No</span> sin designación intercambiable en el snapshot.</p>`
      : "");

  const sec4 = patentes.length
    ? `${resumenOb}${tablaPat(patsVig, "Patentes vigentes")}${tablaPat(patsExp, "Patentes expiradas")}`
    : "";

  const sec6 = tentative.length
    ? `
      <p class="muted sku-note">Aprobaciones tentativas en Drugs@FDA. Las activas sugieren competencia futura.</p>
      ${taActivas.length ? `<p><strong>${taActivas.length}</strong> activas:</p>
        <ul class="fda-ta-list">${taActivas.map((t) => `
          <li><strong>${escapeHtml(t.application_number || "—")}</strong>
            ${escapeHtml(t.brand_name || "")} · ${escapeHtml(t.sponsor || "")}
            · TA ${escapeHtml(String(t.submission_status_date || ""))}
            ${t.url ? ` · ${linkFuente(t.url, "carta")}` : ""}
          </li>`).join("")}</ul>` : `<p class="muted">No hay aprobaciones tentativas activas ahora.</p>`}
      ${taOtras.length ? `<details class="fda-details"><summary>${taOtras.length} históricas</summary>
          <ul class="fda-ta-list">${taOtras.slice(0, 30).map((t) => `
            <li>${escapeHtml(t.application_number || "—")} · ${escapeHtml(String(t.submission_status_date || ""))}
              ${t.url ? ` · ${linkFuente(t.url, "carta")}` : ""}</li>`).join("")}</ul>
        </details>` : ""}`
    : "";

  const tablePurple = filasOrd.length
    ? `<p class="muted sku-note">Productos del Purple Book (biológicos y licencias BLA). ${btnFdaPatentesHelp("Detalle sobre patentes")}</p>
      <div class="table-wrap">
        <table class="data sku-grid purple-grid">
          <thead>
            <tr>
              <th>Marca</th><th>Nombre propio</th><th>BLA</th><th>Clase</th><th>Intercambiable</th>
              <th>Concentración</th><th>Presentación</th><th>Estado</th><th>Aprobación</th>
              <th>Exclusividades</th><th>Patentes <span class="th-help">${btnFdaPatentesHelp("?")}</span></th><th>Innovador (ref.)</th><th>Fuente</th><th></th>
            </tr>
          </thead>
          <tbody>
            ${filasOrd.map((f) => {
              const pair = emaAuth.find((e) => matchFdaEmaProducto(f, e));
              const cmpId = pair ? registrarComparePair(f, pair) : null;
              return `
              <tr class="${esFilaIntercambiable(f) ? "is-inter-row" : ""}">
                <td class="med">${escapeHtml(f.nombre_comercial || "—")}<div class="muted">${escapeHtml(f.solicitante || "")}</div></td>
                <td>${escapeHtml(f.nombre_propio || "—")}</td>
                <td>${escapeHtml(f.bla_number || "—")}<div class="muted">#${escapeHtml(f.product_number || "")}</div></td>
                <td>${badgeClaseFda(f.clase_producto || f.tipo_licencia)}</td>
                <td>${esFilaIntercambiable(f) ? `<span class="badge is-fda-inter">Sí</span>` : `<span class="muted">No</span>`}
                  ${f.fecha_intercambio ? `<div class="muted">${escapeHtml(f.fecha_intercambio)}</div>` : ""}
                </td>
                <td>${escapeHtml(f.concentracion || "—")}</td>
                <td>${escapeHtml([f.presentacion, f.forma_dosificacion, f.via_administracion].filter(Boolean).join(" · ") || "—")}</td>
                <td>${escapeHtml(f.estado_marketing || "—")}<div class="muted">${escapeHtml(f.licensure || "")}</div></td>
                <td>${escapeHtml(f.fecha_aprobacion || "—")}</td>
                <td class="muted" style="font-size:11.5px">
                  ${[["Excl.", f.exclusividad_expira], ["Inter.", f.exclusividad_intercambio_expira], ["Ref.", f.exclusividad_ref_expira], ["Huérfano", f.exclusividad_orphan_expira]]
                    .filter((x) => x[1]).map(([a, b]) => `${a}: ${escapeHtml(b)}`).join("<br>") || "—"}
                </td>
                <td>${f.patent_list ? escapeHtml(f.patent_list) : "—"}</td>
                <td>${escapeHtml(f.ref_nombre_comercial || f.ref_nombre_propio || "—")}</td>
                <td>${f.bla_number
                  ? linkFuente(`https://purplebooksearch.fda.gov/index.cfm?event=productdetails&blaNo=${encodeURIComponent(f.bla_number)}`, "ficha")
                  : "—"}
                </td>
                <td>${cmpId != null ? btnCompararReg(cmpId) : `<span class="muted">—</span>`}</td>
              </tr>`;
            }).join("")}
          </tbody>
        </table>
      </div>`
    : "";

  return `
    <div class="fda-head">
      <div class="fda-head-main">
        <h3>Información FDA</h3>
        <p class="muted sku-note">
          Snapshot <strong>${escapeHtml(String(periodo))}</strong>${fechaDato ? ` · dato ${escapeHtml(fmtFecha(fechaDato))}` : ""}
          ${info?.fecha_registro ? ` · registrado ${escapeHtml(fmtFecha(info.fecha_registro))}` : ""}.
          Solo datos regulatorios (no precios de farmacia).
        </p>
      </div>
      ${headChips}
    </div>
    ${fdaSectionsBuild([
      { titulo: "Indicaciones de uso", html: sec1, abierta: false, ok: !!ind },
      { titulo: "Intercambiables", html: sec3, abierta: false, ok: !!sec3 },
      { titulo: "Patentes FDA", html: sec4, ok: !!patentes.length },
      { titulo: "Posibles aprobaciones (tentative)", html: sec6, ok: !!tentative.length },
      { titulo: "Productos Purple Book (licenciados)", html: tablePurple, ok: !!filasOrd.length },
    ])}
  `;
}

async function openFdaPrincipioModal(n, paisId, from) {
  const row = overlayComparativo().find((r) => r.n === Number(n));
  const pais = paisesUi().find((x) => x.id === paisId) || paisesUi().find((x) => x.id === state.coverPais);
  const modal = $("coverListModal");
  const body = $("coverListBody");
  if (!modal || !body) return;
  const origen = from || REG_CHOOSER.from || "cover";
  REG_CHOOSER = { n: Number(n), paisId: pais?.id || paisId || null, from: origen };
  modal.classList.add("modal--fda");
  modal.classList.remove("modal--reg");
  modal.classList.remove("modal--cover-pa");
  body.innerHTML = `
    <div class="modal-hero">
      <button type="button" class="modal-back" data-back-reg-chooser="${n}" data-cover-pais="${pais?.id || ""}" data-reg-from="${escapeHtml(origen)}">
        ← FDA / EMA${pais && origen === "cover" ? ` · ${escapeHtml(pais.nombre)}` : ""}
      </button>
      <h1 id="coverListTitle">${escapeHtml(row?.medicamento || `Principio #${n}`)}</h1>
      <div class="modal-hero-meta">
        ${row ? badge(row.programa) : ""}
        <span>Información FDA</span>
      </div>
    </div>
    <div class="modal-body modal-body--fda">
      <div id="purpleBookBlock" class="sku-table purple-book" data-n="${n}">
        <p class="muted sku-note">Cargando datos FDA…</p>
      </div>
    </div>
  `;
  modal.hidden = false;
  modal.classList.add("is-open");
  // Forzar datos frescos (patentes nuevas)
  delete PURPLE_CACHE[n];
  await cargarPurpleBookEnFicha(n);
}

function nombrePrincipioLista(n) {
  const num = Number(n);
  const row = overlayComparativo().find((r) => r.n === num);
  if (row?.medicamento) return row.medicamento;
  const fromData = (D.comparativo || []).find((r) => r.n === num);
  if (fromData?.medicamento) return fromData.medicamento;
  return null;
}

function htmlRegSinDatos({ agencia = "EMA", principio = "" } = {}) {
  const nombre = principio || "este principio activo";
  const isEma = agencia === "EMA";
  const titulo = isEma ? "Sin información EMA" : `Sin información ${agencia}`;
  const desc = isEma
    ? `No tenemos datos almacenados de la Agencia Europea de Medicamentos para <strong>${escapeHtml(nombre)}</strong>.`
    : `No tenemos datos almacenados de ${escapeHtml(agencia)} para <strong>${escapeHtml(nombre)}</strong>.`;
  const hint = isEma
    ? "Puede que el medicamento no figure en el catálogo europeo, que aún no hayamos importado su ficha, o que el cruce automático por nombre no haya encontrado coincidencias."
    : "El cruce automático no encontró coincidencias en nuestro repositorio.";
  return `
    <div class="reg-empty ${isEma ? "reg-empty--ema" : ""}">
      <div class="reg-empty-icon" aria-hidden="true">${isEma ? "🇪🇺" : "📋"}</div>
      <div class="reg-empty-body">
        <h3>${escapeHtml(titulo)}</h3>
        <p>${desc}</p>
        <p class="muted">${escapeHtml(hint)}</p>
      </div>
    </div>`;
}

function htmlEmaBook(n, data, fdaData = null) {
  REG_COMPARE_ROWS = [];
  const filas = Array.isArray(data?.filas) ? data.filas : [];
  const info = data?.info || null;
  const periodo = info?.periodo_etiqueta || filas[0]?.periodo_etiqueta || "—";
  const fechaDato = info?.fecha_dato || filas[0]?.fecha_dato || "";
  const auth = filas.filter((f) => String(f.medicine_status || "").toLowerCase() === "authorised");
  const chips = [];
  const emaInnovador = auth.some((f) => esEmaInnovador(f));
  if (emaInnovador) chips.push(regChipInnovador());
  if (info?.tiene_biosimilar) chips.push(`<span class="reg-chip is-bio">Biosimilar</span>`);
  if (info?.tiene_generic) chips.push(`<span class="reg-chip is-gen">Genérico</span>`);
  if (info?.tiene_orphan) chips.push(`<span class="reg-chip is-ref">Huérfano</span>`);
  if (info?.tiene_advanced_therapy) chips.push(`<span class="reg-chip">Terapia avanzada</span>`);
  const headNote = info
    ? `${info.total_authorised || 0} autorizados · ${info.total_medicamentos || 0} en catálogo`
    : "";
  const headChips = (chips.length || headNote)
    ? `<div class="fda-head-class" title="${escapeHtml(headNote)}">
         <div class="fda-head-chips">${chips.join("")}</div>
         ${headNote ? `<span class="fda-head-class-note">${escapeHtml(headNote)}</span>` : ""}
       </div>`
    : "";

  const otras = filas.filter((f) => String(f.medicine_status || "").toLowerCase() !== "authorised");
  const fdaFilas = Array.isArray(fdaData?.filas) ? fdaData.filas : [];
  const detalleInd = indicacionesEmaDetalle(filas, info);
  const textosEs = Array.isArray(info?.indicaciones_es) ? info.indicaciones_es : null;

  const secMeta = (info && ((info.inns || []).length || (info.atc_codes || []).length || (info.therapeutic_areas || []).length))
    ? `
      <p class="muted sku-note">
        ${(info?.inns || []).length ? `DCI/INN: <strong>${escapeHtml((info.inns || []).join(", "))}</strong>. ` : ""}
        ${(info?.atc_codes || []).length ? `ATC: <strong>${escapeHtml((info.atc_codes || []).join(", "))}</strong>. ` : ""}
      </p>
      ${(info?.therapeutic_areas_es || info?.therapeutic_areas || []).length ? `<p>Áreas terapéuticas: ${escapeHtml((info.therapeutic_areas_es || info.therapeutic_areas || []).join("; "))}</p>` : ""}`
    : "";

  const secInd = detalleInd.length
    ? `
      <p class="muted sku-note ema-ind-hint">Indicaciones terapéuticas desde el Medicine overview EPAR en español (PDF oficial). Si no hay ES, se completa por traducción.</p>
      <div class="ema-ind-list" id="emaIndList-${n}">
        ${htmlIndicacionesEma(n, detalleInd, textosEs)}
      </div>`
    : "";

  const tablaMeds = (lista, titulo, conCompare) => {
    if (!lista.length) return "";
    return `
      <p><strong>${escapeHtml(titulo)}</strong> · ${lista.length}
        <span class="muted" style="font-weight:400;font-size:12px"> · estado según <code>Medicine status</code> del catálogo EMA</span>
      </p>
      <div class="table-wrap">
        <table class="data sku-grid purple-grid">
          <thead>
            <tr>
              <th>Medicamento</th>
              <th>Estado</th>
              <th>INN / sustancia</th>
              <th>ATC</th>
              <th>Clase</th>
              <th>Titular</th>
              <th>Autorización</th>
              <th>Fuente</th>
              ${conCompare ? "<th></th>" : ""}
            </tr>
          </thead>
          <tbody>
            ${lista.map((f) => {
              const pair = conCompare ? fdaFilas.find((p) => matchFdaEmaProducto(p, f)) : null;
              const cmpId = pair ? registrarComparePair(pair, f) : null;
              return `
              <tr>
                <td class="med">
                  ${escapeHtml(f.nombre_medicamento || "—")}
                  <div class="muted">${escapeHtml(f.ema_product_number || "")}</div>
                </td>
                <td>${escapeHtml(estadoEmaEs(f.medicine_status))}</td>
                <td>
                  ${escapeHtml(f.inn || "—")}
                  ${f.active_substance && f.active_substance !== f.inn
                    ? `<div class="muted">${escapeHtml(f.active_substance)}</div>` : ""}
                </td>
                <td>${escapeHtml(f.atc_code || "—")}</td>
                <td>
                  ${f.es_biosimilar ? badgeClaseFda("biosimilar") : ""}
                  ${f.es_generic ? badgeClaseFda("generico") : ""}
                  ${f.es_orphan ? `<span class="badge is-pct">Huérfano</span>` : ""}
                  ${esEmaInnovador(f) ? badgeInnovador() : ""}
                  ${f.es_advanced_therapy ? `<span class="badge">Terapia avanzada</span>` : ""}
                </td>
                <td class="muted">${escapeHtml(f.mah || "—")}</td>
                <td>${escapeHtml(f.marketing_authorisation_date || f.ec_decision_date || "—")}</td>
                <td>${f.medicine_url ? linkFuente(f.medicine_url, "EPAR") : "—"}</td>
                ${conCompare ? `<td>${cmpId != null ? btnCompararReg(cmpId) : `<span class="muted">—</span>`}</td>` : ""}
              </tr>`;
            }).join("")}
          </tbody>
        </table>
      </div>`;
  };

  return `
    <div class="fda-head">
      <div class="fda-head-main">
        <h3>Información EMA</h3>
        <p class="muted sku-note">
          Snapshot <strong>${escapeHtml(String(periodo))}</strong>${fechaDato ? ` · dato ${escapeHtml(fmtFecha(fechaDato))}` : ""}.
          Catálogo oficial de medicamentos (no precios de farmacia).
        </p>
        <p class="muted sku-note">${fuentesEmaHtml()}</p>
      </div>
      ${headChips}
    </div>
    ${fdaSectionsBuild([
      { titulo: "Datos del principio", html: secMeta, abierta: false, ok: !!secMeta },
      { titulo: "Indicaciones terapéuticas", html: secInd, abierta: false, ok: !!detalleInd.length },
      { titulo: "Medicamentos autorizados", html: tablaMeds(auth, "Autorizados", true), ok: !!auth.length },
      { titulo: "Otros estados (retirados, rechazados…)", html: tablaMeds(otras, "Otros", false), ok: !!otras.length },
    ])}
  `;
}

async function openEmaPrincipioModal(n, paisId, from) {
  const row = overlayComparativo().find((r) => r.n === Number(n));
  const pais = paisesUi().find((x) => x.id === paisId) || paisesUi().find((x) => x.id === state.coverPais);
  const modal = $("coverListModal");
  const body = $("coverListBody");
  if (!modal || !body) return;
  const origen = from || REG_CHOOSER.from || "cover";
  REG_CHOOSER = { n: Number(n), paisId: pais?.id || paisId || null, from: origen };
  modal.classList.add("modal--fda");
  modal.classList.remove("modal--reg");
  modal.classList.remove("modal--cover-pa");
  body.innerHTML = `
    <div class="modal-hero">
      <button type="button" class="modal-back" data-back-reg-chooser="${n}" data-cover-pais="${pais?.id || ""}" data-reg-from="${escapeHtml(origen)}">
        ← FDA / EMA${pais && origen === "cover" ? ` · ${escapeHtml(pais.nombre)}` : ""}
      </button>
      <h1 id="coverListTitle">${escapeHtml(row?.medicamento || `Principio #${n}`)}</h1>
      <div class="modal-hero-meta">
        ${row ? badge(row.programa) : ""}
        <span>Información EMA</span>
      </div>
    </div>
    <div class="modal-body modal-body--fda">
      <div id="emaBookBlock" class="sku-table purple-book" data-n="${n}">
        <p class="muted sku-note">Cargando datos EMA…</p>
      </div>
    </div>
  `;
  modal.hidden = false;
  modal.classList.add("is-open");
  delete EMA_CACHE[n];
  await cargarEmaEnFicha(n);
}

async function asegurarEmaCache(n) {
  if (EMA_CACHE[n]?.ok) return EMA_CACHE[n];
  try {
    const r = await fetch(`/api/ema?n_lista=${encodeURIComponent(n)}&traducir=0`, { cache: "no-store" });
    const data = await r.json();
    if (data?.ok) EMA_CACHE[n] = data;
    return data;
  } catch {
    return null;
  }
}

function emaTieneDatos(data) {
  return Boolean(data?.ok) && Array.isArray(data.filas) && data.filas.length > 0;
}

async function emaDisponiblePara(n) {
  const data = await asegurarEmaCache(n);
  return emaTieneDatos(data);
}

async function asegurarPurpleCache(n) {
  if (PURPLE_CACHE[n]?.ok) return PURPLE_CACHE[n];
  try {
    const r = await fetch(`/api/purple-book?n_lista=${encodeURIComponent(n)}`, { cache: "no-store" });
    const data = await r.json();
    if (data?.ok) PURPLE_CACHE[n] = data;
    return data;
  } catch {
    return null;
  }
}

async function cargarEmaEnFicha(n) {
  const block = $("emaBookBlock");
  if (!block || Number(block.dataset.n) !== Number(n)) return;
  try {
    block.innerHTML = `<p class="muted sku-note">Cargando datos EMA…</p>`;
    let data = await asegurarEmaCache(n);
    if (Number(block.dataset.n) !== Number(n)) return;
    if (!data?.ok) throw new Error(data?.error || "API EMA");
    if (!(data.filas || []).length) {
      block.innerHTML = htmlRegSinDatos({
        agencia: "EMA",
        principio: nombrePrincipioLista(n),
      });
      return;
    }
    const fdaData = await asegurarPurpleCache(n);
    if (Number(block.dataset.n) !== Number(n)) return;
    data.info = data.info || {};
    data._indsDetalle = indicacionesEmaDetalle(data.filas, data.info);
    // Preferir ES oficial del overview EPAR; si no, EN y traducir en fondo.
    if (!Array.isArray(data.info.indicaciones_es) || data.info.indicaciones_es.length !== data._indsDetalle.length) {
      data.info.indicaciones_es = data._indsDetalle.map((d) => {
        if (d.texto_es) return d.texto_es;
        const fila = (data.filas || []).find((f) => String(f.therapeutic_indication || "").trim() === d.texto);
        return fila?.therapeutic_indication_es || d.texto;
      });
    }
    block.innerHTML = htmlEmaBook(n, data, fdaData);
    traducirIndicacionesEmaEnFondo(n, data);
  } catch (err) {
    console.error(err);
    if (Number(block.dataset.n) !== Number(n)) return;
    block.innerHTML = `
      <h3>EMA</h3>
      <p class="muted sku-note">No se pudo cargar (${escapeHtml(String(err.message || err))}).</p>
    `;
  }
}

async function traducirIndicacionesEmaEnFondo(n, data) {
  const detalle = data?._indsDetalle || indicacionesEmaDetalle(data?.filas || [], data?.info);
  if (!detalle.length || !data?.info) return;
  data.info.indicaciones_es = Array.isArray(data.info.indicaciones_es)
    ? data.info.indicaciones_es.slice()
    : detalle.map((d) => d.texto);

  // Completar en español una a una (sin barrido masivo al API que satura Google).
  for (let i = 0; i < detalle.length; i++) {
    if (Number($("emaBookBlock")?.dataset.n) !== Number(n)) return;
    const raw = detalle[i].texto;
    let es = data.info.indicaciones_es[i] || detalle[i].texto_es || raw;
    // Ya tenemos español oficial del Medicine overview EPAR
    if (detalle[i].fuente_es === "epar_overview_es" || (es && !pareceInglesUi(es))) {
      data.info.indicaciones_es[i] = es;
      continue;
    }
    if (!pareceInglesUi(es)) continue;
    const card = $(`emaInd-${n}-${i}`);
    const body = card?.querySelector?.("[data-ema-ind-body]");
    const lang = card?.querySelector?.("[data-ema-lang]");
    if (body) body.classList.add("is-translating");
    if (lang) {
      lang.textContent = "…";
      lang.classList.add("is-busy");
      lang.classList.remove("is-en");
    }
    try {
      delete TRAD_CACHE[raw];
      es = await traducirAes(raw, { timeoutMs: 90000 });
    } catch {
      es = raw;
    }
    data.info.indicaciones_es[i] = es;
    if (Number($("emaBookBlock")?.dataset.n) !== Number(n)) return;
    if (body) {
      body.classList.remove("is-translating");
      body.innerHTML = formatearIndicacionEmaHtml(es);
    }
    if (lang) {
      lang.classList.remove("is-busy");
      if (es && !pareceInglesUi(es)) {
        lang.textContent = "ES";
        lang.classList.remove("is-en");
      } else {
        lang.textContent = "EN";
        lang.classList.add("is-en");
      }
    }
  }
}

async function cargarPurpleBookEnFicha(n) {
  const block = $("purpleBookBlock");
  if (!block || Number(block.dataset.n) !== Number(n)) return;
  try {
    block.innerHTML = `<p class="muted sku-note">Cargando datos FDA…</p>`;
    let data = await asegurarPurpleCache(n);
    if (Number(block.dataset.n) !== Number(n)) return;
    if (!data?.ok) throw new Error(data?.error || "API Purple Book");
    const emaData = await asegurarEmaCache(n);
    if (Number(block.dataset.n) !== Number(n)) return;
    block.innerHTML = htmlPurpleBook(n, data, emaData);
  } catch (err) {
    console.error(err);
    if (Number(block.dataset.n) !== Number(n)) return;
    block.innerHTML = `
      <h3>FDA</h3>
      <p class="muted sku-note">No se pudo cargar (${escapeHtml(String(err.message || err))}).</p>
    `;
  }
}

function closeRegCompareModal() {
  const el = $("regCompareModal");
  if (!el) return;
  el.classList.remove("is-open");
  el.hidden = true;
}

function normCmpTxt(s) {
  return String(s || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function cmpCampoEstado(fdaVal, emaVal) {
  const a = normCmpTxt(fdaVal);
  const b = normCmpTxt(emaVal);
  if (!a && !b) return { tipo: "na", label: "Sin dato" };
  if (!a) return { tipo: "solo-ema", label: "Solo EMA" };
  if (!b) return { tipo: "solo-fda", label: "Solo FDA" };
  if (a === b) return { tipo: "igual", label: "Igual" };
  if (a.includes(b) || b.includes(a)) return { tipo: "similar", label: "Similar" };
  return { tipo: "diff", label: "Difiere" };
}

function claseFdaTexto(fda) {
  const bits = [];
  const c = String(fda.clase_producto || fda.tipo_licencia || "").toLowerCase();
  if (fda.es_intercambiable || c.includes("interchange")) bits.push("Intercambiable");
  else if (c.includes("biosimilar")) bits.push("Biosimilar");
  else if (c.includes("referencia") || c.includes("351(a)")) bits.push(REG_LABEL_INNOVADOR);
  else if (c.includes("generic") || c.includes("anda")) bits.push("Genérico");
  if (!bits.length && c) bits.push(fda.clase_producto || fda.tipo_licencia);
  return bits.join(" · ") || "—";
}

function claseEmaTexto(ema) {
  const bits = [];
  if (esEmaInnovador(ema)) bits.push(REG_LABEL_INNOVADOR);
  if (ema.es_biosimilar) bits.push("Biosimilar");
  if (ema.es_generic) bits.push("Genérico");
  if (ema.es_orphan) bits.push("Huérfano");
  if (ema.es_advanced_therapy) bits.push("Terapia avanzada");
  return bits.join(" · ") || "—";
}

function buildRegCompareRows(fda, ema) {
  const fdaClase = claseFdaTexto(fda);
  const emaClase = claseEmaTexto(ema);
  const fdaPres = [fda.presentacion, fda.forma_dosificacion, fda.via_administracion].filter(Boolean).join(" · ");
  const rows = [
    {
      campo: "Nombre / marca",
      fda: fda.nombre_comercial || "—",
      ema: ema.nombre_medicamento || "—",
      nota: "Identidad comercial del producto en cada agencia.",
    },
    {
      campo: "Nombre propio / INN",
      fda: fda.nombre_propio || "—",
      ema: [ema.inn, ema.active_substance].filter(Boolean).join(" · ") || "—",
      nota: "Principio activo o nombre propio; en EMA suele ir como INN.",
    },
    {
      campo: "Identificador",
      fda: fda.bla_number ? `BLA ${fda.bla_number}${fda.product_number ? ` · #${fda.product_number}` : ""}` : "—",
      ema: ema.ema_product_number || "—",
      nota: "BLA (FDA) vs número de producto EMA.",
    },
    {
      campo: "Clasificación",
      fda: fdaClase,
      ema: emaClase,
      nota: "FDA: innovador / biosimilar / intercambiable. EMA: innovador / biosimilar / genérico / huérfano.",
    },
    {
      campo: "Estado",
      fda: fda.estado_marketing || fda.licensure || "—",
      ema: estadoEmaEs(ema.medicine_status),
      nota: "Estado de comercialización / autorización.",
    },
    {
      campo: "Concentración / forma",
      fda: [fda.concentracion, fdaPres].filter(Boolean).join(" · ") || "—",
      ema: "No detallado en el extracto EMA (ver EPAR)",
      nota: "Purple Book trae dosis/forma; el XLSX EMA no desglosa presentación.",
    },
    {
      campo: "Titular / solicitante",
      fda: fda.solicitante || "—",
      ema: ema.mah || "—",
      nota: "Solicitante FDA vs titular de autorización EMA (MAH).",
    },
    {
      campo: "Fecha de autorización",
      fda: fda.fecha_aprobacion || "—",
      ema: ema.marketing_authorisation_date || ema.ec_decision_date || "—",
      nota: "Fechas pueden diferir por agencia y procedimiento.",
    },
    {
      campo: "Producto innovador",
      fda: fda.ref_nombre_comercial || fda.ref_nombre_propio || "—",
      ema: ema.es_biosimilar ? "Biosimilar (innovador en EPAR)" : "—",
      nota: "Innovador 351(a) en FDA; en EMA el innovador del biosimilar está en el EPAR.",
    },
    {
      campo: "Área terapéutica",
      fda: "—",
      ema: ema.therapeutic_area_es || ema.therapeutic_area || "—",
      nota: "EMA resume áreas; las indicaciones FDA detalladas están en la comparación por principio.",
    },
  ];
  return rows.map((r) => ({ ...r, estado: cmpCampoEstado(r.fda, r.ema) }));
}

function badgeCmpEstado(est) {
  const t = est?.tipo || "na";
  const label = est?.label || "—";
  return `<span class="cmp-pill cmp-pill--${t}">${escapeHtml(label)}</span>`;
}

function uniqTextos(vals) {
  const out = [];
  const seen = new Set();
  for (const v of vals || []) {
    const t = String(v || "").trim();
    if (!t) continue;
    const k = t.toLowerCase();
    if (seen.has(k)) continue;
    seen.add(k);
    out.push(t);
  }
  return out;
}

/** INN/sustancia FDA: Purple Book (biológicos) o Orange Book ingredient (molécula pequeña). */
function innsSustanciaFda(fdaInfo, fdaFilas) {
  const fi = fdaInfo || {};
  const lista = String(fi.medicamento_lista || "");
  const listaCombo = lista.includes("/");
  const esComboInn = (raw) => {
    const s = String(raw || "").toLowerCase();
    return s.includes(" and ") || s.includes(";");
  };
  const fromPurple = uniqTextos(
    (fdaFilas || [])
      .map((f) => f.nombre_propio || f.proper_name)
      .filter((ing) => {
        if (!ing) return false;
        if (!listaCombo && esComboInn(ing)) return false;
        return true;
      })
  );
  // productos_fda ya viene emparejado en el scraper (aliases + Orange Book);
  // solo filtramos combos vs monoprincipio, sin re-cruzar por palabras del nombre en español.
  const prods = Array.isArray(fi.productos_fda) ? fi.productos_fda : [];
  const fromOrange = uniqTextos(
    prods
      .map((p) => String(p.ingredient || p.substance || "").trim())
      .filter((ing) => {
        if (!ing) return false;
        const combo = esComboInn(ing);
        return listaCombo ? combo : !combo;
      })
  );
  if (fi.es_biologico) return fromPurple.length ? fromPurple : fromOrange;
  return fromOrange.length ? fromOrange : fromPurple;
}

function buildRegCompareGeneralRows(fdaInfo, emaInfo, fdaFilas, emaFilas, meta = {}) {
  const fi = fdaInfo || {};
  const ei = emaInfo || {};
  const n = meta.n != null ? Number(meta.n) : "";
  const paisId = meta.paisId || "";
  const from = meta.from || "ficha";
  const emaInnovador = (emaFilas || []).some(
    (f) => String(f.medicine_status || "").toLowerCase() === "authorised" && esEmaInnovador(f),
  );
  const fdaClase = [
    fi.es_biologico ? "Biológico" : "",
    fi.tiene_referencia ? REG_LABEL_INNOVADOR : "",
    fi.tiene_biosimilar ? "Biosimilar" : "",
    fi.tiene_intercambiable ? "Intercambiable" : "",
    fi.tiene_generico ? "Genérico" : "",
  ].filter(Boolean).join(" · ") || regClaseDisplay(fi.resumen_clase || "—");
  const emaClase = [
    emaInnovador ? REG_LABEL_INNOVADOR : "",
    ei.tiene_biosimilar ? "Biosimilar" : "",
    ei.tiene_generic ? "Genérico" : "",
    ei.tiene_orphan ? "Huérfano" : "",
    ei.tiene_advanced_therapy ? "Terapia avanzada" : "",
  ].filter(Boolean).join(" · ") || "—";
  const innsFda = innsSustanciaFda(fi, fdaFilas);
  const areasEma = uniqTextos(ei.therapeutic_areas_es || ei.therapeutic_areas || []).slice(0, 10);
  const esBiologico = !!fi.es_biologico;
  const esGenericoMolecula = !esBiologico && !!fi.tiene_generico;
  const fdaIndLink = n
    ? `<button type="button" class="cmp-fda-link" data-open-fda="${n}" data-cover-pais="${escapeHtml(paisId)}" data-reg-from="${escapeHtml(from)}">Ver indicaciones en ficha FDA →</button>`
    : "—";
  const rows = [
    {
      campo: "Principio / cobertura",
      fda: fi.medicamento_lista || "—",
      ema: ei.medicamento_lista || fi.medicamento_lista || "—",
      nota: "Principio activo cruzado en ambas fuentes.",
    },
    {
      campo: "Clasificación",
      fda: fdaClase,
      ema: emaClase,
      nota: "Banderas regulatorias agregadas del principio.",
    },
    {
      campo: "Biosimilar",
      fda: esGenericoMolecula || !esBiologico
        ? "No aplica"
        : (fi.tiene_biosimilar ? "Sí" : "No"),
      ema: esGenericoMolecula || (!esBiologico && !ei.tiene_biosimilar)
        ? "No aplica"
        : (ei.tiene_biosimilar ? "Sí" : "No"),
      nota: "Presencia de biosimilares; no aplica a genéricos de molécula pequeña.",
    },
    {
      campo: "Genérico",
      fda: fi.tiene_generico ? "Sí" : (esBiologico ? "No aplica" : "No"),
      ema: ei.tiene_generic ? "Sí" : (esBiologico ? "No aplica" : "No"),
      nota: "Genéricos de molécula pequeña / genéricos EMA.",
    },
    {
      campo: "INN / sustancia",
      fda: innsFda.length ? innsFda.map(textoUi).join(", ") : "—",
      ema: (ei.inns || []).length ? (ei.inns || []).map(textoUi).join(", ") : "—",
      nota: fi.es_biologico
        ? "Nombre propio Purple Book (FDA) y DCI/INN EMA."
        : "Ingrediente Orange Book (FDA) y DCI/INN EMA.",
    },
    {
      campo: "Áreas terapéuticas",
      fda: "Ver indicaciones",
      fdaHtml: fdaIndLink,
      ema: areasEma.length ? areasEma.join("; ") : "—",
      nota: "Solo EMA publica áreas terapéuticas; en FDA abre la ficha de indicaciones.",
    },
  ];
  return rows.map((r) => ({ ...r, estado: cmpCampoEstado(r.fda, r.ema) }));
}

function cmpCellHtml(val, html) {
  if (html) return html;
  return escapeHtml(String(val ?? "—"));
}

function renderRegCompareTable(titulo, crumb, rows, linksHtml = "") {
  return `
    <div class="modal-hero">
      <p class="crumb">${escapeHtml(crumb)}</p>
      <h1 id="regCompareTitle">${escapeHtml(titulo)}</h1>
      <div class="modal-hero-meta">
        <span>FDA · Purple Book</span>
        <span>EMA · Autorizado</span>
      </div>
    </div>
    <div class="modal-body modal-body--reg-compare">
      <section class="cmp-table-wrap">
        <h3>Tabla comparativa</h3>
        <div class="table-wrap table-wrap--modal-flow">
          <table class="data data-static cmp-table">
            <thead>
              <tr>
                <th>Campo</th>
                <th>FDA</th>
                <th>EMA</th>
              </tr>
            </thead>
            <tbody>
              ${rows.map((r) => `
                <tr>
                  <td class="med">
                    ${escapeHtml(r.campo)}
                    <div class="muted" style="white-space:normal;font-size:11.5px">${escapeHtml(r.nota || "")}</div>
                  </td>
                  <td style="white-space:normal">${cmpCellHtml(r.fda, r.fdaHtml)}</td>
                  <td style="white-space:normal">${cmpCellHtml(r.ema, r.emaHtml)}</td>
                </tr>`).join("")}
            </tbody>
          </table>
        </div>
        ${linksHtml ? `<p class="muted sku-note" style="margin-top:12px">${linksHtml}</p>` : ""}
      </section>
    </div>`;
}

function openRegCompareModal(id) {
  const pair = REG_COMPARE_ROWS[Number(id)];
  const modal = $("regCompareModal");
  const body = $("regCompareBody");
  if (!pair || !modal || !body) return;
  const fda = pair.fda || {};
  const ema = pair.ema || {};
  const titulo = fda.nombre_comercial || ema.nombre_medicamento || "Producto";
  const rows = buildRegCompareRows(fda, ema);
  const links = [
    fda.bla_number
      ? linkFuente(`https://purplebooksearch.fda.gov/index.cfm?event=productdetails&blaNo=${encodeURIComponent(fda.bla_number)}`, "Ficha Purple Book")
      : "",
    ema.medicine_url ? linkFuente(ema.medicine_url, "EPAR EMA") : "",
  ].filter(Boolean).join(" · ");
  body.innerHTML = renderRegCompareTable(titulo, "Comparación regulatoria · producto", rows, links);
  modal.hidden = false;
  modal.classList.add("is-open");
}

async function openRegCompareGeneralModal(n, paisId, from = "ficha") {
  const modal = $("regCompareModal");
  const body = $("regCompareBody");
  if (!modal || !body) return;
  const row = overlayComparativo().find((r) => r.n === Number(n));
  const titulo = row?.medicamento || `Principio #${n}`;
  const emaData = await asegurarEmaCache(n);
  if (!emaTieneDatos(emaData)) {
    openFdaPrincipioModal(n, paisId, from);
    return;
  }
  body.innerHTML = `
    <div class="modal-hero">
      <p class="crumb">Comparación regulatoria · principio</p>
      <h1 id="regCompareTitle">${escapeHtml(titulo)}</h1>
      <div class="modal-hero-meta">
        <span>Cargando FDA y EMA…</span>
      </div>
    </div>
    <div class="modal-body modal-body--reg-compare">
      <p class="muted">Preparando tabla comparativa…</p>
    </div>`;
  modal.hidden = false;
  modal.classList.add("is-open");
  try {
    const [fdaData, emaData] = await Promise.all([
      asegurarPurpleCache(n),
      asegurarEmaCache(n),
    ]);
    const rows = buildRegCompareGeneralRows(
      fdaData?.info,
      emaData?.info,
      fdaData?.filas || [],
      emaData?.filas || [],
      { n, paisId: paisId || "", from: from || "ficha" },
    );
    body.innerHTML = `
      <div class="modal-hero">
        <button type="button" class="modal-back" data-back-reg-chooser="${n}" data-cover-pais="${escapeHtml(paisId || "")}" data-reg-from="${escapeHtml(from || "ficha")}">
          ← FDA / EMA
        </button>
        <h1 id="regCompareTitle">${escapeHtml(titulo)}</h1>
        <div class="modal-hero-meta">
          ${row ? badge(row.programa) : ""}
          <span>Comparación general · FDA · EMA</span>
        </div>
      </div>
      <div class="modal-body modal-body--reg-compare">
        <section class="cmp-table-wrap">
          <h3>Tabla comparativa</h3>
          <div class="table-wrap table-wrap--modal-flow">
            <table class="data data-static cmp-table">
              <thead>
                <tr>
                  <th>Campo</th>
                  <th>FDA</th>
                  <th>EMA</th>
                </tr>
              </thead>
              <tbody>
                ${rows.map((r) => `
                  <tr>
                    <td class="med">
                      ${escapeHtml(r.campo)}
                      <div class="muted" style="white-space:normal;font-size:11.5px">${escapeHtml(r.nota || "")}</div>
                    </td>
                    <td style="white-space:normal">${cmpCellHtml(r.fda, r.fdaHtml)}</td>
                    <td style="white-space:normal">${cmpCellHtml(r.ema, r.emaHtml)}</td>
                  </tr>`).join("")}
              </tbody>
            </table>
          </div>
        </section>
      </div>`;
  } catch (err) {
    console.error(err);
    body.innerHTML = `
      <div class="modal-hero">
        <h1 id="regCompareTitle">${escapeHtml(titulo)}</h1>
      </div>
      <div class="modal-body">
        <p class="muted">No se pudo armar la comparación (${escapeHtml(String(err.message || err))}).</p>
      </div>`;
  }
}

function closeModal() {
  const el = $("fichaModal");
  if (!el) return;
  el.classList.remove("is-open");
  el.classList.remove("modal--cover-pa");
  el.hidden = true;
  state.selected = null;
  state.coverPais = null;
  state.coverVista = "principios";
  closeCoverListModal();
}

function animateStage() {
  const stage = $("stage");
  if (!stage) return;
  stage.classList.remove("is-entering");
  void stage.offsetWidth;
  stage.classList.add("is-entering");
}

function renderLoadingStage() {
  const stage = $("stage");
  if (!stage) return;
  stage.innerHTML = `
    <article class="card loading-card">
      <div class="card-head">
        <div class="loading-line w-40"></div>
      </div>
      <div class="loading-grid">
        <div class="loading-kpi"></div>
        <div class="loading-kpi"></div>
        <div class="loading-kpi"></div>
        <div class="loading-kpi"></div>
      </div>
      <div class="loading-table">
        <div class="loading-line w-90"></div>
        <div class="loading-line w-96"></div>
        <div class="loading-line w-88"></div>
        <div class="loading-line w-92"></div>
        <div class="loading-line w-84"></div>
      </div>
    </article>`;
  animateStage();
}

function render() {
  const meta = VIEWS[state.view] || VIEWS.tablero;
  const crumb = $("crumb");
  const title = $("pageTitle");
  if (crumb) crumb.textContent = meta.crumb;
  if (title) title.textContent = meta.title;
  document.querySelectorAll(".nav-item").forEach((b) => {
    b.classList.toggle("is-active", b.dataset.view === state.view);
  });
  try {
    if (state.view === "tablero") renderTablero();
    else if (state.view === "comparativo") renderComparativo();
    else if (state.view === "detalle") renderDetalle();
    else if (state.view === "tendencias") renderTendencias();
    else if (state.view === "fuentes") {
      renderFuentes();
      cargarEstadosJobs().then((data) => {
        if (data && state.view === "fuentes") {
          renderFuentes();
          const activos = Object.values(JOBS_ESTADOS).some((j) => ["queued", "running"].includes(j?.estado));
          if (activos) startJobsPolling();
        }
      });
    }
    else if (state.view === "metodologia") renderMetodologia();
    else if (state.view === "documentacion") renderDocumentacion();
  } catch (err) {
    const stage = $("stage");
    if (stage) stage.innerHTML = `<p class="note">No se pudo pintar esta vista: ${escapeHtml(err.message)}</p>`;
    console.error(err);
  }
  animateStage();
}

function irA(view) {
  if (!VIEWS[view]) view = "tablero";
  state.view = view;
  state.page = 1;
  state.dpage = 1;
  closeModal();
  syncRoute(view);
  render();
}

function setSidebarCollapsed(collapsed) {
  const app = document.getElementById("appShell");
  if (!app) return;
  app.classList.toggle("is-collapsed", !!collapsed);
  try { localStorage.setItem("alto_costo_sidebar", collapsed ? "1" : "0"); } catch (_) { /* ignore */ }
  const btn = $("sideToggle");
  if (btn) {
    const label = collapsed ? "Expandir menú" : "Contraer menú";
    btn.title = label;
    btn.setAttribute("aria-label", label);
    btn.setAttribute("aria-expanded", collapsed ? "false" : "true");
  }
}

function actualizarPill() {
  const pill = $("livePill");
  if (!pill) return;
  // Mostrar siempre el badge de precios (aunque aún cargue)
  pill.hidden = false;
  pill.removeAttribute("hidden");
  if (!LIVE_LOADED) {
    pill.classList.remove("is-live");
    pill.textContent = "Cargando precios…";
    return;
  }
  if (LIVE_OK) {
    pill.classList.add("is-live");
    const cuando = SNAPSHOT_FECHA ? ` · ${fmtFecha(SNAPSHOT_FECHA)}` : "";
    pill.textContent = `${filasTablaBase().length} precios en vivo${cuando}`;
  } else {
    pill.classList.remove("is-live");
    pill.textContent = "Sin conexión a la tabla";
  }
}

function bind() {
  window.addEventListener("popstate", () => {
    const nextView = viewFromLocation();
    if (nextView === state.view) return;
    state.view = nextView;
    state.page = 1;
    state.dpage = 1;
    closeModal();
    render();
  });
  window.addEventListener("resize", () => {
    if (state.view === "comparativo" || state.view === "detalle") syncFlowSticky();
  });
  document.addEventListener("click", (e) => {
    if (e.target.closest("#btnDocPdf")) {
      e.preventDefault();
      exportDocumentacionPdf();
      return;
    }
    if (e.target.closest("#btnDocWord")) {
      e.preventDefault();
      exportDocumentacionWord();
      return;
    }
    if (e.target.closest?.("[data-close-tend-insight]")) {
      closeTendInsightModal();
      return;
    }
    const tendInsightRow = e.target.closest?.("tr[data-tend-pick]");
    if (tendInsightRow && $("tendInsightModal")?.classList.contains("is-open")) {
      seleccionarTendMedicamento(tendInsightRow.getAttribute("data-tend-pick") || "");
      closeTendInsightModal();
      return;
    }
    const tendBar = e.target.closest?.("[data-tend-insight-chart]");
    if (tendBar) {
      openTendInsightModal(
        tendBar.getAttribute("data-tend-insight-chart"),
        tendBar.getAttribute("data-tend-insight-key"),
        tendBar.getAttribute("data-tend-insight-label"),
        tendBar.getAttribute("data-tend-insight-value"),
      );
      return;
    }
    const paisChip = e.target.closest?.("[data-tend-pais-toggle]");
    if (paisChip) {
      const pais = paisChip.getAttribute("data-tend-pais-toggle");
      const all = [...document.querySelectorAll("[data-tend-pais-toggle]")].map((b) => b.getAttribute("data-tend-pais-toggle"));
      const set = new Set(state.tendPaises && state.tendPaises.length ? state.tendPaises : all);
      if (set.has(pais)) {
        if (set.size > 1) set.delete(pais);
      } else {
        set.add(pais);
      }
      state.tendPaises = [...set];
      aplicarVistaTendencia();
      return;
    }
    const pick = e.target.closest?.("[data-tend-pick]");
    if (pick) {
      seleccionarTendMedicamento(pick.getAttribute("data-tend-pick") || "");
      return;
    }
    if (state.tendPickerOpen && !e.target.closest?.(".tend-picker-wrap")) {
      cerrarTendPicker();
    }
    if (e.target.closest("[data-close-fda-src-help]")) {
      closeFdaSrcHelpModal();
      return;
    }
    if (e.target.closest("[data-close-fda-patentes-help]")) {
      closeFdaPatentesHelpModal();
      return;
    }
    if (e.target.closest("[data-close-ema-src-help]")) {
      closeEmaSrcHelpModal();
      return;
    }
    const openEmaSrcHelp = e.target.closest("[data-open-ema-src-help]");
    if (openEmaSrcHelp) {
      e.preventDefault();
      e.stopPropagation();
      openEmaSrcHelpModal();
      return;
    }
    const openFdaPatentesHelp = e.target.closest("[data-open-fda-patentes-help]");
    if (openFdaPatentesHelp) {
      e.preventDefault();
      e.stopPropagation();
      openFdaPatentesHelpModal();
      return;
    }
    const openFdaSrcHelp = e.target.closest("[data-open-fda-src-help]");
    if (openFdaSrcHelp) {
      e.preventDefault();
      e.stopPropagation();
      openFdaSrcHelpModal();
      return;
    }
    if (e.target.closest("[data-close-cover-list]")) {
      closeCoverListModal();
      return;
    }
    if (e.target.closest("[data-close-modal]")) {
      closeModal();
      return;
    }
    const enqueueBtn = e.target.closest("[data-enqueue]");
    if (enqueueBtn) {
      e.preventDefault();
      encolarFuente(enqueueBtn.dataset.enqueue, enqueueBtn);
      return;
    }
    const covChip = e.target.closest(".cover-pa-cov-chips [data-cover-pa-cov]");
    if (covChip && ($("coverListModal")?.classList.contains("is-open") || $("fichaModal")?.classList.contains("is-open"))) {
      e.preventDefault();
      const cov = covChip.dataset.coverPaCov || "todos";
      // La pestaña de medicamentos cambia de vista completa, no de filtro: requiere repintar el modal de país.
      if (cov === "medicamentos" || state.coverVista === "medicamentos") {
        state.coverVista = cov === "medicamentos" ? "medicamentos" : "principios";
        if (cov !== "medicamentos") COVER_LIST_CACHE.cobertura = cov;
        closeCoverListModal();
        openCoverModal(COVER_LIST_CACHE.paisId || state.coverPais);
        return;
      }
      COVER_LIST_CACHE.cobertura = cov;
      document.querySelectorAll(".cover-pa-cov-chips [data-cover-pa-cov]").forEach((el) => {
        el.classList.toggle("is-on", el.dataset.coverPaCov === COVER_LIST_CACHE.cobertura);
      });
      filtrarCoverPaCards(COVER_LIST_CACHE.q || ($("coverPaFilter")?.value || ""));
      return;
    }
    const coverList = e.target.closest("[data-open-cover-list]");
    if (coverList) {
      e.preventDefault();
      const paisId = coverList.dataset.coverPais || COVER_LIST_CACHE.paisId;
      const pais = paisesUi().find((x) => x.id === paisId);
      if (!pais) return;
      openCoverListModal({
        pais,
        titulo: `Principios activos · ${pais.full}`,
        badgeTexto: { cls: "ok", label: "Principios activos" },
        items: COVER_LIST_CACHE.todos,
        emptyText: "No hay principios activos en la lista.",
        tipo: "todos",
        cobertura: "todos",
      });
      return;
    }
    const backList = e.target.closest("[data-back-cover-list]");
    if (backList) {
      e.preventDefault();
      const paisId = backList.dataset.backCoverList || COVER_LIST_CACHE.paisId || state.coverPais;
      if (!paisesUi().some((x) => x.id === paisId)) return;
      state.coverVista = "principios";
      closeCoverListModal();
      openCoverModal(paisId);
      return;
    }
    const openReg = e.target.closest("[data-open-reg]");
    if (openReg) {
      e.preventDefault();
      openRegulatorChooserModal(
        openReg.dataset.openReg,
        openReg.dataset.coverPais || COVER_LIST_CACHE.paisId,
        openReg.dataset.regFrom || "cover",
      );
      return;
    }
    const backReg = e.target.closest("[data-back-reg-chooser]");
    if (backReg) {
      e.preventDefault();
      const compareOpen = $("regCompareModal")?.classList.contains("is-open");
      if (compareOpen) {
        closeRegCompareModal();
        return;
      }
      const from = backReg.dataset.regFrom || REG_CHOOSER.from || "cover";
      const n = backReg.dataset.backRegChooser || REG_CHOOSER.n;
      const paisId = backReg.dataset.coverPais || REG_CHOOSER.paisId || COVER_LIST_CACHE.paisId;
      if (from === "ficha") {
        closeCoverListModal();
        return;
      }
      openRegulatorChooserModal(n, paisId, from);
      return;
    }
    const openFda = e.target.closest("[data-open-fda]");
    if (openFda) {
      e.preventDefault();
      closeRegCompareModal();
      openFdaPrincipioModal(
        openFda.dataset.openFda,
        openFda.dataset.coverPais || COVER_LIST_CACHE.paisId,
        openFda.dataset.regFrom || REG_CHOOSER.from || "ficha",
      );
      return;
    }
    const openEma = e.target.closest("[data-open-ema]");
    if (openEma) {
      e.preventDefault();
      openEmaPrincipioModal(
        openEma.dataset.openEma,
        openEma.dataset.coverPais || COVER_LIST_CACHE.paisId,
        openEma.dataset.regFrom || REG_CHOOSER.from || "ficha",
      );
      return;
    }
    const openCmpGen = e.target.closest("[data-open-reg-compare-general]");
    if (openCmpGen) {
      e.preventDefault();
      openRegCompareGeneralModal(
        openCmpGen.dataset.openRegCompareGeneral,
        openCmpGen.dataset.coverPais || COVER_LIST_CACHE.paisId,
        openCmpGen.dataset.regFrom || REG_CHOOSER.from || "ficha",
      );
      return;
    }
    const regCompare = e.target.closest("[data-reg-compare]");
    if (regCompare) {
      e.preventDefault();
      openRegCompareModal(regCompare.dataset.regCompare);
      return;
    }
    const closeRegCompare = e.target.closest("[data-close-reg-compare]");
    if (closeRegCompare) {
      e.preventDefault();
      closeRegCompareModal();
      return;
    }
    const back = e.target.closest("[data-back-cover]");
    if (back) {
      e.preventDefault();
      openCoverModal(back.dataset.backCover);
      return;
    }
    const cover = e.target.closest("[data-cover-pais]");
    if (cover) {
      e.preventDefault();
      state.cq = "";
      state.csort = "medicamento";
      state.cdir = 1;
      state.cpage = 1;
      state.csize = 50;
      openCoverModal(cover.dataset.coverPais);
      return;
    }
    const open = e.target.closest("[data-open]");
    const detail = e.target.closest("[data-cover-detail]");
    if (detail) {
      e.preventDefault();
      const item = COVER_DETAIL_CACHE[Number(detail.dataset.coverDetail)];
      openCoverDetailModal(item);
      return;
    }
    const skuDetail = e.target.closest("[data-sku-detail]");
    if (skuDetail) {
      e.preventDefault();
      const group = skuDetail.dataset.skuGroup || "sku";
      const item = (SKU_DETAIL_CACHE[group] || [])[Number(skuDetail.dataset.skuDetail)];
      openCoverDetailModal(item);
      return;
    }
    const skuSort = e.target.closest("[data-sku-sort]");
    if (skuSort && state.selected != null) {
      e.preventDefault();
      const group = skuSort.dataset.skuGroup || "sku";
      const key = skuSort.dataset.skuSort;
      const st = skuTableState(group);
      st.dir = st.sort === key ? -st.dir : 1;
      st.sort = key;
      st.page = 1;
      openModal(state.selected);
      return;
    }
    const skuNav = e.target.closest("[data-sku-nav]");
    if (skuNav && state.selected != null) {
      e.preventDefault();
      const group = skuNav.dataset.skuGroup || "sku";
      const st = skuTableState(group);
      st.page += skuNav.dataset.skuNav === "next" ? 1 : -1;
      openModal(state.selected);
      return;
    }
    if (open) {
      // Si data-open está en un <tr>, no abrir al clic en controles hijos (enlaces/botones).
      // Si el propio control tiene data-open (p. ej. "Ver comparación"), sí debe abrir.
      const nested = e.target.closest("a[href], button");
      if (nested && nested !== open) return;
      e.preventDefault();
      const stage = $("stage");
      if (stage && stage.contains(open)) state.coverPais = null;
      openModal(Number(open.dataset.open));
      return;
    }
    if (e.target.closest("#sideToggle")) {
      e.preventDefault();
      const app = document.getElementById("appShell");
      setSidebarCollapsed(!app?.classList.contains("is-collapsed"));
      return;
    }
    const nav = e.target.closest("[data-view]");
    if (nav && nav.classList.contains("nav-item")) {
      e.preventDefault();
      irA(nav.dataset.view);
      return;
    }
    const coverSort = e.target.closest("[data-cover-sort]");
    if (coverSort && state.coverPais) {
      const key = coverSort.dataset.coverSort;
      state.cdir = state.csort === key ? -state.cdir : 1;
      state.csort = key;
      openCoverModal(state.coverPais);
      return;
    }
    if (e.target.closest("[data-nav='cover-prev']")) { state.cpage -= 1; openCoverModal(state.coverPais); return; }
    if (e.target.closest("[data-nav='cover-next']")) { state.cpage += 1; openCoverModal(state.coverPais); return; }
    const stage = $("stage");
    if (!stage || !stage.contains(e.target)) return;
    const prog = e.target.closest("[data-prog]");
    if (prog) {
      state.programa = prog.dataset.prog;
      state.page = 1;
      render();
      return;
    }
    const sort = e.target.closest("[data-sort]");
    if (sort) {
      const key = sort.dataset.sort;
      state.dir = state.sort === key ? -state.dir : 1;
      state.sort = key;
      render();
      return;
    }
    if (e.target.closest("[data-nav='c-prev']")) { state.page -= 1; render(); return; }
    if (e.target.closest("[data-nav='c-next']")) { state.page += 1; render(); return; }
    if (e.target.closest("[data-nav='d-prev']")) { state.dpage -= 1; render(); return; }
    if (e.target.closest("[data-nav='d-next']")) { state.dpage += 1; render(); return; }
  });
  document.addEventListener("focusin", (e) => {
    if (e.target.id === "tendSearch") abrirTendPicker();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      const fdaSrcHelp = $("fdaSrcHelpModal");
      if (fdaSrcHelp && fdaSrcHelp.classList.contains("is-open")) {
        closeFdaSrcHelpModal();
        return;
      }
      const regCompareModal = $("regCompareModal");
      if (regCompareModal && regCompareModal.classList.contains("is-open")) {
        closeRegCompareModal();
        return;
      }
      const coverListModal = $("coverListModal");
      if (coverListModal && coverListModal.classList.contains("is-open")) {
        closeCoverListModal();
        return;
      }
      if (state.selected != null && state.coverPais) {
        openCoverModal(state.coverPais);
        return;
      }
      closeModal();
    }
    if (e.target.id === "tendSearch" && e.key === "Enter") {
      const first = document.querySelector("[data-tend-pick]");
      if (first) {
        e.preventDefault();
        seleccionarTendMedicamento(first.getAttribute("data-tend-pick") || "");
      }
      return;
    }
    if (state.tendPickerOpen && e.key === "Escape") {
      cerrarTendPicker();
      return;
    }
    const cover = e.target.closest("[data-cover-pais]");
    if (cover && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault();
      openCoverModal(cover.dataset.coverPais);
    }
  });
  document.addEventListener("input", (e) => {
    if (e.target.id === "q") {
      state.q = e.target.value;
      state.page = 1;
      renderComparativo();
      const el = $("q");
      if (el) {
        el.focus();
        el.setSelectionRange(state.q.length, state.q.length);
      }
    }
    if (e.target.id === "dq") {
      state.dq = e.target.value;
      state.dpage = 1;
      renderDetalle();
      const el = $("dq");
      if (el) {
        el.focus();
        el.setSelectionRange(state.dq.length, state.dq.length);
      }
    }
    if (e.target.id === "coverQ" && state.coverPais) {
      state.cq = e.target.value;
      state.cpage = 1;
      openCoverModal(state.coverPais);
      const el = $("coverQ");
      if (el) {
        el.focus();
        el.setSelectionRange(state.cq.length, state.cq.length);
      }
    }
    if (e.target.id === "coverPaFilter") {
      filtrarCoverPaCards(e.target.value);
    }
    if (e.target.id === "tendSearch") {
      state.tendSearchQ = e.target.value || "";
      abrirTendPicker();
      renderTendPickerList();
    }
  });
  document.addEventListener("mouseover", (e) => {
    const dot = e.target.closest?.(".tend-dot");
    const tip = $("tendTip");
    if (dot && tip && dot.dataset.tip) tip.textContent = dot.dataset.tip;
  });
  document.addEventListener("change", (e) => {
    if (e.target.id === "tendSoloMulti") {
      state.tendSoloMulti = !!e.target.checked;
      cargarTendenciasUI();
      return;
    }
    if (e.target.id === "tendPaisSelect") {
      state.tendPaisFiltro = e.target.value || "todos";
      state.tendSearchQ = "";
      const input = $("tendSearch");
      if (input) input.value = "";
      const opts = tendMedicamentosVisibles();
      const selectedVal = tendSelectedValue();
      if (selectedVal && !opts.some((m) => tendOptionValue(m) === selectedVal)) {
        const first = opts[0];
        state.tendenciaN = first ? Number(first.n_lista) : null;
        state.tendenciaProductoKey = first ? String(first.producto_key || "") : null;
      }
      renderTendPickerList();
      if (state.tendenciaN && state.tendenciaProductoKey) {
        pintarTendenciaMedicamento(state.tendenciaN, state.tendenciaProductoKey);
      } else {
        const table = $("tendTable");
        if (table) table.innerHTML = `<p class="muted">Selecciona un medicamento del país elegido.</p>`;
        const kpis = $("tendKpis");
        const gapsEl = $("tendGaps");
        if (kpis) kpis.innerHTML = "";
        if (gapsEl) gapsEl.innerHTML = "";
      }
      return;
    }
    if (e.target.id === "filtroConc") {
      state.conc = e.target.value;
      state.page = 1;
      state.dpage = 1;
      render();
      return;
    }
    if (e.target.id === "filtroPres") {
      state.pres = e.target.value;
      state.page = 1;
      state.dpage = 1;
      render();
      return;
    }
    if (e.target.id === "filtroAlcance") {
      state.alcance = e.target.value;
      state.page = 1;
      state.dpage = 1;
      render();
      return;
    }
    if (e.target.id === "filtroDato") {
      state.conDato = e.target.value;
      state.page = 1;
      render();
      return;
    }
    if (e.target.id === "filtroPais") {
      state.paisFiltro = e.target.value;
      state.page = 1;
      render();
      return;
    }
    if (e.target.id === "dpais") {
      state.dpais = e.target.value;
      state.dpage = 1;
      render();
    }
    if (e.target.dataset.size === "c") {
      state.size = Number(e.target.value);
      state.page = 1;
      render();
    }
    if (e.target.dataset.size === "d") {
      state.dsize = Number(e.target.value);
      state.dpage = 1;
      render();
    }
    if (e.target.dataset.size === "cover" && state.coverPais) {
      state.csize = Number(e.target.value);
      state.cpage = 1;
      openCoverModal(state.coverPais);
    }
  });
}

async function cargarTasas() {
  try {
    const r = await fetch("/api/tasas", { cache: "no-store" });
    const data = await r.json();
    if (!data.ok || !Array.isArray(data.tasas)) return;
    D.tasas = D.tasas || [];
    for (const t of data.tasas) {
      const mon = monedaDeEtiqueta(t["País / moneda"]);
      if (!mon) continue;
      const i = D.tasas.findIndex((x) => monedaDeEtiqueta(x["País / moneda"]) === mon);
      if (i >= 0) D.tasas[i] = { ...D.tasas[i], ...t };
      else D.tasas.push(t);
    }
  } catch (err) {
    console.error(err);
  }
}

async function cargarTabla() {
  try {
    const r = await fetch("/api/precios", { cache: "no-store" });
    const data = await r.json();
    if (!data.ok) throw new Error(data.error || "API");
    TABLA = data.filas || [];
    SNAPSHOT_FECHA = data.fecha_dato || data.snapshot || null;
    LIVE_OK = true;
  } catch (err) {
    console.error(err);
    TABLA = detalleFallbackTabla();
    SNAPSHOT_FECHA = D?.generado || null;
    LIVE_OK = false;
  }
  LIVE_LOADED = true;
  actualizarPill();
}

function detalleFallbackTabla() {
  const det = Array.isArray(D?.detalle) ? D.detalle : [];
  return det.map((row) => ({
    n_lista: row.n,
    medicamento_lista: row.medicamento,
    programa: row.programa,
    pais: row.pais,
    farmacia: row.tipo || row.farmacia || "",
    nombre_comercial: row.producto,
    presentacion: row.presentacion,
    concentracion: row.dosis,
    cantidad_concentracion: row.cantidad_concentracion,
    unidad_concentracion: row.unidad_concentracion,
    tipo_presentacion: row.tipo_presentacion,
    cantidad_presentacion: row.cantidad_presentacion,
    alcance_presentacion: row.alcance_presentacion,
    precio: row.precio_local,
    moneda: row.moneda,
    fuente_url: row.fuente,
    fecha_dato: row.fecha_dato,
    calidad: row.calidad || "ok",
    laboratorio: row.laboratorio,
    disponibilidad: row.disponibilidad || "Disponible",
  }));
}

async function iniciar() {
  closeModal();
  try {
    setSidebarCollapsed(localStorage.getItem("alto_costo_sidebar") === "1");
  } catch (_) { /* ignore */ }
  state.view = viewFromLocation();
  const stage = $("stage");
  if (!D) {
    if (stage) stage.innerHTML = "<p>Falta data.js. Corre <code>python exportar_web.py</code>.</p>";
    bind();
    return;
  }
  try {
    const v = ventaBcrd();
    const chip = $("fxChip");
    if (chip) chip.textContent = v ? `DOP · ${v.toFixed(2)} por USD` : "Tasas locales";
  } catch (err) {
    console.error(err);
  }
  bind();
  actualizarPill();
  renderLoadingStage();
  await cargarTasas();
  await cargarTabla();
  await asegurarIndicadoresTendencias();
  sanitizarPaisesDesactivados();
  syncRoute(state.view, true);
  render();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", iniciar);
} else {
  iniciar();
}
