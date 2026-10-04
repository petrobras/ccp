/* Curves digitizer: point editor drawn over the vendor plot image.
 *
 * The SVG viewBox is the plot crop in page pixels (at the digitization dpi);
 * the axis calibration maps data (flow, value) to those pixels:
 *   x = x_axis.offset + x_axis.slope * flow
 *   y = y_axis.offset + y_axis.slope * value
 * Alpine's x-for does not work inside <svg>, so the overlay is drawn by hand.
 */
(function () {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";
  // Line colours: distinct from the black vendor lines and the red surge line.
  const COLORS = ["#1f6feb", "#e8710a", "#1a9e55", "#8b4fd6", "#c2185b", "#00897b", "#6d4c41", "#5c6bc0"];
  const HISTORY = 100;

  function el(name, attrs) {
    const node = document.createElementNS(NS, name);
    Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
    return node;
  }

  function fmt(v) {
    if (v == null || !isFinite(v)) return "—";
    const a = Math.abs(v);
    if (a >= 1000) return v.toFixed(0);
    if (a >= 100) return v.toFixed(1);
    if (a >= 10) return v.toFixed(2);
    if (a >= 1) return v.toFixed(3);
    return v.toFixed(4);
  }

  // Ask before leaving a plot with unsaved edits (htmx swaps and page unload).
  document.addEventListener("htmx:confirm", (e) => {
    const target = e.detail.target;
    if (!window.ccpEditorDirty || !window.ccpEditorDirty()) return;
    if (!target || target.id !== "editor-area") return;
    e.preventDefault();
    if (window.confirm("Discard the unsaved edits of this plot?")) {
      window.ccpEditorDirty = null;
      e.detail.issueRequest(true);
    }
  });

  window.ccpCurveEditor = function () {
    return {
      plot: null,
      curves: [],
      sel: -1, // selected line
      pt: null, // selected point index on the selected line
      mode: "move", // "move" | "add"
      zoom: 1,
      imgOpacity: 1,
      showTicks: true,
      soloSel: false,
      hidden: {},
      hist: [],
      fut: [],
      dirty: false,
      saving: false,
      status: "",
      notes: [],
      cursor: null,
      newSpeed: "",
      k: 1, // viewBox units per CSS pixel
      drag: null,

      init() {
        const raw = this.$el.querySelector('script[type="application/json"]');
        this.plot = JSON.parse(raw.textContent);
        this.curves = this.plot.curves.map((c) => ({ speed: c.speed, points: c.points.map((p) => [p[0], p[1]]) }));
        this.sel = this.curves.length ? 0 : -1;
        this._key = (e) => this.onKey(e);
        this._unload = (e) => {
          if (this.dirty) {
            e.preventDefault();
            e.returnValue = "";
          }
        };
        window.addEventListener("keydown", this._key);
        window.addEventListener("beforeunload", this._unload);
        window.ccpEditorDirty = () => this.dirty;
        this.$nextTick(() => {
          this._ro = new ResizeObserver(() => this.measure());
          this._ro.observe(this.$refs.svg);
          this.measure();
        });
      },

      destroy() {
        window.removeEventListener("keydown", this._key);
        window.removeEventListener("beforeunload", this._unload);
        if (this._ro) this._ro.disconnect();
        window.ccpEditorDirty = null;
      },

      // ------------------------------------------------------- geometry
      px(f) { return this.plot.x_axis.offset + this.plot.x_axis.slope * f; },
      py(v) { return this.plot.y_axis.offset + this.plot.y_axis.slope * v; },
      fx(x) { return (x - this.plot.x_axis.offset) / this.plot.x_axis.slope; },
      vy(y) { return (y - this.plot.y_axis.offset) / this.plot.y_axis.slope; },
      get calibrated() { return !!(this.plot.x_axis && this.plot.y_axis); },
      measure() {
        const svg = this.$refs.svg;
        const c = this.plot.crop;
        const w = svg.getBoundingClientRect().width;
        this.k = w ? (c[2] - c[0]) / w : 1;
        this.draw();
      },
      svgPoint(e) {
        const svg = this.$refs.svg;
        const p = svg.createSVGPoint();
        p.x = e.clientX;
        p.y = e.clientY;
        return p.matrixTransform(svg.getScreenCTM().inverse());
      },
      color(i) { return COLORS[i % COLORS.length]; },

      // ------------------------------------------------------- history
      snapshot() {
        this.hist.push(JSON.stringify(this.curves));
        if (this.hist.length > HISTORY) this.hist.shift();
        this.fut = [];
      },
      undo() {
        if (!this.hist.length) return;
        this.fut.push(JSON.stringify(this.curves));
        this.curves = JSON.parse(this.hist.pop());
        this.afterChange();
      },
      redo() {
        if (!this.fut.length) return;
        this.hist.push(JSON.stringify(this.curves));
        this.curves = JSON.parse(this.fut.pop());
        this.afterChange();
      },
      afterChange() {
        if (this.sel >= this.curves.length) this.sel = this.curves.length - 1;
        if (this.pt != null && (this.sel < 0 || this.pt >= this.curves[this.sel].points.length)) this.pt = null;
        this.dirty = true;
        this.status = "";
        this.draw();
      },

      // ------------------------------------------------------- editing
      sortLine(i, keep) {
        const c = this.curves[i];
        const moved = keep != null ? c.points[keep] : null;
        c.points.sort((a, b) => a[0] - b[0]);
        return moved ? c.points.indexOf(moved) : null;
      },
      addPointAt(p) {
        if (this.sel < 0) {
          this.status = "Add a line first (give its speed in the Lines panel).";
          return;
        }
        this.snapshot();
        const point = [this.fx(p.x), this.vy(p.y)];
        const c = this.curves[this.sel];
        c.points.push(point);
        this.pt = this.sortLine(this.sel, c.points.length - 1);
        this.afterChange();
      },
      deletePoint() {
        if (this.sel < 0 || this.pt == null) return;
        this.snapshot();
        this.curves[this.sel].points.splice(this.pt, 1);
        this.pt = null;
        this.afterChange();
      },
      setPoint(axis, value) {
        const v = parseFloat(String(value).replace(",", "."));
        if (this.sel < 0 || this.pt == null || !isFinite(v)) return;
        this.snapshot();
        this.curves[this.sel].points[this.pt][axis] = v;
        this.pt = this.sortLine(this.sel, this.pt);
        this.afterChange();
      },
      nudge(dx, dy) {
        if (this.sel < 0 || this.pt == null) return;
        this.snapshot();
        const p = this.curves[this.sel].points[this.pt];
        const x = this.px(p[0]) + dx * this.k;
        const y = this.py(p[1]) + dy * this.k;
        this.curves[this.sel].points[this.pt] = [this.fx(x), this.vy(y)];
        this.pt = this.sortLine(this.sel, this.pt);
        this.afterChange();
      },
      selectLine(i) {
        this.sel = i;
        this.pt = null;
        this.draw();
      },
      setSpeed(i, value) {
        const v = parseFloat(String(value).replace(",", "."));
        if (!isFinite(v) || v <= 0) return;
        this.snapshot();
        this.curves[i].speed = v;
        this.afterChange();
      },
      deleteLine(i) {
        const c = this.curves[i];
        if (!window.confirm(`Delete the ${c.speed || "?"} rpm line (${c.points.length} points)?`)) return;
        this.snapshot();
        this.curves.splice(i, 1);
        this.hidden = {};
        this.sel = Math.min(this.sel, this.curves.length - 1);
        this.pt = null;
        this.afterChange();
      },
      addLine() {
        const v = parseFloat(String(this.newSpeed).replace(",", "."));
        if (!isFinite(v) || v <= 0) {
          this.status = "Type the speed (rpm) of the new line.";
          return;
        }
        if (this.curves.some((c) => Math.abs(c.speed - v) < 1e-9)) {
          this.status = "A line with that speed already exists.";
          return;
        }
        this.snapshot();
        this.curves.push({ speed: v, points: [] });
        this.sel = this.curves.length - 1;
        this.pt = null;
        this.mode = "add";
        this.newSpeed = "";
        this.afterChange();
        this.status = "Click along the line to add its points.";
      },
      toggleHidden(i) {
        this.hidden = Object.assign({}, this.hidden, { [i]: !this.hidden[i] });
        this.draw();
      },
      get selPoint() {
        if (this.sel < 0 || this.pt == null) return null;
        return this.curves[this.sel].points[this.pt] || null;
      },

      // ------------------------------------------------------- pointer
      onDown(e) {
        if (e.button !== 0 || !this.calibrated) return;
        const t = e.target;
        const p = this.svgPoint(e);
        if (t.dataset.pt !== undefined) {
          this.sel = +t.dataset.line;
          this.pt = +t.dataset.pt;
          this.snapshot();
          this.drag = { moved: false };
          this.$refs.svg.setPointerCapture(e.pointerId);
          e.preventDefault();
          this.draw();
          return;
        }
        if (this.mode === "add" || e.shiftKey) {
          if (t.dataset.line !== undefined && this.mode !== "add") this.sel = +t.dataset.line;
          this.addPointAt(p);
          return;
        }
        if (t.dataset.line !== undefined) {
          this.selectLine(+t.dataset.line);
          return;
        }
        this.pt = null;
        this.draw();
      },
      onMove(e) {
        if (!this.calibrated) return;
        const p = this.svgPoint(e);
        this.cursor = [this.fx(p.x), this.vy(p.y)];
        if (this.drag && this.pt != null) {
          const c = this.curves[this.sel];
          const c0 = this.plot.crop;
          const x = Math.min(Math.max(p.x, c0[0]), c0[2]);
          const y = Math.min(Math.max(p.y, c0[1]), c0[3]);
          c.points[this.pt] = [this.fx(x), this.vy(y)];
          this.drag.moved = true;
          this.dirty = true;
          this.draw();
        }
      },
      onUp() {
        if (!this.drag) return;
        if (!this.drag.moved) this.hist.pop();
        else {
          this.pt = this.sortLine(this.sel, this.pt);
          this.status = "";
        }
        this.drag = null;
        this.draw();
      },
      onLeave() { this.cursor = null; },
      onContext(e) {
        const t = e.target;
        if (t.dataset.pt === undefined) return;
        e.preventDefault();
        this.sel = +t.dataset.line;
        this.pt = +t.dataset.pt;
        this.deletePoint();
      },

      onKey(e) {
        if (!document.body.contains(this.$el)) return;
        const tag = (e.target.tagName || "").toLowerCase();
        const typing = tag === "input" || tag === "select" || tag === "textarea";
        const mod = e.metaKey || e.ctrlKey;
        if (mod && e.key.toLowerCase() === "s") {
          e.preventDefault();
          this.save();
          return;
        }
        if (typing) return;
        if (mod && e.key.toLowerCase() === "z") {
          e.preventDefault();
          e.shiftKey ? this.redo() : this.undo();
        } else if (mod && e.key.toLowerCase() === "y") {
          e.preventDefault();
          this.redo();
        } else if (e.key === "Delete" || e.key === "Backspace") {
          if (this.pt != null) {
            e.preventDefault();
            this.deletePoint();
          }
        } else if (e.key === "Escape") {
          this.pt = null;
          this.mode = "move";
          this.draw();
        } else if (e.key === "a" && !mod) {
          this.mode = this.mode === "add" ? "move" : "add";
        } else if (e.key.startsWith("Arrow") && this.pt != null) {
          e.preventDefault();
          const step = e.shiftKey ? 10 : 1;
          const d = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] }[e.key];
          this.nudge(d[0], d[1]);
        } else if ((e.key === "[" || e.key === "]") && this.curves.length) {
          const n = this.curves.length;
          this.selectLine((this.sel + (e.key === "]" ? 1 : n - 1)) % n);
        }
      },

      // ------------------------------------------------------- drawing
      draw() {
        const g = this.$refs.layer;
        if (!g || !this.calibrated) return;
        while (g.firstChild) g.removeChild(g.firstChild);
        const k = this.k;
        const box = this.plot.box;
        if (this.showTicks) {
          const tick = el("g", { class: "dz-ticks" });
          this.plot.x_ticks.forEach((v) => {
            const x = this.px(v);
            tick.appendChild(el("line", { x1: x, x2: x, y1: box[3] - 9 * k, y2: box[3] + 2 * k, "stroke-width": 1.5 * k }));
          });
          this.plot.y_ticks.forEach((v) => {
            const y = this.py(v);
            tick.appendChild(el("line", { x1: box[0] - 2 * k, x2: box[0] + 9 * k, y1: y, y2: y, "stroke-width": 1.5 * k }));
          });
          g.appendChild(tick);
        }
        const order = this.curves.map((_, i) => i).filter((i) => i !== this.sel);
        if (this.sel >= 0) order.push(this.sel);
        order.forEach((i) => {
          if (this.hidden[i]) return;
          if (this.soloSel && i !== this.sel) return;
          const c = this.curves[i];
          const active = i === this.sel;
          const color = this.color(i);
          const pts = c.points.map((p) => `${this.px(p[0]).toFixed(2)},${this.py(p[1]).toFixed(2)}`).join(" ");
          if (c.points.length > 1) {
            // wide transparent stroke: an easy target to select the line
            g.appendChild(el("polyline", { points: pts, class: "dz-hit", "stroke-width": 12 * k, "data-line": i }));
            g.appendChild(el("polyline", {
              points: pts,
              class: "dz-line",
              stroke: color,
              "stroke-width": (active ? 2.4 : 1.6) * k,
              opacity: active ? 1 : 0.75,
              "data-line": i,
            }));
          }
          c.points.forEach((p, j) => {
            const selected = active && j === this.pt;
            g.appendChild(el("circle", {
              cx: this.px(p[0]),
              cy: this.py(p[1]),
              r: (selected ? 6 : active ? 4.2 : 2.6) * k,
              class: "dz-pt" + (selected ? " sel" : ""),
              fill: selected ? "#fff" : color,
              stroke: selected ? color : "#fff",
              "stroke-width": (selected ? 2.5 : 1) * k,
              "data-line": i,
              "data-pt": j,
            }));
          });
        });
      },

      // ------------------------------------------------------- persistence
      async save() {
        if (this.saving) return;
        this.saving = true;
        this.status = "Saving…";
        const token = document.querySelector('meta[name="csrf-token"]');
        try {
          const res = await fetch(this.plot.urls.save, {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRFToken": token ? token.content : "" },
            credentials: "same-origin",
            body: JSON.stringify({ curves: this.curves }),
          });
          const body = await res.json();
          if (!res.ok || !body.ok) {
            this.status = "Not saved: " + Object.values(body.errors || { e: res.statusText }).join("; ");
            return;
          }
          this.curves = body.curves;
          this.notes = body.notes || [];
          this.plot.edited = true;
          this.dirty = false;
          this.pt = null;
          this.sel = Math.min(this.sel, this.curves.length - 1);
          this.status = "Saved";
          this.draw();
          document.body.dispatchEvent(new CustomEvent("ccp:digitized-changed", { bubbles: true }));
        } catch (err) {
          this.status = "Not saved: " + err;
        } finally {
          this.saving = false;
        }
      },

      fmt,
    };
  };
})();
