# ============================================================
# Revelado · Organizador de fotos, videos y audios por fecha
# Taller: Identificación y análisis de estructuras de decisión
# Autor: Andrés Felipe Martínez Chamucero
# ------------------------------------------------------------
# Versión para ejecutar en el computador. El usuario elige una
# carpeta (ese es el permiso que le da a la app) y el algoritmo:
#   1. Recorre los archivos y reconoce fotos (JPG, PNG, HEIC),
#      fotos RAW, videos (MOV, MP4) y audios (MP3, WAV).
#   2. Averigua la fecha en que se tomó o grabó cada uno.
#   3. Muestra una vista previa y pide confirmación.
#   4. Crea una carpeta por día (AAAAMMDD) y renombra cada
#      archivo como "AAAAMMDD (1).ext". Dentro de cada día van
#      primero las JPG, luego HEIC, PNG, RAW, videos y audios,
#      con una sola numeración continua.
#   5. Guarda un registro CSV con los nombres originales.
# Este mismo archivo lo usa la app web (app.py) para leer las
# fechas y calcular los nombres nuevos.
# Estructuras usadas: if / elif / else, for, while
# Librerías opcionales: exifread, Pillow, pillow-heif, mutagen
# ============================================================

import csv
import datetime
import logging
import os
import struct
import sys
from pathlib import Path

# ---------- Formatos reconocidos ----------

EXT_JPG = {".jpg", ".jpeg"}
EXT_HEIC = {".heic", ".heif"}                       # fotos de iPhone
EXT_PNG = {".png"}
EXT_RAW = {".cr2", ".cr3", ".nef", ".arw", ".dng",  # Canon, Nikon, Sony,
           ".raf", ".orf", ".rw2"}                  # Fuji, Olympus, Panasonic
EXT_VIDEO = {".mov", ".mp4"}
EXT_AUDIO = {".mp3", ".wav"}
EXT_TODAS = EXT_JPG | EXT_HEIC | EXT_PNG | EXT_RAW | EXT_VIDEO | EXT_AUDIO

ZONA_LOCAL = datetime.timezone(datetime.timedelta(hours=-5))   # hora de Colombia
logging.getLogger("exifread").setLevel(logging.CRITICAL)        # sin avisos técnicos


def tipo_archivo(extension):
    """Clasifica un archivo según su extensión (en minúsculas)."""
    if extension in EXT_JPG:
        return "jpg"
    elif extension in EXT_HEIC:
        return "heic"
    elif extension in EXT_PNG:
        return "png"
    elif extension in EXT_RAW:
        return "raw"
    elif extension in EXT_VIDEO:
        return "video"
    elif extension in EXT_AUDIO:
        return "audio"
    else:
        return None                                  # no se organiza


def prioridad(tipo):
    """Orden dentro de cada día: JPG, HEIC, PNG, RAW, videos, audios."""
    if tipo == "jpg":
        return 0
    elif tipo == "heic":
        return 1
    elif tipo == "png":
        return 2
    elif tipo == "raw":
        return 3
    elif tipo == "video":
        return 4
    else:
        return 5                                     # audio


# ---------- Lectura de fechas (funcionan con cualquier archivo abierto) ----------

def convertir_texto_fecha(texto):
    """Convierte textos como '2026:11:02 19:05:30' o '2026-11-02T19:05' en fecha."""
    texto = str(texto).strip().replace("T", " ").split(".")[0].split("+")[0]
    formatos = ["%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
                "%Y:%m:%d", "%Y-%m-%d"]
    for formato in formatos:
        try:
            fecha = datetime.datetime.strptime(texto[:19], formato)
            if fecha.year >= 1990:                   # descarta fechas vacías
                return fecha
        except ValueError:
            continue
    return None


def fecha_foto(archivo):
    """Fecha de toma (EXIF) de JPG, PNG, HEIC y RAW."""
    # Intento 1: exifread, que entiende JPG, HEIC y la mayoría de RAW
    try:
        import exifread
        archivo.seek(0)
        etiquetas = exifread.process_file(archivo, details=False,
                                          stop_tag="EXIF DateTimeOriginal")
        for clave in ("EXIF DateTimeOriginal", "Image DateTime"):
            if clave in etiquetas:
                fecha = convertir_texto_fecha(etiquetas[clave])
                if fecha:
                    return fecha
    except Exception:
        pass
    # Intento 2: Pillow (y pillow-heif para HEIC)
    try:
        from PIL import Image
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:
            pass
        archivo.seek(0)
        with Image.open(archivo) as img:
            exif = img.getexif()
            valor = exif.get_ifd(0x8769).get(36867) or exif.get(306)
        if valor:
            return convertir_texto_fecha(valor)
    except Exception:
        pass
    return None


def fecha_video(archivo):
    """Fecha de creación de MP4, MOV (y CR3), guardada en el átomo 'mvhd'."""
    try:
        archivo.seek(0, os.SEEK_END)
        fin = archivo.tell()
        pos = 0
        while pos < fin:                             # recorre los átomos
            archivo.seek(pos)
            cabecera = archivo.read(8)
            if len(cabecera) < 8:
                break
            tamano, tipo = struct.unpack(">I4s", cabecera)
            largo_cab = 8
            if tamano == 1:
                tamano = struct.unpack(">Q", archivo.read(8))[0]
                largo_cab = 16
            elif tamano == 0:
                tamano = fin - pos

            if tipo == b"moov":                      # entrar a 'moov'
                pos += largo_cab
                continue
            elif tipo == b"mvhd":                    # aquí está la fecha
                version = archivo.read(4)[0]
                if version == 1:
                    segundos = struct.unpack(">Q", archivo.read(8))[0]
                else:
                    segundos = struct.unpack(">I", archivo.read(4))[0]
                if segundos == 0:
                    return None
                # Segundos desde 1904 en UTC -> hora de Colombia (UTC-5)
                utc = (datetime.datetime(1904, 1, 1, tzinfo=datetime.timezone.utc)
                       + datetime.timedelta(seconds=segundos))
                return utc.astimezone(ZONA_LOCAL).replace(tzinfo=None)

            if tamano < largo_cab:
                break
            pos += tamano
    except (OSError, struct.error, IndexError):
        pass
    return None


def fecha_wav(archivo):
    """Fecha de grabación de un WAV (bloque 'bext' de grabadoras como Zoom o Tascam)."""
    try:
        archivo.seek(0)
        if archivo.read(4) != b"RIFF":
            return None
        archivo.seek(12)
        while True:                                  # recorre los bloques
            cabecera = archivo.read(8)
            if len(cabecera) < 8:
                break
            nombre, tamano = struct.unpack("<4sI", cabecera)
            if nombre == b"bext":
                datos = archivo.read(tamano)
                fecha = datos[320:330].decode("ascii", "ignore")   # AAAA-MM-DD
                hora = datos[330:338].decode("ascii", "ignore")    # HH:MM:SS
                for separador in (":", "_", ".", " "):     # la norma admite
                    fecha = fecha.replace(separador, "-")  # varios separadores
                for separador in ("-", "_", ".", " "):
                    hora = hora.replace(separador, ":")
                return convertir_texto_fecha(f"{fecha} {hora}")
            archivo.seek(tamano + (tamano % 2), os.SEEK_CUR)
    except (OSError, struct.error):
        pass
    return None


def fecha_mp3(archivo):
    """Fecha de grabación guardada en las etiquetas ID3 de un MP3."""
    try:
        from mutagen.id3 import ID3
        archivo.seek(0)
        etiquetas = ID3(archivo)
        for clave in ("TDRC", "TDOR", "TDRL"):
            if clave in etiquetas:
                texto = str(etiquetas[clave].text[0])
                if len(texto) >= 10:                 # solo si trae día completo
                    return convertir_texto_fecha(texto)
    except Exception:
        pass
    return None


def fecha_interna(nombre, archivo):
    """Decide de dónde leer la fecha según el tipo de archivo.

    Devuelve (fecha, origen). Si el archivo no trae la fecha por
    dentro, devuelve (None, "") y quien llama decide el respaldo.
    """
    extension = Path(nombre).suffix.lower()
    tipo = tipo_archivo(extension)
    fecha = None
    origen = ""

    if tipo in ("jpg", "heic", "png"):
        fecha = fecha_foto(archivo)
        origen = "EXIF"
    elif tipo == "raw":
        fecha = fecha_foto(archivo)
        origen = "EXIF"
        if fecha is None and extension == ".cr3":    # el CR3 es como un video
            fecha = fecha_video(archivo)
            origen = "metadatos"
    elif tipo == "video":
        fecha = fecha_video(archivo)
        origen = "metadatos"
    elif tipo == "audio":
        if extension == ".wav":
            fecha = fecha_wav(archivo)
        else:
            fecha = fecha_mp3(archivo)
        origen = "metadatos"

    if fecha is None:
        origen = ""
    return fecha, origen


# ---------- Cálculo de los nombres nuevos ----------

def planificar(elementos, existe=None):
    """Ordena y asigna el nombre nuevo a cada elemento.

    elementos: lista de diccionarios con 'nombre', 'fecha' y 'tipo'.
    existe: función opcional que dice si una ruta ya está ocupada.
    Agrega a cada elemento 'dia' (AAAAMMDD) y 'nuevo' ("AAAAMMDD (n).ext").
    """
    elementos.sort(key=lambda e: (e["fecha"].date(), prioridad(e["tipo"]), e["fecha"]))
    contador_dia = {}
    for e in elementos:
        dia = e["fecha"].strftime("%Y%m%d")
        numero = contador_dia.get(dia, 0) + 1        # la secuencia continúa
        extension = Path(e["nombre"]).suffix.lower().replace(".jpeg", ".jpg")
        nuevo = f"{dia} ({numero}){extension}"
        while existe is not None and existe(dia, nuevo):   # nunca sobrescribir
            numero += 1
            nuevo = f"{dia} ({numero}){extension}"
        contador_dia[dia] = numero
        e["dia"] = dia
        e["nuevo"] = nuevo
    return elementos


# ---------- Programa para el computador ----------

def elegir_carpeta():
    if len(sys.argv) > 1:                            # ruta escrita al ejecutar
        return Path(sys.argv[1])
    try:                                             # ventana del sistema
        import tkinter
        from tkinter import filedialog
        ventana = tkinter.Tk()
        ventana.withdraw()
        ruta = filedialog.askdirectory(title="Elige la carpeta de fotos, videos y audios")
        ventana.destroy()
        if ruta:
            return Path(ruta)
    except Exception:
        pass
    return Path(input("Escribe la ruta de la carpeta: ").strip().strip('"'))


def main():
    print("=== REVELADO · ORGANIZADOR POR FECHA ===")
    carpeta = elegir_carpeta()
    while not carpeta.is_dir():                      # validar la carpeta
        print(f"  '{carpeta}' no es una carpeta válida.")
        carpeta = Path(input("Escribe la ruta de la carpeta: ").strip().strip('"'))
    print(f"Carpeta elegida: {carpeta}\n")

    # Paso 2: recorrer, clasificar y leer la fecha
    elementos = []
    conteo = {"jpg": 0, "heic": 0, "png": 0, "raw": 0, "video": 0, "audio": 0}
    omitidos = 0
    for ruta in sorted(carpeta.iterdir()):
        if not ruta.is_file():
            continue                                 # las subcarpetas no se tocan
        tipo = tipo_archivo(ruta.suffix.lower())
        if tipo is None:
            omitidos += 1                            # .pdf, .txt, etc.
            continue
        conteo[tipo] += 1
        with open(ruta, "rb") as archivo:
            fecha, origen = fecha_interna(ruta.name, archivo)
        if fecha is None:                            # respaldo: fecha del archivo
            fecha = datetime.datetime.fromtimestamp(ruta.stat().st_mtime)
            origen = "modificación"
        elementos.append({"nombre": ruta.name, "ruta": ruta, "fecha": fecha,
                          "tipo": tipo, "origen": origen})

    fotos = conteo["jpg"] + conteo["heic"] + conteo["png"]
    print(f"Encontrados: {fotos} fotos, {conteo['raw']} RAW, {conteo['video']} videos, "
          f"{conteo['audio']} audios, {omitidos} omitidos")
    if len(elementos) == 0:
        print("No hay archivos para organizar.")
        return

    # Paso 3: calcular nombres nuevos
    planificar(elementos, existe=lambda dia, nuevo: (carpeta / dia / nuevo).exists())
    dias = sorted({e["dia"] for e in elementos})

    print("\nVista previa:")
    for e in elementos:
        print(f"  {e['nombre']:<24} -> {e['dia']}/{e['nuevo']:<18} ({e['origen']})")

    # Paso 4: confirmación
    respuesta = ""
    while respuesta not in ("s", "n"):
        respuesta = input(f"\n¿Organizar {len(elementos)} archivos en {len(dias)} "
                          f"carpetas? (s/n): ").strip().lower()
    if respuesta == "n":
        print("Operación cancelada. No se modificó ningún archivo.")
        return

    # Paso 5: mover, renombrar y registrar
    registro = carpeta / "registro_organizador.csv"
    nuevo_registro = not registro.exists()
    movidos = errores = 0
    with open(registro, "a", newline="", encoding="utf-8") as archivo_csv:
        escritor = csv.writer(archivo_csv)
        if nuevo_registro:
            escritor.writerow(["nombre_original", "nombre_nuevo", "fuente_fecha"])
        for e in elementos:
            destino = carpeta / e["dia"] / e["nuevo"]
            try:
                destino.parent.mkdir(exist_ok=True)
                e["ruta"].rename(destino)
                escritor.writerow([e["nombre"], f"{e['dia']}/{e['nuevo']}", e["origen"]])
                movidos += 1
            except OSError as error:
                print(f"  No se pudo mover {e['nombre']}: {error}")
                errores += 1

    print("\n========== RESUMEN ==========")
    print(f"Archivos organizados: {movidos}")
    print(f"Carpetas por día: {', '.join(dias)}")
    if errores > 0:
        print(f"Archivos con error: {errores}")
    print(f"Registro guardado en: {registro.name}")


if __name__ == "__main__":
    main()
