#!/usr/bin/env python3
"""Inserta en <head> las etiquetas Open Graph / Twitter y los datos estructurados
(JSON-LD) de la home y de la página de viviendas, en español e inglés.

Uso (desde la raíz del repo):  python3 i18n/seo_head.py
build_en.py lo ejecuta al final, así que basta con regenerar la versión inglesa.
El bloque va entre <!-- seo:start --> y <!-- seo:end --> y se reescribe entero
cada vez. Las preguntas frecuentes se leen del array FAQ de cada página, de modo
que si cambias una pregunta en la web el JSON-LD se actualiza solo.
"""
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://nudade.es"
OG_IMAGE = BASE + "/assets/og-nudade.jpg"
START, END = "<!-- seo:start -->", "<!-- seo:end -->"

ORG = {
    "@type": "RealEstateAgent",
    "@id": BASE + "/#org",
    "name": "Nudade",
    "url": BASE + "/",
    "logo": BASE + "/apple-touch-icon.png",
    "image": OG_IMAGE,
    "email": "info@nudade.es",
    "telephone": "+34604149420",
    "address": {
        "@type": "PostalAddress",
        "streetAddress": "Calle Mesón de Paredes, 1",
        "postalCode": "28012",
        "addressLocality": "Madrid",
        "addressCountry": "ES",
    },
    "areaServed": {"@type": "Country", "name": "España"},
    "founder": {"@type": "Person", "name": "Iván Hernández Gonzalo"},
    "sameAs": ["https://www.instagram.com/nudade.es/"],
}

PAGES = [
    {
        "file": "index.html", "lang": "es", "locale": "es_ES", "alt_locale": "en_GB",
        "url": BASE + "/", "kind": "home",
        "org_desc": "Especialistas en nuda propiedad en España. Acompañamos a las familias en la venta de la nuda propiedad de la vivienda de sus mayores, que siguen viviendo en casa de por vida gracias al usufructo vitalicio.",
        "img_alt": "Pareja de personas mayores en el sofá de su casa",
    },
    {
        "file": "en/index.html", "lang": "en", "locale": "en_GB", "alt_locale": "es_ES",
        "url": BASE + "/en/", "kind": "home",
        "org_desc": "Bare ownership (nuda propiedad) specialists in Spain. We guide families through selling the bare ownership of their elderly relatives' home, while they keep living there for life.",
        "img_alt": "Older couple on the sofa at home",
    },
    {
        "file": "viviendas.html", "lang": "es", "locale": "es_ES", "alt_locale": "en_GB",
        "url": BASE + "/viviendas.html", "kind": "listings", "home": BASE + "/",
        "crumbs": ["Inicio", "Viviendas en nuda propiedad"],
        "img_alt": "Pareja de personas mayores en el sofá de su casa",
    },
    {
        "file": "en/homes.html", "lang": "en", "locale": "en_GB", "alt_locale": "es_ES",
        "url": BASE + "/en/homes.html", "kind": "listings", "home": BASE + "/en/",
        "crumbs": ["Home", "Homes in bare ownership"],
        "img_alt": "Older couple on the sofa at home",
    },
    {
        "file": "calculadora-nuda-propiedad/index.html", "lang": "es", "locale": "es_ES", "alt_locale": "en_GB",
        "url": BASE + "/calculadora-nuda-propiedad/", "kind": "calc", "home": BASE + "/",
        "crumbs": ["Inicio", "Calculadora de nuda propiedad"],
        "app": "Calculadora de nuda propiedad",
        "img_alt": "Pareja de personas mayores en el sofá de su casa",
    },
    {
        "file": "en/bare-ownership-calculator/index.html", "lang": "en", "locale": "en_GB", "alt_locale": "es_ES",
        "url": BASE + "/en/bare-ownership-calculator/", "kind": "calc", "home": BASE + "/en/",
        "crumbs": ["Home", "Bare ownership calculator"],
        "app": "Bare ownership calculator",
        "img_alt": "Older couple on the sofa at home",
    },
]


def clean(s):
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("\\'", "'")
    return html.unescape(s).strip()


def faq_from(src):
    m = re.search(r"const FAQ = \[(.*?)\n\s*\];", src, re.S)
    if not m:
        return []
    pairs = re.findall(r"\[\s*'((?:[^'\\]|\\.)*)'\s*,\s*'((?:[^'\\]|\\.)*)'\s*\]", m.group(1))
    return [(clean(q), clean(a)) for q, a in pairs]


def meta(name, content, prop=True):
    attr = "property" if prop else "name"
    return '<meta %s="%s" content="%s">' % (attr, name, html.escape(content, quote=True))


def block(p, src):
    title = html.unescape(re.search(r"<title>(.*?)</title>", src, re.S).group(1))
    desc = html.unescape(re.search(r'<meta name="description" content="([^"]*)">', src).group(1))
    tags = [
        meta("og:type", "website"),
        meta("og:site_name", "Nudade"),
        meta("og:locale", p["locale"]),
        meta("og:locale:alternate", p["alt_locale"]),
        meta("og:url", p["url"]),
        meta("og:title", title),
        meta("og:description", desc),
        meta("og:image", OG_IMAGE),
        meta("og:image:width", "1200"),
        meta("og:image:height", "630"),
        meta("og:image:alt", p["img_alt"]),
        meta("twitter:card", "summary_large_image", prop=False),
        meta("twitter:title", title, prop=False),
        meta("twitter:description", desc, prop=False),
        meta("twitter:image", OG_IMAGE, prop=False),
    ]
    graph = []
    if p["kind"] == "home":
        org = dict(ORG, description=p["org_desc"])
        graph.append(org)
        graph.append({
            "@type": "WebSite", "@id": BASE + "/#website", "url": BASE + "/",
            "name": "Nudade", "inLanguage": ["es", "en"], "publisher": {"@id": BASE + "/#org"},
        })
        graph.append({
            "@type": "WebPage", "@id": p["url"] + "#webpage", "url": p["url"], "name": title,
            "description": desc, "inLanguage": p["lang"],
            "isPartOf": {"@id": BASE + "/#website"}, "about": {"@id": BASE + "/#org"},
        })
        faq = faq_from(src)
        if faq:
            graph.append({
                "@type": "FAQPage", "@id": p["url"] + "#faq", "inLanguage": p["lang"],
                "mainEntity": [
                    {"@type": "Question", "name": q,
                     "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq
                ],
            })
    elif p["kind"] == "calc":
        graph.append({
            "@type": "WebApplication", "@id": p["url"] + "#app", "url": p["url"], "name": p["app"],
            "description": desc, "inLanguage": p["lang"], "applicationCategory": "FinanceApplication",
            "operatingSystem": "Web", "isAccessibleForFree": True,
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"},
            "provider": {"@id": BASE + "/#org"},
        })
        graph.append({
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": p["crumbs"][0], "item": p["home"]},
                {"@type": "ListItem", "position": 2, "name": p["crumbs"][1], "item": p["url"]},
            ],
        })
    else:
        graph.append({
            "@type": "CollectionPage", "@id": p["url"] + "#webpage", "url": p["url"],
            "name": title, "description": desc, "inLanguage": p["lang"],
            "isPartOf": {"@id": BASE + "/#website"}, "provider": {"@id": BASE + "/#org"},
        })
        graph.append({
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": p["crumbs"][0], "item": p["home"]},
                {"@type": "ListItem", "position": 2, "name": p["crumbs"][1], "item": p["url"]},
            ],
        })
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=1)
    ld = ld.replace("</", "<\\/")
    return START + "\n" + "\n".join(tags) + '\n<script type="application/ld+json">\n' + ld + "\n</script>\n" + END


def run():
    for p in PAGES:
        path = os.path.join(ROOT, p["file"])
        src = open(path, encoding="utf-8").read()
        src = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", src, flags=re.S)
        b = block(p, src)
        anchor = '<meta name="theme-color"'
        i = src.index(anchor)
        j = src.index("\n", i) + 1
        src = src[:j] + b + "\n" + src[j:]
        open(path, "w", encoding="utf-8").write(src)
    print("OK: Open Graph y JSON-LD actualizados en home, viviendas y calculadora (ES/EN).")


if __name__ == "__main__":
    run()
