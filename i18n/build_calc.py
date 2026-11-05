#!/usr/bin/env python3
"""Genera la página de la calculadora (/calculadora-nuda-propiedad/) a partir de index.html.

Uso (desde la raíz del repo):  python3 i18n/build_calc.py
build_en.py lo ejecuta al principio, así que basta con:  python3 i18n/build_en.py

La página reutiliza de index.html el <head>, el menú, el formulario de valoración,
el pie, los modales y todo el script, de modo que cualquier cambio de diseño en la
home se hereda. Lo propio de la página (cabecera, calculadora y "cómo se calcula")
vive en _calc/calculadora.html: edita ahí la calculadora.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "/calculadora-nuda-propiedad/"
EN_URL = "/en/bare-ownership-calculator/"
TITLE = "Calculadora de nuda propiedad gratis: cuánto vale tu casa | Nudade"
DESC = ("Calcula gratis y al instante cuánto podría recibir una persona mayor por vender la nuda propiedad "
        "de su vivienda sin dejar de vivir en ella. Pago único, renta vitalicia o mixto.")

M_HERO = "<!-- ===================== HERO ===================== -->"
M_VAL = "<!-- ===================== VALORACIÓN / FORM ===================== -->"
M_FAQ = "<!-- ===================== FAQ ===================== -->"
M_FOOT = "<!-- ===================== FOOTER ===================== -->"

# Anclas de la home que no existen en esta página
HOME_ANCHORS = ("como-funciona", "por-que", "garantias", "faq", "viviendas", "contacto", "calculadora")


def build():
    src = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    frag = open(os.path.join(ROOT, "_calc", "calculadora.html"), encoding="utf-8").read()

    head_nav = src[:src.index(M_HERO)]
    valoracion = src[src.index(M_VAL):src.index(M_FAQ)]
    tail = src[src.index(M_FOOT):]
    out = head_nav + frag + valoracion + tail

    # <head>
    out = re.sub(r"<title>.*?</title>", "<title>" + TITLE + "</title>", out, count=1)
    out = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="' + DESC + '">', out, count=1)
    out = out.replace('<link rel="canonical" href="https://nudade.es/">', '<link rel="canonical" href="https://nudade.es' + URL + '">', 1)
    out = out.replace('<link rel="alternate" hreflang="es" href="https://nudade.es/">', '<link rel="alternate" hreflang="es" href="https://nudade.es' + URL + '">', 1)
    out = out.replace('<link rel="alternate" hreflang="en" href="https://nudade.es/en/">', '<link rel="alternate" hreflang="en" href="https://nudade.es' + EN_URL + '">', 1)
    out = out.replace('<link rel="alternate" hreflang="x-default" href="https://nudade.es/">', '<link rel="alternate" hreflang="x-default" href="https://nudade.es' + URL + '">', 1)
    out = out.replace('data-screen-label="Nudade home"', 'data-screen-label="Nudade calculadora"')

    # Selector de idioma: EN apunta a la calculadora en inglés
    out = re.sub(r'(<a[^>]*?)href="/en/"([^>]*hreflang="en")', r'\1href="' + EN_URL + r'"\2', out)
    out = re.sub(r'(<a class="ndLangMob" )href="/en/"', r'\1href="' + EN_URL + '"', out)

    # Enlaces y rutas (la página vive en un subdirectorio)
    for a in HOME_ANCHORS:
        out = out.replace('href="#' + a + '" data-nav', 'href="/#' + a + '"')
        out = out.replace('href="#' + a + '"', 'href="/#' + a + '"')
    out = out.replace('href="/#calculadora"', 'href="' + URL + '"')
    out = out.replace('href="#top" data-nav class="ndBrand"', 'href="/" class="ndBrand"')
    out = out.replace('href="viviendas.html"', 'href="/viviendas.html"')
    out = out.replace('href="index.html', 'href="/')
    out = out.replace('src="./support.js"', 'src="/support.js"')
    out = out.replace('src="assets/', 'src="/assets/')
    out = out.replace("fetch('viviendas.json'", "fetch('/viviendas.json'")

    dst = os.path.join(ROOT, URL.strip("/"), "index.html")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "w", encoding="utf-8").write(out)
    print("OK: calculadora generada en " + URL)


if __name__ == "__main__":
    build()
