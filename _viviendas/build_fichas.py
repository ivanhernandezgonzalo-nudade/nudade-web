#!/usr/bin/env python3
"""Genera una ficha con URL propia por vivienda, en español e inglés, a partir de viviendas.json.

Uso (desde la raíz del repo):  python3 _viviendas/build_fichas.py
build_en.py lo ejecuta al final, así que basta con:  python3 i18n/build_en.py

Reglas
- Vivienda "disponible" o "reservada": tiene ficha en /viviendas/<id>/ y /en/homes/<id>/.
- Vivienda "vendida" o eliminada de viviendas.json: su ficha se borra, la tarjeta deja de
  enlazar y la URL antigua redirige (301) al listado, para no dejar enlaces rotos.
- _viviendas/publicadas.json guarda todos los id que han tenido ficha alguna vez, para
  mantener esas redirecciones en _redirects.
- El sitemap se actualiza solo con las fichas vigentes.

El diseño reutiliza viviendas.html y en/homes.html (menú, pie, modales, banda de inversores
y script), así que cualquier cambio de estilo en el listado se hereda en las fichas.
"""
import datetime
import html
import json
import os
import re
import shutil
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://nudade.es"
TODAY = datetime.date.today().isoformat()
WA = "34604149420"

M_HEADER = "<!-- ===================== HEADER ===================== -->"
M_CTA = "<!-- ===================== CTA BAND ===================== -->"
M_FOOT = "<!-- ===================== FOOTER ===================== -->"
SEO_START, SEO_END = "<!-- seo:start -->", "<!-- seo:end -->"
RED_START, RED_END = "# fichas:start (generado por _viviendas/build_fichas.py)", "# fichas:end"

E = html.escape

T = {
    "es": {
        "home": "Inicio", "list": "Viviendas", "list_url": "/viviendas.html", "home_url": "/",
        "ficha": "/viviendas/{id}/", "back_list": "Ver todas las viviendas", "back_home": "Volver al inicio",
        "eyebrow": "Vivienda en nuda propiedad", "reservada": "Reservada", "disponible": "Disponible",
        "pago": "Pago inicial", "renta": "Renta mensual vitalicia", "modalidad": "Modalidad", "unico": "Pago único",
        "tasacion": "Tasación oficial", "info": "Solicitar información", "wa": "Preguntar por WhatsApp",
        "wa_txt": "Hola Nudade, me interesa la vivienda {t} ({u})",
        "nota": "Sin compromiso. Te respondemos en menos de 24 horas.",
        "nota_res": "Esta vivienda está reservada. Si la operación no sigue adelante, te avisamos con prioridad.",
        "carac": "Características", "hab": "Habitaciones", "sup": "Superficie", "planta": "Planta",
        "asc": "Ascensor", "si": "Sí", "no": "No", "ubic": "Ubicación", "extras": "Extras",
        "desc": "Descripción", "usu": "Usufructuarios", "usu_1": "1 usufructuario", "usu_n": "{n} usufructuarios",
        "usu_txt": "Los usufructuarios siguen viviendo en la casa de por vida. El comprador adquiere hoy la nuda propiedad y recupera el pleno dominio cuando se extingue el usufructo.",
        "anyos": "años", "sexo": {"Mujer": "Mujer", "Hombre": "Hombre"},
        "como": "Cómo se compra una nuda propiedad",
        "pasos": [("Te enviamos el dossier", "Documentación de la vivienda, nota simple y tasación, para que lo estudies con calma."),
                  ("Visita y oferta", "Organizamos la visita respetando a los usufructuarios y te acompañamos en la negociación."),
                  ("Firma ante notario", "Escritura e inscripción en el Registro de la Propiedad, con todo el proceso revisado.")],
        "otras": "Otras viviendas disponibles", "ver": "Ver ficha",
        "foto": "foto", "de": "de", "render": "Recreación · posible reforma",
        "render_alt": ", recreación de una posible reforma", "prox": "Fotos próximamente",
        "prev": "Foto anterior", "next": "Foto siguiente", "ver_foto": "Ver foto {n}",
        "title": "{t} en nuda propiedad | Nudade",
        "mdesc": "{t}: {f}. Pago inicial {p}{r}. Ficha completa con fotos y datos de la vivienda en nuda propiedad.",
        "renta_d": ", renta de {r}", "mes": "{x}/mes", "lang": "es", "locale": "es_ES", "alt_locale": "en_GB",
    },
    "en": {
        "home": "Home", "list": "Homes", "list_url": "/en/homes.html", "home_url": "/en/",
        "ficha": "/en/homes/{id}/", "back_list": "See all homes", "back_home": "Back to home",
        "eyebrow": "Home for sale in bare ownership", "reservada": "Reserved", "disponible": "Available",
        "pago": "Upfront payment", "renta": "Lifetime monthly income", "modalidad": "Payment", "unico": "Lump sum",
        "tasacion": "Official valuation", "info": "Request information", "wa": "Ask on WhatsApp",
        "wa_txt": "Hi Nudade, I am interested in the home {t} ({u})",
        "nota": "No obligation. We reply within 24 hours.",
        "nota_res": "This home is reserved. If the sale does not go ahead, we will let you know first.",
        "carac": "Key features", "hab": "Bedrooms", "sup": "Floor area", "planta": "Floor",
        "asc": "Lift", "si": "Yes", "no": "No", "ubic": "Location", "extras": "Extras",
        "desc": "Description", "usu": "Residents", "usu_1": "1 resident", "usu_n": "{n} residents",
        "usu_txt": "The residents keep living in the home for life. The buyer acquires the bare ownership today and gains full ownership when the lifetime right ends.",
        "anyos": "years old", "sexo": {"Mujer": "Woman", "Hombre": "Man"},
        "como": "How buying bare ownership works",
        "pasos": [("We send you the dossier", "Property documents, Land Registry extract and valuation, so you can review everything calmly."),
                  ("Viewing and offer", "We arrange the viewing with respect for the residents and support you through the negotiation."),
                  ("Signing before a notary", "Deed and registration in the Land Registry, with the whole process checked.")],
        "otras": "Other homes available", "ver": "View details",
        "foto": "photo", "de": "of", "render": "Rendering · possible renovation",
        "render_alt": ", rendering of a possible renovation", "prox": "Photos coming soon",
        "prev": "Previous photo", "next": "Next photo", "ver_foto": "Show photo {n}",
        "title": "{t} in bare ownership, Spain | Nudade",
        "mdesc": "{t}: {f}. Upfront payment {p}{r}. Full details and photos of this bare ownership home in Spain.",
        "renta_d": ", income of {r}", "mes": "{x} a month", "lang": "en", "locale": "en_GB", "alt_locale": "es_ES",
    },
}


def eur_en(s):
    if not s:
        return s
    digits = re.sub(r"[^0-9,]", "", str(s)).replace(",", ".")
    try:
        n = float(digits)
    except ValueError:
        return s
    return "€{:,.0f}".format(n)


def floor_en(s):
    if not s:
        return s
    m = re.match(r"^(\d+)\s*[ªº]?\s*planta", s, re.I)
    if m:
        n = int(m.group(1))
        suf = "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return "%d%s floor" % (n, suf)
    if re.match(r"^bajo", s, re.I):
        return "Ground floor"
    if re.match(r"^[aá]tico", s, re.I):
        return "Penthouse"
    return s


def num(s):
    d = re.sub(r"[^0-9,]", "", str(s or "")).replace(",", ".")
    try:
        return float(d)
    except ValueError:
        return None


def loc(v, lang):
    """Devuelve los datos de la vivienda listos para mostrar en el idioma pedido."""
    o = dict(v)
    if lang == "en":
        e = v.get("en") or {}
        o.update(e)
        if not e.get("altura"):
            o["altura"] = floor_en(v.get("altura"))
        o["pagoInicial"] = eur_en(v.get("pagoInicial"))
        o["tasacion"] = eur_en(v.get("tasacion"))
        if o.get("superficie"):
            o["superficie"] = str(o["superficie"]).replace(",", ".")
        if v.get("renta"):
            o["renta"] = T["en"]["mes"].format(x=eur_en(v["renta"]))
    return o


def active(v):
    return bool(v.get("id")) and (v.get("estado") or "disponible") != "vendida"


def photos(v):
    f = v.get("fotos") or ([v["foto"]] if v.get("foto") else [])
    return [] if v.get("sinFotos") and not v.get("fotos") else f


def gallery(o, t):
    fotos = photos(o)
    renders = o.get("renders") or []
    alt = o.get("titulo") or o.get("localidad") or "Vivienda"
    if not fotos:
        return ('<div style="position:relative;aspect-ratio:4/3;border-radius:14px;overflow:hidden;background:repeating-linear-gradient(135deg,#ECE7DD,#ECE7DD 12px,#E4DED2 12px,#E4DED2 24px);display:flex;align-items:center;justify-content:center">'
                '<span style="font-size:14px;font-weight:600;color:#5A6B7D;background:#F5F2EC;padding:8px 16px;border-radius:999px">' + E(t["prox"]) + '</span></div>')
    n = len(fotos)
    rtag = ('<span style="position:absolute;left:14px;bottom:14px;background:rgba(15,22,18,.74);color:#F5F2EC;font-size:12px;font-weight:700;letter-spacing:.03em;padding:6px 12px;border-radius:999px;pointer-events:none">'
            + E(t["render"]) + '</span>')
    slides = "".join(
        '<div class="ndFSlide" style="flex:0 0 100%;width:100%;height:100%;position:relative;scroll-snap-align:start">'
        '<img src="/' + E(f) + '" alt="' + E(alt) + ' (' + t["foto"] + ' ' + str(i + 1) + ' ' + t["de"] + ' ' + str(n)
        + (t["render_alt"] if f in renders else '') + ')"' + (' data-render="1"' if f in renders else '')
        + ' loading="' + ('eager' if i == 0 else 'lazy') + '" style="width:100%;height:100%;object-fit:cover;cursor:zoom-in">'
        + (rtag if f in renders else '') + '</div>'
        for i, f in enumerate(fotos))
    arrow = ('<button class="{c}" aria-label="{l}" style="position:absolute;{side}:14px;top:50%;transform:translateY(-50%);width:44px;height:44px;border-radius:50%;border:none;background:rgba(245,242,236,.92);color:#1F3A2E;font-size:26px;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 6px 18px -8px rgba(0,0,0,.35)">{g}</button>')
    nav = ""
    if n > 1:
        nav = (arrow.format(c="ndFPrev", l=E(t["prev"]), side="left", g="&lsaquo;")
               + arrow.format(c="ndFNext", l=E(t["next"]), side="right", g="&rsaquo;")
               + '<span id="ndFCnt" style="position:absolute;right:14px;bottom:14px;background:rgba(15,22,18,.62);color:#F5F2EC;font-size:12.5px;font-weight:600;letter-spacing:.04em;padding:6px 11px;border-radius:999px;pointer-events:none">1 / ' + str(n) + '</span>')
    main = ('<div style="position:relative;aspect-ratio:4/3;border-radius:14px;overflow:hidden;background:#ECE7DD">'
            '<div id="ndFGal" class="ndGal" style="position:absolute;top:0;left:0;right:0;bottom:0;display:flex;overflow-x:auto;overflow-y:hidden;scroll-snap-type:x mandatory;scrollbar-width:none;-ms-overflow-style:none;-webkit-overflow-scrolling:touch">'
            + slides + '</div>' + nav + '</div>')
    thumbs = ""
    if n > 1:
        thumbs = ('<div class="ndGal" style="display:flex;gap:10px;margin-top:12px;overflow-x:auto;scrollbar-width:none;padding-bottom:2px">'
                  + "".join('<button class="ndFThumb" data-i="' + str(i) + '" aria-label="' + E(t["ver_foto"].format(n=i + 1)) + '" style="flex:0 0 auto;width:92px;height:69px;padding:0;border:2px solid ' + ('#1F3A2E' if i == 0 else 'transparent') + ';border-radius:8px;overflow:hidden;cursor:pointer;background:#ECE7DD;opacity:' + ('1' if i == 0 else '.72') + ';transition:opacity .2s, border-color .2s">'
                            '<img src="/' + E(f) + '" alt="" loading="lazy" style="width:100%;height:100%;object-fit:cover;display:block"></button>' for i, f in enumerate(fotos))
                  + '</div>')
    return main + thumbs


def chip(txt):
    return '<span style="font-size:13.5px;color:#1A1A1A;background:#F5F2EC;border:1px solid rgba(31,58,46,.1);padding:6px 12px;border-radius:6px;font-weight:500">' + E(txt) + '</span>'


def fact(label, val):
    return ('<div style="background:#fff;border:1px solid rgba(31,58,46,.1);border-radius:10px;padding:16px 18px">'
            '<span style="display:block;font-size:11.5px;text-transform:uppercase;letter-spacing:.09em;color:#5A6B7D;font-weight:600;margin-bottom:6px">' + E(label) + '</span>'
            '<strong style="font-size:1.05rem;color:#1F3A2E;font-weight:700">' + E(val) + '</strong></div>')


def h2(txt):
    return '<h2 style="font-size:clamp(1.35rem,2.2vw,1.7rem);line-height:1.15;letter-spacing:-.015em;color:#1F3A2E;font-weight:700;margin-bottom:16px">' + E(txt) + '</h2>'


def mini_card(o, t):
    fotos = photos(o)
    url = t["ficha"].format(id=o["id"])
    img = ('<img src="/' + E(fotos[0]) + '" alt="' + E(o.get("titulo", "")) + '" loading="lazy" style="width:100%;height:100%;object-fit:cover">' if fotos
           else '<span style="font-size:12px;color:#5A6B7D;background:#F5F2EC;padding:5px 11px;border-radius:999px">' + E(t["prox"]) + '</span>')
    price = o.get("pagoInicial") or ""
    return ('<a href="' + url + '" class="ndFMini" style="display:flex;flex-direction:column;background:#fff;border:1px solid rgba(31,58,46,.1);border-radius:12px;overflow:hidden;text-decoration:none;transition:transform .35s ease, box-shadow .35s ease">'
            '<span style="display:flex;align-items:center;justify-content:center;aspect-ratio:4/3;overflow:hidden;background:repeating-linear-gradient(135deg,#ECE7DD,#ECE7DD 12px,#E4DED2 12px,#E4DED2 24px)">' + img + '</span>'
            '<span style="display:flex;flex-direction:column;gap:4px;padding:16px 18px 18px">'
            '<strong style="font-size:1rem;color:#1A1A1A;font-weight:700">' + E(o.get("localidad", "")) + '</strong>'
            '<span style="font-size:13.5px;color:#5A6B7D">' + E(o.get("zona", "")) + '</span>'
            '<span style="display:flex;justify-content:space-between;align-items:center;margin-top:10px;padding-top:12px;border-top:1px solid rgba(31,58,46,.1)">'
            '<span style="font-size:1.05rem;font-weight:700;color:#1F3A2E">' + E(price) + '</span>'
            '<span style="font-size:13.5px;font-weight:700;color:#1F3A2E">' + E(t["ver"]) + ' ›</span></span></span></a>')


def content(v, todas, lang, cta_band):
    t = T[lang]
    o = loc(v, lang)
    estado = o.get("estado") or "disponible"
    url = t["ficha"].format(id=o["id"])
    titulo = o.get("titulo") or o.get("localidad")
    sub = ", ".join(x for x in [o.get("zona"), o.get("localidad")] if x) + (" · " + o["cp"] if o.get("cp") else "")
    owners = o.get("propietarios") or []
    usu_lbl = t["usu_1"] if len(owners) == 1 else t["usu_n"].format(n=len(owners))
    pills = "".join('<span style="font-size:14px;font-weight:600;color:#1F3A2E;background:rgba(31,58,46,.08);border-radius:999px;padding:7px 14px">'
                    + E(t["sexo"].get(p.get("sexo"), p.get("sexo", ""))) + ' · ' + E(str(p.get("edad", ""))) + ' ' + t["anyos"] + '</span>' for p in owners)

    facts = []
    if o.get("habitaciones"):
        facts.append(fact(t["hab"], o["habitaciones"]))
    if o.get("superficie"):
        facts.append(fact(t["sup"], o["superficie"]))
    if o.get("altura"):
        facts.append(fact(t["planta"], o["altura"]))
    facts.append(fact(t["asc"], t["si"] if o.get("ascensor") else t["no"]))
    facts.append(fact(t["ubic"], ", ".join(x for x in [o.get("zona"), o.get("localidad")] if x)))
    extras = "".join(chip(x) for x in (o.get("extras") or []))

    chip_estado = ('<span style="display:inline-block;background:#C25A48;color:#F5F2EC;font-size:12px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;padding:6px 12px;border-radius:999px">' + E(t["reservada"]) + '</span>'
                   if estado == "reservada" else
                   '<span style="display:inline-block;background:rgba(31,58,46,.1);color:#1F3A2E;font-size:12px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;padding:6px 12px;border-radius:999px">' + E(t["disponible"]) + '</span>')
    etiqueta = ('<span style="display:inline-block;background:#F5F2EC;border:1px solid rgba(31,58,46,.18);color:#1F3A2E;font-size:12px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;padding:6px 12px;border-radius:999px">' + E(o["etiqueta"]) + '</span>'
                if o.get("etiqueta") else "")

    renta_row = ((t["renta"], o["renta"]) if o.get("renta") else (t["modalidad"], t["unico"]))
    wa_txt = t["wa_txt"].format(t=titulo, u="nudade.es" + url)
    wa_href = "https://wa.me/" + WA + "?text=" + urllib.parse.quote(wa_txt)
    side = (
        '<aside class="ndFSide" style="grid-column:2;grid-row:1 / span 2;align-self:start;position:sticky;top:96px;background:#fff;border:1px solid rgba(31,58,46,.12);border-radius:14px;padding:clamp(22px,2.6vw,30px);box-shadow:0 24px 50px -34px rgba(31,58,46,.35)">'
        '<span style="display:block;font-size:11.5px;text-transform:uppercase;letter-spacing:.09em;color:#5A6B7D;font-weight:600">' + E(t["pago"]) + '</span>'
        '<strong style="display:block;font-size:clamp(1.9rem,3vw,2.4rem);letter-spacing:-.02em;color:#1F3A2E;font-weight:700;line-height:1.1;margin:4px 0 18px">' + E(o.get("pagoInicial") or "") + '</strong>'
        '<div style="display:flex;justify-content:space-between;gap:14px;padding:13px 0;border-top:1px solid rgba(31,58,46,.1);font-size:14.5px"><span style="color:#5A6B7D">' + E(renta_row[0]) + '</span><strong style="color:#1F3A2E;text-align:right">' + E(renta_row[1]) + '</strong></div>'
        + ('<div style="display:flex;justify-content:space-between;gap:14px;padding:13px 0;border-top:1px solid rgba(31,58,46,.1);font-size:14.5px"><span style="color:#5A6B7D">' + E(t["tasacion"]) + '</span><strong style="color:#1A1A1A">' + E(o["tasacion"]) + '</strong></div>' if o.get("tasacion") else '')
        + '<div style="display:flex;justify-content:space-between;gap:14px;padding:13px 0;border-top:1px solid rgba(31,58,46,.1);font-size:14.5px"><span style="color:#5A6B7D">' + E(t["usu"]) + '</span><strong style="color:#1F3A2E;text-align:right">' + E(", ".join(str(p.get("edad", "")) for p in owners) + " " + t["anyos"] if owners else "") + '</strong></div>'
        '<button class="ndCallTrigger ndFBtn" style="font-family:inherit;cursor:pointer;display:block;width:100%;margin-top:18px;background:#1F3A2E;color:#F5F2EC;border:2px solid #1F3A2E;padding:15px;border-radius:999px;font-size:15px;font-weight:700;transition:background .25s">' + E(t["info"]) + '</button>'
        '<a href="' + E(wa_href) + '" target="_blank" rel="noopener" style="display:flex;align-items:center;justify-content:center;gap:9px;width:100%;margin-top:10px;background:transparent;color:#1F3A2E;border:1.5px solid #1F3A2E;padding:13px;border-radius:999px;font-size:14.5px;font-weight:700;text-decoration:none">'
        '<svg viewBox="0 0 24 24" aria-hidden="true" style="width:18px;height:18px"><path fill="#25D366" d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2.05 22l5.25-1.38a9.9 9.9 0 0 0 4.74 1.21h.01c5.46 0 9.91-4.45 9.91-9.91A9.85 9.85 0 0 0 12.04 2z"/></svg>'
        + E(t["wa"]) + '</a>'
        '<p style="font-size:12.5px;line-height:1.5;color:#5A6B7D;text-align:center;margin-top:14px">' + E(t["nota_res"] if estado == "reservada" else t["nota"]) + '</p>'
        '</aside>')

    pasos = "".join('<li style="display:flex;gap:14px;align-items:flex-start"><span style="flex:0 0 auto;display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;border-radius:50%;background:#1F3A2E;color:#F5F2EC;font-size:13px;font-weight:700">' + str(i + 1) + '</span>'
                    '<span><strong style="display:block;font-size:15px;color:#1F3A2E;margin-bottom:3px">' + E(a) + '</strong><span style="font-size:14.5px;line-height:1.55;color:#5A6B7D">' + E(b) + '</span></span></li>'
                    for i, (a, b) in enumerate(t["pasos"]))

    otras = [loc(x, lang) for x in todas if active(x) and x["id"] != v["id"]]
    otras.sort(key=lambda x: ({"disponible": 0, "reservada": 1}.get(x.get("estado") or "disponible", 2), x.get("orden") or 99))
    otras = otras[:3]
    otras_html = ""
    if otras:
        otras_html = ('<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px;margin-bottom:30px">'
                      + "".join(mini_card(x, t) for x in otras) + '</div>')

    btn_p = 'display:inline-block;background:#1F3A2E;color:#F5F2EC;padding:15px 28px;border-radius:999px;font-size:15px;font-weight:600;text-decoration:none'
    btn_s = 'display:inline-block;background:transparent;color:#1F3A2E;border:1.5px solid #1F3A2E;padding:13px 26px;border-radius:999px;font-size:15px;font-weight:600;text-decoration:none'

    return (
        '<!-- ===================== FICHA ===================== -->\n'
        '<style>@media (max-width:980px){.ndFichaGrid{grid-template-columns:minmax(0,1fr) !important;row-gap:28px !important}.ndFichaGrid>*{grid-column:1 !important;grid-row:auto !important}.ndFSide{position:static !important}}'
        '@media (max-width:640px){.ndFFacts{grid-template-columns:1fr 1fr !important}}.ndFMini:hover{transform:translateY(-4px);box-shadow:0 18px 40px -22px rgba(31,58,46,.35)}.ndFThumb:hover{opacity:1 !important}</style>\n'
        '<main id="ndFicha" data-id="' + E(o["id"]) + '">\n'
        '<header id="top" style="position:relative;padding:118px clamp(20px,5vw,44px) clamp(22px,3vw,34px);overflow:hidden;background:#F5F2EC">'
        '<svg viewBox="0 0 600 600" fill="none" stroke="#1F3A2E" stroke-width="1.2" style="position:absolute;top:-160px;right:-180px;width:680px;height:680px;opacity:.05;pointer-events:none"><path d="M60 580 L60 300 A240 240 0 0 1 540 300 L540 580"/><path d="M180 580 L180 330 A120 120 0 0 1 420 330 L420 580"/></svg>'
        '<div style="max-width:1240px;margin:0 auto;position:relative">'
        '<nav aria-label="breadcrumb" style="font-size:13.5px;color:#5A6B7D;font-weight:600;margin-bottom:18px;display:flex;flex-wrap:wrap;gap:8px">'
        '<a href="' + t["home_url"] + '" style="color:#5A6B7D">' + E(t["home"]) + '</a><span aria-hidden="true">›</span>'
        '<a href="' + t["list_url"] + '" style="color:#5A6B7D">' + E(t["list"]) + '</a><span aria-hidden="true">›</span>'
        '<span style="color:#1F3A2E">' + E(o.get("localidad", "")) + '</span></nav>'
        '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px">' + chip_estado + etiqueta + '</div>'
        '<p style="font-size:13px;text-transform:uppercase;letter-spacing:.2em;color:#5A6B7D;font-weight:600;margin-bottom:12px">' + E(t["eyebrow"]) + '</p>'
        '<h1 style="font-size:clamp(2rem,4.4vw,3.2rem);line-height:1.06;letter-spacing:-.03em;color:#1F3A2E;font-weight:700;max-width:900px;text-wrap:balance">' + E(titulo) + '</h1>'
        '<p style="font-size:clamp(1rem,1.4vw,1.15rem);color:#5A6B7D;margin-top:10px">' + E(sub) + '</p>'
        '</div></header>\n'
        '<section style="background:#F5F2EC;padding:0 clamp(20px,5vw,44px) clamp(60px,8vw,100px)">'
        '<div class="ndFichaGrid" style="max-width:1240px;margin:0 auto;display:grid;grid-template-columns:minmax(0,1.65fr) minmax(0,1fr);column-gap:clamp(26px,4vw,52px);row-gap:44px;align-items:start">'
        '<div class="ndFGalCol" style="grid-column:1;grid-row:1">' + gallery(o, t) + '</div>' + side
        + '<div class="ndFInfo" style="grid-column:1;grid-row:2">'
        + '<div style="margin-top:4px">' + h2(t["carac"]) + '<div class="ndFFacts" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">' + "".join(facts) + '</div>'
        + ('<div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:16px">' + extras + '</div>' if extras else '') + '</div>'
        + ('<div style="margin-top:44px">' + h2(t["desc"]) + '<p style="font-size:16px;line-height:1.7;color:#3A4A40;max-width:760px">' + E(o["descripcion"]) + '</p></div>' if o.get("descripcion") else '')
        + '<div style="margin-top:44px">' + h2(usu_lbl) + '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px">' + pills + '</div><p style="font-size:15px;line-height:1.65;color:#5A6B7D;max-width:760px">' + E(t["usu_txt"]) + '</p></div>'
        + '<div style="margin-top:44px;background:#ECE7DD;border-radius:14px;padding:clamp(22px,3vw,32px)">' + h2(t["como"]) + '<ol style="list-style:none;display:flex;flex-direction:column;gap:16px">' + pasos + '</ol></div>'
        + '</div></div></section>\n'
        '<section style="background:#ECE7DD;padding:clamp(56px,7vw,90px) clamp(20px,5vw,44px)">'
        '<div style="max-width:1240px;margin:0 auto">'
        + (h2(t["otras"]) + otras_html if otras else '')
        + '<div style="display:flex;flex-wrap:wrap;gap:12px">'
        '<a href="' + t["list_url"] + '" class="ndBtnP" style="' + btn_p + '">' + E(t["back_list"]) + '</a>'
        '<a href="' + t["home_url"] + '" style="' + btn_s + '">' + E(t["back_home"]) + '</a></div>'
        '</div></section>\n'
        '</main>\n\n' + cta_band
    )


SCRIPT = r"""
    /* ---------- FICHA (galería) ---------- */
    (() => {
      const g = $('#ndFGal'); if (!g) return;
      const slides = $$('.ndFSlide', g), thumbs = $$('.ndFThumb'), cnt = $('#ndFCnt'), n = slides.length;
      const imgs = slides.map(s => s.querySelector('img'));
      const srcs = imgs.map(im => im.getAttribute('src'));
      const flags = imgs.map(im => im.getAttribute('data-render') === '1');
      const cur = () => Math.round(g.scrollLeft / Math.max(1, g.clientWidth));
      const go = (i) => { i = (i + n) % n; g.scrollTo({ left: i * g.clientWidth, behavior: 'smooth' }); };
      const mark = () => {
        const i = cur();
        if (cnt) cnt.textContent = (i + 1) + ' / ' + n;
        thumbs.forEach((b, k) => { b.style.borderColor = k === i ? '#1F3A2E' : 'transparent'; b.style.opacity = k === i ? '1' : '.72'; });
        const a = thumbs[i]; if (a && a.parentElement) { const p = a.parentElement; const x = a.offsetLeft - (p.clientWidth - a.clientWidth) / 2; p.scrollTo({ left: x, behavior: 'smooth' }); }
      };
      let t = null;
      g.addEventListener('scroll', () => { clearTimeout(t); t = setTimeout(mark, 60); }, { passive: true });
      const pv = $('.ndFPrev'), nx = $('.ndFNext');
      if (pv) pv.addEventListener('click', () => go(cur() - 1));
      if (nx) nx.addEventListener('click', () => go(cur() + 1));
      thumbs.forEach(b => b.addEventListener('click', () => go(parseInt(b.getAttribute('data-i'), 10))));
      imgs.forEach((im, k) => im.addEventListener('click', () => openLB(srcs, k, (im.getAttribute('alt') || '').replace(/ \(.*$/, ''), flags)));
      document.addEventListener('keydown', (e) => { if (document.querySelector('[aria-modal="true"]')) return; if (e.key === 'ArrowRight') go(cur() + 1); else if (e.key === 'ArrowLeft') go(cur() - 1); });
      window.addEventListener('resize', () => { const i = cur(); g.scrollLeft = i * g.clientWidth; });
    })();
    $$('.ndFBtn').forEach(b => { b.addEventListener('mouseenter', () => { b.style.background = '#14271E'; }); b.addEventListener('mouseleave', () => { b.style.background = '#1F3A2E'; }); });
"""


def head_block(v, lang, url_es, url_en):
    t = T[lang]
    o = loc(v, lang)
    url = BASE + (url_es if lang == "es" else url_en)
    titulo = o.get("titulo") or o.get("localidad")
    f = []
    if o.get("habitaciones"):
        f.append(o["habitaciones"] + (" habitaciones" if lang == "es" else " bedrooms"))
    if o.get("superficie"):
        f.append(o["superficie"])
    f.append(", ".join(x for x in [o.get("zona"), o.get("localidad")] if x))
    desc = t["mdesc"].format(t=titulo, f=", ".join(f), p=o.get("pagoInicial") or "",
                             r=t["renta_d"].format(r=o["renta"]) if o.get("renta") else "")
    if len(desc) > 165:
        desc = desc[:162].rsplit(" ", 1)[0] + "…"
    title = t["title"].format(t=titulo)
    fotos = photos(v)
    img = BASE + "/" + fotos[0] if fotos else BASE + "/assets/og-nudade.jpg"
    meta = lambda k, val, p=True: '<meta %s="%s" content="%s">' % ("property" if p else "name", k, E(val, quote=True))
    tags = [meta("og:type", "website"), meta("og:site_name", "Nudade"), meta("og:locale", t["locale"]),
            meta("og:locale:alternate", t["alt_locale"]), meta("og:url", url), meta("og:title", title),
            meta("og:description", desc), meta("og:image", img), meta("og:image:alt", titulo),
            meta("twitter:card", "summary_large_image", False), meta("twitter:title", title, False),
            meta("twitter:description", desc, False), meta("twitter:image", img, False)]
    estado = v.get("estado") or "disponible"
    residence = {"@type": "Residence", "name": titulo,
                 "address": {"@type": "PostalAddress", "addressLocality": v.get("localidad", ""), "addressCountry": "ES"}}
    if v.get("cp"):
        residence["address"]["postalCode"] = v["cp"]
    if v.get("zona"):
        residence["address"]["addressRegion"] = v["zona"]
    if num(v.get("habitaciones")):
        residence["numberOfRooms"] = int(num(v["habitaciones"]))
    if num(v.get("superficie")):
        residence["floorSize"] = {"@type": "QuantitativeValue", "value": num(v["superficie"]), "unitCode": "MTK"}
    listing = {"@type": "RealEstateListing", "@id": url + "#listing", "url": url, "name": titulo,
               "description": o.get("descripcion") or desc, "inLanguage": lang,
               "image": [BASE + "/" + x for x in fotos], "about": residence,
               "provider": {"@id": BASE + "/#org"}}
    if num(v.get("pagoInicial")):
        listing["offers"] = {"@type": "Offer", "price": int(num(v["pagoInicial"])), "priceCurrency": "EUR",
                             "availability": "https://schema.org/" + ("LimitedAvailability" if estado == "reservada" else "InStock"),
                             "seller": {"@id": BASE + "/#org"}}
    crumbs = {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": t["home"], "item": BASE + t["home_url"]},
        {"@type": "ListItem", "position": 2, "name": t["list"], "item": BASE + t["list_url"]},
        {"@type": "ListItem", "position": 3, "name": titulo, "item": url}]}
    ld = json.dumps({"@context": "https://schema.org", "@graph": [listing, crumbs]}, ensure_ascii=False, indent=1).replace("</", "<\\/")
    return title, desc, url, SEO_START + "\n" + "\n".join(tags) + '\n<script type="application/ld+json">\n' + ld + "\n</script>\n" + SEO_END


def page(shell, v, todas, lang):
    url_es = T["es"]["ficha"].format(id=v["id"])
    url_en = T["en"]["ficha"].format(id=v["id"])
    s = shell
    cta_band = s[s.index(M_CTA):s.index(M_FOOT)]
    s = s[:s.index(M_HEADER)] + content(v, todas, lang, cta_band) + s[s.index(M_FOOT):]
    title, desc, url, block = head_block(v, lang, url_es, url_en)
    s = re.sub(re.escape(SEO_START) + r".*?" + re.escape(SEO_END), lambda m: block, s, count=1, flags=re.S)
    s = re.sub(r"<title>.*?</title>", lambda m: "<title>" + E(title, quote=False) + "</title>", s, count=1)
    s = re.sub(r'<meta name="description" content="[^"]*">', lambda m: '<meta name="description" content="' + E(desc) + '">', s, count=1)
    s = re.sub(r'<link rel="canonical" href="[^"]*">', '<link rel="canonical" href="' + url + '">', s, count=1)
    s = re.sub(r'<link rel="alternate" hreflang="es" href="[^"]*">', '<link rel="alternate" hreflang="es" href="' + BASE + url_es + '">', s, count=1)
    s = re.sub(r'<link rel="alternate" hreflang="en" href="[^"]*">', '<link rel="alternate" hreflang="en" href="' + BASE + url_en + '">', s, count=1)
    s = re.sub(r'<link rel="alternate" hreflang="x-default" href="[^"]*">', '<link rel="alternate" hreflang="x-default" href="' + BASE + url_es + '">', s, count=1)
    # selector de idioma
    other = url_en if lang == "es" else url_es
    olang = "en" if lang == "es" else "es"
    s = re.sub(r'href="[^"]*"(?=[^>]*hreflang="' + olang + '")', 'href="' + other + '"', s)
    # rutas absolutas (la ficha vive en un subdirectorio)
    s = s.replace('src="./support.js"', 'src="/support.js"').replace('src="assets/', 'src="/assets/')
    s = s.replace('href="index.html', 'href="/').replace('href="viviendas.html"', 'href="/viviendas.html"')
    s = s.replace("fetch('viviendas.json'", "fetch('/viviendas.json'")
    s = s.replace('data-screen-label="Nudade viviendas"', 'data-screen-label="Nudade ficha"')
    # script de la galería, antes de la carga de viviendas.json
    m = re.search(r"\n    fetch\('/viviendas\.json'", s)
    assert m, "no encuentro el fetch de viviendas.json en el script"
    s = s[:m.start()] + "\n" + SCRIPT.rstrip("\n") + s[m.start():]
    return s


def update_sitemap(ids):
    path = os.path.join(ROOT, "sitemap.xml")
    s = open(path, encoding="utf-8").read()
    s = re.sub(r"  <url><loc>https://nudade\.es/(?:en/homes|viviendas)/[^<]+/</loc>.*?</url>\n", "", s)
    rows = ""
    for i in ids:
        es, en = BASE + T["es"]["ficha"].format(id=i), BASE + T["en"]["ficha"].format(id=i)
        alt = '<xhtml:link rel="alternate" hreflang="es" href="%s"/><xhtml:link rel="alternate" hreflang="en" href="%s"/>' % (es, en)
        for u in (es, en):
            rows += "  <url><loc>%s</loc><lastmod>%s</lastmod><priority>0.7</priority>%s</url>\n" % (u, TODAY, alt)
    anchor = "  <url><loc>https://nudade.es/en/homes.html</loc>"
    i = s.index(anchor)
    j = s.index("\n", i) + 1
    s = s[:j] + rows + s[j:]
    open(path, "w", encoding="utf-8").write(s)


def update_redirects(retired):
    path = os.path.join(ROOT, "_redirects")
    s = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    s = re.sub(re.escape(RED_START) + r".*?" + re.escape(RED_END) + r"\n?", "", s, flags=re.S)
    lines = [RED_START,
             "/viviendas/            /viviendas.html     301",
             "/en/homes/             /en/homes.html      301"]
    for i in sorted(retired):
        lines.append("/viviendas/%s/  /viviendas.html  301" % i)
        lines.append("/en/homes/%s/  /en/homes.html  301" % i)
    lines.append(RED_END)
    s = s.rstrip("\n") + ("\n\n" if s.strip() else "") + "\n".join(lines) + "\n"
    open(path, "w", encoding="utf-8").write(s.lstrip("\n"))


def build():
    data = json.load(open(os.path.join(ROOT, "viviendas.json"), encoding="utf-8"))
    todas = data.get("viviendas", [])
    reg_path = os.path.join(ROOT, "_viviendas", "publicadas.json")
    registro = json.load(open(reg_path, encoding="utf-8")) if os.path.exists(reg_path) else []
    vivas = [v for v in todas if active(v)]
    ids = [v["id"] for v in vivas]
    shells = {"es": open(os.path.join(ROOT, "viviendas.html"), encoding="utf-8").read(),
              "en": open(os.path.join(ROOT, "en", "homes.html"), encoding="utf-8").read()}
    dirs = {"es": os.path.join(ROOT, "viviendas"), "en": os.path.join(ROOT, "en", "homes")}
    for lang, d in dirs.items():
        os.makedirs(d, exist_ok=True)
        for name in os.listdir(d):  # fichas retiradas
            if name not in ids and os.path.isdir(os.path.join(d, name)):
                shutil.rmtree(os.path.join(d, name))
        for v in vivas:
            out = os.path.join(d, v["id"], "index.html")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            open(out, "w", encoding="utf-8").write(page(shells[lang], v, todas, lang))
    registro = sorted(set(registro) | set(ids))
    json.dump(registro, open(reg_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    update_sitemap(ids)
    update_redirects([i for i in registro if i not in ids])
    print("OK: fichas generadas (%d) en /viviendas/<id>/ y /en/homes/<id>/" % len(ids))


if __name__ == "__main__":
    build()
