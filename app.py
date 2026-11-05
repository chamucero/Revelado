# ============================================================
# Revelado · App web (Streamlit)
# Autor: Andrés Felipe Martínez Chamucero
# ------------------------------------------------------------
# Versión en línea del organizador. Como la app corre en un
# servidor, no puede tocar las carpetas del computador: la
# persona sube sus archivos, ve la vista previa en forma de
# rollo fotográfico y descarga un ZIP ya organizado por día.
# También puede descargar el programa para su computador.
# La lógica (fechas, orden y nombres) vive en organizador_fotos.py
# ============================================================

import base64
import csv
import datetime
import html
import io
import zipfile
from pathlib import Path

import streamlit as st

from organizador_fotos import (EXT_TODAS, ZONA_LOCAL, fecha_interna,
                               planificar, tipo_archivo)

st.set_page_config(page_title="Revelado · Organizador por fecha", page_icon="🎞️",
                   layout="wide")

CARPETA_APP = Path(__file__).parent

# ---------- Estilo vintage: rollo fotográfico en amarillo y azul ----------

ESTILO = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Special+Elite&family=Courier+Prime:wght@400;700&display=swap');
:root{--amarillo:#F2B705;--amarillo-claro:#F8DE8A;--azul:#1F4E79;--azul-noche:#14213D;
--crema:#F3E9D2;--papel:#EADBB8;--pelicula:#1C1A17;--borde:#E58A2B;}
.stApp{background:var(--crema);
background-image:radial-gradient(rgba(20,33,61,.05) 1px,transparent 1px);background-size:4px 4px;}
html,body,.stApp,.stMarkdown,p,li,label,span,div{font-family:'Courier Prime','Courier New',monospace;color:var(--azul-noche);}
h1,h2,h3{font-family:'Special Elite','Courier New',monospace !important;color:var(--azul) !important;letter-spacing:.5px;}
.block-container{padding-top:1.4rem;max-width:1200px;}
header[data-testid="stHeader"]{background:transparent;}
/* --- Cabecera en forma de tira de película --- */
.tira{background:var(--pelicula);border-radius:6px;padding:34px 28px;position:relative;
box-shadow:0 8px 24px rgba(20,33,61,.25);margin-bottom:1.2rem;overflow:hidden;}
.tira:before,.tira:after{content:"";position:absolute;left:0;right:0;height:14px;
background:repeating-linear-gradient(90deg,transparent 0 10px,var(--crema) 10px 26px,transparent 26px 36px);
opacity:.92;}
.tira:before{top:9px;}.tira:after{bottom:9px;}
.tira-interior{display:flex;align-items:center;gap:26px;
border-left:6px solid var(--amarillo);padding-left:22px;}
.tira-texto{flex:1;min-width:0;}
@media (max-width:700px){.tira-interior{flex-wrap:wrap;}.lata{margin-left:0 !important;}}
.tira h1,.tira h1 *{font-size:3.6rem !important;margin:0 !important;padding:0 !important;
color:var(--amarillo) !important;line-height:1.05;text-shadow:3px 3px 0 var(--azul);}
.tira h1 a{display:none !important;}
.tira p{color:var(--crema) !important;margin:.2rem 0 0;font-size:1.05rem;}
.tira .marca{font-family:'Courier Prime',monospace;color:var(--borde) !important;font-size:.8rem;
letter-spacing:3px;text-transform:uppercase;}
.lata{margin-left:auto;background:var(--amarillo);color:var(--azul-noche);border-radius:10px;
padding:10px 16px;font-family:'Special Elite','Courier New',monospace;text-align:center;border:3px solid var(--azul);
transform:rotate(-3deg);box-shadow:4px 4px 0 var(--azul);}
.lata b{display:block;font-size:1.6rem;color:var(--azul);}
.lata span{color:var(--azul-noche) !important;font-size:.8rem;}
/* --- Pestañas --- */
button[data-baseweb="tab"]{font-family:'Special Elite',cursive !important;font-size:1.05rem;}
button[data-baseweb="tab"][aria-selected="true"]{color:var(--azul) !important;}
div[data-baseweb="tab-highlight"]{background:var(--amarillo) !important;height:4px;}
/* --- Zona para subir archivos --- */
[data-testid="stFileUploaderDropzone"]{background:var(--amarillo-claro);border:3px dashed var(--azul);
border-radius:12px;}
[data-testid="stFileUploaderDropzone"] *{color:var(--azul-noche) !important;}
/* --- Botones --- */
.stButton>button,[data-testid="stDownloadButton"] button{background:var(--azul) !important;
color:var(--amarillo) !important;border:2px solid var(--azul-noche) !important;border-radius:8px;
font-family:'Special Elite',cursive !important;font-size:1.05rem;padding:.55rem 1.3rem;
box-shadow:4px 4px 0 var(--amarillo);transition:transform .1s;}
.stButton>button *,[data-testid="stDownloadButton"] button *{color:var(--amarillo) !important;}
.stButton>button:hover,[data-testid="stDownloadButton"] button:hover{transform:translate(-1px,-1px);
box-shadow:5px 5px 0 var(--amarillo);}
/* --- Etiquetas de conteo (como latas de rollo) --- */
.conteos{display:flex;gap:12px;flex-wrap:wrap;margin:.6rem 0 1.2rem;}
.conteo{background:var(--azul);border-radius:10px;padding:10px 16px;min-width:110px;
border-bottom:5px solid var(--amarillo);}
.conteo b{display:block;font-family:'Special Elite',cursive;font-size:1.9rem;color:var(--amarillo) !important;}
.conteo span{color:var(--crema) !important;font-size:.85rem;letter-spacing:1px;text-transform:uppercase;}
.conteo.alerta{background:var(--borde);border-bottom-color:var(--azul-noche);}
.conteo.alerta b{color:var(--azul-noche) !important;}
.conteo.alerta span{color:var(--azul-noche) !important;}
/* --- Rollo de cada día --- */
.rollo{background:var(--pelicula);border-radius:6px;margin:0 0 1.3rem;padding:26px 14px 30px;
position:relative;overflow-x:auto;box-shadow:0 6px 18px rgba(20,33,61,.22);}
.rollo:before,.rollo:after{content:"";position:absolute;left:0;height:10px;
width:max(100%,var(--ancho));
background:repeating-linear-gradient(90deg,transparent 0 8px,var(--crema) 8px 20px,transparent 20px 28px);opacity:.9;}
.rollo:before{top:8px;}.rollo:after{bottom:8px;}
.rollo-titulo{font-family:'Courier Prime',monospace;color:var(--borde) !important;font-weight:700;
letter-spacing:3px;font-size:.85rem;margin:0 0 8px 4px;white-space:nowrap;}
.cuadros{display:flex;gap:14px;width:max-content;}
.cuadro{width:170px;flex:none;}
.foto{width:170px;height:114px;background:#2b2824;border:2px solid #000;display:flex;align-items:center;
justify-content:center;overflow:hidden;position:relative;}
.foto img{width:100%;height:100%;object-fit:cover;filter:sepia(.18) saturate(1.1) contrast(1.02);}
.foto .icono{font-size:2.4rem;}
.insignia{position:absolute;top:6px;left:6px;background:var(--amarillo);color:var(--azul-noche) !important;
font-size:.7rem;font-weight:700;padding:1px 6px;border-radius:3px;letter-spacing:1px;}
.nombre{color:var(--amarillo) !important;font-weight:700;font-size:.86rem;margin-top:6px;white-space:nowrap;
overflow:hidden;text-overflow:ellipsis;}
.original{color:#b9b2a4 !important;font-size:.72rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.fuente{color:var(--borde) !important;font-size:.68rem;letter-spacing:1px;text-transform:uppercase;}
.ondas{display:flex;gap:3px;align-items:center;height:60px;}
.ondas i{display:block;width:5px;background:var(--amarillo);border-radius:2px;}
/* --- Tarjeta de papel --- */
.papel{background:#FBF5E6;border:2px solid var(--azul);border-radius:10px;padding:18px 22px;
box-shadow:5px 5px 0 var(--amarillo);margin-bottom:1rem;}
.papel h3{margin-top:0 !important;}
.pie{text-align:center;color:var(--azul) !important;font-size:.85rem;margin-top:2.5rem;opacity:.85;}
</style>
"""
st.markdown(ESTILO, unsafe_allow_html=True)

st.markdown(
    '<div class="tira"><div class="tira-interior"><div class="tira-texto">'
    '<div class="marca">◀ 24 EXP · ISO 400 · ORGANIZADOR POR FECHA ▶</div>'
    '<h1>Revelado</h1>'
    '<p>Ordena tus fotos, RAW, videos y audios por fecha: <b style="color:#F2B705">20261102 (1)</b>, '
    '<b style="color:#F2B705">20261102 (2)</b>...</p></div>'
    '<div class="lata"><span>FORMATOS</span><b>17</b><span>JPG · HEIC · RAW · MOV · MP3</span></div>'
    '</div></div>', unsafe_allow_html=True)

ICONOS = {"jpg": "📷", "heic": "📱", "png": "🖼️", "raw": "🎞️", "video": "🎬", "audio": "🎙️"}
ETIQUETAS = {"jpg": "JPG", "heic": "HEIC", "png": "PNG", "raw": "RAW", "video": "VIDEO", "audio": "AUDIO"}


# ---------- Funciones de apoyo ----------

def miniatura(datos, tipo):
    """Devuelve una miniatura en base64 para fotos que el navegador puede mostrar."""
    if tipo not in ("jpg", "png", "heic", "raw"):
        return None
    try:
        from PIL import Image, ImageOps
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:
            pass
        with Image.open(io.BytesIO(datos)) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            img.thumbnail((340, 228))
            salida = io.BytesIO()
            img.save(salida, "JPEG", quality=78)
        return base64.b64encode(salida.getvalue()).decode()
    except Exception:
        return None


def analizar(archivo_subido):
    """Lee tipo, fecha y miniatura de un archivo subido (se guarda en memoria de sesión)."""
    cache = st.session_state.setdefault("analisis", {})
    clave = (archivo_subido.name, archivo_subido.size, getattr(archivo_subido, "file_id", ""))
    if clave not in cache:
        datos = archivo_subido.getvalue()
        tipo = tipo_archivo(Path(archivo_subido.name).suffix.lower())
        fecha, origen = fecha_interna(archivo_subido.name, io.BytesIO(datos))
        cache[clave] = {"nombre": archivo_subido.name, "tipo": tipo, "fecha": fecha,
                        "origen": origen, "miniatura": miniatura(datos, tipo)}
    return dict(cache[clave], archivo=archivo_subido)


def cuadro_html(e):
    """Un cuadro del rollo: imagen o ícono, nombre nuevo y nombre original."""
    if e["miniatura"]:
        contenido = f'<img src="data:image/jpeg;base64,{e["miniatura"]}">'
    elif e["tipo"] == "audio":
        alturas = [18, 34, 50, 26, 44, 58, 30, 46, 22, 38, 54, 28, 16]
        contenido = '<div class="ondas">' + "".join(f'<i style="height:{a}px"></i>' for a in alturas) + "</div>"
    else:
        contenido = f'<span class="icono">{ICONOS[e["tipo"]]}</span>'
    fuente = e["origen"] if e["origen"] else "fecha elegida"
    return ('<div class="cuadro"><div class="foto">' + contenido +
            f'<span class="insignia">{ETIQUETAS[e["tipo"]]}</span></div>'
            f'<div class="nombre">{html.escape(e["nuevo"])}</div>'
            f'<div class="original">{html.escape(e["nombre"])}</div>'
            f'<div class="fuente">{html.escape(fuente)}</div></div>')


def rollo_html(dia, elementos):
    """Una tira de película con todas las tomas de un día."""
    titulo = f"{dia[:4]}·{dia[4:6]}·{dia[6:]}" if dia != "sin_fecha" else "SIN FECHA"
    cuadros = "".join(cuadro_html(e) for e in elementos)
    ancho = len(elementos) * 184 + 40
    return (f'<div class="rollo" style="--ancho:{ancho}px"><div class="rollo-titulo">'
            f'▶ ROLLO {titulo} · {len(elementos)} TOMA{"S" if len(elementos) != 1 else ""} · '
            f'CARPETA {html.escape(dia)}</div><div class="cuadros">{cuadros}</div></div>')


def crear_zip(elementos):
    """Arma el ZIP con una carpeta por día y el registro de nombres originales."""
    memoria = io.BytesIO()
    registro = io.StringIO()
    escritor = csv.writer(registro)
    escritor.writerow(["nombre_original", "nombre_nuevo", "fuente_fecha"])
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as zip_final:
        for e in elementos:
            ruta = f'{e["dia"]}/{e["nuevo"]}'
            # Las fotos y videos ya vienen comprimidos: se guardan sin recomprimir
            zip_final.writestr(zipfile.ZipInfo(ruta, date_time=e["fecha"].timetuple()[:6]),
                               e["archivo"].getvalue(), compress_type=zipfile.ZIP_STORED)
            escritor.writerow([e["nombre"], ruta, e["origen"] or "fecha elegida"])
        zip_final.writestr("registro_organizador.csv", registro.getvalue().encode("utf-8-sig"))
    return memoria.getvalue()


# ---------- Pestañas ----------

pestana_web, pestana_pc, pestana_info = st.tabs(
    ["🎞️  Revelar en línea", "💾  Descargar para tu computador", "📖  Cómo funciona"])

with pestana_web:
    subidos = st.file_uploader(
        "Sube tus fotos, RAW, videos y audios (puedes arrastrar varios a la vez)",
        type=sorted(ext.strip(".") for ext in EXT_TODAS), accept_multiple_files=True)

    if not subidos:
        st.markdown(
            '<div class="papel"><h3>Cómo usarlo</h3>'
            '1. Sube los archivos de tu cubrimiento.<br>'
            '2. Revisa el rollo: cada día queda en su tira, primero las JPG, luego HEIC, PNG, RAW, videos y audios.<br>'
            '3. Descarga el ZIP con las carpetas por día y los nombres <b>AAAAMMDD (n)</b>.<br><br>'
            '<i>Tus archivos no se guardan: se procesan mientras la página está abierta.</i></div>',
            unsafe_allow_html=True)
    else:
        with st.spinner("Revelando el rollo..."):
            elementos = [analizar(a) for a in subidos]
        con_fecha = [e for e in elementos if e["fecha"] is not None]
        sin_fecha = [e for e in elementos if e["fecha"] is None]

        # Conteo por tipo
        cuenta = {t: sum(1 for e in elementos if e["tipo"] == t) for t in ICONOS}
        fotos = cuenta["jpg"] + cuenta["heic"] + cuenta["png"]
        tarjetas = [("Fotos", fotos), ("RAW", cuenta["raw"]), ("Videos", cuenta["video"]),
                    ("Audios", cuenta["audio"])]
        html_conteo = "".join(f'<div class="conteo"><b>{n}</b><span>{t}</span></div>' for t, n in tarjetas)
        if sin_fecha:
            html_conteo += f'<div class="conteo alerta"><b>{len(sin_fecha)}</b><span>Sin fecha</span></div>'
        st.markdown(f'<div class="conteos">{html_conteo}</div>', unsafe_allow_html=True)

        # Archivos sin fecha interna (capturas, WhatsApp, audios sin etiquetas)
        if sin_fecha:
            st.markdown(
                f'<div class="papel"><h3>⚠️ {len(sin_fecha)} archivo(s) sin fecha por dentro</h3>'
                'Las capturas de pantalla, las fotos de WhatsApp y algunos audios no guardan la fecha. '
                'Al subirlos a la web también se pierde la fecha de modificación, así que elige qué hacer:</div>',
                unsafe_allow_html=True)
            opcion = st.radio("¿Qué hago con ellos?",
                              ["Ponerles una fecha", "Dejarlos en una carpeta «sin_fecha»"], horizontal=True)
            if opcion == "Ponerles una fecha":
                dia_elegido = st.date_input("Fecha para los archivos sin fecha",
                                            value=datetime.datetime.now(ZONA_LOCAL).date(),
                                            format="DD/MM/YYYY")
                for e in sin_fecha:
                    e["fecha"] = datetime.datetime.combine(dia_elegido, datetime.time(23, 59))
                con_fecha += sin_fecha
                sin_fecha = []

        planificar(con_fecha)
        for e in sin_fecha:                          # se conservan con su nombre
            e["dia"] = "sin_fecha"
            e["nuevo"] = e["nombre"]
            e["fecha"] = datetime.datetime.now(ZONA_LOCAL).replace(tzinfo=None)

        # Un rollo por día
        dias = sorted({e["dia"] for e in con_fecha})
        st.markdown(f"### Tu rollo revelado · {len(dias)} día(s)")
        for dia in dias:
            st.markdown(rollo_html(dia, [e for e in con_fecha if e["dia"] == dia]),
                        unsafe_allow_html=True)
        if sin_fecha:
            st.markdown(rollo_html("sin_fecha", sin_fecha), unsafe_allow_html=True)

        # Descarga
        todos = con_fecha + sin_fecha
        if st.button(f"🎞️  Revelar {len(todos)} archivos en un ZIP"):
            with st.spinner("Armando el ZIP..."):
                st.session_state["zip"] = crear_zip(todos)
                st.session_state["zip_cantidad"] = len(todos)
        if st.session_state.get("zip") and st.session_state.get("zip_cantidad") == len(todos):
            st.download_button("⬇️  Descargar rollo_organizado.zip", st.session_state["zip"],
                               file_name="rollo_organizado.zip", mime="application/zip")

with pestana_pc:
    st.markdown(
        '<div class="papel"><h3>Organiza directamente tus carpetas</h3>'
        'Para cubrimientos con cientos de archivos o videos pesados, lo mejor es el programa de escritorio. '
        'Trabaja sobre tu propia carpeta, <b>sin subir nada a internet</b>: eliges la carpeta (ese es el permiso), '
        'revisas la vista previa y confirmas con <b>s</b>. Además conserva la fecha de modificación de los archivos '
        'y deja un registro con los nombres originales.</div>', unsafe_allow_html=True)
    columna1, columna2 = st.columns(2)
    with columna1:
        st.download_button("💾  Descargar organizador_fotos.py",
                           (CARPETA_APP / "organizador_fotos.py").read_bytes(),
                           file_name="organizador_fotos.py", mime="text/x-python")
    with columna2:
        st.download_button("📄  Descargar requirements.txt",
                           (CARPETA_APP / "requirements.txt").read_bytes(),
                           file_name="requirements.txt", mime="text/plain")
    st.markdown("#### Pasos")
    st.markdown("1. Instala [Python](https://www.python.org/downloads/) (marca *Add Python to PATH*).\n"
                "2. Abre una terminal en la carpeta donde descargaste los archivos y ejecuta:")
    st.code("pip install exifread pillow pillow-heif mutagen\npython organizador_fotos.py", language="bash")
    st.markdown("3. Elige la carpeta de tu cubrimiento en la ventana que se abre, revisa la vista previa "
                "y escribe **s** para organizar.")

with pestana_info:
    st.markdown(
        '<div class="papel"><h3>¿De dónde sale la fecha?</h3>'
        '<b>📷 JPG · 📱 HEIC · 🖼️ PNG · 🎞️ RAW</b> (CR2, CR3, NEF, ARW, DNG, RAF, ORF, RW2): fecha de toma que '
        'guarda la cámara (EXIF).<br>'
        '<b>🎬 MOV · MP4</b>: fecha de creación guardada dentro del video, convertida a la hora de Colombia.<br>'
        '<b>🎙️ WAV</b>: fecha de grabación de grabadoras de campo (bloque <i>bext</i>). '
        '<b>MP3</b>: fecha de las etiquetas ID3.<br>'
        '<b>Sin fecha por dentro</b>: tú eliges la fecha o se guardan en la carpeta <i>sin_fecha</i>.</div>'
        '<div class="papel"><h3>¿En qué orden quedan?</h3>'
        'Cada día es una carpeta <b>AAAAMMDD</b>. Dentro van primero las JPG, luego HEIC, PNG, RAW, videos y '
        'audios, cada grupo en el orden en que se tomó, con una sola numeración: '
        '<b>20261102 (1).jpg</b>, <b>20261102 (2).heic</b>, ... <b>20261102 (6).mov</b>.</div>',
        unsafe_allow_html=True)

st.markdown('<div class="pie">Revelado · Andrés Felipe Martínez Chamucero · '
            'Especialización en Diseño y Creación con IA · Lenguajes de Programación Multiplataforma</div>',
            unsafe_allow_html=True)
