/**
 * Panel de gráficos interactivos (React + Recharts).
 * Conveniencia por tema: ranking con país líder destacado + detalle inline.
 * Otros gráficos: clic en barra → modal con evidencia del historial/fuente.
 */
import React, { useEffect, useMemo, useState } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import { createPortal } from "https://esm.sh/react-dom@18.3.1";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Brush,
  LabelList,
} from "https://esm.sh/recharts@2.15.0?deps=react@18.3.1,react-dom@18.3.1";

const PALETTE = ["#003eab", "#ea580c", "#0f766e", "#7c3aed", "#db2777", "#0891b2", "#ca8a04", "#4338ca"];
const BLUE = PALETTE[0];
const TEAL = PALETTE[2];
const PURPLE = PALETTE[3];
const LEADER = "#0f766e";

const PAIS_FLAG = {
  "República Dominicana": { id: "do", emoji: "🇩🇴" },
  "Rep. Dominicana": { id: "do", emoji: "🇩🇴" },
  Argentina: { id: "ar", emoji: "🇦🇷" },
  Brasil: { id: "br", emoji: "🇧🇷" },
  Colombia: { id: "co", emoji: "🇨🇴" },
  Perú: { id: "pe", emoji: "🇵🇪" },
  Peru: { id: "pe", emoji: "🇵🇪" },
  Chile: { id: "cl", emoji: "🇨🇱" },
  México: { id: "mx", emoji: "🇲🇽" },
  Mexico: { id: "mx", emoji: "🇲🇽" },
  "Costa Rica": { id: "cr", emoji: "🇨🇷" },
  Ecuador: { id: "ec", emoji: "🇪🇨" },
  Honduras: { id: "hn", emoji: "🇭🇳" },
  Guatemala: { id: "gt", emoji: "🇬🇹" },
  Nicaragua: { id: "ni", emoji: "🇳🇮" },
  Panamá: { id: "pa", emoji: "🇵🇦" },
  Panama: { id: "pa", emoji: "🇵🇦" },
  Uruguay: { id: "uy", emoji: "🇺🇾" },
  "El Salvador": { id: "sv", emoji: "🇸🇻" },
  Paraguay: { id: "py", emoji: "🇵🇾" },
  Venezuela: { id: "ve", emoji: "🇻🇪" },
  Guyana: { id: "gy", emoji: "🇬🇾" },
  "Trinidad y Tobago": { id: "tt", emoji: "🇹🇹" },
  Bolivia: { id: "bo", emoji: "🇧🇴" },
  "Estados Unidos": { id: "us", emoji: "🇺🇸" },
  Canadá: { id: "ca", emoji: "🇨🇦" },
  Canada: { id: "ca", emoji: "🇨🇦" },
};
const FLAG_SVG = new Set([
  "do", "br", "mx", "ar", "co", "pe", "cl", "cr", "ec", "hn", "gt", "ni", "pa", "uy", "sv",
  "py", "ve", "gy", "tt", "bo", "us", "ca",
]);

/** Colores característicos por país (acento de badges / chips). */
const PAIS_ACCENT = {
  do: "#002d62",
  ar: "#74acdf",
  br: "#009c3b",
  co: "#fcd116",
  pe: "#d91023",
  cl: "#0039a6",
  mx: "#006847",
  cr: "#002b7f",
  ec: "#ffd100",
  hn: "#0073cf",
  gt: "#4997d0",
  ni: "#0067c6",
  pa: "#da121a",
  uy: "#0038a8",
  sv: "#0f47af",
  py: "#0038a8",
  ve: "#cf142b",
  gy: "#009e49",
  tt: "#ce1126",
  bo: "#d52b1e",
  us: "#3c3b6e",
  ca: "#ff0000",
};

const h = React.createElement;

function metaPais(nombre) {
  return PAIS_FLAG[String(nombre || "").trim()] || null;
}

function flagPais(nombre) {
  const meta = metaPais(nombre);
  if (!meta) return null;
  if (FLAG_SVG.has(meta.id)) {
    return h("img", {
      className: "graf-flag",
      src: `/flags/${meta.id}.svg`,
      alt: "",
      width: 22,
      height: 16,
    });
  }
  return h("span", { className: "graf-flag is-emoji", "aria-hidden": "true" }, meta.emoji);
}

function accentPais(nombre) {
  const meta = metaPais(nombre);
  return (meta && PAIS_ACCENT[meta.id]) || "#64748b";
}

function celdaPais(nombre, extra) {
  return h(
    "span",
    { className: "graf-pais-cell" },
    flagPais(nombre),
    h("span", null, nombre || "—", extra || null),
  );
}

function fmtUsd(n) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  const num = Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `USD ${num}`;
}

function moneyNode(n) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  const num = Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return h(
    "span",
    { className: "money" },
    h("span", { className: "money-cur" }, "USD"),
    " ",
    num,
  );
}

function fmtLocal(precio, moneda) {
  if (precio == null) return "—";
  const n = Number(precio);
  if (Number.isNaN(n)) return "—";
  if (String(moneda || "").toUpperCase() === "USD") return moneyNode(n);
  return `${n.toLocaleString("en-US", { maximumFractionDigits: 2 })} ${moneda || ""}`.trim();
}

function Tip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return h(
    "div",
    { className: "graf-tip" },
    h("strong", null, label),
    payload.map((p) =>
      h(
        "div",
        { key: p.dataKey, style: { color: p.color || p.fill } },
        `${p.name || p.dataKey}: ${typeof p.value === "number" ? p.value.toLocaleString("es-DO") : p.value}`,
      ),
    ),
    h("div", { className: "graf-tip-hint" }, "Clic para ver el detalle"),
  );
}

function TipTema({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const row = payload[0]?.payload || {};
  return h(
    "div",
    { className: "graf-tip" },
    h("strong", null, label),
    payload.map((p) =>
      h(
        "div",
        { key: p.dataKey, style: { color: p.color || p.fill } },
        `${p.name || p.dataKey}: ${typeof p.value === "number" ? p.value.toLocaleString("es-DO") : p.value}`,
      ),
    ),
    row.es_lider
      ? h("div", { className: "graf-tip-hint graf-tip-hint--lider" }, "País más conveniente del tema")
      : null,
  );
}

function renderEvidenciaBloques({ columns, rows, sections, meta, nota }) {
  const bloques =
    Array.isArray(sections) && sections.length
      ? sections
      : [{ title: null, columns: columns || [], rows: rows || [] }];
  return h(
    React.Fragment,
    null,
    nota ? h("p", { className: "graf-tema-detail-nota" }, nota) : null,
    meta
      ? h(
          "div",
          { className: "graf-tema-detail-meta" },
          ...(Array.isArray(meta) ? meta : [meta]).map((m, i) =>
            h("span", { key: i, className: "graf-tema-detail-chip" }, m),
          ),
        )
      : null,
    ...bloques.map((sec, si) => {
      const secRows = sec.rows || [];
      const secCols = sec.columns || columns || [];
      const multi = bloques.length > 1;
      const tone = si % 4;
      return h(
        "section",
        {
          key: si,
          className: `graf-tema-detail-section tone-${tone}${multi ? " is-multi" : ""}`,
          "data-section": String(si + 1),
        },
        sec.title || multi
          ? h(
              "div",
              { className: "graf-tema-detail-section-head" },
              multi
                ? h("span", { className: "graf-tema-detail-section-index", "aria-hidden": "true" }, String(si + 1))
                : null,
              h(
                "div",
                { className: "graf-tema-detail-section-titles" },
                h("h4", null, sec.title || `Comparación ${si + 1}`),
                sec.subtitle ? h("p", { className: "muted" }, sec.subtitle) : null,
              ),
            )
          : null,
        !secRows.length
          ? h("p", { className: "muted graf-empty" }, "No hay filas de evidencia para este punto.")
          : h(
              "div",
              { className: "graf-modal-table-wrap" },
              h(
                "table",
                { className: "graf-modal-table" },
                h(
                  "thead",
                  null,
                  h(
                    "tr",
                    null,
                    secCols.map((c) => h("th", { key: c.key }, c.label)),
                  ),
                ),
                h(
                  "tbody",
                  null,
                  secRows.map((row, i) =>
                    h(
                      "tr",
                      {
                        key: row.key || i,
                        className: row.es_min ? "graf-row-min" : undefined,
                      },
                      secCols.map((c) =>
                        h(
                          "td",
                          { key: c.key, className: c.className || "" },
                          c.render ? c.render(row) : row[c.key] ?? "—",
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
      );
    }),
  );
}

function TemaYTick({ x, y, payload, lider }) {
  const name = payload?.value || "";
  const isLider = name && lider && name === lider;
  return h(
    "g",
    { transform: `translate(${x},${y})` },
    h(
      "text",
      {
        x: -6,
        y: 0,
        dy: 4,
        textAnchor: "end",
        fill: isLider ? LEADER : "#1e293b",
        fontSize: isLider ? 13 : 12,
        fontWeight: isLider ? 800 : 600,
      },
      isLider ? `★ ${name}` : name,
    ),
  );
}

function Panel({ title, subtitle, children, wide, action }) {
  return h(
    "section",
    { className: `graf-panel${wide ? " graf-panel--wide" : ""}` },
    h(
      "header",
      { className: "graf-panel-head" },
      h(
        "div",
        { className: "graf-panel-head-row" },
        h("div", null,
          h("h3", null, title),
          subtitle ? h("p", null, subtitle) : null,
        ),
        action || null,
      ),
    ),
    h("div", { className: "graf-panel-body" }, children),
  );
}

function renderOtrosPaises(row) {
  const o = row.precios_otros || {};
  const entries = Object.entries(o).slice(0, 6);
  if (!entries.length) return "—";
  return h(
    "ul",
    { className: "graf-otros-list" },
    entries.map(([k, v]) =>
      h(
        "li",
        { key: k, className: "graf-otros-item" },
        h("strong", null, k),
        h("span", null, moneyNode(v)),
      ),
    ),
  );
}

function EvidenciaModal({ open, title, subtitle, nota, columns, rows, sections, meta, onClose }) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === "Escape") onClose?.();
    };
    const prevBody = document.body.style.overflow;
    const prevHtml = document.documentElement.style.overflow;
    document.body.style.overflow = "hidden";
    document.documentElement.style.overflow = "hidden";
    document.documentElement.classList.add("graf-modal-open");
    document.addEventListener("keydown", onKey);
    requestAnimationFrame(() => {
      const backdrop = document.querySelector(".graf-modal-backdrop");
      if (backdrop) backdrop.scrollTop = 0;
    });
    return () => {
      document.body.style.overflow = prevBody;
      document.documentElement.style.overflow = prevHtml;
      document.documentElement.classList.remove("graf-modal-open");
      document.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  if (!open || typeof document === "undefined") return null;

  const bloques =
    Array.isArray(sections) && sections.length
      ? sections
      : [{ title: null, columns: columns || [], rows: rows || [] }];

  return createPortal(
    h(
      "div",
      {
        className: "graf-modal-backdrop",
        role: "presentation",
        onClick: (e) => {
          if (e.target === e.currentTarget) onClose?.();
        },
      },
      h(
        "div",
        {
          className: "graf-modal",
          role: "dialog",
          "aria-modal": "true",
          "aria-labelledby": "grafModalTitle",
        },
        h(
          "header",
          { className: "graf-modal-head" },
          h("div", null,
            h("h2", { id: "grafModalTitle" }, title),
            subtitle ? h("p", { className: "muted" }, subtitle) : null,
          ),
          h(
            "button",
            { type: "button", className: "graf-modal-close", onClick: onClose, "aria-label": "Cerrar" },
            "×",
          ),
        ),
        nota ? h("p", { className: "graf-modal-nota" }, nota) : null,
        h(
          "div",
          { className: "graf-modal-body" },
          meta
            ? h(
                "div",
                { className: "graf-modal-meta" },
                ...(Array.isArray(meta) ? meta : [meta]).map((m, i) =>
                  h("span", { key: i, className: "graf-modal-count" }, m),
                ),
              )
            : null,
          ...bloques.map((sec, si) => {
            const secRows = sec.rows || [];
            const secCols = sec.columns || columns || [];
            const multi = bloques.length > 1;
            return h(
              "section",
              { key: si, className: `graf-modal-section${multi ? " is-multi" : ""}` },
              sec.title || multi
                ? h(
                    "div",
                    { className: "graf-modal-section-head" },
                    multi
                      ? h("span", { className: "graf-modal-section-index", "aria-hidden": "true" }, String(si + 1))
                      : null,
                    h(
                      "div",
                      { className: "graf-modal-section-head-text" },
                      h("h3", null, sec.title || `Comparación ${si + 1}`),
                      sec.subtitle ? h("p", { className: "muted" }, sec.subtitle) : null,
                    ),
                  )
                : null,
              !secRows.length
                ? h("p", { className: "graf-modal-empty" }, "No hay filas de evidencia para este punto.")
                : h(
                    "div",
                    { className: "graf-modal-table-wrap" },
                    h(
                      "table",
                      { className: "graf-modal-table" },
                      h(
                        "thead",
                        null,
                        h(
                          "tr",
                          null,
                          secCols.map((c) => h("th", { key: c.key }, c.label)),
                        ),
                      ),
                      h(
                        "tbody",
                        null,
                        secRows.map((row, i) =>
                          h(
                            "tr",
                            {
                              key: row.key || i,
                              className: row.es_min ? "graf-row-min" : undefined,
                            },
                            secCols.map((c) =>
                              h(
                                "td",
                                { key: c.key, className: c.className || "" },
                                c.render ? c.render(row) : row[c.key] ?? "—",
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
            );
          }),
        ),
      ),
    ),
    document.body,
  );
}

function ChartPaises({ rows, onBarClick }) {
  const data = useMemo(
    () =>
      [...(rows || [])]
        .slice(0, 12)
        .map((r) => ({
          name: r.pais,
          veces: r.veces_mas_barato,
          pct: r.pct_mas_barato,
          promedio: r.precio_promedio_usd,
        }))
        .reverse(),
    [rows],
  );
  if (!data.length) return h("p", { className: "muted graf-empty" }, "Sin datos de países.");
  return h(
    ResponsiveContainer,
    { width: "100%", height: Math.max(320, data.length * 36) },
    h(
      BarChart,
      {
        data,
        layout: "vertical",
        margin: { top: 8, right: 24, left: 8, bottom: 8 },
        className: "graf-chart-clickable",
      },
      h(CartesianGrid, { strokeDasharray: "3 3", stroke: "#e2e8f0", horizontal: false }),
      h(XAxis, { type: "number", tick: { fill: "#64748b", fontSize: 12 } }),
      h(YAxis, {
        type: "category",
        dataKey: "name",
        width: 118,
        tick: { fill: "#1e293b", fontSize: 12, fontWeight: 600 },
      }),
      h(Tooltip, { content: Tip }),
      h(Bar, {
        dataKey: "veces",
        name: "Veces más barato",
        fill: BLUE,
        radius: [0, 8, 8, 0],
        barSize: 18,
        cursor: "pointer",
        onClick: (bar) => onBarClick?.(bar?.payload || bar),
      }),
    ),
  );
}

function ChartComparar({ comparar, onBarClick }) {
  const paises = comparar?.paises || [comparar?.pais_a, comparar?.pais_b].filter(Boolean);
  if (!comparar?.pares?.length || paises.length < 2) {
    return h(
      "p",
      { className: "muted graf-empty" },
      "No hay presentaciones comparables (misma dosis, forma y cantidad) con precio en todos los países elegidos.",
    );
  }
  const data = [...comparar.pares]
    .slice(0, 14)
    .map((p) => {
      const full = p.label || (p.presentacion ? `${p.principio} · ${p.presentacion}` : p.principio) || "";
      const row = {
        name: full.length > 42 ? `${full.slice(0, 40)}…` : full,
        _par: p,
      };
      const precios = p.precios || {};
      for (const pais of paises) {
        row[pais] = precios[pais] != null ? precios[pais] : (pais === comparar.pais_a ? p.precio_a : p.precio_b);
      }
      return row;
    })
    .reverse();

  return h(
    ResponsiveContainer,
    { width: "100%", height: Math.max(360, data.length * 38) },
    h(
      BarChart,
      {
        data,
        layout: "vertical",
        margin: { top: 8, right: 16, left: 8, bottom: 8 },
        className: "graf-chart-clickable",
        onClick: (state) => {
          const payload = state?.activePayload?.[0]?.payload;
          if (payload?._par) onBarClick?.(payload._par);
        },
      },
      h(CartesianGrid, { strokeDasharray: "3 3", stroke: "#e2e8f0", horizontal: false }),
      h(XAxis, {
        type: "number",
        tick: { fill: "#64748b", fontSize: 12 },
        tickFormatter: (v) => fmtUsd(v),
      }),
      h(YAxis, {
        type: "category",
        dataKey: "name",
        width: 210,
        tick: { fill: "#1e293b", fontSize: 11, fontWeight: 600 },
      }),
      h(Tooltip, {
        formatter: (v) => fmtUsd(v),
        contentStyle: { borderRadius: 10, border: "1px solid #d7e2ef" },
        content: ({ active, payload, label }) => {
          if (!active || !payload?.length) return null;
          return h(
            "div",
            { className: "graf-tip" },
            h("strong", null, label),
            payload.map((p) =>
              h("div", { key: p.dataKey, style: { color: p.color } }, `${p.dataKey}: ${fmtUsd(p.value)}`),
            ),
            h("div", { className: "graf-tip-hint" }, "Clic para ver farmacia y fuente"),
          );
        },
      }),
      h(Legend, { verticalAlign: "top", height: 28 }),
      ...paises.map((pais, i) =>
        h(Bar, {
          key: pais,
          dataKey: pais,
          fill: PALETTE[i % PALETTE.length],
          radius: [0, 6, 6, 0],
          barSize: Math.max(8, 14 - paises.length),
          cursor: "pointer",
          onClick: (bar) => onBarClick?.(bar?.payload?._par || bar?.payload),
        }),
      ),
    ),
  );
}

function ChartTema({ rows, conveniente }) {
  const data = useMemo(() => {
    const sorted = [...(rows || [])]
      .map((r) => ({
        name: r.pais,
        veces: Number(r.veces_mas_barato) || 0,
        pct: r.pct_mas_barato,
        promedio: r.precio_promedio_usd,
        casos: r.casos,
      }))
      .sort((a, b) => b.veces - a.veces || String(a.name).localeCompare(String(b.name), "es"));
    const topName =
      conveniente && String(conveniente).toLowerCase() !== "empate"
        ? conveniente
        : sorted[0]?.name || "";
    return sorted.map((r, i) => ({
      ...r,
      rank: i + 1,
      es_lider: Boolean(topName) && r.name === topName,
    }));
  }, [rows, conveniente]);

  if (!data.length) {
    return h(
      "p",
      { className: "muted graf-empty" },
      "No hay presentaciones comparables (≥2 países) para este tema en la última fecha disponible.",
    );
  }

  const lider = data.find((d) => d.es_lider) || data[0];
  const empate = String(conveniente || "").toLowerCase() === "empate";
  const maxVeces = Math.max(...data.map((d) => d.veces), 0);

  return h(
    "div",
    { className: "graf-tema-chart" },
    lider
      ? h(
          "div",
          { className: "graf-tema-lider", role: "status" },
          h("div", { className: "graf-tema-lider-badge", "aria-hidden": "true" }, "1°"),
          h(
            "div",
            { className: "graf-tema-lider-body" },
            h("span", { className: "graf-tema-lider-label" }, empate ? "Empate en conveniencia" : "País más conveniente"),
            h(
              "div",
              { className: "graf-tema-lider-name" },
              flagPais(lider.name),
              h("strong", null, empate ? `${lider.name} (entre los mejores)` : lider.name),
            ),
            h(
              "p",
              { className: "graf-tema-lider-meta" },
              `${lider.veces.toLocaleString("es-DO")} vez${lider.veces === 1 ? "" : "es"} con el PVP más bajo`,
              maxVeces > 0 && data.length > 1
                ? ` · lidera el ranking de ${data.length} países`
                : "",
            ),
          ),
        )
      : null,
    h(
      ResponsiveContainer,
      { width: "100%", height: Math.max(300, data.length * 42) },
      h(
        BarChart,
        {
          data,
          layout: "vertical",
          margin: { top: 8, right: 40, left: 8, bottom: 8 },
        },
        h(CartesianGrid, { strokeDasharray: "3 3", stroke: "#e2e8f0", horizontal: false }),
        h(XAxis, {
          type: "number",
          allowDecimals: false,
          domain: [0, Math.max(maxVeces + 1, 1)],
          tick: { fill: "#64748b", fontSize: 12 },
        }),
        h(YAxis, {
          type: "category",
          dataKey: "name",
          width: 138,
          tick: (props) => h(TemaYTick, { ...props, lider: lider?.name }),
        }),
        h(Tooltip, { content: TipTema }),
        h(
          Bar,
          {
            dataKey: "veces",
            name: "Veces más barato",
            radius: [0, 10, 10, 0],
            barSize: 22,
            isAnimationActive: true,
          },
          ...data.map((d) =>
            h(Cell, {
              key: d.name,
              fill: d.es_lider ? LEADER : d.veces > 0 ? PURPLE : "#cbd5e1",
            }),
          ),
          h(LabelList, {
            dataKey: "veces",
            position: "right",
            fill: "#334155",
            fontSize: 12,
            fontWeight: 700,
            formatter: (v) => (v > 0 ? String(v) : "0"),
          }),
        ),
      ),
    ),
  );
}

function IconPlus() {
  return h(
    "svg",
    { width: 16, height: 16, viewBox: "0 0 16 16", fill: "none", "aria-hidden": "true" },
    h("path", {
      d: "M8 3v10M3 8h10",
      stroke: "currentColor",
      strokeWidth: 2,
      strokeLinecap: "round",
    }),
  );
}

function IconMinus() {
  return h(
    "svg",
    { width: 14, height: 14, viewBox: "0 0 16 16", fill: "none", "aria-hidden": "true" },
    h("path", {
      d: "M3 8h10",
      stroke: "currentColor",
      strokeWidth: 2,
      strokeLinecap: "round",
    }),
  );
}

function corregirUrlKielsa(url) {
  const u = String(url || "").trim();
  if (!u || !/kielsa\.com/i.test(u)) return u;
  const m = u.match(/^(https?:\/\/(?:www\.)?kielsa\.com(?:\.[a-z]{2})?)\/producto\/[^/]+\/([^/?#]+)/i);
  if (m) return `${m[1]}/ProductDetails/${m[2]}`;
  return u.replace(
    /^(https?:\/\/(?:www\.)?kielsa\.com(?:\.[a-z]{2})?)\/productdetails?\//i,
    (_, origin) => `${origin}/ProductDetails/`,
  );
}

function corregirUrlInkafarma(url) {
  const u = String(url || "").trim();
  if (!u || !/inkafarma\.pe/i.test(u) || /\/producto\//i.test(u)) return u;
  try {
    const parsed = new URL(u);
    const parts = parsed.pathname.replace(/^\/+|\/+$/g, "").split("/").filter(Boolean);
    if (parts.length !== 1) return u;
    const slug = parts[0];
    if (!slug || /^(buscador|buscar|404|cart|login|categoria)$/i.test(slug)) return u;
    return `${parsed.origin}/producto/${slug}`;
  } catch (_) {
    return u;
  }
}

function linkFuente(url) {
  const href = corregirUrlInkafarma(corregirUrlKielsa(url));
  if (!href) return "—";
  return h(
    "a",
    {
      href,
      target: "_blank",
      rel: "noreferrer",
      className: "graf-src-icon",
      title: "Ver fuente",
      "aria-label": "Ver fuente",
    },
    h(
      "svg",
      {
        width: 16,
        height: 16,
        viewBox: "0 0 16 16",
        fill: "none",
        "aria-hidden": "true",
      },
      h("path", {
        d: "M6.5 3.5H3.5A1.5 1.5 0 0 0 2 5v7.5A1.5 1.5 0 0 0 3.5 14H11a1.5 1.5 0 0 0 1.5-1.5V9.5M9.5 2H14m0 0v4.5M14 2 7.5 8.5",
        stroke: "currentColor",
        strokeWidth: 1.6,
        strokeLinecap: "round",
        strokeLinejoin: "round",
      }),
    ),
  );
}

function App({ initial, onFilters, onReady }) {
  const [data, setData] = useState(initial || null);
  const [loading, setLoading] = useState(!initial);
  const [error, setError] = useState("");
  const [fecha, setFecha] = useState(initial?.fecha || "");
  const [seleccion, setSeleccion] = useState([]);
  const [modal, setModal] = useState(null);
  const [temas, setTemas] = useState([]);
  const [temaId, setTemaId] = useState("");
  const [temaData, setTemaData] = useState(null);
  const [temaLoading, setTemaLoading] = useState(false);
  const [paisesTema, setPaisesTema] = useState([]);
  const [readyOnce, setReadyOnce] = useState(!!initial);
  const readyNotified = React.useRef(!!initial);

  async function loadTemas(fd, keepId) {
    try {
      const qs = new URLSearchParams();
      if (fd) qs.set("fecha", fd);
      const res = await fetch(`/api/tendencias/temas?${qs}`);
      const json = await res.json();
      if (!json?.ok) return null;
      const list = json.temas || [];
      setTemas(list);
      const keep = keepId && list.some((t) => t.id === keepId) ? keepId : "";
      const prefer =
        keep ||
        (
          list.find((t) => /breast|mama|pulm|lung|carcinoma/i.test(`${t.id} ${t.label || ""}`) && Number(t.n_comparables || t.n_principios) >= 1) ||
          list.find((t) => Number(t.n_comparables) >= 1) ||
          list.find((t) => Number(t.n_principios) >= 2) ||
          list[0]
        )?.id ||
        "";
      if (prefer) setTemaId(prefer);
      return prefer || null;
    } catch (err) {
      console.warn("temas", err);
      return null;
    }
  }

  function defaultSeleccion(disponibles, prev) {
    const list = [...(disponibles || [])];
    if (!list.length) return [];
    const keep = (prev || []).filter((p) => list.includes(p));
    if (keep.length >= 2) return keep;
    // Por defecto todos los países con dato en el tema (badges activos).
    const prefer = "República Dominicana";
    if (list.includes(prefer)) {
      return [prefer, ...list.filter((p) => p !== prefer)];
    }
    return list;
  }

  async function loadTema(next = {}) {
    const tid = next.temaId ?? temaId;
    if (!tid) {
      setTemaData(null);
      setPaisesTema([]);
      return;
    }
    setTemaLoading(true);
    try {
      const f = next.fecha ?? fecha;
      const reset = Boolean(next.resetSeleccion);
      let sel = next.seleccion;

      // 1) Descubrir países del tema (sin forzar filtro) si cambiamos de tema o no hay selección.
      if (reset || !sel?.length) {
        const qs0 = new URLSearchParams();
        qs0.set("tema", tid);
        if (f) qs0.set("fecha", f);
        const res0 = await fetch(`/api/tendencias/temas?${qs0}`);
        const json0 = await res0.json();
        if (!json0?.ok) throw new Error(json0?.error || `HTTP ${res0.status}`);
        const disponibles = json0.paises || [];
        setPaisesTema(disponibles);
        sel = defaultSeleccion(disponibles, reset ? [] : seleccion);
        setSeleccion(sel);
        // Si el backend ya usó todos, reutilizamos; si no, pedimos con sel explícita.
        const backendSel = json0.paises_cmp || [];
        const same =
          sel.length === backendSel.length && sel.every((p, i) => p === backendSel[i]);
        if (same || sel.length < 2) {
          setTemaData(json0);
          onFilters?.({
            fecha: json0.fecha || f,
            paises_cmp: sel,
            pais_a: sel[0],
            pais_b: sel[1],
          });
          return;
        }
      }

      const qs = new URLSearchParams();
      qs.set("tema", tid);
      if (f) qs.set("fecha", f);
      for (const p of sel || []) {
        if (p) qs.append("pais", p);
      }
      const res = await fetch(`/api/tendencias/temas?${qs}`);
      const json = await res.json();
      if (!json?.ok) throw new Error(json?.error || `HTTP ${res.status}`);
      setPaisesTema(json.paises || paisesTema);
      setTemaData(json);
      if (json.paises_cmp?.length) {
        setSeleccion(json.paises_cmp);
      }
      onFilters?.({
        fecha: json.fecha || f,
        paises_cmp: json.paises_cmp || sel,
        pais_a: json.pais_a,
        pais_b: json.pais_b,
      });
    } catch (err) {
      console.error(err);
      setTemaData(null);
    } finally {
      setTemaLoading(false);
    }
  }

  async function load(next = {}) {
    setLoading(true);
    setError("");
    try {
      // Sin fecha en query → el backend toma la última disponible (hoy hacia atrás).
      const res = await fetch("/api/tendencias/graficos");
      const json = await res.json();
      if (!json?.ok) throw new Error(json?.error || `HTTP ${res.status}`);
      setData(json);
      const f = json.fecha || "";
      setFecha(f);
      const chosen =
        (await loadTemas(f, next.temaId || temaId)) ||
        next.temaId ||
        temaId;
      if (chosen) {
        await loadTema({
          fecha: f,
          temaId: chosen,
          resetSeleccion: next.resetSeleccion !== false && !next.seleccion,
          seleccion: next.seleccion,
        });
      }
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setLoading(false);
      setReadyOnce(true);
      if (!readyNotified.current) {
        readyNotified.current = true;
        try {
          onReady?.();
        } catch (_) {
          /* ignore */
        }
      }
    }
  }

  useEffect(() => {
    if (!initial) load({ resetSeleccion: true });
    else if (!readyNotified.current) {
      readyNotified.current = true;
      try {
        onReady?.();
      } catch (_) {
        /* ignore */
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const busy = loading || temaLoading;
  const blockingBoot = !readyOnce;
  const detalle = data?.detalle || {};
  const notaBase =
    temaData?.detalle?.nota ||
    detalle.nota ||
    "Datos del historial de scrapes (PVP publicado en farmacia).";
  const activos = new Set(seleccion);

  function openPais(payload) {
    const pais = payload?.name || payload?.pais;
    if (!pais) return;
    const rows = detalle.por_pais?.[pais] || [];
    setModal({
      title: `País más barato · ${pais}`,
      subtitle: `Fecha ${data?.fecha || "—"} · ${rows.length} principio(s) donde ${pais} ofrece el PVP mínimo`,
      nota: notaBase,
      columns: [
        { key: "principio", label: "Principio", className: "graf-td-principio" },
        {
          key: "presentacion",
          label: "Presentación",
          render: (row) => row.presentacion || "—",
        },
        { key: "nombre_comercial", label: "Producto", className: "graf-td-producto" },
        { key: "farmacia", label: "Farmacia" },
        {
          key: "precio_usd",
          label: "USD",
          className: "graf-td-usd",
          render: (row) => moneyNode(row.precio_usd),
        },
        {
          key: "otros",
          label: "Otros países (USD)",
          className: "graf-td-otros",
          render: renderOtrosPaises,
        },
        {
          key: "fuente",
          label: "Fuente",
          className: "graf-td-fuente",
          render: (row) => linkFuente(row.fuente_url),
        },
      ],
      rows,
    });
  }

  const colsParPais = [
    {
      key: "pais",
      label: "País",
      className: "graf-td-principio",
      render: (row) =>
        celdaPais(
          row.pais,
          row.es_min ? h("span", { className: "graf-badge-min" }, " más barato") : null,
        ),
    },
    { key: "nombre_comercial", label: "Producto", className: "graf-td-producto" },
    {
      key: "presentacion",
      label: "Presentación",
      render: (row) => row.presentacion || row.concentracion || "—",
    },
    { key: "farmacia", label: "Farmacia" },
    {
      key: "precio_usd",
      label: "USD",
      className: "graf-td-usd",
      render: (row) => moneyNode(row.precio_usd),
    },
    {
      key: "fuente",
      label: "Fuente",
      className: "graf-td-fuente",
      render: (row) => linkFuente(row.fuente_url),
    },
  ];

  function rowsFromPar(par) {
    const evidencia = par?.evidencia || {};
    const paises = Object.keys(evidencia).length
      ? Object.keys(evidencia)
      : Object.keys(par?.precios || {});
    const rows = paises.map((pais) => {
      const ev = evidencia[pais] || {};
      return {
        key: pais,
        pais,
        nombre_comercial: ev.nombre_comercial,
        farmacia: ev.farmacia,
        precio: ev.precio,
        moneda: ev.moneda,
        precio_usd: ev.precio_usd ?? (par.precios || {})[pais],
        fuente_url: ev.fuente_url,
        presentacion: ev.presentacion || par.presentacion || "",
        concentracion: ev.concentracion || "",
        es_min: par.mas_barato === pais,
      };
    });
    rows.sort((a, b) => (a.precio_usd || 0) - (b.precio_usd || 0));
    return rows;
  }

  function openPar(par) {
    if (!par) return;
    setModal({
      title: par.principio || "Principio",
      subtitle: [
        par.presentacion ? `Presentación: ${par.presentacion}` : null,
        `Comparación a ${data?.fecha || "—"}`,
        `más barato: ${par.mas_barato === "empate" ? "empate" : par.mas_barato}`,
      ].filter(Boolean).join(" · "),
      nota: notaBase,
      columns: colsParPais,
      rows: rowsFromPar(par),
    });
  }

  const temaDetalle = (() => {
    if (!temaData?.ok) return null;
    const tema = temaData.tema || {};
    const res = temaData.resumen || {};
    const sections = [];
    for (const bloque of temaData.tablas?.por_principio || []) {
      for (const par of bloque.pares || []) {
        sections.push({
          title: bloque.principio || par.principio || "Principio",
          subtitle: [
            par.presentacion ? `Presentación: ${par.presentacion}` : null,
            `más barato: ${par.mas_barato === "empate" ? "empate" : par.mas_barato || "—"}`,
          ]
            .filter(Boolean)
            .join(" · "),
          columns: colsParPais,
          rows: rowsFromPar(par),
        });
      }
    }
    return {
      title: tema.label || tema.label_es || tema.label_en || "Tema terapéutico",
      subtitle: [
        `Fecha ${temaData.fecha || "—"}`,
        "misma dosis · forma · cantidad",
        res.conveniente ? `más conveniente: ${res.conveniente}` : null,
      ]
        .filter(Boolean)
        .join(" · "),
      meta: [
        `Principios en tema: ${res.principios_tema ?? tema.n_principios ?? "—"}`,
        `Con precio: ${res.principios_con_precio ?? "—"}`,
        `Casos comparables: ${res.casos_comparables ?? sections.length}`,
        res.conveniente ? `Conveniente: ${res.conveniente}` : null,
      ].filter(Boolean),
      columns: colsParPais,
      sections,
    };
  })();

  function togglePais(pais) {
    const on = seleccion.includes(pais);
    let next;
    if (on) {
      if (seleccion.length <= 2) return; // mínimo 2 activos para comparar
      next = seleccion.filter((p) => p !== pais);
    } else {
      next = [...seleccion, pais];
    }
    setSeleccion(next);
    loadTema({ seleccion: next, temaId });
  }

  function setTodosPaises(on) {
    if (!paisesTema.length) return;
    if (on) {
      const next = defaultSeleccion(paisesTema, []);
      setSeleccion(next);
      loadTema({ seleccion: next, temaId });
      return;
    }
    // Apagar todos no tiene sentido; dejar 2 (RD + siguiente) si hay.
    const next = defaultSeleccion(paisesTema, []).slice(0, 2);
    setSeleccion(next);
    loadTema({ seleccion: next, temaId });
  }

  const toolbar = h(
    "div",
    { className: "graf-toolbar" },
    h(
      "label",
      { className: "filter-field graf-tema-field" },
      h("span", null, "Tema terapéutico"),
      h(
        "select",
        {
          className: "selectish",
          value: temaId,
          disabled: !temas.length || temaLoading,
          onChange: (e) => {
            const id = e.target.value;
            setTemaId(id);
            loadTema({ temaId: id, resetSeleccion: true });
          },
        },
        !temas.length
          ? h("option", { value: "" }, "Sin temas EMA")
          : temas.map((t) =>
              h(
                "option",
                { key: t.id, value: t.id },
                `${t.label || t.label_es || t.id} (${t.n_comparables ?? t.n_principios ?? 0} comparables)`,
              ),
            ),
      ),
    ),
    fecha
      ? h(
          "p",
          { className: "muted graf-fecha-meta", title: "Última fecha con datos en el historial" },
          `Datos al ${fecha}`,
        )
      : null,
  );

  const controlsMount =
    typeof document !== "undefined" ? document.getElementById("grafControlsMount") : null;
  const toolbarNode = controlsMount ? createPortal(toolbar, controlsMount) : toolbar;

  return h(
    "div",
    { className: `graf-react${busy || blockingBoot ? " is-busy" : ""}` },
    busy || blockingBoot
      ? h(
          "div",
          { className: "graf-react-busy", role: "status", "aria-live": "polite" },
          h("div", { className: "tend-tab-spinner", "aria-hidden": "true" }),
          h(
            "p",
            null,
            blockingBoot
              ? "Cargando indicadores del tema…"
              : temaLoading
                ? "Actualizando comparación por tema…"
                : "Actualizando gráficos…",
          ),
        )
      : null,
    toolbarNode,
    h(
      "div",
      {
        className: "graf-react-body",
        inert: busy || blockingBoot ? "" : undefined,
        "aria-hidden": busy || blockingBoot ? "true" : undefined,
      },
    h(
      "div",
      { className: "graf-pais-badges", role: "group", "aria-label": "Países del tema" },
      h(
        "div",
        { className: "graf-pais-badges-head" },
        h("span", { className: "graf-pais-badges-label" }, "Países con precio en este tema"),
        h(
          "span",
          { className: "muted graf-pais-badges-meta" },
          paisesTema.length
            ? `${seleccion.length} de ${paisesTema.length} activos · clic para activar/desactivar`
            : temaLoading
              ? "Cargando países…"
              : "Sin países con precio",
        ),
        paisesTema.length
          ? h(
              "button",
              {
                type: "button",
                className: "graf-pais-badges-all",
                onClick: () => setTodosPaises(seleccion.length < paisesTema.length),
              },
              seleccion.length < paisesTema.length ? "Activar todos" : "Solo 2",
            )
          : null,
      ),
      h(
        "div",
        { className: "graf-pais-badges-row" },
        paisesTema.map((pais) => {
          const active = activos.has(pais);
          const accent = accentPais(pais);
          const meta = metaPais(pais);
          return h(
            "button",
            {
              type: "button",
              key: pais,
              className: `graf-pais-badge${active ? " is-on" : ""}`,
              "data-pais": meta?.id || undefined,
              "aria-pressed": active,
              style: {
                "--pais-accent": accent,
              },
              title: active
                ? seleccion.length <= 2
                  ? "Mínimo 2 países activos"
                  : `Quitar ${pais} de la comparación`
                : `Incluir ${pais} en la comparación`,
              onClick: () => togglePais(pais),
            },
            flagPais(pais),
            h("span", { className: "graf-pais-badge-name" }, pais),
          );
        }),
      ),
    ),
    error
      ? h("p", { className: "muted", style: { padding: "12px 18px" } }, `Error: ${error}`)
      : null,
    loading && !data && !temaData
      ? h("p", { className: "muted graf-empty" }, "Cargando indicadores…")
      : h(
          "div",
          { className: "graf-grid" },
          h(
            Panel,
            {
              title: "Conveniencia por tema",
              subtitle:
                (temaData?.tema?.label || "Tema EMA") +
                ` · ${seleccion.length} país(es) activos` +
                " · misma dosis, forma y cantidad (≥2 países). Ranking: más veces con el PVP más bajo.",
              wide: true,
            },
            h(ChartTema, {
              rows: temaData?.tablas?.paises,
              conveniente: temaData?.resumen?.conveniente,
            }),
          ),
          temaDetalle
            ? h(
                Panel,
                {
                  title: `Detalle · ${temaDetalle.title}`,
                  subtitle: temaDetalle.subtitle,
                  wide: true,
                },
                h(
                  "div",
                  { className: "graf-tema-detail", id: "graf-tema-detalle" },
                  temaLoading
                    ? h("p", { className: "muted graf-empty" }, "Cargando detalle…")
                    : !temaDetalle.sections?.length
                      ? h(
                          "p",
                          { className: "muted graf-empty" },
                          "No hay presentaciones comparables para mostrar en detalle.",
                        )
                      : renderEvidenciaBloques(temaDetalle),
                ),
              )
            : null,
        ),
      ),
    h(EvidenciaModal, {
      open: !!modal,
      title: modal?.title,
      subtitle: modal?.subtitle,
      nota: modal?.nota,
      columns: modal?.columns || [],
      rows: modal?.rows || [],
      sections: modal?.sections,
      meta: modal?.meta,
      onClose: () => setModal(null),
    }),
  );
}

const roots = new WeakMap();

export function mountGraficos(el, opts = {}) {
  if (!el) return null;
  let root = roots.get(el);
  if (!root) {
    root = createRoot(el);
    roots.set(el, root);
  }
  root.render(
    h(App, {
      initial: opts.initial || null,
      onFilters: opts.onFilters,
      onReady: opts.onReady,
    }),
  );
  return root;
}

export function unmountGraficos(el) {
  const root = roots.get(el);
  if (root) {
    root.unmount();
    roots.delete(el);
  }
}

/* ─── Serie por medicamento (línea / área / barras + zoom) ─── */

const serieRoots = new WeakMap();

function fmtUsdSerie(n, { decimals } = {}) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  const d = decimals != null ? decimals : 2;
  const num = Number(n).toLocaleString("en-US", {
    minimumFractionDigits: d,
    maximumFractionDigits: d,
  });
  return `USD ${num}`;
}

/** Dominio Y ajustado al rango real (con padding) para que variaciones de centavos se vean. */
function dominioYSerie(data, keys) {
  const vals = [];
  for (const row of data || []) {
    for (const k of keys || []) {
      const v = row?.[k.key];
      if (v != null && !Number.isNaN(Number(v))) vals.push(Number(v));
    }
  }
  if (!vals.length) return ["auto", "auto"];
  let min = Math.min(...vals);
  let max = Math.max(...vals);
  const span = max - min;
  // Padding generoso en % del rango; si el rango es ~0 (centavos o plano), usar banda absoluta.
  let pad;
  if (span < 1e-9) {
    pad = Math.max(Math.abs(min) * 0.01, 0.25);
  } else if (span < 1) {
    // Variación de centavos / pocos dólares: ampliar ~40% + mínimo 0.15
    pad = Math.max(span * 0.4, 0.15);
  } else if (span < 10) {
    pad = Math.max(span * 0.25, 0.5);
  } else {
    pad = span * 0.12;
  }
  min = min - pad;
  max = max + pad;
  // Evitar negativo en precios salvo que el dato lo sea
  if (Math.min(...vals) >= 0 && min < 0) min = 0;
  // Si quedó casi plano tras clamp a 0, forzar un poco de aire arriba
  if (max - min < 0.2) max = min + 0.5;
  return [min, max];
}

function decimalesEjeY(domain) {
  if (!Array.isArray(domain) || domain[0] === "auto") return 2;
  const span = Number(domain[1]) - Number(domain[0]);
  if (!(span > 0)) return 2;
  if (span < 2) return 3;
  if (span < 20) return 2;
  return 0;
}

function SerieTip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return h(
    "div",
    { className: "graf-tip tend-serie-recharts-tip" },
    h("strong", null, label),
    ...payload
      .filter((p) => p.value != null && !Number.isNaN(Number(p.value)))
      .map((p) =>
        h(
          "div",
          { key: p.dataKey, style: { color: p.color || "#003eab" } },
          `${p.name || p.dataKey}: ${fmtUsdSerie(p.value)}`,
        ),
      ),
  );
}

function TendSerieChartApp({ fechas, series, labels, chartTipo, onTipo }) {
  const tipo = chartTipo || "line";
  const [brushRange, setBrushRange] = useState(null);
  const keys = (series || []).map((s, i) => ({
    key: `s${i}`,
    name: s.label || s.farmacia || s.pais || `Serie ${i + 1}`,
    color: PALETTE[i % PALETTE.length],
  }));

  const data = useMemo(() => {
    const rows = [];
    for (const fd of fechas || []) {
      const row = { fd, label: (labels && labels[fd]) || String(fd).slice(0, 10) };
      (series || []).forEach((s, i) => {
        const pts = s.puntos || [];
        const dia = String(fd).slice(0, 10);
        const pt = pts.find((p) => {
          if (String(p.fecha) === String(fd)) return true;
          const desde = String(p.fecha).slice(0, 10);
          const hasta = String(p.vigente_hasta || p.fecha).slice(0, 10);
          return desde <= dia && dia <= hasta;
        });
        let v = null;
        if (pt) {
          const raw = pt.precio_usd ?? pt.precio;
          v = raw == null || Number.isNaN(Number(raw)) ? null : Number(raw);
        }
        row[`s${i}`] = v;
      });
      rows.push(row);
    }
    return rows;
  }, [fechas, series, labels]);

  const dataForY = useMemo(() => {
    if (!brushRange || !data.length) return data;
    const start = Math.max(0, Number(brushRange.startIndex) || 0);
    const end = Math.min(data.length - 1, Number(brushRange.endIndex) ?? data.length - 1);
    if (end < start) return data;
    return data.slice(start, end + 1);
  }, [data, brushRange]);

  const yDomain = useMemo(() => dominioYSerie(dataForY, keys), [dataForY, keys]);
  const yDecimals = useMemo(() => decimalesEjeY(yDomain), [yDomain]);

  const Chart = tipo === "bar" ? BarChart : tipo === "area" ? AreaChart : LineChart;

  const seriesEls = keys.map((k) => {
    if (tipo === "bar") {
      return h(Bar, {
        key: k.key,
        dataKey: k.key,
        name: k.name,
        fill: k.color,
        maxBarSize: 28,
        isAnimationActive: false,
      });
    }
    if (tipo === "area") {
      return h(Area, {
        key: k.key,
        type: "monotone",
        dataKey: k.key,
        name: k.name,
        stroke: k.color,
        fill: k.color,
        fillOpacity: 0.12,
        strokeWidth: 2,
        dot: { r: 2.5 },
        connectNulls: false,
        isAnimationActive: false,
      });
    }
    return h(Line, {
      key: k.key,
      type: "monotone",
      dataKey: k.key,
      name: k.name,
      stroke: k.color,
      strokeWidth: 2.2,
      dot: { r: 3 },
      activeDot: { r: 5 },
      connectNulls: false,
      isAnimationActive: false,
    });
  });

  return h(
    "div",
    { className: "tend-serie-recharts" },
    h(
      "div",
      { className: "tend-serie-recharts-toolbar" },
      h("span", { className: "tend-serie-recharts-label" }, "Formato"),
      ...["line", "area", "bar"].map((t) =>
        h(
          "button",
          {
            key: t,
            type: "button",
            className: `tend-chart-tipo${tipo === t ? " is-on" : ""}`,
            onClick: () => onTipo?.(t),
          },
          t === "line" ? "Líneas" : t === "area" ? "Área" : "Barras",
        ),
      ),
      h("span", { className: "muted tend-serie-recharts-hint" }, "Arrastra la barra inferior para hacer zoom"),
    ),
    h(
      "div",
      { className: "tend-serie-recharts-frame" },
      !data.length || !keys.length
        ? h("p", { className: "muted" }, "Activa al menos un país y una farmacia para ver el gráfico.")
        : h(
            ResponsiveContainer,
            { width: "100%", height: 360 },
            h(
              Chart,
              { data, margin: { top: 12, right: 16, left: 8, bottom: 8 } },
              h(CartesianGrid, { strokeDasharray: "3 3", stroke: "#e2e8f0" }),
              h(XAxis, {
                dataKey: "label",
                tick: { fill: "#64748b", fontSize: 11 },
                interval: "preserveStartEnd",
                minTickGap: 28,
              }),
              h(YAxis, {
                domain: yDomain,
                allowDataOverflow: false,
                tick: { fill: "#64748b", fontSize: 11 },
                tickFormatter: (v) => fmtUsdSerie(v, { decimals: yDecimals }),
                width: 86,
              }),
              h(Tooltip, { content: SerieTip }),
              h(Legend, { wrapperStyle: { fontSize: 12 } }),
              ...seriesEls,
              h(Brush, {
                dataKey: "label",
                height: 28,
                stroke: "#003eab",
                travellerWidth: 8,
                onChange: (range) => {
                  if (!range) {
                    setBrushRange(null);
                    return;
                  }
                  setBrushRange({
                    startIndex: range.startIndex,
                    endIndex: range.endIndex,
                  });
                },
              }),
            ),
          ),
    ),
  );
}

export function mountTendSerieChart(el, opts = {}) {
  if (!el) return null;
  let root = serieRoots.get(el);
  if (!root) {
    root = createRoot(el);
    serieRoots.set(el, root);
  }
  root.render(
    h(TendSerieChartApp, {
      fechas: opts.fechas || [],
      series: opts.series || [],
      labels: opts.labels || {},
      chartTipo: opts.chartTipo || "line",
      onTipo: opts.onTipo,
    }),
  );
  return root;
}

export function unmountTendSerieChart(el) {
  const root = serieRoots.get(el);
  if (root) {
    root.unmount();
  }
  serieRoots.delete(el);
}
