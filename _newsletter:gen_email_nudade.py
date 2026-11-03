#!/usr/bin/env python3
"""Genera el email semanal de inversores de Nudade a partir de viviendas.json del repo nudade-web.

Uso: python3 gen_email_nudade.py RUTA_REPO CARPETA_SALIDA AAAA-MM-DD [DIAS_ATRAS] [MAPA_FOTOS_JPG.json]
Siempre escribe fotos.json (fotos .webp de las viviendas disponibles). Si se pasa MAPA_FOTOS_JPG.json
({"ruta foto": "url jpg"}), escribe ademas doc.html: version sencilla para importar como Google Doc.
Compara el viviendas.json actual con el que había hace DIAS_ATRAS días (por defecto 7)
según el historial git, y marca viviendas nuevas y cambios de precio.
"""
import json, subprocess, sys, os, html, datetime

repo, outdir, hoy = sys.argv[1], sys.argv[2], sys.argv[3]
dias = int(sys.argv[4]) if len(sys.argv) > 4 else 7
mapa = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else None
BASE = "https://nudade.es/"
MESES = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]

def git(*a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True).stdout.strip()

actual = json.load(open(os.path.join(repo, "viviendas.json")))["viviendas"]
fecha_ref = (datetime.date.fromisoformat(hoy) - datetime.timedelta(days=dias)).isoformat()
commit_prev = git("rev-list", "-1", f"--before={fecha_ref} 23:59", "HEAD", "--", "viviendas.json")
previo = {}
if commit_prev:
    try:
        previo = {v["id"]: v for v in json.loads(git("show", f"{commit_prev}:viviendas.json"))["viviendas"]}
    except Exception:
        previo = {}

CAMPOS_PRECIO = [("pagoInicial", "Pago inicial"), ("renta", "Renta vitalicia"), ("tasacion", "Tasación")]
disp = sorted([v for v in actual if v.get("estado", "disponible") == "disponible"], key=lambda v: v.get("orden", 99))
nuevas, precio, resto = [], [], []
for v in disp:
    p = previo.get(v["id"])
    if p is None or p.get("estado", "disponible") != "disponible":
        nuevas.append((v, []))
        continue
    cambios = [(lab, p.get(k, ""), v.get(k, "")) for k, lab in CAMPOS_PRECIO if (p.get(k, "") or "") != (v.get(k, "") or "")]
    (precio if cambios else resto).append((v, cambios))

ids_act = {v["id"]: v for v in actual}
salidas = []
for pid, p in previo.items():
    if p.get("estado", "disponible") != "disponible":
        continue
    a = ids_act.get(pid)
    if a is None:
        salidas.append(f"{p['titulo']}: retirada de la web")
    elif a.get("estado", "disponible") != "disponible":
        salidas.append(f"{a['titulo']}: {a.get('estado')}")

e = html.escape
F = "font-family:'Helvetica Neue',Arial,Helvetica,sans-serif;"

def specs(v):
    partes = []
    if v.get("habitaciones"): partes.append(f"{v['habitaciones']} habitaciones")
    if v.get("superficie"): partes.append(v["superficie"])
    if v.get("altura"):
        partes.append(v["altura"] + (" con ascensor" if v.get("ascensor") else (" sin ascensor" if v.get("ascensor") is False else "")))
    partes += [x for x in v.get("extras", []) if x]
    return " · ".join(partes)

def usufructo(v):
    pr = v.get("propietarios") or []
    edades = [str(x.get("edad")) for x in pr if x.get("edad")]
    if not edades: return ""
    if len(edades) == 1:
        s = "Usufructuaria" if (pr[0].get("sexo", "").lower().startswith("m")) else "Usufructuario"
        return f"{s} de {edades[0]} años."
    return "Usufructuarios de " + " y ".join([", ".join(edades[:-1]), edades[-1]]) + " años."

def pill(txt, fondo, color):
    return (f'<span style="display:inline-block;padding:4px 10px;border-radius:999px;background-color:{fondo};'
            f'color:{color};font-size:11px;line-height:14px;font-weight:bold;letter-spacing:1px;text-transform:uppercase;">{e(txt)}</span>')

def specs_corto(v):
    partes = []
    if v.get("habitaciones"): partes.append(f"{v['habitaciones']} hab")
    if v.get("superficie"): partes.append(v["superficie"])
    if v.get("altura"): partes.append(v["altura"] + (" con ascensor" if v.get("ascensor") else ""))
    extras = [x for x in v.get("extras", []) if x]
    if extras: partes.append(extras[0])
    return " · ".join(partes)

def detalle_corto(v):
    d = []
    if v.get("tasacion"): d.append(f"Tasación {v['tasacion']}")
    pr = v.get("propietarios") or []
    ed = [str(x.get("edad")) for x in pr if x.get("edad")]
    if ed: d.append(("Usufructuario " if len(ed) == 1 else "Usufructuarios ") + " y ".join(ed) + " años")
    return " · ".join(d)

def etiqueta(tipo):
    if tipo == "nueva": return ("NUEVA", "#1F3A2E", "#FFFFFF")
    if tipo == "precio": return ("NUEVO PRECIO", "#F3E3DF", "#8A3B2E")
    return None

def tarjeta(v, tipo, cambios):
    img = ""
    if v.get("foto"):
        img = (f'<a href="{BASE}viviendas" target="_blank"><img src="{BASE}{e(v["foto"])}" width="170" alt="{e(v["titulo"])}" '
               f'style="display:block;width:170px;height:auto;border:0;border-radius:6px;"></a>')
        if v["foto"] in (v.get("renders") or []):
            img += '<span style="font-size:10px;line-height:14px;color:#8A949C;">Imagen: propuesta de reforma</span>'
    et = etiqueta(tipo)
    tag = (f'<span style="display:inline-block;padding:2px 7px;border-radius:999px;background-color:{et[1]};color:{et[2]};'
           f'font-size:10px;line-height:13px;font-weight:bold;letter-spacing:.5px;">{et[0]}</span><br>') if et else ""
    linea = f'<strong>{e(v.get("pagoInicial") or "a consultar")}</strong>'
    if v.get("renta"): linea += f' + {e(v["renta"])}'
    cam = "".join(f'<br><span style="color:#8A3B2E;font-size:12px;">{e(l)}: antes {e(a or "sin dato")}</span>' for l, a, _ in cambios)
    det = detalle_corto(v)
    texto = (f'{tag}<a href="{BASE}viviendas" target="_blank" style="font-size:15px;line-height:20px;font-weight:bold;color:#1F3A2E;text-decoration:none;">{e(v["titulo"])}</a>'
             f'<br><span style="font-size:12px;line-height:18px;color:#5A6B7D;">{e(specs_corto(v))}</span>'
             f'<br><span style="font-size:14px;line-height:21px;color:#1A1A1A;">Inversión inicial: {linea}</span>{cam}'
             + (f'<br><span style="font-size:12px;line-height:18px;color:#5A6B7D;">{e(det)}</span>' if det else ""))
    return (f'<tr><td style="padding:18px 36px 0 36px;{F}"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
            f'<td width="170" valign="top" style="width:170px;padding:0 14px 0 0;">{img}</td>'
            f'<td valign="top" style="{F}line-height:18px;">{texto}</td></tr></table></td></tr>')

def seccion(titulo):
    return (f'<tr><td style="padding:34px 36px 0 36px;{F}"><p style="margin:0;padding-bottom:8px;border-bottom:1px solid #ECE7DD;'
            f'font-size:12px;line-height:16px;letter-spacing:1.5px;text-transform:uppercase;font-weight:bold;color:#5A6B7D;">{e(titulo)}</p></td></tr>')

n = len(disp)
d = datetime.date.fromisoformat(hoy)
fecha_txt = f"{d.day} de {MESES[d.month-1]}"
if len(nuevas) == 1:
    asunto = f"Nueva oportunidad de inversión en Nudade: {nuevas[0][0]['titulo']}"
elif len(nuevas) > 1:
    asunto = f"{len(nuevas)} nuevas oportunidades de inversión en nuda propiedad · Nudade"
elif precio:
    asunto = f"Oportunidades de inversión con precio actualizado · Nudade"
else:
    asunto = f"{n} oportunidades de inversión disponibles esta semana · Nudade"

if nuevas or precio:
    partes = []
    if nuevas: partes.append(f"{len(nuevas)} {'nueva' if len(nuevas)==1 else 'nuevas'}")
    if precio: partes.append(f"{len(precio)} con precio actualizado")
    intro_cambio = f"Esta semana hay novedades: {' y '.join(partes)}. "
else:
    intro_cambio = "Esta semana no hay altas nuevas, pero estas oportunidades siguen disponibles. "
titular = (f"{n} oportunidades de inversión en nuda propiedad" if n != 1 else "1 oportunidad de inversión en nuda propiedad")

cuerpo = []
if nuevas:
    cuerpo.append(seccion("Nuevas esta semana")); cuerpo += [tarjeta(v, "nueva", c) for v, c in nuevas]
if precio:
    cuerpo.append(seccion("Precio actualizado")); cuerpo += [tarjeta(v, "precio", c) for v, c in precio]
if resto:
    cuerpo.append(seccion("Siguen disponibles" if (nuevas or precio) else "Disponibles hoy")); cuerpo += [tarjeta(v, "resto", c) for v, c in resto]

email = f'''<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#F5F2EC;">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;background-color:#FFFFFF;border-radius:12px;">
<tr><td style="padding:28px 36px 0 36px;{F}"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
<td style="font-size:20px;line-height:24px;font-weight:bold;letter-spacing:5px;color:#1F3A2E;">NUDADE</td>
<td align="right" style="font-size:12px;line-height:16px;color:#5A6B7D;">Inversores · {e(fecha_txt)}</td></tr></table></td></tr>
<tr><td style="padding:26px 36px 0 36px;{F}">
<p style="margin:0 0 10px 0;font-size:12px;line-height:16px;letter-spacing:1.5px;text-transform:uppercase;font-weight:bold;color:#5A6B7D;">Oportunidades de inversión</p>
<p style="margin:0 0 18px 0;font-size:26px;line-height:32px;font-weight:bold;color:#1F3A2E;">{e(titular)}</p>
<p style="margin:0 0 12px 0;font-size:15px;line-height:23px;color:#1A1A1A;">Hola,</p>
<p style="margin:0 0 12px 0;font-size:15px;line-height:23px;color:#1A1A1A;">{e(intro_cambio)}Te comparto las viviendas disponibles para inversión en Nudade. Son operaciones reales, con propietarios que quieren seguir viviendo en su casa y convertir parte de su valor en liquidez.</p>
<p style="margin:0;font-size:15px;line-height:23px;color:#1A1A1A;">El inversor compra la nuda propiedad muy por debajo del valor de mercado y, al extinguirse el usufructo, recibe la plena propiedad libre de cargas.</p>
</td></tr>
{chr(10).join(cuerpo)}
<tr><td align="center" style="padding:34px 36px 0 36px;{F}"><table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
<td align="center" bgcolor="#1F3A2E" style="border-radius:999px;"><a href="{BASE}viviendas" target="_blank" style="display:inline-block;padding:14px 30px;font-size:15px;line-height:20px;font-weight:bold;color:#F5F2EC;text-decoration:none;border-radius:999px;">Ver todas las inversiones en nudade.es</a></td>
</tr></table></td></tr>
<tr><td style="padding:30px 36px 30px 36px;{F}">
<p style="margin:0 0 14px 0;font-size:15px;line-height:23px;color:#1A1A1A;">Si alguna inversión encaja con lo que buscas, lo vemos en una llamada de 20 minutos y te paso la documentación completa.</p>
<p style="margin:0 0 2px 0;font-size:15px;line-height:22px;color:#1A1A1A;">Un abrazo,</p>
<p style="margin:0;font-size:15px;line-height:22px;font-weight:bold;color:#1F3A2E;">Iván Hernández Gonzalo</p>
<p style="margin:0;font-size:13px;line-height:20px;color:#5A6B7D;">Fundador · Nudade · 605 23 98 09 · info@nudade.es</p>
</td></tr>
<tr><td style="background-color:#1F3A2E;border-radius:0 0 12px 12px;padding:24px 36px;{F}">
<p style="margin:0 0 4px 0;font-size:16px;line-height:20px;font-weight:bold;letter-spacing:5px;color:#F5F2EC;">NUDADE</p>
<p style="margin:0 0 14px 0;font-size:13px;line-height:19px;color:#F5F2EC;">Tu casa sigue siendo tu casa, ahora también es liquidez. Especialistas en nuda propiedad en España.</p>
<p style="margin:0 0 14px 0;font-size:13px;line-height:19px;"><a href="{BASE}" target="_blank" style="color:#F5F2EC;text-decoration:underline;">nudade.es</a><span style="color:#8FA398;"> · </span><a href="{BASE}viviendas" target="_blank" style="color:#F5F2EC;text-decoration:underline;">Viviendas</a><span style="color:#8FA398;"> · </span><a href="https://wa.me/34605239809" target="_blank" style="color:#F5F2EC;text-decoration:underline;">WhatsApp</a></p>
<p style="margin:0 0 10px 0;font-size:11px;line-height:16px;color:#B9C6BE;">Información orientativa y no vinculante, según la ficha publicada de cada vivienda. Las condiciones pueden variar hasta la firma ante notario. Este email no constituye asesoramiento de inversión.</p>
<p style="margin:0;font-size:11px;line-height:16px;color:#B9C6BE;">Recibes este email porque has mostrado interés en invertir con Nudade. Si no quieres recibir más comunicaciones, responde con la palabra BAJA. <a href="{BASE}politica-privacidad/" target="_blank" style="color:#B9C6BE;text-decoration:underline;">Política de privacidad</a>.</p>
</td></tr>
</table></td></tr></table>'''

pagina = f'''<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Email inversores Nudade {hoy}</title>
<style>
body{{margin:0;background:#ECE7DD;font-family:"Helvetica Neue",Arial,Helvetica,sans-serif;color:#1A1A1A}}
.bar{{position:sticky;top:0;z-index:5;background:#1F3A2E;color:#F5F2EC;padding:14px 16px}}
.bar-in{{max-width:640px;margin:0 auto;display:flex;flex-wrap:wrap;gap:10px;align-items:center}}
.bar b{{font-size:14px;margin-right:auto}}
.bar button{{font:inherit;font-size:14px;font-weight:bold;cursor:pointer;border:0;border-radius:999px;padding:10px 18px;background:#F5F2EC;color:#1F3A2E}}
.ok{{font-size:13px;color:#D9E4DC;width:100%}}
.steps{{max-width:640px;margin:16px auto 0;padding:0 16px;font-size:14px;line-height:21px;color:#3D4A44}}
.steps ol{{margin:6px 0 0 18px;padding:0}} .wrap{{padding:16px}}
</style></head><body>
<div class="bar"><div class="bar-in"><b>Email inversores · {e(fecha_txt)}</b>
<button id="btnAsunto" type="button">1 · Copiar asunto</button><button id="btnEmail" type="button">2 · Copiar email</button>
<div class="ok" id="ok" aria-live="polite">Asunto: {e(asunto)}</div></div></div>
<div class="steps"><strong>Cómo enviarlo desde Gmail</strong><ol>
<li>Abre Gmail y pulsa <em>Redactar</em>. Pon el email del inversor en <em>Para</em>.</li>
<li>Pulsa <em>1 · Copiar asunto</em> y pégalo en el asunto con Cmd+V.</li>
<li>Pulsa <em>2 · Copiar email</em> y pégalo en el cuerpo del mensaje con Cmd+V.</li>
<li>Cambia «Hola,» por «Hola, [nombre]», envíatelo antes a ti para revisarlo y luego envíalo.</li></ol></div>
<div class="wrap"><div id="email">
{email}
</div></div>
<script>
var ASUNTO = {json.dumps(asunto, ensure_ascii=False)};
var ok = document.getElementById('ok');
function cp(fn){{ var h=false; try{{ h=fn(); }}catch(x){{}} return h; }}
document.getElementById('btnAsunto').addEventListener('click', function(){{
  var t=document.createElement('textarea'); t.value=ASUNTO; document.body.appendChild(t); t.select();
  var h=cp(function(){{return document.execCommand('copy');}}); document.body.removeChild(t);
  ok.textContent = h ? 'Asunto copiado: '+ASUNTO : 'No se pudo copiar. Asunto: '+ASUNTO; }});
document.getElementById('btnEmail').addEventListener('click', function(){{
  var s=window.getSelection(); s.removeAllRanges(); var r=document.createRange(); r.selectNode(document.getElementById('email')); s.addRange(r);
  var h=cp(function(){{return document.execCommand('copy');}}); s.removeAllRanges();
  ok.textContent = h ? 'Email copiado. Pégalo en el cuerpo del mensaje de Gmail con Cmd+V.' : 'No se pudo copiar. Selecciona el email con el ratón y copia con Cmd+C.'; }});
</script></body></html>'''

# WhatsApp
wa = [f"Hola [nombre], ¿qué tal?", ""]
if nuevas or precio:
    wa.append(f"Te paso las *oportunidades de inversión* de esta semana en Nudade. {intro_cambio.strip()}")
else:
    wa.append(f"Te paso las *{n} oportunidades de inversión* que siguen disponibles en Nudade.")
wa.append("")
for grupo, marca in ((nuevas, "🆕 "), (precio, "💶 "), (resto, "🏡 ")):
    for v, c in grupo:
        wa.append(f"{marca}*{v['titulo']}*")
        sp = specs(v)
        if sp: wa.append(sp)
        l = f"Inversión inicial: *{v.get('pagoInicial') or 'a consultar'}*"
        if v.get("renta"): l += f" + {v['renta']} de renta vitalicia"
        wa.append(l)
        for lab, antes, ahora in c:
            wa.append(f"{lab}: antes {antes or 'sin dato'}, ahora {ahora or 'sin dato'}")
        wa.append("")
wa += ["Fotos y fichas completas aquí 👇", f"{BASE}viviendas", "",
       "Si alguna inversión encaja con lo que buscas, lo vemos en una llamada de 20 minutos y te paso toda la documentación.", "",
       "Un abrazo,", "Iván · Nudade"]

os.makedirs(outdir, exist_ok=True)
nombre = f"Email inversores Nudade {hoy}.html"
open(os.path.join(outdir, nombre), "w").write(pagina)
open(os.path.join(outdir, f"WhatsApp inversores Nudade {hoy}.txt"), "w").write("\n".join(wa))
resumen = {"asunto": asunto, "disponibles": n, "commit_referencia": commit_prev or None,
           "nuevas": [v["titulo"] for v, _ in nuevas],
           "precio_actualizado": [{"titulo": v["titulo"], "cambios": [f"{l}: {a or 'sin dato'} -> {b or 'sin dato'}" for l, a, b in c]} for v, c in precio],
           "salen": salidas, "html": nombre}
json.dump(resumen, open(os.path.join(outdir, "resumen.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(resumen, ensure_ascii=False, indent=1))

json.dump([v["foto"] for v in disp if v.get("foto")], open(os.path.join(outdir, "fotos.json"), "w"), ensure_ascii=False)

# Version Google Doc (para copiar y pegar en Gmail desde Drive)
if mapa is not None:
    A = "font-family:Arial,Helvetica,sans-serif;"
    def P(txt, estilo): return f'<p style="{A}margin:0 0 8px 0;{estilo}">{txt}</p>'
    d_html = [P("N U D A D E", "font-size:20px;font-weight:bold;color:#1F3A2E;"),
              P(e(f"Inversores · {fecha_txt}"), "font-size:11px;color:#5A6B7D;"), "<br>",
              P("OPORTUNIDADES DE INVERSIÓN", "font-size:11px;font-weight:bold;color:#5A6B7D;"),
              P(e(titular), "font-size:22px;font-weight:bold;color:#1F3A2E;"),
              P("Hola,", "font-size:12px;color:#1A1A1A;"),
              P(e(intro_cambio) + "Te comparto las viviendas disponibles para inversión en Nudade. Son operaciones reales, con propietarios que quieren seguir viviendo en su casa y convertir parte de su valor en liquidez.", "font-size:12px;color:#1A1A1A;"),
              P("El inversor compra la nuda propiedad muy por debajo del valor de mercado y, al extinguirse el usufructo, recibe la plena propiedad libre de cargas.", "font-size:12px;color:#1A1A1A;")]
    def bloque(v, tipo, cambios):
        url = mapa.get(v.get("foto", ""))
        img = f'<a href="{BASE}viviendas"><img src="{e(url)}" width="160" alt="{e(v["titulo"])}"></a>' if url else ""
        if url and v["foto"] in (v.get("renders") or []):
            img += f'<br><span style="{A}font-size:8px;color:#8A949C;">Imagen: propuesta de reforma</span>'
        et = etiqueta(tipo)
        S = lambda t, est: f'<span style="{A}{est}">{t}</span>'
        partes = []
        if et: partes.append(S(et[0], f"font-size:9px;font-weight:bold;color:{et[2]};background-color:{et[1]};"))
        partes.append(f'<a href="{BASE}viviendas" style="{A}font-size:13px;font-weight:bold;color:#1F3A2E;text-decoration:none;">{e(v["titulo"])}</a>')
        partes.append(S(e(specs_corto(v)), "font-size:10px;color:#5A6B7D;"))
        l = f'Inversión inicial: <b>{e(v.get("pagoInicial") or "a consultar")}</b>'
        if v.get("renta"): l += f' + {e(v["renta"])}'
        partes.append(S(l, "font-size:11px;color:#1A1A1A;"))
        for lab, antes, _ in cambios: partes.append(S(e(f"{lab}: antes {antes or 'sin dato'}"), "font-size:10px;color:#8A3B2E;"))
        det = detalle_corto(v)
        if det: partes.append(S(e(det), "font-size:10px;color:#5A6B7D;"))
        celda = "<br>".join(partes)
        return ('<table border="0" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%;"><tr>'
                f'<td style="width:170px;vertical-align:top;border:1px solid #FFFFFF;">{img}</td>'
                f'<td style="vertical-align:top;border:1px solid #FFFFFF;"><p style="{A}margin:0;line-height:1.4;">{celda}</p></td></tr></table>')
    for titulo_s, grupo, tipo in ((("Nuevas esta semana"), nuevas, "nueva"), ("Precio actualizado", precio, "precio"),
                                  ("Siguen disponibles" if (nuevas or precio) else "Disponibles hoy", resto, "resto")):
        if grupo:
            d_html.append("<br>" + P(e(titulo_s.upper()), "font-size:11px;font-weight:bold;color:#5A6B7D;"))
            d_html += [bloque(v, tipo, c) for v, c in grupo]
    d_html += ["<br>", P(f'<a href="{BASE}viviendas" style="color:#1F3A2E;font-weight:bold;">Ver todas las inversiones en nudade.es</a>', "font-size:13px;"), "<br>",
               P("Si alguna inversión encaja con lo que buscas, lo vemos en una llamada de 20 minutos y te paso la documentación completa.", "font-size:12px;color:#1A1A1A;"),
               P("Un abrazo,", "font-size:12px;color:#1A1A1A;"),
               P("Iván Hernández Gonzalo", "font-size:12px;font-weight:bold;color:#1F3A2E;"),
               P("Fundador · Nudade · 605 23 98 09 · info@nudade.es", "font-size:10px;color:#5A6B7D;"), "<br>",
               '<table border="0" cellpadding="16" cellspacing="0" style="border-collapse:collapse;width:100%;"><tr>'
               '<td style="background-color:#1F3A2E;border:1px solid #1F3A2E;">'
               + P("N U D A D E", "font-size:14px;font-weight:bold;color:#F5F2EC;")
               + P("Tu casa sigue siendo tu casa, ahora también es liquidez. Especialistas en nuda propiedad en España.", "font-size:11px;color:#F5F2EC;")
               + P(f'<a href="{BASE}" style="color:#F5F2EC;">nudade.es</a> · <a href="{BASE}viviendas" style="color:#F5F2EC;">Viviendas</a> · <a href="https://wa.me/34605239809" style="color:#F5F2EC;">WhatsApp</a>', "font-size:11px;color:#F5F2EC;")
               + P("Información orientativa y no vinculante, según la ficha publicada de cada vivienda. Las condiciones pueden variar hasta la firma ante notario. Este email no constituye asesoramiento de inversión.", "font-size:8px;color:#B9C6BE;")
               + P(f'Recibes este email porque has mostrado interés en invertir con Nudade. Si no quieres recibir más comunicaciones, responde con la palabra BAJA. <a href="{BASE}politica-privacidad/" style="color:#B9C6BE;">Política de privacidad</a>.', "font-size:8px;color:#B9C6BE;")
               + "</td></tr></table>"]
    open(os.path.join(outdir, "doc.html"), "w").write('<html><head><meta charset="utf-8"></head><body>' + "".join(d_html) + "</body></html>")
