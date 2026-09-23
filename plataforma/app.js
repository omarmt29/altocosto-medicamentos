const D = window.ALTO_COSTO;
const VIEWS = {
  tablero: { crumb: "Panorama", title: "Tablero" },
  comparativo: { crumb: "Análisis", title: "Comparativo" },
  detalle: { crumb: "Coincidencias", title: "Detalle" },
  tendencias: { crumb: "Análisis", title: "Análisis de precios" },
  alertas: { crumb: "Seguimiento", title: "Alertas" },
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
  py: { flag: "🇵🇾", corto: "PY", nombre: "Paraguay", full: "Paraguay" },
  ve: { flag: "🇻🇪", corto: "VE", nombre: "Venezuela", full: "Venezuela" },
  gy: { flag: "🇬🇾", corto: "GY", nombre: "Guyana", full: "Guyana" },
  tt: { flag: "🇹🇹", corto: "TT", nombre: "Trinidad y Tobago", full: "Trinidad y Tobago" },
  bo: { flag: "🇧🇴", corto: "BO", nombre: "Bolivia", full: "Bolivia" },
  us: { flag: "🇺🇸", corto: "US", nombre: "Estados Unidos", full: "Estados Unidos" },
  ca: { flag: "🇨🇦", corto: "CA", nombre: "Canadá", full: "Canadá" },
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
  paisFiltro: "todos",
  compSoloGana: false,
  conc: "todas",
  pres: "todas",
  alcance: "todos",
  sort: "programa",
  dir: 1,
  page: 1,
  size: 12,
  compAbierto: null,
  dq: "",
  dpais: "todos",
  dpage: 1,
  dsize: 12,
  selected: null,
  coverPais: null,
  coverVista: "principios", // principios | farmacias | medicamentos
  coverFarmacia: null,
  cq: "",
  csort: "medicamento",
  cdir: 1,
  cpage: 1,
  csize: 50,
  tendenciaN: null,
  tendenciaProductoKey: null,
  tendenciaLabel: "",
  tendenciaPaisNombre: "",
  tendPaises: null,
  tendFarmacias: null,
  tendAgrupar: "farmacia",
  tendChartTipo: "line",
  tendSearchQ: "",
  tendMedQ: "",
  tendProductoSel: "",
  tendConcSel: "",
  tendPresSel: "",
  tendExpandFd: null,
  tendPickerOpen: false,
  tendPaisFiltro: "todos",
  tendVista: "serie",
  fuentesTab: "datos",
  tendPeriodo: "diario",
  tendTableSort: "fecha",
  tendTableDir: 1,
  grafFecha: "",
  grafPaisA: "República Dominicana",
  grafPaisB: "Brasil",
  grafCache: null,
  expQ: "",
  expPais: "todos",
  expFarmacia: "todas",
  expPrograma: "todos",
  expFecha: "",
  expPrecioMin: "",
  expPrecioMax: "",
  expMinPaises: 0,
  expSoloMin: false,
  expTodas: false,
  expModoPrecio: "paquete",
  expOrden: "precio_asc",
  expLimite: 300,
  alertFuente: "fda",
  alertTipo: "todos",
  alertHorizonte: "180",
  alertSoloNuevas: false,
  alertVista: "patentes",
  headerAlertTab: "patentes",
  /** Solo al entrar desde toast de criterio; null = vista normal sin filtro extra. */
  alertFocusCriterioPat: null,
  alertFocusCriterioPre: null,
  alertActPage: 1,
  alertActSize: 12,
  alertHistPage: 1,
  alertHistSize: 12,
  alertHistSort: "expiration_date",
  alertHistDir: -1,
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
let ALERTAS_DATA = {
  filas: [],
  resumen: {},
  configs: [],
  opcionesCriterios: { medicamentos: [], fuentes: [], presets_dias: [7, 30, 60, 90, 180, 365] },
  cargando: false,
  loaded: false,
  error: null,
  detectando: false,
};
let ALERTAS_PAT_CFG = {
  form: {
    id: null,
    nombre: "",
    dias_min: "0",
    dias_max: "180",
    avisar_vence_hoy: true,
    avisar_paso_expirada: true,
    avisar_diario: true,
    intervalo_valor: "24",
    intervalo_unidad: "horas",
    fuente: "fda",
    n_lista: "",
    medicamento_lista: "",
  },
  modalOpen: false,
  guardando: false,
  error: null,
};
let ALERTAS_PRECIOS = {
  configs: [],
  filas: [],
  resumen: {},
  opciones: { paises: [], farmacias: [], productos: [], medicamentos: [], presentaciones: [], concentraciones: [] },
  form: {
    id: null,
    nombre: "",
    pais: "",
    farmacia: "",
    producto_key: "",
    n_lista: "",
    medicamento_lista: "",
    nombre_comercial: "",
    presentacion: "",
    concentracion: "",
    umbral_baja_pct: "10",
    umbral_sube_pct: "",
    intervalo_valor: "24",
    intervalo_unidad: "horas",
  },
  cargando: false,
  guardando: false,
  detectando: false,
  loaded: false,
  modalOpen: false,
  error: null,
  page: 1,
  size: 12,
};
let TEND_CATALOG = { medicamentos: [], indicadores: null, fechas: [] };
/** Caché en memoria de pestañas Análisis (sobrevive al cambiar de tab; se limpia con hard refresh). */
const TEND_KEEP = {
  host: null,
  panels: new Map(), // vista -> HTMLElement
  loaded: { serie: false, graficos: false, comparativo: false },
  grafMounted: false,
  catalogLoaded: false,
};
/** Serie por medicamento: n|producto_key → respuesta API */
const TEND_SERIE_CACHE = new Map();

const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
const dop = new Intl.NumberFormat("es-DO", { style: "currency", currency: "DOP", maximumFractionDigits: 0 });
const $ = (id) => document.getElementById(id);

function viewFromLocation(pathname = window.location.pathname) {
  const raw = String(pathname || "").replace(/^\/+|\/+$/g, "").trim().toLowerCase();
  if (!raw) return "tablero";
  // Comparativo vive como pestaña dentro de Análisis.
  if (raw === "comparativo") return "comparativo";
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

function corregirUrlKielsa(url) {
  const u = String(url || "").trim();
  if (!u || !/kielsa\.com/i.test(u)) return u;
  // Ruta legacy /producto/{slug}/{id} → /ProductDetails/{id}
  const m = u.match(/^(https?:\/\/(?:www\.)?kielsa\.com(?:\.[a-z]{2})?)\/producto\/[^/]+\/([^/?#]+)/i);
  if (m) return `${m[1]}/ProductDetails/${m[2]}`;
  // Normalizar variantes de casing de la ruta actual
  return u.replace(
    /^(https?:\/\/(?:www\.)?kielsa\.com(?:\.[a-z]{2})?)\/productdetails?\//i,
    (_, origin) => `${origin}/ProductDetails/`,
  );
}

/** Inkafarma PE: /{uri} → /producto/{uri}/{id} (sin /producto/ cae en 404). */
function corregirUrlInkafarma(url, f = null) {
  const u = String(url || "").trim();
  if (!u || !/inkafarma\.pe/i.test(u)) return u;
  if (/\/producto\//i.test(u)) return u;
  try {
    const parsed = new URL(u);
    const parts = parsed.pathname.replace(/^\/+|\/+$/g, "").split("/").filter(Boolean);
    if (parts.length !== 1) return u;
    const slug = parts[0];
    if (!slug || /^(buscador|buscar|404|cart|login|categoria)$/i.test(slug)) return u;
    const oid = String(f?.id_producto_farmacia || f?.sku || "").trim();
    if (oid && !/^https?:/i.test(oid)) {
      return `${parsed.origin}/producto/${slug}/${encodeURIComponent(oid)}`;
    }
    return `${parsed.origin}/producto/${slug}`;
  } catch (_) {
    return u;
  }
}

function fuenteUrlVisible(f) {
  let url = String(f?.fuente_url || f?.fuente || "").trim();
  if (!url) return "";

  if (esUrlApiFarmacia(url) || /^datos\//i.test(url)) {
    const alt = pdpVtexDesdeFila(f, url);
    if (alt) return corregirUrlSiman(alt, f?.pais, f?.farmacia);
    const soloHttp = String(f?.fuente_url || "").trim();
    if (soloHttp && /^https?:\/\//i.test(soloHttp) && !esUrlApiFarmacia(soloHttp)) {
      return corregirUrlInkafarma(
        corregirUrlKielsa(corregirUrlSiman(soloHttp, f?.pais, f?.farmacia)),
        f,
      );
    }
    return "";
  }

  if (!/^https?:\/\//i.test(url)) return "";
  // /s?ft= ya viene normalizado desde la API cuando el SKU no existe en esa tienda regional.
  if (/\/s\?ft=/i.test(url)) return url;
  return corregirUrlInkafarma(
    corregirUrlKielsa(corregirUrlSiman(url, f?.pais, f?.farmacia)),
    f,
  );
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

function fmtUsdText(n) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  const num = Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `USD ${num}`;
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

const FLAG_SVG = new Set([
  "do", "br", "mx", "ar", "co", "pe", "cl", "cr", "ec", "hn", "gt", "ni", "pa", "uy", "sv",
  "py", "ve", "gy", "tt", "bo", "us", "ca",
]);

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

const PAIS_ORDEN = [
  "do", "br", "mx", "ec", "hn", "gt", "ni", "cr", "pa", "ar", "co", "pe", "cl", "uy", "sv",
  "py", "ve", "gy", "tt", "bo", "us", "ca",
];

function ordenarPaisIds(ids) {
  const set = ids instanceof Set ? ids : new Set(ids);
  const ordenados = PAIS_ORDEN.filter((id) => set.has(id) && paisActivo(id));
  const extra = [...set].filter((id) => paisActivo(id) && !PAIS_ORDEN.includes(id)).sort();
  return [...ordenados, ...extra];
}

function paisesUi() {
  const vivos = paisesVivos();
  const ids = vivos.size
    ? ordenarPaisIds(vivos)
    : (D.paises || []).map((p) => p.id).filter(paisActivo);
  return ids.map((id) => {
    const fromData = (D.paises || []).find((p) => p.id === id) || { id, nombre: PAIS_UI[id]?.full || id, corto: (id || "").toUpperCase() };
    return paisUi(fromData);
  });
}

/** Tablero: todos los países del catálogo + historial, aunque el snapshot de hoy no tenga filas. */
function paisesUiPanorama() {
  const ids = ordenarPaisIds(paisesIdsPanorama());
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
    ["paraguay", "py"],
    ["venezuela", "ve"],
    ["guyana", "gy"],
    ["trinidad y tobago", "tt"],
    ["trinidad", "tt"],
    ["bolivia", "bo"],
    ["estados unidos", "us"],
    ["united states", "us"],
    ["canada", "ca"],
    ["canadá", "ca"],
  ];
  for (const [pista, id] of mapa) {
    if (s.includes(pista)) return id;
  }
  if (/\b(usa|u\.s\.a\.|u\.s\.)\b/.test(s)) return "us";
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

/** Agrupa solo formas idénticas; no mezcla recubierto con simple. */
function formaComparacion(forma) {
  return forma || null;
}

function etiquetaFormaComparacion(forma) {
  const map = {
    comprimido: "comprimido",
    comprimido_revestido: "comprimido recubierto",
    capsula: "cápsula",
    tableta: "comprimido",
    inyectable: "inyectable",
    polvo_liofilizado: "polvo liofilizado",
    polvo: "polvo",
    topico: "tópico",
  };
  return map[forma] || String(forma || "").replace(/_/g, " ");
}

/** Sufijos / variantes comerciales que no deben mezclarse en el comparativo. */
function modificadorProducto(f) {
  const blob = asciiNorm(`${f.nombre_comercial || ""} ${f.presentacion || ""} ${f.tipo_presentacion || ""}`);
  const mods = [];
  if (/\b(forte|fort|plus|extra|duo|trio|max|ultra)\b/.test(blob)) {
    const m = blob.match(/\b(forte|fort|plus|extra|duo|trio|max|ultra)\b/);
    if (m) mods.push(m[1] === "fort" ? "forte" : m[1]);
  }
  if (/\b(pediatric|pediatrico|infantil|kids|junior|baby)\b/.test(blob)) mods.push("pediatrico");
  if (/\b(adult|adulto)\b/.test(blob)) mods.push("adulto");
  if (/\b(retard|prolongad|extended|modified|xr|sr|cr|er|mr|pr|la|lp)\b/.test(blob)) mods.push("modificada");
  if (/\b(odis|orodispers|sublingual|bucal)\b/.test(blob)) mods.push("odis");
  if (/\b(hp|high potency)\b/.test(blob)) mods.push("hp");
  return mods.length ? [...new Set(mods)].sort().join("+") : "base";
}

const STOP_TOKENS_PROD = new Set([
  "mg", "mcg", "ug", "ui", "iu", "ml", "g", "x", "c", "de", "del", "la", "el", "los", "las",
  "y", "con", "para", "uso", "ref", "referencia", "generico", "generica", "similar", "equivalente",
  "biosimilar", "comprimido", "comprimidos", "tableta", "tabletas", "capsula", "capsulas",
  "ampolla", "ampollas", "vial", "viales", "jeringa", "jeringas", "caja", "lote", "kit",
  "frasco", "solucion", "inyectable", "oral", "prellenada", "precargada", "recubierto",
  "revestido", "film", "coated",
]);

function tokensNombreProducto(f) {
  let t = asciiNorm(f.nombre_comercial || "");
  t = t.replace(/\b\d+(?:[.,]\d+)?\s*(?:mg|mcg|ug|ui|iu|g|ml)(?:\s*\/\s*\d+(?:[.,]\d+)?\s*(?:ml|mg))?/g, " ");
  t = t.replace(/\b(?:x|c)\s*\d+\b/g, " ");
  t = t.replace(/[^a-z0-9\s+/]/g, " ");
  const principio = new Set(asciiNorm(f.medicamento_lista || "").split(/\s+/).filter(Boolean));
  return t
    .split(/[\s+/]+/)
    .map((tok) => tok.trim())
    .filter((tok) => tok.length >= 3 && !STOP_TOKENS_PROD.has(tok) && !principio.has(tok));
}

function jaccardTokens(a, b) {
  const A = new Set(a || []);
  const B = new Set(b || []);
  if (!A.size || !B.size) return 0;
  let inter = 0;
  for (const x of A) if (B.has(x)) inter += 1;
  return inter / (A.size + B.size - inter);
}

function similitudProducto(fa, fb) {
  const ta = tokensNombreProducto(fa);
  const tb = tokensNombreProducto(fb);
  let score = jaccardTokens(ta, tb);
  // Primer token de marca: si coincide, refuerza; si ambos existen y difieren, penaliza.
  if (ta[0] && tb[0]) {
    if (ta[0] === tb[0]) score = Math.min(1, score + 0.35);
    else score *= 0.45;
  }
  if (modificadorProducto(fa) !== modificadorProducto(fb)) score *= 0.25;
  return score;
}

function coherenciaProductosGrupo(filas) {
  const porPais = new Map();
  for (const f of filas) {
    const id = idPaisPorTexto(f.pais);
    if (!id) continue;
    if (!porPais.has(id)) porPais.set(id, f);
  }
  const samples = [...porPais.values()];
  if (samples.length < 2) return samples.length === 1 ? 0.5 : 0;
  let sum = 0;
  let n = 0;
  for (let i = 0; i < samples.length; i += 1) {
    for (let j = i + 1; j < samples.length; j += 1) {
      sum += similitudProducto(samples[i], samples[j]);
      n += 1;
    }
  }
  return n ? sum / n : 0;
}

function firmaConsensoProductos(filas) {
  const freq = new Map();
  for (const f of filas) {
    for (const tok of tokensNombreProducto(f)) {
      freq.set(tok, (freq.get(tok) || 0) + 1);
    }
  }
  return [...freq.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, 4)
    .map(([t]) => t);
}

function scoreVsFirma(f, firmaTokens) {
  if (!(firmaTokens || []).length) return 0;
  return jaccardTokens(tokensNombreProducto(f), firmaTokens);
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
  const alcance = alcanceDe(f) || "desconocido";
  const mod = modificadorProducto(f);
  // Liberación ya va en `lib`; si el modificador solo dice "modificada", no duplicar.
  const modKey = mod === "modificada" && lib === "modificada" ? "base" : mod;
  const incompleto = !conc || !forma || !cant;
  const claveMedicina = incompleto
    ? null
    : `${f.n_lista}|${conc}|${forma}|${lib}|${via}|${modKey}`;
  // Empaque (alcance) entra en la clave: no mezclar unidad con caja/lote/kit.
  const clavePresentacion = claveMedicina && cant
    ? `${claveMedicina}|${cant}|${alcance}`
    : null;
  return {
    n_lista: f.n_lista,
    concentracion: conc,
    forma,
    formaRaw,
    cantidad: cant,
    liberacion: lib,
    via,
    alcance,
    modificador: modKey,
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

/** Combinación de dos principios (p. ej. "50 mg + otro" o "A / B"). */
function esComboMultiprincipio(f) {
  const n = String(f.nombre_comercial || "");
  const mPlus = n.match(/^(.+?)\s*\+\s*(.+)$/i);
  const mSlash = !mPlus ? n.match(/^(.+?)\s*\/\s*(.+)$/i) : null;
  const m = mPlus || mSlash;
  if (!m) return false;
  const izq = asciiNorm(m[1]);
  const der = asciiNorm(m[2]);
  const principio = tokenPrincipioActivo(f);
  if (principio && der.includes(principio)) return false;
  // "mg / ml" de una sola concentración no es combo.
  if (mSlash && /\b(mg|mcg|ui|iu|g)\b/.test(izq) && /^(ml|mg)\b/.test(der)) return false;
  return (/\d+\s*mg/.test(izq) && /\d+\s*mg/.test(der)) || (mPlus && izq.length > 2 && der.length > 2);
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

  // Quitar outliers de nombre dentro del mismo grupo (p. ej. variante "Forte" mal etiquetada).
  if (pool.length >= 4) {
    const firma = firmaConsensoProductos(pool);
    if (firma.length) {
      const scored = pool.map((f) => ({ f, s: scoreVsFirma(f, firma) }));
      const buenos = scored.filter((x) => x.s >= 0.15 || tokensNombreProducto(x.f).length === 0);
      // Si hay marcas distintas pero genéricas sin tokens, no vaciar el pool.
      if (buenos.length >= Math.max(2, Math.ceil(pool.length * 0.4))) {
        pool = buenos.map((x) => x.f);
      }
    }
  }

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

function elegirFilaRepresentativaPais(filasPais, firmaTokens = null) {
  const ordenadas = filasPais
    .map((f) => ({
      f,
      u: aUsd(f.precio, f.moneda),
      sim: firmaTokens && firmaTokens.length ? scoreVsFirma(f, firmaTokens) : 0,
    }))
    .filter((x) => x.u != null)
    .sort((a, b) => {
      if (Math.abs((b.sim || 0) - (a.sim || 0)) > 0.08) return (b.sim || 0) - (a.sim || 0);
      return a.u - b.u;
    });
  if (!ordenadas.length) return filasPais[0] || null;
  if (ordenadas.length <= 2) return ordenadas[0].f;
  const topSim = ordenadas[0].sim || 0;
  const cercanos = ordenadas.filter((x) => (x.sim || 0) >= topSim - 0.12);
  const mid = Math.floor(cercanos.length / 2);
  return cercanos[mid].f;
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
    return `${p.claveMedicina}|1|unidad`;
  }
  return p.clavePresentacion;
}

function etiquetaClave(clave) {
  if (!clave) return "";
  const parts = String(clave).split("|");
  // Nuevo: n|conc|forma|lib|via|mod|cant|alcance  (8)
  // Previo: n|conc|forma|lib|via|cant               (6)
  if (parts.length >= 7) {
    const conc = parts[1];
    const forma = parts[2];
    const lib = parts[3];
    const mod = parts.length >= 8 ? parts[5] : "base";
    const cant = parts.length >= 8 ? parts[6] : parts[5];
    const alcance = parts.length >= 8 ? parts[7] : (parts.length >= 7 ? parts[6] : "");
    let base = `${conc} · ${etiquetaFormaComparacion(forma)} x ${cant}`;
    if (alcance && alcance !== "desconocido") base += ` · ${etiquetaAlcance(alcance)}`;
    if (lib === "modificada") base += " · liberación modificada";
    if (mod && mod !== "base") base += ` · ${mod.replace(/\+/g, " · ")}`;
    return base;
  }
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
    return `<td class="td-precio ${cls}" title="${escapeHtml(paisMeta.full)}: sin la misma concentración, empaque y variante de producto"><span class="empty">—</span></td>`;
  }
  const pu = cel.min_usd_unidad;
  const cant = cel.cantidad;
  const prod = cel.ejemplo || "";
  const farm = cel.tipo || cel.farmacia || "";
  const title = [
    `${paisMeta.full}: ${fmtUsdText(v)}`,
    pu != null && cant > 1 ? `${fmtUsdText(pu)} por unidad (${cant} uds.)` : "",
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
    if (!votos.has(k)) votos.set(k, { paises: new Set(), n: 0, filas: [] });
    const v = votos.get(k);
    v.paises.add(id);
    v.n += 1;
    v.filas.push(f);
  }
  let mejor = null;
  let score = [-1, -1, -1, -1];
  for (const [k, v] of votos) {
    const alcanceConocido = !String(k).endsWith("|desconocido") ? 1 : 0;
    const coherencia = coherenciaProductosGrupo(v.filas);
    // [países, alcance conocido, coherencia de nombre, filas]
    const s = [v.paises.size, alcanceConocido, Math.round(coherencia * 1000), v.n];
    const better =
      s[0] > score[0] ||
      (s[0] === score[0] && s[1] > score[1]) ||
      (s[0] === score[0] && s[1] === score[1] && s[2] > score[2]) ||
      (s[0] === score[0] && s[1] === score[1] && s[2] === score[2] && s[3] > score[3]);
    if (better) {
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
      : (filas.length ? "Sin concentración, empaque y variante comparable" : "");
    if (!elec.clave) continue;
    const pool = filasComparablesClave(filas, elec.clave);
    const firma = firmaConsensoProductos(pool);
    const porPais = new Map();
    for (const f of pool) {
      const id = idPaisPorTexto(f.pais);
      if (!id) continue;
      if (!porPais.has(id)) porPais.set(id, []);
      porPais.get(id).push(f);
    }
    for (const [id, fps] of porPais) {
      const f = elegirFilaRepresentativaPais(fps, firma);
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
  // Sin ningún país con precio no hay nada que comparar: la tarjeta no aporta.
  let rows = overlayComparativo().filter((r) => Number(r.paises_con_dato || 0) > 0);
  if (state.programa === "fomac") rows = rows.filter((r) => String(r.programa).includes("FOMAC"));
  else if (state.programa !== "todos") rows = rows.filter((r) => r.programa === state.programa);
  if (state.paisFiltro !== "todos") {
    rows = rows.filter((r) => (r.paises[state.paisFiltro]?.min_usd ?? null) != null);
    if (state.compSoloGana) {
      const paises = paisesUi();
      // Con un solo país no hay comparación que ganar, así que esos quedan fuera.
      rows = rows.filter((r) => {
        const orden = compPaisesConPrecio(r, paises);
        return orden.length > 1 && orden[0].meta.id === state.paisFiltro;
      });
    }
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

function panelFiltros({ buscaId, buscaVal, placeholder, extra = "", sinCampos = false }) {
  const concs = sinCampos ? [] : opcionesCampo("concentracion");
  const press = sinCampos ? [] : opcionesCampo("presentacion");
  const alcances = sinCampos ? [] : opcionesCampo("alcance");
  return `
    <div class="filter-panel${sinCampos ? " filter-panel--comp" : ""}">
      <label class="filter-field">
        <span>Buscar</span>
        <input class="search" id="${buscaId}" placeholder="${escapeHtml(placeholder)}" value="${escapeHtml(buscaVal)}" />
      </label>
      ${sinCampos ? "" : `
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
      </label>`}
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

/** Clave de producto alineada al historial (nombre · concentración · presentación). */
function productoKeyFila(f) {
  const parts = [
    String(f?.nombre_comercial || "").trim().toLowerCase(),
    String(f?.concentracion || "").trim().toLowerCase(),
    String(f?.presentacion || "").trim().toLowerCase(),
  ].filter(Boolean);
  return parts.join("|") || String(f?.id_producto_farmacia || f?.sku || "").trim() || "sin_identificar";
}

/** Principios con precio en un país — misma métrica que «Principios activos por país» en Tendencias. */
function principiosActivosPorPaisId(paisId) {
  const histN = Number(histPaisRow(paisId)?.principios || 0);
  if (histN > 0) return histN;
  return snapPrincipiosPorPaisId(paisId);
}

/** Medicamentos (producto_key) con precio — misma métrica que en Tendencias. */
function medicamentosPorPaisId(paisId) {
  const histN = Number(histPaisRow(paisId)?.medicamentos || 0);
  if (histN > 0) return histN;
  return snapMedicamentosPorPaisId(paisId);
}

function snapPrincipiosPorPaisId(paisId) {
  return new Set(
    TABLA.filter((f) => filaPaisActivo(f) && idPaisPorTexto(f.pais) === paisId && filaConPrecio(f))
      .map((f) => f.n_lista)
      .filter((n) => n != null),
  ).size;
}

function snapMedicamentosPorPaisId(paisId) {
  return new Set(
    TABLA.filter((f) => filaPaisActivo(f) && idPaisPorTexto(f.pais) === paisId && filaConPrecio(f))
      .map((f) => productoKeyFila(f)),
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
    const snapMeds = snapMedicamentosPorPaisId(p.id);
    const conHits = principiosActivosPorPaisId(p.id);
    const conMeds = medicamentosPorPaisId(p.id);
    const farms = [...new Set(base.filter((f) => idPaisPorTexto(f.pais) === p.id).map((f) => f.farmacia).filter(Boolean))];
    const soloHistorial = histPrincipios > 0 && snapPrincipios === 0;
    return {
      ...p,
      conHits,
      conMeds,
      snapPrincipios,
      snapMeds,
      histPrincipios,
      histMeds,
      farms,
      soloHistorial,
    };
  }).sort((a, b) => b.conHits - a.conHits || b.conMeds - a.conMeds || a.nombre.localeCompare(b.nombre, "es"));
  $("stage").innerHTML = `
    <article class="card cover-card">
      <div class="card-head cover-card-head">
        <div>
          <h2>Principios activos por país</h2>
          <p class="muted cover-card-note">Principios activos y medicamentos (presentaciones) con precio en la última fecha del historial (mismas cifras que en Análisis). Si aún no hay historial para el país, se usa el snapshot en vivo.</p>
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
          const medLabel = p.conMeds === 1 ? "medicamento" : "medicamentos";
          return `
          <div class="cover-country cover-country--${p.id}${p.soloHistorial ? " is-historial" : ""}" data-cover-pais="${p.id}" role="button" tabindex="0" title="${escapeHtml(nFarms ? p.farms.join(", ") : p.full)}">
            <div class="cover-country-head">
              ${flagImg(p.id, "cover-flag")}
              <h3 class="cover-country-name">${escapeHtml(p.nombre)}</h3>
            </div>
            <div class="cover-country-body">
              <div class="cover-stats">
                <div class="cover-stat">
                  <p class="cover-num">${p.conHits}</p>
                  <p class="cover-num-caption">principios activos</p>
                </div>
                <div class="cover-stat cover-stat--meds">
                  <p class="cover-num cover-num--meds">${p.conMeds}</p>
                  <p class="cover-num-caption">${medLabel}</p>
                </div>
              </div>
            </div>
            <div class="cover-country-foot">
              <span class="cover-foot-text">${escapeHtml(pieTexto)}</span>
            </div>
          </div>`;
        }).join("")}
      </div>
    </article>
  `;
}

/** Filas de la página visible del comparativo: evita recalcular el overlay al desplegar. */
let COMP_PAGE_ROWS = [];

function compProgramaClase(programa) {
  const p = String(programa || "");
  if (p === "FOMAC") return "es-fomac";
  if (p === "FOMAC*") return "es-fomac-star";
  if (p.includes("FOMAC")) return "es-mix";
  return "es-damac";
}

/** Países con precio del principio, del más barato al más caro. */
function compPaisesConPrecio(r, paises = paisesUi()) {
  return paises
    .map((p) => ({ meta: p, cel: r.paises?.[p.id] }))
    .filter((x) => x.cel?.min_usd != null)
    .sort((a, b) => Number(a.cel.min_usd) - Number(b.cel.min_usd));
}

function htmlCompCard(r, paises) {
  const filas = compPaisesConPrecio(r, paises);
  const mejor = filas[0] || null;
  // Con un solo país no hay comparación: el precio no se pinta como "el más barato".
  const comparable = filas.length > 1;
  const abierta = Number(state.compAbierto) === Number(r.n);
  return `
    <article class="comp-card ${compProgramaClase(r.programa)}${comparable ? "" : " is-sinpar"}${abierta ? " is-open" : ""}"
      data-comp-card="${r.n}" role="button" tabindex="0" aria-expanded="${abierta ? "true" : "false"}"
      title="Ver precios por país de ${escapeHtml(r.medicamento)}">
      <div class="comp-card-head">
        ${badge(r.programa)}
        <span class="comp-card-paises">${filas.length} ${filas.length === 1 ? "país" : "países"}</span>
      </div>
      <div class="comp-card-body">
        <h3 class="comp-card-name">${escapeHtml(r.medicamento)}</h3>
        <p class="comp-card-pres">${escapeHtml(r.presentacion_comparada || "Sin presentación comparable")}</p>
      </div>
      <div class="comp-card-price">
        ${mejor ? `
          <span class="comp-card-usd${comparable ? "" : " is-unico"}">${money(mejor.cel.min_usd)}</span>
          <span class="comp-card-usd-cap">
            ${flagImg(mejor.meta.id, "comp-card-flag")}
            ${comparable ? "más barato en" : "único país con precio:"} ${escapeHtml(mejor.meta.nombre)}
          </span>
          ${mejor.cel.min_usd_unidad != null && mejor.cel.cantidad > 1
            ? `<span class="comp-card-pu">${money(mejor.cel.min_usd_unidad)} por unidad</span>`
            : ""}`
        : `<span class="comp-card-sinpar">Sin precio</span>
           <span class="comp-card-usd-cap">Ninguna farmacia publica esta presentación</span>`}
      </div>
      <div class="comp-card-foot">
        <span class="comp-card-cta">${abierta ? "Ocultar precios" : "Ver precios por país"}</span>
      </div>
    </article>`;
}

function htmlCompDetalle(r) {
  const paises = paisesUi();
  const filas = compPaisesConPrecio(r, paises);
  const comparable = filas.length > 1;
  const sinDato = paises.filter((p) => r.paises?.[p.id]?.min_usd == null);
  const cuerpo = filas.length
    ? `<div class="table-wrap">
        <table class="data data-static comp-det-table">
          <colgroup>
            <col class="comp-col-pais" />
            <col class="comp-col-prod" />
            <col class="comp-col-farm" />
            <col class="comp-col-ud" />
            <col class="comp-col-precio" />
            <col class="comp-col-src" />
          </colgroup>
          <thead>
            <tr>
              <th>País</th>
              <th class="comp-det-prod">Producto</th>
              <th class="comp-det-farm">Farmacia</th>
              <th class="comp-det-num">Por unidad</th>
              <th class="comp-det-num">Precio</th>
              <th class="th-actions">Fuente</th>
            </tr>
          </thead>
          <tbody>
            ${filas.map(({ meta, cel }, i) => `
              <tr class="${i === 0 && comparable ? "is-best" : ""}">
                <td class="comp-det-pais">
                  <span class="comp-det-pais-in">
                    ${flagImg(meta.id, "comp-det-flag")}
                    <span>${escapeHtml(meta.nombre)}</span>
                    ${i === 0 && comparable ? `<span class="comp-det-tag">Más barato</span>` : ""}
                  </span>
                </td>
                <td class="comp-det-prod">${escapeHtml(cel.ejemplo || "—")}</td>
                <td class="comp-det-farm">${escapeHtml(cel.tipo || "—")}</td>
                <td class="comp-det-num">${cel.min_usd_unidad != null && cel.cantidad > 1 ? money(cel.min_usd_unidad) : `<span class="empty">—</span>`}</td>
                <td class="comp-det-num comp-det-precio">
                  ${money(cel.min_usd)}
                  ${cel.min_dop != null ? `<span class="comp-det-dop">${dop.format(cel.min_dop)}</span>` : ""}
                </td>
                <td class="td-actions">
                  ${cel.fuente
                    ? `<a class="icon-action" href="${escapeHtml(cel.fuente)}" target="_blank" rel="noreferrer" data-tooltip="Ver fuente" aria-label="Ver fuente">↗</a>`
                    : `<span class="icon-action is-disabled" data-tooltip="Sin fuente" aria-hidden="true">↗</span>`}
                </td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>`
    : `<p class="muted comp-det-vacio">Todavía no hay precios comparables para este principio activo.</p>`;
  return `
    <div class="comp-det-head">
      <div class="comp-det-titulo">
        <h3>${escapeHtml(r.medicamento)}</h3>
        <p class="muted">${escapeHtml(r.presentacion_comparada || "Sin presentación comparable")}</p>
      </div>
      <div class="comp-det-acciones">
        <button type="button" class="comp-det-btn" data-open="${r.n}">Ver ficha completa</button>
        <button type="button" class="comp-det-btn" data-comp-cerrar aria-label="Cerrar detalle">Cerrar</button>
      </div>
    </div>
    ${cuerpo}
    ${sinDato.length
      ? `<p class="muted comp-det-sin">Sin la misma presentación en: ${sinDato.map((p) => escapeHtml(p.nombre)).join(", ")}.</p>`
      : ""}`;
}

/**
 * Inserta el detalle como fila completa del grid, después de la última tarjeta de
 * la misma fila visual. Se mide con offsetTop porque el número de columnas cambia
 * con el ancho de pantalla.
 */
function pintarCompDetalle() {
  const grid = $("compGrid");
  if (!grid) return;
  grid.querySelector(".comp-detalle")?.remove();
  grid.querySelector(".comp-link")?.remove();
  if (state.compAbierto == null) return;
  const cards = [...grid.querySelectorAll(".comp-card")];
  const activa = cards.find((c) => Number(c.dataset.compCard) === Number(state.compAbierto));
  if (!activa) return;
  const row = COMP_PAGE_ROWS.find((r) => Number(r.n) === Number(state.compAbierto));
  if (!row) return;
  const prog = compProgramaClase(row.programa);
  const fila = cards.filter((c) => c.offsetTop === activa.offsetTop);
  const panel = document.createElement("section");
  // Hereda el color del programa para que se lea como continuación de su tarjeta.
  panel.className = `comp-detalle ${prog}`;
  panel.innerHTML = htmlCompDetalle(row);
  (fila[fila.length - 1] || activa).after(panel);

  // Línea que baja de la tarjeta al panel. Va suelta en el grid porque tanto la
  // tarjeta como el panel recortan su contenido con overflow hidden.
  const link = document.createElement("span");
  link.className = `comp-link ${prog}`;
  const desde = activa.offsetTop + activa.offsetHeight;
  link.style.left = `${activa.offsetLeft + activa.offsetWidth / 2}px`;
  link.style.top = `${desde}px`;
  link.style.height = `${Math.max(panel.offsetTop - desde, 0)}px`;
  grid.appendChild(link);
}

/** El panel se ubica midiendo la fila visual, que cambia con el número de columnas. */
function bindCompResize() {
  if (bindCompResize.listo) return;
  bindCompResize.listo = true;
  let t = null;
  window.addEventListener("resize", () => {
    if (state.compAbierto == null || !$("compGrid")) return;
    window.clearTimeout(t);
    t = window.setTimeout(pintarCompDetalle, 120);
  }, { passive: true });
}

function toggleCompCard(n) {
  const num = Number(n);
  state.compAbierto = Number(state.compAbierto) === num ? null : num;
  document.querySelectorAll("#compGrid .comp-card").forEach((c) => {
    const on = Number(c.dataset.compCard) === Number(state.compAbierto);
    c.classList.toggle("is-open", on);
    c.setAttribute("aria-expanded", on ? "true" : "false");
    const cta = c.querySelector(".comp-card-cta");
    if (cta) cta.textContent = on ? "Ocultar precios" : "Ver precios por país";
  });
  pintarCompDetalle();
  if (state.compAbierto != null) {
    $("compGrid")?.querySelector(".comp-detalle")
      ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

function renderComparativo() {
  // El comparativo vive como pestaña de Análisis.
  state.tendVista = "comparativo";
  if (state.view !== "tendencias") {
    state.view = "tendencias";
    syncRoute("tendencias");
  }
  renderTendencias();
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
                <td class="med sticky-l">${escapeHtml(r.medicamento)}<div class="muted">${r.calidad === "revisar" ? `<span class="badge revisar">revisar</span>` : ""}</div></td>
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

function htmlCronCorridaResumen(cron) {
  if (!cron) {
    return `
      <div class="cron-log-panel">
        <h3>Cron diario</h3>
        <p class="muted">Aún no hay corridas registradas. La próxima madrugada quedará el detalle aquí.</p>
      </div>`;
  }
  const pasos = Array.isArray(cron.pasos) ? cron.pasos : [];
  const bad = pasos.filter((p) => ["error", "cache", "warn", "skip"].includes(String(p.estado || "")));
  const okN = Number(cron.total_ok || 0);
  const cacheN = Number(cron.total_cache || 0);
  const warnN = Number(cron.total_warn || 0);
  const errN = Number(cron.total_error || 0);
  const skipN = Number(cron.total_skip || 0);
  const inicio = cron.inicio ? fmtFechaHora(cron.inicio) : "—";
  const fin = cron.fin ? fmtFechaHora(cron.fin) : "en curso";
  const rows = (bad.length ? bad : pasos.slice(0, 12)).map((p) => {
    const est = String(p.estado || "");
    const pill =
      est === "ok" ? "is-done" :
      est === "error" ? "is-error" :
      est === "cache" || est === "warn" ? "is-queued" :
      "is-running";
    const label =
      est === "ok" ? "OK" :
      est === "cache" ? "Caché/bloqueo" :
      est === "warn" ? "Sin filas" :
      est === "skip" ? "Omitido" :
      est === "error" ? "Error" : est;
    const cuando = p.fin || p.inicio || "";
    return `
      <tr>
        <td>${escapeHtml(p.nombre || p.fuente_id || "—")}</td>
        <td><span class="job-pill ${pill}">${escapeHtml(label)}</span></td>
        <td class="muted">${escapeHtml(p.mensaje || "—")}</td>
        <td class="muted">${p.filas_merge != null ? Number(p.filas_merge) : "—"}</td>
        <td class="muted">${cuando ? escapeHtml(fmtFechaHora(cuando)) : "—"}</td>
      </tr>`;
  }).join("");
  return `
    <div class="cron-log-panel">
      <div class="cron-log-head">
        <div>
          <h3>Último cron diario <span class="muted">#${escapeHtml(String(cron.id || ""))}</span></h3>
          <p class="muted">${escapeHtml(inicio)} → ${escapeHtml(fin)} · estado <strong>${escapeHtml(String(cron.estado || ""))}</strong></p>
        </div>
        <div class="cron-log-kpis">
          <span class="cron-kpi is-ok">${okN} ok</span>
          <span class="cron-kpi is-cache">${cacheN} caché</span>
          <span class="cron-kpi is-warn">${warnN} warn</span>
          <span class="cron-kpi is-err">${errN} error</span>
          ${skipN ? `<span class="cron-kpi">${skipN} skip</span>` : ""}
        </div>
      </div>
      <p class="muted cron-log-hint">${
        bad.length
          ? `Detalle de ${bad.length} fuente(s) con incidencias (caché, sin filas, error u omitidas):`
          : "Todas las fuentes del cron cerraron OK. Muestra de pasos:"
      }</p>
      <div class="table-wrap cron-log-table-wrap">
        <table class="data data-static cron-log-table">
          <thead>
            <tr>
              <th>Fuente</th>
              <th>Estado</th>
              <th>Detalle</th>
              <th>MERGE</th>
              <th>Hora</th>
            </tr>
          </thead>
          <tbody>${rows || `<tr><td colspan="5" class="muted">Sin pasos.</td></tr>`}</tbody>
        </table>
      </div>
    </div>`;
}

function fmtFechaHora(v) {
  const s = String(v || "").trim();
  if (!s) return "—";
  // "2026-09-14 06:15:00" o ISO
  const m = s.match(/^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})/);
  if (m) return `${fmtFecha(m[1])} ${m[2]}`;
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return fmtFecha(s);
  return s;
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
let CRON_ULTIMA = null;

async function cargarEstadosJobs() {
  try {
    const r = await fetch("/api/fuentes-jobs", { cache: "no-store" });
    const data = await r.json();
    if (!data.ok) return null;
    JOBS_ESTADOS = data.estados || {};
    CRON_ULTIMA = data.cron || null;
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

function tendPrincipioLabel(m) {
  const p = String(m?.medicamento_lista || "").trim();
  if (p) return p;
  const n = Number(m?.n_lista || 0);
  return n ? `Principio #${n}` : "Principio activo";
}

function tendMedLabel(m) {
  return m.producto_label
    || [m.nombre_comercial, m.concentracion, m.presentacion].filter(Boolean).join(" · ")
    || tendPrincipioLabel(m);
}

function tendMedHaystack(m) {
  return [
    tendPrincipioLabel(m),
    m.nombre_comercial,
    m.concentracion,
    m.presentacion,
    m.producto_label,
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
  return ordenarPaisIds(idSet).map((id) => {
    const fromData = (D.paises || []).find((p) => p.id === id);
    return paisUi(fromData || { id, nombre: PAIS_UI[id]?.full || id });
  });
}

function tendFiltrarMedicamentos(meds, q) {
  const tokens = tendSearchTokens(q);
  if (!tokens.length) {
    return [...meds].sort((a, b) => {
      const dp = Number(b.paises || 0) - Number(a.paises || 0);
      if (dp) return dp;
      const df = Number(b.farmacias || 0) - Number(a.farmacias || 0);
      if (df) return df;
      return String(tendMedLabel(a)).localeCompare(String(tendMedLabel(b)), "es");
    });
  }
  const ranked = [];
  for (const m of meds) {
    const sc = tendScoreMedicamento(m, tokens);
    if (sc < 0) continue;
    ranked.push({ m, sc });
  }
  ranked.sort((a, b) => b.sc - a.sc || String(tendMedLabel(a.m)).localeCompare(String(tendMedLabel(b.m)), "es"));
  return ranked.map((x) => x.m);
}

function tendSearchTokens(q) {
  return String(q || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .split(/[^a-z0-9]+/i)
    .map((t) => t.trim())
    .filter((t) => t.length >= 2);
}

function tendNormTxt(s) {
  return String(s || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

/** Ranking: nombre de producto > principio > resto. */
function tendScoreMedicamento(m, tokens) {
  if (!tokens.length) return 0;
  const producto = tendNormTxt(tendNormProductoLabel(m));
  const principio = tendNormTxt(tendPrincipioLabel(m));
  const hay = tendNormTxt(tendMedHaystack(m));
  let score = 0;
  for (const t of tokens) {
    if (!hay.includes(t) && !producto.includes(t) && !principio.includes(t)) return -1;
    if (producto.startsWith(t) || producto.split(/\s+/).some((w) => w.startsWith(t))) score += 150;
    else if (producto.includes(t)) score += 110;
    if (principio.startsWith(t) || principio.split(/\s+/).some((w) => w.startsWith(t))) score += 70;
    else if (principio.includes(t)) score += 40;
    score += 5;
  }
  score += Math.min(30, Number(m.paises || 0) * 6);
  score += Math.min(20, Number(m.farmacias || 0) * 4);
  score += Math.min(10, Number(m.fechas || 0));
  return score;
}

const TEND_MIN_FECHAS = 4;

function tendMedicamentosVisibles() {
  let meds = Array.isArray(TEND_CATALOG.medicamentos) ? [...TEND_CATALOG.medicamentos] : [];
  meds = meds.filter((m) => Number(m.fechas || 0) >= TEND_MIN_FECHAS);
  const paisId = state.tendPaisFiltro || "todos";
  if (paisId && paisId !== "todos") {
    meds = meds.filter((m) => tendMedEnPais(m, paisId));
  }
  return tendFiltrarMedicamentos(meds, state.tendSearchQ);
}

function tendPickerMeta(m) {
  const bits = [];
  if (m.fechas) bits.push(`${m.fechas} fecha${Number(m.fechas) === 1 ? "" : "s"}`);
  if (m.paises) bits.push(`${m.paises} país${Number(m.paises) === 1 ? "" : "es"}`);
  if (m.farmacias) bits.push(`${m.farmacias} farmacia${Number(m.farmacias) === 1 ? "" : "s"}`);
  const cover = Number(m.paises || 0) >= 2 || Number(m.farmacias || 0) >= 2;
  return { text: bits.join(" · "), cover };
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
  const q = String(state.tendSearchQ || "").trim();
  if (count) {
    count.textContent = opts.length
      ? `${opts.length} resultado${opts.length === 1 ? "" : "s"}${q ? ` para “${q}”` : ""}`
      : "Sin coincidencias";
  }
  list.innerHTML = opts.length
    ? opts.slice(0, 80).map((m) => {
        const val = tendOptionValue(m);
        const label = tendMedLabel(m);
        const sub = m.medicamento_lista && normRegKey(m.medicamento_lista) !== normRegKey(label)
          ? m.medicamento_lista
          : "";
        const meta = tendPickerMeta(m);
        return `
          <button type="button" class="tend-picker-item${val === selectedVal ? " is-active" : ""}${meta.cover ? " is-cover" : ""}"
            data-tend-pick="${escapeHtml(val)}" role="option" aria-selected="${val === selectedVal}">
            <span class="tend-picker-item-label">${escapeHtml(label)}</span>
            ${sub ? `<span class="tend-picker-item-sub">Principio: ${escapeHtml(sub)}</span>` : ""}
            <span class="tend-picker-item-meta">${escapeHtml(meta.text)}${meta.cover ? "" : " · poca cobertura para comparar"}</span>
          </button>`;
      }).join("") + (opts.length > 80 ? `<p class="muted tend-picker-more">+${opts.length - 80} más; afina con principio, marca o concentración</p>` : "")
    : `<p class="muted tend-picker-empty">Ningún medicamento coincide. Prueba el principio activo (ej. letrozol) o la marca.</p>`;
  list.hidden = !state.tendPickerOpen;
}

function abrirTendPicker() {
  state.tendPickerOpen = true;
  renderTendPickerList();
}

function cerrarTendPicker() {
  cerrarTendMedPicker({ restoreLabel: true });
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

function tendVistaTabsHtml() {
  // Explorador de precios: oculto (código e htmlTendExplorador se conservan).
  const tabs = [
    // ["explorador", "Explorador de precios", "Comparar países y fuentes en una fecha"],
    ["serie", "Serie por medicamento", "Evolución del precio en el tiempo"],
    ["graficos", "Tema terapéutico", "Conveniencia por tema terapéutico"],
    ["comparativo", "Comparativo", "Precio más bajo por país y principio activo"],
  ];
  if (state.tendVista === "explorador") state.tendVista = "serie";
  return `
    <div class="tend-vista-tabs" role="tablist" aria-label="Vistas de análisis">
      ${tabs.map(([id, label, hint]) => `
        <button type="button" role="tab" class="tend-vista-tab${state.tendVista === id ? " is-active" : ""}"
          data-tend-vista="${id}" aria-selected="${state.tendVista === id}" title="${escapeHtml(hint)}">
          ${escapeHtml(label)}
        </button>`).join("")}
    </div>`;
}

function htmlTendVistaBody() {
  if (state.tendVista === "serie") return htmlTendSerie();
  if (state.tendVista === "graficos") return htmlTendGraficos();
  if (state.tendVista === "comparativo") return htmlTendComparativo();
  // Explorador oculto: no se renderiza desde las pestañas.
  if (state.tendVista === "explorador") return htmlTendExplorador();
  return htmlTendSerie();
}

function tendTabShellHtml(kind, innerHtml) {
  const labels = {
    serie: "Cargando serie por medicamento…",
    graficos: "Cargando tema terapéutico…",
    comparativo: "Cargando comparativo…",
    explorador: "Cargando explorador…",
  };
  const title = labels[kind] || "Cargando…";
  return `
    <div class="tend-tab-shell is-loading" data-tend-tab="${escapeHtml(kind)}" aria-busy="true">
      <div class="tend-tab-loader" role="status" aria-live="polite">
        <div class="tend-tab-spinner" aria-hidden="true"></div>
        <p class="tend-tab-loader-title">${escapeHtml(title)}</p>
        <p class="tend-tab-loader-sub">Los controles se habilitan cuando termine la carga.</p>
      </div>
      <div class="tend-tab-content" inert>
        ${innerHtml}
      </div>
    </div>`;
}

function setTendTabLoading(loading, opts = {}) {
  const shell = document.querySelector(".tend-tab-shell");
  const card = document.querySelector(".tend-card");
  if (card) card.classList.toggle("is-tab-loading", !!loading);
  if (shell) {
    const content = shell.querySelector(".tend-tab-content");
    const titleEl = shell.querySelector(".tend-tab-loader-title");
    if (opts.message && titleEl) titleEl.textContent = opts.message;
    shell.classList.toggle("is-loading", !!loading);
    shell.setAttribute("aria-busy", loading ? "true" : "false");
    if (content) {
      if (loading) content.setAttribute("inert", "");
      else content.removeAttribute("inert");
    }
  }
  // Mientras carga, no permitir cambiar de tab (evita estados a medias).
  document.querySelectorAll(".tend-vista-tab").forEach((btn) => {
    btn.disabled = !!loading;
    btn.setAttribute("aria-disabled", loading ? "true" : "false");
  });
}

function stashTendKeepHost() {
  const stage = $("stage");
  const live = stage?.querySelector("#tendKeepHost");
  if (live) {
    TEND_KEEP.host = live;
    live.remove();
  }
}

function ensureTendKeepHost() {
  const stage = $("stage");
  if (!stage) return null;
  let host = TEND_KEEP.host;
  if (!host) {
    host = document.createElement("div");
    host.id = "tendKeepHost";
    host.className = "tend-keep-host";
    TEND_KEEP.host = host;
  }
  if (host.parentElement !== stage) {
    stage.replaceChildren(host);
  }
  return host;
}

function syncTendTabsActive(root) {
  if (!root) return;
  root.querySelectorAll("[data-tend-vista]").forEach((btn) => {
    const id = btn.getAttribute("data-tend-vista");
    const on = id === state.tendVista;
    btn.classList.toggle("is-active", on);
    btn.setAttribute("aria-selected", on ? "true" : "false");
  });
}

function tendSerieCacheKey(n, productoKey) {
  return `${Number(n)}|${String(productoKey || "")}`;
}

function createTendPanel(vista) {
  const panel = document.createElement("div");
  panel.className = "tend-keep-panel";
  panel.dataset.tendPanel = vista;
  const esComp = vista === "comparativo";
  panel.innerHTML = `
    <article class="card tend-card tend-card--split${esComp ? " card--flow" : " is-tab-loading"}">
      ${htmlTendVistaBody()}
    </article>`;
  return panel;
}

function refreshTendComparativoPanel(panel) {
  if (!panel) return;
  panel.innerHTML = `
    <article class="card tend-card tend-card--split card--flow">
      ${htmlTendComparativo()}
    </article>`;
}

function activateTendPanel(vista) {
  const host = ensureTendKeepHost();
  if (!host) return null;
  for (const [id, el] of TEND_KEEP.panels) {
    if (id !== vista && el.parentElement === host) el.remove();
  }
  let panel = TEND_KEEP.panels.get(vista);
  const isNew = !panel;
  if (isNew) {
    panel = createTendPanel(vista);
    TEND_KEEP.panels.set(vista, panel);
  } else if (vista === "comparativo") {
    // Comparativo es sync y depende de filtros: regenerar contenido.
    refreshTendComparativoPanel(panel);
  }
  if (panel.parentElement !== host) host.appendChild(panel);
  syncTendTabsActive(panel);
  return { panel, isNew };
}

function restoreTendSerieUi() {
  syncTendTabsActive(TEND_KEEP.panels.get("serie"));
  renderTendCascadeSelects();
  if (!tendCascadeCompleto()) {
    if (!TEND_DATA) tendVaciarResultadosSerie();
    return;
  }
  const same =
    TEND_DATA &&
    Number(TEND_DATA.n_lista) === Number(state.tendenciaN) &&
    String(TEND_DATA.producto_key || "") === String(state.tendenciaProductoKey || "");
  if (same) return; // panel + gráfico ya montados
  pintarTendenciaMedicamento(state.tendenciaN, state.tendenciaProductoKey, { resetBadges: false });
}

function renderTendencias() {
  if (state.tendVista === "explorador") state.tendVista = "serie";
  const vista = state.tendVista;
  const { panel, isNew } = activateTendPanel(vista) || {};
  if (!panel) return;

  if (vista === "comparativo") {
    TEND_KEEP.loaded.comparativo = true;
    setTendTabLoading(false);
    bindCompResize();
    pintarCompDetalle();
    syncFlowSticky();
    return;
  }

  if (vista === "serie" && TEND_KEEP.loaded.serie && !isNew) {
    setTendTabLoading(false);
    restoreTendSerieUi();
    return;
  }

  if (vista === "graficos" && TEND_KEEP.loaded.graficos && TEND_KEEP.grafMounted && !isNew) {
    setTendTabLoading(false);
    syncTendTabsActive(panel);
    return;
  }

  setTendTabLoading(true);
  if (vista === "serie") cargarTendenciasUI();
  else if (vista === "graficos") iniciarGraficos();
  else iniciarExplorador();
}

function htmlTendComparativo() {
  const all = filtrarComparativo();
  const pg = paginate(all, state.page, state.size);
  state.page = pg.page;
  COMP_PAGE_ROWS = pg.rows;
  const paises = paisesUi();
  const paisSel = paises.find((p) => p.id === state.paisFiltro) || null;
  const orden = `${state.sort}:${state.dir}`;
  const extra = `
    <label class="filter-field">
      <span>País</span>
      <select class="selectish" id="filtroPais" title="País con dato">
        <option value="todos" ${state.paisFiltro === "todos" ? "selected" : ""}>Cualquier país</option>
        ${paises.map((p) => `
          <option value="${p.id}" ${state.paisFiltro === p.id ? "selected" : ""}>${p.flag} ${escapeHtml(p.nombre)}</option>
        `).join("")}
      </select>
    </label>
    <div class="filter-field">
      <span>Comparación</span>
      <label class="comp-check${paisSel ? "" : " is-disabled"}"
        title="${paisSel ? `Deja solo los principios donde ${escapeHtml(paisSel.nombre)} tiene el precio más bajo` : "Elige primero un país"}">
        <input type="checkbox" id="compSoloGana" ${state.compSoloGana ? "checked" : ""} ${paisSel ? "" : "disabled"} />
        <span>Solo donde ${paisSel ? escapeHtml(paisSel.nombre) : "el país"} es el más barato</span>
      </label>
    </div>
    <label class="filter-field">
      <span>Ordenar por</span>
      <select class="selectish" id="compOrden" title="Ordenar tarjetas">
        <option value="programa:1" ${orden === "programa:1" ? "selected" : ""}>Programa</option>
        <option value="medicamento:1" ${orden === "medicamento:1" ? "selected" : ""}>Medicamento (A–Z)</option>
        <option value="medicamento:-1" ${orden === "medicamento:-1" ? "selected" : ""}>Medicamento (Z–A)</option>
        <option value="min_usd:1" ${orden === "min_usd:1" ? "selected" : ""}>Precio más bajo</option>
        <option value="min_usd:-1" ${orden === "min_usd:-1" ? "selected" : ""}>Precio más alto</option>
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
  return tendTabShellHtml(
    "comparativo",
    `
    <div class="tend-controls-card">
      <div class="card-head tend-card-head--tabs">${tendVistaTabsHtml()}</div>
      <div class="comp-sticky-stack">
        ${panelFiltros({
          buscaId: "q",
          buscaVal: state.q,
          placeholder: "Buscar medicamento, concentración o país…",
          extra,
          sinCampos: true,
        })}
      </div>
    </div>
    <div class="tend-section-card tend-comp-body">
      <div class="comp-grid" id="compGrid">
        ${pg.rows.length
          ? pg.rows.map((r) => htmlCompCard(r, paises)).join("")
          : `<p class="muted comp-grid-vacio">Ningún principio activo coincide con los filtros.</p>`}
      </div>
      ${pager("c", pg.page, pg.pages, pg.total, pg.start, state.size)}
    </div>`,
  );
}

function htmlTendGraficos() {
  return tendTabShellHtml(
    "graficos",
    `
    <div class="tend-controls-card">
      <div class="card-head tend-card-head--tabs">${tendVistaTabsHtml()}</div>
      <div id="grafControlsMount" class="graf-controls-mount"></div>
    </div>
    <div id="grafReactRoot" class="graf-react-host"></div>`,
  );
}

let _grafRootEl = null;

async function iniciarGraficos() {
  const el = $("grafReactRoot");
  if (!el) {
    setTendTabLoading(false);
    return;
  }
  if (TEND_KEEP.grafMounted) {
    setTendTabLoading(false);
    return;
  }
  // Evita remount si el boot ya empezó (p. ej. cambiaste de tab a mitad de carga).
  if (el.dataset.tendGrafInit === "1") {
    setTendTabLoading(true, { message: "Cargando tema terapéutico…" });
    return;
  }
  el.dataset.tendGrafInit = "1";
  _grafRootEl = el;
  setTendTabLoading(true, { message: "Cargando tema terapéutico…" });
  try {
    const mod = await import(`/graficos-react.js?v=37`);
    mod.mountGraficos(el, {
      onReady: () => {
        TEND_KEEP.grafMounted = true;
        TEND_KEEP.loaded.graficos = true;
        setTendTabLoading(false);
      },
      onFilters: ({ fecha, pais_a, pais_b }) => {
        if (fecha) state.grafFecha = fecha;
        if (pais_a) state.grafPaisA = pais_a;
        if (pais_b) state.grafPaisB = pais_b;
      },
    });
  } catch (err) {
    el.dataset.tendGrafInit = "";
    setTendTabLoading(false);
    el.innerHTML = `<p class="muted graf-empty">No se pudo cargar React/Recharts: ${escapeHtml(String(err.message || err))}</p>`;
  }
}

function htmlTendSerie() {
  const periodo = state.tendPeriodo || "diario";
  const paisFiltro = state.tendPaisFiltro || "todos";
  const optsPeriodo = [
    ["diario", "Diaria"],
    ["mensual", "Mensual"],
    ["quincenal", "Quincenal"],
    ["trimestral", "Trimestral"],
  ];
  return tendTabShellHtml(
    "serie",
    `
    <div class="tend-controls-card">
      <div class="card-head tend-card-head--tabs">
        ${tendVistaTabsHtml()}
      </div>
      <div class="tend-cascade-fields tend-cascade-fields--serie">
        <label class="filter-field tend-field-pais${paisFiltro === "todos" ? " is-awaiting-pick" : ""}" data-cascade-field="pais">
          <span>1. País</span>
          <select class="selectish${paisFiltro === "todos" ? " is-awaiting-pick" : ""}" id="tendPaisSelect" aria-label="Filtrar por país">
            <option value="todos"${paisFiltro === "todos" ? " selected" : ""}>Selecciona un país…</option>
          </select>
        </label>
        <label class="filter-field tend-field-med tend-picker-wrap" data-cascade-field="med">
          <span>2. Nombre de producto</span>
          <input type="search" class="search selectish tend-med-search" id="tendMedSearch"
            value="" placeholder="Primero elige un país…" autocomplete="off"
            aria-label="Buscar nombre de producto" aria-autocomplete="list"
            aria-controls="tendMedList" aria-expanded="false" ${paisFiltro === "todos" ? "disabled" : ""} />
          <div class="tend-picker-list tend-med-list" id="tendMedList" role="listbox" hidden></div>
        </label>
        <label class="filter-field" data-cascade-field="periodo">
          <span>3. Tendencia</span>
          <select class="selectish" id="tendPeriodo" aria-label="Periodicidad de la tendencia" disabled>
            ${optsPeriodo.map(([v, lab]) => `<option value="${v}"${periodo === v ? " selected" : ""}>${lab}</option>`).join("")}
          </select>
        </label>
      </div>
    </div>
    <div class="tend-section-card tend-chart-panel">
      <div class="tend-serie-chart-wrap" id="tendSerieChart"></div>
    </div>
    <div class="tend-section-card tend-table-block">
      <h3 class="tend-table-title">Precios por fecha (USD)</h3>
      <div id="tendTable" class="tend-table"></div>
    </div>`,
  );
}

let EXP_DATA = null;
let EXP_TIMER = null;
let EXP_SEQ = 0;

const EXP_ORDENES = [
  ["precio_asc", "Precio: más barato primero"],
  ["precio_desc", "Precio: más caro primero"],
  ["dispersion", "Mayor brecha entre países"],
  ["paises", "Más países con dato"],
  ["nombre", "Principio activo (A-Z)"],
];

function expOpciones(valores, sel, todosLabel, todosVal) {
  const opts = [`<option value="${todosVal}">${escapeHtml(todosLabel)}</option>`];
  for (const v of valores || []) {
    opts.push(`<option value="${escapeHtml(v)}"${v === sel ? " selected" : ""}>${escapeHtml(v)}</option>`);
  }
  return opts.join("");
}

function htmlTendExplorador() {
  return `
    <div class="exp-filtros">
      <label class="filter-field exp-field-q">
        <span>Buscar</span>
        <input type="search" class="search" id="expQ" value="${escapeHtml(state.expQ)}"
          placeholder="Principio activo, marca, concentración…" autocomplete="off" />
      </label>
      <label class="filter-field">
        <span>País</span>
        <select class="selectish" id="expPais"><option value="todos">Todos los países</option></select>
      </label>
      <label class="filter-field">
        <span>Fuente</span>
        <select class="selectish" id="expFarmacia"><option value="todas">Todas las fuentes</option></select>
      </label>
      <label class="filter-field">
        <span>Programa</span>
        <select class="selectish" id="expPrograma"><option value="todos">Todos</option></select>
      </label>
      <label class="filter-field">
        <span>Fecha</span>
        <select class="selectish" id="expFecha"><option value="">Última disponible</option></select>
      </label>
      <label class="filter-field exp-field-num">
        <span>USD desde</span>
        <input type="number" class="search" id="expPrecioMin" min="0" step="1"
          value="${escapeHtml(state.expPrecioMin)}" placeholder="0" />
      </label>
      <label class="filter-field exp-field-num">
        <span>USD hasta</span>
        <input type="number" class="search" id="expPrecioMax" min="0" step="1"
          value="${escapeHtml(state.expPrecioMax)}" placeholder="Sin tope" />
      </label>
      <label class="filter-field exp-field-num">
        <span>Mín. países</span>
        <select class="selectish" id="expMinPaises">
          ${[0, 2, 3, 4, 5, 6, 8].map((v) => `<option value="${v}"${Number(state.expMinPaises) === v ? " selected" : ""}>${v ? `${v}+` : "Sin mínimo"}</option>`).join("")}
        </select>
      </label>
      <label class="filter-field">
        <span>Tipo de precio</span>
        <select class="selectish" id="expModoPrecio" title="Por defecto se ocultan los PVP al detalle / por unidad (***DET)">
          <option value="paquete"${state.expModoPrecio === "paquete" ? " selected" : ""}>Empaque (sin detalle/unidad)</option>
          <option value="unidad"${state.expModoPrecio === "unidad" ? " selected" : ""}>Solo precio por unidad</option>
          <option value="todos"${state.expModoPrecio === "todos" ? " selected" : ""}>Todos</option>
        </select>
      </label>
      <label class="filter-field exp-field-orden">
        <span>Ordenar por</span>
        <select class="selectish" id="expOrden">
          ${EXP_ORDENES.map(([v, l]) => `<option value="${v}"${state.expOrden === v ? " selected" : ""}>${escapeHtml(l)}</option>`).join("")}
        </select>
      </label>
      <div class="exp-checks">
        <label class="comp-check" title="Deja una fila por principio activo: el país donde está más barato">
          <input type="checkbox" id="expSoloMin" ${state.expSoloMin ? "checked" : ""} />
          <span>Solo el país más barato</span>
        </label>
        <label class="comp-check" title="Muestra cada presentación por separado en vez de la más barata de cada país">
          <input type="checkbox" id="expTodas" ${state.expTodas ? "checked" : ""} />
          <span>Todas las presentaciones</span>
        </label>
        <button type="button" class="exp-reset" id="expReset">Limpiar filtros</button>
      </div>
    </div>
    <div class="exp-resumen" id="expResumen"></div>
    <div class="exp-resultado" id="expResultado">
      <p class="muted">Cargando precios…</p>
    </div>`;
}

function iniciarExplorador() {
  EXP_DATA = null;
  cargarExplorador();
}

function expQueryString() {
  const p = new URLSearchParams();
  if (state.expQ.trim()) p.set("q", state.expQ.trim());
  if (state.expPais !== "todos") p.set("pais", state.expPais);
  if (state.expFarmacia !== "todas") p.set("farmacia", state.expFarmacia);
  if (state.expPrograma !== "todos") p.set("programa", state.expPrograma);
  if (state.expFecha) p.set("fecha", state.expFecha);
  if (state.expPrecioMin !== "") p.set("precio_min", state.expPrecioMin);
  if (state.expPrecioMax !== "") p.set("precio_max", state.expPrecioMax);
  if (Number(state.expMinPaises) > 1) p.set("min_paises", String(state.expMinPaises));
  if (state.expSoloMin) p.set("solo_min", "1");
  if (state.expTodas) p.set("todas", "1");
  if (state.expModoPrecio && state.expModoPrecio !== "paquete") p.set("modo_precio", state.expModoPrecio);
  p.set("orden", state.expOrden);
  p.set("limite", String(state.expLimite));
  return p.toString();
}

async function cargarExplorador() {
  const cont = $("expResultado");
  if (!cont) return;
  const seq = ++EXP_SEQ;
  cont.setAttribute("aria-busy", "true");
  try {
    const r = await fetch(`/api/tendencias/buscar?${expQueryString()}`, { cache: "no-store" });
    const d = await r.json();
    // Una respuesta vieja no debe pisar a una búsqueda más reciente.
    if (seq !== EXP_SEQ) return;
    if (!d?.ok) throw new Error(d?.error || "API buscar");
    EXP_DATA = d;
    sincronizarExpFiltros(d);
    pintarExplorador(d);
  } catch (err) {
    if (seq !== EXP_SEQ) return;
    console.error(err);
    cont.innerHTML = `<p class="muted">No se pudo cargar el explorador (${escapeHtml(String(err.message || err))}).</p>`;
    const res = $("expResumen");
    if (res) res.innerHTML = "";
  } finally {
    if (seq === EXP_SEQ) cont.removeAttribute("aria-busy");
  }
}

/** Rellena los selects con las opciones que de verdad existen en la fecha consultada. */
function sincronizarExpFiltros(d) {
  const f = d.facetas || {};
  const pais = $("expPais");
  if (pais) pais.innerHTML = expOpciones(f.paises, state.expPais, "Todos los países", "todos");
  const farm = $("expFarmacia");
  if (farm) farm.innerHTML = expOpciones(f.farmacias, state.expFarmacia, "Todas las fuentes", "todas");
  const prog = $("expPrograma");
  if (prog) prog.innerHTML = expOpciones(f.programas, state.expPrograma, "Todos", "todos");
  const fecha = $("expFecha");
  if (fecha && Array.isArray(d.fechas)) {
    const activa = state.expFecha || d.fecha || "";
    fecha.innerHTML = [`<option value="">Última disponible</option>`]
      .concat([...d.fechas].reverse().map((v) => `<option value="${escapeHtml(v)}"${v === activa && state.expFecha ? " selected" : ""}>${escapeHtml(fmtFecha(v))}</option>`))
      .join("");
  }
}

function expPrecioLocal(row) {
  const p = row.precio;
  if (p == null || Number.isNaN(Number(p))) return "—";
  const n = Number(p);
  const m = String(row.moneda || "").trim().toUpperCase();
  if (m === "USD") return money(n);
  if (m === "DOP") return dop.format(n);
  return `${n.toLocaleString("es", { maximumFractionDigits: 2 })}${m ? ` ${m}` : ""}`;
}

function expBrechaHtml(row) {
  if (row.es_min) return `<span class="exp-tag exp-tag--min">más barato</span>`;
  const pct = row.sobrecosto_pct;
  if (pct == null) return `<span class="muted">—</span>`;
  const clase = pct >= 100 ? "exp-tag--alto" : pct >= 30 ? "exp-tag--medio" : "exp-tag--bajo";
  return `<span class="exp-tag ${clase}">+${pct.toLocaleString("es", { maximumFractionDigits: 0 })}%</span>`;
}

function expPaisCelda(nombre) {
  const id = idPaisPorTexto(nombre);
  const meta = PAIS_UI[id];
  return `<span class="exp-pais">${flagImg(id, "exp-flag")}<span>${escapeHtml(meta?.nombre || nombre || "—")}</span></span>`;
}

function expAccionesHtml(r, conFicha) {
  const n = Number(r.n_lista);
  // La ficha vive en el comparativo; si el principio no está allí, el botón no lleva a ningún lado.
  const enComparativo = !Number.isNaN(n) && conFicha.has(n);
  return `
    <div class="exp-acciones">
      <button type="button" class="exp-accion${enComparativo ? "" : " is-disabled"}"
        ${enComparativo ? `data-exp-ficha="${n}"` : "disabled"}
        title="${enComparativo ? "Abrir la ficha comparativa del principio activo" : "Este principio no está en el comparativo"}">
        Ficha comparativa
      </button>
      <button type="button" class="exp-accion"
        data-exp-serie
        data-exp-n="${n}"
        data-exp-pk="${escapeHtml(String(r.producto_key || ""))}"
        data-exp-pais="${escapeHtml(String(r.pais || ""))}"
        data-exp-label="${escapeHtml(String(r.producto_label || r.nombre_comercial || r.medicamento_lista || ""))}"
        title="Ver la evolución del precio de esta presentación">
        Precios por fecha
      </button>
    </div>`;
}

function pintarExplorador(d) {
  const cont = $("expResultado");
  const resumen = $("expResumen");
  const filas = Array.isArray(d.filas) ? d.filas : [];
  if (resumen) {
    const baratos = filas.filter((r) => r.es_min).length;
    resumen.innerHTML = `
      <span class="exp-resumen-item"><strong>${Number(d.total || 0).toLocaleString("es")}</strong> resultado${d.total === 1 ? "" : "s"}</span>
      <span class="exp-resumen-item">Precios vigentes al <strong>${escapeHtml(fmtFecha(d.fecha))}</strong></span>
      <span class="exp-resumen-item">${
        (d.modo_precio || state.expModoPrecio) === "unidad"
          ? "Solo PVP por unidad / detalle"
          : (d.modo_precio || state.expModoPrecio) === "todos"
            ? "Empaque + precio por unidad"
            : "Empaque (sin detalle/unidad)"
      }</span>
      ${baratos ? `<span class="exp-resumen-item exp-resumen-item--min"><strong>${baratos}</strong> en verde son el precio más bajo de su principio</span>` : ""}
      ${d.truncado ? `<span class="exp-resumen-item exp-resumen-item--warn">Mostrando los primeros ${filas.length}; afina los filtros para ver el resto</span>` : ""}`;
  }
  if (!filas.length) {
    cont.innerHTML = `<p class="muted exp-vacio">Ningún precio cumple estos filtros. Prueba a quitar el país, la fuente o el rango de precio.</p>`;
    return;
  }
  // Una sola vez por pintado: overlayComparativo() reconstruye la lista completa en cada llamada.
  const conFicha = new Set(overlayComparativo().map((x) => Number(x.n)));
  cont.innerHTML = `
    <div class="table-wrap">
      <table class="data data-static exp-table">
        <thead>
          <tr>
            <th class="exp-col-pa">Principio activo</th>
            <th class="exp-col-prod">Producto</th>
            <th class="exp-col-pais">País</th>
            <th class="exp-col-src">Fuente</th>
            <th class="exp-col-loc">PVP local</th>
            <th class="exp-col-usd">PVP (USD)</th>
            <th class="exp-col-gap">vs. más barato</th>
            <th class="exp-col-acc">Acciones</th>
          </tr>
        </thead>
        <tbody>
          ${filas.map((r) => `
            <tr class="${r.es_min ? "is-min" : ""}">
              <td class="exp-col-pa">
                <strong>${escapeHtml(r.medicamento_lista || "—")}</strong>
                ${r.programa ? `<span class="exp-prog ${compProgramaClase(r.programa)}">${escapeHtml(r.programa)}</span>` : ""}
              </td>
              <td class="exp-col-prod">${escapeHtml(r.nombre_comercial || r.producto_label || "—")}
                ${r.es_precio_unidad ? `<span class="exp-tag exp-tag--unidad" title="PVP al detalle / por unidad">por unidad</span>` : ""}
                ${r.concentracion || r.presentacion
                  ? `<em class="exp-pres">${escapeHtml([r.concentracion, r.presentacion].filter(Boolean).join(" · "))}</em>`
                  : ""}
              </td>
              <td class="exp-col-pais">${expPaisCelda(r.pais)}</td>
              <td class="exp-col-src muted">${escapeHtml(r.farmacia || "—")}</td>
              <td class="exp-col-loc">${escapeHtml(expPrecioLocal(r))}</td>
              <td class="exp-col-usd">${money(Number(r.precio_usd || 0))}</td>
              <td class="exp-col-gap">${expBrechaHtml(r)}</td>
              <td class="exp-col-acc">${expAccionesHtml(r, conFicha)}</td>
            </tr>`).join("")}
        </tbody>
      </table>
    </div>`;
}

function programarBusquedaExplorador() {
  clearTimeout(EXP_TIMER);
  EXP_TIMER = setTimeout(cargarExplorador, 300);
}

function abrirSerieDesdeExplorador(btn) {
  const n = Number(btn.getAttribute("data-exp-n"));
  const pk = String(btn.getAttribute("data-exp-pk") || "").trim();
  if (!n || !pk) return;
  state.tendenciaN = n;
  state.tendenciaProductoKey = pk;
  state.tendenciaLabel = String(btn.getAttribute("data-exp-label") || "").trim();
  state.tendenciaPaisNombre = String(btn.getAttribute("data-exp-pais") || "").trim();
  const paisId = idPaisPorTexto(state.tendenciaPaisNombre);
  // El catálogo de la serie recorta a 500 y filtra por país / mín. fechas:
  // si eso oculta el registro clicado, cargarTendenciasUI lo sustituía por el primero.
  state.tendPaisFiltro = paisActivo(paisId) ? paisId : "todos";
  state.tendSearchQ = "";
  state.tendMedQ = "";
  state.tendProductoSel = "";
  state.tendConcSel = "";
  state.tendPresSel = "";
  state.tendExpandFd = null;
  state.tendVista = "serie";
  renderTendencias();
}

function tendNormPresLabel(m) {
  return String(m?.presentacion || "").trim() || "(sin presentación)";
}

function tendNormConcLabel(m) {
  return String(m?.concentracion || "").trim() || "(sin concentración)";
}

function tendNormProductoLabel(m) {
  const nc = String(m?.nombre_comercial || "").trim();
  if (nc) return nc;
  // producto_label suele ser "marca · conc · pres"; tomar solo la marca si se puede.
  const pl = String(m?.producto_label || "").trim();
  if (pl) {
    const first = pl.split("·")[0].trim();
    if (first) return first;
  }
  return "(sin nombre de producto)";
}

function tendProductoOptionValue(g) {
  return `${g.n_lista}::${encodeURIComponent(g.label)}`;
}

function parseTendProductoOptionValue(raw) {
  const s = String(raw || "");
  const i = s.indexOf("::");
  if (i < 0) return { n: null, producto: "" };
  return {
    n: Number(s.slice(0, i)) || null,
    producto: decodeURIComponent(s.slice(i + 2)),
  };
}

function syncCascadeFromProductoKey() {
  if (!state.tendenciaN || !state.tendenciaProductoKey) return;
  const rows = (TEND_CATALOG.medicamentos || []).filter((m) => Number(m.n_lista) === Number(state.tendenciaN));
  const m = rows.find((r) => String(r.producto_key) === String(state.tendenciaProductoKey));
  if (!m) return;
  state.tendProductoSel = String(m.producto_label || m.nombre_comercial || tendNormProductoLabel(m) || "").trim();
  state.tendPresSel = tendNormPresLabel(m);
  state.tendConcSel = tendNormConcLabel(m);
}

function tendCascadeCompleto() {
  return !!(state.tendenciaN && state.tendenciaProductoKey);
}

function tendVaciarResultadosSerie(msg) {
  const table = $("tendTable");
  let texto = msg;
  if (!texto) {
    if (!tendPaisElegido()) texto = "Selecciona un país y luego un medicamento para ver la serie.";
    else texto = "Selecciona un nombre de producto para ver la serie.";
  }
  if (table) table.innerHTML = `<p class="muted">${texto}</p>`;
  montarTendSerieChart($("tendSerieChart"), [], [], {});
  TEND_DATA = null;
}

async function cargarTendenciasUI() {
  const table = $("tendTable");
  const meta = $("tendMeta");
  if (!table) {
    setTendTabLoading(false);
    return;
  }
  setTendTabLoading(true, { message: "Cargando serie por medicamento…" });
  try {
    if (!TEND_KEEP.catalogLoaded || !(TEND_CATALOG.medicamentos || []).length) {
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
      if (!medicamentos.length) {
        const madre = overlayComparativo();
        TEND_CATALOG.medicamentos = madre.map((x) => ({
          n_lista: x.n,
          medicamento_lista: x.medicamento,
          producto_key: "sin_identificar",
          producto_label: x.medicamento,
          concentracion: "",
          presentacion: "",
          fechas: 0,
          paises: 0,
          farmacias: 0,
        }));
      }
      TEND_KEEP.catalogLoaded = true;
    }

    const fechas = TEND_CATALOG.fechas || [];
    const selectedVal = tendSelectedValue();
    const all = tendCatalogFiltradoBase();
    let active = all.find((m) => tendOptionValue(m) === selectedVal);
    // Si la selección previa no cumple el mínimo de fechas, se limpia.
    if (selectedVal && !active) {
      state.tendenciaN = null;
      state.tendenciaProductoKey = null;
      state.tendenciaLabel = "";
      state.tendProductoSel = "";
      state.tendPresSel = "";
      state.tendConcSel = "";
    }
    if (active) syncCascadeFromProductoKey();
    else if (!tendSelectedValue()) {
      if (!state.tendenciaN || !state.tendProductoSel) {
        state.tendProductoSel = "";
        state.tendPresSel = "";
        state.tendConcSel = "";
        state.tendenciaProductoKey = null;
      }
    }

    renderTendCascadeSelects();

    if (meta) {
      const opts = tendProductosSelectOpts();
      let step = "Elige un nombre de producto";
      if (!tendPaisElegido()) step = "Elige un país";
      else if (tendCascadeCompleto()) step = "Serie lista";
      meta.textContent = fechas.length
        ? `${step} · ${fechas.length} fecha${fechas.length === 1 ? "" : "s"} · ${opts.length} producto${opts.length === 1 ? "" : "s"}`
        : "Aún no hay historial. Se creará con el próximo scrape / snapshot.";
    }

    if (tendCascadeCompleto()) {
      await pintarTendenciaMedicamento(state.tendenciaN, state.tendenciaProductoKey);
    } else {
      tendVaciarResultadosSerie();
    }
    TEND_KEEP.loaded.serie = true;
  } catch (err) {
    console.error(err);
    const msg = `No se pudo cargar tendencias (${escapeHtml(String(err.message || err))}).`;
    table.innerHTML = `<p class="muted">${msg}</p>`;
  } finally {
    setTendTabLoading(false);
  }
}

function actualizarTendPaisSelect() {
  const sel = $("tendPaisSelect");
  if (!sel) return;
  const cur = state.tendPaisFiltro || "todos";
  const opts = tendPaisesHistorialOpts();
  sel.innerHTML = `<option value="todos">Selecciona un país…</option>${
    opts.map((p) => `<option value="${escapeHtml(p.id)}"${cur === p.id ? " selected" : ""}>${escapeHtml(p.nombre)}</option>`).join("")
  }`;
  if (cur !== "todos" && !opts.some((p) => p.id === cur)) {
    state.tendPaisFiltro = "todos";
    sel.value = "todos";
  }
  const awaiting = (state.tendPaisFiltro || "todos") === "todos";
  sel.classList.toggle("is-awaiting-pick", awaiting);
  sel.closest(".tend-field-pais")?.classList.toggle("is-awaiting-pick", awaiting);
}

function tendSerieId(s) {
  if (!s) return "";
  if (s.id) return String(s.id);
  if (s.farmacia) return `${s.farmacia}||${s.pais || ""}`;
  return String(s.pais || s.label || "");
}

function tendSerieLabel(s) {
  return s?.label || (s?.farmacia ? `${s.farmacia} · ${s.pais}` : s?.pais) || "—";
}

function tendCatalogFiltradoBase() {
  let meds = Array.isArray(TEND_CATALOG.medicamentos) ? [...TEND_CATALOG.medicamentos] : [];
  meds = meds.filter((m) => Number(m.fechas || 0) >= TEND_MIN_FECHAS);
  const paisId = state.tendPaisFiltro || "todos";
  if (paisId && paisId !== "todos") {
    meds = meds.filter((m) => tendMedEnPais(m, paisId));
  }
  const q = tendNormTxt(state.tendMedQ || "");
  if (q) {
    const tokens = tendSearchTokens(q);
    meds = meds.filter((m) => {
      if (!tokens.length) return tendNormTxt(tendMedHaystack(m)).includes(q);
      return tendScoreMedicamento(m, tokens) >= 0;
    });
  }
  return meds;
}

/** Opciones del select: un ítem por producto_key (ya trae presentación/concentración en el nombre). */
function tendProductosSelectOpts() {
  const map = new Map();
  for (const m of tendCatalogFiltradoBase()) {
    const n = Number(m.n_lista);
    const pk = String(m.producto_key || "").trim();
    if (!n || !pk) continue;
    const label = String(
      m.producto_label
      || m.nombre_comercial
      || tendMedLabel(m)
      || tendNormProductoLabel(m)
      || pk,
    ).trim();
    const prev = map.get(pk);
    const paises = Number(m.paises || 0);
    const farmacias = Number(m.farmacias || 0);
    const fechas = Number(m.fechas || 0);
    if (!prev || paises > prev.paises || fechas > prev.fechas) {
      map.set(pk, {
        n_lista: n,
        producto_key: pk,
        label,
        principio: tendPrincipioLabel(m),
        presentacion: tendNormPresLabel(m),
        concentracion: tendNormConcLabel(m),
        paises,
        farmacias,
        fechas,
      });
    }
  }
  return [...map.values()].sort((a, b) => a.label.localeCompare(b.label, "es"));
}

function tendProductoGroups() {
  const map = new Map();
  for (const m of tendCatalogFiltradoBase()) {
    const n = Number(m.n_lista);
    if (!n) continue;
    const label = tendNormProductoLabel(m);
    const key = `${n}||${tendNormTxt(label)}`;
    const prev = map.get(key);
    const principio = tendPrincipioLabel(m);
    if (!prev) {
      map.set(key, {
        n_lista: n,
        label,
        principio,
        paises: Number(m.paises || 0),
        farmacias: Number(m.farmacias || 0),
        fechas: Number(m.fechas || 0),
        rows: [m],
      });
    } else {
      prev.rows.push(m);
      if ((!prev.principio || prev.principio.startsWith("Principio #")) && principio && !principio.startsWith("Principio #")) {
        prev.principio = principio;
      }
      prev.paises = Math.max(prev.paises, Number(m.paises || 0));
      prev.farmacias = Math.max(prev.farmacias, Number(m.farmacias || 0));
      prev.fechas = Math.max(prev.fechas, Number(m.fechas || 0));
    }
  }
  return [...map.values()].sort((a, b) => {
    const dp = b.paises - a.paises;
    if (dp) return dp;
    return a.label.localeCompare(b.label, "es");
  });
}

/** @deprecated alias: la cascada usa productos, no solo principios. */
function tendMedGroups() {
  return tendProductoGroups();
}

function tendRowsForProducto(nLista, productoNombre) {
  const n = Number(nLista);
  const nom = String(productoNombre || "");
  return tendCatalogFiltradoBase().filter((m) =>
    Number(m.n_lista) === n && tendNormProductoLabel(m) === nom
  );
}

function tendRowsForMed(nLista) {
  if (state.tendProductoSel) return tendRowsForProducto(nLista, state.tendProductoSel);
  const n = Number(nLista);
  return tendCatalogFiltradoBase().filter((m) => Number(m.n_lista) === n);
}

/** Presentaciones del producto elegido (paso 2). */
function tendPresOptions(nLista, productoNombre = state.tendProductoSel) {
  const map = new Map();
  const rows = productoNombre
    ? tendRowsForProducto(nLista, productoNombre)
    : tendCatalogFiltradoBase().filter((m) => Number(m.n_lista) === Number(nLista));
  for (const m of rows) {
    const pres = tendNormPresLabel(m);
    const prev = map.get(pres);
    if (!prev) {
      map.set(pres, {
        presentacion: pres,
        paises: Number(m.paises || 0),
        farmacias: Number(m.farmacias || 0),
        fechas: Number(m.fechas || 0),
        concs: 1,
      });
    } else {
      prev.paises = Math.max(prev.paises, Number(m.paises || 0));
      prev.farmacias = Math.max(prev.farmacias, Number(m.farmacias || 0));
      prev.fechas = Math.max(prev.fechas, Number(m.fechas || 0));
      prev.concs += 1;
    }
  }
  return [...map.values()].sort((a, b) => b.paises - a.paises || a.presentacion.localeCompare(b.presentacion, "es"));
}

/** Concentraciones para producto + presentación (paso 3). */
function tendConcOptions(nLista, presentacion, productoNombre = state.tendProductoSel) {
  const rows = (productoNombre
    ? tendRowsForProducto(nLista, productoNombre)
    : tendCatalogFiltradoBase().filter((m) => Number(m.n_lista) === Number(nLista))
  ).filter((m) => {
    if (!presentacion) return false;
    return tendNormPresLabel(m) === presentacion;
  });
  const map = new Map();
  for (const m of rows) {
    const c = tendNormConcLabel(m);
    const prev = map.get(c);
    if (!prev) {
      map.set(c, {
        concentracion: c,
        producto_key: m.producto_key,
        paises: Number(m.paises || 0),
        farmacias: Number(m.farmacias || 0),
        fechas: Number(m.fechas || 0),
        label: tendMedLabel(m),
      });
    } else {
      prev.paises = Math.max(prev.paises, Number(m.paises || 0));
      prev.farmacias = Math.max(prev.farmacias, Number(m.farmacias || 0));
      prev.fechas = Math.max(prev.fechas, Number(m.fechas || 0));
      if (Number(m.paises || 0) > Number(prev.paises || 0)) prev.producto_key = m.producto_key;
    }
  }
  return [...map.values()].sort((a, b) => b.paises - a.paises || a.concentracion.localeCompare(b.concentracion, "es"));
}

function tendResolveProductoKey(nLista, presentacion, concentracion, productoNombre = state.tendProductoSel) {
  const concs = tendConcOptions(nLista, presentacion, productoNombre);
  const hit = concs.find((c) => c.concentracion === concentracion);
  return hit?.producto_key || null;
}

function tendPaisElegido() {
  const p = state.tendPaisFiltro || "todos";
  return !!(p && p !== "todos");
}

function tendUpdateCascadeSteps() {
  const paisOk = tendPaisElegido();
  const medOk = tendCascadeCompleto();
  document.querySelectorAll("[data-cascade-field]").forEach((el) => {
    const field = el.getAttribute("data-cascade-field");
    let locked = false;
    if (field === "med") locked = !paisOk;
    if (field === "periodo") locked = !medOk;
    el.classList.toggle("is-locked", locked);
  });
  const input = $("tendMedSearch");
  if (input) {
    input.disabled = !paisOk;
    input.placeholder = paisOk
      ? "Buscar producto o marca…"
      : "Primero elige un país…";
    if (!paisOk) input.setAttribute("aria-disabled", "true");
    else input.removeAttribute("aria-disabled");
  }
}

function tendMedOptionLabel(o) {
  if (!o) return "";
  const label = String(o.label || "").trim();
  const principio = String(o.principio || "").trim();
  if (principio && tendNormTxt(principio) !== tendNormTxt(label) && !tendNormTxt(label).includes(tendNormTxt(principio))) {
    return `${label} (${principio})`;
  }
  return label;
}

function tendMedOptsFiltrados() {
  const all = tendProductosSelectOpts();
  const q = String(state.tendMedQ || "").trim();
  if (!q) return all;
  const tokens = tendSearchTokens(q);
  const qn = tendNormTxt(q);
  return all.filter((o) => {
    const hay = tendNormTxt(`${o.label} ${o.principio} ${o.concentracion} ${o.presentacion}`);
    if (!tokens.length) return hay.includes(qn);
    return tokens.every((t) => hay.includes(t));
  });
}

function tendMedSelectedOpt() {
  if (!state.tendenciaN || !state.tendenciaProductoKey) return null;
  return tendProductosSelectOpts().find((o) =>
    Number(o.n_lista) === Number(state.tendenciaN)
    && String(o.producto_key) === String(state.tendenciaProductoKey)
  ) || null;
}

function renderTendMedPickerList() {
  const list = $("tendMedList");
  const input = $("tendMedSearch");
  if (!list) return;
  const opts = tendMedOptsFiltrados();
  const selectedVal = tendSelectedValue();
  const q = String(state.tendMedQ || "").trim();
  const countTxt = opts.length
    ? `${opts.length} resultado${opts.length === 1 ? "" : "s"}${q ? ` para “${q}”` : ""} · mín. ${TEND_MIN_FECHAS} fechas`
    : `Sin coincidencias (mín. ${TEND_MIN_FECHAS} fechas)`;
  list.innerHTML = `
    <p class="muted tend-picker-count-inlist">${escapeHtml(countTxt)}</p>
    ${opts.length
      ? opts.slice(0, 100).map((o) => {
          const val = tendOptionValue(o);
          const label = tendMedOptionLabel(o);
          return `
            <button type="button" class="tend-picker-item${val === selectedVal ? " is-active" : ""}"
              data-tend-med-pick="${escapeHtml(val)}" role="option" aria-selected="${val === selectedVal}">
              <span class="tend-picker-item-label">${escapeHtml(label)}</span>
            </button>`;
        }).join("") + (opts.length > 100
          ? `<p class="muted tend-picker-more">+${opts.length - 100} más; afina la búsqueda</p>`
          : "")
      : `<p class="muted tend-picker-empty">Ningún producto coincide.</p>`}`;
  list.hidden = !state.tendPickerOpen;
  if (input) input.setAttribute("aria-expanded", state.tendPickerOpen ? "true" : "false");
}

function abrirTendMedPicker() {
  if (!tendPaisElegido()) {
    state.tendPickerOpen = false;
    const list = $("tendMedList");
    if (list) {
      list.hidden = false;
      list.innerHTML = `<p class="muted tend-picker-empty">Elige un país arriba para filtrar el catálogo.</p>`;
    }
    return;
  }
  state.tendPickerOpen = true;
  renderTendMedPickerList();
}

function cerrarTendMedPicker({ restoreLabel = true } = {}) {
  state.tendPickerOpen = false;
  const list = $("tendMedList");
  const input = $("tendMedSearch");
  if (list) list.hidden = true;
  if (input) {
    input.setAttribute("aria-expanded", "false");
    if (restoreLabel) {
      const opt = tendMedSelectedOpt();
      state.tendMedQ = "";
      input.value = opt ? tendMedOptionLabel(opt) : "";
      input.placeholder = opt ? "Buscar producto o marca…" : "Buscar producto o marca…";
    }
  }
}

function renderTendCascadeSelects() {
  actualizarTendPaisSelect();
  const selPeriodo = $("tendPeriodo");
  const input = $("tendMedSearch");
  const opt = tendMedSelectedOpt();
  if (input && !state.tendPickerOpen) {
    input.value = opt ? tendMedOptionLabel(opt) : "";
  }
  if (selPeriodo) selPeriodo.disabled = !tendCascadeCompleto();
  tendUpdateCascadeSteps();
  if (state.tendPickerOpen) renderTendMedPickerList();
}

async function aplicarSeleccionCascade({ load = true } = {}) {
  renderTendCascadeSelects();
  if (!load) return;
  if (tendCascadeCompleto()) {
    await pintarTendenciaMedicamento(state.tendenciaN, state.tendenciaProductoKey, { resetBadges: true });
  } else {
    tendVaciarResultadosSerie();
  }
}

function syncTendBadgesFromData(d, { reset = false } = {}) {
  const paises = (d?.paises_disponibles || []).filter((p) => paisActivo(idPaisPorTexto(p)));
  const farms = (d?.farmacias_disponibles || []).filter((f) => paisActivo(idPaisPorTexto(f.pais)));
  if (reset || !Array.isArray(state.tendPaises) || !state.tendPaises.length) {
    state.tendPaises = [...paises];
  } else {
    const set = new Set(paises);
    state.tendPaises = state.tendPaises.filter((p) => set.has(p));
    if (!state.tendPaises.length) state.tendPaises = [...paises];
  }
  const farmIds = farms.map((f) => f.id || `${f.farmacia}||${f.pais}`);
  if (reset || !Array.isArray(state.tendFarmacias) || !state.tendFarmacias.length) {
    state.tendFarmacias = [...farmIds];
  } else {
    const set = new Set(farmIds);
    state.tendFarmacias = state.tendFarmacias.filter((id) => set.has(id));
    if (!state.tendFarmacias.length) state.tendFarmacias = [...farmIds];
  }
}

function renderTendBadgesPanel() {
  // Filtros por país/farmacia desactivados: la serie usa todos los disponibles.
  const panel = $("tendBadgesPanel");
  if (panel) {
    panel.hidden = true;
    panel.innerHTML = "";
  }
}

function tendSeriesFiltradasFarms(series) {
  // Sin toggle de farmacia: incluir series del país activo (o todos).
  const paisId = state.tendPaisFiltro || "todos";
  return (Array.isArray(series) ? series : []).filter((s) => {
    if (!paisActivo(idPaisPorTexto(s.pais))) return false;
    if (paisId && paisId !== "todos" && idPaisPorTexto(s.pais) !== paisId) return false;
    return true;
  });
}

/** Una sola serie: mínimo USD entre todas las farmacias/países. */
function tendSerieGlobalDesdeFarmacias(fechas, farmSeries, label = "Precio mínimo") {
  const puntos = (fechas || []).map((fd) => {
    let best = null;
    let bestV = null;
    let bestFarm = null;
    let bestPais = null;
    for (const s of farmSeries || []) {
      const pt = tendPuntoEnFecha(s, fd);
      const v = tendVal(pt);
      if (v == null) continue;
      if (bestV == null || v < bestV) {
        bestV = v;
        best = pt;
        bestFarm = s.farmacia || pt?.farmacia || null;
        bestPais = s.pais || pt?.pais || null;
      }
    }
    if (!best) {
      return {
        fecha: fd,
        vigente_hasta: fd,
        precio_usd: null,
        precio: null,
        moneda: null,
        farmacia: null,
        pais: null,
        fuente_url: null,
        precio_lista: null,
        precio_oferta: null,
      };
    }
    return {
      fecha: fd,
      vigente_hasta: best.vigente_hasta || fd,
      precio_usd: best.precio_usd ?? bestV,
      precio: best.precio,
      moneda: best.moneda,
      farmacia: bestFarm,
      pais: bestPais,
      fuente_url: best.fuente_url || best.fuente || null,
      nombre_comercial: best.nombre_comercial || null,
      precio_lista: best.precio_lista ?? null,
      precio_oferta: best.precio_oferta ?? null,
    };
  });
  return [{ id: "min-global", label, pais: "", farmacia: null, puntos }];
}

/** Agrega series de farmacia → una serie por país (mínimo USD vigente). */
function tendSeriesPaisDesdeFarmacias(fechas, farmSeries) {
  const byPais = new Map();
  for (const s of farmSeries || []) {
    const pais = s.pais || "—";
    if (!byPais.has(pais)) byPais.set(pais, []);
    byPais.get(pais).push(s);
  }
  const out = [];
  for (const [pais, farms] of [...byPais.entries()].sort((a, b) => a[0].localeCompare(b[0], "es"))) {
    const puntos = (fechas || []).map((fd) => {
      let best = null;
      let bestV = null;
      let bestFarm = null;
      for (const s of farms) {
        const pt = tendPuntoEnFecha(s, fd);
        const v = tendVal(pt);
        if (v == null) continue;
        if (bestV == null || v < bestV) {
          bestV = v;
          best = pt;
          bestFarm = s.farmacia || pt?.farmacia;
        }
      }
      if (!best) return { fecha: fd, vigente_hasta: fd, precio_usd: null, precio: null, moneda: null, farmacia: null };
      return {
        fecha: fd,
        vigente_hasta: best.vigente_hasta || fd,
        precio_usd: best.precio_usd ?? bestV,
        precio: best.precio,
        moneda: best.moneda,
        farmacia: bestFarm,
      };
    });
    out.push({ id: pais, label: pais, pais, farmacia: null, puntos });
  }
  return out;
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

/** Clave de periodo para agregar la serie (mensual / quincenal / trimestral). */
function tendPeriodoKey(fd, modo) {
  const s = String(fd).slice(0, 10);
  const [y, m, d] = s.split("-").map(Number);
  if (!y || !m) return s;
  if (modo === "trimestral") {
    const q = Math.floor((m - 1) / 3) + 1;
    return `${y}-T${q}`;
  }
  if (modo === "quincenal") {
    const half = d <= 15 ? "A" : "B";
    return `${y}-${String(m).padStart(2, "0")}-${half}`;
  }
  return `${y}-${String(m).padStart(2, "0")}`;
}

function tendPeriodoLabel(key, modo) {
  const k = String(key || "");
  if (modo === "trimestral") {
    const m = k.match(/^(\d{4})-T([1-4])$/);
    if (m) return `T${m[2]} ${m[1]}`;
  } else if (modo === "quincenal") {
    const m = k.match(/^(\d{4})-(\d{2})-([AB])$/);
    if (m) {
      const mes = Number(m[2]);
      const rango = m[3] === "A" ? "1–15" : "16–fin";
      return `${rango}/${String(mes).padStart(2, "0")}/${m[1]}`;
    }
  } else if (modo === "mensual") {
    const m = k.match(/^(\d{4})-(\d{2})$/);
    if (m) return `${m[2]}/${m[1]}`;
  }
  return fmtFecha(k);
}

/**
 * Agrega fechas diarias del historial al periodo elegido.
 * - diario: sin agregar (un punto por fecha de scrape; sin promedio).
 * - mensual / quincenal / trimestral: promedio de los precios USD del intervalo.
 */
function tendAgregarSerie(fechas, series, modo) {
  const m = modo || "diario";
  if (m === "diario" || !fechas?.length) {
    const labels = {};
    for (const fd of fechas || []) {
      labels[fd] = fmtFecha(fd);
    }
    return { fechas: fechas || [], series: series || [], labels };
  }
  const buckets = new Map();
  for (const fd of fechas) {
    const key = tendPeriodoKey(fd, m);
    if (!buckets.has(key)) {
      buckets.set(key, { key, label: tendPeriodoLabel(key, m), fds: [] });
    }
    buckets.get(key).fds.push(fd);
  }
  const periodos = [...buckets.values()].sort((a, b) => a.key.localeCompare(b.key));
  const fechasAgg = periodos.map((p) => p.key);
  const labels = Object.fromEntries(periodos.map((p) => [p.key, p.label]));
  const seriesAgg = (series || []).map((s) => {
    const puntos = periodos.map((p) => {
      const usdVals = [];
      const localVals = [];
      let moneda = null;
      let monedaUnica = true;
      for (const fd of p.fds) {
        const pt = tendPuntoEnFecha(s, fd);
        const v = tendVal(pt);
        if (v == null) continue;
        usdVals.push(v);
        if (pt?.precio != null && !Number.isNaN(Number(pt.precio))) {
          localVals.push(Number(pt.precio));
          const mon = String(pt.moneda || "").trim().toUpperCase();
          if (moneda == null) moneda = mon;
          else if (mon !== moneda) monedaUnica = false;
        }
      }
      if (!usdVals.length) {
        return { fecha: p.key, vigente_hasta: p.key, precio_usd: null, precio: null, moneda: null, n_obs: 0 };
      }
      const avgUsd = usdVals.reduce((a, b) => a + b, 0) / usdVals.length;
      const avgLocal = monedaUnica && localVals.length
        ? localVals.reduce((a, b) => a + b, 0) / localVals.length
        : null;
      return {
        fecha: p.key,
        vigente_hasta: p.key,
        precio_usd: avgUsd,
        precio: avgLocal,
        moneda: monedaUnica ? moneda : null,
        farmacia: `n=${usdVals.length}`,
        n_obs: usdVals.length,
      };
    });
    return { ...s, puntos, id: s.id, label: s.label, pais: s.pais, farmacia: s.farmacia };
  });
  return { fechas: fechasAgg, series: seriesAgg, labels };
}

function tendFmtPeriodo(fd, labels) {
  if (labels && labels[fd]) return labels[fd];
  return fmtFecha(fd);
}

function tendGapsHtml(fechas, series, labels) {
  const gaps = [];
  for (const s of series) {
    const missing = fechas.filter((fd) => tendVal(tendPuntoEnFecha(s, fd)) == null);
    const lab = tendSerieLabel(s);
    if (missing.length && missing.length < fechas.length) {
      gaps.push(`<li><strong>${escapeHtml(lab)}</strong> sin dato: ${missing.map((f) => escapeHtml(tendFmtPeriodo(f, labels))).join(", ")}</li>`);
    } else if (missing.length === fechas.length) {
      gaps.push(`<li><strong>${escapeHtml(lab)}</strong> sin puntos en el historial</li>`);
    }
  }
  if (!gaps.length) return "";
  return `<div class="tend-gaps"><p class="tend-gaps-title">Huecos en la serie</p><ul>${gaps.join("")}</ul></div>`;
}

function tendPrecioLocal(pt) {
  if (!pt) return "—";
  const p = pt.precio;
  if (p == null || Number.isNaN(Number(p))) return "—";
  const n = Number(p);
  const m = String(pt.moneda || "").trim().toUpperCase();
  if (m === "USD") return money(n);
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

function tendFuentePreferida(...urls) {
  let best = "";
  let bestS = -1;
  for (const raw of urls) {
    const u = String(raw || "").trim();
    if (!u || !/^https?:\/\//i.test(u)) continue;
    const low = u.toLowerCase();
    let s = 3;
    if (low.includes("farmacias.do")) s = 1;
    else if (low.includes("farmavalue.com")) s = 6;
    else if (low.includes("farmaciacarol") || low.includes("hidalgos") || low.includes("qualipharma")) s = 5;
    if (s > bestS) {
      bestS = s;
      best = u;
    }
  }
  return best;
}

function tendFuentePunto(pt) {
  if (!pt) return "";
  const directa = String(pt.fuente_url || pt.fuente || "").trim();
  const n = Number(state.tendenciaN);
  const pk = String(state.tendenciaProductoKey || "").trim();
  const farm = tendNormTxt(pt.farmacia || "");
  const pais = tendNormTxt(pt.pais || "");

  // Preferir el PDP vivo de la misma farmacia/país (evita farmacias.do vs farmavalue.com).
  let liveUrl = "";
  if (n) {
    const cands = (TABLA || []).filter((f) => {
      if (Number(f.n_lista) !== n) return false;
      if (farm && tendNormTxt(f.farmacia || "") !== farm) return false;
      if (pais && tendNormTxt(f.pais || "") !== pais) return false;
      return !!fuenteUrlVisible(f);
    });
    const exact = pk
      ? cands.find((f) => {
          const fpk = String(f.producto_key || productoKeyFila(f) || "").trim();
          return fpk === pk;
        })
      : null;
    const pick = exact || cands.find((f) => !String(fuenteUrlVisible(f) || "").toLowerCase().includes("farmacias.do")) || cands[0];
    if (pick) liveUrl = fuenteUrlVisible(pick);
  }

  const directaVis = directa
    ? fuenteUrlVisible({
        fuente_url: directa,
        farmacia: pt.farmacia,
        pais: pt.pais,
        id_producto_farmacia: pt.id_producto_farmacia,
        sku: pt.sku,
      })
    : "";
  return tendFuentePreferida(liveUrl, directaVis);
}

function tendTableSortMark(key) {
  if (state.tendTableSort !== key) return `<span class="ord">↕</span>`;
  return `<span class="ord">${state.tendTableDir === 1 ? "↑" : "↓"}</span>`;
}

function tendDescuentoPunto(pt, { permitirLive = false } = {}) {
  if (!pt) return { lista: null, oferta: null, pct: null };
  let lista = pt.precio_lista != null ? Number(pt.precio_lista) : null;
  let oferta = pt.precio_oferta != null ? Number(pt.precio_oferta) : null;
  // Solo enriquecer con live en el punto más reciente: no inventar descuentos históricos.
  if (permitirLive && (lista == null || oferta == null) && LIVE_OK) {
    const n = Number(state.tendenciaN);
    const farm = tendNormTxt(pt.farmacia || "");
    const pais = tendNormTxt(pt.pais || "");
    const hit = (TABLA || []).find((f) => {
      if (n && Number(f.n_lista) !== n) return false;
      if (farm && tendNormTxt(f.farmacia || "") !== farm) return false;
      if (pais && tendNormTxt(f.pais || "") !== pais) return false;
      return f.precio_lista != null || f.precio_oferta != null;
    });
    if (hit) {
      if (lista == null && hit.precio_lista != null) lista = Number(hit.precio_lista);
      if (oferta == null && hit.precio_oferta != null) oferta = Number(hit.precio_oferta);
    }
  }
  if (!(lista > 0)) lista = null;
  if (!(oferta > 0)) oferta = null;
  if (lista != null && oferta != null && oferta < lista * 0.999) {
    const pct = ((1 - oferta / lista) * 100);
    return { lista, oferta, pct };
  }
  return { lista: lista || (pt.precio != null ? Number(pt.precio) : null), oferta: null, pct: null };
}

/** USD de la oferta usando el mismo FX implícito del USD de lista ese día. */
function tendUsdOferta(usdLista, desc) {
  const usd = usdLista != null ? Number(usdLista) : null;
  if (!(usd > 0) || !desc || !(desc.lista > 0) || desc.oferta == null) return null;
  if (!(desc.oferta > 0) || !(desc.oferta < desc.lista * 0.999)) return null;
  return usd * (Number(desc.oferta) / Number(desc.lista));
}

/** Segunda serie del gráfico: USD con descuento (null si ese día no hay oferta). */
function tendSerieUsdDescuentoDesdeGlobal(serieGlobal) {
  const s0 = (serieGlobal || [])[0];
  if (!s0) return [];
  const puntos = (s0.puntos || []).map((pt) => {
    const usd = tendVal(pt);
    const desc = tendDescuentoPunto(pt);
    const usdOferta = tendUsdOferta(usd, desc);
    return {
      fecha: pt.fecha,
      vigente_hasta: pt.vigente_hasta || pt.fecha,
      precio_usd: usdOferta,
      precio: desc.oferta,
      moneda: pt.moneda,
      farmacia: pt.farmacia,
      pais: pt.pais,
      fuente_url: pt.fuente_url || null,
      precio_lista: desc.lista,
      precio_oferta: desc.oferta,
    };
  });
  if (!puntos.some((p) => p.precio_usd != null)) return [];
  return [{ id: "usd-descuento", label: "USD descuento", pais: "", farmacia: null, puntos }];
}

function tendLocalMoney(n, moneda) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  const m = String(moneda || "").trim().toUpperCase();
  const num = Number(n);
  if (m === "USD") return money(num);
  if (m === "DOP") return dop.format(num);
  return `${num.toLocaleString("es", { maximumFractionDigits: 2 })}${m ? ` ${m}` : ""}`;
}

function tendFilasPreciosTable(fechas, serieGlobal, labels) {
  const s0 = (serieGlobal || [])[0];
  const ultimaFd = fechas?.length ? String(fechas[fechas.length - 1]).slice(0, 10) : null;
  return (fechas || []).map((fd, i) => {
    const pt = tendPuntoEnFecha(s0, fd);
    const v = tendVal(pt);
    const prevFd = i > 0 ? fechas[i - 1] : null;
    const prevV = prevFd != null ? tendVal(tendPuntoEnFecha(s0, prevFd)) : null;
    let delta = null;
    if (prevV != null && v != null && prevV > 0) delta = ((v - prevV) / prevV) * 100;
    const esUltima = ultimaFd && String(fd).slice(0, 10) === ultimaFd;
    const desc = tendDescuentoPunto(pt, { permitirLive: !!esUltima });
    const usdOferta = tendUsdOferta(v, desc);
    return {
      fd,
      label: tendFmtPeriodo(fd, labels),
      usd: v,
      usdOferta,
      delta,
      farmacia: pt?.farmacia || "",
      pais: pt?.pais || "",
      moneda: pt?.moneda || "",
      fuente: tendFuentePunto(pt),
      fechaSort: String(fd || "").slice(0, 10),
      precioLista: desc.lista,
      precioOferta: desc.oferta,
      descPct: desc.pct,
    };
  });
}

function renderTendenciaPreciosTable(fechas, serieGlobal, labels, periodo) {
  const esDiario = periodo === "diario";
  const sortKey = state.tendTableSort || "fecha";
  const dir = Number(state.tendTableDir) === -1 ? -1 : 1;
  let rows = tendFilasPreciosTable(fechas, serieGlobal, labels);
  const hayDesc = rows.some((r) => r.precioOferta != null && r.descPct != null);
  const cmp = (a, b) => {
    let av;
    let bv;
    if (sortKey === "usd") {
      av = a.usd == null ? Number.POSITIVE_INFINITY : a.usd;
      bv = b.usd == null ? Number.POSITIVE_INFINITY : b.usd;
    } else if (sortKey === "usd_oferta") {
      av = a.usdOferta == null ? Number.POSITIVE_INFINITY : a.usdOferta;
      bv = b.usdOferta == null ? Number.POSITIVE_INFINITY : b.usdOferta;
    } else if (sortKey === "delta") {
      av = a.delta == null ? Number.POSITIVE_INFINITY : a.delta;
      bv = b.delta == null ? Number.POSITIVE_INFINITY : b.delta;
    } else if (sortKey === "farmacia") {
      av = tendNormTxt(a.farmacia);
      bv = tendNormTxt(b.farmacia);
    } else if (sortKey === "oferta") {
      av = a.precioOferta == null ? Number.POSITIVE_INFINITY : a.precioOferta;
      bv = b.precioOferta == null ? Number.POSITIVE_INFINITY : b.precioOferta;
    } else if (sortKey === "lista") {
      av = a.precioLista == null ? Number.POSITIVE_INFINITY : a.precioLista;
      bv = b.precioLista == null ? Number.POSITIVE_INFINITY : b.precioLista;
    } else {
      av = a.fechaSort;
      bv = b.fechaSort;
    }
    if (av < bv) return -1 * dir;
    if (av > bv) return 1 * dir;
    return 0;
  };
  rows = [...rows].sort(cmp);

  const th = (key, label) => `
    <th class="sortable${sortKey === key ? " is-sorted" : ""}" data-tend-table-sort="${key}" scope="col">
      ${escapeHtml(label)} ${tendTableSortMark(key)}
    </th>`;

  const body = rows.map((r) => {
    const fuenteHtml = r.fuente
      ? `<a class="tend-fuente-link" href="${escapeHtml(r.fuente)}" target="_blank" rel="noreferrer" title="Ver producto en la farmacia">Ver fuente ↗</a>`
      : `<span class="muted">Sin enlace</span>`;
    let deltaHtml = "—";
    if (r.usd != null && r.delta != null) {
      if (Math.abs(r.delta) < 0.05) deltaHtml = `<span class="tend-delta">0.0%</span>`;
      else {
        const cls = r.delta > 0 ? "is-up" : "is-down";
        deltaHtml = `<span class="tend-delta ${cls}">${r.delta >= 0 ? "+" : ""}${r.delta.toFixed(1)}%</span>`;
      }
    }
    const listaHtml = r.precioLista != null
      ? `<span class="tend-precio-lista${r.precioOferta != null ? " is-tachado" : ""}">${tendLocalMoney(r.precioLista, r.moneda)}</span>`
      : `<span class="muted">—</span>`;
    const ofertaHtml = r.precioOferta != null
      ? `<span class="tend-precio-oferta">${tendLocalMoney(r.precioOferta, r.moneda)}${
          r.descPct != null ? ` <em class="tend-desc-pct">−${r.descPct.toFixed(0)}%</em>` : ""
        }</span>`
      : `<span class="muted">Sin descuento</span>`;
    const usdOfertaHtml = r.usdOferta != null
      ? `<span class="tend-usd-oferta">${money(r.usdOferta)}</span>`
      : `<span class="muted">—</span>`;
    return `
      <tr class="${r.precioOferta != null ? "has-descuento" : ""}">
        <td>${escapeHtml(r.label)}</td>
        <td class="tend-td-usd">${r.usd == null ? `<span class="muted">—</span>` : money(r.usd)}</td>
        <td class="tend-td-usd-oferta">${usdOfertaHtml}</td>
        <td>${deltaHtml}</td>
        <td class="tend-td-lista">${listaHtml}</td>
        <td class="tend-td-oferta">${ofertaHtml}</td>
        <td>${escapeHtml(r.farmacia || "—")}</td>
        <td class="tend-td-fuente">${fuenteHtml}</td>
      </tr>`;
  }).join("");

  return `
    <div class="table-wrap tend-precios-wrap">
      <p class="muted tend-desc-nota">
        <strong>Precio base</strong> = PVP de lista en moneda local.
        <strong>Precio descuento</strong> = oferta vigente cuando la farmacia la publica.
        <strong>USD (lista)</strong> convierte el PVP de lista; <strong>USD (desc.)</strong> convierte la oferta con el mismo tipo de cambio del día${hayDesc ? " (hay al menos una fecha con oferta)" : ""}.
        El Δ es sobre el USD de lista.
      </p>
      <table class="data tend-precios-table">
        <thead>
          <tr>
            ${th("fecha", esDiario ? "Fecha" : "Periodo")}
            ${th("usd", "USD (lista)")}
            ${th("usd_oferta", "USD (desc.)")}
            ${th("delta", "Δ lista")}
            ${th("lista", "Precio base")}
            ${th("oferta", "Precio descuento")}
            ${th("farmacia", "Farmacia")}
            <th scope="col">Fuente</th>
          </tr>
        </thead>
        <tbody>${body || `<tr><td colspan="8" class="muted">Sin fechas.</td></tr>`}</tbody>
      </table>
    </div>`;
}

let TEND_SERIE_CHART_MOD = null;
let TEND_CHART_SEQ = 0;

async function asegurarTendSerieChartMod() {
  if (TEND_SERIE_CHART_MOD) return TEND_SERIE_CHART_MOD;
  TEND_SERIE_CHART_MOD = await import(`/graficos-react.js?v=37`);
  return TEND_SERIE_CHART_MOD;
}

async function montarTendSerieChart(chartEl, fechas, series, labels) {
  if (!chartEl) return;
  const seq = ++TEND_CHART_SEQ;
  try {
    const mod = await asegurarTendSerieChartMod();
    if (seq !== TEND_CHART_SEQ) return;
    // Siempre montar vía React (incluye vacío): nunca innerHTML/replaceChildren
    // con un root vivo — eso hacía desaparecer el gráfico al filtrar.
    mod.mountTendSerieChart(chartEl, {
      fechas: fechas || [],
      series: series || [],
      labels: labels || {},
      chartTipo: state.tendChartTipo || "line",
      onTipo: (t) => {
        state.tendChartTipo = t;
        montarTendSerieChart(chartEl, fechas, series, labels);
      },
    });
  } catch (err) {
    console.error(err);
    if (seq !== TEND_CHART_SEQ) return;
    try {
      TEND_SERIE_CHART_MOD?.unmountTendSerieChart?.(chartEl);
    } catch (_) { /* ignore */ }
    chartEl.replaceChildren();
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = `No se pudo cargar el gráfico (${String(err.message || err)}).`;
    chartEl.appendChild(p);
  }
}

function aplicarVistaTendencia({ soloTabla = false } = {}) {
  const table = $("tendTable");
  const chartEl = $("tendSerieChart");
  if (!table || !TEND_DATA) return;
  const d = TEND_DATA;

  const farmRaw = (Array.isArray(d.series) ? d.series : []).filter((s) => paisActivo(idPaisPorTexto(s.pais)));
  const fechasRaw = Array.isArray(d.fechas) ? d.fechas : [];
  const n = d.n_lista ?? state.tendenciaN;
  const titulo = d.producto_label || d.nombre_comercial || d.medicamento_lista || `Medicamento #${n}`;

  if (!fechasRaw.length || !farmRaw.length) {
    table.innerHTML = `
      <div class="tend-empty">
        <h3>${escapeHtml(titulo)}</h3>
        <p class="muted">Todavía no hay puntos históricos.</p>
      </div>`;
    if (!soloTabla) {
      if (chartEl) montarTendSerieChart(chartEl, [], [], {});
    }
    return;
  }

  const periodo = state.tendPeriodo || "diario";
  const farmFiltered = tendSeriesFiltradasFarms(farmRaw);
  const aggFarms = tendAgregarSerie(fechasRaw, farmFiltered, periodo);
  const fechas = aggFarms.fechas;
  const labels = aggFarms.labels;
  const farmSeries = aggFarms.series;
  const serieGlobal = tendSerieGlobalDesdeFarmacias(fechas, farmSeries, "USD lista");
  const serieDesc = tendSerieUsdDescuentoDesdeGlobal(serieGlobal);
  const seriesChart = serieDesc.length
    ? [...serieGlobal, ...serieDesc]
    : serieGlobal;

  const tituloTabla = document.querySelector(".tend-table-title");
  if (tituloTabla) {
    tituloTabla.textContent = periodo === "diario"
      ? "Precios por fecha (USD · mínimo observado)"
      : "Precios promedio por periodo (USD · mínimo observado)";
  }

  const meta = $("tendMeta");
  if (meta) {
    meta.textContent = `${fechas.length} ${periodo === "diario" ? "fecha(s)" : "periodo(s)"} · precio mínimo entre farmacias${
      serieDesc.length ? " · con serie de descuento cuando hay oferta" : ""
    }`;
  }

  if (!soloTabla) {
    montarTendSerieChart(chartEl, fechas, seriesChart, labels);
  }
  table.innerHTML = renderTendenciaPreciosTable(fechas, serieGlobal, labels, periodo);
}

async function pintarTendenciaMedicamento(n, productoKey, { resetBadges = true } = {}) {
  const table = $("tendTable");
  if (!table) return;
  const cacheKey = tendSerieCacheKey(n, productoKey);
  const cached = TEND_SERIE_CACHE.get(cacheKey);
  if (cached?.ok) {
    TEND_DATA = cached;
    state.tendExpandFd = null;
    syncTendBadgesFromData(cached, { reset: resetBadges });
    aplicarVistaTendencia();
    return;
  }
  table.innerHTML = `<p class="muted">Cargando serie…</p>`;
  // No vaciar el chart con innerHTML: rompe el root de React y luego “desaparece”.
  try {
    const qs = new URLSearchParams({
      n_lista: String(n),
      producto_key: String(productoKey || ""),
      agrupar: "farmacia",
    });
    const r = await fetch(`/api/tendencias?${qs}`, { cache: "no-store" });
    const d = await r.json();
    if (!d?.ok) throw new Error(d?.error || "API");
    const packed = { ...d, n_lista: Number(n), producto_key: String(productoKey || "") };
    TEND_SERIE_CACHE.set(cacheKey, packed);
    TEND_DATA = packed;
    state.tendExpandFd = null;
    syncTendBadgesFromData(packed, { reset: resetBadges });
    aplicarVistaTendencia();
  } catch (err) {
    console.error(err);
    table.innerHTML = `<p class="muted">Error al cargar serie (${escapeHtml(String(err.message || err))}).</p>`;
  }
}

/** Escala Y “bonita” a partir del rango de valores. */
function tendNiceScale(minV, maxV, ticksWanted = 4) {
  if (!(maxV > minV)) {
    const pad = Math.max(Math.abs(maxV) * 0.08, 1);
    return { y0: Math.max(0, minV - pad), y1: maxV + pad, ticks: [minV, maxV] };
  }
  const span = maxV - minV;
  const raw = span / Math.max(ticksWanted, 1);
  const mag = 10 ** Math.floor(Math.log10(raw));
  const norm = raw / mag;
  const step = (norm <= 1.5 ? 1 : norm <= 3 ? 2 : norm <= 7 ? 5 : 10) * mag;
  const y0 = Math.max(0, Math.floor(minV / step) * step);
  const y1 = Math.ceil(maxV / step) * step;
  const ticks = [];
  for (let v = y0; v <= y1 + step * 0.001; v += step) ticks.push(v);
  return { y0, y1: Math.max(y1, y0 + step), ticks };
}

/**
 * Gráfico de líneas: periodo (X) × precio USD promedio (Y).
 * Adapta ancho, densidad de etiquetas y tamaño de puntos a la cantidad de datos.
 */
function renderTendSerieLineChart(fechas, series, labels, periodo) {
  const n = fechas.length;
  if (!n || !series.length) {
    return `<div class="tend-serie-chart"><p class="muted">Sin puntos para graficar.</p></div>`;
  }

  const vals = [];
  series.forEach((s) => {
    fechas.forEach((fd) => {
      const v = tendVal(tendPuntoEnFecha(s, fd));
      if (v != null) vals.push(v);
    });
  });
  if (!vals.length) {
    return `<div class="tend-serie-chart"><p class="muted">Sin precios en el periodo seleccionado.</p></div>`;
  }

  const dense = n > 18;
  const medium = n > 10;
  const manySeries = series.length > 4;
  const perSlot = dense ? 52 : medium ? 68 : 86;
  const w = Math.max(640, Math.min(1280, 120 + n * perSlot));
  const h = manySeries ? 360 : dense ? 300 : 320;
  const pad = {
    t: 28,
    r: dense ? 22 : 28,
    b: dense || medium ? 72 : 56,
    l: 72,
  };
  const iw = w - pad.l - pad.r;
  const ih = h - pad.t - pad.b;

  const minV = Math.min(...vals);
  const maxV = Math.max(...vals);
  const padY = Math.max((maxV - minV) * 0.08, maxV * 0.02, 1);
  const { y0, y1, ticks: yTicks } = tendNiceScale(
    Math.max(0, minV - padY),
    maxV + padY,
    dense ? 3 : 4,
  );

  const xAt = (i) => pad.l + (n <= 1 ? iw / 2 : (i / (n - 1)) * iw);
  const yAt = (v) => pad.t + ih - ((Number(v) - y0) / (y1 - y0)) * ih;

  const colors = ["#003eab", "#0e7490", "#b45309", "#15803d", "#7c3aed", "#be123c", "#0369a1", "#a16207"];
  const uid = `ts${Math.abs(String(fechas[0]).split("").reduce((a, c) => a + c.charCodeAt(0), 0)) % 1e6}`;

  const maxXLabels = dense ? 6 : medium ? 8 : Math.min(n, 12);
  const stepX = Math.max(1, Math.ceil(n / maxXLabels));
  const rotateX = dense || medium || (periodo === "quincenal" && n > 6);

  const grid = yTicks.map((v) => {
    const y = yAt(v);
    return `<line class="tend-serie-grid" x1="${pad.l}" x2="${w - pad.r}" y1="${y}" y2="${y}"/>
      <text class="tend-serie-axis tend-serie-axis-y" x="${pad.l - 10}" y="${y + 3.5}" text-anchor="end">${escapeHtml(fmtUsdText(v))}</text>`;
  }).join("");

  const xAxis = `<line class="tend-serie-axis-line" x1="${pad.l}" x2="${w - pad.r}" y1="${pad.t + ih}" y2="${pad.t + ih}"/>
    <line class="tend-serie-axis-line" x1="${pad.l}" x2="${pad.l}" y1="${pad.t}" y2="${pad.t + ih}"/>`;

  const xLabels = fechas.map((fd, i) => {
    const show = i === 0 || i === n - 1 || i % stepX === 0;
    if (!show) return "";
    const lab = tendFmtPeriodo(fd, labels);
    const x = xAt(i);
    const y = pad.t + ih + (rotateX ? 14 : 20);
    if (rotateX) {
      return `<text class="tend-serie-axis tend-serie-axis-x" x="${x}" y="${y}" text-anchor="end" transform="rotate(-38 ${x} ${y})">${escapeHtml(lab)}</text>`;
    }
    return `<text class="tend-serie-axis tend-serie-axis-x" x="${x}" y="${y}" text-anchor="middle">${escapeHtml(lab)}</text>`;
  }).join("");

  const strokeW = dense ? 1.8 : manySeries ? 2 : 2.4;
  const dotR = dense ? 3.2 : n <= 6 ? 5 : 4.2;

  const layers = series.map((s, si) => {
    const color = colors[si % colors.length];
    const pts = fechas.map((fd, i) => {
      const pt = tendPuntoEnFecha(s, fd);
      const v = tendVal(pt);
      if (v == null) return null;
      return { i, fd, v, x: xAt(i), y: yAt(v), nObs: pt?.n_obs || 0 };
    });

    let dLine = "";
    let dArea = "";
    let penUp = true;
    let areaOpen = false;
    let firstX = null;
    let lastX = null;
    pts.forEach((p) => {
      if (!p) {
        if (areaOpen && firstX != null && lastX != null) {
          dArea += ` L${lastX},${pad.t + ih} L${firstX},${pad.t + ih} Z`;
          areaOpen = false;
          firstX = null;
        }
        penUp = true;
        return;
      }
      dLine += `${penUp ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)} `;
      if (penUp) {
        dArea += `M${p.x.toFixed(1)},${(pad.t + ih).toFixed(1)} L${p.x.toFixed(1)},${p.y.toFixed(1)} `;
        firstX = p.x;
        areaOpen = true;
      } else {
        dArea += `L${p.x.toFixed(1)},${p.y.toFixed(1)} `;
      }
      lastX = p.x;
      penUp = false;
    });
    if (areaOpen && firstX != null && lastX != null) {
      dArea += ` L${lastX},${pad.t + ih} L${firstX},${pad.t + ih} Z`;
    }

    const showArea = series.length <= 3;
    const area = showArea
      ? `<path class="tend-serie-area" d="${dArea.trim()}" fill="url(#${uid}-g${si})" opacity="0.55"/>`
      : "";
    const line = `<path class="tend-serie-line" d="${dLine.trim()}" fill="none" stroke="${color}" stroke-width="${strokeW}" stroke-linecap="round" stroke-linejoin="round"/>`;
    const dots = pts.filter(Boolean).map((p) => {
      const periodoTxt = tendFmtPeriodo(p.fd, labels);
      return `<circle class="tend-serie-dot" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${dotR}"
        fill="#fff" stroke="${color}" stroke-width="2"
        data-pais="${escapeHtml(s.pais)}"
        data-periodo="${escapeHtml(periodoTxt)}"
        data-precio="${escapeHtml(fmtUsdText(p.v))}"
        data-obs="${p.nObs ? String(p.nObs) : ""}"
        data-color="${color}"></circle>`;
    }).join("");

    return `${area}${line}${dots}`;
  }).join("");

  const grads = series.slice(0, 3).map((s, si) => {
    const color = colors[si % colors.length];
    return `<linearGradient id="${uid}-g${si}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="${color}" stop-opacity="0.28"/>
      <stop offset="100%" stop-color="${color}" stop-opacity="0.02"/>
    </linearGradient>`;
  }).join("");

  const periodoLab = periodo === "diario"
    ? "diario"
    : periodo === "quincenal"
      ? "quincenal"
      : periodo === "trimestral"
        ? "trimestral"
        : "mensual";
  const esDiario = periodo === "diario";
  const legend = series.map((s, i) => `
    <span class="tend-leg"><i style="background:${colors[i % colors.length]}"></i>${escapeHtml(s.pais)}</span>
  `).join("");

  return `
    <div class="tend-serie-chart">
      <div class="tend-serie-chart-head">
        <div>
          <h3>${esDiario ? "Evolución del precio diario" : "Evolución del precio promedio"}</h3>
          <p class="tend-serie-chart-sub">Eje X: ${esDiario ? "fecha" : `periodo ${periodoLab}`} · Eje Y: PVP USD · ${n} ${esDiario ? (n === 1 ? "día" : "días") : (n === 1 ? "periodo" : "periodos")}</p>
        </div>
        <div class="tend-legend">${legend}</div>
      </div>
      <div class="tend-serie-chart-frame">
        <svg viewBox="0 0 ${w} ${h}" class="tend-serie-svg" role="img" aria-label="${esDiario ? "Gráfico de precios por día" : "Gráfico de precios por periodo"}" preserveAspectRatio="xMidYMid meet">
          <defs>
            <linearGradient id="${uid}-bg" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#f4f8fc" stop-opacity="1"/>
              <stop offset="100%" stop-color="#ffffff" stop-opacity="1"/>
            </linearGradient>
            ${grads}
          </defs>
          <rect x="${pad.l}" y="${pad.t}" width="${iw}" height="${ih}" fill="url(#${uid}-bg)" rx="6"/>
          ${grid}
          ${xAxis}
          ${layers}
          ${xLabels}
        </svg>
        <div class="tend-serie-tooltip" id="tendSerieTip" hidden role="tooltip">
          <div class="tend-serie-tooltip__accent"></div>
          <div class="tend-serie-tooltip__body">
            <div class="tend-serie-tooltip__pais"></div>
            <div class="tend-serie-tooltip__periodo"></div>
            <div class="tend-serie-tooltip__precio"></div>
            <div class="tend-serie-tooltip__obs" hidden></div>
          </div>
        </div>
      </div>
    </div>`;
}

/** Tooltip flotante para puntos del gráfico de serie. */
function bindTendSerieTooltip(root) {
  if (!root) return;
  const frame = root.querySelector(".tend-serie-chart-frame");
  const tip = root.querySelector(".tend-serie-tooltip");
  const svg = root.querySelector(".tend-serie-svg");
  if (!frame || !tip || !svg) return;

  const accent = tip.querySelector(".tend-serie-tooltip__accent");
  const elPais = tip.querySelector(".tend-serie-tooltip__pais");
  const elPeriodo = tip.querySelector(".tend-serie-tooltip__periodo");
  const elPrecio = tip.querySelector(".tend-serie-tooltip__precio");
  const elObs = tip.querySelector(".tend-serie-tooltip__obs");

  const hide = () => {
    tip.hidden = true;
    tip.classList.remove("is-visible");
  };

  const show = (dot, clientX, clientY) => {
    const pais = dot.getAttribute("data-pais") || "";
    const periodoTxt = dot.getAttribute("data-periodo") || "";
    const precio = dot.getAttribute("data-precio") || "";
    const obs = dot.getAttribute("data-obs") || "";
    const color = dot.getAttribute("data-color") || "#003eab";
    const meta = metaPaisPorTexto(pais);
    const flag = meta?.flag ? `${meta.flag} ` : "";

    if (accent) accent.style.background = color;
    if (elPais) elPais.innerHTML = `<span class="tend-serie-tooltip__flag">${flag}</span><strong>${escapeHtml(pais)}</strong>`;
    if (elPeriodo) elPeriodo.textContent = periodoTxt;
    if (elPrecio) elPrecio.innerHTML = `<span class="tend-serie-tooltip__label">PVP</span> <strong class="money"><span class="money-cur">USD</span> ${escapeHtml(String(precio).replace(/^USD\s+/i, ""))}</strong>`;
    if (elObs) {
      if (obs) {
        elObs.hidden = false;
        elObs.textContent = `${obs} observación${obs === "1" ? "" : "es"} en el periodo`;
      } else {
        elObs.hidden = true;
        elObs.textContent = "";
      }
    }

    tip.hidden = false;
    tip.classList.add("is-visible");

    const frameRect = frame.getBoundingClientRect();
    const tipRect = tip.getBoundingClientRect();
    let left = clientX - frameRect.left + 14;
    let top = clientY - frameRect.top - tipRect.height - 12;

    if (left + tipRect.width > frameRect.width - 8) {
      left = clientX - frameRect.left - tipRect.width - 14;
    }
    if (left < 8) left = 8;
    if (top < 8) top = clientY - frameRect.top + 18;

    tip.style.left = `${left}px`;
    tip.style.top = `${top}px`;
  };

  frame.querySelectorAll(".tend-serie-dot").forEach((dot) => {
    dot.addEventListener("pointerenter", (e) => show(dot, e.clientX, e.clientY));
    dot.addEventListener("pointermove", (e) => {
      if (!tip.hidden) show(dot, e.clientX, e.clientY);
    });
    dot.addEventListener("pointerleave", hide);
  });
  frame.addEventListener("scroll", hide, { passive: true });
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
        data-tip="${escapeHtml(p.pais)} · ${escapeHtml(fmtFecha(p.fd))} · ${fmtUsdText(p.v)}${p.clipped ? " (fuera de escala)" : ""}"
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
      <text x="${pad.l - 6}" y="${y + 3}" text-anchor="end" class="tend-axis">${fmtUsdText(v)}</text>`;
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
  const tab = ["datos", "regulatorias", "tasas"].includes(state.fuentesTab)
    ? state.fuentesTab
    : "datos";
  state.fuentesTab = tab;

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
            ${job?.solicitado_por === "cron" && job.estado === "done" ? `<span class="muted source-job-msg">vía cron</span>` : ""}
            ${job?.mensaje && job.estado === "error" ? `<span class="muted source-job-msg">${escapeHtml(job.mensaje)}</span>` : ""}
            ${job?.mensaje && job.estado === "done" && String(job.mensaje).includes("[cron]") && /caché|bloqueo|MERGE 0/i.test(job.mensaje)
              ? `<span class="muted source-job-msg">${escapeHtml(job.mensaje.replace(/^\[cron\]\s*/, ""))}</span>` : ""}
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

  const tabs = [
    ["datos", "Fuentes de datos", `${datos.length} farmacia${datos.length === 1 ? "" : "s"}`],
    ["regulatorias", "Regulatorias", "FDA · EMA"],
    ["tasas", "Tasa de cambio", `${tasasPais.length} país${tasasPais.length === 1 ? "" : "es"}`],
  ];

  const paneles = {
    datos: {
      nota: "PVP publicado en las farmacias. El cron de madrugada actualiza solo; «Actualizar ahora» encola un scrape manual en el worker.",
      body: `<div class="source-grid">${datos.map(tarjetaDato).join("") || `<p class="muted" style="padding:18px">No hay fuentes de datos.</p>`}</div>`,
    },
    regulatorias: {
      nota: "FDA (Purple Book / openFDA) y EMA (medicines XLSX). Misma cola durable en backend.",
      body: `<div class="source-grid">${regFuenteCards}</div>`,
    },
    tasas: {
      nota: "Cuánto vale 1 dólar en DOP, ARS, BRL, COP y MXN. Con esa tasa se pasa el PVP a USD y a pesos dominicanos (BCRD venta).",
      body: `<div class="source-grid">${tasasPais.map(tarjetaFx).join("") || `<p class="muted" style="padding:18px">No hay tasas cargadas.</p>`}</div>`,
    },
  };
  const panel = paneles[tab];

  $("stage").innerHTML = `
    <article class="card fuentes-card">
      <div class="card-head fuentes-card-head">
        <div class="tend-vista-tabs fuentes-tabs" role="tablist" aria-label="Tipo de fuente">
          ${tabs.map(([id, label, hint]) => `
            <button type="button" role="tab" class="tend-vista-tab${tab === id ? " is-active" : ""}"
              data-fuentes-tab="${id}" aria-selected="${tab === id}" title="${escapeHtml(hint)}">
              ${escapeHtml(label)}
              <span class="fuentes-tab-count">${escapeHtml(hint)}</span>
            </button>`).join("")}
        </div>
      </div>
      <p class="muted fuentes-panel-nota">${escapeHtml(panel.nota)}</p>
      ${panel.body}
    </article>
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
    kicker: "Entrada",
    accent: "tablero",
    resumen: "Panorama de cobertura por país: principios y presentaciones con precio antes de entrar al análisis.",
    secciones: [
      {
        titulo: "Qué muestra",
        parrafos: [
          "Una tarjeta por país con bandera, farmacias consultadas y contadores de principios activos y medicamentos (presentaciones) en la última fecha del historial.",
          "Si un país no tiene scrape del día pero sí histórico, la tarjeta usa borde punteado y muestra cuántas presentaciones hay disponibles.",
        ],
      },
      {
        titulo: "Cómo usarlo",
        lista: [
          "Clic en un país → listado DAMAC/FOMAC de ese mercado.",
          "Dentro del modal: Principios, Farmacias (con logo) o tabla de Medicamentos.",
          "Desde una farmacia se abre su catálogo con búsqueda y paginación.",
        ],
      },
      {
        titulo: "Conexión con el resto",
        lista: [
          "Los contadores salen del mismo historial que alimenta Análisis.",
          "La ficha del medicamento enlaza Comparativo, Detalle y datos FDA/EMA.",
        ],
      },
    ],
  },
  {
    id: "tendencias",
    titulo: "Análisis",
    kicker: "Precios",
    accent: "analisis",
    resumen: "Tres vistas: serie temporal, tema terapéutico y comparativo del PVP representativo por país.",
    secciones: [
      {
        titulo: "Serie por medicamento",
        parrafos: [
          "Serie del PVP mínimo por país para una presentación concreta (medicamento + dosis + forma + empaque).",
          "Tabla por fecha con PVP local, USD, farmacia y variación porcentual frente al punto anterior.",
        ],
      },
      {
        titulo: "Tema terapéutico",
        parrafos: [
          "Indicadores por tema EMA (conveniencia y detalle por país), siempre con la última fecha del historial.",
          "Activá o desactivá países con los badges (bandera y color).",
        ],
      },
      {
        titulo: "Comparativo",
        parrafos: [
          "Por cada principio DAMAC/FOMAC, el precio mínimo representativo por país en la misma presentación comparable.",
          "Con varios genéricos se usa la mediana; si hay uno solo, el más barato. Clic en la tarjeta abre la ficha.",
        ],
      },
      {
        titulo: "Huecos en la serie",
        lista: [
          "Si un país no aparece en una fecha, ese día no hubo scrape con precio; no se interpola.",
          "Un precio estable no crea fila nueva cada día: la fila existente extiende su vigencia.",
        ],
      },
    ],
  },
  {
    id: "alertas",
    titulo: "Alertas",
    kicker: "Seguimiento",
    accent: "alertas",
    resumen: "Notificaciones de patentes por vencer y de movimientos de precio según criterios que vos definís.",
    secciones: [
      {
        titulo: "Patentes",
        parrafos: [
          "Seguimiento de vencimientos FDA (Orange Book / Purple Book) ligados a los principios de la lista.",
          "La tuerca abre criterios: ventana de días restantes, fuente, medicamento opcional, aviso si vence hoy, si pasó a expirada y recordatorio diario.",
        ],
        lista: [
          "Las coincidencias alimentan el badge y el panel superior de alertas.",
          "«Evaluar ahora» o el cron de madrugada aplican los criterios activos.",
        ],
      },
      {
        titulo: "Precios",
        parrafos: [
          "Criterios por producto/farmacia con umbrales de baja o alza porcentual.",
          "Cuando el scrape cruza el umbral se genera una alerta en el historial de la pestaña Precios.",
        ],
      },
    ],
  },
  {
    id: "detalle",
    titulo: "Detalle",
    kicker: "Granular",
    accent: "detalle",
    resumen: "Cada presentación scrapeada en farmacia, sin agregar por principio. Ideal para auditar un precio concreto.",
    secciones: [
      {
        titulo: "Qué muestra",
        parrafos: [
          "Una fila por producto: marca, farmacia, concentración, presentación y precios en USD, DOP y moneda local.",
          "Incluye enlace a la página original de la farmacia cuando está disponible.",
        ],
      },
      {
        titulo: "Filtros",
        lista: [
          "Búsqueda por producto, concentración o molécula.",
          "Filtro por país.",
          "Columnas: medicamento, país, farmacia, producto, concentración, presentación, USD, DOP, local y fecha.",
        ],
      },
      {
        titulo: "Cuándo usarlo",
        lista: [
          "Auditar un precio o ver todas las variantes comerciales de un principio.",
          "Contrastar con el Comparativo de Análisis, que resume un solo valor representativo por país.",
        ],
      },
    ],
  },
  {
    id: "fuentes",
    titulo: "Fuentes",
    kicker: "Origen",
    accent: "fuentes",
    resumen: "Farmacias scrapeadas, tasas de cambio, jobs regulatorios y bitácora del cron diario.",
    secciones: [
      {
        titulo: "Farmacias y scrapers",
        lista: [
          "Cada tarjeta: país, farmacia, método de extracción y SKU en tabla.",
          "«Actualizar ahora» encola un scrape (en cola → ejecutando → listo / error).",
          "Enlace al catálogo público cuando existe.",
        ],
      },
      {
        titulo: "Tasas de cambio",
        parrafos: [
          "USD → moneda local para homogenizar precios. República Dominicana usa la venta del BCRD para el equivalente en DOP.",
        ],
      },
      {
        titulo: "Regulatorias y cron",
        lista: [
          "FDA Purple Book, openFDA / patentes (Orange y Purple) y EMA medicines (XLSX oficial).",
          "El cron de madrugada registra corridas y pasos; el panel Fuentes muestra el último resultado.",
        ],
      },
    ],
  },
  {
    id: "ficha",
    titulo: "Ficha de medicamento",
    kicker: "Modal",
    accent: "ficha",
    resumen: "Se abre desde Tablero, Comparativo o enlaces regulatorios. No está en el menú lateral, pero concentra el flujo clínico-regulatorio.",
    secciones: [
      {
        titulo: "Contenido",
        lista: [
          "Resumen DAMAC/FOMAC, presentación comparada y precios por país.",
          "Productos comparables vs. excluidos (innovadores, combinaciones, precios atípicos).",
          "Selector FDA · EMA · comparación FDA/EMA.",
        ],
      },
      {
        titulo: "FDA",
        lista: [
          "Purple Book u Orange Book según biológico o molécula pequeña.",
          "Indicaciones con PDF oficial de Drugs@FDA; patentes, exclusividades y tentativas.",
        ],
      },
      {
        titulo: "EMA",
        lista: [
          "Catálogo europeo (INN, ATC, clase: innovador, biosimilar, genérico, huérfano).",
          "Indicaciones desde EPAR en español cuando están disponibles.",
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

function htmlDocModulo(mod, { exportMode = false, index = 0 } = {}) {
  const anchor = exportMode ? "" : ` id="doc-${mod.id}"`;
  const n = String(index + 1).padStart(2, "0");
  const accent = escapeHtml(mod.accent || "tablero");
  return `
    <article class="doc-module doc-module--${accent}"${anchor}>
      <header class="doc-module-head">
        <span class="doc-module-num" aria-hidden="true">${n}</span>
        <div class="doc-module-titles">
          ${mod.kicker ? `<p class="doc-module-kicker">${escapeHtml(mod.kicker)}</p>` : ""}
          <h2>${escapeHtml(mod.titulo)}</h2>
          <p class="doc-module-lead">${escapeHtml(mod.resumen)}</p>
        </div>
      </header>
      <div class="doc-module-body">
        ${(mod.secciones || []).map((s) => htmlDocSeccion(s)).join("")}
      </div>
    </article>`;
}

function htmlDocumentacionBody({ exportMode = false, toc = false } = {}) {
  const tocHtml = toc
    ? `<nav class="doc-toc" aria-label="Índice de módulos">
        <p class="doc-toc-label">Índice</p>
        <ol>
          ${DOC_MODULOS.map((m, i) => `
            <li>
              <a href="#doc-${m.id}">
                <span class="doc-toc-n">${String(i + 1).padStart(2, "0")}</span>
                <span class="doc-toc-t">${escapeHtml(m.titulo)}</span>
              </a>
            </li>`).join("")}
        </ol>
      </nav>`
    : "";
  return `
    <header class="doc-hero">
      <p class="doc-hero-kicker">Guía de uso</p>
      <h1>Documentación del observatorio</h1>
      <p class="doc-hero-sub">${escapeHtml(docGeneradoTexto())}</p>
      <p class="doc-hero-lead">Recorrido de Tablero, Análisis, Alertas, Detalle, Fuentes y la ficha de medicamento. Los precios son PVP al consumidor; la conversión a USD usa la tasa vigente de cada país.</p>
    </header>
    <div class="doc-layout${toc ? " doc-layout--toc" : ""}">
      ${tocHtml}
      <div class="doc-modules">
        ${DOC_MODULOS.map((m, i) => htmlDocModulo(m, { exportMode, index: i })).join("")}
      </div>
    </div>`;
}

function renderDocumentacion() {
  $("stage").innerHTML = `
    <article class="card doc-card">
      <div class="card-head doc-card-head">
        <div class="doc-card-intro">
          <p class="doc-card-kicker">Manual interno</p>
          <h2>Guía de módulos</h2>
          <p class="muted">Cómo leer y operar cada vista del observatorio. Exportá la guía en PDF, Word o Excel.</p>
        </div>
        <div class="doc-export-actions" role="group" aria-label="Exportar documentación">
          <button type="button" class="btn-doc-export btn-doc-export--pdf" id="btnDocPdf" title="Exportar PDF">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5z"/><path d="M14 3v5h5M8 13h8M8 17h5"/></svg>
            <span>PDF</span>
          </button>
          <button type="button" class="btn-doc-export btn-doc-export--word" id="btnDocWord" title="Exportar Word">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5z"/><path d="M14 3v5h5M9 13l1.4 5L12 13l1.6 5L15 13"/></svg>
            <span>Word</span>
          </button>
          <button type="button" class="btn-doc-export btn-doc-export--excel" id="btnDocExcel" title="Exportar Excel">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5z"/><path d="M14 3v5h5M9 13l6 5M15 13l-6 5"/></svg>
            <span>Excel</span>
          </button>
        </div>
      </div>
      <div class="doc-body" id="docBody">
        ${htmlDocumentacionBody({ toc: true })}
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

function docExportStamp() {
  return new Date().toISOString().slice(0, 10);
}

function buildDocumentacionExportHtml() {
  const inner = htmlDocumentacionBody({ exportMode: true });
  return `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <title>Documentación · Observatorio alto costo</title>
  <style>
    body { font-family: "IBM Plex Sans", Calibri, Arial, sans-serif; color: #1a2b3c; line-height: 1.5; margin: 24px 32px; font-size: 11pt; }
    h1 { color: #003eab; font-size: 22pt; margin: 0 0 8px; }
    h2 { color: #003eab; font-size: 14pt; margin: 22px 0 8px; border-bottom: 1px solid #d7e2ef; padding-bottom: 4px; }
    h3 { font-size: 11pt; margin: 14px 0 6px; color: #334455; }
    p { margin: 0 0 8px; }
    ul { margin: 0 0 10px; padding-left: 20px; }
    li { margin-bottom: 4px; }
    .doc-hero-kicker, .doc-module-kicker, .doc-module-num { color: #5a6b7c; font-size: 10pt; text-transform: uppercase; letter-spacing: .04em; }
    .doc-hero-sub { color: #5a6b7c; font-size: 10pt; }
    .doc-hero-lead { color: #445566; margin-bottom: 18px; }
    .doc-module { margin-bottom: 18px; page-break-inside: avoid; }
    .doc-module-lead { color: #445566; margin: 0 0 10px; }
    .doc-module-num { display: inline-block; margin-right: 8px; font-weight: 700; color: #003eab; }
  </style>
</head>
<body>
  ${inner}
</body>
</html>`;
}

function xmlEscape(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function filasDocumentacionExcel() {
  const rows = [
    ["Módulo", "Sección", "Tipo", "Contenido"],
  ];
  for (const mod of DOC_MODULOS) {
    rows.push([mod.titulo, "Resumen", "texto", mod.resumen || ""]);
    for (const sec of mod.secciones || []) {
      for (const p of sec.parrafos || []) {
        rows.push([mod.titulo, sec.titulo, "párrafo", p]);
      }
      for (const it of sec.lista || []) {
        rows.push([mod.titulo, sec.titulo, "viñeta", it]);
      }
    }
  }
  return rows;
}

/** SpreadsheetML (.xls) que Excel abre nativo, sin dependencias CDN. */
function buildDocumentacionExcelXml() {
  const rows = filasDocumentacionExcel();
  const cells = rows.map((row, ri) => {
    const tds = row.map((cell) => {
      const v = xmlEscape(cell);
      const isHeader = ri === 0;
      return `<Cell${isHeader ? ' ss:StyleID="hdr"' : ""}><Data ss:Type="String">${v}</Data></Cell>`;
    }).join("");
    return `<Row>${tds}</Row>`;
  }).join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
  <Styles>
    <Style ss:ID="hdr">
      <Font ss:Bold="1" ss:Color="#FFFFFF"/>
      <Interior ss:Color="#003EAB" ss:Pattern="Solid"/>
    </Style>
  </Styles>
  <Worksheet ss:Name="Documentación">
    <Table>
      <Column ss:Width="120"/>
      <Column ss:Width="140"/>
      <Column ss:Width="70"/>
      <Column ss:Width="420"/>
      ${cells}
    </Table>
  </Worksheet>
  <Worksheet ss:Name="Índice">
    <Table>
      <Column ss:Width="40"/>
      <Column ss:Width="160"/>
      <Column ss:Width="420"/>
      <Row>
        <Cell ss:StyleID="hdr"><Data ss:Type="String">#</Data></Cell>
        <Cell ss:StyleID="hdr"><Data ss:Type="String">Módulo</Data></Cell>
        <Cell ss:StyleID="hdr"><Data ss:Type="String">Resumen</Data></Cell>
      </Row>
      ${DOC_MODULOS.map((m, i) => `
      <Row>
        <Cell><Data ss:Type="Number">${i + 1}</Data></Cell>
        <Cell><Data ss:Type="String">${xmlEscape(m.titulo)}</Data></Cell>
        <Cell><Data ss:Type="String">${xmlEscape(m.resumen || "")}</Data></Cell>
      </Row>`).join("")}
    </Table>
  </Worksheet>
</Workbook>`;
}

function exportDocumentacionWord() {
  try {
    const html = buildDocumentacionExportHtml();
    const blob = new Blob(["\ufeff", html], { type: "application/msword;charset=utf-8" });
    downloadBlob(blob, `documentacion-observatorio-alto-costo-${docExportStamp()}.doc`);
  } catch (err) {
    console.error(err);
    alert(`No se pudo exportar a Word: ${err.message || err}`);
  }
}

function exportDocumentacionExcel() {
  const btn = $("btnDocExcel");
  if (btn) {
    btn.disabled = true;
    btn.querySelector("span") && (btn.querySelector("span").textContent = "…");
  }
  try {
    const xml = buildDocumentacionExcelXml();
    const blob = new Blob(["\ufeff", xml], {
      type: "application/vnd.ms-excel;charset=utf-8",
    });
    downloadBlob(blob, `documentacion-observatorio-alto-costo-${docExportStamp()}.xls`);
  } catch (err) {
    console.error(err);
    alert(`No se pudo exportar a Excel: ${err.message || err}`);
  } finally {
    if (btn) {
      btn.disabled = false;
      const span = btn.querySelector("span");
      if (span) span.textContent = "Excel";
    }
  }
}

async function loadHtml2Pdf() {
  const src = "https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js";
  if (typeof window.html2pdf === "function") return window.html2pdf;
  await new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`);
    if (existing) {
      if (typeof window.html2pdf === "function") {
        resolve();
        return;
      }
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("No se pudo cargar la librería PDF")), { once: true });
      return;
    }
    const s = document.createElement("script");
    s.src = src;
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("No se pudo cargar la librería PDF"));
    document.head.appendChild(s);
  });
  if (typeof window.html2pdf !== "function") {
    throw new Error("La librería PDF no quedó disponible");
  }
  return window.html2pdf;
}

function mountDocPdfClone() {
  const host = document.createElement("div");
  host.id = "docPdfClone";
  host.className = "doc-pdf-clone";
  host.setAttribute("aria-hidden", "true");
  host.innerHTML = htmlDocumentacionBody({ exportMode: true });
  document.body.appendChild(host);
  return host;
}

async function exportDocumentacionPdf() {
  const btn = $("btnDocPdf");
  if (btn) {
    btn.disabled = true;
    const span = btn.querySelector("span");
    if (span) span.textContent = "Generando…";
  }
  let clone = null;
  try {
    const html2pdf = await loadHtml2Pdf();
    clone = mountDocPdfClone();
    // Dejar que el layout pinte antes de capturar.
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    await html2pdf()
      .set({
        margin: [12, 12, 14, 12],
        filename: `documentacion-observatorio-alto-costo-${docExportStamp()}.pdf`,
        image: { type: "jpeg", quality: 0.96 },
        html2canvas: {
          scale: 2,
          useCORS: true,
          logging: false,
          backgroundColor: "#ffffff",
          windowWidth: 820,
        },
        jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
        pagebreak: { mode: ["css", "legacy"], avoid: [".doc-module", ".doc-block"] },
      })
      .from(clone)
      .save();
  } catch (err) {
    console.error(err);
    alert(`No se pudo generar el PDF: ${err.message || err}`);
  } finally {
    if (clone?.parentNode) clone.parentNode.removeChild(clone);
    if (btn) {
      btn.disabled = false;
      const span = btn.querySelector("span");
      if (span) span.textContent = "PDF";
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
          : `<span class="cover-pa-miss">Sin precio</span>`}
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
  return all;
}

function dominioDeUrl(url) {
  try {
    return new URL(String(url || "")).hostname.replace(/^www\./i, "");
  } catch {
    return "";
  }
}

// Mapa farmacia → archivo de logo local (en /logos/farmacias/)
const LOGO_LOCAL = {
  "FarmaValue":            "farmavalue.png",
  "Carol":                 "carol.png",
  "Los Hidalgos":          "hidalgos.png",
  "Qualipharma":           "qualipharma.png",
  "GBC":                   "gbc.png",
  "Pague Menos":           "paguemenos.svg",
  "Salcobrand":            "salcobrand.svg",
  "Farmacias Ahumada":     "ahumada.svg",
  "Farmacity":             "farmacity.png",
  "Locatel":               "locatel.png",
  "Farmatodo":             "farmatodo.svg",
  "Macrofarmacias":        "macrofarmacias.png",
  "Farmacias Similares":   "similares.png",
  "Cruz Azul":             "cruzazul.svg",
  "Pharmacy's":            "pharmacys.svg",
  "Kielsa":                "kielsa.png",
  "Inkafarma":             "inkafarma.png",
  "Carulla":               "carulla.svg",
  "Siman":                 "siman.png",
  "Arrocha":               "arrocha.png",
  "Farmacias del Ahorro":  "fahorro.png",
  "Farmacias San Nicolás": "sannicolas.png",
  "Farmashop":             "farmashop.png",
  "Cruz Verde":            null,
  "Droga Raia":            "drogaraia.png",
  "Drogasil":              "drogasil.png",
  "MiFarmacia":            "mifarmacia.png",
  "Farmacias Fischel":     "fischel.png",
  "Farmacias Galeno":      "galeno.ico",
  "La Rebaja":             null,
};

function logoFarmaciaHtml(farmacia, paisNombre, cls = "farm-logo") {
  // cls puede ser "farm-logo farm-logo--hero"; usamos el primer token como base
  const base = cls.split(" ")[0];
  const initial = String(farmacia || "?").trim().charAt(0).toUpperCase() || "?";
  const fbSpan = `<span class="${base}--fallback" hidden aria-hidden="true">${escapeHtml(initial)}</span>`;
  const fbOnly = `<span class="${base}-wrap"><span class="${base}--fallback" aria-hidden="true">${escapeHtml(initial)}</span></span>`;

  // Logo local
  const localFile = LOGO_LOCAL[farmacia] ?? LOGO_LOCAL[String(farmacia).trim()];
  if (localFile) {
    return `<span class="${base}-wrap"><img class="${cls}" src="/logos/farmacias/${localFile}"
        alt="${escapeHtml(farmacia)}" loading="lazy"
        onerror="this.style.display='none';var n=this.nextElementSibling;if(n)n.hidden=false" />${fbSpan}</span>`;
  }

  // Favicon de Google como segundo recurso
  const meta = metaFuenteFarmacia(farmacia, paisNombre);
  const domain = dominioDeUrl(meta.link);
  if (!domain) return fbOnly;
  return `<span class="${base}-wrap"><img class="${cls}" src="https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=256"
      alt="${escapeHtml(farmacia)}" loading="lazy"
      onerror="this.style.display='none';var n=this.nextElementSibling;if(n)n.hidden=false" />${fbSpan}</span>`;
}

function farmaciasDelPais(paisId) {
  const base = filasTablaBase().filter((f) => idPaisPorTexto(f.pais) === paisId && f.farmacia);
  const byFarm = new Map();
  for (const f of base) {
    const nombre = String(f.farmacia).trim();
    if (!nombre) continue;
    let cur = byFarm.get(nombre);
    if (!cur) {
      cur = { farmacia: nombre, skus: 0, principios: new Set(), pais: f.pais };
      byFarm.set(nombre, cur);
    }
    cur.skus += 1;
    if (f.n_lista != null) cur.principios.add(Number(f.n_lista));
  }
  return [...byFarm.values()]
    .map((x) => {
      const meta = metaFuenteFarmacia(x.farmacia, x.pais);
      return {
        farmacia: x.farmacia,
        skus: x.skus,
        principios: x.principios.size,
        pais: x.pais,
        link: meta.link || "",
        que: meta.que || "",
      };
    })
    .sort((a, b) => b.skus - a.skus || a.farmacia.localeCompare(b.farmacia, "es"));
}

function coverFarmCardHtml(farm, idx = 0) {
  const tieneLogoLocal = !!(LOGO_LOCAL[farm.farmacia] ?? LOGO_LOCAL[String(farm.farmacia).trim()]);
  const nombreHtml = tieneLogoLocal
    ? ""
    : `<h3 class="cover-farm-name">${escapeHtml(farm.farmacia)}</h3>`;
  return `
    <button type="button" class="cover-farm-card" style="--pa-i:${idx % 12}"
      data-open-cover-farm="${escapeHtml(farm.farmacia)}"
      title="Ver medicamentos de ${escapeHtml(farm.farmacia)}">
      ${logoFarmaciaHtml(farm.farmacia, farm.pais)}
      ${nombreHtml}
      <p class="cover-farm-meta">
        <strong>${farm.skus}</strong> medicamento${farm.skus === 1 ? "" : "s"}
        · <strong>${farm.principios}</strong> principio${farm.principios === 1 ? "" : "s"}
      </p>
      <span class="cover-farm-cta">Ver medicamentos →</span>
    </button>`;
}

function renderCoverFarmGrid(farms) {
  if (!farms.length) return `<p class="muted cover-pa-empty">No hay farmacias con precio en este país.</p>`;
  return `<div class="cover-pa-grid cover-farm-grid" id="coverFarmGrid">${farms.map((f, i) => coverFarmCardHtml(f, i)).join("")}</div>`;
}

function coverPaTabsHtml({ nPa = 0, nFarms = 0, nMeds = 0, vista = "principios" }) {
  const on = (v) => (vista === v ? " is-on" : "");
  return `
    <div class="filter-chips cover-pa-cov-chips" role="group" aria-label="Vista del país">
      <button type="button" class="chip${on("principios")}" data-cover-pa-cov="principios">Principios (${nPa})</button>
      <button type="button" class="chip${on("farmacias")}" data-cover-pa-cov="farmacias">Farmacias (${nFarms})</button>
      <button type="button" class="chip chip--meds${on("medicamentos")}" data-cover-pa-cov="medicamentos">Medicamentos (${nMeds})</button>
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
      countEl.textContent = q
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

function openCoverListModal({ pais, titulo, badgeTexto, items, emptyText, tipo }) {
  const modal = $("coverListModal");
  const body = $("coverListBody");
  if (!modal || !body) return;
  modal.classList.remove("modal--fda");
  modal.classList.remove("modal--reg");
  modal.classList.add("modal--cover-pa");
  const listTipo = tipo || "todos";
  COVER_LIST_CACHE.tipo = listTipo;
  COVER_LIST_CACHE.q = "";
  COVER_LIST_CACHE.emptyText = emptyText || "";
  if (Array.isArray(items) && items.length) {
    COVER_LIST_CACHE.todos = items;
  }
  const nEn = (COVER_LIST_CACHE.todos || []).filter((x) => x.enFarmacia).length;
  const nSin = (COVER_LIST_CACHE.todos || []).length - nEn;
  const farms = farmaciasDelPais(pais.id);
  const rows = itemsCoverListActual();
  body.innerHTML = `
    <div class="modal-hero">
      <p class="crumb">Principios activos · lista completa</p>
      <h1 id="coverListTitle" class="modal-title-flag">${flagImg(pais.id, "cover-flag")} ${escapeHtml(titulo)}</h1>
      <div class="modal-hero-meta">
        <span class="badge ${badgeTexto.cls}">${escapeHtml(badgeTexto.label)}</span>
        <span id="coverPaCount">${rows.length} principio${rows.length === 1 ? "" : "s"}</span>
        <span>${nEn} en farmacia · ${nSin} sin precio</span>
        <span>${escapeHtml(pais.full)}</span>
      </div>
    </div>
    <div class="modal-body modal-body--cover modal-body--cover-pa">
      <div class="cover-pa-toolbar">
        <label class="filter-field cover-pa-search">
          <span>Filtrar principios</span>
          <input type="search" class="search" id="coverPaFilter" placeholder="Nombre, programa, farmacia o ejemplo…" autocomplete="off" />
        </label>
        ${coverPaTabsHtml({ nPa: rows.length, nFarms: farms.length, nMeds: 0, vista: "principios" })}
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
  const backFarm = state.coverFarmacia
    ? `<button type="button" class="modal-back" data-back-cover-farm-detail="${escapeHtml(state.coverFarmacia)}">← ${escapeHtml(state.coverFarmacia)}</button>`
    : `<p class="crumb">Detalle del producto</p>`;
  body.innerHTML = `
    <div class="modal-hero">
      ${backFarm}
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
        <article class="country-card"><h4>USD</h4><div class="price-lg">${usdVal != null ? money(usdVal) : "—"}</div></article>
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
  if (changingPais) {
    state.cpage = 1;
    state.cq = "";
    state.coverFarmacia = null;
    state.coverVista = "principios";
  }
  const madre = overlayComparativo();
  const base = filasTablaBase();
  const tiene = (n) => base.some((f) => f.n_lista === n && idPaisPorTexto(f.pais) === paisId);
  const encontrados = madre.filter((r) => tiene(r.n));
  const faltan = madre.filter((r) => !tiene(r.n));
  const filasPais = base.filter((f) => idPaisPorTexto(f.pais) === paisId);
  const farms = farmaciasDelPais(paisId);
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
  COVER_LIST_CACHE = {
    paisId: p.id,
    encontrados: encontradosItems,
    faltan: faltanItems,
    todos: [...encontradosItems, ...faltanItems],
    tipo: "todos",
    q: "",
    emptyText: "No hay principios activos en la lista.",
  };
  const vista = ["farmacias", "medicamentos"].includes(state.coverVista)
    ? state.coverVista
    : "principios";
  state.coverVista = vista;
  const rows = itemsCoverListActual();
  const crumb = vista === "farmacias"
    ? "Farmacias del país · lista DAMAC/FOMAC"
    : vista === "medicamentos"
      ? "Medicamentos · lista DAMAC/FOMAC"
      : "Principios activos · lista DAMAC/FOMAC";

  const modal = $("fichaModal");
  modal?.classList.add("modal--cover-pa");
  $("modalBody").innerHTML = `
    <div class="modal-hero">
      <p class="crumb">${crumb}</p>
      <h1 id="modalTitle" class="modal-title-flag">${flagImg(p.id, "cover-flag")} ${escapeHtml(p.full)}</h1>
      <div class="modal-hero-row">
        <div class="modal-hero-meta">
          <span id="coverPaCount">${madre.length} principios activos</span>
          <span>${encontrados.length} con precio · ${farms.length} farmacia${farms.length === 1 ? "" : "s"}</span>
          <span>${escapeHtml(farms.map((f) => f.farmacia).join(" · ") || "Sin farmacia")}</span>
        </div>
      </div>
    </div>
    <div class="modal-body modal-body--cover modal-body--cover-pa">
      <div class="cover-pa-toolbar${vista !== "principios" ? " cover-pa-toolbar--meds" : ""}">
        ${vista === "principios" ? `
        <label class="filter-field cover-pa-search">
          <span>Filtrar principios</span>
          <input type="search" class="search" id="coverPaFilter" placeholder="Nombre, programa, farmacia o ejemplo…" autocomplete="off" />
        </label>` : ""}
        ${coverPaTabsHtml({ nPa: madre.length, nFarms: farms.length, nMeds: filasPais.length, vista })}
      </div>
      ${vista === "principios"
        ? `<div class="cover-pa-scroll">
            ${renderCoverPaGrid(rows, "todos", COVER_LIST_CACHE.emptyText)}
            <p class="muted cover-pa-empty" id="coverPaFilterEmpty" hidden>Ningún principio coincide con el filtro.</p>
          </div>`
        : vista === "farmacias"
          ? `<div class="cover-pa-scroll">${renderCoverFarmGrid(farms)}</div>`
          : `<div class="sku-table">${filasTablaCoberturaPais(filasPais)}</div>`}
    </div>
  `;
  modal.hidden = false;
  modal.classList.add("is-open");
}

/** Modal secundario: medicamentos de una farmacia concreta (misma tabla que «Medicamentos»). */
function openCoverFarmModal(farmacia) {
  const paisId = state.coverPais || COVER_LIST_CACHE.paisId;
  const p = paisesUi().find((x) => x.id === paisId);
  const farmName = String(farmacia || "").trim();
  if (!p || !farmName) return;
  state.coverFarmacia = farmName;
  state.coverVista = "farmacias";
  if (!state.cq) state.cpage = 1;
  const filasFarm = filasTablaBase().filter(
    (f) => idPaisPorTexto(f.pais) === paisId && String(f.farmacia || "").trim() === farmName,
  );
  const meta = metaFuenteFarmacia(farmName, p.full);
  const modal = $("coverListModal");
  const body = $("coverListBody");
  if (!modal || !body) return;
  modal.classList.remove("modal--fda");
  modal.classList.remove("modal--reg");
  modal.classList.add("modal--cover-pa");
  body.innerHTML = `
    <div class="modal-hero">
      <button type="button" class="modal-back" data-back-cover-farm="${escapeHtml(p.id)}">
        ← Farmacias · ${escapeHtml(p.nombre)}
      </button>
      <h1 id="coverListTitle" class="modal-title-farm">
        ${escapeHtml(farmName)}
      </h1>
      <div class="modal-hero-meta">
        <span>${filasFarm.length} medicamento${filasFarm.length === 1 ? "" : "s"}</span>
        <span class="modal-title-flag" style="display:inline-flex;align-items:center;gap:8px">
          ${flagImg(p.id, "cover-flag")} ${escapeHtml(p.full)}
        </span>
        ${meta.link ? `<a href="${escapeHtml(meta.link)}" target="_blank" rel="noreferrer">Abrir catálogo ↗</a>` : ""}
      </div>
    </div>
    <div class="modal-body modal-body--cover modal-body--cover-pa">
      <div class="sku-table">${filasTablaCoberturaPais(filasFarm)}</div>
    </div>
  `;
  modal.hidden = false;
  modal.classList.add("is-open");
}

function repintarCoverActual() {
  if (state.coverFarmacia && $("coverListModal")?.classList.contains("is-open")) {
    openCoverFarmModal(state.coverFarmacia);
    return;
  }
  if (state.coverPais) openCoverModal(state.coverPais);
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
        ${row.par_comparable
          ? ``
          : `<span>Sin par comparable (misma concentración y presentación) entre países</span>`}
        `;
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
    <div class="modal-body modal-body--ficha">${bodyRest}</div>
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

/** Una sola clase principal del principio: Genérico | Biosimilar | Innovador. */
function clasePrincipalReg(info, opts = {}) {
  const fi = info || {};
  const emaInnovador = !!opts.emaInnovador;
  const tieneGen = !!(fi.tiene_generico || fi.tiene_generic);
  const tieneBio = !!fi.tiene_biosimilar;
  const tieneInn = !!(fi.tiene_referencia || emaInnovador);
  // Genérico (molécula pequeña) gana; si es biológico, Innovador > Biosimilar.
  if (!fi.es_biologico && tieneGen) return "generico";
  if (tieneInn) return "innovador";
  if (tieneBio) return "biosimilar";
  if (tieneGen) return "generico";
  return "";
}

function regChipPrincipal(info, opts = {}) {
  const c = clasePrincipalReg(info, opts);
  if (c === "generico") return `<span class="reg-chip is-gen">Genérico</span>`;
  if (c === "biosimilar") return `<span class="reg-chip is-bio">Biosimilar</span>`;
  if (c === "innovador") return regChipInnovador();
  return "";
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

/**
 * Recalcula el estado de una patente FDA respecto a HOY.
 * El snapshot guarda `estado` al día del scrape; sin esto la ficha queda desfasada
 * respecto a Alertas (que sí usan la fecha actual).
 */
function estadoPatenteHoy(p) {
  const exp = String(p?.expiration_date || "").slice(0, 10);
  const m = exp.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return String(p?.estado || "sin_fecha").toLowerCase() || "sin_fecha";
  const dExp = Date.UTC(+m[1], +m[2] - 1, +m[3]);
  const hoy = new Date();
  const dHoy = Date.UTC(hoy.getFullYear(), hoy.getMonth(), hoy.getDate());
  const dias = Math.round((dExp - dHoy) / 86400000);
  if (dias < 0) return "expirada";
  if (dias === 0) return "vence_hoy";
  return "vigente";
}

function patenteAunVigente(p) {
  const e = estadoPatenteHoy(p);
  return e === "vigente" || e === "vence_hoy";
}

function patenteConEstadoHoy(p) {
  return { ...p, estado: estadoPatenteHoy(p), estado_origen: p?.estado };
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

/** Búsqueda por nº de patente en Orange Book (fuente FDA). */
function urlOrangePatente(patentNo) {
  const pn = String(patentNo || "").replace(/,/g, "").trim().replace(/\*PED$/i, "");
  if (!pn) return "";
  return `${OB_SEARCH}results_patent.cfm?Patent_No=${encodeURIComponent(pn)}`;
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
  // Preferir siempre el Book FDA (no Google Patents).
  for (const key of ["patent_info_url", "fuente_url", "url_orange", "url_purple", "patent_url", "detalle_producto_url"]) {
    const u = String(p[key] || "").trim();
    if (u && /accessdata\.fda\.gov|purplebooksearch\.fda\.gov/i.test(u)) return u;
  }
  if (fuente === "purple_book" || p.bla_number) {
    const listPat = urlPurplePatentListPatente(p.patent_no);
    if (listPat) return listPat;
    const purple = urlPurpleProducto(p.bla_number);
    return purple || PURPLE_PATENT_LIST_URL;
  }
  if (p.appl_no) {
    const info = urlOrangePatentInfo(p.appl_type || "N", p.appl_no, p.product_no);
    if (info) return info;
    const prod = urlOrangeProductoAncla(p.appl_type || "N", p.appl_no, p.product_no, p.ob_anchor)
      || urlOrangeProducto(p.appl_type || "N", p.appl_no);
    if (prod) return prod;
  }
  const byPatent = urlOrangePatente(p.patent_no);
  if (byPatent) return byPatent;
  return OB_INDEX;
}

/** Enlace a la fuente FDA (Orange/Purple Book) de una alerta de patente. */
function urlFuenteAlertaPatente(a) {
  const d = a?.detalle || {};
  for (const key of ["patent_info_url", "fuente_url", "url", "url_orange", "url_purple"]) {
    const u = String(d[key] || "").trim();
    if (u && /accessdata\.fda\.gov|purplebooksearch\.fda\.gov/i.test(u)) return u;
  }
  return urlPatenteFda({
    fuente: d.fuente_patente || a?.fuente,
    patent_no: a?.patent_no,
    appl_no: d.appl_no || a?.clave_producto,
    appl_type: d.appl_type || "N",
    bla_number: d.bla_number,
    product_no: d.product_no || "001",
    patent_info_url: d.patent_info_url,
    fuente_url: d.fuente_url,
  });
}

/** Documento real de la patente (texto/claims) en Google Patents / USPTO. */
function urlDetalleDocumentoPatente(a) {
  const d = a?.detalle || {};
  const stored = String(d.google_patent_url || "").trim();
  if (stored) return stored;
  return urlGooglePatenteUs(a?.patent_no) || "";
}

function etiquetaFuenteBookAlerta(a) {
  const d = a?.detalle || {};
  const fuente = String(d.fuente_patente || a?.fuente || "").toLowerCase();
  if (fuente.includes("purple") || d.bla_number) return "Purple Book";
  return "Orange Book";
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
  const pats = (Array.isArray(patentes) ? patentes : []).map(patenteConEstadoHoy);
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
    vigentes: pats.filter((p) => patenteAunVigente(p)).length,
    expiradas: pats.filter((p) => estadoPatenteHoy(p) === "expirada").length,
    venceHoy: pats.filter((p) => estadoPatenteHoy(p) === "vence_hoy").length,
  };
}

function htmlResumenOrangeBook(info, patentes, productosFda) {
  const res = resumenPatentesOb(patentes, productosFda);
  const pats = Array.isArray(patentes) ? patentes : [];
  const nPb = pats.filter((p) => String(p.fuente || "").toLowerCase() === "purple_book").length;
  const nOb = pats.filter((p) => String(p.fuente || "").toLowerCase() === "orange_book").length;
  const ing = String(info?.medicamento_lista || "").trim();
  const bits = [];
  if (res.patentesUnicas) {
    bits.push(`<strong>${res.patentesUnicas}</strong> patente(s) distintas`);
    if (res.entradas && res.entradas !== res.patentesUnicas) {
      bits.push(`<strong>${res.entradas}</strong> entrada(s) en tabla`);
    }
  } else if (res.entradas) {
    bits.push(`<strong>${res.entradas}</strong> entrada(s) de patente`);
  }
  if (res.vigentes || res.expiradas) {
    bits.push(`<strong>${res.vigentes}</strong> vigente(s)`);
    if (res.venceHoy) bits.push(`<strong>${res.venceHoy}</strong> vence hoy`);
    bits.push(`<strong>${res.expiradas}</strong> expirada(s)`);
  }
  const cuenta = bits.length ? bits.join(" · ") : "Sin patentes en FDA";
  const fuenteLinks = [];
  if (nPb) fuenteLinks.push(linkFuente(PURPLE_PATENT_LIST_URL, "Purple Book · Patent List"));
  if (nOb) {
    fuenteLinks.push(linkFuente(OB_INDEX, "Orange Book"));
    if (ing) fuenteLinks.push(linkFuente(urlOrangeIngrediente(ing), "Búsqueda por ingrediente"));
  }
  if (!fuenteLinks.length) {
    fuenteLinks.push(linkFuente(PURPLE_PATENT_LIST_URL, "Purple Book"));
    fuenteLinks.push(linkFuente(OB_INDEX, "Orange Book"));
  }
  const fuentes = fuenteLinks.join(" · ");
  return `<p class="muted sku-note">${cuenta}. Estado recalculado a la fecha de hoy (misma lógica que Alertas). Una entrada = patente + aplicación (+ variante <code>*PED</code> si aplica). Fuentes: ${fuentes} · ${btnFdaPatentesHelp()}</p>`;
}

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

function urlFuenteDrugsAtFda(info, filas = []) {
  const pdfCandidates = [
    info?.fuente_indicaciones_pdf,
    ...(Array.isArray(info?.fuentes) ? info.fuentes.map((f) => f?.url) : []),
  ];
  const pdf = pdfCandidates
    .map((url) => String(url || "").trim())
    .find((url) => /accessdata\.fda\.gov\/drugsatfda_docs\/label\//i.test(url));

  if (pdf) {
    return pdf;
  }

  const aplicaciones = [
    ...(Array.isArray(info?.productos_fda) ? info.productos_fda : []),
    ...(Array.isArray(filas) ? filas : []),
  ];
  const referencia = aplicacionFdaReferencia(info, filas);
  if (referencia) {
    const bla = String(referencia.bla_number || "").match(/\d+/)?.[0] || "";
    if (bla) return `${DRUGS_AT_FDA}?event=overview.process&ApplNo=${encodeURIComponent(bla)}`;
    const at = String(referencia.appl_type || "").trim().toUpperCase();
    const an = padObApplNo(referencia.appl_no);
    if (at && an) return `${DRUGS_AT_FDA}?event=overview.process&ApplNo=${encodeURIComponent(an)}`;
  }

  // Respaldo para NDA/ANDA cuando no hay un BLA.
  for (const p of aplicaciones) {
    const at = String(p.appl_type || "").trim().toUpperCase();
    const an = padObApplNo(p.appl_no);
    if (at && an) {
      return `${DRUGS_AT_FDA}?event=overview.process&ApplNo=${encodeURIComponent(an)}`;
    }
  }

  return DRUGS_AT_FDA;
}

function aplicacionFdaReferencia(info, filas = []) {
  const productos = Array.isArray(info?.productos_fda) ? info.productos_fda : [];
  const filasFda = Array.isArray(filas) ? filas : [];
  const selectedApp = String(info?.fuente_indicaciones_drugsfda_app || "").trim().toUpperCase();
  if (selectedApp) {
    const selected = productos.find((p) => {
      const at = String(p?.appl_type || "").trim().toUpperCase();
      const normalizedAt = { N: "NDA", A: "ANDA" }[at] || at;
      const an = String(p?.appl_no || "").trim();
      return `${normalizedAt}${an}` === selectedApp || `BLA${String(p?.bla_number || "").trim()}` === selectedApp;
    });
    if (selected) return selected;
  }
  const combo = (value) => /\band\b|\+|;/.test(String(value || "").toLowerCase());
  const activo = String(info?.medicamento_lista || "")
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const esActivoExacto = (p) => {
    const ingrediente = String(p?.ingredient || p?.substance || "")
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    return Boolean(activo && ingrediente.includes(activo) && !combo(ingrediente));
  };
  const refProductos = productos.filter((p) =>
    ["marca_nda", "marca_bla", "referencia"].includes(String(p?.clase || "").toLowerCase())
    && esActivoExacto(p)
  );
  const refProductosFallback = productos.filter((p) =>
    ["marca_nda", "marca_bla", "referencia"].includes(String(p?.clase || "").toLowerCase())
    && !combo(p?.ingredient || p?.substance)
  );
  const refFilas = filasFda.filter((f) =>
    ["referencia", "351(a)", "innovador"].includes(String(f?.clase_producto || f?.tipo_licencia || "").toLowerCase())
    && !combo(f?.nombre_propio)
  );
  return (refProductos[0] || refProductosFallback[0] || refFilas[0] || productos[0] || filasFda[0] || null);
}

function urlDetalleDrugsAtFda(info, filas = []) {
  const p = aplicacionFdaReferencia(info, filas);
  if (p) {
    const bla = String(p?.bla_number || "").match(/\d+/)?.[0] || "";
    if (bla) return `${DRUGS_AT_FDA}?event=overview.process&ApplNo=${encodeURIComponent(bla)}`;
    const at = String(p?.appl_type || "").trim().toUpperCase();
    const an = padObApplNo(p?.appl_no);
    if (at && an) return `${DRUGS_AT_FDA}?event=overview.process&ApplNo=${encodeURIComponent(an)}`;
  }
  return "";
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

function htmlIndicacionesFda(info, filas = []) {
  const drugsUrl = urlFuenteDrugsAtFda(info, filas);
  const detalleUrl = urlDetalleDrugsAtFda(info, filas);
  if (!drugsUrl) {
    return `<p class="fda-ind-guide-missing muted">PDF de etiqueta no disponible en este snapshot.</p>`;
  }
  return `
    <div class="src-links fda-ind-guide-actions">
      ${linkFuenteChip(drugsUrl, "PDF etiqueta FDA (Drugs@FDA)", "fda")}
      ${detalleUrl ? linkFuenteChip(detalleUrl, "Detalle BLA/NDA", "fda") : ""}
    </div>`;
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
  const patentes = (Array.isArray(info?.patentes) ? info.patentes : []).map(patenteConEstadoHoy);
  const productosOb = Array.isArray(info?.productos_fda) ? info.productos_fda : [];
  const ind = !!(info?.indicaciones_uso || urlPdfIndicacionesFda(info) || urlFuenteDrugsAtFda(info, filas));
  const patsVig = patentes.filter((p) => patenteAunVigente(p));
  const patsExp = patentes.filter((p) => estadoPatenteHoy(p) === "expirada");
  const resumenOb = htmlResumenOrangeBook(info, patentes, productosOb);
  const taActivas = tentative.filter((t) => t.sigue_tentative);
  const taOtras = tentative.filter((t) => !t.sigue_tentative);
  const emaAuth = (Array.isArray(emaData?.filas) ? emaData.filas : [])
    .filter((f) => String(f.medicine_status || "").toLowerCase() === "authorised");

  const chip = regChipPrincipal(info);
  const chips = chip ? [chip] : [];
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

  const sec1 = ind ? htmlIndicacionesFda(info, filas) : "";

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
    : "";

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
  const chip = regChipPrincipal(info, { emaInnovador });
  if (chip) chips.push(chip);
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
  const fdaClaseMap = { generico: "Genérico", biosimilar: "Biosimilar", innovador: REG_LABEL_INNOVADOR };
  const fdaClase = fdaClaseMap[clasePrincipalReg(fi)] || regClaseDisplay(fi.resumen_clase || "—");
  const emaClase = fdaClaseMap[clasePrincipalReg(ei, { emaInnovador })] || "—";
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
  state.coverFarmacia = null;
  closeCoverListModal();
}

function animateStage() {
  const stage = $("stage");
  if (!stage) return;
  stage.classList.remove("is-entering");
  void stage.offsetWidth;
  stage.classList.add("is-entering");
}

const ALERTA_TIPO_LABEL = {
  paso_a_expirada: "Pasó a expirada",
  vence_hoy: "Vence hoy",
  vence_en_30d: "Vence en ≤30 días",
  vence_en_60d: "Vence en ≤60 días",
  vence_en_90d: "Vence en ≤90 días",
  vence_en_180d: "Vence en ≤6 meses",
  vence_en_365d: "Vence en ≤12 meses",
};

/** Ventana máxima de alertas “por vencer” (≈12 meses). */
const ALERTA_VENTANA_DIAS = 365;

function etiquetaTipoAlerta(tipo) {
  const t = String(tipo || "");
  if (t.startsWith("criterio_")) return "Según tu criterio";
  return ALERTA_TIPO_LABEL[t] || t || "—";
}

function horizonteEfectivoAlertas() {
  return ALERTA_VENTANA_DIAS;
}

/** Días restantes: usa el valor persistido si el cron/API lo actualizó hoy; si no, calcula. */
function diasRestantesAlerta(a) {
  const act = String(a?.dias_actualizado_en || "").slice(0, 10);
  const ahora = new Date();
  const hoyIso = `${ahora.getFullYear()}-${String(ahora.getMonth() + 1).padStart(2, "0")}-${String(ahora.getDate()).padStart(2, "0")}`;
  const stored = a?.dias_restantes;
  if (
    act === hoyIso &&
    stored != null &&
    stored !== "" &&
    Number.isFinite(Number(stored))
  ) {
    return Number(stored);
  }
  const exp = String(a?.expiration_date || "").slice(0, 10);
  const mExp = exp.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!mExp) return null;
  const dExp = Date.UTC(+mExp[1], +mExp[2] - 1, +mExp[3]);
  const dHoy = Date.UTC(ahora.getFullYear(), ahora.getMonth(), ahora.getDate());
  return Math.round((dExp - dHoy) / 86400000);
}

/** Texto de la columna Tipo: días exactos hasta vencer; filtros siguen usando tipo_alerta. */
function etiquetaTipoAlertaFila(a) {
  const tipo = a?.tipo_alerta || "";
  if (tipo === "paso_a_expirada") return "Pasó a expirada";

  const dias = diasRestantesAlerta(a);
  if (dias == null) return etiquetaTipoAlerta(tipo);

  if (dias === 0) return "Vence hoy";
  if (dias > 0) return `Vence en ${dias} día${dias === 1 ? "" : "s"}`;
  const atras = Math.abs(dias);
  return `Venció hace ${atras} día${atras === 1 ? "" : "s"}`;
}

/** Ya venció (historial): paso_a_expirada o expiration_date < hoy. */
function alertaEsVencida(a) {
  if ((a?.tipo_alerta || "") === "paso_a_expirada") return true;
  const dias = diasRestantesAlerta(a);
  return dias != null && dias < 0;
}

function configsPatentesActivas() {
  return (ALERTAS_DATA.configs || []).filter(
    (c) => c && (c.activo === 1 || c.activo === true || c.activo === "1"),
  );
}

/** Si hay criterios activos, solo alertas generadas por esos criterios (`criterio_{id}`). */
function alertaPatenteSegunCriterios(a) {
  const activas = configsPatentesActivas();
  if (!activas.length) return true;
  const tipo = String(a?.tipo_alerta || "");
  return activas.some((c) => tipo === `criterio_${c.id}`);
}

/** Alertas activas en el listado: por vencer / hoy (sin filtro de horizonte). */
function alertaEnVentanaActiva(a) {
  return !alertaEsVencida(a);
}

/** Historial de vencidas: independiente de criterios de alerta. */
function alertaEnHistorialVencidas(a) {
  return alertaEsVencida(a);
}

function filtrarAlertasBase(lista) {
  const fuente = ["fda", "ema"].includes(String(state.alertFuente || "").toLowerCase())
    ? String(state.alertFuente).toLowerCase()
    : "fda";
  return (lista || []).filter((a) => {
    if (String(a.fuente || "").toLowerCase() !== fuente) return false;
    if (state.alertTipo !== "todos" && (a.tipo_alerta || "") !== state.alertTipo) {
      return false;
    }
    if (state.alertSoloNuevas && Number(a.leida)) return false;
    return true;
  });
}

function ordenarAlertasActivas(lista) {
  return lista.slice().sort((a, b) => {
    const unreadA = Number(a?.leida) ? 1 : 0;
    const unreadB = Number(b?.leida) ? 1 : 0;
    if (unreadA !== unreadB) return unreadA - unreadB;
    const diasA = diasRestantesAlerta(a);
    const diasB = diasRestantesAlerta(b);
    if (diasA == null && diasB != null) return 1;
    if (diasA != null && diasB == null) return -1;
    if (diasA != null && diasB != null && diasA !== diasB) return diasA - diasB;
    return String(b?.fecha_alerta || "").localeCompare(String(a?.fecha_alerta || ""));
  });
}

function ordenarAlertasHistorial(lista) {
  const key = state.alertHistSort || "expiration_date";
  const dir = Number(state.alertHistDir) === 1 ? 1 : -1;
  return lista.slice().sort((a, b) => {
    let cmp = 0;
    if (key === "medicamento_lista") {
      cmp = String(a?.medicamento_lista || "").localeCompare(String(b?.medicamento_lista || ""), "es", { sensitivity: "base" });
    } else if (key === "patent_no") {
      cmp = String(a?.patent_no || "").localeCompare(String(b?.patent_no || ""), "es", { sensitivity: "base" });
    } else if (key === "estado") {
      cmp = String(etiquetaTipoAlertaFila(a) || "").localeCompare(String(etiquetaTipoAlertaFila(b) || ""), "es", { sensitivity: "base" });
    } else if (key === "fecha_alerta") {
      cmp = String(a?.fecha_alerta || "").localeCompare(String(b?.fecha_alerta || ""));
    } else {
      cmp = String(a?.expiration_date || "").localeCompare(String(b?.expiration_date || ""));
    }
    if (cmp !== 0) return cmp * dir;
    return String(b?.fecha_alerta || "").localeCompare(String(a?.fecha_alerta || ""));
  });
}

function alertHistSortMark(key) {
  if (state.alertHistSort !== key) return `<span class="ord">↕</span>`;
  return `<span class="ord">${Number(state.alertHistDir) === 1 ? "↑" : "↓"}</span>`;
}

function resetAlertasPaginacion() {
  state.alertActPage = 1;
  state.alertHistPage = 1;
}

function urgenciaAlerta(a) {
  const dias = diasRestantesAlerta(a);
  if (alertaEsVencida(a)) return "expired";
  if (dias == null) return "neutral";
  if (dias <= 0) return "critical";
  if (dias <= 7) return "critical";
  if (dias <= 30) return "warn";
  return "info";
}

function htmlCardAlertaPatente(a) {
  const tipo = a.tipo_alerta || "";
  const leida = Boolean(Number(a.leida));
  const urlBook = urlFuenteAlertaPatente(a);
  const urlDoc = urlDetalleDocumentoPatente(a);
  const bookLabel = etiquetaFuenteBookAlerta(a);
  const urg = urgenciaAlerta(a);
  const dias = diasRestantesAlerta(a);
  const etiqueta = etiquetaTipoAlertaFila(a);
  let diasHint = "";
  if (dias != null && dias > 0) diasHint = `${dias}d`;
  else if (dias === 0) diasHint = "Hoy";
  else if (dias != null && dias < 0) diasHint = `${Math.abs(dias)}d atrás`;

  return `
    <article class="alerta-card urg-${escapeHtml(urg)} ${leida ? "is-read" : "is-unread"}" data-alerta-id="${a.id}">
      <div class="alerta-card-accent" aria-hidden="true"></div>
      <div class="alerta-card-main">
        <div class="alerta-card-top">
          <div class="alerta-card-title-wrap">
            <h4 class="alerta-card-title">${escapeHtml(a.medicamento_lista || "Medicamento")}</h4>
            <p class="alerta-card-sub">n=${escapeHtml(a.n_lista)} · ${escapeHtml(String(a.fuente || "fda").toUpperCase())}</p>
          </div>
          <div class="alerta-card-status">
            <span class="alerta-pill alerta-pill--${escapeHtml(urg)}">${escapeHtml(etiqueta)}</span>
            ${diasHint ? `<span class="alerta-days">${escapeHtml(diasHint)}</span>` : ""}
          </div>
        </div>
        <div class="alerta-card-meta">
          <div class="alerta-meta-item">
            <span class="alerta-meta-label">Patente</span>
            <code>${escapeHtml(a.patent_no || "—")}</code>
          </div>
          <div class="alerta-meta-item">
            <span class="alerta-meta-label">Vence</span>
            <strong>${escapeHtml(fmtFecha(a.expiration_date) || "—")}</strong>
          </div>
          <div class="alerta-meta-item">
            <span class="alerta-meta-label">Detectada</span>
            <span>${escapeHtml(fmtFecha(a.fecha_alerta) || "—")}</span>
          </div>
          ${a.clave_producto ? `<div class="alerta-meta-item"><span class="alerta-meta-label">Producto</span><span>${escapeHtml(a.clave_producto)}</span></div>` : ""}
        </div>
        <div class="alerta-card-actions">
          ${urlBook ? `<a class="alerta-action" href="${escapeHtml(urlBook)}" target="_blank" rel="noreferrer">${escapeHtml(bookLabel)}</a>` : ""}
          ${urlDoc ? `<a class="alerta-action" href="${escapeHtml(urlDoc)}" target="_blank" rel="noreferrer">Documento</a>` : ""}
          ${leida
            ? `<button type="button" class="alerta-action alerta-action--ghost" data-alerta-unread="${a.id}">Marcar no leída</button>`
            : `<button type="button" class="alerta-action alerta-action--primary" data-alerta-read="${a.id}">Marcar leída</button>`}
        </div>
      </div>
    </article>`;
}

function htmlGridAlertasActivas(filas, emptyMsg) {
  if (!(filas || []).length) {
    return `<div class="alerta-empty"><p>${escapeHtml(emptyMsg)}</p></div>`;
  }
  return `<div class="alerta-cards">${filas.map(htmlCardAlertaPatente).join("")}</div>`;
}

function htmlFilaAlertaPatente(a) {
  const leida = Boolean(Number(a.leida));
  const urlBook = urlFuenteAlertaPatente(a);
  const urlDoc = urlDetalleDocumentoPatente(a);
  const bookLabel = etiquetaFuenteBookAlerta(a);
  const vencida = alertaEsVencida(a);
  const urg = urgenciaAlerta(a);
  return `
    <tr class="alerta-row ${leida ? "is-read" : "is-unread"} ${vencida ? "is-expired" : ""}" data-alerta-id="${a.id}">
      <td>${escapeHtml(fmtFecha(a.expiration_date) || "—")}</td>
      <td>
        <strong>${escapeHtml(a.medicamento_lista || "—")}</strong>
        <div class="muted">n=${escapeHtml(a.n_lista)}</div>
      </td>
      <td>
        <code>${escapeHtml(a.patent_no || "—")}</code>
        <div class="alerta-patente-links">
          ${urlBook ? `<a class="alerta-patente-link" href="${escapeHtml(urlBook)}" target="_blank" rel="noreferrer">${escapeHtml(bookLabel)}</a>` : ""}
          ${urlDoc ? `<a class="alerta-patente-link" href="${escapeHtml(urlDoc)}" target="_blank" rel="noreferrer">Documento</a>` : ""}
        </div>
      </td>
      <td><span class="alerta-pill alerta-pill--${escapeHtml(urg)}">${escapeHtml(etiquetaTipoAlertaFila(a))}</span></td>
      <td>${escapeHtml(fmtFecha(a.fecha_alerta) || "—")}</td>
      <td class="td-actions">
        ${leida
          ? `<button type="button" class="btn-ico" data-alerta-unread="${a.id}" title="Marcar no leída" aria-label="Marcar no leída">↩</button>`
          : `<button type="button" class="btn-ico is-mark-read" data-alerta-read="${a.id}" title="Marcar leída" aria-label="Marcar leída">✓</button>`}
      </td>
    </tr>`;
}

function htmlTablaAlertasPatentes(filas, emptyMsg) {
  const sort = state.alertHistSort || "expiration_date";
  const th = (key, label) =>
    `<th class="sortable ${sort === key ? "is-sorted" : ""}" data-alerta-hist-sort="${key}">${label} ${alertHistSortMark(key)}</th>`;
  const rows = (filas || []).map(htmlFilaAlertaPatente).join("");
  return `
    <div class="table-wrap alerta-hist-wrap">
      <table class="data alertas-table alertas-table--hist">
        <thead>
          <tr>
            ${th("expiration_date", "Venció")}
            ${th("medicamento_lista", "Medicamento")}
            ${th("patent_no", "Patente")}
            ${th("estado", "Estado")}
            ${th("fecha_alerta", "Registrada")}
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${rows || `<tr><td colspan="6" class="muted">${escapeHtml(emptyMsg)}</td></tr>`}
        </tbody>
      </table>
    </div>`;
}

function contarNoLeidasPatentes() {
  const filas = ALERTAS_DATA.filas || [];
  if (filas.length || ALERTAS_DATA.loaded) {
    return filas.filter((a) => alertaPatenteSegunCriterios(a) && !Number(a.leida)).length;
  }
  // Sin filas aún: si hay criterios, no usar el resumen global (incluye auto-detectadas).
  if (configsPatentesActivas().length) return 0;
  return Number(ALERTAS_DATA.resumen?.no_leidas || 0);
}

function contarNoLeidasPrecios() {
  const filas = ALERTAS_PRECIOS.filas || [];
  if (filas.length || ALERTAS_PRECIOS.loaded) {
    return filas.filter((a) => !Number(a.leida)).length;
  }
  return Number(ALERTAS_PRECIOS.resumen?.no_leidas || 0);
}

function actualizarBadgeAlertas(_resumen) {
  const n = contarNoLeidasPatentes() + contarNoLeidasPrecios();
  for (const el of [$("navAlertasBadge"), $("headerAlertBadge")]) {
    if (!el) continue;
    if (n > 0) {
      el.hidden = false;
      el.removeAttribute("hidden");
      el.textContent = n > 99 ? "99+" : String(n);
    } else {
      el.hidden = true;
      el.setAttribute("hidden", "");
      el.textContent = "";
    }
  }
}

function irAModuloAlertas(vista, opts = {}) {
  if (!opts.desdeToastCriterio) {
    state.alertFocusCriterioPat = null;
    state.alertFocusCriterioPre = null;
  }
  if (vista === "precios" || vista === "patentes") state.alertVista = vista;
  state.view = "alertas";
  syncRoute("alertas");
  render();
  if (state.alertVista === "precios") {
    cargarAlertasPrecios().then(() => {
      if (state.view === "alertas") renderAlertas({ soft: true });
    });
  } else {
    cargarAlertasPatentes().then(() => {
      if (state.view === "alertas") renderAlertas({ soft: true });
    });
  }
}

/** Entrada desde toast de un criterio: aplica filtro solo en esa visita. */
function irAAlertasDesdeToastCriterio(vista, cfgId) {
  const id = Number(cfgId);
  if (!Number.isFinite(id) || id <= 0) {
    irAModuloAlertas(vista);
    return;
  }
  if (vista === "precios") {
    state.alertFocusCriterioPre = id;
    state.alertFocusCriterioPat = null;
    state.alertVista = "precios";
    ALERTAS_PRECIOS.page = 1;
  } else {
    state.alertFocusCriterioPat = id;
    state.alertFocusCriterioPre = null;
    state.alertVista = "patentes";
    state.alertActPage = 1;
  }
  state.view = "alertas";
  syncRoute("alertas");
  render();
  const loader = vista === "precios" ? cargarAlertasPrecios() : cargarAlertasPatentes();
  loader.then(() => {
    if (state.view === "alertas") renderAlertas({ soft: true });
  });
}

function limpiarFiltroToastAlertas() {
  state.alertFocusCriterioPat = null;
  state.alertFocusCriterioPre = null;
  if (state.view === "alertas") renderAlertas({ soft: true });
}

function nombreCriterioPatente(c) {
  const n = String(c?.nombre || "").trim();
  return n || `Criterio #${c?.id ?? "—"}`;
}

function nombreCriterioPrecio(c) {
  const n = String(c?.nombre || "").trim();
  return n || `Criterio #${c?.id ?? "—"}`;
}

function htmlBannerFiltroToastCriterio({ vista, cfgId, nombre }) {
  return `
    <div class="alertas-focus-banner">
      <div>
        <strong>Filtro desde alerta</strong>
        <p class="muted">Mostrando ${vista === "precios" ? "alertas de precios" : "por vencer"} del criterio «${escapeHtml(nombre)}».</p>
      </div>
      <button type="button" class="btn-refresh btn-refresh--ghost" data-alert-focus-clear>Quitar filtro</button>
    </div>`;
}

function cerrarHeaderAlertas() {
  const panel = $("headerAlertPanel");
  const btn = $("headerAlertBtn");
  if (panel) panel.hidden = true;
  if (btn) btn.setAttribute("aria-expanded", "false");
}

function filasHeaderAlertasPatentes() {
  return (ALERTAS_DATA.filas || [])
    .filter((a) => alertaPatenteSegunCriterios(a) && alertaEnVentanaActiva(a))
    .slice()
    .sort((a, b) => {
      const unreadA = Number(a?.leida) ? 1 : 0;
      const unreadB = Number(b?.leida) ? 1 : 0;
      if (unreadA !== unreadB) return unreadA - unreadB;
      const diasA = diasRestantesAlerta(a);
      const diasB = diasRestantesAlerta(b);
      if (diasA == null && diasB != null) return 1;
      if (diasA != null && diasB == null) return -1;
      if (diasA != null && diasB != null && diasA !== diasB) return diasA - diasB;
      return String(b?.fecha_alerta || "").localeCompare(String(a?.fecha_alerta || ""));
    })
    .slice(0, 6);
}

function filasHeaderAlertasPrecios() {
  return (ALERTAS_PRECIOS.filas || [])
    .slice()
    .sort((a, b) => {
      const unreadA = Number(a?.leida) ? 1 : 0;
      const unreadB = Number(b?.leida) ? 1 : 0;
      if (unreadA !== unreadB) return unreadA - unreadB;
      return String(b?.fecha_alerta || "").localeCompare(String(a?.fecha_alerta || ""));
    })
    .slice(0, 6);
}

function htmlHeaderFilaPatente(a) {
  const tipo = etiquetaTipoAlertaFila(a);
  const leida = Boolean(Number(a?.leida));
  return `
    <button type="button" class="top-alerts-row ${leida ? "" : "is-unread"}" data-header-alert-go="patentes" data-header-alert-id="${escapeHtml(String(a.id || ""))}">
      <span class="top-alerts-row-main">
        <strong class="top-alerts-row-title">${escapeHtml(a.medicamento_lista || "—")}</strong>
        <span class="top-alerts-row-meta"><code>${escapeHtml(a.patent_no || "—")}</code> · ${escapeHtml(a.fuente ? String(a.fuente).toUpperCase() : "FDA")}</span>
      </span>
      <span class="top-alerts-row-side">
        <span class="badge alerta-tipo alerta-tipo--${escapeHtml(a.tipo_alerta || "")}">${escapeHtml(tipo)}</span>
      </span>
    </button>`;
}

function htmlHeaderFilaPrecio(a) {
  const baja = String(a.tipo_alerta || "") === "baja";
  const leida = Boolean(Number(a?.leida));
  const titulo = a.nombre_comercial || a.medicamento_lista || "—";
  const varN = Number(a.variacion_pct);
  const varTxt = Number.isFinite(varN) ? `${varN > 0 ? "+" : ""}${varN.toFixed(1)}%` : "—";
  return `
    <button type="button" class="top-alerts-row ${leida ? "" : "is-unread"}" data-header-alert-go="precios" data-header-alert-id="${escapeHtml(String(a.id || ""))}">
      <span class="top-alerts-row-main">
        <strong class="top-alerts-row-title">${escapeHtml(titulo)}</strong>
        <span class="top-alerts-row-meta">${escapeHtml(a.pais || "—")} · ${escapeHtml(a.farmacia || "—")}</span>
      </span>
      <span class="top-alerts-row-side">
        <span class="badge alerta-tipo alerta-tipo--${baja ? "baja" : "alza"}">${baja ? "Baja" : "Alza"} ${escapeHtml(varTxt)}</span>
      </span>
    </button>`;
}

function renderHeaderAlertas() {
  const body = $("headerAlertBody");
  const title = $("headerAlertTitle");
  if (!body) return;
  const tab = state.headerAlertTab === "precios" ? "precios" : "patentes";
  state.headerAlertTab = tab;
  const nPat = contarNoLeidasPatentes();
  const nPre = contarNoLeidasPrecios();
  if (title) title.textContent = "Alertas";

  const tabsHtml = `
    <div class="top-alerts-tabs" role="tablist" aria-label="Tipo de alerta">
      <button type="button" class="top-alerts-tab ${tab === "patentes" ? "is-on" : ""}" data-header-alert-tab="patentes" role="tab" aria-selected="${tab === "patentes"}">
        Patentes${nPat ? `<span class="top-alerts-tab-n">${nPat > 99 ? "99+" : nPat}</span>` : ""}
      </button>
      <button type="button" class="top-alerts-tab ${tab === "precios" ? "is-on" : ""}" data-header-alert-tab="precios" role="tab" aria-selected="${tab === "precios"}">
        Precios${nPre ? `<span class="top-alerts-tab-n">${nPre > 99 ? "99+" : nPre}</span>` : ""}
      </button>
    </div>`;

  let listHtml = "";
  if (tab === "patentes") {
    if (ALERTAS_DATA.cargando && !(ALERTAS_DATA.filas || []).length) {
      listHtml = `<p class="muted">Cargando alertas…</p>`;
    } else if (ALERTAS_DATA.error && !(ALERTAS_DATA.filas || []).length) {
      listHtml = `<p class="note note--warn">${escapeHtml(ALERTAS_DATA.error)}</p>`;
    } else {
      const filas = filasHeaderAlertasPatentes();
      if (!filas.length) {
        const hayCfg = configsPatentesActivas().length > 0;
        listHtml = `<p class="muted top-alerts-empty">${
          hayCfg
            ? "No hay patentes por vencer que coincidan con tus criterios activos."
            : "No hay patentes por vencer. Configurá criterios en Alertas → Patentes (tuerca)."
        }</p>`;
      } else {
        listHtml = filas.map(htmlHeaderFilaPatente).join("");
      }
    }
  } else if (ALERTAS_PRECIOS.cargando && !ALERTAS_PRECIOS.loaded) {
    listHtml = `<p class="muted">Cargando alertas…</p>`;
  } else if (ALERTAS_PRECIOS.error && !ALERTAS_PRECIOS.loaded) {
    listHtml = `<p class="note note--warn">${escapeHtml(ALERTAS_PRECIOS.error)}</p>`;
  } else {
    const filas = filasHeaderAlertasPrecios();
    if (!filas.length) {
      const hayCfg = (ALERTAS_PRECIOS.configs || []).some((c) => Number(c.activo));
      listHtml = `<p class="muted top-alerts-empty">${
        hayCfg
          ? "No hay alertas de precio disparadas todavía."
          : "Configurá criterios en Alertas → Precios (tuerca)."
      }</p>`;
    } else {
      listHtml = filas.map(htmlHeaderFilaPrecio).join("");
    }
  }

  body.innerHTML = `${tabsHtml}<div class="top-alerts-list">${listHtml}</div>`;
  actualizarBadgeAlertas();
}

function toggleHeaderAlertas(force) {
  const panel = $("headerAlertPanel");
  const btn = $("headerAlertBtn");
  if (!panel || !btn) return;
  const next = typeof force === "boolean" ? force : panel.hidden;
  panel.hidden = !next;
  btn.setAttribute("aria-expanded", next ? "true" : "false");
  if (!next) return;
  renderHeaderAlertas();
  const loads = [];
  if (!(ALERTAS_DATA.filas || []).length && !ALERTAS_DATA.cargando) {
    loads.push(cargarAlertasPatentes({ silent: true }));
  }
  if (!ALERTAS_PRECIOS.loaded && !ALERTAS_PRECIOS.cargando) {
    loads.push(cargarAlertasPrecios({ silent: true }));
  }
  if (loads.length) {
    Promise.all(loads).then(() => renderHeaderAlertas());
  }
}

function hoyIsoLocal() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function claveToastPatenteDia(a) {
  const pn = String(a?.patent_no || "").replace(/,/g, "").trim();
  const exp = String(a?.expiration_date || "").slice(0, 10);
  return `mac_patente_toast_${pn}_${exp}`;
}

function toastPatenteYaMostrado(a) {
  try {
    return localStorage.getItem(claveToastPatenteDia(a)) === "1";
  } catch (_) {
    return false;
  }
}

function marcarToastPatenteMostrado(a) {
  try {
    localStorage.setItem(claveToastPatenteDia(a), "1");
  } catch (_) { /* ignore */ }
}

function asegurarHostToastsAlertas() {
  let host = $("alertToastHost");
  if (host) return host;
  const legacy = $("patenteToastHost");
  if (legacy) {
    legacy.id = "alertToastHost";
    legacy.className = "alert-toast-host";
    return legacy;
  }
  host = document.createElement("div");
  host.id = "alertToastHost";
  host.className = "alert-toast-host";
  host.setAttribute("aria-live", "polite");
  document.body.appendChild(host);
  return host;
}

/** Notificación tipo card en la esquina inferior derecha. */
function mostrarToastAlerta({
  titulo = "Alerta",
  texto = "",
  meta = "",
  kind = "info",
  duracionMs = 12000,
  accionLabel = "Ver alertas",
  onAccion = null,
} = {}) {
  const host = asegurarHostToastsAlertas();
  const el = document.createElement("aside");
  el.className = `alert-toast alert-toast--${escapeHtml(kind)}`;
  el.setAttribute("role", "status");
  const ico = kind === "precio"
    ? `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3v18"/><path d="M16 7H9.5a2.5 2.5 0 0 0 0 5H14a2.5 2.5 0 0 1 0 5H7"/></svg>`
    : `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></svg>`;
  el.innerHTML = `
    <div class="alert-toast-ico" aria-hidden="true">${ico}</div>
    <div class="alert-toast-body">
      <strong>${escapeHtml(titulo)}</strong>
      ${texto ? `<p>${escapeHtml(texto)}</p>` : ""}
      ${meta ? `<p class="alert-toast-meta">${escapeHtml(meta)}</p>` : ""}
      <div class="alert-toast-actions">
        <button type="button" class="btn-link" data-toast-alertas>${escapeHtml(accionLabel)}</button>
      </div>
    </div>
    <button type="button" class="alert-toast-close" data-toast-close aria-label="Cerrar">×</button>
  `;
  const cerrar = () => {
    el.classList.add("is-out");
    window.setTimeout(() => el.remove(), 280);
  };
  el.querySelector("[data-toast-close]")?.addEventListener("click", cerrar);
  el.querySelector("[data-toast-alertas]")?.addEventListener("click", () => {
    if (typeof onAccion === "function") onAccion();
    else irAModuloAlertas("patentes");
    cerrar();
  });
  host.appendChild(el);
  requestAnimationFrame(() => el.classList.add("is-in"));
  if (duracionMs > 0) window.setTimeout(cerrar, duracionMs);
  return el;
}

function mostrarToastPatenteExpirada(a) {
  const med = a?.medicamento_lista || "Medicamento";
  const pn = a?.patent_no || "—";
  mostrarToastAlerta({
    titulo: "Patente venció hoy",
    texto: med,
    meta: `${pn} · FDA Orange Book`,
    kind: "patente",
    duracionMs: 16000,
    onAccion: () => irAModuloAlertas("patentes"),
  });
}

function intervaloMinutosCriterio(c) {
  const m = Number(c?.intervalo_minutos);
  if (Number.isFinite(m) && m >= 1) return Math.min(43200, Math.floor(m));
  const h = Number(c?.intervalo_horas);
  if (Number.isFinite(h) && h >= 1) return Math.min(43200, Math.floor(h) * 60);
  return 1440;
}

function unidadIntervaloCriterio(c) {
  const u = String(c?.intervalo_unidad || "").trim().toLowerCase();
  return u === "minutos" || u === "min" || u === "m" ? "minutos" : "horas";
}

function valorIntervaloParaForm(c) {
  const mins = intervaloMinutosCriterio(c);
  const unidad = unidadIntervaloCriterio(c);
  if (unidad === "minutos") return String(mins);
  return String(Math.max(1, Math.round(mins / 60)));
}

function etiquetaIntervaloCriterio(c) {
  const mins = intervaloMinutosCriterio(c);
  const unidad = unidadIntervaloCriterio(c);
  if (unidad === "minutos") return `cada ${mins} min`;
  const h = Math.max(1, Math.round(mins / 60));
  return `cada ${h} h`;
}

function claveUiNotifyPat(cfgId) {
  return `mac_pat_ui_notify_v1_${cfgId}`;
}

/** Última notificación UI en este navegador (no se reinicia al recargar). */
function ultimaUiNotifyPatMs(cfg) {
  try {
    const local = Number(localStorage.getItem(claveUiNotifyPat(cfg.id)) || 0) || 0;
    if (local > 0) return local;
  } catch (_) { /* ignore */ }
  const server = Date.parse(String(cfg?.ultima_notificacion_en || "").replace(" ", "T"));
  return Number.isFinite(server) ? server : 0;
}

function criterioUiNotifyDue(cfg) {
  const last = ultimaUiNotifyPatMs(cfg);
  if (!last) return true;
  const everyMs = intervaloMinutosCriterio(cfg) * 60 * 1000;
  return Date.now() - last >= everyMs;
}

function marcarUiNotifyPatentes(cfgIds) {
  const ids = [...new Set((cfgIds || []).map((x) => Number(x)).filter((n) => Number.isFinite(n) && n > 0))];
  if (!ids.length) return Promise.resolve(false);
  const now = Date.now();
  for (const id of ids) {
    try {
      localStorage.setItem(claveUiNotifyPat(id), String(now));
    } catch (_) { /* ignore */ }
  }
  return fetch("/api/alertas/patentes/configs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ accion: "reasaltar", ids }),
  })
    .then((r) => r.json())
    .then(async (data) => {
      if (!data?.ok) return false;
      const stamp = new Date().toISOString().slice(0, 19);
      for (const c of ALERTAS_DATA.configs || []) {
        if (ids.includes(Number(c.id))) c.ultima_notificacion_en = stamp;
      }
      // Recargar filas para que el badge cuente las no leídas.
      await cargarAlertasPatentes({ silent: true });
      actualizarBadgeAlertas();
      renderHeaderAlertas();
      if (state.view === "alertas") renderAlertas({ soft: true });
      return true;
    })
    .catch(() => false);
}

function configsPatentesConMatchesUi() {
  const matches = filasHeaderAlertasPatentes();
  const tipos = new Set(matches.map((a) => String(a?.tipo_alerta || "")));
  return configsPatentesActivas().filter((c) => tipos.has(`criterio_${c.id}`));
}

/**
 * Un toast por criterio (no por patente). Click → Alertas/Patentes con filtro POR VENCER del criterio.
 * @param {{ nuevas?: number, mensaje?: string, forzar?: boolean }} opts
 */
function mostrarToastsCriteriosPatentes({ nuevas = 0, mensaje = "", forzar = false } = {}) {
  const nCfg = configsPatentesActivas().length;
  if (!nCfg) {
    if (forzar) {
      mostrarToastAlerta({
        titulo: "Sin criterios activos",
        texto: "Configurá criterios con la tuerca para recibir notificaciones de patentes.",
        kind: "info",
        duracionMs: 10000,
      });
    }
    return false;
  }
  const conMatch = configsPatentesConMatchesUi();
  const due = forzar ? conMatch : conMatch.filter(criterioUiNotifyDue);
  if (!due.length) {
    if (forzar && !conMatch.length) {
      mostrarToastAlerta({
        titulo: "Criterios evaluados",
        texto: mensaje || "Ninguna patente coincide ahora con tus criterios.",
        kind: "info",
        duracionMs: 10000,
      });
    }
    return false;
  }

  const nNuevas = Number(nuevas) || 0;
  due.forEach((c, i) => {
    const matches = filasHeaderAlertasPatentes().filter(
      (a) => String(a?.tipo_alerta || "") === `criterio_${c.id}`,
    );
    const n = matches.length;
    const nombre = nombreCriterioPatente(c);
    window.setTimeout(() => {
      mostrarToastAlerta({
        titulo: nombre,
        texto: nNuevas > 0 && i === 0
          ? (mensaje || `${n} patente${n === 1 ? "" : "s"} por vencer según este criterio.`)
          : `${n} patente${n === 1 ? "" : "s"} por vencer · aviso ${etiquetaIntervaloCriterio(c).replace(/^cada\s+/i, "")}.`,
        kind: "patente",
        duracionMs: 14000,
        onAccion: () => irAAlertasDesdeToastCriterio("patentes", c.id),
      });
    }, 220 * i);
  });

  marcarUiNotifyPatentes(due.map((c) => c.id));
  return true;
}

function configsPreciosActivas() {
  return (ALERTAS_PRECIOS.configs || []).filter(
    (c) => c && (c.activo === 1 || c.activo === true || c.activo === "1"),
  );
}

function filasPreciosDeConfig(cfgId) {
  const id = Number(cfgId);
  return (ALERTAS_PRECIOS.filas || []).filter((a) => Number(a?.config_id) === id);
}

function configsPreciosConMatchesUi() {
  return configsPreciosActivas().filter((c) => filasPreciosDeConfig(c.id).length > 0);
}

function claveUiNotifyPre(cfgId) {
  return `mac_pre_ui_notify_v1_${cfgId}`;
}

function ultimaUiNotifyPreMs(cfg) {
  try {
    const local = Number(localStorage.getItem(claveUiNotifyPre(cfg.id)) || 0) || 0;
    if (local > 0) return local;
  } catch (_) { /* ignore */ }
  const server = Date.parse(String(cfg?.ultima_notificacion_en || "").replace(" ", "T"));
  return Number.isFinite(server) ? server : 0;
}

function criterioUiNotifyDuePrecio(cfg) {
  const last = ultimaUiNotifyPreMs(cfg);
  if (!last) return true;
  return Date.now() - last >= intervaloMinutosCriterio(cfg) * 60 * 1000;
}

function marcarUiNotifyPrecios(cfgIds) {
  const ids = [...new Set((cfgIds || []).map((x) => Number(x)).filter((n) => Number.isFinite(n) && n > 0))];
  if (!ids.length) return Promise.resolve(false);
  const now = Date.now();
  for (const id of ids) {
    try {
      localStorage.setItem(claveUiNotifyPre(id), String(now));
    } catch (_) { /* ignore */ }
  }
  return fetch("/api/alertas/precios/configs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ accion: "reasaltar", ids }),
  })
    .then((r) => r.json())
    .then(async (data) => {
      if (!data?.ok) return false;
      const stamp = new Date().toISOString().slice(0, 19);
      for (const c of ALERTAS_PRECIOS.configs || []) {
        if (ids.includes(Number(c.id))) c.ultima_notificacion_en = stamp;
      }
      await cargarAlertasPrecios({ silent: true });
      actualizarBadgeAlertas();
      renderHeaderAlertas();
      if (state.view === "alertas") renderAlertas({ soft: true });
      return true;
    })
    .catch(() => false);
}

/** Un toast por criterio de precios. Click → Alertas/Precios filtrado a ese criterio. */
function mostrarToastsCriteriosPrecios({ nuevas = 0, mensaje = "", forzar = false } = {}) {
  const nCfg = configsPreciosActivas().length;
  if (!nCfg) {
    if (forzar) {
      mostrarToastAlerta({
        titulo: "Sin criterios activos",
        texto: "Configurá criterios de precios con la tuerca para recibir notificaciones.",
        kind: "info",
        duracionMs: 10000,
      });
    }
    return false;
  }
  const conMatch = configsPreciosConMatchesUi();
  const due = forzar ? conMatch : conMatch.filter(criterioUiNotifyDuePrecio);
  if (!due.length) {
    if (forzar && !conMatch.length) {
      mostrarToastAlerta({
        titulo: "Criterios evaluados",
        texto: mensaje || "Ningún precio coincide ahora con tus criterios.",
        kind: "info",
        duracionMs: 10000,
      });
    }
    return false;
  }
  const nNuevas = Number(nuevas) || 0;
  due.forEach((c, i) => {
    const n = filasPreciosDeConfig(c.id).length;
    const nombre = nombreCriterioPrecio(c);
    window.setTimeout(() => {
      mostrarToastAlerta({
        titulo: nombre,
        texto: nNuevas > 0 && i === 0
          ? (mensaje || `${n} alerta${n === 1 ? "" : "s"} de precio según este criterio.`)
          : `${n} alerta${n === 1 ? "" : "s"} de precio · aviso ${etiquetaIntervaloCriterio(c).replace(/^cada\s+/i, "")}.`,
        kind: "info",
        duracionMs: 14000,
        onAccion: () => irAAlertasDesdeToastCriterio("precios", c.id),
      });
    }, 220 * i);
  });
  marcarUiNotifyPrecios(due.map((c) => c.id));
  return true;
}

/** Al entrar / recargar / reloj: solo notifica si ya pasó el intervalo guardado. */
function revisarNotificacionesUiPatentes() {
  if (!ALERTAS_DATA.loaded) return;
  if (!configsPatentesActivas().length) return;
  if (!filasHeaderAlertasPatentes().length) return;
  mostrarToastsCriteriosPatentes({ forzar: false });
}

function revisarNotificacionesUiPrecios() {
  if (!ALERTAS_PRECIOS.loaded) return;
  if (!configsPreciosActivas().length) return;
  if (!configsPreciosConMatchesUi().length) return;
  mostrarToastsCriteriosPrecios({ forzar: false });
}

let PAT_UI_NOTIFY_TIMER = null;
let PAT_UI_NOTIFY_TICKING = false;
let PAT_UI_NOTIFY_VIS_BOUND = false;

/** Cada cuánto revisar el reloj (mín. 10s; ~½ del intervalo más corto). */
function periodoRelojUiPatMs() {
  const mins = [
    ...configsPatentesActivas().map(intervaloMinutosCriterio),
    ...configsPreciosActivas().map(intervaloMinutosCriterio),
  ];
  if (!mins.length) return 30000;
  const half = Math.min(...mins) * 30 * 1000;
  return Math.max(10000, Math.min(30000, half || 10000));
}

async function tickNotificacionesUiPatentes() {
  if (PAT_UI_NOTIFY_TICKING) return;
  if (document.visibilityState === "hidden") return;
  PAT_UI_NOTIFY_TICKING = true;
  try {
    await Promise.all([
      fetch("/api/alertas/patentes/configs", { cache: "no-store" })
        .then((r) => r.json())
        .then((data) => {
          if (data?.ok && Array.isArray(data.configs)) ALERTAS_DATA.configs = data.configs;
        })
        .catch(() => {}),
      fetch("/api/alertas/precios/configs", { cache: "no-store" })
        .then((r) => r.json())
        .then((data) => {
          if (data?.ok && Array.isArray(data.configs)) ALERTAS_PRECIOS.configs = data.configs;
        })
        .catch(() => {}),
      cargarAlertasPatentes({ silent: true }).catch(() => {}),
      cargarAlertasPrecios({ silent: true }).catch(() => {}),
    ]);
    actualizarBadgeAlertas();
    revisarNotificacionesUiPatentes();
    revisarNotificacionesUiPrecios();
  } finally {
    PAT_UI_NOTIFY_TICKING = false;
  }
}

function arrancarRelojNotificacionesUiPatentes() {
  if (PAT_UI_NOTIFY_TIMER) {
    window.clearInterval(PAT_UI_NOTIFY_TIMER);
    PAT_UI_NOTIFY_TIMER = null;
  }
  const period = periodoRelojUiPatMs();
  PAT_UI_NOTIFY_TIMER = window.setInterval(() => {
    tickNotificacionesUiPatentes().catch(() => {});
  }, period);
  if (!PAT_UI_NOTIFY_VIS_BOUND) {
    PAT_UI_NOTIFY_VIS_BOUND = true;
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") {
        tickNotificacionesUiPatentes().catch(() => {});
      }
    });
  }
}

async function revisarToastsPatentesExpiradasHoy() {
  const hoy = hoyIsoLocal();
  let filas = [];
  try {
    const r = await fetch("/api/alertas/patentes?limite=500", { cache: "no-store" });
    const data = await r.json();
    if (data?.ok && Array.isArray(data.filas)) filas = data.filas;
  } catch (_) {
    return;
  }
  const vistos = new Set();
  for (const a of filas) {
    const exp = String(a?.expiration_date || "").slice(0, 10);
    if (exp !== hoy) continue;
    const pn = String(a?.patent_no || "").trim();
    if (!pn || vistos.has(pn)) continue;
    vistos.add(pn);
    if (toastPatenteYaMostrado(a)) continue;
    marcarToastPatenteMostrado(a);
    mostrarToastPatenteExpirada(a);
  }
}

async function cargarAlertasPatentes({ silent = false } = {}) {
  if (!silent) ALERTAS_DATA.cargando = true;
  ALERTAS_DATA.error = null;
  renderHeaderAlertas();
  try {
    const params = new URLSearchParams();
    if (state.alertFuente === "ema") params.set("fuente", "ema");
    else params.set("fuente", "fda");
    // Tipo se filtra en cliente para poder llenar «por vencer» + historial en la misma carga.
    if (state.alertSoloNuevas) params.set("solo_no_leidas", "1");
    params.set("limite", "1000");
    const r = await fetch(`/api/alertas/patentes?${params}`, { cache: "no-store" });
    const data = await r.json();
    if (!data?.ok) throw new Error(data?.error || "No se pudieron cargar alertas");
    ALERTAS_DATA.filas = Array.isArray(data.filas) ? data.filas : [];
    ALERTAS_DATA.resumen = data.resumen || {};
    ALERTAS_DATA.configs = Array.isArray(data.configs) ? data.configs : (ALERTAS_DATA.configs || []);
    if (data.opciones_criterios) ALERTAS_DATA.opcionesCriterios = data.opciones_criterios;
    ALERTAS_DATA.loaded = true;
    actualizarBadgeAlertas();
    renderHeaderAlertas();
  } catch (err) {
    ALERTAS_DATA.error = err?.message || String(err);
    ALERTAS_DATA.filas = [];
    renderHeaderAlertas();
  } finally {
    ALERTAS_DATA.cargando = false;
    actualizarBadgeAlertas();
    renderHeaderAlertas();
  }
  return ALERTAS_DATA;
}

async function refrescarResumenAlertas() {
  try {
    await Promise.all([
      cargarAlertasPatentes({ silent: true }),
      cargarAlertasPrecios({ silent: true }),
    ]);
  } catch (_) { /* ignore */ }
  actualizarBadgeAlertas();
  renderHeaderAlertas();
  // Solo si ya venció el intervalo guardado (localStorage + BD).
  window.setTimeout(() => {
    revisarNotificacionesUiPatentes();
    revisarNotificacionesUiPrecios();
  }, 700);
}

function alertaVistaTabsHtml() {
  const tabs = [
    ["patentes", "Patentes", "Vencimientos de patentes FDA"],
    ["precios", "Precios", "Cambios relevantes de precio entre mercados"],
  ];
  if (!tabs.some(([id]) => id === state.alertVista)) state.alertVista = "patentes";
  return `
    <div class="tend-vista-tabs alertas-vista-tabs" role="tablist" aria-label="Tipos de alerta">
      ${tabs.map(([id, label, hint]) => `
        <button type="button" role="tab" class="tend-vista-tab${state.alertVista === id ? " is-active" : ""}"
          data-alerta-vista="${id}" aria-selected="${state.alertVista === id}" title="${escapeHtml(hint)}">
          ${escapeHtml(label)}
        </button>`).join("")}
    </div>`;
}

function htmlAlertasPanelPlaceholder({ kicker, title, lead, points }) {
  const lista = (points || [])
    .map((p) => `<li>${escapeHtml(p)}</li>`)
    .join("");
  return `
    <header class="alertas-hero alertas-hero--compact">
      <div class="alertas-hero-copy">
        <p class="alertas-kicker">${escapeHtml(kicker)}</p>
        <h2>${escapeHtml(title)}</h2>
        <p class="alertas-lead">${escapeHtml(lead)}</p>
      </div>
    </header>
    <section class="alertas-section">
      <div class="alerta-empty alerta-empty--panel">
        <p class="alerta-empty-title">Pronto en este espacio</p>
        <p>Estamos preparando este tipo de alertas. Cuando estén disponibles verás aquí:</p>
        <ul class="alerta-empty-list">${lista}</ul>
      </div>
    </section>`;
}

function htmlAlertasExclusividadesBody() {
  return htmlAlertasPanelPlaceholder({
    kicker: "FDA · Orange Book / Purple Book",
    title: "Exclusividades",
    lead: "Seguimiento del fin de exclusividades regulatorias que pueden abrir la puerta a competencia.",
    points: [
      "Exclusividades próximas a vencer y las que ya vencieron",
      "Principios activos de la lista con ventana regulatoria por cerrar",
      "Enlaces a la ficha FDA para revisar el detalle",
    ],
  });
}

function fmtUsdAlerta(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return usd.format(n);
}

function textoCriterioPrecio(c) {
  const prod = c.nombre_comercial || c.medicamento_lista
    || (c.producto_key ? `Producto ${c.producto_key}` : null)
    || (c.n_lista != null ? `Principio #${c.n_lista}` : "Todos los medicamentos");
  const bits = [prod];
  bits.push(c.pais || "Todos los países");
  bits.push(c.farmacia || "Todas las farmacias");
  bits.push(c.presentacion || "Todas las presentaciones");
  bits.push(c.concentracion || "Todas las concentraciones");
  const umb = [];
  if (c.umbral_baja_pct != null && c.umbral_baja_pct !== "") umb.push(`baja ≥ ${c.umbral_baja_pct}%`);
  if (c.umbral_sube_pct != null && c.umbral_sube_pct !== "") umb.push(`alza ≥ ${c.umbral_sube_pct}%`);
  return { alcance: bits.join(" · "), umbrales: umb.join(" · ") || "Sin umbral" };
}

function htmlCardConfigPrecio(c) {
  const t = textoCriterioPrecio(c);
  const activa = Boolean(Number(c.activo));
  return `
    <article class="ap-config-card ${activa ? "is-on" : "is-off"}" data-ap-config-id="${c.id}">
      <div class="ap-config-top">
        <div>
          <h4>${escapeHtml(c.nombre || c.nombre_comercial || t.alcance.split(" · ")[0] || "Criterio")}</h4>
          <p class="muted">${escapeHtml(t.alcance)}</p>
        </div>
        <span class="ap-config-badge ${activa ? "is-on" : ""}">${activa ? "Activa" : "Pausada"}</span>
      </div>
      <p class="ap-config-umb">${escapeHtml(t.umbrales)} · UI ${escapeHtml(etiquetaIntervaloCriterio(c))}</p>
      <div class="ap-config-actions">
        <button type="button" class="alerta-action" data-ap-edit="${c.id}">Editar</button>
        <button type="button" class="alerta-action" data-ap-toggle="${c.id}" data-ap-activo="${activa ? "0" : "1"}">
          ${activa ? "Pausar" : "Activar"}
        </button>
        <button type="button" class="alerta-action alerta-action--ghost" data-ap-del="${c.id}">Eliminar</button>
      </div>
    </article>`;
}

function htmlFilaAlertaPrecio(a) {
  const baja = String(a.tipo_alerta || "") === "baja";
  const varN = Number(a.variacion_pct);
  const varTxt = Number.isFinite(varN)
    ? `${varN > 0 ? "+" : ""}${varN.toFixed(1)}%`
    : "—";
  const leida = Boolean(Number(a.leida));
  const titulo = a.nombre_comercial || a.medicamento_lista || "—";
  return `
    <tr class="alerta-row ${leida ? "is-read" : "is-unread"}">
      <td>${escapeHtml(fmtFecha(a.fecha_alerta) || "—")}</td>
      <td>
        <strong>${escapeHtml(titulo)}</strong>
        <div class="muted">${escapeHtml(a.medicamento_lista && a.nombre_comercial ? a.medicamento_lista : "")}</div>
        <div class="muted">${escapeHtml(a.pais || "—")} · ${escapeHtml(a.farmacia || "—")}</div>
      </td>
      <td>
        <div class="muted">${escapeHtml(a.presentacion || "Todas")}</div>
        <div class="muted">${escapeHtml(a.concentracion || "Todas")}</div>
      </td>
      <td>
        <span class="alerta-pill alerta-pill--${baja ? "warn" : "critical"}">${baja ? "Baja" : "Alza"}</span>
        <strong class="ap-var ${baja ? "is-down" : "is-up"}">${escapeHtml(varTxt)}</strong>
      </td>
      <td>
        <div>${escapeHtml(fmtUsdAlerta(a.precio_anterior_usd))} → ${escapeHtml(fmtUsdAlerta(a.precio_nuevo_usd))}</div>
        <div class="muted">umbral ${escapeHtml(a.umbral_pct != null ? `${a.umbral_pct}%` : "—")}</div>
      </td>
      <td class="td-actions">
        ${leida
          ? `<button type="button" class="btn-ico" data-ap-unread="${a.id}" title="Marcar no leída">↩</button>`
          : `<button type="button" class="btn-ico is-mark-read" data-ap-read="${a.id}" title="Marcar leída">✓</button>`}
      </td>
    </tr>`;
}

function htmlApConfigModalInner() {
  const f = ALERTAS_PRECIOS.form || {};
  const opts = ALERTAS_PRECIOS.opciones || {};
  const configs = ALERTAS_PRECIOS.configs || [];
  const productos = opts.productos || opts.medicamentos || [];
  const prodSelected = f.producto_key || "";

  const optSimple = (lista, val, emptyLabel) => {
    const items = (lista || []).map((x) => {
      const s = String(x);
      return `<option value="${escapeHtml(s)}"${String(val) === s ? " selected" : ""}>${escapeHtml(s)}</option>`;
    }).join("");
    return `<option value="">${escapeHtml(emptyLabel)}</option>${items}`;
  };

  const optProductos = () => {
    const items = productos.map((x) => {
      const key = String(x.producto_key || "");
      const lab = x.label || [x.nombre_comercial, x.concentracion, x.presentacion].filter(Boolean).join(" · ") || x.medicamento_lista || key;
      return `<option value="${escapeHtml(key)}"${prodSelected === key ? " selected" : ""}>${escapeHtml(lab)}</option>`;
    }).join("");
    return `<option value="">Todos los medicamentos</option>${items}`;
  };

  return `
    <div class="ap-modal-shell">
      <header class="ap-modal-hero">
        <p class="alertas-kicker">Configuración</p>
        <h2 id="apConfigTitle">Criterios de alertas de precios</h2>
        <p class="muted">Definí el alcance en cascada: lo que dejés vacío significa «todos». Ej.: solo país = todas las farmacias y medicamentos de ese país.</p>
      </header>
      ${ALERTAS_PRECIOS.error ? `<p class="note note--warn">${escapeHtml(ALERTAS_PRECIOS.error)}</p>` : ""}
      <div class="ap-layout ap-layout--modal">
        <div class="ap-config-panel">
          <div class="ap-panel-head">
            <h3>${f.id ? "Editar criterio" : "Nuevo criterio"}</h3>
            <p class="muted">País → farmacia → medicamento → presentación → concentración. Vacío = todo el nivel.</p>
          </div>
          <form class="ap-form" data-ap-form>
            <label class="filter-field">
              <span>Nombre (opcional)</span>
              <input class="selectish" type="text" name="nombre" maxlength="200"
                value="${escapeHtml(f.nombre || "")}" placeholder="Ej. Baja en Carol RD" />
            </label>
            <div class="ap-form-grid">
              <label class="filter-field">
                <span>País</span>
                <select class="selectish" name="pais" data-ap-cascade="pais">
                  ${optSimple(opts.paises, f.pais, "Todos los países")}
                </select>
              </label>
              <label class="filter-field">
                <span>Farmacia</span>
                <select class="selectish" name="farmacia" data-ap-cascade="farmacia">
                  ${optSimple(opts.farmacias, f.farmacia, "Todas las farmacias")}
                </select>
              </label>
              <label class="filter-field ap-span-2">
                <span>Medicamento / producto</span>
                <select class="selectish" name="producto_key" data-ap-cascade="producto_key">
                  ${optProductos()}
                </select>
              </label>
              <label class="filter-field">
                <span>Presentación</span>
                <select class="selectish" name="presentacion" data-ap-cascade="presentacion">
                  ${optSimple(opts.presentaciones, f.presentacion, "Todas las presentaciones")}
                </select>
              </label>
              <label class="filter-field">
                <span>Concentración</span>
                <select class="selectish" name="concentracion">
                  ${optSimple(opts.concentraciones, f.concentracion, "Todas las concentraciones")}
                </select>
              </label>
              <label class="filter-field">
                <span>Baja desde (%)</span>
                <input class="selectish" type="number" name="umbral_baja_pct" min="0.1" step="0.1"
                  value="${escapeHtml(f.umbral_baja_pct || "")}" placeholder="Ej. 10" />
              </label>
              <label class="filter-field">
                <span>Alza desde (%)</span>
                <input class="selectish" type="number" name="umbral_sube_pct" min="0.1" step="0.1"
                  value="${escapeHtml(f.umbral_sube_pct || "")}" placeholder="Ej. 15" />
              </label>
              <div class="filter-field ap-span-2">
                <span>Notificar cada</span>
                <div class="ap-interval-row">
                  <input class="selectish" type="number" name="intervalo_valor" min="1"
                    max="${String(f.intervalo_unidad || "horas").toLowerCase() === "minutos" ? 43200 : 720}"
                    step="1" required
                    value="${escapeHtml(f.intervalo_valor || "24")}"
                    placeholder="${String(f.intervalo_unidad || "horas").toLowerCase() === "minutos" ? "30" : "24"}" />
                  <input type="hidden" name="intervalo_unidad"
                    value="${String(f.intervalo_unidad || "horas").toLowerCase() === "minutos" ? "minutos" : "horas"}" />
                  <div class="ap-unit-switch" role="group" aria-label="Unidad del intervalo">
                    <button type="button" class="ap-unit-btn${String(f.intervalo_unidad || "horas").toLowerCase() !== "minutos" ? " is-on" : ""}" data-ap-unidad="horas">Horas</button>
                    <button type="button" class="ap-unit-btn${String(f.intervalo_unidad || "horas").toLowerCase() === "minutos" ? " is-on" : ""}" data-ap-unidad="minutos">Minutos</button>
                  </div>
                </div>
              </div>
            </div>
            <p class="muted ap-form-hint">Toast por criterio (no por producto). El click abre Precios filtrado a este criterio.</p>
            <div class="ap-form-actions">
              <button type="submit" class="btn-refresh" ${ALERTAS_PRECIOS.guardando ? "disabled" : ""}>
                ${ALERTAS_PRECIOS.guardando ? "Guardando…" : (f.id ? "Guardar cambios" : "Guardar criterio")}
              </button>
              ${f.id ? `<button type="button" class="btn-refresh btn-refresh--ghost" data-ap-reset>Cancelar edición</button>` : ""}
            </div>
          </form>
        </div>

        <div class="ap-config-list">
          <div class="ap-panel-head">
            <h3>Criterios guardados <span class="muted">(${configs.length})</span></h3>
            <p class="muted">Podés pausarlos, editarlos o eliminarlos cuando quieras.</p>
          </div>
          ${configs.length
            ? `<div class="ap-config-grid">${configs.map(htmlCardConfigPrecio).join("")}</div>`
            : `<div class="alerta-empty"><p>Todavía no hay criterios. Creá el primero a la izquierda.</p></div>`}
        </div>
      </div>
    </div>`;
}

function renderApConfigModal() {
  const body = $("apConfigModalBody");
  if (body) body.innerHTML = htmlApConfigModalInner();
}

function openApConfigModal() {
  const modal = $("apConfigModal");
  if (!modal) return;
  ALERTAS_PRECIOS.modalOpen = true;
  renderApConfigModal();
  modal.hidden = false;
  modal.classList.add("is-open");
}

function closeApConfigModal() {
  const modal = $("apConfigModal");
  ALERTAS_PRECIOS.modalOpen = false;
  if (!modal) return;
  modal.classList.remove("is-open");
  modal.hidden = true;
}

function htmlAlertasPreciosBody() {
  const focusId = Number(state.alertFocusCriterioPre) || null;
  const focusCfg = focusId
    ? (ALERTAS_PRECIOS.configs || []).find((c) => Number(c.id) === focusId)
    : null;
  const filasAll = (ALERTAS_PRECIOS.filas || []).filter((a) => {
    if (!focusId) return true;
    return Number(a?.config_id) === focusId;
  });
  const pg = paginate(filasAll, ALERTAS_PRECIOS.page || 1, ALERTAS_PRECIOS.size || 12);
  ALERTAS_PRECIOS.page = pg.page;
  const nCfg = (ALERTAS_PRECIOS.configs || []).length;

  if (ALERTAS_PRECIOS.cargando && !ALERTAS_PRECIOS.loaded) {
    return `<p class="note">Cargando alertas de precios…</p>`;
  }

  return `
    <header class="alertas-hero">
      <div class="alertas-hero-copy">
        <p class="alertas-kicker">Mercados · farmacias de la región</p>
        <h2>Precios</h2>
        <p class="alertas-lead">
          Seguimiento de bajas y alzas según los criterios que configures.
          Usá la tuerca para crear o revisar esos criterios.
        </p>
      </div>
      <div class="alertas-actions">
        <button type="button" class="btn-refresh btn-refresh--icon" data-ap-config-open
          title="Criterios de alerta" aria-label="Criterios de alerta">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z"/>
            <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>
          </svg>
          ${nCfg ? `<span class="btn-refresh-count">${nCfg}</span>` : ""}
        </button>
        <button type="button" class="btn-refresh" data-ap-detectar ${ALERTAS_PRECIOS.detectando ? "disabled" : ""}>
          ${ALERTAS_PRECIOS.detectando ? "Evaluando…" : "Evaluar ahora"}
        </button>
        <button type="button" class="btn-refresh btn-refresh--ghost" data-ap-leer-todas>Marcar todas leídas</button>
      </div>
    </header>
    ${ALERTAS_PRECIOS.error && !ALERTAS_PRECIOS.modalOpen ? `<p class="note note--warn">${escapeHtml(ALERTAS_PRECIOS.error)}</p>` : ""}
    ${focusId ? htmlBannerFiltroToastCriterio({
      vista: "precios",
      cfgId: focusId,
      nombre: nombreCriterioPrecio(focusCfg || { id: focusId }),
    }) : ""}

    <section class="alertas-section">
      <div class="alertas-section-head">
        <h3>Alertas disparadas <span class="muted">(${pg.total})</span></h3>
        <p class="muted">${focusId
          ? "Listado filtrado al criterio desde el que abriste la alerta."
          : "Registros generados cuando el precio cruza el umbral del criterio."}</p>
      </div>
      ${pager("apHist", pg.page, pg.pages, pg.total, pg.start, ALERTAS_PRECIOS.size || 12)}
      <div class="table-wrap alerta-hist-wrap">
        <table class="data alertas-table alertas-table--hist">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Medicamento</th>
              <th>Presentación</th>
              <th>Cambio</th>
              <th>USD</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            ${pg.rows.length
              ? pg.rows.map(htmlFilaAlertaPrecio).join("")
              : `<tr><td colspan="6" class="muted">${focusId
                ? "No hay alertas de este criterio."
                : "Aún no hay alertas de precio. Abrí la tuerca, guardá un criterio y pulsá «Evaluar ahora»."}</td></tr>`}
          </tbody>
        </table>
      </div>
    </section>`;
}

function resetFormAlertaPrecio() {
  ALERTAS_PRECIOS.form = {
    id: null,
    nombre: "",
    pais: "",
    farmacia: "",
    producto_key: "",
    n_lista: "",
    medicamento_lista: "",
    nombre_comercial: "",
    presentacion: "",
    concentracion: "",
    umbral_baja_pct: "10",
    umbral_sube_pct: "",
    intervalo_valor: "24",
    intervalo_unidad: "horas",
  };
}

function productosAlertasOpts() {
  const opts = ALERTAS_PRECIOS.opciones || {};
  return opts.productos || opts.medicamentos || [];
}

function leerFormAlertaPrecio(formEl) {
  if (!formEl) return { ...ALERTAS_PRECIOS.form };
  const fd = new FormData(formEl);
  const productoKey = String(fd.get("producto_key") || "").trim();
  const prod = productosAlertasOpts().find((m) => String(m.producto_key) === productoKey);
  return {
    id: ALERTAS_PRECIOS.form.id || null,
    nombre: String(fd.get("nombre") || "").trim(),
    pais: String(fd.get("pais") || "").trim(),
    farmacia: String(fd.get("farmacia") || "").trim(),
    producto_key: productoKey,
    n_lista: productoKey && prod?.n_lista != null ? String(prod.n_lista) : "",
    medicamento_lista: productoKey ? (prod?.medicamento_lista || "") : "",
    nombre_comercial: productoKey ? (prod?.nombre_comercial || "") : "",
    presentacion: String(fd.get("presentacion") || "").trim(),
    concentracion: String(fd.get("concentracion") || "").trim(),
    umbral_baja_pct: String(fd.get("umbral_baja_pct") || "").trim(),
    umbral_sube_pct: String(fd.get("umbral_sube_pct") || "").trim(),
    intervalo_valor: String(fd.get("intervalo_valor") || ALERTAS_PRECIOS.form.intervalo_valor || "24").trim(),
    intervalo_unidad: String(fd.get("intervalo_unidad") || ALERTAS_PRECIOS.form.intervalo_unidad || "horas").toLowerCase() === "minutos"
      ? "minutos"
      : "horas",
  };
}

async function cargarOpcionesAlertasPrecios() {
  const f = ALERTAS_PRECIOS.form || {};
  const params = new URLSearchParams();
  if (f.pais) params.set("pais", f.pais);
  if (f.farmacia) params.set("farmacia", f.farmacia);
  if (f.producto_key) params.set("producto_key", f.producto_key);
  else if (f.n_lista) params.set("n_lista", f.n_lista);
  if (f.presentacion) params.set("presentacion", f.presentacion);
  const r = await fetch(`/api/alertas/precios/opciones?${params}`, { cache: "no-store" });
  const data = await r.json();
  if (!data?.ok) throw new Error(data?.error || "No se pudieron cargar opciones");
  ALERTAS_PRECIOS.opciones = {
    paises: data.paises || [],
    farmacias: data.farmacias || [],
    productos: data.productos || data.medicamentos || [],
    medicamentos: data.productos || data.medicamentos || [],
    presentaciones: data.presentaciones || [],
    concentraciones: data.concentraciones || [],
  };
}

async function cargarAlertasPrecios({ silent = false } = {}) {
  if (!silent) ALERTAS_PRECIOS.cargando = true;
  ALERTAS_PRECIOS.error = null;
  try {
    try {
      await cargarOpcionesAlertasPrecios();
    } catch (optErr) {
      if (!silent) throw optErr;
    }
    const r = await fetch("/api/alertas/precios?limite=500", { cache: "no-store" });
    const data = await r.json();
    if (!data?.ok) throw new Error(data?.error || "No se pudieron cargar alertas de precios");
    ALERTAS_PRECIOS.configs = Array.isArray(data.configs) ? data.configs : [];
    ALERTAS_PRECIOS.filas = Array.isArray(data.filas) ? data.filas : [];
    ALERTAS_PRECIOS.resumen = data.resumen || {};
    ALERTAS_PRECIOS.loaded = true;
  } catch (err) {
    ALERTAS_PRECIOS.error = err?.message || String(err);
    if (!ALERTAS_PRECIOS.loaded) {
      ALERTAS_PRECIOS.configs = [];
      ALERTAS_PRECIOS.filas = [];
    }
  } finally {
    ALERTAS_PRECIOS.cargando = false;
  }
  actualizarBadgeAlertas();
  if (ALERTAS_PRECIOS.modalOpen) renderApConfigModal();
  const panel = $("headerAlertPanel");
  if (panel && !panel.hidden) renderHeaderAlertas();
  return ALERTAS_PRECIOS;
}

function syncPatCfgFormDesdeModal() {
  const form = document.querySelector("#patConfigModal [data-pat-form]");
  if (!form || !ALERTAS_PAT_CFG.form) return;
  const fd = new FormData(form);
  ALERTAS_PAT_CFG.form.nombre = String(fd.get("nombre") || "");
  ALERTAS_PAT_CFG.form.dias_min = String(fd.get("dias_min") ?? "0");
  ALERTAS_PAT_CFG.form.dias_max = String(fd.get("dias_max") || "180");
  ALERTAS_PAT_CFG.form.intervalo_valor = String(fd.get("intervalo_valor") || "24");
  ALERTAS_PAT_CFG.form.intervalo_unidad =
    String(fd.get("intervalo_unidad") || ALERTAS_PAT_CFG.form.intervalo_unidad || "horas").toLowerCase() === "minutos"
      ? "minutos"
      : "horas";
  ALERTAS_PAT_CFG.form.fuente = String(fd.get("fuente") || "fda").toLowerCase() === "ema" ? "ema" : "fda";
  ALERTAS_PAT_CFG.form.n_lista = String(fd.get("n_lista") || "");
  ALERTAS_PAT_CFG.form.avisar_vence_hoy = form.querySelector('[name="avisar_vence_hoy"]')?.checked !== false;
  ALERTAS_PAT_CFG.form.avisar_paso_expirada = form.querySelector('[name="avisar_paso_expirada"]')?.checked !== false;
  ALERTAS_PAT_CFG.form.avisar_diario = form.querySelector('[name="avisar_diario"]')?.checked !== false;
}

function resetPatCfgForm() {
  ALERTAS_PAT_CFG.form = {
    id: null,
    nombre: "",
    dias_min: "0",
    dias_max: "180",
    avisar_vence_hoy: true,
    avisar_paso_expirada: true,
    avisar_diario: true,
    intervalo_valor: "24",
    intervalo_unidad: "horas",
    fuente: "fda",
    n_lista: "",
    medicamento_lista: "",
  };
  ALERTAS_PAT_CFG.error = null;
}

function htmlCardConfigPatente(c) {
  const activa = c.activo === 1 || c.activo === true || c.activo === "1";
  const minD = Number(c.dias_min) || 0;
  const maxD = Number(c.dias_max) || 0;
  const rango = minD > 0 ? `${minD}–${maxD} días` : `≤ ${maxD} días`;
  const intLabel = etiquetaIntervaloCriterio(c);
  const flags = [
    c.avisar_vence_hoy ? "vence hoy" : null,
    c.avisar_paso_expirada ? "pasó a expirada" : null,
    c.avisar_diario ? "aviso diario" : "una vez",
    `UI ${intLabel}`,
  ].filter(Boolean);
  return `
    <article class="ap-config-card ${activa ? "is-on" : "is-off"}" data-pat-config-id="${c.id}">
      <div class="ap-config-top">
        <div>
          <h4>${escapeHtml(c.nombre || `Criterio #${c.id}`)}</h4>
          <p class="muted">Ventana: ${escapeHtml(rango)} · notificación ${escapeHtml(intLabel)}</p>
        </div>
        <span class="ap-config-badge ${activa ? "is-on" : ""}">${activa ? "Activo" : "Pausado"}</span>
      </div>
      <p class="ap-config-umb">${escapeHtml(c.medicamento_lista || "Todos los medicamentos")} · ${escapeHtml(
        String(c.fuente || "").toLowerCase() === "ema" ? "EMA" : "FDA"
      )}</p>
      <p class="muted">${escapeHtml(flags.join(" · "))}</p>
      <div class="ap-config-actions">
        <button type="button" class="alerta-action" data-pat-edit="${c.id}">Editar</button>
        <button type="button" class="alerta-action" data-pat-toggle="${c.id}" data-pat-activo="${activa ? "0" : "1"}">
          ${activa ? "Pausar" : "Activar"}
        </button>
        <button type="button" class="alerta-action alerta-action--ghost" data-pat-del="${c.id}">Eliminar</button>
      </div>
    </article>`;
}

function htmlPatConfigModalInner() {
  const f = ALERTAS_PAT_CFG.form || {};
  const opts = ALERTAS_DATA.opcionesCriterios || {};
  const configs = ALERTAS_DATA.configs || [];
  const meds = opts.medicamentos || [];
  const fuentes = [
    { id: "fda", label: "FDA" },
    { id: "ema", label: "EMA" },
  ];
  const fuenteSel = ["fda", "ema"].includes(String(f.fuente || "").toLowerCase())
    ? String(f.fuente).toLowerCase()
    : "fda";
  const presets = opts.presets_dias || [7, 30, 60, 90, 180, 365];
  const optMeds = meds.map((m) => {
    const id = String(m.n_lista);
    return `<option value="${escapeHtml(id)}"${String(f.n_lista) === id ? " selected" : ""}>${escapeHtml(m.medicamento_lista || `#${id}`)}</option>`;
  }).join("");
  const optFuentes = fuentes.map((x) => {
    const id = String(x.id || "");
    return `<option value="${escapeHtml(id)}"${fuenteSel === id ? " selected" : ""}>${escapeHtml(x.label || id)}</option>`;
  }).join("");
  const chips = presets.map((d) => `
    <button type="button" class="chip ${String(f.dias_max) === String(d) ? "is-on" : ""}" data-pat-preset-dias="${d}">≤ ${d}d</button>
  `).join("");
  const intervaloSel = String(f.intervalo_valor || "24");
  const unidadSel = String(f.intervalo_unidad || "horas").toLowerCase() === "minutos" ? "minutos" : "horas";
  const maxIntervalo = unidadSel === "minutos" ? 43200 : 720;

  return `
    <div class="ap-modal-shell">
      <header class="ap-modal-hero">
        <p class="alertas-kicker">Configuración</p>
        <h2 id="patConfigTitle">Criterios de alertas de patentes</h2>
        <p class="muted">Definí cuándo avisar en el módulo superior y cada cuánto repetir el toast y el modal. El tiempo se guarda para no reiniciarse al recargar.</p>
      </header>
      ${ALERTAS_PAT_CFG.error ? `<p class="note note--warn">${escapeHtml(ALERTAS_PAT_CFG.error)}</p>` : ""}
      <div class="ap-layout ap-layout--modal">
        <div class="ap-config-panel">
          <div class="ap-panel-head">
            <h3>${f.id ? "Editar criterio" : "Nuevo criterio"}</h3>
            <p class="muted">Ejemplo: avisarme cada 24 h las que vencen en los próximos 180 días.</p>
          </div>
          <form class="ap-form" data-pat-form>
            <label class="filter-field">
              <span>Nombre (opcional)</span>
              <input class="selectish" type="text" name="nombre" maxlength="200"
                value="${escapeHtml(f.nombre || "")}" placeholder="Ej. Ventana 6 meses FDA" />
            </label>
            <div class="ap-form-grid">
              <label class="filter-field">
                <span>Desde (días restantes)</span>
                <input class="selectish" type="number" name="dias_min" min="0" step="1"
                  value="${escapeHtml(f.dias_min ?? "0")}" placeholder="0" />
              </label>
              <div class="filter-field">
                <span>Ventana (días restantes)</span>
                <input type="hidden" name="dias_max" value="${escapeHtml(f.dias_max || "180")}" />
                <div class="filter-chips">${chips}</div>
              </div>
              <label class="filter-field">
                <span>Fuente</span>
                <select class="selectish" name="fuente">${optFuentes}</select>
              </label>
              <label class="filter-field">
                <span>Medicamento (opcional)</span>
                <select class="selectish" name="n_lista">
                  <option value="">Todos los de la lista</option>
                  ${optMeds}
                </select>
              </label>
              <div class="filter-field ap-span-2">
                <span>Notificar cada</span>
                <div class="ap-interval-row">
                  <input class="selectish" type="number" name="intervalo_valor" min="1" max="${maxIntervalo}" step="1" required
                    value="${escapeHtml(intervaloSel)}" placeholder="${unidadSel === "minutos" ? "30" : "24"}" />
                  <input type="hidden" name="intervalo_unidad" value="${unidadSel}" />
                  <div class="ap-unit-switch" role="group" aria-label="Unidad del intervalo">
                    <button type="button" class="ap-unit-btn${unidadSel === "horas" ? " is-on" : ""}" data-pat-unidad="horas">Horas</button>
                    <button type="button" class="ap-unit-btn${unidadSel === "minutos" ? " is-on" : ""}" data-pat-unidad="minutos">Minutos</button>
                  </div>
                </div>
              </div>
            </div>
            <p class="muted ap-form-hint">Aplica al toast de la esquina y al modal del header. No se reinicia al recargar la página.</p>
            <div class="ap-form-checks">
              <label class="chk"><input type="checkbox" name="avisar_vence_hoy" ${f.avisar_vence_hoy ? "checked" : ""} /> Avisar si vence hoy</label>
              <label class="chk"><input type="checkbox" name="avisar_paso_expirada" ${f.avisar_paso_expirada ? "checked" : ""} /> Avisar cuando pase a expirada</label>
              <label class="chk"><input type="checkbox" name="avisar_diario" ${f.avisar_diario ? "checked" : ""} /> Recordatorio diario mientras esté en la ventana</label>
            </div>
            <div class="ap-form-actions">
              <button type="submit" class="btn-refresh" ${ALERTAS_PAT_CFG.guardando ? "disabled" : ""}>
                ${ALERTAS_PAT_CFG.guardando ? "Guardando…" : (f.id ? "Guardar cambios" : "Guardar criterio")}
              </button>
              ${f.id ? `<button type="button" class="btn-refresh btn-refresh--ghost" data-pat-reset>Cancelar edición</button>` : ""}
              <button type="button" class="btn-refresh btn-refresh--ghost" data-pat-evaluar>Evaluar ahora</button>
            </div>
          </form>
        </div>
        <div class="ap-config-list">
          <div class="ap-panel-head">
            <h3>Criterios guardados <span class="muted">(${configs.length})</span></h3>
            <p class="muted">Los activos alimentan el badge y el panel de arriba.</p>
          </div>
          ${configs.length
            ? `<div class="ap-config-grid">${configs.map(htmlCardConfigPatente).join("")}</div>`
            : `<div class="alerta-empty"><p>Todavía no hay criterios. Creá el primero a la izquierda.</p></div>`}
        </div>
      </div>
    </div>`;
}

function renderPatConfigModal() {
  const body = $("patConfigModalBody");
  if (body) body.innerHTML = htmlPatConfigModalInner();
}

function openPatConfigModal() {
  const modal = $("patConfigModal");
  if (!modal) return;
  ALERTAS_PAT_CFG.modalOpen = true;
  renderPatConfigModal();
  modal.hidden = false;
  modal.classList.add("is-open");
  if (!(ALERTAS_DATA.configs || []).length && !ALERTAS_DATA.cargando) {
    cargarAlertasPatentes({ silent: true }).then(() => {
      if (ALERTAS_PAT_CFG.modalOpen) renderPatConfigModal();
    });
  }
}

function closePatConfigModal() {
  const modal = $("patConfigModal");
  ALERTAS_PAT_CFG.modalOpen = false;
  if (!modal) return;
  modal.classList.remove("is-open");
  modal.hidden = true;
}

async function guardarPatConfigDesdeForm(form) {
  const fd = new FormData(form);
  const nLista = String(fd.get("n_lista") || "").trim();
  const med = (ALERTAS_DATA.opcionesCriterios?.medicamentos || []).find((m) => String(m.n_lista) === nLista);
  const payload = {
    id: ALERTAS_PAT_CFG.form.id || undefined,
    nombre: String(fd.get("nombre") || "").trim(),
    dias_min: Number(fd.get("dias_min") || 0),
    dias_max: Number(fd.get("dias_max") || 0),
    avisar_vence_hoy: form.querySelector('[name="avisar_vence_hoy"]')?.checked !== false,
    avisar_paso_expirada: form.querySelector('[name="avisar_paso_expirada"]')?.checked !== false,
    avisar_diario: form.querySelector('[name="avisar_diario"]')?.checked !== false,
    intervalo_valor: Number(fd.get("intervalo_valor") || 24),
    intervalo_unidad: String(fd.get("intervalo_unidad") || "horas").toLowerCase() === "minutos" ? "minutos" : "horas",
    fuente: String(fd.get("fuente") || "fda").trim().toLowerCase() === "ema" ? "ema" : "fda",
    n_lista: nLista || null,
    medicamento_lista: med?.medicamento_lista || null,
    activo: true,
  };
  ALERTAS_PAT_CFG.guardando = true;
  ALERTAS_PAT_CFG.error = null;
  renderPatConfigModal();
  try {
    const r = await fetch("/api/alertas/patentes/configs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await r.json();
    if (!data?.ok) throw new Error(data?.error || "No se pudo guardar");
    resetPatCfgForm();
    await cargarAlertasPatentes({ silent: true });
    // Evaluar al guardar para que el badge se actualice sin esperar al cron.
    const crit = await fetch("/api/alertas/patentes/configs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ accion: "evaluar" }),
    }).then((x) => x.json()).catch(() => null);
    await cargarAlertasPatentes({ silent: true });
    renderHeaderAlertas();
    mostrarToastsCriteriosPatentes({
      nuevas: Number(crit?.insertadas || 0),
      mensaje: crit?.mensaje || "",
      forzar: true,
    });
    arrancarRelojNotificacionesUiPatentes();
  } catch (err) {
    ALERTAS_PAT_CFG.error = err?.message || String(err);
  } finally {
    ALERTAS_PAT_CFG.guardando = false;
    if (ALERTAS_PAT_CFG.modalOpen) renderPatConfigModal();
    if (state.view === "alertas") renderAlertas({ soft: true });
  }
}

function htmlAlertasPatentesBody() {
  const filas = ALERTAS_DATA.filas || [];
  const base = filtrarAlertasBase(filas);
  const focusId = Number(state.alertFocusCriterioPat) || null;
  const focusCfg = focusId
    ? (ALERTAS_DATA.configs || []).find((c) => Number(c.id) === focusId)
    : null;
  const activasAll = ordenarAlertasActivas(
    base.filter(alertaEnVentanaActiva).filter((a) => {
      if (!focusId) return true;
      return String(a?.tipo_alerta || "") === `criterio_${focusId}`;
    }),
  );
  const historialAll = ordenarAlertasHistorial(base.filter(alertaEnHistorialVencidas));
  const pgAct = paginate(activasAll, state.alertActPage || 1, state.alertActSize || 12);
  const pgHist = paginate(historialAll, state.alertHistPage || 1, state.alertHistSize || 12);
  state.alertActPage = pgAct.page;
  state.alertHistPage = pgHist.page;
  const nCfg = (ALERTAS_DATA.configs || []).filter((c) => c.activo === 1 || c.activo === true).length;

  if (ALERTAS_DATA.cargando && !filas.length) {
    return `<p class="note">Cargando alertas de patentes…</p>`;
  }

  return `
    <header class="alertas-hero">
      <div class="alertas-hero-copy">
        <p class="alertas-kicker">FDA · Orange Book / Purple Book</p>
        <h2>Patentes</h2>
        <p class="alertas-lead">
          Acompañá los vencimientos de patentes de los principios de la lista.
          Usá la tuerca para definir criterios (p. ej. avisarme diariamente las que vencen en X días).
        </p>
      </div>
      <div class="alertas-actions">
        <button type="button" class="btn-refresh btn-refresh--icon" data-pat-config-open
          title="Criterios de alerta" aria-label="Criterios de alerta">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z"/>
            <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>
          </svg>
          ${nCfg ? `<span class="btn-refresh-count">${nCfg}</span>` : ""}
        </button>
        <button type="button" class="btn-refresh" data-alerta-detectar ${ALERTAS_DATA.detectando ? "disabled" : ""}>
          ${ALERTAS_DATA.detectando ? "Actualizando…" : "Actualizar alertas"}
        </button>
        <button type="button" class="btn-refresh btn-refresh--ghost" data-alerta-leer-todas>Marcar todas leídas</button>
      </div>
    </header>

    <div class="filters alertas-filters">
      <label>Fuente
        <select data-alerta-fuente>
          <option value="fda"${state.alertFuente === "fda" ? " selected" : ""}>FDA</option>
          <option value="ema"${state.alertFuente === "ema" ? " selected" : ""}>EMA</option>
        </select>
      </label>
      <label>Tipo
        <select data-alerta-tipo>
          <option value="todos"${!state.alertTipo || state.alertTipo === "todos" || state.alertTipo === "paso_a_expirada" ? " selected" : ""}>Todos</option>
          <option value="vence_hoy"${state.alertTipo === "vence_hoy" ? " selected" : ""}>Vence hoy</option>
          <option value="vence_en_30d"${state.alertTipo === "vence_en_30d" ? " selected" : ""}>≤30 días</option>
          <option value="vence_en_60d"${state.alertTipo === "vence_en_60d" ? " selected" : ""}>≤60 días</option>
          <option value="vence_en_90d"${state.alertTipo === "vence_en_90d" ? " selected" : ""}>≤90 días</option>
          <option value="vence_en_180d"${state.alertTipo === "vence_en_180d" ? " selected" : ""}>≤6 meses</option>
          <option value="vence_en_365d"${state.alertTipo === "vence_en_365d" ? " selected" : ""}>≤12 meses</option>
        </select>
      </label>
      <label class="chk">
        <input type="checkbox" data-alerta-nuevas ${state.alertSoloNuevas ? "checked" : ""} />
        Solo no leídas
      </label>
    </div>
    ${ALERTAS_DATA.error ? `<p class="note note--warn">${escapeHtml(ALERTAS_DATA.error)}</p>` : ""}
    ${focusId ? htmlBannerFiltroToastCriterio({
      vista: "patentes",
      cfgId: focusId,
      nombre: nombreCriterioPatente(focusCfg || { id: focusId }),
    }) : ""}

    <section class="alertas-section">
      <div class="alertas-section-head">
        <h3>Por vencer <span class="muted">(${pgAct.total})</span></h3>
        <p class="muted" style="margin: 0;">${focusId
          ? `Filtrado al criterio «${escapeHtml(nombreCriterioPatente(focusCfg || { id: focusId }))}».`
          : `Ordenadas por urgencia, de las más próximas a las más lejanas${nCfg ? ` · criterios activos: ${nCfg}` : ""}.`}</p>
      </div>
      ${pager("alertAct", pgAct.page, pgAct.pages, pgAct.total, pgAct.start, state.alertActSize || 12)}
      ${htmlGridAlertasActivas(pgAct.rows, focusId
        ? "No hay patentes por vencer para este criterio."
        : "No hay patentes por vencer con los filtros seleccionados.")}
      ${pgAct.total > (state.alertActSize || 12) ? pager("alertAct", pgAct.page, pgAct.pages, pgAct.total, pgAct.start, state.alertActSize || 12) : ""}
    </section>

    <section class="alertas-section alertas-section--historial">
      <div class="alertas-section-head">
        <h3>Historial de vencidas <span class="muted">(${pgHist.total})</span></h3>
        <p class="muted">Registro de patentes que ya alcanzaron su fecha de vencimiento.</p>
      </div>
      ${pager("alertHist", pgHist.page, pgHist.pages, pgHist.total, pgHist.start, state.alertHistSize || 12)}
      ${htmlTablaAlertasPatentes(pgHist.rows, "Aún no hay patentes vencidas en el historial.")}
      ${pgHist.total > (state.alertHistSize || 12) ? pager("alertHist", pgHist.page, pgHist.pages, pgHist.total, pgHist.start, state.alertHistSize || 12) : ""}
    </section>`;
}

function htmlAlertasVistaBody() {
  if (state.alertVista === "precios") return htmlAlertasPreciosBody();
  return htmlAlertasPatentesBody();
}

function renderAlertas({ soft = false } = {}) {
  const stage = $("stage");
  if (!stage) return;
  const existing = stage.querySelector(".alertas-shell");
  const bodyHtml = htmlAlertasVistaBody();
  const tabsHtml = alertaVistaTabsHtml();
  // Soft: no regenerar toda la card (evita el “reload” al cambiar Patentes/Precios).
  if (soft && existing) {
    const head = existing.querySelector(".alertas-card-head--tabs");
    const body = existing.querySelector(".alertas-tab-body");
    if (head) head.innerHTML = tabsHtml;
    if (body) {
      body.setAttribute("data-alerta-tab", state.alertVista || "patentes");
      body.innerHTML = bodyHtml;
    }
  } else {
    stage.innerHTML = `
      <article class="card alertas-shell">
        <div class="card-head tend-card-head--tabs alertas-card-head--tabs">
          ${tabsHtml}
        </div>
        <div class="alertas-tab-body" data-alerta-tab="${escapeHtml(state.alertVista || "patentes")}">
          ${bodyHtml}
        </div>
      </article>`;
  }
  if (state.alertVista === "precios" && !ALERTAS_PRECIOS.loaded && !ALERTAS_PRECIOS.cargando) {
    cargarAlertasPrecios({ silent: true }).then(() => {
      if (state.view === "alertas" && state.alertVista === "precios") renderAlertas({ soft: true });
    });
  }
  if (ALERTAS_PRECIOS.modalOpen) renderApConfigModal();
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
    const navView = b.dataset.view;
    const active =
      navView === state.view ||
      (navView === "tendencias" && state.view === "comparativo");
    b.classList.toggle("is-active", active);
  });
  try {
    if (state.view !== "tendencias") stashTendKeepHost();
    if (state.view === "tablero") renderTablero();
    else if (state.view === "comparativo") renderComparativo();
    else if (state.view === "detalle") renderDetalle();
    else if (state.view === "tendencias") renderTendencias();
    else if (state.view === "alertas") {
      renderAlertas();
      // Si ya hay datos, no re-pintar al terminar el fetch (evita un segundo “reload”).
      if (!ALERTAS_DATA.loaded) {
        cargarAlertasPatentes({ silent: true }).then(() => {
          if (state.view === "alertas") renderAlertas({ soft: true });
        });
      } else {
        cargarAlertasPatentes({ silent: true }).catch(() => {});
      }
    }
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
  if (view === "detalle" || view === "metodologia") view = "tablero";
  if (view === "comparativo") {
    state.tendVista = "comparativo";
    view = "tendencias";
  }
  // Entrada normal (sidebar / nav): sin filtro de toast.
  if (view === "alertas") {
    state.alertFocusCriterioPat = null;
    state.alertFocusCriterioPre = null;
  } else {
    state.alertFocusCriterioPat = null;
    state.alertFocusCriterioPre = null;
  }
  cerrarHeaderAlertas();
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
    let nextView = viewFromLocation();
    if (nextView === "comparativo") {
      state.tendVista = "comparativo";
      nextView = "tendencias";
      syncRoute("tendencias", true);
    }
    if (nextView === state.view) {
      if (nextView === "tendencias") renderTendencias();
      return;
    }
    cerrarHeaderAlertas();
    state.view = nextView;
    state.page = 1;
    state.dpage = 1;
    closeModal();
    render();
  });
  window.addEventListener("resize", () => {
    if (
      state.view === "comparativo" ||
      state.view === "detalle" ||
      (state.view === "tendencias" && state.tendVista === "comparativo")
    ) {
      syncFlowSticky();
    }
  });
  document.addEventListener("click", (e) => {
    if (e.target.closest("#headerAlertBtn")) {
      e.preventDefault();
      toggleHeaderAlertas();
      return;
    }
    const headerTab = e.target.closest("[data-header-alert-tab]");
    if (headerTab) {
      e.preventDefault();
      e.stopPropagation();
      const tab = headerTab.getAttribute("data-header-alert-tab");
      if (tab === "precios" || tab === "patentes") {
        state.headerAlertTab = tab;
        renderHeaderAlertas();
      }
      return;
    }
    if (e.target.closest("[data-header-alertas-open]")) {
      e.preventDefault();
      const vista = state.headerAlertTab === "precios" ? "precios" : "patentes";
      cerrarHeaderAlertas();
      irAModuloAlertas(vista);
      return;
    }
    const headerGo = e.target.closest("[data-header-alert-go]");
    if (headerGo) {
      e.preventDefault();
      const vista = headerGo.getAttribute("data-header-alert-go") === "precios" ? "precios" : "patentes";
      cerrarHeaderAlertas();
      irAModuloAlertas(vista);
      return;
    }
    if (!e.target.closest("#topAlerts")) cerrarHeaderAlertas();
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
    if (e.target.closest("#btnDocExcel")) {
      e.preventDefault();
      exportDocumentacionExcel();
      return;
    }
    const tendTab = e.target.closest?.("[data-tend-vista]");
    if (tendTab) {
      const vista = tendTab.getAttribute("data-tend-vista");
      if (vista && vista !== state.tendVista) {
        state.tendVista = vista;
        if (vista === "comparativo") state.page = 1;
        renderTendencias();
      }
      return;
    }
    const alertaTab = e.target.closest?.("[data-alerta-vista]");
    if (alertaTab) {
      const vista = alertaTab.getAttribute("data-alerta-vista");
      if (vista && vista !== state.alertVista) {
        if (vista !== "precios") closeApConfigModal();
        if (vista !== "patentes") closePatConfigModal();
        // Cambio manual de tab = vista normal (sin filtro de toast).
        state.alertFocusCriterioPat = null;
        state.alertFocusCriterioPre = null;
        state.alertVista = vista;
        if (state.view === "alertas") renderAlertas({ soft: true });
        if (vista === "precios" && !ALERTAS_PRECIOS.loaded && !ALERTAS_PRECIOS.cargando) {
          cargarAlertasPrecios({ silent: true }).then(() => {
            if (state.view === "alertas" && state.alertVista === "precios") renderAlertas({ soft: true });
          });
        }
      }
      return;
    }
    if (e.target.closest("[data-alert-focus-clear]")) {
      e.preventDefault();
      limpiarFiltroToastAlertas();
      return;
    }
    const tendSort = e.target.closest?.("[data-tend-table-sort]");
    if (tendSort) {
      const key = tendSort.getAttribute("data-tend-table-sort");
      if (key) {
        if (state.tendTableSort === key) state.tendTableDir = -Number(state.tendTableDir || 1);
        else {
          state.tendTableSort = key;
          state.tendTableDir = key === "fecha" ? 1 : 1;
        }
        if (TEND_DATA) aplicarVistaTendencia({ soloTabla: true });
      }
      return;
    }
    const fuentesTab = e.target.closest?.("[data-fuentes-tab]");
    if (fuentesTab) {
      const tab = fuentesTab.getAttribute("data-fuentes-tab");
      if (tab && tab !== state.fuentesTab) {
        state.fuentesTab = tab;
        renderFuentes();
      }
      return;
    }
    const expFicha = e.target.closest?.("[data-exp-ficha]");
    if (expFicha) {
      openModal(Number(expFicha.getAttribute("data-exp-ficha")));
      return;
    }
    const expSerie = e.target.closest?.("[data-exp-serie]");
    if (expSerie) {
      abrirSerieDesdeExplorador(expSerie);
      return;
    }
    if (e.target.closest?.("#expReset")) {
      Object.assign(state, {
        expQ: "",
        expPais: "todos",
        expFarmacia: "todas",
        expPrograma: "todos",
        expFecha: "",
        expPrecioMin: "",
        expPrecioMax: "",
        expMinPaises: 0,
        expSoloMin: false,
        expTodas: false,
        expModoPrecio: "paquete",
        expOrden: "precio_asc",
      });
      renderTendencias();
      return;
    }
    const paisChip = e.target.closest?.("[data-tend-pais-toggle]");
    if (paisChip) {
      e.preventDefault();
      const pais = paisChip.getAttribute("data-tend-pais-toggle");
      const all = (TEND_DATA?.paises_disponibles || []).filter((p) => paisActivo(idPaisPorTexto(p)));
      const set = new Set(state.tendPaises && state.tendPaises.length ? state.tendPaises : all);
      if (set.has(pais)) {
        if (set.size <= 1) return;
        set.delete(pais);
      } else set.add(pais);
      state.tendPaises = [...set];
      if (Array.isArray(TEND_DATA?.farmacias_disponibles)) {
        const ok = new Set(
          TEND_DATA.farmacias_disponibles
            .filter((f) => set.has(f.pais))
            .map((f) => f.id || `${f.farmacia}||${f.pais}`),
        );
        state.tendFarmacias = (state.tendFarmacias || []).filter((id) => ok.has(id));
        if (!state.tendFarmacias.length) state.tendFarmacias = [...ok];
      }
      aplicarVistaTendencia();
      return;
    }
    if (e.target.closest?.("[data-tend-pais-all]")) {
      e.preventDefault();
      state.tendPaises = (TEND_DATA?.paises_disponibles || []).filter((p) => paisActivo(idPaisPorTexto(p)));
      if (Array.isArray(TEND_DATA?.farmacias_disponibles)) {
        state.tendFarmacias = TEND_DATA.farmacias_disponibles
          .filter((f) => state.tendPaises.includes(f.pais))
          .map((f) => f.id || `${f.farmacia}||${f.pais}`);
      }
      aplicarVistaTendencia();
      return;
    }
    const farmChip = e.target.closest?.("[data-tend-farm-toggle]");
    if (farmChip) {
      e.preventDefault();
      const id = farmChip.getAttribute("data-tend-farm-toggle");
      const paisOn = new Set(state.tendPaises || []);
      const all = (TEND_DATA?.farmacias_disponibles || [])
        .filter((f) => paisActivo(idPaisPorTexto(f.pais)) && (!paisOn.size || paisOn.has(f.pais)))
        .map((f) => f.id || `${f.farmacia}||${f.pais}`);
      const set = new Set(state.tendFarmacias && state.tendFarmacias.length ? state.tendFarmacias : all);
      if (set.has(id)) {
        if (set.size <= 1) return;
        set.delete(id);
      } else set.add(id);
      state.tendFarmacias = [...set];
      aplicarVistaTendencia();
      return;
    }
    if (e.target.closest?.("[data-tend-farm-all]")) {
      e.preventDefault();
      const paisOn = new Set(state.tendPaises || []);
      state.tendFarmacias = (TEND_DATA?.farmacias_disponibles || [])
        .filter((f) => paisActivo(idPaisPorTexto(f.pais)) && (!paisOn.size || paisOn.has(f.pais)))
        .map((f) => f.id || `${f.farmacia}||${f.pais}`);
      aplicarVistaTendencia();
      return;
    }
    const expandRow = e.target.closest?.("[data-tend-expand-fd]");
    if (expandRow && !e.target.closest?.("a, button, .tend-farm-subtable")) {
      e.preventDefault();
      const fd = expandRow.getAttribute("data-tend-expand-fd") || "";
      state.tendExpandFd = state.tendExpandFd === fd ? null : fd;
      aplicarVistaTendencia({ soloTabla: true });
      return;
    }
    const agruparBtn = e.target.closest?.("[data-tend-agrupar]");
    if (agruparBtn) {
      e.preventDefault();
      // Modo fijo: siempre farmacia → gráfico por país. Se ignora el toggle legado.
      return;
    }
    const medPick = e.target.closest?.("[data-tend-med-pick]");
    if (medPick) {
      const val = medPick.getAttribute("data-tend-med-pick") || "";
      const parsed = parseTendOptionValue(val);
      state.tendenciaN = parsed.n;
      state.tendenciaProductoKey = parsed.producto_key || null;
      state.tendExpandFd = null;
      TEND_DATA = null;
      if (state.tendenciaN && state.tendenciaProductoKey) {
        const opt = tendProductosSelectOpts().find((o) =>
          Number(o.n_lista) === Number(state.tendenciaN)
          && String(o.producto_key) === String(state.tendenciaProductoKey)
        );
        state.tendProductoSel = opt?.label || "";
        state.tendPresSel = opt?.presentacion || "";
        state.tendConcSel = opt?.concentracion || "";
        state.tendMedQ = "";
        cerrarTendMedPicker({ restoreLabel: true });
        aplicarSeleccionCascade({ load: true });
      } else {
        state.tendProductoSel = "";
        state.tendPresSel = "";
        state.tendConcSel = "";
        cerrarTendMedPicker({ restoreLabel: true });
        aplicarSeleccionCascade({ load: false });
        tendVaciarResultadosSerie("Selecciona un nombre de producto.");
      }
      return;
    }
    const pick = e.target.closest?.("[data-tend-pick]");
    if (pick) {
      seleccionarTendMedicamento(pick.getAttribute("data-tend-pick") || "");
      return;
    }
    if (state.tendPickerOpen && !e.target.closest?.(".tend-picker-wrap")) {
      cerrarTendMedPicker({ restoreLabel: true });
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
      const cov = covChip.dataset.coverPaCov || "principios";
      state.coverVista = ["farmacias", "medicamentos"].includes(cov) ? cov : "principios";
      state.coverFarmacia = null;
      state.cpage = 1;
      state.cq = "";
      closeCoverListModal();
      openCoverModal(COVER_LIST_CACHE.paisId || state.coverPais);
      return;
    }
    const openFarm = e.target.closest("[data-open-cover-farm]");
    if (openFarm) {
      e.preventDefault();
      state.cpage = 1;
      state.cq = "";
      openCoverFarmModal(openFarm.getAttribute("data-open-cover-farm") || "");
      return;
    }
    const backFarm = e.target.closest("[data-back-cover-farm]");
    if (backFarm) {
      e.preventDefault();
      const paisId = backFarm.dataset.backCoverFarm || COVER_LIST_CACHE.paisId || state.coverPais;
      state.coverFarmacia = null;
      state.coverVista = "farmacias";
      state.cpage = 1;
      state.cq = "";
      closeCoverListModal();
      if (paisesUi().some((x) => x.id === paisId)) openCoverModal(paisId);
      return;
    }
    const backFarmDetail = e.target.closest("[data-back-cover-farm-detail]");
    if (backFarmDetail) {
      e.preventDefault();
      openCoverFarmModal(backFarmDetail.getAttribute("data-back-cover-farm-detail") || state.coverFarmacia || "");
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
      });
      return;
    }
    const backList = e.target.closest("[data-back-cover-list]");
    if (backList) {
      e.preventDefault();
      const paisId = backList.dataset.backCoverList || COVER_LIST_CACHE.paisId || state.coverPais;
      if (!paisesUi().some((x) => x.id === paisId)) return;
      state.coverVista = "principios";
      state.coverFarmacia = null;
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
    const alertaDetectar = e.target.closest("[data-alerta-detectar]");
    if (alertaDetectar) {
      e.preventDefault();
      if (ALERTAS_DATA.detectando) return;
      ALERTAS_DATA.detectando = true;
      renderAlertas({ soft: true });
      // Primero criterios (notificaciones), luego detección general FDA/EMA.
      fetch("/api/alertas/patentes/configs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accion: "evaluar" }),
      })
        .then((r) => r.json())
        .then(async (crit) => {
          if (!crit?.ok && crit?.error) throw new Error(crit.error || crit.mensaje || "No se pudieron evaluar criterios");
          const det = await fetch("/api/alertas/patentes/detectar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ fuente: "todas" }),
          }).then((r) => r.json()).catch(() => null);
          await cargarAlertasPatentes({ silent: true });
          renderHeaderAlertas();
          const nuevas = Number(
            crit?.insertadas
            ?? det?.criterios?.insertadas
            ?? 0,
          );
          mostrarToastsCriteriosPatentes({
            nuevas,
            mensaje: crit?.mensaje || det?.criterios?.mensaje || "",
            forzar: true,
          });
        })
        .catch((err) => {
          ALERTAS_DATA.error = err?.message || String(err);
          mostrarToastAlerta({
            titulo: "No se pudo actualizar",
            texto: ALERTAS_DATA.error,
            kind: "info",
            duracionMs: 10000,
          });
        })
        .finally(() => {
          ALERTAS_DATA.detectando = false;
          if (state.view === "alertas") renderAlertas({ soft: true });
        });
      return;
    }
    const alertaLeerTodas = e.target.closest("[data-alerta-leer-todas]");
    if (alertaLeerTodas) {
      e.preventDefault();
      fetch("/api/alertas/patentes/leer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ todas: true }),
      })
        .then((r) => r.json())
        .then(async () => {
          await cargarAlertasPatentes({ silent: true });
          if (state.view === "alertas") renderAlertas({ soft: true });
        })
        .catch(() => {});
      return;
    }
    const alertaRead = e.target.closest("[data-alerta-read]");
    if (alertaRead) {
      e.preventDefault();
      fetch("/api/alertas/patentes/leer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: Number(alertaRead.dataset.alertaRead), leida: true }),
      })
        .then((r) => r.json())
        .then(async () => {
          await cargarAlertasPatentes({ silent: true });
          if (state.view === "alertas") renderAlertas({ soft: true });
        })
        .catch(() => {});
      return;
    }
    const alertaUnread = e.target.closest("[data-alerta-unread]");
    if (alertaUnread) {
      e.preventDefault();
      fetch("/api/alertas/patentes/leer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: Number(alertaUnread.dataset.alertaUnread), leida: false }),
      })
        .then((r) => r.json())
        .then(async () => {
          await cargarAlertasPatentes({ silent: true });
          if (state.view === "alertas") renderAlertas({ soft: true });
        })
        .catch(() => {});
      return;
    }
    const apConfigOpen = e.target.closest("[data-ap-config-open]");
    if (apConfigOpen) {
      e.preventDefault();
      openApConfigModal();
      return;
    }
    if (e.target.closest("[data-close-ap-config]")) {
      e.preventDefault();
      closeApConfigModal();
      return;
    }
    const patConfigOpen = e.target.closest("[data-pat-config-open]");
    if (patConfigOpen) {
      e.preventDefault();
      openPatConfigModal();
      return;
    }
    if (e.target.closest("[data-close-pat-config]")) {
      e.preventDefault();
      closePatConfigModal();
      return;
    }
    if (e.target.closest("[data-pat-reset]")) {
      e.preventDefault();
      resetPatCfgForm();
      renderPatConfigModal();
      return;
    }
    const patPreset = e.target.closest("[data-pat-preset-dias]");
    if (patPreset) {
      e.preventDefault();
      syncPatCfgFormDesdeModal();
      ALERTAS_PAT_CFG.form.dias_max = String(patPreset.getAttribute("data-pat-preset-dias") || "180");
      ALERTAS_PAT_CFG.form.dias_min = "0";
      renderPatConfigModal();
      return;
    }
    const patUnidad = e.target.closest("[data-pat-unidad]");
    if (patUnidad) {
      e.preventDefault();
      syncPatCfgFormDesdeModal();
      const next = patUnidad.getAttribute("data-pat-unidad") === "minutos" ? "minutos" : "horas";
      const prev = ALERTAS_PAT_CFG.form.intervalo_unidad === "minutos" ? "minutos" : "horas";
      let valor = Math.max(1, Number(ALERTAS_PAT_CFG.form.intervalo_valor) || 1);
      if (prev !== next) {
        if (next === "minutos") valor = Math.min(43200, valor * 60);
        else valor = Math.max(1, Math.round(valor / 60));
      }
      ALERTAS_PAT_CFG.form.intervalo_unidad = next;
      ALERTAS_PAT_CFG.form.intervalo_valor = String(valor);
      renderPatConfigModal();
      return;
    }
    const apUnidad = e.target.closest("[data-ap-unidad]");
    if (apUnidad) {
      e.preventDefault();
      const form = document.querySelector("#apConfigModal [data-ap-form]") || document.querySelector("[data-ap-form]");
      if (form) ALERTAS_PRECIOS.form = { ...ALERTAS_PRECIOS.form, ...leerFormAlertaPrecio(form) };
      const next = apUnidad.getAttribute("data-ap-unidad") === "minutos" ? "minutos" : "horas";
      const prev = ALERTAS_PRECIOS.form.intervalo_unidad === "minutos" ? "minutos" : "horas";
      let valor = Math.max(1, Number(ALERTAS_PRECIOS.form.intervalo_valor) || 1);
      if (prev !== next) {
        if (next === "minutos") valor = Math.min(43200, valor * 60);
        else valor = Math.max(1, Math.round(valor / 60));
      }
      ALERTAS_PRECIOS.form.intervalo_unidad = next;
      ALERTAS_PRECIOS.form.intervalo_valor = String(valor);
      if (ALERTAS_PRECIOS.modalOpen) renderApConfigModal();
      else if (state.view === "alertas") renderAlertas({ soft: true });
      return;
    }
    const patEdit = e.target.closest("[data-pat-edit]");
    if (patEdit) {
      e.preventDefault();
      const id = Number(patEdit.getAttribute("data-pat-edit"));
      const cfg = (ALERTAS_DATA.configs || []).find((c) => Number(c.id) === id);
      if (cfg) {
        ALERTAS_PAT_CFG.form = {
          id: cfg.id,
          nombre: cfg.nombre || "",
          dias_min: String(cfg.dias_min ?? 0),
          dias_max: String(cfg.dias_max ?? 180),
          avisar_vence_hoy: cfg.avisar_vence_hoy !== 0 && cfg.avisar_vence_hoy !== false,
          avisar_paso_expirada: cfg.avisar_paso_expirada !== 0 && cfg.avisar_paso_expirada !== false,
          avisar_diario: cfg.avisar_diario !== 0 && cfg.avisar_diario !== false,
          intervalo_valor: valorIntervaloParaForm(cfg),
          intervalo_unidad: unidadIntervaloCriterio(cfg),
          fuente: String(cfg.fuente || "").toLowerCase() === "ema" ? "ema" : "fda",
          n_lista: cfg.n_lista != null ? String(cfg.n_lista) : "",
          medicamento_lista: cfg.medicamento_lista || "",
        };
        renderPatConfigModal();
      }
      return;
    }
    const patToggle = e.target.closest("[data-pat-toggle]");
    if (patToggle) {
      e.preventDefault();
      const id = Number(patToggle.getAttribute("data-pat-toggle"));
      const activo = patToggle.getAttribute("data-pat-activo") === "1";
      fetch("/api/alertas/patentes/configs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accion: "activar", id, activo }),
      })
        .then((r) => r.json())
        .then(async (data) => {
          if (!data?.ok) throw new Error(data?.error || "No se pudo actualizar");
          await cargarAlertasPatentes({ silent: true });
          if (ALERTAS_PAT_CFG.modalOpen) renderPatConfigModal();
          if (state.view === "alertas") renderAlertas({ soft: true });
          renderHeaderAlertas();
        })
        .catch((err) => {
          ALERTAS_PAT_CFG.error = err?.message || String(err);
          if (ALERTAS_PAT_CFG.modalOpen) renderPatConfigModal();
        });
      return;
    }
    const patDel = e.target.closest("[data-pat-del]");
    if (patDel) {
      e.preventDefault();
      const id = Number(patDel.getAttribute("data-pat-del"));
      if (!confirm("¿Eliminar este criterio?")) return;
      fetch("/api/alertas/patentes/configs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accion: "eliminar", id }),
      })
        .then((r) => r.json())
        .then(async (data) => {
          if (!data?.ok) throw new Error(data?.error || "No se pudo eliminar");
          if (ALERTAS_PAT_CFG.form.id === id) resetPatCfgForm();
          await cargarAlertasPatentes({ silent: true });
          if (ALERTAS_PAT_CFG.modalOpen) renderPatConfigModal();
          if (state.view === "alertas") renderAlertas({ soft: true });
          renderHeaderAlertas();
        })
        .catch((err) => {
          ALERTAS_PAT_CFG.error = err?.message || String(err);
          if (ALERTAS_PAT_CFG.modalOpen) renderPatConfigModal();
        });
      return;
    }
    const patEvaluar = e.target.closest("[data-pat-evaluar]");
    if (patEvaluar) {
      e.preventDefault();
      patEvaluar.disabled = true;
      fetch("/api/alertas/patentes/configs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accion: "evaluar" }),
      })
        .then((r) => r.json())
        .then(async (data) => {
          if (!data?.ok) throw new Error(data?.error || data?.mensaje || "No se pudo evaluar");
          await cargarAlertasPatentes({ silent: true });
          renderHeaderAlertas();
          if (ALERTAS_PAT_CFG.modalOpen) renderPatConfigModal();
          if (state.view === "alertas") renderAlertas({ soft: true });
          mostrarToastsCriteriosPatentes({
            nuevas: Number(data?.insertadas || 0),
            mensaje: data?.mensaje || "",
            forzar: true,
          });
        })
        .catch((err) => {
          ALERTAS_PAT_CFG.error = err?.message || String(err);
          if (ALERTAS_PAT_CFG.modalOpen) renderPatConfigModal();
        })
        .finally(() => {
          patEvaluar.disabled = false;
        });
      return;
    }
    const apDetectar = e.target.closest("[data-ap-detectar]");
    if (apDetectar) {
      e.preventDefault();
      if (ALERTAS_PRECIOS.detectando) return;
      ALERTAS_PRECIOS.detectando = true;
      renderAlertas({ soft: true });
      fetch("/api/alertas/precios/detectar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      })
        .then((r) => r.json())
        .then(async (data) => {
          if (!data?.ok) throw new Error(data?.error || data?.mensaje || "No se pudo evaluar");
          await cargarAlertasPrecios({ silent: true });
          mostrarToastsCriteriosPrecios({
            nuevas: Number(data?.insertadas || data?.nuevas || 0),
            mensaje: data?.mensaje || "",
            forzar: true,
          });
          arrancarRelojNotificacionesUiPatentes();
        })
        .catch((err) => {
          ALERTAS_PRECIOS.error = err?.message || String(err);
        })
        .finally(() => {
          ALERTAS_PRECIOS.detectando = false;
          if (state.view === "alertas") renderAlertas({ soft: true });
        });
      return;
    }
    const apLeerTodas = e.target.closest("[data-ap-leer-todas]");
    if (apLeerTodas) {
      e.preventDefault();
      fetch("/api/alertas/precios/leer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ todas: true }),
      })
        .then((r) => r.json())
        .then(async () => {
          await cargarAlertasPrecios({ silent: true });
          if (state.view === "alertas") renderAlertas({ soft: true });
        })
        .catch(() => {});
      return;
    }
    const apRead = e.target.closest("[data-ap-read]");
    if (apRead) {
      e.preventDefault();
      fetch("/api/alertas/precios/leer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: Number(apRead.dataset.apRead), leida: true }),
      })
        .then((r) => r.json())
        .then(async () => {
          await cargarAlertasPrecios({ silent: true });
          if (state.view === "alertas") renderAlertas({ soft: true });
        })
        .catch(() => {});
      return;
    }
    const apUnread = e.target.closest("[data-ap-unread]");
    if (apUnread) {
      e.preventDefault();
      fetch("/api/alertas/precios/leer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: Number(apUnread.dataset.apUnread), leida: false }),
      })
        .then((r) => r.json())
        .then(async () => {
          await cargarAlertasPrecios({ silent: true });
          if (state.view === "alertas") renderAlertas({ soft: true });
        })
        .catch(() => {});
      return;
    }
    const apReset = e.target.closest("[data-ap-reset]");
    if (apReset) {
      e.preventDefault();
      resetFormAlertaPrecio();
      cargarOpcionesAlertasPrecios()
        .then(() => {
          if (ALERTAS_PRECIOS.modalOpen) renderApConfigModal();
          else if (state.view === "alertas") renderAlertas({ soft: true });
        })
        .catch(() => {
          if (ALERTAS_PRECIOS.modalOpen) renderApConfigModal();
          else if (state.view === "alertas") renderAlertas({ soft: true });
        });
      return;
    }
    const apEdit = e.target.closest("[data-ap-edit]");
    if (apEdit) {
      e.preventDefault();
      const cfg = (ALERTAS_PRECIOS.configs || []).find((c) => String(c.id) === String(apEdit.dataset.apEdit));
      if (!cfg) return;
      ALERTAS_PRECIOS.form = {
        id: cfg.id,
        nombre: cfg.nombre || "",
        pais: cfg.pais || "",
        farmacia: cfg.farmacia || "",
        producto_key: cfg.producto_key || "",
        n_lista: cfg.n_lista != null ? String(cfg.n_lista) : "",
        medicamento_lista: cfg.medicamento_lista || "",
        nombre_comercial: cfg.nombre_comercial || "",
        presentacion: cfg.presentacion || "",
        concentracion: cfg.concentracion || "",
        umbral_baja_pct: cfg.umbral_baja_pct != null ? String(cfg.umbral_baja_pct) : "",
        umbral_sube_pct: cfg.umbral_sube_pct != null ? String(cfg.umbral_sube_pct) : "",
        intervalo_valor: valorIntervaloParaForm(cfg),
        intervalo_unidad: unidadIntervaloCriterio(cfg),
      };
      if (!ALERTAS_PRECIOS.modalOpen) openApConfigModal();
      cargarOpcionesAlertasPrecios()
        .then(() => {
          renderApConfigModal();
        })
        .catch(() => {
          renderApConfigModal();
        });
      return;
    }
    const apToggle = e.target.closest("[data-ap-toggle]");
    if (apToggle) {
      e.preventDefault();
      fetch("/api/alertas/precios/configs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          accion: "activar",
          id: Number(apToggle.dataset.apToggle),
          activo: apToggle.dataset.apActivo === "1",
        }),
      })
        .then((r) => r.json())
        .then(async () => {
          await cargarAlertasPrecios({ silent: true });
          if (state.view === "alertas") renderAlertas({ soft: true });
        })
        .catch(() => {});
      return;
    }
    const apDel = e.target.closest("[data-ap-del]");
    if (apDel) {
      e.preventDefault();
      if (!window.confirm("¿Eliminar este criterio?")) return;
      fetch("/api/alertas/precios/configs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accion: "eliminar", id: Number(apDel.dataset.apDel) }),
      })
        .then((r) => r.json())
        .then(async () => {
          if (String(ALERTAS_PRECIOS.form.id) === String(apDel.dataset.apDel)) resetFormAlertaPrecio();
          await cargarAlertasPrecios({ silent: true });
          if (state.view === "alertas") renderAlertas({ soft: true });
        })
        .catch(() => {});
      return;
    }
    const coverSort = e.target.closest("[data-cover-sort]");
    if (coverSort && state.coverPais) {
      const key = coverSort.dataset.coverSort;
      state.cdir = state.csort === key ? -state.cdir : 1;
      state.csort = key;
      repintarCoverActual();
      return;
    }
    if (e.target.closest("[data-nav='cover-prev']")) { state.cpage -= 1; repintarCoverActual(); return; }
    if (e.target.closest("[data-nav='cover-next']")) { state.cpage += 1; repintarCoverActual(); return; }
    const stage = $("stage");
    if (!stage || !stage.contains(e.target)) return;
    const prog = e.target.closest("[data-prog]");
    if (prog) {
      state.programa = prog.dataset.prog;
      state.page = 1;
      render();
      return;
    }
    if (e.target.closest("[data-comp-cerrar]")) {
      e.preventDefault();
      toggleCompCard(state.compAbierto);
      return;
    }
    const compCard = e.target.closest("[data-comp-card]");
    if (compCard) {
      e.preventDefault();
      toggleCompCard(compCard.dataset.compCard);
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
    if (e.target.closest("[data-nav='alertAct-prev']")) {
      state.alertActPage = Math.max(1, (state.alertActPage || 1) - 1);
      if (state.view === "alertas") renderAlertas({ soft: true });
      return;
    }
    if (e.target.closest("[data-nav='alertAct-next']")) {
      state.alertActPage = (state.alertActPage || 1) + 1;
      if (state.view === "alertas") renderAlertas({ soft: true });
      return;
    }
    if (e.target.closest("[data-nav='alertHist-prev']")) {
      state.alertHistPage = Math.max(1, (state.alertHistPage || 1) - 1);
      if (state.view === "alertas") renderAlertas({ soft: true });
      return;
    }
    if (e.target.closest("[data-nav='alertHist-next']")) {
      state.alertHistPage = (state.alertHistPage || 1) + 1;
      if (state.view === "alertas") renderAlertas({ soft: true });
      return;
    }
    if (e.target.closest("[data-nav='apHist-prev']")) {
      ALERTAS_PRECIOS.page = Math.max(1, (ALERTAS_PRECIOS.page || 1) - 1);
      if (state.view === "alertas") renderAlertas({ soft: true });
      return;
    }
    if (e.target.closest("[data-nav='apHist-next']")) {
      ALERTAS_PRECIOS.page = (ALERTAS_PRECIOS.page || 1) + 1;
      if (state.view === "alertas") renderAlertas({ soft: true });
      return;
    }
    const histSort = e.target.closest("[data-alerta-hist-sort]");
    if (histSort) {
      const key = histSort.dataset.alertaHistSort || "expiration_date";
      state.alertHistDir = state.alertHistSort === key ? -Number(state.alertHistDir || 1) : (key === "expiration_date" || key === "fecha_alerta" ? -1 : 1);
      state.alertHistSort = key;
      state.alertHistPage = 1;
      if (state.view === "alertas") renderAlertas({ soft: true });
      return;
    }
  });
  document.addEventListener("focusin", (e) => {
    if (e.target.id === "tendMedSearch") {
      const opt = tendMedSelectedOpt();
      const label = opt ? tendMedOptionLabel(opt) : "";
      if (label && e.target.value === label) {
        state.tendMedQ = "";
        try { e.target.select(); } catch (_) { /* ignore */ }
      } else {
        state.tendMedQ = e.target.value || "";
      }
      abrirTendMedPicker();
    }
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (state.tendPickerOpen) {
        cerrarTendMedPicker({ restoreLabel: true });
        return;
      }
      const patConfigModal = $("patConfigModal");
      if (patConfigModal && patConfigModal.classList.contains("is-open")) {
        closePatConfigModal();
        return;
      }
      const apConfigModal = $("apConfigModal");
      if (apConfigModal && apConfigModal.classList.contains("is-open")) {
        closeApConfigModal();
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
    const expandRow = e.target.closest?.("[data-tend-expand-fd]");
    if (expandRow && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault();
      const fd = expandRow.getAttribute("data-tend-expand-fd") || "";
      state.tendExpandFd = state.tendExpandFd === fd ? null : fd;
      aplicarVistaTendencia({ soloTabla: true });
      return;
    }
    const cover = e.target.closest("[data-cover-pais]");
    if (cover && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault();
      openCoverModal(cover.dataset.coverPais);
      return;
    }
    const compCard = e.target.closest("[data-comp-card]");
    if (compCard && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault();
      toggleCompCard(compCard.dataset.compCard);
    }
  });
  let TEND_MED_Q_TIMER = null;
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
      repintarCoverActual();
      const el = $("coverQ");
      if (el) {
        el.focus();
        el.setSelectionRange(state.cq.length, state.cq.length);
      }
    }
    if (e.target.id === "coverPaFilter") {
      filtrarCoverPaCards(e.target.value);
    }
    if (e.target.id === "expQ") {
      state.expQ = e.target.value || "";
      programarBusquedaExplorador();
    }
    if (e.target.id === "expPrecioMin" || e.target.id === "expPrecioMax") {
      const clave = e.target.id === "expPrecioMin" ? "expPrecioMin" : "expPrecioMax";
      state[clave] = e.target.value || "";
      programarBusquedaExplorador();
    }
  });
  document.addEventListener("mouseover", (e) => {
    const dot = e.target.closest?.(".tend-dot");
    const tip = $("tendTip");
    if (dot && tip && dot.dataset.tip) tip.textContent = dot.dataset.tip;
  });
  document.addEventListener("submit", (e) => {
    const patForm = e.target.closest?.("[data-pat-form]");
    if (patForm) {
      e.preventDefault();
      if (ALERTAS_PAT_CFG.guardando) return;
      guardarPatConfigDesdeForm(patForm);
      return;
    }
    const form = e.target.closest?.("[data-ap-form]");
    if (!form) return;
    e.preventDefault();
    if (ALERTAS_PRECIOS.guardando) return;
    const payload = leerFormAlertaPrecio(form);
    if (!payload.umbral_baja_pct && !payload.umbral_sube_pct) {
      ALERTAS_PRECIOS.error = "Indicá al menos un umbral de baja o de alza.";
      if (ALERTAS_PRECIOS.modalOpen) renderApConfigModal();
      else renderAlertas();
      return;
    }
    ALERTAS_PRECIOS.guardando = true;
    ALERTAS_PRECIOS.error = null;
    ALERTAS_PRECIOS.form = payload;
    if (ALERTAS_PRECIOS.modalOpen) renderApConfigModal();
    else renderAlertas();
    fetch("/api/alertas/precios/configs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id: payload.id || undefined,
        nombre: payload.nombre || null,
        n_lista: payload.n_lista ? Number(payload.n_lista) : null,
        medicamento_lista: payload.medicamento_lista || null,
        producto_key: payload.producto_key || null,
        nombre_comercial: payload.nombre_comercial || null,
        pais: payload.pais || null,
        farmacia: payload.farmacia || null,
        presentacion: payload.presentacion || null,
        concentracion: payload.concentracion || null,
        umbral_baja_pct: payload.umbral_baja_pct || null,
        umbral_sube_pct: payload.umbral_sube_pct || null,
        intervalo_valor: Number(payload.intervalo_valor || 24),
        intervalo_unidad: payload.intervalo_unidad === "minutos" ? "minutos" : "horas",
        activo: true,
      }),
    })
      .then((r) => r.json())
      .then(async (data) => {
        if (!data?.ok) throw new Error(data?.error || "No se pudo guardar");
        resetFormAlertaPrecio();
        await cargarAlertasPrecios({ silent: true });
        mostrarToastsCriteriosPrecios({ forzar: true });
        arrancarRelojNotificacionesUiPatentes();
      })
      .catch((err) => {
        ALERTAS_PRECIOS.error = err?.message || String(err);
      })
      .finally(() => {
        ALERTAS_PRECIOS.guardando = false;
        if (ALERTAS_PRECIOS.modalOpen) renderApConfigModal();
        if (state.view === "alertas") renderAlertas({ soft: true });
      });
  });
  document.addEventListener("change", (e) => {
    const expSelects = {
      expPais: "expPais",
      expFarmacia: "expFarmacia",
      expPrograma: "expPrograma",
      expFecha: "expFecha",
      expOrden: "expOrden",
      expModoPrecio: "expModoPrecio",
    };
    if (expSelects[e.target.id]) {
      state[expSelects[e.target.id]] = e.target.value;
      cargarExplorador();
      return;
    }
    if (e.target.id === "expMinPaises") {
      state.expMinPaises = Number(e.target.value) || 0;
      cargarExplorador();
      return;
    }
    if (e.target.id === "expSoloMin" || e.target.id === "expTodas") {
      state[e.target.id === "expSoloMin" ? "expSoloMin" : "expTodas"] = !!e.target.checked;
      cargarExplorador();
      return;
    }
    if (e.target.id === "tendPeriodo") {
      state.tendPeriodo = e.target.value || "diario";
      aplicarVistaTendencia();
      return;
    }
    if (e.target.id === "tendMedSearch") {
      state.tendMedQ = e.target.value || "";
      // Al escribir, no mantener selección previa como “texto fijo”: es búsqueda.
      abrirTendMedPicker();
      return;
    }
    if (e.target.id === "tendPaisSelect") {
      state.tendPaisFiltro = e.target.value || "todos";
      state.tendMedQ = "";
      state.tendenciaN = null;
      state.tendenciaProductoKey = null;
      state.tendenciaLabel = "";
      state.tendProductoSel = "";
      state.tendPresSel = "";
      state.tendConcSel = "";
      state.tendPickerOpen = false;
      TEND_DATA = null;
      renderTendencias();
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
    if (e.target.id === "filtroPais") {
      state.paisFiltro = e.target.value;
      // Sin país elegido el filtro de "más barato" no tiene referencia.
      if (state.paisFiltro === "todos") state.compSoloGana = false;
      state.page = 1;
      render();
      return;
    }
    if (e.target.id === "compSoloGana") {
      state.compSoloGana = !!e.target.checked;
      state.page = 1;
      render();
      return;
    }
    if (e.target.id === "compOrden") {
      const [key, dir] = String(e.target.value || "programa:1").split(":");
      state.sort = key;
      state.dir = Number(dir) === -1 ? -1 : 1;
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
      repintarCoverActual();
    }
    if (e.target.dataset.size === "alertAct") {
      state.alertActSize = Number(e.target.value) || 12;
      state.alertActPage = 1;
      if (state.view === "alertas") renderAlertas({ soft: true });
      return;
    }
    if (e.target.dataset.size === "alertHist") {
      state.alertHistSize = Number(e.target.value) || 12;
      state.alertHistPage = 1;
      if (state.view === "alertas") renderAlertas({ soft: true });
      return;
    }
    if (e.target.dataset.size === "apHist") {
      ALERTAS_PRECIOS.size = Number(e.target.value) || 12;
      ALERTAS_PRECIOS.page = 1;
      if (state.view === "alertas") renderAlertas({ soft: true });
      return;
    }
    if (e.target.matches("[data-ap-cascade], [data-ap-form] select, [data-ap-form] input")) {
      const form = e.target.closest("[data-ap-form]");
      if (!form) return;
      const prev = { ...ALERTAS_PRECIOS.form };
      ALERTAS_PRECIOS.form = leerFormAlertaPrecio(form);
      const cascade = e.target.getAttribute("data-ap-cascade");
      if (cascade === "pais") {
        ALERTAS_PRECIOS.form.farmacia = "";
        ALERTAS_PRECIOS.form.producto_key = "";
        ALERTAS_PRECIOS.form.n_lista = "";
        ALERTAS_PRECIOS.form.medicamento_lista = "";
        ALERTAS_PRECIOS.form.nombre_comercial = "";
        ALERTAS_PRECIOS.form.presentacion = "";
        ALERTAS_PRECIOS.form.concentracion = "";
      } else if (cascade === "farmacia") {
        ALERTAS_PRECIOS.form.producto_key = "";
        ALERTAS_PRECIOS.form.n_lista = "";
        ALERTAS_PRECIOS.form.medicamento_lista = "";
        ALERTAS_PRECIOS.form.nombre_comercial = "";
        ALERTAS_PRECIOS.form.presentacion = "";
        ALERTAS_PRECIOS.form.concentracion = "";
      } else if (cascade === "producto_key") {
        ALERTAS_PRECIOS.form.presentacion = "";
        ALERTAS_PRECIOS.form.concentracion = "";
      } else if (cascade === "presentacion") {
        ALERTAS_PRECIOS.form.concentracion = "";
      }
      // Preserve edit id / nombre / umbrales when cascading
      ALERTAS_PRECIOS.form.id = prev.id;
      const nombreEl = form.querySelector('[name="nombre"]');
      const bajaEl = form.querySelector('[name="umbral_baja_pct"]');
      const subeEl = form.querySelector('[name="umbral_sube_pct"]');
      ALERTAS_PRECIOS.form.nombre = String(nombreEl?.value ?? prev.nombre);
      ALERTAS_PRECIOS.form.umbral_baja_pct = String(bajaEl?.value ?? prev.umbral_baja_pct);
      ALERTAS_PRECIOS.form.umbral_sube_pct = String(subeEl?.value ?? prev.umbral_sube_pct);
      if (cascade) {
        cargarOpcionesAlertasPrecios()
          .then(() => {
            if (ALERTAS_PRECIOS.modalOpen) renderApConfigModal();
            else if (state.view === "alertas" && state.alertVista === "precios") renderAlertas({ soft: true });
          })
          .catch(() => {});
      }
      return;
    }
    if (e.target.matches("[data-alerta-fuente]")) {
      state.alertFuente = e.target.value === "ema" ? "ema" : "fda";
      resetAlertasPaginacion();
      cargarAlertasPatentes().then(() => {
        if (state.view === "alertas") renderAlertas({ soft: true });
      });
      return;
    }
    if (e.target.matches("[data-alerta-tipo]")) {
      const tipo = e.target.value || "todos";
      state.alertTipo = tipo === "paso_a_expirada" ? "todos" : tipo;
      resetAlertasPaginacion();
      cargarAlertasPatentes().then(() => {
        if (state.view === "alertas") renderAlertas({ soft: true });
      });
      return;
    }
    if (e.target.matches("[data-alerta-nuevas]")) {
      state.alertSoloNuevas = Boolean(e.target.checked);
      resetAlertasPaginacion();
      cargarAlertasPatentes().then(() => {
        if (state.view === "alertas") renderAlertas({ soft: true });
      });
      return;
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
  if (state.view === "comparativo") {
    state.tendVista = "comparativo";
    state.view = "tendencias";
  }
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
  await refrescarResumenAlertas();
  sanitizarPaisesDesactivados();
  syncRoute(state.view, true);
  render();
  // Toast de patentes que vencen hoy (una sola vez por patente/día).
  revisarToastsPatentesExpiradasHoy().catch(() => {});
  // Toast por criterio según intervalo (persiste entre recargas; reloj con la pestaña abierta).
  revisarNotificacionesUiPatentes();
  revisarNotificacionesUiPrecios();
  arrancarRelojNotificacionesUiPatentes();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", iniciar);
} else {
  iniciar();
}
