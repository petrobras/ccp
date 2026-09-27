/* ccp web client: theme tweaks, Plotly mounting, gas table, shortcuts. */
(function () {
  "use strict";

  // ------------------------------------------------------------ tweaks
  const TWEAKS_KEY = "ccp-tweaks";
  const PALETTES = {
    graphite: { hue: 260, chroma: 0.02 },
    indigo: { hue: 258, chroma: 0.14 },
    teal: { hue: 186, chroma: 0.11 },
    amber: { hue: 65, chroma: 0.14 },
    rose: { hue: 15, chroma: 0.17 },
    moss: { hue: 145, chroma: 0.09 },
  };
  const DEFAULTS = { mode: "light", palette: "indigo", typeface: "geist", density: "comfortable", accentHue: null };

  function loadTweaks() {
    try {
      return Object.assign({}, DEFAULTS, JSON.parse(localStorage.getItem(TWEAKS_KEY) || "{}"));
    } catch (_) {
      return Object.assign({}, DEFAULTS);
    }
  }

  function applyTweaks(t) {
    const html = document.documentElement;
    html.setAttribute("data-mode", t.mode);
    html.setAttribute("data-type", t.typeface);
    html.setAttribute("data-density", t.density);
    const p = PALETTES[t.palette] || PALETTES.indigo;
    const hue = t.accentHue != null ? t.accentHue : p.hue;
    const dark = t.mode === "dark";
    html.style.setProperty("--hue", hue);
    html.style.setProperty("--accent", `oklch(${dark ? 68 : 52}% ${p.chroma} ${hue})`);
    html.style.setProperty("--accent-2", `oklch(${dark ? 30 : 94}% ${Math.min(p.chroma * 0.5, 0.05)} ${hue})`);
    html.style.setProperty("--accent-ink", `oklch(${dark ? 92 : 30}% ${p.chroma} ${hue})`);
  }

  window.ccpTweaks = function () {
    return {
      open: false,
      t: loadTweaks(),
      palettes: PALETTES,
      set(key, value) {
        this.t[key] = value;
        if (key === "palette") this.t.accentHue = PALETTES[value].hue;
        this.save();
      },
      hue() {
        const p = PALETTES[this.t.palette] || PALETTES.indigo;
        return this.t.accentHue != null ? this.t.accentHue : p.hue;
      },
      setHue(v) {
        this.t.accentHue = Number(v);
        this.save();
      },
      toggleMode() {
        this.set("mode", this.t.mode === "dark" ? "light" : "dark");
      },
      save() {
        applyTweaks(this.t);
        try {
          localStorage.setItem(TWEAKS_KEY, JSON.stringify(this.t));
        } catch (_) {}
        document.dispatchEvent(new CustomEvent("ccp:theme"));
      },
    };
  };

  applyTweaks(loadTweaks());

  // ------------------------------------------------------------ plotly
  // Plotly cannot parse oklch(); resolve colour tokens to rgb() through a canvas.
  const colorCanvas = document.createElement("canvas");
  colorCanvas.width = colorCanvas.height = 1;
  const colorCtx = colorCanvas.getContext("2d", { willReadFrequently: true });

  function toRgb(color) {
    if (!color || !colorCtx) return color;
    colorCtx.clearRect(0, 0, 1, 1);
    colorCtx.fillStyle = "#000";
    colorCtx.fillStyle = color;
    colorCtx.fillRect(0, 0, 1, 1);
    const [r, g, b, a] = colorCtx.getImageData(0, 0, 1, 1).data;
    return a === 255 ? `rgb(${r},${g},${b})` : `rgba(${r},${g},${b},${(a / 255).toFixed(3)})`;
  }

  function cssVar(name) {
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return name.startsWith("--font") ? value : toRgb(value);
  }

  function themeLayout(layout) {
    const ink2 = cssVar("--ink-2") || "#333";
    const ink3 = cssVar("--ink-3") || "#666";
    const rule = cssVar("--rule") || "#ddd";
    const soft = cssVar("--rule-soft") || "#eee";
    const font = cssVar("--font-sans") || "sans-serif";
    const out = Object.assign({}, layout);
    out.paper_bgcolor = "rgba(0,0,0,0)";
    out.plot_bgcolor = "rgba(0,0,0,0)";
    out.font = Object.assign({}, out.font || {}, { color: ink2, family: font });
    out.autosize = true;
    delete out.width;
    delete out.height;
    out.margin = Object.assign({ l: 60, r: 20, t: 40, b: 50 }, out.margin || {});
    if (out.title && typeof out.title === "object") {
      out.title = Object.assign({}, out.title, { font: Object.assign({}, out.title.font || {}, { color: ink2, size: 13 }) });
    }
    out.modebar = { bgcolor: "rgba(0,0,0,0)", color: cssVar("--ink-4"), activecolor: cssVar("--accent") };
    // The ccp template draws a black mirrored frame; recolour it even when
    // the figure layout does not name the axes itself.
    ["xaxis", "yaxis"].forEach((k) => {
      if (!out[k]) out[k] = {};
    });
    Object.keys(out).forEach((k) => {
      if (/^[xy]axis\d*$/.test(k)) {
        out[k] = Object.assign({}, out[k], {
          gridcolor: soft,
          linecolor: rule,
          zerolinecolor: rule,
          tickfont: Object.assign({}, (out[k] || {}).tickfont || {}, { color: ink3 }),
        });
      }
    });
    if (out.legend) {
      out.legend = Object.assign({}, out.legend, { bgcolor: "rgba(0,0,0,0)", font: { color: ink2, size: 11 } });
    }
    (out.annotations || []).forEach((a) => {
      if (a.bgcolor) a.bgcolor = cssVar("--panel");
      a.font = Object.assign({}, a.font || {}, { color: ink2 });
    });
    return out;
  }

  const mounted = new Set();

  window.ccpPlot = function (el) {
    const script = el.querySelector('script[type="application/json"]');
    if (!script || typeof Plotly === "undefined") return;
    let fig;
    try {
      fig = JSON.parse(script.textContent);
    } catch (e) {
      el.textContent = "Could not read figure";
      return;
    }
    el._ccpFigure = fig;
    const render = () => {
      const layout = themeLayout(fig.layout || {});
      Plotly.react(el, fig.data || [], layout, { responsive: true, displaylogo: false });
    };
    render();
    el._ccpRender = render;
    mounted.add(el);
  };

  document.addEventListener("ccp:theme", () => {
    mounted.forEach((el) => {
      if (!document.body.contains(el)) {
        mounted.delete(el);
        return;
      }
      el._ccpRender && el._ccpRender();
    });
  });

  // Plotly needs a resize when a hidden tab or collapsed section is shown.
  window.ccpResizePlots = function (root) {
    if (typeof Plotly === "undefined") return;
    (root || document).querySelectorAll(".plot.js-plotly-plot").forEach((el) => {
      if (el.offsetParent !== null) Plotly.Plots.resize(el);
    });
  };

  // ------------------------------------------------------------ gas table
  window.ccpGasTable = function (initial) {
    return {
      names: initial.names,
      rows: initial.rows.map((r) => ({ component: r[0], values: r[1].map((v) => (v === 0 ? "" : String(v))) })),
      fluids: initial.fluids,
      hues: [255, 186, 65, 15, 145, 300],
      num(v) {
        const n = parseFloat(String(v).replace(",", "."));
        return isNaN(n) ? 0 : n;
      },
      total(i) {
        return this.rows.reduce((s, r) => s + this.num(r.values[i]), 0);
      },
      totalOk(i) {
        const t = this.total(i);
        return t === 0 || Math.abs(t - 100) < 0.5 || Math.abs(t - 1) < 0.005;
      },
      bar(r, i) {
        const max = Math.max(...r.values.map((v) => this.num(v)));
        return max > 0 ? (this.num(r.values[i]) / max) * 0.65 : 0;
      },
      addRow() {
        this.rows.push({ component: "", values: this.names.map(() => "") });
        this.changed();
      },
      removeRow(idx) {
        this.rows.splice(idx, 1);
        this.changed();
      },
      normalize() {
        this.names.forEach((_, i) => {
          const t = this.total(i);
          if (t > 0) {
            this.rows.forEach((r) => {
              const v = this.num(r.values[i]);
              r.values[i] = v ? String(+((v * 100) / t).toFixed(5)) : "";
            });
          }
        });
        this.changed();
      },
      changed() {
        this.$nextTick(() => {
          const form = this.$root.closest("form");
          if (form) form.dispatchEvent(new Event("change", { bubbles: true }));
        });
      },
    };
  };

  // ------------------------------------------------------------ errors
  window.ccpMarkErrors = function (errors) {
    document.querySelectorAll(".invalid[data-job-error]").forEach((el) => {
      el.classList.remove("invalid");
      el.removeAttribute("data-job-error");
    });
    let first = null;
    Object.entries(errors || {}).forEach(([key, message]) => {
      document.querySelectorAll(`[name="${CSS.escape(key)}"]:not([type=hidden])`).forEach((el) => {
        el.classList.add("invalid");
        el.setAttribute("data-job-error", "1");
        el.title = message;
        const field = el.closest(".field");
        if (field) field.classList.add("invalid");
        first = first || el;
      });
    });
    if (first) {
      const section = first.closest(".section");
      if (section && section.__x_collapsed !== undefined) section.__x_collapsed = false;
    }
  };

  // Save the whole case form now, then reload (used by switches that change
  // which sections the server renders, such as the data source).
  window.ccpSaveAndReload = function (formId) {
    const form = document.getElementById(formId || "case-form");
    const token = document.querySelector('meta[name="csrf-token"]');
    fetch(form.getAttribute("hx-post"), {
      method: "POST",
      body: new FormData(form),
      headers: { "X-CSRFToken": token ? token.content : "" },
      credentials: "same-origin",
    }).then(() => window.location.reload());
  };

  // ------------------------------------------------------------ shortcuts
  window.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      const btn = document.getElementById("runBtn");
      if (btn && !btn.disabled) {
        e.preventDefault();
        btn.click();
      }
    }
  });

  // ------------------------------------------------------------ tooltips
  // One positioned tooltip for ⓘ icons ([data-help]) and title attributes.
  // Native title tooltips are delayed and do not show in some webviews or
  // Wayland browsers; sections clip overflow, so the tip is position: fixed.
  let tip = null;
  let tipFor = null;

  function tipTarget(el) {
    const t = el && el.closest ? el.closest("[data-help], [title]") : null;
    if (t && t.hasAttribute("title")) {
      // Move the title so the native tooltip does not show as well.
      if (t.getAttribute("title")) t.setAttribute("data-help", t.getAttribute("title"));
      t.removeAttribute("title");
    }
    return t && t.getAttribute("data-help") ? t : null;
  }

  function showTip(el) {
    if (!tip) {
      tip = document.createElement("div");
      tip.className = "tip";
      tip.setAttribute("role", "tooltip");
      document.body.appendChild(tip);
    }
    tipFor = el;
    tip.textContent = el.getAttribute("data-help");
    tip.classList.add("show");
    const r = el.getBoundingClientRect();
    const w = tip.offsetWidth;
    const h = tip.offsetHeight;
    const left = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), window.innerWidth - w - 8);
    const top = r.top - h - 6 < 8 ? r.bottom + 6 : r.top - h - 6;
    tip.style.left = `${left}px`;
    tip.style.top = `${top}px`;
  }

  function hideTip() {
    tipFor = null;
    if (tip) tip.classList.remove("show");
  }

  document.addEventListener("pointerover", (e) => {
    const t = tipTarget(e.target);
    if (t && t !== tipFor) showTip(t);
    else if (!t && tipFor) hideTip();
  });
  document.addEventListener("focusin", (e) => {
    const t = tipTarget(e.target);
    if (t) showTip(t);
  });
  document.addEventListener("focusout", hideTip);
  document.addEventListener("scroll", hideTip, true);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") hideTip(); });
  // Touch: tapping an ⓘ toggles its tip.
  document.addEventListener("click", (e) => {
    const t = e.target.closest && e.target.closest("button.help");
    if (!t) return;
    e.preventDefault();
    if (tipFor === t) hideTip();
    else showTip(t);
  });

  // htmx: send the CSRF token with every request.
  document.addEventListener("htmx:configRequest", (e) => {
    const token = document.querySelector('meta[name="csrf-token"]');
    if (token) e.detail.headers["X-CSRFToken"] = token.content;
  });

  // Keep plots sized after htmx swaps.
  document.addEventListener("htmx:afterSettle", (e) => window.ccpResizePlots(e.target));
})();
