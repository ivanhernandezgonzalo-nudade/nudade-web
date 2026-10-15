#!/usr/bin/env python3
"""Genera la versión en inglés (/en/) a partir de index.html y viviendas.html.

Uso (desde la raíz del repo):  python3 i18n/build_en.py
Si cambia un texto en español y no tiene traducción, el script lo lista y falla:
añade la traducción en i18n/strings_en.py y vuelve a ejecutarlo.
Las páginas legales en inglés (en/legal-notice, en/privacy-policy, en/cookie-policy)
se mantienen a mano.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strings_en import TEXT, ATTR, JS, HELPERS  # noqa: E402

WA_ES = "text=Hola%20Nudade%2C%20me%20gustar%C3%ADa%20recibir%20informaci%C3%B3n"
WA_EN = "text=Hi%20Nudade%2C%20I%E2%80%99d%20like%20some%20information"

PAGES = [
    {
        "src": "index.html", "dst": "en/index.html", "es": "/", "en": "/en/",
        "title": "Nudade · Bare ownership in Spain: your home is still your home",
        "desc": "Nudade helps families turn their parents&rsquo; Spanish home into cash through bare ownership (nuda propiedad), with no moving and no debt. Free, no-obligation valuation.",
    },
    {
        "src": "viviendas.html", "dst": "en/homes.html", "es": "/viviendas.html", "en": "/en/homes.html",
        "title": "Homes for sale in bare ownership in Spain | Nudade",
        "desc": "Homes available in bare ownership (nuda propiedad) in Spain, with residents who keep living at home for life. Opportunities for investors with a social impact.",
    },
]

LINKS = [
    ('href="viviendas.html"', 'href="/en/homes.html"'),
    ('href="index.html#', 'href="/en/#'),
    ('href="index.html"', 'href="/en/"'),
    ('href="/aviso-legal/"', 'href="/en/legal-notice/"'),
    ('href="/politica-privacidad/"', 'href="/en/privacy-policy/"'),
    ('href="/politica-cookies/"', 'href="/en/cookie-policy/"'),
    ('src="./support.js"', 'src="/support.js"'),
    ('src="assets/', 'src="/assets/'),
    ("fetch('viviendas.json'", "fetch('/viviendas.json'"),
    ("src=\"' + f + '\"", "src=\"/' + f + '\""),
    ("src=\"' + fotos[0] + '\"", "src=\"/' + fotos[0] + '\""),
    ('name="idioma" value="es"', 'name="idioma" value="en"'),
    (WA_ES, WA_EN),
]

SPANISH_HINT = re.compile(
    r"[áéíóúñ¿¡]|\b(de|del|la|las|los|el|que|con|por|para|una|sin|tu|tus|su|sus|vivienda|viviendas|"
    r"años|nuestro|nos|te|hemos|puedes|propietario|renta|pago|solicitar|ver|más|también)\b",
    re.I,
)


ALLOW = ("Español", "Málaga", "José, 74", "Dinámico", "EUR(v.renta)", "(v.renta")


def build(p):
    src = open(os.path.join(ROOT, p["src"]), encoding="utf-8").read()
    out = src
    missing = []

    # Cabecera
    out = out.replace('<html lang="es">', '<html lang="en">', 1)
    out = re.sub(r"<title>.*?</title>", "<title>" + p["title"] + "</title>", out, count=1)
    out = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="' + p["desc"] + '">', out, count=1)
    out = out.replace('<link rel="canonical" href="https://nudade.es' + p["es"] + '">',
                      '<link rel="canonical" href="https://nudade.es' + p["en"] + '">', 1)

    # Selector de idioma
    out = re.sub(
        r'<span aria-current="true">ES</span><span aria-hidden="true" style="opacity:.3">\|</span><a href="[^"]*" hreflang="en" lang="en" title="English" style="([^"]*)">EN</a>',
        lambda m: '<a href="' + p["es"] + '" hreflang="es" lang="es" title="Español" style="' + m.group(1) + '">ES</a><span aria-hidden="true" style="opacity:.3">|</span><span aria-current="true">EN</span>',
        out)
    out = re.sub(r'<a class="ndLangMob" href="[^"]*" hreflang="en" lang="en"([^>]*)>EN</a>',
                 lambda m: '<a class="ndLangMob" href="' + p["es"] + '" hreflang="es" lang="es"' + m.group(1) + '>ES</a>', out)

    # Separar plantilla y script
    i_script = out.index('<script type="text/x-dc"')
    tpl, js = out[:i_script], out[i_script:]

    # Texto visible
    def tr_text(m):
        lead, t, trail = m.group(1), m.group(2), m.group(3)
        key = t.strip()
        if key in TEXT:
            return ">" + lead + TEXT[key] + trail + "<"
        return m.group(0)

    text_re = re.compile(r">(\s*)([^<>]*?[^\s<>][^<>]*?)(\s*)<")
    tpl = text_re.sub(tr_text, tpl)
    js = text_re.sub(tr_text, js)

    # Atributos
    def tr_attr(m):
        name, val = m.group(1), m.group(2)
        return name + '="' + ATTR.get(val, val) + '"'

    attr_re = re.compile(r'\b(alt|aria-label|placeholder|title)="([^"]*)"')
    tpl = attr_re.sub(tr_attr, tpl)
    js = attr_re.sub(tr_attr, js)

    # Script
    for a, b in JS:
        js = js.replace(a, b)
    for anchor in ("const vivCard = (v) => {", "const card = (v) => {"):
        if anchor in js:
            js = js.replace(anchor, HELPERS.strip("\n") + "\n    " + anchor + "\n      v = L(v);", 1)

    out = tpl + js
    for a, b in LINKS:
        out = out.replace(a, b)

    # Comprobación de restos en español
    body = out[out.index("<x-dc>"):]
    body_nostyle = re.sub(r"<style>.*?</style>", "", body, flags=re.S)
    for t in re.findall(r">([^<>]+)<", body_nostyle):
        t = t.strip()
        if t and SPANISH_HINT.search(t) and "{" not in t and ";" not in t:
            missing.append("TEXT  " + t)
    for v in re.findall(r'\b(?:alt|aria-label|placeholder|title)="([^"]*)"', body):
        if SPANISH_HINT.search(v) and "'" not in v:
            missing.append("ATTR  " + v)
    script = out[out.index('<script type="text/x-dc"'):]
    for lit in re.findall(r"'((?:[^'\\\n]|\\.)*)'", script):
        txt = re.sub(r"<[^>]*>", " ", lit)
        txt = re.sub(r"style=\"[^\"]*\"", "", txt)
        if re.search(r"[áéíóúñ¿¡]|\\u00[ef][0-9a-f]", txt) or re.search(r"\b(usufructuari|Ascensor|Renta|Pago|Modalidad|Tasaci|Viviendas|vivienda|Solicitud|Nombre)\b", txt):
            missing.append("JS    " + txt.strip()[:120])

    os.makedirs(os.path.dirname(os.path.join(ROOT, p["dst"])), exist_ok=True)
    open(os.path.join(ROOT, p["dst"]), "w", encoding="utf-8").write(out)
    return missing


if __name__ == "__main__":
    problems = []
    for p in PAGES:
        for m in build(p):
            problems.append(p["dst"] + "  " + m)
    problems = [x for x in problems if not any(a in x for a in ALLOW)]
    if problems:
        print("Textos sin traducir:")
        print("\n".join(sorted(set(problems))))
        sys.exit(1)
    print("OK: versión inglesa generada sin restos en español.")
