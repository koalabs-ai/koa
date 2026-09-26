// KOA UI i18n: no build step, no dependencies. Language = localStorage
// "koa-lang" if set > navigator.language starting with "es" -> "es" ->
// else "en". Exposes window.KoaI18n = { t, lang, setLang, apply }.
(function () {
  "use strict";

  var STORAGE_KEY = "koa-lang";

  var EN = {
    "tabs.chat": "Chat",
    "tabs.items": "Items",
    "tabs.memory": "Memory",
    "tabs.activity": "Activity",
    "tabs.devices": "Devices",

    "chat.connect_title": "Connect a model",
    "chat.connect_body": "KOA works without one. To chat, run this on the machine:",
    "chat.connect_options": "Ollama: free, local. Claude or OpenAI: paid per use, needs your own API key.",
    "chat.placeholder": "Ask your KOA…",
    "chat.send": "Send",
    "chat.usage_line": "tokens: {input} in / {output} out",
    "chat.tool.context": "checked the workspace",
    "chat.tool.todo_list": "looked at pending items",
    "chat.tool.todo_add": "added a pending item",
    "chat.tool.todo_update": "updated a pending item",
    "chat.tool.memory_recall": "searched memory",
    "chat.tool.memory_add": "saved a memory",
    "chat.tool.plans_list": "looked at plans",
    "chat.tool.claim_acquire": "took a lock",
    "chat.tool.claim_release": "released a lock",
    "chat.tool.activity_log": "logged an activity note",

    "items.placeholder": "New item…",
    "items.add": "Add",
    "items.empty": "No open items.",
    "items.mark_done": "Mark done",
    "items.evidence_prompt": "Evidence (what proves it's done):",

    "memory.placeholder": "Search memory…",
    "memory.search": "Search",
    "memory.empty": "No results.",
    "memory.load_error": "Couldn't search: {error}",

    "activity.empty": "No activity yet.",

    "devices.new_pairing": "Pair a new device",
    "devices.expires": "Expires:",
    "devices.open_on_new_device": "Open this URL on the new device:",
    "devices.empty": "No paired devices.",
    "devices.revoke": "Revoke",
    "devices.revoke_confirm": 'Revoke access for "{name}"?',
    "devices.generate_error": "Couldn't generate the code: {error}",
    "devices.status_active": "active",
    "devices.status_revoked": "revoked",
    "devices.no_platform": "no platform",
    "devices.never_seen": "never",
    "devices.seen_label": "seen",

    "pair.title": "Pair this device",
    "pair.hint": "Give this device a name to connect it to your KOA.",
    "pair.code_placeholder": "XXXX-XXXX",
    "pair.name_placeholder": "This device's name",
    "pair.connect": "Connect",
    "pair.memory_only_warning":
      "Connected, but this browser won't let us save the token: if you " +
      "reload, it's lost and you'll have to pair again. Keep using this tab.",
    "pair.done": "Done, this device is now connected.",

    "connect.title": "Connect this device",
    "connect.hint_prefix": "This KOA asks you to identify yourself. Get a code with ",
    "connect.hint_suffix":
      " (or from the Devices tab on another device that's already connected) " +
      "and type it here.",
    "connect.code_placeholder": "XXXX-XXXX",
    "connect.name_placeholder": "This device's name",
    "connect.connect": "Connect",
    "connect.no_credential": "this device doesn't have a credential (or it's no longer valid)",
    "connect.server_unreachable": "Couldn't reach the server.",

    "common.retry": "Retry",
    "common.load_error": "Couldn't load. {error}",
    "common.offline":
      "Can't find your KOA. Is it on? If you're going through a tunnel or " +
      "a VPN, check that it's still open.",

    "platform.android": "Android",
    "platform.ios": "iPhone/iPad",
    "platform.windows": "Windows PC",
    "platform.mac": "Mac",
    "platform.linux": "Linux",
    "platform.web": "Browser",
    "platform.default": "device",

    "lang.toggle_label": "Language",
  };

  var ES = {
    "tabs.chat": "Chat",
    "tabs.items": "Pendientes",
    "tabs.memory": "Memoria",
    "tabs.activity": "Actividad",
    "tabs.devices": "Dispositivos",

    "chat.connect_title": "Conecta un modelo",
    "chat.connect_body": "KOA funciona sin uno. Para platicar, corre esto en la máquina:",
    "chat.connect_options": "Ollama: gratis, local. Claude u OpenAI: de pago por uso, necesita tu propia llave de API.",
    "chat.placeholder": "Pregúntale a tu KOA…",
    "chat.send": "Enviar",
    "chat.usage_line": "tokens: {input} entrada / {output} salida",
    "chat.tool.context": "revisó el workspace",
    "chat.tool.todo_list": "miró los pendientes",
    "chat.tool.todo_add": "agregó un pendiente",
    "chat.tool.todo_update": "actualizó un pendiente",
    "chat.tool.memory_recall": "buscó en memoria",
    "chat.tool.memory_add": "guardó una memoria",
    "chat.tool.plans_list": "miró los planes",
    "chat.tool.claim_acquire": "tomó un candado",
    "chat.tool.claim_release": "liberó un candado",
    "chat.tool.activity_log": "anotó algo en la bitácora",

    "items.placeholder": "Pendiente nuevo…",
    "items.add": "Agregar",
    "items.empty": "Sin pendientes abiertos.",
    "items.mark_done": "Marcar hecho",
    "items.evidence_prompt": "Evidencia (qué prueba que quedó hecho):",

    "memory.placeholder": "Buscar en memoria…",
    "memory.search": "Buscar",
    "memory.empty": "Sin resultados.",
    "memory.load_error": "No se pudo buscar: {error}",

    "activity.empty": "Sin actividad todavía.",

    "devices.new_pairing": "Emparejar dispositivo nuevo",
    "devices.expires": "Vence:",
    "devices.open_on_new_device": "Abre esta URL en el dispositivo nuevo:",
    "devices.empty": "Sin dispositivos emparejados.",
    "devices.revoke": "Revocar",
    "devices.revoke_confirm": '¿Revocar el acceso de "{name}"?',
    "devices.generate_error": "No se pudo generar el código: {error}",
    "devices.status_active": "activo",
    "devices.status_revoked": "revocado",
    "devices.no_platform": "sin plataforma",
    "devices.never_seen": "nunca",
    "devices.seen_label": "visto",

    "pair.title": "Emparejar este dispositivo",
    "pair.hint": "Dale un nombre a este dispositivo para conectarlo con tu KOA.",
    "pair.code_placeholder": "XXXX-XXXX",
    "pair.name_placeholder": "Nombre de este dispositivo",
    "pair.connect": "Conectar",
    "pair.memory_only_warning":
      "Conectado, pero este navegador no deja guardar el token: si recargas, " +
      "se pierde y hay que emparejar de nuevo. Sigue usando esta pestaña.",
    "pair.done": "Listo, este dispositivo ya quedó conectado.",

    "connect.title": "Conectar este dispositivo",
    "connect.hint_prefix": "Este KOA pide identificarte. Pide un código con ",
    "connect.hint_suffix":
      " (o desde la pestaña Dispositivos en otro dispositivo ya conectado) y " +
      "escríbelo aquí.",
    "connect.code_placeholder": "XXXX-XXXX",
    "connect.name_placeholder": "Nombre de este dispositivo",
    "connect.connect": "Conectar",
    "connect.no_credential": "este dispositivo no tiene credencial (o ya no vale)",
    "connect.server_unreachable": "No se pudo hablar con el servidor.",

    "common.retry": "Reintentar",
    "common.load_error": "No se pudo cargar. {error}",
    "common.offline":
      "No encuentro tu KOA. ¿Está prendido? Si entras por un túnel o una " +
      "VPN, revisa que siga abierto.",

    "platform.android": "Android",
    "platform.ios": "iPhone/iPad",
    "platform.windows": "PC con Windows",
    "platform.mac": "Mac",
    "platform.linux": "Linux",
    "platform.web": "Navegador",
    "platform.default": "dispositivo",

    "lang.toggle_label": "Idioma",
  };

  var CATALOGS = { en: EN, es: ES };

  function detectLang() {
    try {
      var stored = localStorage.getItem(STORAGE_KEY);
      if (stored === "en" || stored === "es") return stored;
    } catch (e) { /* private/blocked storage: fall through */ }
    var nav = (navigator.language || navigator.userLanguage || "").toLowerCase();
    return nav.indexOf("es") === 0 ? "es" : "en";
  }

  var current = detectLang();

  function t(key, params) {
    var template = (CATALOGS[current] && CATALOGS[current][key]) || EN[key] || key;
    if (params) {
      Object.keys(params).forEach(function (k) {
        template = template.replace("{" + k + "}", params[k]);
      });
    }
    return template;
  }

  function applyStaticText() {
    document.documentElement.lang = current;
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      el.textContent = t(el.getAttribute("data-i18n"));
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach(function (el) {
      el.setAttribute("placeholder", t(el.getAttribute("data-i18n-placeholder")));
    });
    document.querySelectorAll("[data-i18n-aria-label]").forEach(function (el) {
      el.setAttribute("aria-label", t(el.getAttribute("data-i18n-aria-label")));
    });
  }

  function setLang(lang) {
    if (lang !== "en" && lang !== "es") return;
    current = lang;
    try { localStorage.setItem(STORAGE_KEY, lang); } catch (e) { /* per-viewer only */ }
    applyStaticText();
    document.dispatchEvent(new CustomEvent("koa-lang-changed", { detail: { lang: lang } }));
  }

  function initToggle() {
    var btn = document.getElementById("lang-toggle");
    if (!btn) return;
    function render() { btn.textContent = current === "es" ? "EN" : "ES"; }
    render();
    btn.addEventListener("click", function () {
      setLang(current === "es" ? "en" : "es");
      render();
    });
  }

  window.KoaI18n = {
    t: t,
    lang: function () { return current; },
    setLang: setLang,
    apply: applyStaticText,
  };

  function init() {
    applyStaticText();
    initToggle();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
