import streamlit as st
import streamlit.components.v1 as components
import requests, pymupdf, warnings, re, os, base64, io, shutil
import pandas as pd

try:
    import cv2
    import numpy as np
    CV2_DISPONIBLE = True
except ImportError:
    cv2 = None
    np = None
    CV2_DISPONIBLE = False

from io import BytesIO
from urllib3.exceptions import InsecureRequestWarning


# ==========================================================
# OCR PARA OFICIOS ESCANEADOS
# ==========================================================

try:
    import pytesseract
    from PIL import Image
    OCR_DISPONIBLE = True
except ImportError:
    pytesseract = None
    Image = None
    OCR_DISPONIBLE = False

OCR_LANG = "spa"
OCR_PSM = 11


# ==========================================================
# CONFIGURACIÓN AUTOMÁTICA DE TESSERACT
# ==========================================================

if OCR_DISPONIBLE:

    RUTAS_TESSERACT = [
        os.environ.get("TESSERACT_CMD"),
        shutil.which("tesseract"),
        "/opt/homebrew/bin/tesseract",
        "/usr/local/bin/tesseract",
        "/usr/bin/tesseract",
    ]

    for _ruta_tesseract in RUTAS_TESSERACT:

        if _ruta_tesseract and os.path.exists(_ruta_tesseract):

            pytesseract.pytesseract.tesseract_cmd = _ruta_tesseract
            break


# ==========================================================
# CONFIGURACIÓN GENERAL
# ==========================================================

warnings.simplefilter("ignore", InsecureRequestWarning)

PDF_DIR = "PDF_UAdeC"
IMG_DIR = "Resultados_UAdeC"

os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)


st.set_page_config(
    page_title="STUAC INFORMA - Buscador UAdeC",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ==========================================================
# ESTILOS RESPONSIVOS PARA USO COMO APLICACIÓN MÓVIL
# ==========================================================

st.markdown(
    """
    <style>
    .block-container {
        width: 100%;
        max-width: 1100px;
        padding-left: clamp(.65rem, 3vw, 1.5rem);
        padding-right: clamp(.65rem, 3vw, 1.5rem);
        padding-top: .8rem;
        padding-bottom: 2rem;
    }
    .stButton > button, .stDownloadButton > button {
        width: 100%;
        min-height: 2.9rem;
        border-radius: 12px;
        white-space: normal;
        overflow-wrap: anywhere;
    }
    [data-testid="stExpander"] details summary {
        min-height: 2.8rem;
    }
    @media (max-width: 768px) {
        .block-container {
            padding-left: .55rem;
            padding-right: .55rem;
            padding-top: .4rem;
        }
        h1 { font-size: 1.55rem !important; line-height: 1.2; }
        h2 { font-size: 1.25rem !important; }
        h3 { font-size: 1.1rem !important; }
        [data-testid="stDataFrame"], [data-testid="stTable"] {
            max-width: 100%;
            overflow-x: auto;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ==========================================================
# CONFIGURACIÓN DE ZOOM PARA CELULAR
# ==========================================================

components.html(
    """
    <script>
    try {
        const d = window.parent.document;

        let v = d.querySelector('meta[name="viewport"]');

        if (!v) {
            v = d.createElement('meta');
            v.name = 'viewport';
            d.head.appendChild(v);
        }

        v.setAttribute(
            'content',
            'width=device-width,' +
            'initial-scale=1.0,' +
            'minimum-scale=0.5,' +
            'maximum-scale=5.0,' +
            'user-scalable=yes'
        );

    } catch(e) {}
    </script>
    """,
    height=0
)


# ==========================================================
# FONDO Y ESTILO
# ==========================================================

if os.path.exists("STUAC_INFORMA.png"):

    with open("STUAC_INFORMA.png", "rb") as f:
        bg = base64.b64encode(f.read()).decode()

    st.markdown(
        f"""
        <style>

        .stApp {{
            background-image:
                linear-gradient(
                    rgba(255,255,255,.84),
                    rgba(255,255,255,.84)
                ),
                url("data:image/png;base64,{bg}");

            background-size: cover;
            background-position: center top;
            background-attachment: fixed;
        }}

        .block-container {{
            max-width: 1100px;
            padding-top: 1rem;
            padding-bottom: 3rem;
        }}

        h1 {{
            text-align: center;
            font-weight: 800;
        }}

        .stButton > button {{
            width: 100%;
            border-radius: 12px;
            min-height: 3.2em;
            font-weight: 700;
        }}

        [data-testid="stMetric"] {{
            background: rgba(255,255,255,.9);
            padding: 12px;
            border-radius: 12px;
        }}

        @media(max-width:768px) {{

            .block-container {{
                padding: .5rem .7rem 3rem;
            }}

            h1 {{
                font-size: 27px;
            }}

        }}

        </style>
        """,
        unsafe_allow_html=True
    )


# ==========================================================
# ENCABEZADO
# ==========================================================

st.title("🏛️ STUAC INFORMA")

st.markdown(
    """
    <div style="
        text-align:center;
        font-size:30px;
        font-weight:600;
        margin-bottom:20px">
        Buscador STUAC-UAdeC
    </div>
    """,
    unsafe_allow_html=True
)


# ==========================================================
# DOCUMENTOS UADEC
# ==========================================================

PDFS = {

    "Escuelas US":
        "https://www2.uadec.mx/transparencia/sassit/docs/Escuelas_US.pdf",

    "Escuelas UT":
        "https://www2.uadec.mx/transparencia/sassit/docs/Escuelas_UT.pdf",

    "Escuelas UN":
        "https://www2.uadec.mx/transparencia/sassit/docs/Escuelas_UN.pdf",

    "Hospital Saltillo":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_HOSPITAL_SALTILLO.pdf",

    "Hospital Torreón":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_HOSPITAL_TORREON.pdf",

    "Hospital Infantil":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_HOSPITAL_INFANTIL.pdf",

    "Rectoría":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_RECTORIA.pdf",

    "Tesorería":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_TESORERIA.pdf",

    "Secretaría General":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_SECRETARIA_GENERAL.pdf",

    "Oficialía Mayor":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_OFICIALIA_MAYOR.pdf",

    "Planeación":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_PLANEACION.pdf",

    "Posgrado":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_POSGRADO.pdf",

    "Adquisiciones":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_ADQUISICIONES.pdf",

    "Agenda Ambiental":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_AGENDA_AMBIENTAL.pdf",

    "Asuntos Académicos":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_ASUNTOS_ACADEMICOS.pdf",

    "CEII":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_CEII.pdf",

    "CIB":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_CIB.pdf",

    "CICBEC":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_CICBEC.pdf",

    "CIGA":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_CIGA.pdf",

    "CIICYT":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_CIICYT.pdf",

    "CIJE":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_CIJE.pdf",

    "CIMA":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_CIMA.pdf",

    "CISE":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_CISE.pdf",

    "Comunicación Institucional":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_COMUNICACION_INSTITUCIONAL.pdf",

    "Contraloría":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_CONTRALORIA.pdf",

    "Coordinación General Jurídica":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_COORDINACION_GENERAL_JURIDICA.pdf",

    "CUN":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_CUN.pdf",

    "CUS":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_CUS.pdf",

    "CUT":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_CUT.pdf",

    "Defensoría de los Derechos Humanos":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_DEFENSORIA_DE_LOS_DERECHOS_HUMANOS.pdf",

    "Deportes":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_DEPORTES.pdf",

    "Difusión y Patrimonio Cultural":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_DIFUSION_Y_PATRIMONIO_CULTURAL.pdf",

    "Educación a Distancia":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_EDUCACION_A_DISTANCIA.pdf",

    "Equidad de Género":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_EQUIDAD_DE_GENERO.pdf",

    "Extensión Universitaria":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_EXTENSION_UNIVERSITARIA.pdf",

    "IIDIMU":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_IIDIMU.pdf",

    "Informática":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_INFORMATICA.pdf",

    "Relaciones Internacionales":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_RELACIONES_INTERNACIONALES.pdf",

    "Tribunal Universitario":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_TRIBUNAL_UNIVERSITARIO.pdf",

    "Vinculación":
        "https://www2.uadec.mx/transparencia/sassit/docs/ORGANIGRAMA_VINCULACION.pdf"
}


# ==========================================================
# FUNCIONES
# ==========================================================

def safe(s):
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(s))


@st.cache_data(show_spinner=False, ttl=86400)
def download_pdf(name, url):

    path = os.path.join(
        PDF_DIR,
        safe(name) + ".pdf"
    )

    if not os.path.exists(path):

        r = requests.get(
            url,
            verify=False,
            timeout=120,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        r.raise_for_status()

        if not r.content.startswith(b"%PDF"):
            raise ValueError(
                "El servidor no devolvió un PDF válido."
            )

        open(path, "wb").write(r.content)

    return path


def dependencia(text):

    patrones = [

        r"DEPENDENCIA\s*[:\-]?\s*([^\n]+)",

        r"DEPENDENCIA\s+([^\n]+)"
    ]

    for patron in patrones:

        m = re.search(
            patron,
            text,
            re.I
        )

        if m:
            return m.group(1).strip()

    return "No identificada"


def search_quads(page, term):

    qs = []

    variantes = dict.fromkeys([
        term,
        term.upper(),
        term.lower(),
        term.title()
    ])

    for v in variantes:

        try:

            for q in page.search_for(
                v,
                quads=True
            ):

                if not any(
                    abs(x.rect.x0 - q.rect.x0) < 1
                    and
                    abs(x.rect.y0 - q.rect.y0) < 1
                    for x in qs
                ):

                    qs.append(q)

        except Exception:
            pass

    return qs


def save_marked(
    page,
    term,
    pdfname,
    pageno
):

    for q in search_quads(page, term):

        try:

            a = page.add_highlight_annot(q)

            a.set_colors(
                stroke=(1, 1, 0)
            )

            a.update()

        except Exception:
            pass

    path = os.path.join(
        IMG_DIR,
        f"{safe(pdfname)}_pagina_{pageno+1}_{safe(term)}.png"
    )

    page.get_pixmap(
        matrix=pymupdf.Matrix(2, 2),
        alpha=False
    ).save(path)

    return path


def _texto_lineas_con_bbox(page):
    """Devuelve las líneas de texto de la página junto con su posición."""
    lineas = []

    try:
        data = page.get_text("dict") or {}

        for block in data.get("blocks", []):
            if block.get("type") != 0:
                continue

            for line in block.get("lines", []):
                spans = line.get("spans", [])
                texto = "".join(
                    str(span.get("text", ""))
                    for span in spans
                ).strip()

                if not texto:
                    continue

                cajas = [
                    span.get("bbox")
                    for span in spans
                    if span.get("bbox")
                ]

                if not cajas:
                    continue

                x0 = min(c[0] for c in cajas)
                y0 = min(c[1] for c in cajas)
                x1 = max(c[2] for c in cajas)
                y1 = max(c[3] for c in cajas)

                lineas.append({
                    "texto": texto,
                    "rect": pymupdf.Rect(x0, y0, x1, y1)
                })

    except Exception:
        pass

    return lineas


def _rectangulo_cuadro(page, punto):
    """
    Busca el rectángulo que contiene el punto de una palabra VACANTE.

    En los organigramas de UAdeC, cada puesto aparece dentro de un cuadro.
    El nombre de la categoría está en la parte superior de ese mismo cuadro.
    """
    candidatos = []

    try:
        for drawing in page.get_drawings():
            rect = drawing.get("rect")

            if not rect:
                continue

            rect = pymupdf.Rect(rect)

            if rect.width < 80 or rect.height < 35:
                continue

            if rect.contains(punto):
                candidatos.append(rect)

    except Exception:
        pass

    if not candidatos:
        return None

    # Si hay varios rectángulos que contienen el punto,
    # se toma el cuadro más pequeño que lo contiene.
    return min(
        candidatos,
        key=lambda r: r.width * r.height
    )


def _categoria_desde_cuadro(page, rect_vacante):
    """
    Obtiene la primera línea de texto del cuadro que contiene VACANTE.
    Esa primera línea es la categoría, por ejemplo:
        Cocinero
        Enfermera General
    """
    if rect_vacante is None:
        return "NO IDENTIFICADA"

    lineas = _texto_lineas_con_bbox(page)

    dentro = []

    for linea in lineas:
        r = linea["rect"]

        # La línea debe estar dentro del cuadro. Se deja un pequeño margen
        # para evitar tomar texto de otro cuadro.
        if (
            r.x0 >= rect_vacante.x0 - 2
            and r.x1 <= rect_vacante.x1 + 2
            and r.y0 >= rect_vacante.y0 - 2
            and r.y1 <= rect_vacante.y1 + 2
        ):
            texto = re.sub(r"\s+", " ", linea["texto"]).strip()

            if not texto:
                continue

            # No tomar la palabra VACANTE como categoría.
            if re.search(r"\bVACANTE\b", texto, re.I):
                continue

            dentro.append(linea)

    if dentro:
        # El encabezado de la categoría es el texto más alto del cuadro.
        dentro.sort(
            key=lambda x: (x["rect"].y0, x["rect"].x0)
        )

        categoria = dentro[0]["texto"]
        categoria = re.sub(r"\s+", " ", categoria).strip(" .:-")

        # Evitar devolver un renglón que claramente sea un número de
        # expediente o una causa entre paréntesis.
        if (
            categoria
            and not re.fullmatch(r"[\d\s]+", categoria)
            and not categoria.startswith("(")
        ):
            return categoria

    return "NO IDENTIFICADA"


def extraer_categoria_vacante(page, rect_vacante=None, texto=None):
    """
    Obtiene la CATEGORÍA de una VACANTE a partir de la estructura
    gráfica del organigrama.

    REGLA DEL REPORTE:
    CATEGORÍA = el texto que aparece en la parte superior del mismo
    cuadro que contiene la palabra VACANTE.

    Ejemplos:
        VACANTE (Por permiso 72438)
            -> Cocinero

        VACANTE (Por pensión de 10648)
            -> Enfermera General

    No se utilizan palabras genéricas como DOCENTE, ADMINISTRATIVO,
    etc. y tampoco se toma una categoría de otra parte de la página.
    """

    if rect_vacante is None:
        return "NO IDENTIFICADA"

    # 1. Encontrar el cuadro que contiene físicamente la VACANTE.
    rect_cuadro = _rectangulo_cuadro(
        page,
        pymupdf.Point(
            (rect_vacante.x0 + rect_vacante.x1) / 2,
            (rect_vacante.y0 + rect_vacante.y1) / 2
        )
    )

    if rect_cuadro is None:
        return "NO IDENTIFICADA"

    # 2. Obtener las líneas de texto que están dentro de ese mismo cuadro.
    lineas = _texto_lineas_con_bbox(page)
    dentro = []

    for linea in lineas:
        r = linea["rect"]

        if not (
            r.x0 >= rect_cuadro.x0 - 2
            and r.x1 <= rect_cuadro.x1 + 2
            and r.y0 >= rect_cuadro.y0 - 2
            and r.y1 <= rect_cuadro.y1 + 2
        ):
            continue

        texto_linea = re.sub(r"\s+", " ", linea["texto"]).strip()

        if not texto_linea:
            continue

        # La categoría nunca es la propia palabra VACANTE.
        if re.search(r"\bVACANTE\b", texto_linea, re.I):
            continue

        # Ignorar líneas que solamente sean números.
        if re.fullmatch(r"[\d\s]+", texto_linea):
            continue

        # Ignorar causas que estén solas entre paréntesis.
        if texto_linea.startswith("("):
            continue

        dentro.append({
            "texto": texto_linea,
            "rect": r
        })

    if not dentro:
        return "NO IDENTIFICADA"

    # 3. La categoría es el texto más alto dentro del cuadro.
    dentro.sort(
        key=lambda x: (x["rect"].y0, x["rect"].x0)
    )

    categoria = re.sub(
        r"\s+",
        " ",
        dentro[0]["texto"]
    ).strip(" .:-")

    return categoria if categoria else "NO IDENTIFICADA"



def _imagen_a_color_amarillo(imagen):
    """Devuelve una máscara de los resaltados amarillos de VACANTE."""
    if not CV2_DISPONIBLE:
        return None

    hsv = cv2.cvtColor(imagen, cv2.COLOR_BGR2HSV)
    inferior = np.array([18, 70, 70], dtype=np.uint8)
    superior = np.array([45, 255, 255], dtype=np.uint8)
    mascara = cv2.inRange(hsv, inferior, superior)

    # Elimina ruido muy pequeño sin borrar los resaltados.
    kernel = np.ones((3, 3), np.uint8)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, kernel)
    return mascara


def _cuadros_organigrama_desde_imagen(imagen):
    """
    Detecta los cuadros rectangulares del organigrama directamente en la imagen.
    Se buscan rectángulos grandes formados por las líneas negras del cuadro.
    """
    if not CV2_DISPONIBLE:
        return []

    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    gris = cv2.GaussianBlur(gris, (3, 3), 0)
    bordes = cv2.Canny(gris, 50, 150, apertureSize=3)

    # Unimos pequeños cortes de las líneas de los cuadros.
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    bordes = cv2.morphologyEx(bordes, cv2.MORPH_CLOSE, kernel)

    contornos, _ = cv2.findContours(
        bordes,
        cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE
    )

    h_img, w_img = imagen.shape[:2]
    cuadros = []

    for contorno in contornos:
        x, y, w, h = cv2.boundingRect(contorno)

        # Los cuadros de organigrama no deben ser diminutos ni ocupar toda la página.
        if w < max(160, int(w_img * 0.10)):
            continue
        if h < max(120, int(h_img * 0.12)):
            continue
        if w > int(w_img * 0.95) or h > int(h_img * 0.90):
            continue

        proporcion = w / float(h)
        if proporcion < 0.35 or proporcion > 4.5:
            continue

        perimetro = cv2.arcLength(contorno, True)
        if perimetro <= 0:
            continue

        aprox = cv2.approxPolyDP(
            contorno,
            0.02 * perimetro,
            True
        )

        if len(aprox) != 4:
            continue

        area_contorno = cv2.contourArea(contorno)
        area_rect = float(w * h)

        # Un rectángulo de cuadro debe estar razonablemente lleno.
        if area_contorno < area_rect * 0.45:
            continue

        cuadros.append((x, y, w, h))

    # Quitar duplicados o cuadros casi idénticos.
    unicos = []
    for cuadro in sorted(cuadros, key=lambda q: q[2] * q[3]):
        x, y, w, h = cuadro
        repetido = False

        for ux, uy, uw, uh in unicos:
            if (
                abs(x - ux) <= 8
                and abs(y - uy) <= 8
                and abs(w - uw) <= 12
                and abs(h - uh) <= 12
            ):
                repetido = True
                break

        if not repetido:
            unicos.append(cuadro)

    return unicos


def _texto_categoria_desde_imagen(imagen, cuadro):
    """
    OCR del cuadro. La categoría es la primera línea de texto del cuadro,
    que en los organigramas UAdeC corresponde al encabezado en negritas.
    """
    if not OCR_DISPONIBLE or not CV2_DISPONIBLE:
        return "NO IDENTIFICADA"

    x, y, w, h = cuadro
    margen = 5

    # Solo necesitamos la parte superior del cuadro.
    alto = min(85, h - 2 * margen)
    if alto <= 0:
        return "NO IDENTIFICADA"

    recorte = imagen[
        y + margen:y + margen + alto,
        x + margen:x + w - margen
    ]

    if recorte.size == 0:
        return "NO IDENTIFICADA"

    # Se amplía el recorte para mejorar la lectura de letras pequeñas.
    recorte = cv2.resize(
        recorte,
        None,
        fx=2.5,
        fy=2.5,
        interpolation=cv2.INTER_CUBIC
    )

    # Dos variantes: color original y escala de grises.
    candidatos = []

    for imagen_ocr in (recorte, cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)):
        try:
            datos = pytesseract.image_to_data(
                imagen_ocr,
                lang=OCR_LANG,
                config="--psm 6",
                output_type=pytesseract.Output.DICT
            )
        except Exception:
            continue

        lineas = {}

        for i, texto in enumerate(datos.get("text", [])):
            texto = str(texto).strip()
            if not texto:
                continue

            try:
                conf = float(datos["conf"][i])
            except Exception:
                conf = 0

            if conf < 15:
                continue

            clave = (
                datos["block_num"][i],
                datos["par_num"][i],
                datos["line_num"][i]
            )

            lineas.setdefault(clave, []).append({
                "texto": texto,
                "x": int(datos["left"][i]),
                "y": int(datos["top"][i])
            })

        for palabras in lineas.values():
            palabras.sort(key=lambda z: z["x"])
            texto_linea = " ".join(
                p["texto"] for p in palabras
            )
            texto_linea = re.sub(r"\s+", " ", texto_linea).strip()
            if texto_linea:
                candidatos.append((min(p["y"] for p in palabras), texto_linea))

    if not candidatos:
        return "NO IDENTIFICADA"

    # La primera línea NO numérica es el encabezado/categoría.
    # Esto evita que un OCR imperfecto descarte la categoría y tome
    # el primer expediente como encabezado.
    candidatos.sort(key=lambda z: z[0])

    candidatos_texto = []
    for y_linea, texto_linea in candidatos:
        texto_linea = re.sub(r"\s+", " ", texto_linea).strip(" .:-")

        if not texto_linea:
            continue
        if re.search(r"\bVACANTE\b", texto_linea, re.I):
            continue
        if re.fullmatch(r"[\d\s.-]+", texto_linea):
            continue
        if re.match(r"^\d{3,}\b", texto_linea):
            continue

        candidatos_texto.append((y_linea, texto_linea))

    if not candidatos_texto:
        return "NO IDENTIFICADA"

    categoria = candidatos_texto[0][1]
    return categoria or "NO IDENTIFICADA"


def _analizar_vacantes_en_imagen(page, image_path, termino="VACANTE"):
    """
    Analiza una página renderizada como imagen.

    REGLA:
      término resaltado -> cuadro que lo contiene -> primera línea del cuadro
      -> CATEGORÍA.

    En modo VACANTE analiza la palabra VACANTE. En modo PALABRA O FRASE
    analiza el término consultado, que save_marked ya resaltó en amarillo.
    La búsqueda se apoya en el PDF para conservar todas las coincidencias;
    la imagen se usa para detectar el cuadro y leer visualmente la categoría.
    """
    if not CV2_DISPONIBLE or not OCR_DISPONIBLE:
        return None

    imagen = cv2.imread(image_path)
    if imagen is None:
        return None

    mascara_amarillo = _imagen_a_color_amarillo(imagen)
    cuadros = _cuadros_organigrama_desde_imagen(imagen)

    if not cuadros:
        return None

    try:
        rects_pdf = page.search_for(termino)
    except Exception:
        rects_pdf = []

    if not rects_pdf:
        return []

    # Relación entre coordenadas PDF y píxeles de la imagen.
    pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
    escala_x = imagen.shape[1] / float(page.rect.width)
    escala_y = imagen.shape[0] / float(page.rect.height)

    resultados = []

    for numero, rect_pdf in enumerate(rects_pdf, start=1):
        x = int(rect_pdf.x0 * escala_x)
        y = int(rect_pdf.y0 * escala_y)
        w = max(1, int(rect_pdf.width * escala_x))
        h = max(1, int(rect_pdf.height * escala_y))

        # Comprueba si el área de VACANTE tiene amarillo. Si la anotación
        # fue renderizada con otro tono, se permite una búsqueda un poco mayor.
        amarillo = 0
        if mascara_amarillo is not None:
            x1 = max(0, x - 8)
            y1 = max(0, y - 8)
            x2 = min(imagen.shape[1], x + w + 8)
            y2 = min(imagen.shape[0], y + h + 8)
            region = mascara_amarillo[y1:y2, x1:x2]
            if region.size:
                amarillo = float(np.mean(region > 0))

        cx = x + w / 2
        cy = y + h / 2

        candidatos = []
        for cuadro in cuadros:
            qx, qy, qw, qh = cuadro
            if qx <= cx <= qx + qw and qy <= cy <= qy + qh:
                candidatos.append((qw * qh, cuadro))

        if not candidatos:
            categoria = "NO IDENTIFICADA"
            cuadro = None
        else:
            candidatos.sort(key=lambda z: z[0])
            cuadro = candidatos[0][1]
            categoria = _texto_categoria_desde_imagen(
                imagen,
                cuadro
            )

        resultados.append({
            "numero": numero,
            "rect_pdf": rect_pdf,
            "categoria": categoria,
            "amarillo": amarillo,
            "cuadro": cuadro
        })

    return resultados


def vacancy_causes(page, image_path=None):
    """
    Cuenta las VACANTES por CATEGORÍA y CAUSA.

    La CATEGORÍA se obtiene preferentemente desde la imagen generada de la
    página: se localiza la VACANTE, se identifica el cuadro del organigrama
    que la contiene y se lee la primera línea del cuadro (encabezado en
    negritas). Si el análisis visual no está disponible, se utiliza como
    respaldo la geometría del PDF.
    """
    text = page.get_text("text") or ""

    pat = re.compile(
        r"\bVACANTE\b\s*(?:\(\s*([^()]+?)\s*\))?",
        re.I | re.S
    )

    matches = list(pat.finditer(text))

    if not matches:
        return {}

    resultados_imagen = None

    if image_path:
        try:
            resultados_imagen = _analizar_vacantes_en_imagen(
                page,
                image_path
            )
        except Exception:
            resultados_imagen = None

    # Coincidencias geométricas para respaldo y para causas.
    try:
        rects_vacante = page.search_for("VACANTE")
    except Exception:
        rects_vacante = []

    counts = {}

    for i, match in enumerate(matches):
        cause = (match.group(1) or "").strip()
        cause = re.sub(r"\s+", " ", cause).strip().upper()

        if not cause:
            cause = "SIN CAUSA ESPECIFICADA"

        categoria = None

        if resultados_imagen and i < len(resultados_imagen):
            categoria = resultados_imagen[i].get("categoria")

        if not categoria or categoria == "NO IDENTIFICADA":
            rect_vacante = (
                rects_vacante[i]
                if i < len(rects_vacante)
                else None
            )
            categoria = extraer_categoria_vacante(
                page,
                rect_vacante=rect_vacante,
                texto=text
            )

        clave = (categoria, cause)
        counts[clave] = counts.get(clave, 0) + 1

    return counts


# ==========================================================
# IMAGEN INTERACTIVA
# ==========================================================

def interactive_image(
    path,
    height=650
):

    try:

        with open(path, "rb") as f:
            b64 = base64.b64encode(
                f.read()
            ).decode()

        html = f"""
        <!doctype html>

        <html>

        <head>

        <meta
        name="viewport"
        content="width=device-width,
        initial-scale=1,
        maximum-scale=5,
        user-scalable=yes">

        <style>

        html,body {{
            margin:0;
            padding:0;
            width:100%;
            background:transparent;
            -webkit-text-size-adjust:100%;
        }}

        .wrap {{
            width:100%;
            text-align:center;
            box-sizing:border-box;
            padding:2px;
        }}

        .image-link {{
            display:block;
            width:100%;
            touch-action:pan-x pan-y pinch-zoom;
        }}

        img {{
            width:100%;
            max-width:100%;
            height:auto;
            display:block;
            border-radius:9px;
            box-shadow:0 3px 12px rgba(0,0,0,.2);
            cursor:zoom-in;
            touch-action:pan-x pan-y pinch-zoom;
        }}

        .open-link {{
            display:inline-block;
            margin:10px auto 2px;
            padding:11px 16px;
            border-radius:10px;
            background:#174a7e;
            color:#fff !important;
            text-decoration:none !important;
            font:700 15px Arial,sans-serif;
            min-height:22px;
        }}

        .hint {{
            font:600 13px Arial,sans-serif;
            line-height:1.45;
            color:#444;
            margin:8px 4px;
        }}

        @media(max-width:600px) {{
            .wrap {{ padding:0; }}
            img {{ border-radius:6px; }}
            .open-link {{ width:calc(100% - 32px); }}
        }}

        </style>

        </head>

        <body>

        <div class="wrap">

        <a
        class="image-link"
        href="data:image/png;base64,{b64}"
        target="_blank"
        rel="noopener noreferrer"
        aria-label="Abrir imagen en una pestaña nueva para ampliar">

        <img
        src="data:image/png;base64,{b64}"
        alt="Página del documento. Toca para abrir en otra pestaña y ampliar">

        </a>

        <a
        class="open-link"
        href="data:image/png;base64,{b64}"
        target="_blank"
        rel="noopener noreferrer">
        🔎 Abrir imagen en nueva pestaña / Zoom
        </a>

        <div class="hint">
        En la pestaña nueva, usa dos dedos para ampliar o reducir la imagen en el celular.
        </div>

        </div>

        </body>

        </html>
        """

        components.html(
            html,
            height=height,
            scrolling=True
        )

    except Exception as e:

        st.warning(
            f"No se pudo mostrar la imagen: {e}"
        )


# ==========================================================
# FUNCIONES OCR
# ==========================================================


def normalizar_espacios(texto):
    """Normaliza espacios conservando saltos de línea cuando son útiles."""
    if texto is None:
        return ""
    texto = str(texto).replace("\r\n", "\n").replace("\r", "\n")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n[ \t]+", "\n", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def limpiar_nombre(nombre):
    nombre = normalizar_espacios(nombre)
    nombre = re.sub(r"^[\-:;,]+", "", nombre).strip()
    nombre = re.sub(r"[.;,]+$", "", nombre).strip()
    return nombre


def extraer_dependencia_robusta(texto, nombre_oficio=""):
    """
    Busca la dependencia en el texto del oficio y, si no existe un
    campo explícito, intenta reconocer dependencias institucionales.
    La inferencia desde el nombre del archivo es limitada a abreviaturas
    inequívocas.
    """
    t = normalizar_espacios(texto).upper()
    oficio = str(nombre_oficio or "").upper()

    # 1) Campos explícitos.
    for patron in [
        r"\bDEPENDENCIA\s*[:\-]\s*([^\n]+)",
        r"\bUNIDAD\s+RESPONSABLE\s*[:\-]\s*([^\n]+)",
        r"\bÁREA\s+RESPONSABLE\s*[:\-]\s*([^\n]+)",
        r"\bAREA\s+RESPONSABLE\s*[:\-]\s*([^\n]+)",
    ]:
        m = re.search(patron, t, re.I)
        if m:
            valor = re.sub(r"\s+", " ", m.group(1)).strip(" .:-")
            if valor:
                return valor

    # 2) Dependencias conocidas de la estructura UAdeC.
    dependencias = [
        ("OFICIALÍA MAYOR", ["OFICIALIA MAYOR", "OFICIALÍA MAYOR"]),
        ("SECRETARÍA GENERAL", ["SECRETARIA GENERAL", "SECRETARÍA GENERAL"]),
        ("RECTORÍA", ["RECTORIA", "RECTORÍA"]),
        ("TESORERÍA", ["TESORERIA", "TESORERÍA"]),
        ("CONTRALORÍA", ["CONTRALORIA", "CONTRALORÍA"]),
        ("PLANEACIÓN", ["PLANEACION", "PLANEACIÓN"]),
        ("POSGRADO", ["POSGRADO"]),
        ("ADQUISICIONES", ["ADQUISICIONES"]),
        ("AGENDA AMBIENTAL", ["AGENDA AMBIENTAL"]),
        ("ASUNTOS ACADÉMICOS", ["ASUNTOS ACADEMICOS", "ASUNTOS ACADÉMICOS"]),
        ("COMUNICACIÓN INSTITUCIONAL",
         ["COMUNICACION INSTITUCIONAL", "COMUNICACIÓN INSTITUCIONAL"]),
        ("COORDINACIÓN GENERAL JURÍDICA",
         ["COORDINACION GENERAL JURIDICA", "COORDINACIÓN GENERAL JURÍDICA"]),
        ("INFORMÁTICA", ["INFORMATICA", "INFORMÁTICA"]),
        ("VINCULACIÓN", ["VINCULACION", "VINCULACIÓN"]),
        ("RELACIONES INTERNACIONALES", ["RELACIONES INTERNACIONALES"]),
        ("EXTENSIÓN UNIVERSITARIA",
         ["EXTENSION UNIVERSITARIA", "EXTENSIÓN UNIVERSITARIA"]),
        ("EQUIDAD DE GÉNERO",
         ["EQUIDAD DE GENERO", "EQUIDAD DE GÉNERO"]),
        ("DEPORTES", ["DEPORTES"]),
        ("DEFENSORÍA DE LOS DERECHOS HUMANOS",
         ["DEFENSORIA DE LOS DERECHOS HUMANOS",
          "DEFENSORÍA DE LOS DERECHOS HUMANOS"]),
        ("TRIBUNAL UNIVERSITARIO", ["TRIBUNAL UNIVERSITARIO"]),
    ]

    for nombre, variantes in dependencias:
        if any(v in t for v in variantes):
            return nombre

    # 3) Abreviaturas sólo si aparecen delimitadas en el nombre del oficio.
    abreviaturas = {
        "OM": "OFICIALÍA MAYOR",
        "SG": "SECRETARÍA GENERAL",
        "RECT": "RECTORÍA",
        "TES": "TESORERÍA",
        "CONT": "CONTRALORÍA",
        "PL": "PLANEACIÓN",
        "POS": "POSGRADO",
        "ADQ": "ADQUISICIONES",
    }

    for abrev, nombre in abreviaturas.items():
        if re.search(rf"(^|[-_\s]){re.escape(abrev)}([-_\s.]|$)", oficio):
            return nombre

    return "No identificada"


def limpiar_referencia(referencia):
    referencia = normalizar_espacios(referencia)
    referencia = re.sub(r"^\s*REFERENCIA\s*[:\-]?\s*", "", referencia, flags=re.I)
    referencia = re.sub(r"\s+([,.;:])", r"\1", referencia)
    return referencia.strip(" \n\t.-")


def extraer_nombre_exclusivo(referencia):
    """
    Deja exclusivamente el nombre después de frases administrativas
    como 'CAMBIO DE CATEGORÍA DE'.
    """
    nombre = limpiar_referencia(referencia)

    prefijos = [
        r"CAMBIO\s+DE\s+CATEGOR[IÍ]A\s+DE",
        r"CAMBIO\s+DE\s+PUESTO\s+DE",
        r"CAMBIO\s+DE\s+ADSCRIPCI[ÓO]N\s+DE",
        r"CAMBIO\s+DE\s+PLAZA\s+DE",
        r"CAMBIO\s+DE\s+NOMBRAMIENTO\s+DE",
        r"MOVIMIENTO\s+DE",
        r"BAJA\s+DE",
        r"ALTA\s+DE",
        r"NOMBRAMIENTO\s+DE",
        r"CONTRATACI[ÓO]N\s+DE",
        r"DESIGNACI[ÓO]N\s+DE",
        r"PROMOCI[ÓO]N\s+DE",
        r"JUBILACI[ÓO]N\s+DE",
        r"RENUNCIA\s+DE",
        r"LICENCIA\s+DE",
        r"ACTUALIZACI[ÓO]N\s+DE",
    ]

    cambio = True
    while cambio:
        cambio = False
        for patron in prefijos:
            nuevo = re.sub(rf"^\s*{patron}\s+", "", nombre, flags=re.I)
            if nuevo != nombre:
                nombre = nuevo.strip()
                cambio = True

    # Quita complementos que ya no pertenecen al nombre.
    nombre = re.split(
        r"\s+(?:PARA|EN|COMO|POR|A\s+PARTIR\s+DE|CON\s+EFECTOS\s+DE)\s+",
        nombre,
        maxsplit=1,
        flags=re.I
    )[0]

    return nombre.strip(" ,;:.-")


def extraer_nombre_de_referencia(texto):
    """
    Extrae:
      - NOMBRE: exclusivamente el nombre
      - REFERENCIA: texto completo de la referencia

    Permite que la referencia se extienda a varias líneas y se detiene
    ante campos administrativos comunes.
    """
    texto = str(texto or "").replace("\r\n", "\n").replace("\r", "\n")

    patron = re.compile(
        r"\bREFERENCIA\s*[:\-]\s*(.*?)"
        r"(?=\n\s*(?:ASUNTO|OFICIO|FECHA|C\.?\s*C\.?|CC|"
        r"DESTINATARIO|ATENTAMENTE|PRESENTE|ANEXO|"
        r"DE\s+ACUERDO|FIRMA)\s*[:\-]|\Z)",
        re.I | re.S
    )

    m = patron.search(texto)

    if not m:
        # Fallback para OCR que eliminó los saltos de línea.
        m = re.search(
            r"\bREFERENCIA\s*[:\-]\s*([^\n]+)",
            texto,
            re.I
        )

    if not m:
        return "", ""

    referencia = limpiar_referencia(m.group(1))
    nombre = extraer_nombre_exclusivo(referencia)

    return nombre, referencia



def extraer_partes_oficio(texto):
    """Extrae los campos principales del oficio desde texto PDF/OCR.
    Los campos que no se localicen quedan vacíos; el OCR puede requerir revisión.
    """
    original = str(texto or "").replace("\r\n", "\n").replace("\r", "\n")
    lineas = [re.sub(r"[ \t]+", " ", x).strip() for x in original.split("\n")]
    lineas = [x for x in lineas if x]
    plano = "\n".join(lineas)

    def campo(patrones):
        for patron in patrones:
            m = re.search(patron, plano, re.I | re.M | re.S)
            if m:
                valor = re.sub(r"\s+", " ", m.group(1)).strip(" \t\n:;.-")
                if valor:
                    return valor
        return ""

    lugar_fecha = campo([
        r"^\s*((?:Saltillo|Torre[oó]n|Monclova|Piedras Negras|Acu[nñ]a|[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ .-]{2,}),\s*(?:Coahuila\s*)?(?:a\s+)?\d{1,2}\s+de\s+[A-Za-zÁÉÍÓÚáéíóú]+\s+de\s+\d{4})\s*$",
        r"^\s*(?:Lugar y fecha|Fecha)\s*[:\-]\s*([^\n]+)",
        r"^\s*([A-ZÁÉÍÓÚÑ][^\n]{3,80}\b\d{1,2}\s+de\s+[A-Za-zÁÉÍÓÚáéíóú]+\s+de\s+\d{4})\s*$"
    ])
    numeracion = campo([
        r"^\s*((?:OFICIO\s*(?:N[ÚU]M(?:ERO)?\.?\s*)?(?:NO\.?\s*)?[:#-]?\s*)[A-Z0-9./_-]+)\s*$",
        r"^\s*(OFICIO\s*(?:NO\.?|N[ÚU]MERO)?\s*[:#-]?\s*[A-Z0-9./_-]+)"
    ])
    referencia = campo([
        r"^\s*(?:ASUNTO\s*[:\-]\s*)([^\n]+)",
        r"\bREFERENCIA\s*[:\-]\s*(.*?)(?=\n\s*(?:ASUNTO|OFICIO|FECHA|DESTINATARIO|ATENTAMENTE|PRESENTE|C\.?\s*C\.?\s*P?\.?|ANEXO)\s*[:\-]?|\Z)"
    ])
    if not referencia:
        _, referencia = extraer_nombre_de_referencia(plano)
    referencia = re.sub(r"\s+", " ", referencia).strip()

    copia = campo([
        r"^\s*(c\.?\s*c\.?\s*p?\.?\s*[:\-]?\s*[^\n]+(?:\n(?!\s*(?:ATENTAMENTE|\b[A-ZÁÉÍÓÚÑ ]{3,}\b\s*$))[^\n]+)*)",
        r"^\s*(con copia\s*[:\-]?\s*[^\n]+)"
    ])
    if copia:
        copia = re.sub(r"\s+", " ", copia).strip()

    # Membrete: líneas institucionales iniciales, antes de fecha/numeración/destinatario.
    fin_membrete = len(lineas)
    for i, linea in enumerate(lineas[:12]):
        if re.search(r"\b(?:OFICIO\s*(?:NO\.?|N[ÚU]MERO)?|REFERENCIA\s*:|ASUNTO\s*:|PRESENTE\.?|A\s+\d{1,2}\s+DE\s+\w+\s+DE\s+\d{4})", linea, re.I):
            fin_membrete = i
            break
    membrete = " | ".join(lineas[:fin_membrete]).strip(" |")
    # Si las primeras líneas son claramente la ciudad/fecha, no incluirlas como membrete.
    if lugar_fecha and membrete and lugar_fecha.lower() in membrete.lower():
        membrete = " | ".join(x for x in lineas[:fin_membrete] if lugar_fecha.lower() not in x.lower()).strip(" |")

    # Cuerpo: desde después de PRESENTE hasta la despedida/firma, sin encabezados administrativos.
    inicio = None
    for i, linea in enumerate(lineas):
        if re.search(r"\bPRESENTE\.?\s*$", linea, re.I):
            inicio = i + 1
            break
    if inicio is None:
        # Alternativa: después de un saludo/destinatario, si aparece una línea de contenido.
        for i, linea in enumerate(lineas):
            if re.search(r"\b(?:PRESENTE|ESTIMAD[OA]|A QUIEN CORRESPONDA)\b", linea, re.I):
                inicio = i + 1
                break
    if inicio is None:
        inicio = 0
    fin = len(lineas)
    for i in range(inicio, len(lineas)):
        if re.search(r"\b(?:ATENTAMENTE|CORDIALMENTE|SIN OTRO PARTICULAR|A T E N T A M E N T E)\b", lineas[i], re.I):
            fin = i
            break
    excluir = re.compile(r"^(?:OFICIO\b|REFERENCIA\s*:|ASUNTO\s*:|C\.?\s*C\.?\s*P?\.?\s*[:\-]?|CON COPIA\b)", re.I)
    cuerpo_lineas = [x for x in lineas[inicio:fin] if not excluir.search(x)]
    cuerpo = " ".join(cuerpo_lineas).strip()

    return {
        "MEMBRETE": membrete,
        "LUGAR Y FECHA": lugar_fecha,
        "NUMERACION": numeracion,
        "ASUNTO O REFERENCIA": referencia,
        "CUERPO O TEXTO": cuerpo,
        "CON COPIA": copia,
    }


def ocr_pdf_referencia(archivo_pdf, progreso=None, nombre_oficio=""):
    """
    Procesa PDF digital y PDF escaneado.
    Si la página tiene poco texto o no contiene REFERENCIA, intenta OCR.
    """
    documento = pymupdf.open(archivo_pdf)
    resultados = []

    try:
        total = len(documento)

        for indice, pagina in enumerate(documento):
            texto_pdf = pagina.get_text("text") or ""
            texto = texto_pdf
            metodo = "Texto PDF"

            nombre, referencia = extraer_nombre_de_referencia(texto_pdf)

            # OCR si el PDF está escaneado o el texto digital no permitió
            # localizar REFERENCIA.
            if (len(texto_pdf.strip()) < 20 or not referencia) and OCR_DISPONIBLE:
                try:
                    pix = pagina.get_pixmap(
                        matrix=pymupdf.Matrix(3, 3),
                        alpha=False
                    )
                    imagen = Image.open(io.BytesIO(pix.tobytes("png")))

                    try:
                        texto_ocr = pytesseract.image_to_string(
                            imagen,
                            lang="spa",
                            config="--psm 6"
                        )
                    except Exception:
                        texto_ocr = pytesseract.image_to_string(
                            imagen,
                            lang="eng",
                            config="--psm 6"
                        )

                    nombre_ocr, referencia_ocr = extraer_nombre_de_referencia(
                        texto_ocr
                    )

                    if referencia_ocr:
                        texto = texto_ocr
                        nombre = nombre_ocr
                        referencia = referencia_ocr
                        metodo = "OCR"

                except Exception:
                    pass

            if referencia:
                resultados.append({
                    "PAGINA": indice + 1,
                    "DEPENDENCIA": extraer_dependencia_robusta(
                        texto,
                        nombre_oficio=nombre_oficio
                    ),
                    "NOMBRE": nombre,
                    "REFERENCIA": referencia,
                    **extraer_partes_oficio(texto),
                    "METODO": metodo
                })

            if progreso:
                progreso.progress((indice + 1) / max(total, 1))

    finally:
        documento.close()

    return resultados

def verificar_ocr():

    if not OCR_DISPONIBLE:

        return (
            False,
            "No están instalados "
            "pytesseract/Pillow."
        )

    ejecutable = getattr(
        pytesseract.pytesseract,
        "tesseract_cmd",
        None
    )

    if (
        not ejecutable
        or
        not os.path.exists(ejecutable)
    ):

        ejecutable = shutil.which(
            "tesseract"
        )

    if not ejecutable:

        return (
            False,
            "Python tiene pytesseract, "
            "pero no se encontró "
            "Tesseract en el sistema."
        )

    pytesseract.pytesseract.tesseract_cmd = (
        ejecutable
    )

    try:

        pytesseract.get_tesseract_version()

    except Exception as error:

        return (
            False,
            f"Tesseract fue localizado, "
            f"pero no pudo ejecutarse: {error}"
        )

    try:

        idiomas = (
            pytesseract
            .get_languages(config="")
        )

        if "spa" not in idiomas:

            return (
                False,
                "Tesseract está instalado, "
                "pero falta el idioma español (spa)."
            )

    except Exception:
        pass

    return True, ejecutable


# ==========================================================
# TIPO DE BÚSQUEDA
# ==========================================================

st.subheader(
    "🔎 Tipo de búsqueda"
)

kind = st.radio(
    "Seleccione qué desea buscar:",

    [
        "Persona",
        "Expediente",
        "Vacante",
        "Palabra o frase",
        "📄 Referencia de oficio"
    ],

    horizontal=True
)


# ==========================================================
# REFERENCIA DE OFICIO
# ==========================================================

if kind == "📄 Referencia de oficio":

    st.info(
        'Este modo permite subir uno o varios '
        'oficios PDF y obtener automáticamente '
        'el nombre de la persona que aparece '
        'después de "REFERENCIA:". '
        'Funciona también con PDFs escaneados '
        'mediante OCR.'
    )

    archivos_oficio = st.file_uploader(
        "📎 Seleccione uno o varios oficios PDF",
        type=["pdf"],
        accept_multiple_files=True
    )

    if archivos_oficio:

        ok_ocr, diagnostico = verificar_ocr()

        if not ok_ocr:

            st.warning(
                "Para oficios escaneados "
                "se necesita OCR. "
                + diagnostico
            )

            st.code(
                "pip install pytesseract pillow"
            )

            st.code(
                "brew install tesseract tesseract-lang"
            )

    procesar_oficios = st.button(
        "📄 EXTRAER NOMBRE DE REFERENCIA",
        type="primary",
        use_container_width=True,
        disabled=not archivos_oficio
    )

    if procesar_oficios:

        resultados_referencia = []

        imagenes_referencia = []

        for archivo_subido in archivos_oficio:

            ruta_temporal = os.path.join(
                "Resultados_UAdeC",
                "_oficio_"
                + safe(archivo_subido.name)
            )

            with open(
                ruta_temporal,
                "wb"
            ) as f:

                f.write(
                    archivo_subido.getvalue()
                )

            st.write(
                f"**Procesando:** "
                f"{archivo_subido.name}"
            )

            progreso = st.progress(0)

            try:

                encontrados = ocr_pdf_referencia(
                    ruta_temporal,
                    progreso=progreso,
                    nombre_oficio=archivo_subido.name
                )

                if encontrados:

                    for item in encontrados:

                        resultados_referencia.append({

                            "OFICIO":
                                archivo_subido.name,

                            **item
                        })

                        try:

                            doc_img = pymupdf.open(
                                ruta_temporal
                            )

                            pagina = doc_img[
                                item["PAGINA"] - 1
                            ]

                            pix = pagina.get_pixmap(
                                matrix=pymupdf.Matrix(2, 2),
                                alpha=False
                            )

                            nombre_img = (
                                f"Referencia_"
                                f"{safe(archivo_subido.name)}"
                                f"_pagina_"
                                f"{item['PAGINA']}.png"
                            )

                            ruta_img = os.path.join(
                                IMG_DIR,
                                nombre_img
                            )

                            pix.save(ruta_img)

                            imagenes_referencia.append({

                                "oficio":
                                    archivo_subido.name,

                                "pagina":
                                    item["PAGINA"],

                                "imagen":
                                    ruta_img
                            })

                            doc_img.close()

                        except Exception as error_img:

                            st.warning(
                                f"No se pudo generar "
                                f"la imagen: {error_img}"
                            )

                else:

                    st.warning(
                        f"No se encontró REFERENCIA "
                        f"en {archivo_subido.name}."
                    )

            except Exception as error:

                st.error(
                    f"Error procesando "
                    f"{archivo_subido.name}: {error}"
                )

            progreso.empty()

        if resultados_referencia:

            st.divider()

            st.subheader(
                "👤 Persona encontrada en REFERENCIA"
            )

            df_referencia = pd.DataFrame(
                resultados_referencia
            )

            # Limpieza compartida para NOMBRE y ASUNTO O REFERENCIA.
            # Elimina el nombre/cargo, "presente" y la frase de apertura aunque
            # el OCR haya introducido variantes o pequeños residuos antes de ellas.
            patron_destinataria = (
                r"(?:ENF\.?|F\.?)?\s*NORA\s+MIREYA\s+RAMÍREZ\s+SÁNCHEZ"
                r"|SECRETARIA\s+GENERAL\s+DEL\s+STUAC"
                r"|p\s*r\s*e\s*s\s*e\s*n\s*t\s*e\s*[.\-]*"
                r"|A\s+fin\s+de\s+dar\s+cumplimiento\s+a\s+lo\s+establecido[.,;:]*"
            )

            def limpiar_campo_referencia(valor):
                valor = "" if valor is None else str(valor)
                # Quitar basura OCR frecuente justo antes de las frases no deseadas.
                valor = re.sub(
                    r'(?:ESE\s*i\s*/?\s*[“\"”]?|Y\s*Ni\s*[“\"”]?|Y\s*ño\.?\s*/?\s*)'
                    r"(?=\s*(?:SECRETARIA\s+GENERAL\s+DEL\s+STUAC|A\s+fin\s+de\s+dar\s+cumplimiento))",
                    " ", valor, flags=re.IGNORECASE
                )
                valor = re.sub(patron_destinataria, " ", valor, flags=re.IGNORECASE)
                valor = re.sub(r"\s+", " ", valor)
                return valor.strip(" \t\r\n.-:,;“”\"/")

            df_referencia["NOMBRE"] = (
                df_referencia["NOMBRE"].fillna("").astype(str)
                .map(limpiar_campo_referencia)
            )

            df_referencia["LUGAR Y FECHA"] = (
                df_referencia["LUGAR Y FECHA"]
                .fillna("")
                .astype(str)
                .str.replace(
                    r"^\s*SALTILLO\s*,?\s*COAHUILA\s+A\s*",
                    "",
                    regex=True,
                    case=False
                )
                .str.strip()
            )

            df_referencia["ASUNTO O REFERENCIA"] = (
                df_referencia["ASUNTO O REFERENCIA"].fillna("").astype(str)
                .map(limpiar_campo_referencia)
            )

            def limpiar_referencia_final(valor):
                valor = "" if valor is None else str(valor)
                # Quitar "Sin otro particular" y todo el texto que le siga.
                # Se permite que la frase esté distribuida en varias líneas por OCR.
                valor = re.sub(
                    r"\bSin\s+otro\s+particular\b[\s\S]*$",
                    "",
                    valor,
                    flags=re.IGNORECASE
                )
                return valor.strip(" \t\r\n.-:,;“”\"/")

            df_referencia["REFERENCIA"] = (
                df_referencia["REFERENCIA"]
                .fillna("")
                .astype(str)
                .map(limpiar_referencia_final)
            )

            # Se excluyen PAGINA, DEPENDENCIA, MEMBRETE, CON COPIA y METODO del reporte.
            df_referencia = df_referencia[
                [
                    "OFICIO",
                    "NOMBRE",
                    "LUGAR Y FECHA",
                    "NUMERACION",
                    "ASUNTO O REFERENCIA",
                    "CUERPO O TEXTO",
                    "REFERENCIA"
                ]
            ]

            st.dataframe(
                df_referencia,
                use_container_width=True,
                hide_index=True
            )

            for _, fila in df_referencia.iterrows():

                st.success(
                    f"**{fila['NOMBRE']}** — "
                    f"{fila['OFICIO']}"
                )

            buffer_ref = BytesIO()

            with pd.ExcelWriter(
                buffer_ref,
                engine="openpyxl"
            ) as writer:

                df_referencia.to_excel(
                    writer,
                    index=False,
                    sheet_name="PERSONA ENCONTRADA EN REFERENCIA"
                )

            st.download_button(
                "📥 Descargar resultados en Excel",

                data=buffer_ref.getvalue(),

                file_name=
                    "PERSONA_ENCONTRADA_EN_REFERENCIA.xlsx",

                mime=
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",

                use_container_width=True
            )

            st.divider()

            st.subheader(
                "🖼️ Página del oficio"
            )

            for i, item in enumerate(
                imagenes_referencia
            ):

                with st.expander(
                    f"📄 {item['oficio']} — "
                    f"Página {item['pagina']}"
                ):

                    interactive_image(
                        item["imagen"],
                        520
                    )

                    with open(
                        item["imagen"],
                        "rb"
                    ) as f:

                        datos = f.read()

                    st.download_button(
                        "📥 Descargar página",

                        data=datos,

                        file_name=os.path.basename(
                            item["imagen"]
                        ),

                        mime="image/png",

                        key=f"ref_img_{i}",

                        use_container_width=True
                    )

    st.divider()

    st.stop()


# ==========================================================
# MODOS EXISTENTES
# ==========================================================

if kind == "Persona":

    term = st.text_input(
        "👤 Nombre de la persona",
        placeholder=
        "Ejemplo: Martínez Romero Griselda"
    )

elif kind == "Expediente":

    term = st.text_input(
        "📁 Número de expediente",
        placeholder="Ejemplo: 36768"
    )

elif kind == "Vacante":

    term = "vacante"

    st.info(
        "Se buscarán todas las apariciones "
        "de 'VACANTE' y las causas "
        "entre paréntesis."
    )

else:

    term = st.text_area(
        "🔎 Palabra o frase",
        placeholder=(
            "Escriba varias palabras o frases separadas por coma, punto y coma "
            "o una por línea. Ejemplo: DIRECTOR, COORDINADOR, JEFE"
        ),
        help=(
            "Puede buscar una o varias palabras/frases. Sepárelas con coma, "
            "punto y coma o escriba una por línea."
        ),
        height=100
    )


# ==========================================================
# DOCUMENTOS
# ==========================================================

st.subheader(
    "📚 Documentos"
)

choices = [
    "TODOS LOS DOCUMENTOS"
] + list(PDFS)

docs = st.multiselect(
    "Seleccione los documentos:",
    choices,
    default=["TODOS LOS DOCUMENTOS"]
)


# ==========================================================
# BOTÓN BUSCAR
# ==========================================================

if st.button(
    "🔍 BUSCAR",
    type="primary",
    use_container_width=True
):

    if not term.strip():

        st.warning(
            "Por favor escriba al menos una palabra o frase "
            "para realizar la búsqueda."
        )

        st.stop()

    # ------------------------------------------------------
    # VARIAS PALABRAS / FRASES
    # ------------------------------------------------------
    # En "Palabra o frase" se aceptan varios términos separados
    # por coma, punto y coma o saltos de línea.
    # Se eliminan espacios sobrantes y duplicados, conservando
    # el orden en que fueron escritos.
    search_terms = []

    if kind == "Palabra o frase":

        for item in re.split(r"[,;\n]+", term):

            item = re.sub(r"\s+", " ", item).strip()

            if item and item.lower() not in {
                x.lower() for x in search_terms
            }:
                search_terms.append(item)

    else:
        search_terms = [term.strip()]

    if not search_terms:

        st.warning(
            "Por favor escriba al menos una palabra o frase válida."
        )

        st.stop()

    targets = (
        list(PDFS)
        if "TODOS LOS DOCUMENTOS" in docs
        else docs
    )

    if not targets:

        st.warning(
            "Seleccione al menos un documento."
        )

        st.stop()

    results = []

    images = []

    progress = st.progress(0)

    status = st.empty()


    # ======================================================
    # PROCESAMIENTO DE DOCUMENTOS
    # ======================================================

    for i, name in enumerate(targets):

        status.write(
            f"Procesando: **{name}** "
            f"({i+1} de {len(targets)})"
        )

        try:

            pdf = download_pdf(
                name,
                PDFS[name]
            )

            doc = pymupdf.open(pdf)

            for pno, page in enumerate(doc):

                text = page.get_text()

                if not text:
                    continue


                # ==========================================
                # VACANTES
                # ==========================================

                if kind == "Vacante":

                    dep = dependencia(text)

                    # Para VACANTE primero generamos la página marcada.
                    # El análisis de categorías se hace sobre esa imagen.
                    imagen_vacante = None
                    try:
                        imagen_vacante = save_marked(
                            page,
                            term,
                            name,
                            pno
                        )
                    except Exception as e:
                        st.warning(
                            f"No fue posible generar la imagen de {name}, "
                            f"página {pno+1}: {e}"
                        )

                    causes = vacancy_causes(
                        page,
                        image_path=imagen_vacante
                    )

                    if not causes:
                        continue

                    # vacancy_causes relaciona cada VACANTE con la categoría
                    # del cuadro que la contiene. Una misma página puede
                    # tener varias categorías.
                    results.append({

                        "DOCUMENTO":
                            name,

                        "PAGINA":
                            pno + 1,

                        "DEPENDENCIA":
                            dep,

                        "CAUSAS":
                            causes
                    })

                    if imagen_vacante:
                        images.append({
                            "documento": name,
                            "pagina": pno + 1,
                            "dependencia": dep,
                            "imagen": imagen_vacante
                        })

                    continue


                # ==========================================
                # OTROS TIPOS
                # ==========================================

                else:

                    # --------------------------------------
                    # BÚSQUEDA DE VARIOS TÉRMINOS
                    # --------------------------------------
                    # Cada palabra/frase se busca de manera
                    # independiente. Una página puede generar
                    # una o varias filas, según los términos
                    # que encuentre.
                    texto_lower = text.lower()
                    encontrados = []

                    for search_term in search_terms:

                        if search_term.lower() in texto_lower:
                            encontrados.append(search_term)

                    if not encontrados:
                        continue

                    dep = dependencia(text)

                    for search_term in encontrados:

                        imagen_resultado = None
                        categorias_detectadas = []
                        hallazgos_visual = []

                        # ----------------------------------
                        # Imagen marcada por término y análisis visual
                        # ----------------------------------
                        try:
                            imagen_resultado = save_marked(
                                page,
                                search_term,
                                name,
                                pno
                            )

                            # Aplica el algoritmo del organigrama también a
                            # PALABRA O FRASE: término resaltado -> cuadro ->
                            # primera línea del cuadro (categoría en negritas).
                            hallazgos_visual = _analizar_vacantes_en_imagen(
                                page,
                                imagen_resultado,
                                termino=search_term
                            )

                            if hallazgos_visual:
                                categorias_detectadas = list(dict.fromkeys(
                                    str(h.get("categoria", "NO IDENTIFICADA")).strip()
                                    for h in hallazgos_visual
                                    if h.get("categoria")
                                ))

                            images.append({
                                "documento": name,
                                "pagina": pno + 1,
                                "dependencia": dep,
                                "busqueda": search_term,
                                "imagen": imagen_resultado
                            })

                        except Exception as e:
                            st.warning(
                                f"No fue posible analizar la imagen para "
                                f"'{search_term}' en {name}, página {pno+1}: {e}"
                            )

                        if not categorias_detectadas:
                            categoria_reporte = "NO IDENTIFICADA"
                        else:
                            categorias_validas = [
                                c for c in categorias_detectadas
                                if c.upper() != "NO IDENTIFICADA"
                            ]
                            categoria_reporte = "; ".join(
                                categorias_validas or categorias_detectadas
                            )

                        results.append({
                            "DOCUMENTO": name,
                            "PAGINA": pno + 1,
                            "DEPENDENCIA": dep,
                            "BÚSQUEDA": search_term,
                            "CATEGORIA": categoria_reporte,
                            "COINCIDENCIAS VISUALES": len(hallazgos_visual or [])
                        })

                    # Ya se generaron las imágenes para cada término
                    # encontrado; no volver a crear una imagen usando
                    # toda la cadena de búsqueda.
                    continue

            doc.close()

        except Exception as e:

            st.error(
                f"Error procesando {name}: {e}"
            )

        progress.progress(
            (i + 1) / len(targets)
        )

    status.empty()

    st.divider()

    st.subheader(
        "📊 Reporte de resultados"
    )

    if kind == "Palabra o frase":
        st.info(
            "Términos buscados: "
            + " · ".join(f"**{x}**" for x in search_terms)
            + ". También se intenta identificar la categoría del cuadro "
              "del organigrama donde aparece cada término resaltado."
        )


    if not results:

        st.warning(
            "No se encontraron resultados para los términos: "
            + ", ".join(search_terms)
        )

        st.stop()


    # ======================================================
    # MODO VACANTE
    # ======================================================

    if kind == "Vacante":

        # --------------------------------------------------
        # OBTENER TODAS LAS CAUSAS
        # --------------------------------------------------

        # CAUSAS viene como {(CATEGORIA, CAUSA): TOTAL}.
        # Esto permite que una misma página tenga, por ejemplo,
        # COCINERO y ENFERMERA GENERAL sin mezclar las vacantes.
        causes_all = sorted(
            {
                causa
                for r in results
                for (_, causa) in r["CAUSAS"]
            }
        )


        # --------------------------------------------------
        # CREAR FILAS DEL DATAFRAME
        # --------------------------------------------------

        rows = []

        for r in results:

            categorias = {}

            for (categoria, causa), total in r["CAUSAS"].items():

                if categoria not in categorias:
                    categorias[categoria] = {}

                categorias[categoria][causa] = (
                    categorias[categoria].get(causa, 0)
                    + total
                )

            for categoria, causas_categoria in categorias.items():

                row = {

                    "DOCUMENTO":
                        r["DOCUMENTO"],

                    "PAGINA":
                        r["PAGINA"],

                    "DEPENDENCIA":
                        r["DEPENDENCIA"],

                    "CATEGORIA":
                        categoria
                }

                for causa in causes_all:

                    row[causa] = causas_categoria.get(
                        causa,
                        0
                    )

                rows.append(row)


        # --------------------------------------------------
        # DATAFRAME PRINCIPAL
        # --------------------------------------------------

        df = pd.DataFrame(rows)


        # --------------------------------------------------
        # COLUMNAS DE CAUSAS
        # --------------------------------------------------

        cause_cols = [

            c

            for c in df.columns

            if c not in [
                "DOCUMENTO",
                "PAGINA",
                "DEPENDENCIA",
                "CATEGORIA"
            ]
        ]


        # --------------------------------------------------
        # TOTAL DE VACANTES POR FILA
        # --------------------------------------------------

        if cause_cols:

            df["TOTAL VACANTES"] = (
                df[cause_cols]
                .sum(axis=1)
                .astype(int)
            )

        else:

            df["TOTAL VACANTES"] = 0


        # --------------------------------------------------
        # ORDEN DE COLUMNAS
        # --------------------------------------------------

        df = df[
            [
                "DOCUMENTO",
                "PAGINA",
                "DEPENDENCIA",
                "CATEGORIA",
                "TOTAL VACANTES"
            ]
            +
            cause_cols
        ]


        # ==================================================
        # MÉTRICAS
        # ==================================================

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Vacantes",
            int(
                df["TOTAL VACANTES"].sum()
            )
        )

        c2.metric(
            "Páginas",
            len(df)
        )

        c3.metric(
            "Dependencias",
            df["DEPENDENCIA"].nunique()
        )


        # ==================================================
        # DETALLE DE VACANTES
        # ==================================================

        st.subheader(
            "📋 Detalle de vacantes"
        )

        st.caption(
            "TOTAL VACANTES suma todas las "
            "causas entre paréntesis de cada fila."
        )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


        # ==================================================
        # NUEVO RESUMEN POR DEPENDENCIA Y CAUSA
        # ==================================================

        summary_rows = []


        for (dependencia_nombre, categoria_nombre), grupo in df.groupby(
            ["DEPENDENCIA", "CATEGORIA"]
        ):

            for causa in cause_cols:

                total = int(
                    grupo[causa].sum()
                )

                # Solo incluir causas que
                # realmente tengan vacantes.

                if total > 0:

                    summary_rows.append({

                        "DEPENDENCIA":
                            dependencia_nombre,

                        "CATEGORIA":
                            categoria_nombre,

                        "CAUSA":
                            causa,

                        "TOTAL":
                            total
                    })


        # --------------------------------------------------
        # CREAR DATAFRAME RESUMEN
        # --------------------------------------------------

        summary = pd.DataFrame(
            summary_rows,

            columns=[
                "DEPENDENCIA",
                "CATEGORIA",
                "CAUSA",
                "TOTAL"
            ]
        )


        # --------------------------------------------------
        # ORDENAR RESUMEN
        # --------------------------------------------------

        if not summary.empty:

            summary = (
                summary
                .sort_values(
                    [
                        "DEPENDENCIA",
                        "CATEGORIA",
                        "TOTAL"
                    ],
                    ascending=[
                        True,
                        True,
                        False
                    ]
                )
                .reset_index(drop=True)
            )


        # ==================================================
        # MOSTRAR RESUMEN
        # ==================================================

        st.subheader(
            "📊 RESUMEN CAUSA"
        )

        st.caption(
            "Total de vacantes agrupadas por "
            "dependencia, categoría y causa."
        )

        st.dataframe(
            summary,
            use_container_width=True,
            hide_index=True
        )


        # ==================================================
        # RESUMEN TOTAL POR DEPENDENCIA
        # ==================================================

        resumen_dependencia = (
            df.groupby(
                "DEPENDENCIA",
                as_index=False
            )["TOTAL VACANTES"]
            .sum()
            .rename(
                columns={
                    "TOTAL VACANTES":
                        "TOTAL VACANTES"
                }
            )
            .sort_values(
                "TOTAL VACANTES",
                ascending=False
            )
            .reset_index(drop=True)
        )


        st.subheader(
            "🏢 Total de vacantes por dependencia"
        )

        st.dataframe(
            resumen_dependencia,
            use_container_width=True,
            hide_index=True
        )


        # ==================================================
        # EXCEL
        # ==================================================

        try:

            buf = BytesIO()

            with pd.ExcelWriter(
                buf,
                engine="openpyxl"
            ) as writer:

                # ------------------------------------------
                # HOJA 1
                # ------------------------------------------

                df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Vacantes"
                )


                # ------------------------------------------
                # HOJA 2
                # ------------------------------------------

                summary.to_excel(
                    writer,
                    index=False,
                    sheet_name="RESUMEN CAUSA"
                )


                # ------------------------------------------
                # HOJA 3
                # ------------------------------------------

                resumen_dependencia.to_excel(
                    writer,
                    index=False,
                    sheet_name="RESUMEN DEPENDENCIA"
                )


            st.download_button(

                "📥 Descargar reporte en Excel",

                data=buf.getvalue(),

                file_name=
                    "Reporte_Vacantes_UAdeC.xlsx",

                mime=
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",

                use_container_width=True
            )

        except Exception as e:

            st.warning(
                f"No se pudo generar el Excel: {e}"
            )


    # ======================================================
    # PERSONA / EXPEDIENTE / PALABRA
    # ======================================================

    else:

        df = pd.DataFrame(
            results
        )


        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Coincidencias",
            len(df)
        )

        c2.metric(
            "Documentos",
            df["DOCUMENTO"].nunique()
        )

        c3.metric(
            "Dependencias",
            df["DEPENDENCIA"].nunique()
        )


        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        # ==================================================
        # RESUMEN CAUSA PARA PALABRA O FRASE
        # ==================================================
        # En esta modalidad, cada término buscado funciona como CAUSA
        # del resumen. Se agrupa por dependencia, categoría y término.
        resumen_causa = pd.DataFrame()
        if kind == "Palabra o frase":
            df_resumen = df.copy()
            for columna in ["DEPENDENCIA", "CATEGORIA", "BÚSQUEDA"]:
                if columna not in df_resumen.columns:
                    df_resumen[columna] = "NO IDENTIFICADA"
                df_resumen[columna] = (
                    df_resumen[columna].fillna("NO IDENTIFICADA").astype(str).str.strip()
                )
                df_resumen.loc[df_resumen[columna] == "", columna] = "NO IDENTIFICADA"

            # Una fila del detalle representa un término hallado en una página.
            # Si el análisis visual contó varias coincidencias, se usa ese total;
            # en caso contrario se contabiliza al menos una aparición del término.
            if "COINCIDENCIAS VISUALES" in df_resumen.columns:
                conteo = pd.to_numeric(
                    df_resumen["COINCIDENCIAS VISUALES"], errors="coerce"
                ).fillna(0).astype(int)
                df_resumen["TOTAL"] = conteo.where(conteo > 0, 1)
            else:
                df_resumen["TOTAL"] = 1

            resumen_causa = (
                df_resumen.groupby(
                    ["DEPENDENCIA", "CATEGORIA", "BÚSQUEDA"], as_index=False
                )["TOTAL"].sum()
                .rename(columns={"BÚSQUEDA": "CAUSA"})
                .sort_values(
                    ["DEPENDENCIA", "CATEGORIA", "TOTAL"],
                    ascending=[True, True, False]
                )
                .reset_index(drop=True)
            )

            st.subheader("📊 RESUMEN CAUSA")
            st.caption(
                "Resultados de PALABRA O FRASE agrupados por dependencia, "
                "categoría detectada y término buscado. TOTAL cuenta las "
                "coincidencias visuales detectadas; cuando no hay conteo visual, "
                "se contabiliza una aparición por página y término."
            )
            st.dataframe(
                resumen_causa,
                use_container_width=True,
                hide_index=True
            )

        # ==================================================
        # EXCEL
        # ==================================================

        try:

            buf = BytesIO()

            with pd.ExcelWriter(
                buf,
                engine="openpyxl"
            ) as writer:

                df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Resultados"
                )

                if kind == "Palabra o frase":
                    resumen_causa.to_excel(
                        writer,
                        index=False,
                        sheet_name="RESUMEN CAUSA"
                    )

            st.download_button(

                "📥 Descargar reporte en Excel",

                data=buf.getvalue(),

                file_name=(
                    "Reporte_Palabra_o_Frase_UAdeC.xlsx"
                    if kind == "Palabra o frase"
                    else "Reporte_UAdeC.xlsx"
                ),

                mime=
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",

                use_container_width=True
            )

        except Exception as e:

            st.warning(
                f"No se pudo generar el Excel: {e}"
            )


    # ======================================================
    # IMÁGENES
    # ======================================================

    st.divider()

    st.subheader(
        "🖼️ Páginas encontradas"
    )

    st.caption(
        "Toca directamente la imagen para "
        "abrirla en una nueva pestaña y "
        "usar el zoom del navegador."
    )


    for i, item in enumerate(images):

        with st.expander(
            f"📄 {item['documento']} — "
            f"Página {item['pagina']}"
        ):

            st.write(
                f"**DEPENDENCIA:** "
                f"{item['dependencia']}"
            )

            interactive_image(
                item["imagen"],
                520
            )

            try:

                with open(
                    item["imagen"],
                    "rb"
                ) as f:

                    data = f.read()


                st.download_button(

                    "📥 Descargar imagen",

                    data=data,

                    file_name=os.path.basename(
                        item["imagen"]
                    ),

                    mime="image/png",

                    key=f"img_{i}",

                    use_container_width=True
                )

            except Exception as e:

                st.warning(
                    f"No se pudo preparar "
                    f"la descarga: {e}"
                )


# ==========================================================
# PIE DE PÁGINA
# ==========================================================

st.divider()