/* ccp web client, agent side: presence, change polling, reload + highlight,
 * Undo toasts, notes and the agent drawer.
 *
 * An AI agent edits the open case through the bearer-token API
 * (/api/agent/v1/). This page tells the server what the user is looking at
 * (presence), polls for agent writes and notes, and reloads to show new
 * values, with an Undo. The server-side stale-form guard (core.state.save_post
 * with the X-CCP-Rev header) is what keeps a page rendered before an agent
 * write from overwriting it; this script only makes that visible.
 *
 * Agent-provided text (notes, revision notes, values) is only ever set with
 * textContent. The drawer partial is rendered (and escaped) by the server.
 */
(function () {
  "use strict";

  function meta(name) {
    const el = document.querySelector(`meta[name="${name}"]`);
    return el ? el.content : null;
  }

  const POLL_URL = meta("ccp-agent-poll");
  const PRESENCE_URL = meta("ccp-agent-presence");
  if (!POLL_URL || !PRESENCE_URL) return;

  const CASE = meta("ccp-case");
  const REV = Number(meta("ccp-case-rev") || 0);
  const PAGE = meta("ccp-page") || "";
  const PANEL_URL = meta("ccp-agent-panel");
  const UNDO_URL = meta("ccp-agent-undo"); // ".../revisions/0/undo/"
  const DISMISS_URL = meta("ccp-agent-dismiss"); // ".../notes/0/dismiss/"

  const FLASH_KEY = "ccp-agent-flash";
  const NOTE_KEY = `ccp-agent-note-${CASE || "none"}`;
  const FLASH_MAX_AGE_MS = 60000;
  const HIGHLIGHT_MS = 6000;
  const POLL_VISIBLE_MS = 2000;
  const POLL_HIDDEN_MS = 10000;
  const POLL_ERROR_MS = 10000;
  const PRESENCE_MIN_MS = 5000;
  const PRESENCE_HEARTBEAT_MS = 30000;
  const GAS_TABLE_KEY = "gas_compositions_table";
  // Autosaves wait (hx-trigger "change delay:400ms") before htmx sends them;
  // until then they are not in `inflight`. A reload in that window loses the
  // edit, so count a change as pending for a little longer than the delay.
  const AUTOSAVE_PENDING_MS = 700;
  const SETTLE_STEP_MS = 100;
  const SETTLE_MAX_MS = 5000;

  let reloading = false; // a reload is pending: stop polling and requests
  let stale = null; // agent changes seen while the user was typing
  const inflight = new Set(); // non-GET htmx requests (autosaves) in flight
  let lastChangeAt = 0; // last change that triggers an autosave not sent yet
  let undoing = false; // undo POSTs in progress: do not reload under them
  let agentJob; // last agent job seen by the poll ("id:status"); undefined at first
  let jobReload = false; // an agent job the page does not show changed
  let lastNote = 0; // highest note id received by the poll
  const openNotes = new Set(); // undismissed note ids (badge)
  let flashCount = 0; // agent changes shown since load (badge until opened)

  // ---------------------------------------------------------------- storage
  // sessionStorage can be missing or throw (private windows, webviews).
  function storageGet(key) {
    try {
      return window.sessionStorage.getItem(key);
    } catch (_) {
      return null;
    }
  }

  function storageSet(key, value) {
    try {
      window.sessionStorage.setItem(key, value);
    } catch (_) {}
  }

  function storageRemove(key) {
    try {
      window.sessionStorage.removeItem(key);
    } catch (_) {}
  }

  // ---------------------------------------------------------------- http
  function csrf() {
    return meta("csrf-token") || "";
  }

  function postJson(url, body) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
      body: JSON.stringify(body || {}),
    });
  }

  function idUrl(template, id) {
    return template ? template.replace(/\/0\/(?=[^/]*\/?$)/, `/${encodeURIComponent(id)}/`) : null;
  }

  // ---------------------------------------------------------------- formatting
  function fmt(value) {
    if (value === null || value === undefined || value === "") return "—";
    let s = typeof value === "object" ? JSON.stringify(value) : String(value);
    if (s.length > 40) s = `${s.slice(0, 39)}…`;
    return s;
  }

  function isDict(value) {
    return !!value && typeof value === "object" && !Array.isArray(value);
  }

  /** "methane 0.9, ethane 0.1": the components of a gas with a nonzero fraction. */
  function gasSummary(gas) {
    if (!isDict(gas)) return gas;
    const parts = Object.entries(gas)
      .filter(([k, v]) => k.startsWith("molar_fraction_") && v !== null && v !== "" && Number(v) !== 0)
      .map(([k, v]) => `${gas[`component_${k.slice("molar_fraction_".length)}`]} ${v}`);
    return parts.join(", ") || "defined";
  }

  /**
   * [label, old, new] per changed field of the changed gases of the gas table,
   * e.g. ["gas_0 molar_fraction_0", 0.4, 0.5]. Mirrors gas_table_changes (models.py).
   */
  function gasChanges(before, after) {
    const b = isDict(before) ? before : {};
    const a = isDict(after) ? after : {};
    const same = (x, y) => JSON.stringify(x) === JSON.stringify(y);
    const rows = [];
    Array.from(new Set([...Object.keys(b), ...Object.keys(a)]))
      .sort()
      .forEach((g) => {
        const o = b[g];
        const n = a[g];
        if (same(o, n)) return;
        if (!isDict(o) || !isDict(n)) {
          rows.push([g, gasSummary(o), gasSummary(n)]);
          return;
        }
        Array.from(new Set([...Object.keys(n), ...Object.keys(o)])).forEach((k) => {
          if (!same(o[k], n[k])) rows.push([`${g} ${k}`, o[k], n[k]]);
        });
      });
    return rows;
  }

  /** [label, old, new] rows of a key's change; the gas table field by field. */
  function changeLines(key, pair) {
    if (key === GAS_TABLE_KEY && (isDict(pair[0]) || isDict(pair[1]))) return gasChanges(pair[0], pair[1]);
    return [[key, pair[0], pair[1]]];
  }

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function plural(n, word) {
    return `${n} ${word}${n === 1 ? "" : "s"}`;
  }

  /** Keep only what the flash needs from the poll's revision dicts. */
  function compact(rev) {
    return {
      id: rev.id,
      number: rev.number,
      source: rev.source,
      author: rev.author,
      note: rev.note || "",
      undone: !!rev.undone,
      redo: !!rev.redo,
      changed: rev.changed || {},
    };
  }

  // ---------------------------------------------------------------- badge
  function updateBadge() {
    const badge = document.getElementById("agent-badge");
    if (!badge) return;
    const n = openNotes.size + flashCount;
    badge.textContent = n > 99 ? "99+" : String(n);
    badge.hidden = n === 0;
    const btn = document.getElementById("agent-btn");
    if (btn) btn.classList.toggle("has-news", n > 0);
  }

  // ---------------------------------------------------------------- toasts
  function toastHost() {
    let host = document.getElementById("agent-toasts");
    if (!host) {
      host = el("div", "agent-toasts");
      host.id = "agent-toasts";
      host.setAttribute("aria-live", "polite");
      document.body.appendChild(host);
    }
    return host;
  }

  /**
   * A toast: title, optional lines and buttons. `ttl` 0 keeps it until closed.
   * Hovering pauses the auto-hide.
   */
  function toast({ title, meta: metaText, lines, body, actions, ttl, kind, id }) {
    const host = toastHost();
    if (id && document.getElementById(id)) document.getElementById(id).remove();
    const node = el("div", `agent-toast${kind ? ` ${kind}` : ""}`);
    if (id) node.id = id;
    node.setAttribute("role", "status");
    const head = el("div", "agent-toast-head");
    head.appendChild(el("span", "agent-dot"));
    head.appendChild(el("b", null, title));
    const close = el("button", "close", "✕");
    close.type = "button";
    close.setAttribute("aria-label", "Close");
    close.addEventListener("click", () => node.remove());
    head.appendChild(close);
    node.appendChild(head);
    if (metaText) node.appendChild(el("div", "agent-toast-meta mono", metaText));
    if (lines && lines.length) {
      const list = el("ul", "agent-toast-lines");
      lines.forEach((line) => {
        const li = el("li");
        li.appendChild(el("span", "k mono", line[0]));
        if (line.length > 1) {
          li.appendChild(el("span", "mono old", fmt(line[1])));
          li.appendChild(el("span", "arrow", "→"));
          li.appendChild(el("span", "mono new", fmt(line[2])));
        }
        list.appendChild(li);
      });
      node.appendChild(list);
    }
    if (body) node.appendChild(el("div", "agent-toast-body", body));
    if (actions && actions.length) {
      const row = el("div", "agent-toast-actions");
      actions.forEach((a) => {
        const b = el("button", `btn sm${a.primary ? " primary" : a.ghost ? " ghost" : ""}`, a.label);
        b.type = "button";
        b.addEventListener("click", () => a.onClick(b, node));
        row.appendChild(b);
      });
      node.appendChild(row);
    }
    host.appendChild(node);
    if (ttl) {
      let timer = setTimeout(() => node.remove(), ttl);
      node.addEventListener("mouseenter", () => clearTimeout(timer));
      node.addEventListener("mouseleave", () => {
        timer = setTimeout(() => node.remove(), ttl / 2);
      });
    }
    return node;
  }

  // ---------------------------------------------------------------- banner
  function showBanner() {
    let banner = document.getElementById("agent-banner");
    const n = stale ? stale.length : 0;
    const text = `The agent changed this case (${plural(n, "change")}). Reload to see its values; calculations wait until then.`;
    if (banner) {
      banner.querySelector("[data-text]").textContent = text;
      return banner;
    }
    banner = el("div", "banner info agent-banner");
    banner.id = "agent-banner";
    banner.setAttribute("role", "alert");
    banner.appendChild(el("span", "tag", "agent"));
    const msg = el("div", null, text);
    msg.setAttribute("data-text", "");
    banner.appendChild(msg);
    const actions = el("div", "actions");
    const reload = el("button", "btn sm primary", "Reload");
    reload.type = "button";
    // The mousedown blurred the field being edited, which only scheduled its
    // autosave: let it go first (a stale one answers HX-Refresh and reloads).
    reload.addEventListener("click", () => reloadWhenSettled());
    actions.appendChild(reload);
    banner.appendChild(actions);
    const main = document.getElementById("main") || document.body;
    main.insertBefore(banner, main.firstChild);
    return banner;
  }

  function pulseBanner() {
    const banner = showBanner();
    banner.classList.remove("agent-pulse");
    void banner.offsetWidth; // restart the animation
    banner.classList.add("agent-pulse");
  }

  // ---------------------------------------------------------------- reload
  function scroller() {
    return document.getElementById("main");
  }

  function flashAndReload(changes, extra) {
    if (reloading) return;
    reloading = true;
    const main = scroller();
    const flash = Object.assign(
      {
        case: CASE,
        at: Date.now(),
        scroll: main ? main.scrollTop : window.scrollY,
        changes: (changes || []).map(compact),
      },
      extra || {}
    );
    storageSet(FLASH_KEY, JSON.stringify(flash));
    window.location.reload();
  }

  /** The server said HX-Refresh (stale form): fetch what changed, then reload. */
  function refreshWithFlash() {
    if (reloading) return;
    fetchPoll()
      .then((data) => flashAndReload(data.changes || []))
      .catch(() => {
        reloading = true;
        window.location.reload();
      });
  }

  /** Edits not on the server yet: autosaves waiting for their delay or in flight. */
  function busy() {
    return undoing || inflight.size > 0 || Date.now() - lastChangeAt < AUTOSAVE_PENDING_MS;
  }

  /** Reload with the stale changes once pending autosaves are sent and done. */
  function reloadWhenSettled() {
    if (isEditing() && document.activeElement.blur) document.activeElement.blur();
    const deadline = Date.now() + SETTLE_MAX_MS;
    (function check() {
      if (reloading) return;
      if (busy() && Date.now() < deadline) {
        setTimeout(check, SETTLE_STEP_MS);
        return;
      }
      flashAndReload(stale || []);
    })();
  }

  /** Re-check after pending autosaves; reload when the user is not editing. */
  function recheckSoon() {
    setTimeout(() => {
      if (reloading || isEditing()) return;
      if (busy()) {
        recheckSoon();
        return;
      }
      if (stale) flashAndReload(stale);
      else if (jobReload) flashAndReload([], { job: true });
    }, AUTOSAVE_PENDING_MS);
  }

  function isEditing() {
    const a = document.activeElement;
    if (!a || a === document.body) return false;
    if (a.closest("#agent-drawer, #agent-toasts, #agent-banner, .tweaks")) return false;
    return a.matches("input, textarea, select, [contenteditable='true']");
  }

  function onChanges(changes) {
    if (!changes.length || undoing) return;
    if (!isEditing() && !busy()) {
      flashAndReload(changes);
      return;
    }
    stale = changes;
    showBanner();
    if (!isEditing()) recheckSoon();
  }

  /** The agent's job changed (started, finished) and this page does not show it. */
  function onAgentJob(job) {
    const key = job ? `${job.id}:${job.status}` : "";
    if (agentJob === undefined || key === agentJob) {
      agentJob = key;
      return;
    }
    agentJob = key;
    // A job partial on the page polls itself and refreshes the results.
    if (!job || document.getElementById(`job-${job.id}`)) return;
    jobReload = true;
    if (!isEditing() && !busy()) flashAndReload(stale || [], { job: true });
    else if (!isEditing()) recheckSoon();
  }

  // An edit that autosaves: htmx sends it after its delay.
  document.addEventListener(
    "change",
    (e) => {
      const t = e.target;
      if (t && t.closest && t.closest("[hx-post], [hx-trigger]")) lastChangeAt = Date.now();
    },
    true
  );

  // Leaving the focused field reloads (after any autosave it triggered; a
  // stale autosave answers HX-Refresh, handled below).
  document.addEventListener("focusout", () => {
    if ((!stale && !jobReload) || reloading) return;
    recheckSoon();
  });

  // ---------------------------------------------------------------- htmx
  document.addEventListener("htmx:configRequest", (e) => {
    if (CASE) e.detail.headers["X-CCP-Rev"] = String(REV);
  });

  document.addEventListener("htmx:beforeRequest", (e) => {
    const cfg = e.detail.requestConfig || {};
    const verb = String(cfg.verb || "get").toLowerCase();
    if (verb === "get") return;
    if (reloading) {
      e.preventDefault();
      return;
    }
    // While the page is stale, autosaves (change-triggered) still go: the
    // server drops the agent's keys, keeps the user's other edits and answers
    // HX-Refresh. Clicked actions (calculate, run, convert...) wait.
    const trigger = cfg.triggeringEvent;
    const isAutosave = trigger && trigger.type === "change";
    if (stale && !isAutosave && postsForm(e.detail.elt) && !String(cfg.path || "").startsWith("/agent/")) {
      e.preventDefault();
      pulseBanner();
    }
  });

  /**
   * Whether a clicked action posts form state (calculate, run, convert, load,
   * report...: they hx-include a form). Cancel, Stop monitoring or a file's ✕
   * post none, so they work while the page is stale.
   */
  function postsForm(elt) {
    if (!elt || !elt.getAttribute) return true;
    if (elt.tagName === "FORM") return true;
    return /form/.test(elt.getAttribute("hx-include") || "");
  }

  document.addEventListener("htmx:beforeSend", (e) => {
    const cfg = e.detail.requestConfig || {};
    if (String(cfg.verb || "get").toLowerCase() !== "get" && e.detail.xhr) {
      inflight.add(e.detail.xhr);
      // The autosave left its delay: `inflight` covers it now.
      const trigger = cfg.triggeringEvent;
      if (trigger && trigger.type === "change") lastChangeAt = 0;
    }
  });

  function settled(e) {
    if (e.detail && e.detail.xhr) inflight.delete(e.detail.xhr);
  }
  ["htmx:afterRequest", "htmx:sendError", "htmx:sendAbort", "htmx:timeout"].forEach((name) =>
    document.addEventListener(name, settled)
  );

  document.addEventListener("htmx:beforeOnLoad", (e) => {
    const xhr = e.detail.xhr;
    if (CASE && xhr && xhr.getResponseHeader("HX-Refresh") === "true") {
      e.preventDefault();
      inflight.delete(xhr);
      if (!isEditing()) {
        refreshWithFlash();
        return;
      }
      // The user is typing in another field (the autosave of the previous
      // one came back stale): show the banner; leaving the field reloads.
      fetchPoll()
        .then((data) => {
          stale = data.changes && data.changes.length ? data.changes : stale || [];
        })
        .catch(() => {
          stale = stale || [];
        })
        .then(() => {
          if (!reloading) showBanner();
        });
    }
  });

  // app.js's ccpSaveAndReload reloads through here when its save was stale.
  window.ccpAgentReload = refreshWithFlash;

  // ---------------------------------------------------------------- poll
  function fetchPoll() {
    const params = new URLSearchParams();
    if (CASE) {
      params.set("case", CASE);
      params.set("rev", String(REV));
      params.set("note", String(lastNote));
    }
    return fetch(`${POLL_URL}?${params}`, {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      cache: "no-store",
    }).then((r) => {
      if (!r.ok) throw new Error(`poll ${r.status}`);
      return r.json();
    });
  }

  let pollTimer = null;
  let firstPoll = true;

  function schedulePoll(ms) {
    clearTimeout(pollTimer);
    pollTimer = setTimeout(poll, ms);
  }

  function safeNavigate(url) {
    try {
      const target = new URL(url, window.location.href);
      if (target.origin !== window.location.origin) return false;
      reloading = true;
      window.location.assign(target.href);
      return true;
    } catch (_) {
      return false;
    }
  }

  function poll() {
    if (reloading) return;
    if (undoing) {
      // Reloading between two undo POSTs would leave the rest undone.
      schedulePoll(POLL_VISIBLE_MS);
      return;
    }
    fetchPoll()
      .then((data) => {
        if (reloading) return;
        if (data.navigate && safeNavigate(data.navigate)) return;
        handleNotes(data.notes || [], firstPoll);
        firstPoll = false;
        if (CASE && data.revision !== null && data.revision !== undefined && data.revision > REV) {
          onChanges(data.changes || []);
        }
        if (CASE && !reloading) onAgentJob(data.agent_job || null);
        schedulePoll(document.hidden ? POLL_HIDDEN_MS : POLL_VISIBLE_MS);
      })
      .catch(() => schedulePoll(POLL_ERROR_MS));
  }

  // ---------------------------------------------------------------- notes
  function noteToast(note) {
    toast({
      id: `agent-note-toast-${note.id}`,
      title: `Note from ${note.author || "Agent"}`,
      body: note.body,
      kind: "note",
      ttl: 0,
      actions: [
        { label: "Details", ghost: true, onClick: () => openDrawer() },
        {
          label: "Dismiss",
          onClick: (btn, node) => {
            btn.disabled = true;
            dismissNote(note.id).finally(() => node.remove());
          },
        },
      ],
    });
  }

  function handleNotes(notes, first) {
    if (!notes.length) return;
    const seen = Number(storageGet(NOTE_KEY) || 0);
    let toasted = 0;
    // Newest last; on the first poll only toast notes not shown in this tab yet.
    const fresh = notes.filter((n) => n.id > seen);
    fresh.slice(first ? -3 : -5).forEach((n) => {
      noteToast(n);
      toasted += 1;
    });
    notes.forEach((n) => {
      lastNote = Math.max(lastNote, n.id);
      openNotes.add(n.id);
    });
    if (toasted || fresh.length) storageSet(NOTE_KEY, String(Math.max(seen, lastNote)));
    updateBadge();
  }

  function dismissNote(id, explicitUrl) {
    const url = explicitUrl || idUrl(DISMISS_URL, id);
    if (!url) return Promise.resolve();
    return postJson(url).then((r) => {
      if (!r.ok) return;
      openNotes.delete(Number(id));
      updateBadge();
      const t = document.getElementById(`agent-note-toast-${id}`);
      if (t) t.remove();
      const row = document.getElementById(`agent-note-${id}`);
      if (row) {
        row.classList.add("dismissed");
        const b = row.querySelector("[data-agent-dismiss]");
        if (b) b.remove();
      }
    }).catch(() => {});
  }

  // ---------------------------------------------------------------- undo
  /** Undo revisions newest first, then reload showing what the undo changed. */
  function undoRevisions(ids, btn) {
    if (!ids.length) return Promise.resolve();
    if (btn) btn.disabled = true;
    undoing = true;
    const results = [];
    const order = ids.slice().sort((a, b) => b.number - a.number);
    return order
      .reduce(
        (p, rev) =>
          p.then(() =>
            postJson(rev.url || idUrl(UNDO_URL, rev.id)).then((r) =>
              r.ok ? r.json().then((d) => results.push(d.undo)) : null
            )
          ),
        Promise.resolve()
      )
      .then(() => {
        undoing = false;
        if (results.length) flashAndReload(results, { undo: true });
        else {
          if (btn) btn.disabled = false;
          toast({ title: "Nothing to undo", body: "These changes were already undone.", ttl: 6000 });
        }
      })
      .catch(() => {
        undoing = false;
        if (results.length) {
          // Some went through: show them rather than a page at the old revision.
          flashAndReload(results, { undo: true });
          return;
        }
        if (btn) btn.disabled = false;
        toast({ title: "Undo failed", body: "Could not reach the app.", kind: "error", ttl: 8000 });
      });
  }

  // ---------------------------------------------------------------- flash
  function readFlash() {
    const raw = storageGet(FLASH_KEY);
    if (!raw) return null;
    storageRemove(FLASH_KEY);
    try {
      const flash = JSON.parse(raw);
      if (!flash || String(flash.case) !== String(CASE)) return null;
      if (Date.now() - Number(flash.at || 0) > FLASH_MAX_AGE_MS) return null;
      return flash;
    } catch (_) {
      return null;
    }
  }

  function fieldsFor(key) {
    if (key === GAS_TABLE_KEY) {
      return Array.from(document.querySelectorAll("table.gas"));
    }
    return Array.from(document.querySelectorAll(`[name="${CSS.escape(key)}"]:not([type=hidden])`));
  }

  function highlight(changes) {
    const latest = {};
    changes
      .slice()
      .sort((a, b) => a.number - b.number)
      .forEach((rev) => {
        Object.entries(rev.changed || {}).forEach(([key, pair]) => {
          latest[key] = latest[key] ? [latest[key][0], pair[1]] : pair;
        });
      });
    let first = null;
    Object.entries(latest).forEach(([key, pair]) => {
      fieldsFor(key).forEach((node) => {
        const target = node.matches("input[type=checkbox], input[type=radio]")
          ? node.closest("label") || node
          : node;
        target.classList.add("agent-changed");
        // The app's tooltip shows data-help; keep a field's own help text.
        const added = !target.hasAttribute("data-help") && !target.hasAttribute("title");
        if (added) {
          const help = changeLines(key, pair)
            .slice(0, 6)
            .map(([k, o, n]) => (key === GAS_TABLE_KEY ? `${k}: ` : "") + `${fmt(o)} → ${fmt(n)}`)
            .join("; ");
          target.setAttribute("data-help", `Agent: ${help}`);
        }
        const section = target.closest(".section");
        if (section) section.dispatchEvent(new CustomEvent("ccp-expand"));
        first = first || target;
        setTimeout(() => {
          target.classList.remove("agent-changed");
          // The old → new values go stale once the user edits the field.
          if (added) target.removeAttribute("data-help");
        }, HIGHLIGHT_MS);
      });
    });
    return { keys: Object.keys(latest), latest, first };
  }

  function restoreScroll(flash) {
    const main = scroller();
    const y = Number(flash.scroll || 0);
    const apply = () => {
      if (main) main.scrollTop = y;
      else window.scrollTo(0, y);
    };
    apply();
    // Results load after the page (hx-trigger="load"); keep the position.
    setTimeout(apply, 250);
    setTimeout(apply, 900);
  }

  function showFlash(flash) {
    const changes = flash.changes || [];
    restoreScroll(flash);
    // Reloaded to show an agent's job: the job and results are the news.
    if (flash.job && !changes.length) return;
    const { latest } = highlight(changes);
    const keys = Object.keys(latest);
    const isUndo = !!flash.undo || (changes.length > 0 && changes.every((r) => r.source === "undo"));
    // A redo (an undo of an undo) puts the agent's change back.
    const isRedo = isUndo && changes.length > 0 && changes.every((r) => r.redo);
    // Undo offers to undo the agent's writes (or a redo); after an undo, Redo
    // undoes the undo. A batch where the agent already undid its own write
    // offers neither.
    const undoable = changes.filter(
      (r) => !r.undone && (isUndo ? r.source === "undo" && !!r.redo === isRedo : r.source === "agent")
    );
    flashCount = changes.length;
    updateBadge();
    const authors = Array.from(new Set(changes.map((r) => r.author).filter(Boolean)));
    const numbers = changes.map((r) => `#${r.number}`).join(" ");
    const notes = changes.map((r) => r.note).filter(Boolean);
    const rows = keys.flatMap((k) => changeLines(k, latest[k]));
    const title = isRedo
      ? `Redone: ${plural(rows.length, "value")} re-applied`
      : isUndo
        ? `Undone: ${plural(rows.length, "value")} restored`
        : `Agent changed ${plural(rows.length, "value")}`;
    const lines = rows.slice(0, 8);
    if (rows.length > 8) lines.push([`+${rows.length - 8} more`]);
    const actions = [];
    if (undoable.length) {
      actions.push({
        label: isUndo && !isRedo ? "Redo" : "Undo",
        primary: true,
        onClick: (btn) => undoRevisions(undoable, btn),
      });
    }
    actions.push({ label: "Details", ghost: true, onClick: () => openDrawer() });
    toast({
      id: "agent-change-toast",
      title,
      meta: [authors.join(", "), numbers].filter(Boolean).join(" · "),
      lines: rows.length ? lines : [["No values changed"]],
      body: notes.join("\n") || null,
      actions,
      ttl: 20000,
    });
  }

  // ---------------------------------------------------------------- drawer
  function drawer() {
    return document.getElementById("agent-drawer");
  }

  function loadPanel() {
    const body = document.getElementById("agent-drawer-body");
    if (!body || !PANEL_URL || typeof htmx === "undefined") return;
    htmx.ajax("GET", PANEL_URL, { target: body, swap: "innerHTML" });
  }

  function openDrawer() {
    const d = drawer();
    if (!d) return;
    d.classList.add("open");
    d.setAttribute("aria-hidden", "false");
    const btn = document.getElementById("agent-btn");
    if (btn) btn.setAttribute("aria-expanded", "true");
    flashCount = 0;
    updateBadge();
    loadPanel();
  }

  function closeDrawer() {
    const d = drawer();
    if (!d) return;
    d.classList.remove("open");
    d.setAttribute("aria-hidden", "true");
    const btn = document.getElementById("agent-btn");
    if (btn) btn.setAttribute("aria-expanded", "false");
  }

  window.ccpAgentDrawer = { open: openDrawer, close: closeDrawer, reload: loadPanel };

  document.addEventListener("click", (e) => {
    const t = e.target.closest ? e.target : null;
    if (!t) return;
    if (t.closest("#agent-btn")) {
      e.preventDefault();
      const d = drawer();
      if (d && d.classList.contains("open")) closeDrawer();
      else openDrawer();
      return;
    }
    if (t.closest("[data-agent-close]")) {
      closeDrawer();
      return;
    }
    if (t.closest("[data-agent-refresh]")) {
      loadPanel();
      return;
    }
    const undoBtn = t.closest("[data-agent-undo]");
    if (undoBtn) {
      e.preventDefault();
      const id = undoBtn.getAttribute("data-agent-undo");
      const number = Number(undoBtn.getAttribute("data-number") || 0);
      undoRevisions([{ id, number, url: undoBtn.getAttribute("data-url") }], undoBtn);
      return;
    }
    const dismissBtn = t.closest("[data-agent-dismiss]");
    if (dismissBtn) {
      e.preventDefault();
      dismissBtn.disabled = true;
      dismissNote(dismissBtn.getAttribute("data-agent-dismiss"), dismissBtn.getAttribute("data-url")).finally(() => {
        dismissBtn.disabled = false;
      });
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeDrawer();
  });

  // ---------------------------------------------------------------- presence
  let section = "";
  let lastPresence = 0;
  let presenceTimer = null;

  function sendPresence() {
    presenceTimer = null;
    lastPresence = Date.now();
    postJson(PRESENCE_URL, {
      case: CASE ? Number(CASE) : null,
      page: PAGE,
      section,
      url: window.location.pathname + window.location.search + window.location.hash,
      title: document.title,
    }).catch(() => {});
  }

  /** At most one presence POST per 5 s; a later call is sent at the end. */
  function presence() {
    if (reloading || presenceTimer) return;
    const wait = lastPresence + PRESENCE_MIN_MS - Date.now();
    if (wait <= 0) sendPresence();
    else presenceTimer = setTimeout(sendPresence, wait);
  }

  const visible = new Map();
  let observer = null;

  function observeSections(root) {
    if (!observer) return;
    (root || document).querySelectorAll(".section[id]").forEach((s) => {
      if (!s.__ccpAgentSeen) {
        s.__ccpAgentSeen = true;
        observer.observe(s);
      }
    });
  }

  if ("IntersectionObserver" in window) {
    observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((en) => visible.set(en.target.id, en.isIntersecting ? en.intersectionRect.height : 0));
        let best = "";
        let bestH = 0;
        visible.forEach((h, id) => {
          if (h > bestH) {
            best = id;
            bestH = h;
          }
        });
        if (best && best !== section) {
          section = best;
          presence();
        }
      },
      { root: scroller(), threshold: [0, 0.25, 0.5, 0.75, 1] }
    );
  }

  document.addEventListener("htmx:afterSettle", (e) => observeSections(e.target));

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) return;
    presence();
    schedulePoll(0);
  });
  window.addEventListener("focus", presence);
  // Only the window focused last keeps presence fresh: with two windows
  // visible on different cases, both heartbeats would make the agent's
  // default case flip between them. (Not "focused now": the user is often
  // typing to the agent in another app while this window shows the case.)
  // The id survives reloads of the tab (sessionStorage is per tab): the
  // agent's set/calc/open reload the page while the user types elsewhere, and
  // a new id would lose the "focused last" claim, so presence went stale.
  const TAB_ID_KEY = "ccp-agent-tab-id";
  const LAST_FOCUS_KEY = "ccp-agent-last-focus";
  const TAB_ID = storageGet(TAB_ID_KEY) || Math.random().toString(36).slice(2);
  storageSet(TAB_ID_KEY, TAB_ID);

  function markFocused() {
    try {
      window.localStorage.setItem(LAST_FOCUS_KEY, TAB_ID);
    } catch (_) {}
  }

  function focusedLast() {
    try {
      const last = window.localStorage.getItem(LAST_FOCUS_KEY);
      return !last || last === TAB_ID;
    } catch (_) {
      return true;
    }
  }

  window.addEventListener("focus", markFocused);
  if (document.hasFocus()) markFocused();
  setInterval(() => {
    if (!document.hidden && focusedLast()) presence();
  }, PRESENCE_HEARTBEAT_MS);

  // ---------------------------------------------------------------- start
  function start() {
    observeSections(document);
    // The observer reports the visible section asynchronously; let it run first.
    setTimeout(presence, 300);
    const flash = CASE ? readFlash() : null;
    if (flash) {
      // Alpine renders some inputs (the gas table); highlight after it ran.
      setTimeout(() => showFlash(flash), 60);
    }
    schedulePoll(flash ? POLL_VISIBLE_MS : 300);
  }

  if (document.readyState === "complete") start();
  else window.addEventListener("load", start, { once: true });
})();
