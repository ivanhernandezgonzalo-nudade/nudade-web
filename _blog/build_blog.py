#!/usr/bin/env python3
"""Genera el blog estático de nudade.es a partir de _blog/posts/*.md

Uso (desde la raíz del repo):  python3 _blog/build_blog.py [--hasta AAAA-MM-DD]

- Solo publica los artículos cuya fecha sea igual o anterior a hoy (hora de Madrid).
  Los artículos con fecha futura quedan en cola y salen solos en la ejecución de esa semana.
- Genera /blog/index.html, /blog/<slug>/index.html, /blog/feed.xml,
  actualiza sitemap.xml y regenera /llms.txt (GEO).
- Falla si encuentra guiones largos o medios en los textos (estilo de marca).
"""
import datetime as dt
import html
import json
import os
import re
import sys
from zoneinfo import ZoneInfo

import markdown
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "_blog", "posts")
OUT = os.path.join(ROOT, "blog")
SITE = "https://nudade.es"
WA = "https://wa.me/34605239809?text=Hola%20Nudade%2C%20me%20gustar%C3%ADa%20recibir%20informaci%C3%B3n"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
PROHIBIDOS = ["—", "–"]  # guion largo y guion medio

LOGO = ('<svg viewBox="0 0 100 120" fill="none" stroke="{c}" stroke-width="7.5" stroke-linecap="round" '
        'stroke-linejoin="round" style="height:{h}px;width:auto" aria-hidden="true"><path d="M9 116 L9 52 A41 41 0 0 1 91 52 L91 116"/>'
        '<path d="M35 116 L35 65 A15 15 0 0 1 65 65 L65 116"/></svg>')
WA_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true" style="width:17px;height:17px;flex-shrink:0"><path fill="#25D366" d="M17.47 14.38c-.3-.15-1.75-.86-2.02-.96-.27-.1-.47-.15-.67.15-.2.3-.77.96-.94 1.16-.17.2-.35.22-.65.07-.3-.15-1.25-.46-2.38-1.47-.88-.79-1.47-1.76-1.65-2.06-.17-.3-.02-.46.13-.61.14-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.02-.52-.08-.15-.67-1.62-.92-2.22-.24-.58-.49-.5-.67-.51h-.57c-.2 0-.52.07-.8.37-.27.3-1.04 1.02-1.04 2.48 0 1.46 1.07 2.88 1.22 3.08.15.2 2.1 3.2 5.08 4.49.71.31 1.27.49 1.7.63.71.23 1.36.2 1.88.12.57-.09 1.75-.72 2-1.41.25-.7.25-1.29.17-1.41-.07-.13-.27-.2-.57-.35M12.04 21.8h-.01a9.8 9.8 0 0 1-4.99-1.37l-.36-.21-3.71.97.99-3.62-.23-.37a9.78 9.78 0 0 1-1.5-5.22c0-5.42 4.41-9.83 9.84-9.83 2.62 0 5.09 1.02 6.94 2.88a9.77 9.77 0 0 1 2.88 6.96c0 5.42-4.41 9.83-9.84 9.83m8.37-18.2A11.76 11.76 0 0 0 12.04.13C5.5.13.17 5.46.17 12a11.8 11.8 0 0 0 1.58 5.93L.07 24l6.22-1.63a11.84 11.84 0 0 0 5.66 1.44h.01c6.54 0 11.87-5.33 11.87-11.87 0-3.17-1.23-6.15-3.47-8.39"/></svg>')


def esc(s):
    return html.escape(s, quote=True)


def fecha_larga(d):
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def leer_post(path):
    raw = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    if not m:
        sys.exit(f"Front matter no encontrado en {path}")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    body = m.group(2).strip()
    for ch in PROHIBIDOS:
        if ch in raw:
            sys.exit(f"{os.path.basename(path)} contiene un guion largo o medio. Sustitúyelo por coma, punto o dos puntos.")
    for k in ("titulo", "seo_titulo", "descripcion", "slug", "fecha", "imagen", "imagen_alt", "resumen"):
        if not meta.get(k):
            sys.exit(f"Falta '{k}' en {path}")
    meta["fecha_d"] = dt.date.fromisoformat(meta["fecha"])
    meta["actualizado_d"] = dt.date.fromisoformat(meta.get("actualizado") or meta["fecha"])
    meta["body"] = body
    meta["palabras"] = len(re.findall(r"\w+", body))
    meta["lectura"] = max(3, round(meta["palabras"] / 200))
    meta["categoria"] = meta.get("categoria", "Nuda propiedad")
    return meta


def dims(src):
    p = os.path.join(ROOT, src.lstrip("/"))
    if not os.path.exists(p):
        sys.exit(f"No existe la imagen {src}")
    with Image.open(p) as im:
        return im.size


def render_body(md_text):
    # Separa las preguntas frecuentes para el schema FAQPage
    faqs = []
    m = re.search(r"^## Preguntas frecuentes\s*$(.*)", md_text, re.M | re.S)
    if m:
        for q, a in re.findall(r"^### (.+?)\n(.*?)(?=^### |\Z)", m.group(1), re.M | re.S):
            faqs.append((q.strip(), " ".join(a.split())))
    md = markdown.Markdown(extensions=["tables", "toc", "sane_lists"],
                           extension_configs={"toc": {"slugify": lambda v, s: re.sub(r"[^a-z0-9]+", "-", strip_accents(v.lower())).strip("-")}})
    out = md.convert(md_text)
    toc = [(t["id"], t["name"]) for t in md.toc_tokens]

    def img(mm):
        tag = mm.group(1)
        alt = re.search(r'alt="([^"]*)"', tag).group(1)
        src = re.search(r'src="([^"]*)"', tag).group(1)
        w, h = dims(src)
        return (f'<figure class="bImg"><img src="{src}" alt="{alt}" width="{w}" height="{h}" loading="lazy" decoding="async">'
                f'<figcaption>{alt}</figcaption></figure>')

    out = re.sub(r"<p>(<img [^>]*>)</p>", img, out)
    out = out.replace("<table>", '<div class="bTableWrap"><table>').replace("</table>", "</table></div>")
    out = re.sub(r'<a href="(https?://(?!nudade\.es)[^"]+)"', r'<a href="\1" target="_blank" rel="noopener"', out)
    return out, toc, faqs


def strip_accents(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def nav(active_blog=True):
    item = lambda href, txt, act=False: (f'<li><a href="{href}"{" class=\"on\" aria-current=\"page\"" if act else ""}>{txt}</a></li>')
    return f"""<nav id="ndNav" aria-label="Principal">
  <div class="nWrap">
    <a href="/" class="nBrand" aria-label="Nudade, ir al inicio">{LOGO.format(c="#1F3A2E", h=30)}<span id="ndWord">NUDADE</span></a>
    <ul id="ndLinks">
      {item("/#como-funciona", "Cómo funciona")}
      {item("/#por-que", "Por qué Nudade")}
      {item("/viviendas.html", "Viviendas")}
      {item("/#garantias", "Garantías")}
      {item("/#calculadora", "Calcular")}
      {item("/#faq", "Preguntas")}
      {item("/blog/", "Blog", active_blog)}
      <li><a href="{WA}" target="_blank" rel="noopener" class="nWa" aria-label="Escríbenos por WhatsApp">{WA_ICON}<span class="nWaLong">Escríbenos por </span>WhatsApp</a></li>
      <li class="nLang"><span aria-current="true">ES</span><span aria-hidden="true" style="opacity:.3">|</span><a href="/en/" hreflang="en" lang="en" title="English">EN</a></li>
    </ul>
    <a class="nWaMob" href="{WA}" target="_blank" rel="noopener" aria-label="Escríbenos por WhatsApp">{WA_ICON}WhatsApp</a>
    <button id="ndToggle" aria-label="Abrir menú" aria-expanded="false" aria-controls="ndLinks"><span></span><span></span><span></span></button>
  </div>
</nav>"""


def footer():
    return f"""<footer class="bFoot">
  <div class="fWrap">
    <div class="fTop">
      <div style="max-width:320px">
        <div class="fBrand">{LOGO.format(c="#F5F2EC", h=30)}<span>NUDADE</span></div>
        <p>Tu casa sigue siendo tu casa, ahora también es liquidez. Nuda propiedad en España.</p>
      </div>
      <div class="fCols">
        <div><p class="fH">Nudade</p><ul><li><a href="/#como-funciona">Cómo funciona</a></li><li><a href="/#calculadora">Calcular</a></li><li><a href="/viviendas.html">Viviendas</a></li><li><a href="/blog/">Blog</a></li></ul></div>
        <div><p class="fH">Contacto</p><ul><li><a href="{WA}" target="_blank" rel="noopener" class="fWa">{WA_ICON}WhatsApp</a></li><li><a href="mailto:info@nudade.es">info@nudade.es</a></li></ul></div>
        <div><p class="fH">Legal</p><ul><li><a href="/aviso-legal/">Aviso legal</a></li><li><a href="/politica-privacidad/">Política de privacidad</a></li><li><a href="/politica-cookies/">Política de cookies</a></li></ul></div>
      </div>
    </div>
    <div class="fBot"><p>© {dt.date.today().year} Nudade. Todos los derechos reservados.</p><p>nudade.es · nudade.com</p></div>
  </div>
</footer>
<script>
(function(){{var t=document.getElementById('ndToggle'),l=document.getElementById('ndLinks');if(!t)return;
t.addEventListener('click',function(){{var o=l.classList.toggle('open');t.setAttribute('aria-expanded',o?'true':'false');}});
l.addEventListener('click',function(e){{if(e.target.closest('a'))l.classList.remove('open');}});}})();
</script>"""


def head(title, desc, canonical, og_img, extra_jsonld, og_type="website", published=None, modified=None):
    ld = "\n".join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in extra_jsonld)
    art = ""
    if published:
        art = (f'<meta property="article:published_time" content="{published}">\n'
               f'<meta property="article:modified_time" content="{modified}">\n')
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="robots" content="index, follow, max-image-preview:large">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="es" href="{canonical}">
<link rel="alternate" type="application/rss+xml" title="Blog de Nudade" href="{SITE}/blog/feed.xml">
<meta property="og:locale" content="es_ES">
<meta property="og:site_name" content="Nudade">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{SITE}{og_img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
{art}<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/favicon-32.png" type="image/png" sizes="32x32">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#1F3A2E">
<link rel="stylesheet" href="/blog/blog.css">
{ld}
</head>
<body>
"""


ORG = {"@type": "Organization", "@id": f"{SITE}/#organization", "name": "Nudade", "url": f"{SITE}/",
       "logo": {"@type": "ImageObject", "url": f"{SITE}/apple-touch-icon.png"}, "email": "info@nudade.es",
       "areaServed": "ES",
       "description": "Nudade acompaña a las familias en la venta de la nuda propiedad de la vivienda de sus mayores, para que sigan viviendo en casa de por vida y tengan liquidez hoy."}


def og_for(p):
    og = p["imagen"].rsplit(".", 1)[0] + "-og.jpg"
    return og if os.path.exists(os.path.join(ROOT, og.lstrip("/"))) else p["imagen"]


def card(p, h="h2"):
    w, hh = dims(p["imagen"])
    return f"""<article class="bCard">
  <a href="/blog/{p['slug']}/" class="bCardImg"><img src="{p['imagen']}" alt="{esc(p['imagen_alt'])}" width="{w}" height="{hh}" loading="lazy" decoding="async"></a>
  <div class="bCardBody">
    <p class="bMeta"><span class="bCat">{esc(p['categoria'])}</span> · <time datetime="{p['fecha']}">{fecha_larga(p['fecha_d'])}</time> · {p['lectura']} min</p>
    <{h} class="bCardTitle"><a href="/blog/{p['slug']}/">{esc(p['titulo'])}</a></{h}>
    <p class="bCardDesc">{esc(p['descripcion'])}</p>
    <a href="/blog/{p['slug']}/" class="bMore" aria-label="Leer: {esc(p['titulo'])}">Leer artículo ›</a>
  </div>
</article>"""


def cta():
    return f"""<aside class="bCta" aria-label="Habla con Nudade">
  <svg viewBox="0 0 300 300" fill="none" stroke="#F5F2EC" stroke-width="2" class="bCtaArc" aria-hidden="true"><path d="M40 290 L40 150 A110 110 0 0 1 260 150 L260 290"/><path d="M100 290 L100 175 A50 50 0 0 1 200 175 L200 290"/></svg>
  <div>
    <p class="bEyebrow light">Hablamos con calma</p>
    <p class="bCtaTitle">¿Lo estáis pensando en familia?</p>
    <p class="bCtaText">Te explicamos cómo funcionaría en vuestro caso, sin compromiso y sin prisas. Primero una cifra orientativa, luego las dudas que tengáis.</p>
  </div>
  <div class="bCtaBtns">
    <a href="/#calculadora" class="bBtn light">Calcular el valor gratis</a>
    <a href="{WA}" target="_blank" rel="noopener" class="bBtn ghost">{WA_ICON}Escríbenos por WhatsApp</a>
  </div>
</aside>"""


def build_post(p, todos):
    body_html, toc, faqs = render_body(p["body"])
    url = f"{SITE}/blog/{p['slug']}/"
    w, h = dims(p["imagen"])
    jsonld = [
        {"@context": "https://schema.org", "@type": "BlogPosting", "@id": url + "#article",
         "headline": p["titulo"], "description": p["descripcion"], "inLanguage": "es-ES",
         "image": [SITE + p["imagen"], SITE + og_for(p)],
         "datePublished": p["fecha"], "dateModified": p["actualizado_d"].isoformat(),
         "author": {"@type": "Organization", "name": "Equipo Nudade", "url": f"{SITE}/"},
         "publisher": ORG, "mainEntityOfPage": url, "articleSection": p["categoria"],
         "keywords": p.get("keyword", ""), "wordCount": p["palabras"],
         "abstract": p["resumen"]},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Inicio", "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": f"{SITE}/blog/"},
            {"@type": "ListItem", "position": 3, "name": p["titulo"], "item": url}]},
    ]
    if faqs:
        jsonld.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]})

    toc_html = "".join(f'<li><a href="#{i}">{esc(n)}</a></li>' for i, n in toc)
    rel = [x for x in todos if x["slug"] != p["slug"]][:3]
    rel_html = ""
    if rel:
        rel_html = ('<section class="bRel" aria-labelledby="sigue-leyendo"><div class="bWrap"><h2 id="sigue-leyendo" class="bRelTitle">Sigue leyendo</h2>'
                    '<div class="bGrid">' + "".join(card(x, "h3") for x in rel) + "</div></div></section>")

    page = head(p["seo_titulo"], p["descripcion"], url, og_for(p), jsonld, "article",
                p["fecha"], p["actualizado_d"].isoformat())
    page += nav() + f"""
<main id="contenido">
<article class="bArticle">
  <header class="bHero">
    <svg viewBox="0 0 600 600" fill="none" stroke="#1F3A2E" stroke-width="1.2" class="bHeroArc" aria-hidden="true"><path d="M60 580 L60 300 A240 240 0 0 1 540 300 L540 580"/><path d="M180 580 L180 330 A120 120 0 0 1 420 330 L420 580"/></svg>
    <div class="bNarrow">
      <nav class="bCrumbs" aria-label="Migas de pan"><a href="/">Inicio</a><span aria-hidden="true">›</span><a href="/blog/">Blog</a><span aria-hidden="true">›</span><span>{esc(p['categoria'])}</span></nav>
      <h1>{esc(p['titulo'])}</h1>
      <p class="bMeta"><span class="bCat">{esc(p['categoria'])}</span> · Equipo Nudade · <time datetime="{p['fecha']}">{fecha_larga(p['fecha_d'])}</time> · {p['lectura']} min de lectura</p>
    </div>
  </header>
  <figure class="bCover bNarrowWide"><img src="{p['imagen']}" alt="{esc(p['imagen_alt'])}" width="{w}" height="{h}" fetchpriority="high" decoding="async"></figure>
  <div class="bNarrow">
    <section class="bTldr" aria-label="En pocas palabras">
      <p class="bEyebrow">En pocas palabras</p>
      <p>{esc(p['resumen'])}</p>
    </section>
    {"<nav class='bToc' aria-label='Índice del artículo'><p class='bEyebrow'>En este artículo</p><ol>" + toc_html + "</ol></nav>" if len(toc) > 2 else ""}
    <div class="bBody">
{body_html}
    </div>
    <p class="bNote">Este artículo es informativo y no sustituye el asesoramiento legal o fiscal de un profesional para un caso concreto. Última revisión: <time datetime="{p['actualizado_d'].isoformat()}">{fecha_larga(p['actualizado_d'])}</time>.</p>
    {cta()}
  </div>
</article>
{rel_html}
</main>
""" + footer() + "\n</body>\n</html>\n"
    d = os.path.join(OUT, p["slug"])
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(page)


def build_index(posts):
    url = f"{SITE}/blog/"
    jsonld = [{"@context": "https://schema.org", "@type": "Blog", "@id": url, "name": "Blog de Nudade",
               "description": "Guías claras sobre nuda propiedad para familias: cómo funciona, impuestos, gastos y consejos para vender o comprar.",
               "inLanguage": "es-ES", "publisher": ORG,
               "blogPost": [{"@type": "BlogPosting", "headline": p["titulo"], "url": f"{url}{p['slug']}/",
                             "datePublished": p["fecha"]} for p in posts]}]
    og = og_for(posts[0]) if posts else "/apple-touch-icon.png"
    page = head("Blog de nuda propiedad para familias | Nudade",
                "Guías claras sobre nuda propiedad: qué es, cómo funciona, quién paga qué, impuestos, ventajas y desventajas, y consejos para vender o comprar. Escrito para las familias.",
                url, og, jsonld)
    destacado = card(posts[0]).replace('class="bCard"', 'class="bCard feat"', 1) if posts else ""
    resto = "".join(card(p) for p in posts[1:])
    page += nav() + f"""
<main id="contenido">
  <header class="bHero">
    <svg viewBox="0 0 600 600" fill="none" stroke="#1F3A2E" stroke-width="1.2" class="bHeroArc" aria-hidden="true"><path d="M60 580 L60 300 A240 240 0 0 1 540 300 L540 580"/><path d="M180 580 L180 330 A120 120 0 0 1 420 330 L420 580"/></svg>
    <div class="bWrap">
      <a href="/" class="bBack"><span aria-hidden="true">‹</span> Volver al inicio</a>
      <p class="bEyebrow">Blog de Nudade</p>
      <h1>Nuda propiedad, explicada para las familias</h1>
      <p class="bLead">Guías claras para entender la nuda propiedad, hablarlo en casa y decidir con tranquilidad. Sin letra pequeña y sin tecnicismos innecesarios. Un artículo nuevo cada semana.</p>
    </div>
  </header>
  <section class="bList">
    <div class="bWrap">
      {destacado}
      {"<div class='bGrid'>" + resto + "</div>" if resto else ""}
      <div style="margin-top:clamp(40px,6vw,70px)">{cta()}</div>
    </div>
  </section>
</main>
""" + footer() + "\n</body>\n</html>\n"
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page)


def build_feed(posts):
    items = "".join(f"""
  <item><title>{esc(p['titulo'])}</title><link>{SITE}/blog/{p['slug']}/</link><guid>{SITE}/blog/{p['slug']}/</guid>
  <pubDate>{dt.datetime.combine(p['fecha_d'], dt.time(9, 0), ZoneInfo('Europe/Madrid')).strftime('%a, %d %b %Y %H:%M:%S %z')}</pubDate>
  <description>{esc(p['descripcion'])}</description></item>""" for p in posts)
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>Blog de Nudade</title><link>{SITE}/blog/</link><language>es-es</language>
  <description>Guías claras sobre nuda propiedad para familias.</description>{items}
</channel></rss>
"""
    open(os.path.join(OUT, "feed.xml"), "w", encoding="utf-8").write(xml)


def update_sitemap(posts):
    path = os.path.join(ROOT, "sitemap.xml")
    sm = open(path, encoding="utf-8").read()
    sm = re.sub(r"\s*<url><loc>https://nudade\.es/blog/[^<]*</loc>.*?</url>", "", sm)
    last = posts[0]["actualizado_d"].isoformat() if posts else dt.date.today().isoformat()
    entries = [f'  <url><loc>{SITE}/blog/</loc><lastmod>{last}</lastmod><priority>0.7</priority></url>']
    for p in posts:
        entries.append(f'  <url><loc>{SITE}/blog/{p["slug"]}/</loc><lastmod>{p["actualizado_d"].isoformat()}</lastmod><priority>0.6</priority></url>')
    sm = sm.replace("</urlset>", "\n".join(entries) + "\n</urlset>")
    sm = re.sub(r"\n\s*\n", "\n", sm)
    open(path, "w", encoding="utf-8").write(sm)


def build_llms(posts):
    lines = [
        "# Nudade",
        "",
        "> Nudade (nudade.es) acompaña a las familias en España en la venta de la nuda propiedad de la vivienda de sus mayores: la persona mayor cobra hoy un capital, sigue viviendo en su casa de por vida gracias al usufructo vitalicio y no asume ninguna deuda. Nos dirigimos sobre todo a los hijos y familiares que ayudan a decidir.",
        "",
        "Datos clave:",
        "- Servicio: intermediación en compraventa de nuda propiedad con reserva de usufructo vitalicio en toda España.",
        "- Público: personas mayores propietarias de su vivienda y sus familias, y también inversores particulares con horizonte largo.",
        "- Valoración orientativa gratuita y sin compromiso en https://nudade.es/#calculadora",
        "- Contacto: info@nudade.es",
        "",
        "## Páginas principales",
        f"- [Inicio]({SITE}/): qué es Nudade, cómo funciona y preguntas frecuentes",
        f"- [Viviendas en nuda propiedad]({SITE}/viviendas.html): oportunidades disponibles para inversores",
        f"- [Blog]({SITE}/blog/): guías sobre nuda propiedad para familias",
        "",
        "## Artículos del blog",
    ]
    for p in posts:
        lines.append(f"- [{p['titulo']}]({SITE}/blog/{p['slug']}/): {p['resumen']}")
    lines += ["", "## English", f"- [Nudade in English]({SITE}/en/): bare ownership (nuda propiedad) in Spain explained for families abroad", ""]
    open(os.path.join(ROOT, "llms.txt"), "w", encoding="utf-8").write("\n".join(lines))


def main():
    hasta = dt.datetime.now(ZoneInfo("Europe/Madrid")).date()
    if "--hasta" in sys.argv:
        hasta = dt.date.fromisoformat(sys.argv[sys.argv.index("--hasta") + 1])
    todos = [leer_post(os.path.join(SRC, f)) for f in sorted(os.listdir(SRC)) if f.endswith(".md")]
    slugs = [p["slug"] for p in todos]
    if len(slugs) != len(set(slugs)):
        sys.exit("Hay slugs repetidos")
    pub = sorted([p for p in todos if p["fecha_d"] <= hasta], key=lambda p: p["fecha_d"], reverse=True)
    cola = [p for p in todos if p["fecha_d"] > hasta]
    os.makedirs(OUT, exist_ok=True)
    # Borra páginas de artículos que ya no deban estar publicadas
    for d in os.listdir(OUT):
        full = os.path.join(OUT, d)
        if os.path.isdir(full) and d not in [p["slug"] for p in pub]:
            import shutil
            shutil.rmtree(full)
    for p in pub:
        build_post(p, pub)
    build_index(pub)
    build_feed(pub)
    update_sitemap(pub)
    build_llms(pub)
    print(f"Publicados: {len(pub)} · En cola: {len(cola)}")
    for p in pub:
        print(f"  [publicado] {p['fecha']}  /blog/{p['slug']}/")
    for p in sorted(cola, key=lambda p: p["fecha_d"]):
        print(f"  [en cola]   {p['fecha']}  {p['slug']}")


if __name__ == "__main__":
    main()
