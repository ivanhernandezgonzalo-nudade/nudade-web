/*!
 * Nudade · Consentimiento de cookies + Meta Pixel
 * - Sin PIXEL_ID no hace nada (despliegue seguro).
 * - El Pixel solo se carga si el usuario acepta (RGPD / LSSI art. 22.2, guía AEPD).
 * - "Aceptar" y "Rechazar" con el mismo peso visual. Consentimiento revocable.
 * - Eventos: PageView, Lead (formularios de propietarios/familias), Contact (WhatsApp),
 *   InversorLead (formulario de inversores, evento personalizado).
 */
(function () {
  'use strict';

  var PIXEL_ID = ''; // <- ID del conjunto de datos (Pixel) de Meta Events Manager
  var STORE_KEY = 'nd_consent_v1';
  var MAX_AGE_DAYS = 365;

  if (!PIXEL_ID) return;

  var isEN = (document.documentElement.lang || '').toLowerCase().indexOf('en') === 0;
  var T = isEN ? {
    title: 'Can we use marketing cookies?',
    body: 'We use Meta cookies only to know whether our ads reach the families who need us and to show them less to people who do not. Nothing is installed unless you say yes.',
    accept: 'Accept',
    reject: 'Reject',
    more: 'Cookie policy',
    policy: '/en/cookie-policy/',
    settings: 'Cookie settings',
    aria: 'Cookie consent'
  } : {
    title: '¿Nos dejas usar cookies de publicidad?',
    body: 'Usamos cookies de Meta solo para saber si nuestros anuncios llegan a las familias que nos necesitan y no molestar a quien no. No se instala nada si no nos dices que sí.',
    accept: 'Aceptar',
    reject: 'Rechazar',
    more: 'Política de cookies',
    policy: '/politica-cookies/',
    settings: 'Configurar cookies',
    aria: 'Consentimiento de cookies'
  };

  /* ---------- almacenamiento ---------- */
  function readConsent() {
    try {
      var raw = localStorage.getItem(STORE_KEY);
      if (!raw) return null;
      var c = JSON.parse(raw);
      if (!c || !c.t || (Date.now() - c.t) > MAX_AGE_DAYS * 864e5) return null;
      return c.marketing === true ? 'granted' : 'denied';
    } catch (e) { return null; }
  }
  function saveConsent(granted) {
    try { localStorage.setItem(STORE_KEY, JSON.stringify({ marketing: !!granted, t: Date.now() })); } catch (e) {}
  }
  function clearConsent() {
    try { localStorage.removeItem(STORE_KEY); } catch (e) {}
    ['_fbp', '_fbc'].forEach(function (n) {
      var host = location.hostname.replace(/^www\./, '');
      document.cookie = n + '=; Max-Age=0; path=/';
      document.cookie = n + '=; Max-Age=0; path=/; domain=.' + host;
    });
  }

  /* ---------- Meta Pixel ---------- */
  var pixelOn = false;
  function loadPixel() {
    if (pixelOn) return;
    pixelOn = true;
    /* Código base oficial de Meta */
    !function (f, b, e, v, n, t, s) {
      if (f.fbq) return; n = f.fbq = function () { n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments); };
      if (!f._fbq) f._fbq = n; n.push = n; n.loaded = !0; n.version = '2.0'; n.queue = [];
      t = b.createElement(e); t.async = !0; t.src = v; s = b.getElementsByTagName(e)[0]; s.parentNode.insertBefore(t, s);
    }(window, document, 'script', 'https://connect.facebook.net/en_US/fbevents.js');
    window.fbq('consent', 'grant');
    window.fbq('init', PIXEL_ID);
    window.fbq('track', 'PageView');
  }
  function track(type, name, params) {
    if (!pixelOn || !window.fbq) return;
    window.fbq(type, name, params || {});
  }

  /* ---------- eventos: formularios Netlify (POST a "/" con form-name) ---------- */
  var LEAD_FORMS = { 'valoracion': 'Valoración', 'calculadora': 'Calculadora', 'te-llamamos': 'Te llamamos' };
  function formNameFromBody(body) {
    try {
      if (typeof body === 'string') return new URLSearchParams(body).get('form-name');
      if (body instanceof URLSearchParams) return body.get('form-name');
      if (typeof FormData !== 'undefined' && body instanceof FormData) return body.get('form-name');
    } catch (e) {}
    return null;
  }
  if (window.fetch) {
    var origFetch = window.fetch;
    window.fetch = function (input, init) {
      try {
        var method = (init && init.method || 'GET').toUpperCase();
        var fname = method === 'POST' && init ? formNameFromBody(init.body) : null;
        if (fname) {
          if (LEAD_FORMS[fname]) {
            track('track', 'Lead', { content_name: LEAD_FORMS[fname], content_category: 'propietarios', lang: isEN ? 'en' : 'es' });
          } else if (fname === 'inversores') {
            track('trackCustom', 'InversorLead', { content_name: 'Inversores', lang: isEN ? 'en' : 'es' });
          }
        }
      } catch (e) {}
      return origFetch.apply(this, arguments);
    };
  }

  /* ---------- eventos: clic en WhatsApp ---------- */
  document.addEventListener('click', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('a[href*="wa.me"], a[href*="api.whatsapp.com"]') : null;
    if (a) track('track', 'Contact', { content_name: 'WhatsApp', lang: isEN ? 'en' : 'es' });
  }, true);

  /* ---------- banner ---------- */
  var CSS = '' +
    '#ndCk{position:fixed;left:16px;right:16px;bottom:16px;z-index:2147483000;display:flex;justify-content:center;pointer-events:none;font-family:inherit}' +
    '#ndCk .ndCkBox{pointer-events:auto;max-width:560px;width:100%;background:#F5F2EC;color:#1A1A1A;border:1px solid rgba(31,58,46,.14);border-radius:14px;box-shadow:0 18px 50px rgba(20,32,26,.18);padding:20px 22px;box-sizing:border-box}' +
    '#ndCk h2{margin:0 0 6px;font-size:16px;line-height:1.3;font-weight:600;color:#1F3A2E;font-family:inherit}' +
    '#ndCk p{margin:0 0 14px;font-size:14px;line-height:1.5;color:#3A4A42}' +
    '#ndCk .ndCkRow{display:flex;flex-wrap:wrap;gap:10px;align-items:center}' +
    '#ndCk button{font:inherit;font-size:14.5px;font-weight:600;cursor:pointer;border-radius:999px;padding:11px 22px;flex:1 1 120px;border:1.5px solid #1F3A2E}' +
    '#ndCk .ndCkA{background:#1F3A2E;color:#F5F2EC}' +
    '#ndCk .ndCkR{background:#F5F2EC;color:#1F3A2E}' +
    '#ndCk button:focus-visible{outline:3px solid #C9A86A;outline-offset:2px}' +
    '#ndCk .ndCkL{flex:1 1 100%;font-size:13px;color:#5A6B7D;text-decoration:underline;margin-top:2px}' +
    '@media (min-width:560px){#ndCk{left:auto;right:24px;bottom:24px;justify-content:flex-end}#ndCk .ndCkL{flex:0 0 auto;margin:0 0 0 4px}}';

  function showBanner() {
    if (document.getElementById('ndCk')) return;
    if (!document.getElementById('ndCkCss')) {
      var st = document.createElement('style'); st.id = 'ndCkCss'; st.textContent = CSS; document.head.appendChild(st);
    }
    var wrap = document.createElement('div');
    wrap.id = 'ndCk';
    wrap.innerHTML =
      '<div class="ndCkBox" role="dialog" aria-live="polite" aria-label="' + T.aria + '" aria-describedby="ndCkTxt">' +
        '<h2>' + T.title + '</h2>' +
        '<p id="ndCkTxt">' + T.body + '</p>' +
        '<div class="ndCkRow">' +
          '<button type="button" class="ndCkR">' + T.reject + '</button>' +
          '<button type="button" class="ndCkA">' + T.accept + '</button>' +
          '<a class="ndCkL" href="' + T.policy + '">' + T.more + '</a>' +
        '</div>' +
      '</div>';
    document.body.appendChild(wrap);
    wrap.querySelector('.ndCkA').addEventListener('click', function () { saveConsent(true); wrap.remove(); loadPixel(); });
    wrap.querySelector('.ndCkR').addEventListener('click', function () { saveConsent(false); wrap.remove(); });
  }

  /* Reabrir preferencias: enlace inyectado junto a "Política de cookies" del pie
     y cualquier elemento con [data-nd-cookies]. */
  function reopen(e) {
    if (e) e.preventDefault();
    var wasOn = pixelOn;
    clearConsent();
    if (wasOn) { location.reload(); return; }
    showBanner();
  }
  function addSettingsLinks() {
    var links = document.querySelectorAll('footer a[href="' + T.policy + '"]');
    Array.prototype.forEach.call(links, function (a) {
      if (a.parentNode.querySelector('[data-nd-cookies]')) return;
      var b = document.createElement('a');
      b.href = '#'; b.setAttribute('data-nd-cookies', '');
      b.textContent = T.settings;
      b.style.cssText = a.getAttribute('style') || '';
      if (a.className) b.className = a.className;
      if (a.parentNode.tagName === 'LI') {
        var li = document.createElement('li');
        li.style.cssText = a.parentNode.getAttribute('style') || '';
        li.appendChild(b); a.parentNode.parentNode.insertBefore(li, a.parentNode.nextSibling);
      } else {
        a.parentNode.insertBefore(b, a.nextSibling);
      }
    });
    document.addEventListener('click', function (e) {
      var t = e.target && e.target.closest ? e.target.closest('[data-nd-cookies]') : null;
      if (t) reopen(e);
    });
  }

  function init() {
    addSettingsLinks();
    var c = readConsent();
    if (c === 'granted') loadPixel();
    else if (c === null) showBanner();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
