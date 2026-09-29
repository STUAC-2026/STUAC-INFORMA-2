import streamlit as st
import streamlit.components.v1 as components
import requests, pymupdf, warnings, re, os, base64, io, shutil
import pandas as pd
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


def vacancy_causes(page):

    text = page.get_text("text")

    pat = re.compile(
        r"\bVACANTE\b\s*\(\s*([^()]+?)\s*\)",
        re.I | re.S
    )

    counts = {}

    for cause in pat.findall(text):

        cause = re.sub(
            r"\s+",
            " ",
            cause
        ).strip().upper()

        if cause:

            counts[cause] = (
                counts.get(cause, 0) + 1
            )

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
            background:transparent;
        }}

        .wrap {{
            width:100%;
            text-align:center;
        }}

        img {{
            width:100%;
            height:auto;
            display:block;
            border-radius:9px;
            box-shadow:
                0 3px 12px
                rgba(0,0,0,.2);
            cursor:zoom-in;
        }}

        .hint {{
            font:
                700 13px Arial;
            color:#444;
            margin:8px;
        }}

        </style>

        </head>

        <body>

        <div class="wrap">

        <a
        href="data:image/png;base64,{b64}"
        target="_blank"
        rel="noopener noreferrer">

        <img
        src="data:image/png;base64,{b64}"
        alt="Página del documento">

        </a>

        <div class="hint">
        🔍 Toca la imagen para abrirla y ampliarla
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

            # Orden solicitado:
            # OFICIO | PAGINA | DEPENDENCIA | NOMBRE | REFERENCIA | METODO
            df_referencia["NOMBRE"] = (
                df_referencia["NOMBRE"]
                .astype(str)
                .str.strip()
            )

            df_referencia["REFERENCIA"] = (
                df_referencia["REFERENCIA"]
                .astype(str)
                .str.strip()
            )

            df_referencia = df_referencia[
                [
                    "OFICIO",
                    "PAGINA",
                    "DEPENDENCIA",
                    "NOMBRE",
                    "REFERENCIA",
                    "METODO"
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
                    f"{fila['OFICIO']} — "
                    f"página {fila['PAGINA']}"
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
                        650
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

    st.markdown(
        """
        <div style="
            text-align:center;
            opacity:.75;
            font-size:14px;
            padding:10px">

            <b>STUAC INFORMA</b><br>

            Sindicato de Trabajadores de
            la Universidad Autónoma de Coahuila

        </div>
        """,
        unsafe_allow_html=True
    )

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

    term = st.text_input(
        "🔎 Palabra o frase",
        placeholder="Ejemplo: DIRECTOR"
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
            "Por favor escriba un término "
            "para realizar la búsqueda."
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

                    causes = vacancy_causes(
                        page
                    )

                    if not causes:
                        continue

                    dep = dependencia(text)

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


                # ==========================================
                # OTROS TIPOS
                # ==========================================

                else:

                    if (
                        term.lower()
                        not in text.lower()
                    ):
                        continue

                    dep = dependencia(text)

                    results.append({

                        "DOCUMENTO":
                            name,

                        "PAGINA":
                            pno + 1,

                        "DEPENDENCIA":
                            dep,

                        "BÚSQUEDA":
                            term
                    })


                # ==========================================
                # IMAGEN
                # ==========================================

                try:

                    images.append({

                        "documento":
                            name,

                        "pagina":
                            pno + 1,

                        "dependencia":
                            dep,

                        "imagen":
                            save_marked(
                                page,
                                term,
                                name,
                                pno
                            )
                    })

                except Exception as e:

                    st.warning(
                        f"No fue posible generar "
                        f"la imagen de {name}, "
                        f"página {pno+1}: {e}"
                    )

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


    if not results:

        st.warning(
            f"No se encontraron resultados "
            f"para: **{term}**"
        )

        st.stop()


    # ======================================================
    # MODO VACANTE
    # ======================================================

    if kind == "Vacante":

        # --------------------------------------------------
        # OBTENER TODAS LAS CAUSAS
        # --------------------------------------------------

        causes_all = sorted(
            {
                c
                for r in results
                for c in r["CAUSAS"]
            }
        )


        # --------------------------------------------------
        # CREAR FILAS DEL DATAFRAME
        # --------------------------------------------------

        rows = []

        for r in results:

            row = {

                "DOCUMENTO":
                    r["DOCUMENTO"],

                "PAGINA":
                    r["PAGINA"],

                "DEPENDENCIA":
                    r["DEPENDENCIA"]
            }

            for c in causes_all:

                row[c] = r["CAUSAS"].get(
                    c,
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
                "DEPENDENCIA"
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


        for dependencia_nombre, grupo in df.groupby(
            "DEPENDENCIA"
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
                        "TOTAL"
                    ],
                    ascending=[
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
            "dependencia y causa."
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


            st.download_button(

                "📥 Descargar reporte en Excel",

                data=buf.getvalue(),

                file_name=
                    "Reporte_UAdeC.xlsx",

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
                650
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

st.markdown(
    """
    <div style="
        text-align:center;
        opacity:.75;
        font-size:14px;
        padding:10px">

        <b>STUAC INFORMA</b><br>

        Sindicato de Trabajadores de
        la Universidad Autónoma de Coahuila

    </div>
    """,
    unsafe_allow_html=True
)