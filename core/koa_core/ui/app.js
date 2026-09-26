// KOA UI: vanilla JS, sin build, sin CDN. Habla con /v1/* de koa-core.
(function () {
  "use strict";

  const TOKEN_KEY = "koa-core-token";
  let TOKEN = "";
  let TOKEN_IN_MEMORY_ONLY = false;

  try {
    TOKEN = localStorage.getItem(TOKEN_KEY) || "";
  } catch (e) { /* privado o bloqueado: sin token guardado */ }

  function setToken(value) {
    try {
      localStorage.setItem(TOKEN_KEY, value);
      TOKEN_IN_MEMORY_ONLY = false;
    } catch (e) {
      TOKEN_IN_MEMORY_ONLY = true; // se pierde al recargar; ya se avisa en la UI
    }
    TOKEN = value;
  }

  // ── helpers de vista ──────────────────────────────────
  function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }

  function show(id) { document.getElementById(id).classList.remove("hidden"); }
  function hide(id) { document.getElementById(id).classList.add("hidden"); }

  function showView(name) {
    // "app" | "pair" | "connect"
    const tabs = document.getElementById("tabs");
    const main = document.getElementById("app-main");
    const pair = document.getElementById("pair-screen");
    const connect = document.getElementById("connect-screen");
    [tabs, main, pair, connect].forEach((n) => n.classList.add("hidden"));
    if (name === "app") { tabs.classList.remove("hidden"); main.classList.remove("hidden"); }
    if (name === "pair") pair.classList.remove("hidden");
    if (name === "connect") connect.classList.remove("hidden");
  }

  // ── llamadas a la API ─────────────────────────────────
  let onAuthenticated = null; // se corre una vez, tras conectar desde connect-screen
  const t = window.KoaI18n.t;

  function errorBox(box, e, retry) {
    const wrap = el("div", "empty", t("common.load_error", { error: e.message }));
    if (retry) {
      const b = el("button", "secondary", t("common.retry"));
      b.type = "button";
      b.addEventListener("click", retry);
      wrap.appendChild(document.createElement("br"));
      wrap.appendChild(b);
    }
    box.appendChild(wrap);
  }

  async function api(path, opts) {
    opts = opts || {};
    const headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
    if (TOKEN) headers["Authorization"] = "Bearer " + TOKEN;
    let res;
    try {
      res = await fetch(path, Object.assign({}, opts, { headers }));
    } catch (_) {
      throw new Error(t("common.offline"));
    }
    if (res.status === 503) {
      const body = await res.clone().json().catch(() => ({}));
      // El error del service worker es un código ("offline"), no un texto:
      // la localización vive aquí, no en sw.js.
      if (body.offline) throw new Error(t("common.offline"));
    }
    if (res.status === 401) {
      showView("connect");
      throw new Error(t("connect.no_credential"));
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || ("HTTP " + res.status));
    }
    if (res.status === 204) return null;
    return res.json();
  }

  // ── identidad del dispositivo (para nombre/plataforma por defecto) ─
  function guessPlatform() {
    const ua = navigator.userAgent || "";
    if (/android/i.test(ua)) return "android";
    if (/iphone|ipad|ipod/i.test(ua)) return "ios";
    if (/windows/i.test(ua)) return "windows";
    if (/mac os/i.test(ua)) return "mac";
    if (/linux/i.test(ua)) return "linux";
    return "web";
  }

  function guessName(platform) {
    const keys = {
      android: "platform.android", ios: "platform.ios", windows: "platform.windows",
      mac: "platform.mac", linux: "platform.linux", web: "platform.web",
    };
    return t(keys[platform] || "platform.default");
  }

  // ── pantalla: emparejar este dispositivo (/pair#code=XXXX-XXXX) ────
  function codeFromHash() {
    const m = /code=([A-Za-z0-9-]+)/.exec(location.hash || "");
    return m ? decodeURIComponent(m[1]) : "";
  }

  function initPairScreen() {
    const platform = guessPlatform();
    const codeInput = document.getElementById("pair-code");
    const nameInput = document.getElementById("pair-name");
    const errorEl = document.getElementById("pair-error");
    const doneEl = document.getElementById("pair-done");
    const form = document.getElementById("form-pair");

    const fromHash = codeFromHash();
    if (fromHash) codeInput.value = fromHash;
    nameInput.value = guessName(platform);
    // el codigo nunca necesita quedar en la barra de direcciones ni en logs
    if (fromHash && history.replaceState) history.replaceState(null, "", "/pair");

    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      hide("pair-error");
      const code = codeInput.value.trim();
      const name = nameInput.value.trim() || guessName(platform);
      try {
        const body = await api("/v1/pair/claim", {
          method: "POST",
          body: JSON.stringify({ code: code, name: name, platform: platform }),
        });
        setToken(body.token);
        form.classList.add("hidden");
        if (TOKEN_IN_MEMORY_ONLY) {
          doneEl.textContent = t("pair.memory_only_warning");
        } else {
          doneEl.textContent = t("pair.done");
        }
        show("pair-done");
        history.replaceState(null, "", "/");
        setTimeout(function () { showView("app"); initApp(); }, 900);
      } catch (err) {
        errorEl.textContent = err.message;
        show("pair-error");
      }
    });
  }

  // ── pantalla: conectar (aparece sola tras un 401) ──────
  function initConnectScreen() {
    const form = document.getElementById("form-connect");
    const errorEl = document.getElementById("connect-error");
    document.getElementById("connect-name").value = guessName(guessPlatform());
    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      hide("connect-error");
      const code = document.getElementById("connect-code").value.trim();
      const name = document.getElementById("connect-name").value.trim() || guessName(guessPlatform());
      try {
        const res = await fetch("/v1/pair/claim", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code: code, name: name, platform: guessPlatform() }),
        });
        const resBody = await res.json().catch(() => ({}));
        if (!res.ok) {
          errorEl.textContent = resBody.error || ("HTTP " + res.status);
          show("connect-error");
          return;
        }
        setToken(resBody.token);
        form.reset();
        showView("app");
        if (onAuthenticated) onAuthenticated();
      } catch (err) {
        errorEl.textContent = t("connect.server_unreachable");
        show("connect-error");
      }
    });
  }

  // ── chat (agente integrado) ─────────────────────────────
  let CHAT_CONVERSATION_ID = null;

  function chatBubble(role, text) {
    const b = el("div", "chat-msg chat-" + role);
    b.textContent = text;
    return b;
  }

  function chatToolChips(toolCalls) {
    const wrap = el("div", "chat-chips");
    (toolCalls || []).forEach(function (c) {
      const key = "chat.tool." + c.name;
      const label = t(key);
      wrap.appendChild(el("span", "chip", label === key ? c.name : label));
    });
    return wrap;
  }

  function setChatUsage(usage) {
    const box = document.getElementById("chat-usage");
    if (!usage) { box.textContent = ""; return; }
    box.textContent = t("chat.usage_line", { input: usage.input_tokens, output: usage.output_tokens });
  }

  async function sendChat(text) {
    const box = document.getElementById("chat-box");
    box.appendChild(chatBubble("user", text));
    box.scrollTop = box.scrollHeight;
    let result;
    try {
      result = await api("/v1/chat", {
        method: "POST",
        body: JSON.stringify({ conversation_id: CHAT_CONVERSATION_ID, message: text }),
      });
    } catch (e) {
      box.appendChild(chatBubble("error", e.message));
      box.scrollTop = box.scrollHeight;
      return;
    }
    CHAT_CONVERSATION_ID = result.conversation_id;
    box.appendChild(chatBubble("assistant", result.reply));
    if (result.tool_calls && result.tool_calls.length) box.appendChild(chatToolChips(result.tool_calls));
    setChatUsage(result.usage);
    box.scrollTop = box.scrollHeight;
  }

  async function checkLlmStatus() {
    const card = document.getElementById("chat-connect-card");
    const form = document.getElementById("form-chat");
    const box = document.getElementById("chat-box");
    try {
      const status = await api("/v1/llm/status");
      if (status.configured) {
        hide("chat-connect-card");
      } else {
        show("chat-connect-card");
        form.classList.add("hidden");
        box.classList.add("hidden");
        // sin modelo conectado: "Items" es la pestaña útil por defecto
        document.querySelector('.tab[data-tab="pendientes"]').click();
      }
    } catch (e) { /* 401 ya cambio a connect-screen; no hay nada mas que hacer aqui */ }
  }

  document.getElementById("form-chat").addEventListener("submit", async function (e) {
    e.preventDefault();
    const input = document.getElementById("chat-input");
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    await sendChat(text);
  });

  // ── pendientes ────────────────────────────────────────
  async function loadItems() {
    const box = document.getElementById("lista-items");
    box.innerHTML = "";
    let items;
    try {
      items = await api("/v1/items?status=open");
      const doing = await api("/v1/items?status=doing");
      items = items.concat(doing);
    } catch (e) {
      errorBox(box, e, () => loadItems());
      return;
    }
    if (!items.length) {
      box.appendChild(el("div", "empty", t("items.empty")));
      return;
    }
    items.forEach(function (it) {
      const card = el("div", "card");
      card.appendChild(el("div", "card-title", it.title));
      card.appendChild(el("div", "card-meta", it.status + (it.tags.length ? " · #" + it.tags.join(" #") : "")));
      const actions = el("div", "card-actions");
      const doneBtn = el("button", "secondary", t("items.mark_done"));
      doneBtn.addEventListener("click", async function () {
        const evidence = prompt(t("items.evidence_prompt"));
        if (!evidence) return;
        await api("/v1/items/" + it.id, {
          method: "PATCH",
          body: JSON.stringify({ status: "done", evidence: evidence }),
        });
        loadItems();
      });
      actions.appendChild(doneBtn);
      card.appendChild(actions);
      box.appendChild(card);
    });
  }

  // ── memoria ───────────────────────────────────────────
  async function loadMemoria(query) {
    const box = document.getElementById("lista-memoria");
    box.innerHTML = "";
    let hits;
    try {
      hits = await api("/v1/memory?q=" + encodeURIComponent(query || "") + "&limit=20");
    } catch (e) {
      box.appendChild(el("div", "empty", t("memory.load_error", { error: e.message })));
      return;
    }
    if (!hits.length) {
      box.appendChild(el("div", "empty", t("memory.empty")));
      return;
    }
    hits.forEach(function (h) {
      const card = el("div", "card");
      card.appendChild(el("div", "card-title", "[" + h.type + "] " + h.name));
      card.appendChild(el("div", "card-meta", h.description || ""));
      if (h.snippet) card.appendChild(el("div", "card-meta", h.snippet));
      box.appendChild(card);
    });
  }

  // ── actividad ─────────────────────────────────────────
  async function loadActividad() {
    const box = document.getElementById("lista-actividad");
    box.innerHTML = "";
    let rows;
    try {
      rows = await api("/v1/activity?limit=50");
    } catch (e) {
      errorBox(box, e, () => loadActividad());
      return;
    }
    if (!rows.length) {
      box.appendChild(el("div", "empty", t("activity.empty")));
      return;
    }
    rows.forEach(function (r) {
      const card = el("div", "card");
      card.appendChild(el("div", "card-title", r.text || r.kind));
      card.appendChild(el("div", "card-meta", r.ts + " · " + r.agent + " · " + r.kind));
      box.appendChild(card);
    });
  }

  // ── dispositivos ──────────────────────────────────────
  async function loadDispositivos() {
    const box = document.getElementById("lista-dispositivos");
    box.innerHTML = "";
    let rows;
    try {
      rows = await api("/v1/devices");
    } catch (e) {
      errorBox(box, e, () => loadDispositivos());
      return;
    }
    if (!rows.length) {
      box.appendChild(el("div", "empty", t("devices.empty")));
      return;
    }
    rows.forEach(function (d) {
      const card = el("div", "card");
      const title = d.name + (d.admin ? " · admin" : "");
      card.appendChild(el("div", "card-title", title));
      const estado = t(d.revoked_at ? "devices.status_revoked" : "devices.status_active");
      const platform = d.platform || t("devices.no_platform");
      const seen = d.last_seen_at || t("devices.never_seen");
      card.appendChild(el("div", "card-meta",
        estado + " · " + platform + " · " + t("devices.seen_label") + ": " + seen));
      if (!d.revoked_at) {
        const actions = el("div", "card-actions");
        const revokeBtn = el("button", "secondary danger", t("devices.revoke"));
        revokeBtn.addEventListener("click", async function () {
          if (!confirm(t("devices.revoke_confirm", { name: d.name }))) return;
          await api("/v1/devices/" + d.id, { method: "DELETE" });
          loadDispositivos();
        });
        actions.appendChild(revokeBtn);
        card.appendChild(actions);
      }
      box.appendChild(card);
    });
  }

  document.getElementById("btn-nuevo-emparejamiento").addEventListener("click", async function () {
    try {
      const started = await api("/v1/pair/start", { method: "POST", body: JSON.stringify({}) });
      document.getElementById("nuevo-emparejamiento-code").textContent = started.code;
      document.getElementById("nuevo-emparejamiento-vence").textContent = started.expires_at;
      document.getElementById("nuevo-emparejamiento-url").textContent = started.pair_url;
      show("nuevo-emparejamiento");
    } catch (e) {
      alert(t("devices.generate_error", { error: e.message }));
    }
  });

  // ── tabs ──────────────────────────────────────────────
  document.querySelectorAll(".tab").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
      if (btn.dataset.tab === "pendientes") loadItems();
      if (btn.dataset.tab === "memoria") loadMemoria();
      if (btn.dataset.tab === "actividad") loadActividad();
      if (btn.dataset.tab === "dispositivos") loadDispositivos();
    });
  });

  document.getElementById("form-nuevo-item").addEventListener("submit", async function (e) {
    e.preventDefault();
    const input = document.getElementById("nuevo-titulo");
    if (!input.value.trim()) return;
    await api("/v1/items", { method: "POST", body: JSON.stringify({ title: input.value.trim() }) });
    input.value = "";
    loadItems();
  });

  document.getElementById("form-recall").addEventListener("submit", function (e) {
    e.preventDefault();
    loadMemoria(document.getElementById("recall-query").value);
  });

  // ── arranque de la app principal ───────────────────────
  async function initApp() {
    onAuthenticated = function () { loadItems(); checkMe(); checkLlmStatus(); };
    api("/v1/health").then(function (h) {
      document.getElementById("home-path").textContent = h.home || "";
    }).catch(function () { /* si falta token ya se mostro connect-screen */ });
    await checkMe();
    loadItems();
    checkLlmStatus();
  }

  async function checkMe() {
    try {
      const me = await api("/v1/me");
      const btn = document.getElementById("tab-btn-dispositivos");
      if (me.admin) btn.classList.remove("hidden"); else btn.classList.add("hidden");
    } catch (e) { /* 401 ya cambio a connect-screen */ }
  }

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("sw.js").catch(function () { /* opcional */ });
  }

  // ── arranque: elegir vista segun la ruta ───────────────
  initConnectScreen();
  if (location.pathname === "/pair") {
    showView("pair");
    initPairScreen();
  } else {
    showView("app");
    initApp();
  }
})();
