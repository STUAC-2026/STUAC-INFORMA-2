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
# RELACIÓN OBSERVACIONES / RESPUESTA Y NÚMEROS DE OFICIO
# ==========================================================

# Coloque este Excel junto al programa. Los PDF relacionados se buscan en PDF_UAdeC.
RELACION_OFICIOS_XLSX = "Relacion_Observaciones_Respuesta_Numero_Oficio_UAdeC.xlsx"


def _normalizar_nombre_archivo(valor):
    """Normaliza nombres para encontrar PDF aunque haya diferencias de acentos."""
    import unicodedata
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip().casefold()


def _buscar_pdf_relacionado(nombre_pdf):
    """Busca el PDF por nombre en PDF_UAdeC y subcarpetas."""
    if not nombre_pdf:
        return None
    raices = [
        os.path.abspath(PDF_DIR),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), PDF_DIR),
    ]
    objetivo = _normalizar_nombre_archivo(os.path.basename(str(nombre_pdf)))
    try:
        for raiz in dict.fromkeys(raices):
            if not os.path.isdir(raiz):
                continue
            for carpeta, _, archivos in os.walk(raiz):
                for archivo in archivos:
                    if archivo.lower().endswith(".pdf") and _normalizar_nombre_archivo(archivo) == objetivo:
                        return os.path.join(carpeta, archivo)
    except OSError:
        return None
    return None


def _mostrar_pdf_relacionado(ruta_pdf, clave_unica="relacion"):
    """Muestra páginas de un PDF local y permite descargar el documento."""
    try:
        with open(ruta_pdf, "rb") as archivo:
            pdf_bytes = archivo.read()
        documento = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        if len(documento) == 0:
            st.warning("El PDF no contiene páginas legibles.")
            return
        st.caption(f"Archivo: {os.path.basename(ruta_pdf)} · {len(documento)} página(s)")
        pagina_num = st.number_input(
            "Página del oficio que desea visualizar",
            min_value=1,
            max_value=len(documento),
            value=1,
            step=1,
            key=f"pagina_pdf_{clave_unica}_{os.path.basename(ruta_pdf)}",
        )
        pagina = documento.load_page(int(pagina_num) - 1)
        pix = pagina.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
        st.image(pix.tobytes("png"), caption=f"Página {pagina_num} de {len(documento)}", use_container_width=True)
        st.download_button(
            "📥 Descargar PDF relacionado",
            data=pdf_bytes,
            file_name=os.path.basename(ruta_pdf),
            mime="application/pdf",
            key=f"descargar_pdf_{clave_unica}_{os.path.basename(ruta_pdf)}",
            use_container_width=True,
        )
        documento.close()
    except Exception as exc:
        st.error(f"No se pudo abrir el PDF: {exc}")


with st.expander("📑 Relación de observaciones del CCT vs respuesta a oficios por Oficialía", expanded=False):
    st.markdown(
        "Consulta la relación creada entre **Observaciones / respuesta** y **Número de oficio**. "
        "Desde aquí puedes filtrar los registros, descargar el Excel y visualizar el PDF relacionado "
        "cuando el documento esté disponible dentro de la carpeta `PDF_UAdeC`."
    )
    ruta_relacion = os.path.join(os.path.dirname(os.path.abspath(__file__)), RELACION_OFICIOS_XLSX)
    if not os.path.exists(ruta_relacion):
        st.warning(
            f"No se encontró `{RELACION_OFICIOS_XLSX}` junto al programa. "
            "Copia ese archivo Excel en la misma carpeta que este script para habilitar la relación."
        )
        excel_subido = st.file_uploader(
            "O bien, carga el Excel de relación",
            type=["xlsx"],
            key="excel_relacion_oficios_subido",
        )
        if excel_subido is not None:
            try:
                libro_relacion = pd.ExcelFile(excel_subido)
                st.session_state["_excel_relacion_oficios_bytes"] = excel_subido.getvalue()
                st.session_state["_excel_relacion_oficios_nombre"] = excel_subido.name
                st.success("Excel cargado para esta sesión.")
            except Exception as exc:
                st.error(f"No se pudo leer el Excel: {exc}")
    else:
        try:
            with open(ruta_relacion, "rb") as archivo_excel:
                bytes_excel_relacion = archivo_excel.read()
            st.download_button(
                "📥 Descargar Excel: relación de observaciones y oficios",
                data=bytes_excel_relacion,
                file_name=RELACION_OFICIOS_XLSX,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="descargar_excel_relacion_oficios",
                use_container_width=True,
            )
            libro_relacion = pd.ExcelFile(io.BytesIO(bytes_excel_relacion))
        except Exception as exc:
            libro_relacion = None
            st.error(f"No se pudo abrir el Excel de relación: {exc}")

    # El Excel puede venir de la carpeta de trabajo o de una carga manual.
    if not os.path.exists(ruta_relacion) and st.session_state.get("_excel_relacion_oficios_bytes"):
        try:
            libro_relacion = pd.ExcelFile(io.BytesIO(st.session_state["_excel_relacion_oficios_bytes"]))
            st.download_button(
                "📥 Descargar Excel cargado",
                data=st.session_state["_excel_relacion_oficios_bytes"],
                file_name=st.session_state.get("_excel_relacion_oficios_nombre", RELACION_OFICIOS_XLSX),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="descargar_excel_relacion_oficios_cargado",
                use_container_width=True,
            )
        except Exception as exc:
            libro_relacion = None
            st.error(f"No se pudo procesar el Excel cargado: {exc}")

    if 'libro_relacion' in locals() and libro_relacion is not None:
        hojas = libro_relacion.sheet_names
        hoja_principal = next((h for h in hojas if _normalizar_nombre_archivo(h) == _normalizar_nombre_archivo("Relación cotejada")), hojas[0])
        try:
            df_relacion = pd.read_excel(libro_relacion, sheet_name=hoja_principal).fillna("")
            hoja_indice = next((h for h in hojas if _normalizar_nombre_archivo(h) == _normalizar_nombre_archivo("Índice de oficios")), None)
            df_indice = pd.read_excel(libro_relacion, sheet_name=hoja_indice).fillna("") if hoja_indice else pd.DataFrame()
            st.caption(f"Registros de la relación: {len(df_relacion):,} · Hojas disponibles: {', '.join(hojas)}")

            # Filtros de consulta
            c_f1, c_f2 = st.columns(2)
            if "Dependencia" in df_relacion.columns:
                deps = sorted([str(x) for x in df_relacion["Dependencia"].unique() if str(x).strip()])
                with c_f1:
                    dependencia_sel = st.selectbox("Filtrar por dependencia", ["Todas"] + deps, key="filtro_relacion_dependencia")
            else:
                dependencia_sel = "Todas"
            if "Resultado del cotejo" in df_relacion.columns:
                estados = sorted([str(x) for x in df_relacion["Resultado del cotejo"].unique() if str(x).strip()])
                with c_f2:
                    estado_sel = st.selectbox("Filtrar por resultado", ["Todos"] + estados, key="filtro_relacion_estado")
            else:
                estado_sel = "Todos"

            df_vista = df_relacion.copy()
            if dependencia_sel != "Todas" and "Dependencia" in df_vista.columns:
                df_vista = df_vista[df_vista["Dependencia"].astype(str) == dependencia_sel]
            if estado_sel != "Todos" and "Resultado del cotejo" in df_vista.columns:
                df_vista = df_vista[df_vista["Resultado del cotejo"].astype(str) == estado_sel]

            texto_busqueda = st.text_input(
                "Buscar por observación, nombre de archivo, número de oficio o fecha",
                key="busqueda_texto_relacion_oficios",
                placeholder="Ej. 1087/OM/2026, nombre de persona, vacante...",
            )
            if texto_busqueda.strip():
                termino = texto_busqueda.strip().casefold()
                mascara = df_vista.astype(str).apply(
                    lambda col: col.str.casefold().str.contains(re.escape(termino), na=False)
                ).any(axis=1)
                df_vista = df_vista[mascara]

            st.dataframe(df_vista, use_container_width=True, hide_index=True)

            st.markdown("#### 📄 Abrir el PDF correspondiente a un registro")
            if len(df_vista) > 0 and "Archivo PDF relacionado" in df_vista.columns:
                opciones = []
                for indice, fila in df_vista.iterrows():
                    nombre_pdf = str(fila.get("Archivo PDF relacionado", "")).strip()
                    numero_oficio = str(fila.get("Número de oficio (cotejando)", "")).strip()
                    observacion = str(fila.get("Observaciones / respuesta", "")).strip().replace("\n", " ")
                    if nombre_pdf and nombre_pdf.lower() not in {"nan", "none"}:
                        etiqueta = f"{numero_oficio or 'Sin número'} | {nombre_pdf} | {observacion[:100]}"
                        opciones.append((etiqueta, nombre_pdf, numero_oficio, indice))
                if opciones:
                    etiqueta_sel = st.selectbox(
                        "Selecciona el oficio relacionado",
                        [x[0] for x in opciones],
                        key="selector_pdf_relacion_observaciones",
                    )
                    elegido = next(x for x in opciones if x[0] == etiqueta_sel)
                    _, nombre_pdf_sel, numero_oficio_sel, indice_sel = elegido
                    fila_sel = df_vista.loc[indice_sel]
                    st.write(f"**Número de oficio:** {numero_oficio_sel or 'No identificado'}")
                    st.write(f"**Observación / respuesta:** {fila_sel.get('Observaciones / respuesta', '')}")
                    ruta_pdf_sel = _buscar_pdf_relacionado(nombre_pdf_sel)
                    if ruta_pdf_sel:
                        _mostrar_pdf_relacionado(ruta_pdf_sel, clave_unica=str(indice_sel))
                    else:
                        st.info(
                            f"El archivo `{nombre_pdf_sel}` aparece en el Excel, pero no se localizó en `PDF_UAdeC`. "
                            "Copia el PDF a esa carpeta o cárgalo abajo para visualizarlo."
                        )
                        pdf_subido = st.file_uploader(
                            "Cargar el PDF de este oficio",
                            type=["pdf"],
                            key=f"pdf_subido_relacion_{indice_sel}",
                        )
                        if pdf_subido is not None:
                            try:
                                doc_subido = pymupdf.open(stream=pdf_subido.getvalue(), filetype="pdf")
                                if len(doc_subido):
                                    pagina_subida = st.number_input(
                                        "Página del PDF cargado", min_value=1, max_value=len(doc_subido),
                                        value=1, step=1, key=f"pagina_pdf_subido_{indice_sel}"
                                    )
                                    pix_subido = doc_subido.load_page(int(pagina_subida)-1).get_pixmap(
                                        matrix=pymupdf.Matrix(1.5, 1.5), alpha=False
                                    )
                                    st.image(pix_subido.tobytes("png"), caption=f"{pdf_subido.name} · página {pagina_subida}", use_container_width=True)
                                    st.download_button(
                                        "📥 Descargar PDF cargado", data=pdf_subido.getvalue(),
                                        file_name=pdf_subido.name, mime="application/pdf",
                                        key=f"descargar_pdf_subido_{indice_sel}", use_container_width=True
                                    )
                                else:
                                    st.warning("El PDF cargado no contiene páginas.")
                            except Exception as exc:
                                st.error(f"No se pudo visualizar el PDF cargado: {exc}")
                else:
                    st.info("Los registros visibles no tienen un nombre de PDF relacionado. Prueba otro filtro o revisa la hoja Índice de oficios.")

            with st.expander("Consultar índice completo de oficios"):
                if not df_indice.empty:
                    st.dataframe(df_indice, use_container_width=True, hide_index=True)
                else:
                    st.info("El libro no contiene una hoja 'Índice de oficios'.")
            if "Notas del cotejo" in hojas:
                with st.expander("Notas y criterios del cotejo"):
                    df_notas = pd.read_excel(libro_relacion, sheet_name="Notas del cotejo").fillna("")
                    st.dataframe(df_notas, use_container_width=True, hide_index=True)
        except Exception as exc:
            st.error(f"Ocurrió un error al mostrar la relación de observaciones y oficios: {exc}")


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


def _normalizar_busqueda_flexible(valor):
    """Normaliza texto para búsqueda tipo filtro de Excel: contiene,
    sin distinguir mayúsculas/minúsculas, acentos ni puntuación sobrante."""
    import unicodedata

    texto = str(valor or "").casefold()
    # Une palabras partidas por guion al final de una línea (p. ej.
    # "administra-\nción" -> "administración"), habitual en PDF de texto.
    texto = re.sub(r"(?<=[a-záéíóúüñ])[-‐‑]\s*\n\s*(?=[a-záéíóúüñ])", "", texto)
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    # La puntuación se trata como separador; conserva letras y números.
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _coincidencias_flexibles_en_pagina(page, term):
    """Devuelve rectángulos de líneas coincidentes cuando PyMuPDF no
    encuentra el texto literal (por acentos, mayúsculas o saltos de línea)."""
    consulta = _normalizar_busqueda_flexible(term)
    if not consulta:
        return []

    lineas = []
    try:
        datos = page.get_text("dict") or {}
        for bloque in datos.get("blocks", []):
            if bloque.get("type") != 0:
                continue
            for linea in bloque.get("lines", []):
                spans = linea.get("spans", [])
                texto_linea = "".join(str(sp.get("text", "")) for sp in spans)
                cajas = [sp.get("bbox") for sp in spans if sp.get("bbox")]
                if texto_linea.strip() and cajas:
                    rect = pymupdf.Rect(
                        min(c[0] for c in cajas), min(c[1] for c in cajas),
                        max(c[2] for c in cajas), max(c[3] for c in cajas)
                    )
                    lineas.append((texto_linea, rect))
    except Exception:
        return []

    texto_pagina = _normalizar_busqueda_flexible(page.get_text() or "")
    if consulta not in texto_pagina:
        return []

    # Si la frase cabe en una línea, se marca esa línea. Si está partida
    # por un salto de línea, se marcan las líneas que contienen sus palabras.
    exactas = [r for t, r in lineas if consulta in _normalizar_busqueda_flexible(t)]
    if exactas:
        return exactas

    palabras = [w for w in consulta.split() if len(w) > 1]
    seleccionadas = []
    for texto_linea, rect in lineas:
        normal = _normalizar_busqueda_flexible(texto_linea)
        if any(palabra in normal for palabra in palabras):
            seleccionadas.append(rect)
    return seleccionadas


def search_quads(page, term):
    """Búsqueda literal y flexible; la flexible permite acentos/case distintos."""
    qs = []
    variantes = dict.fromkeys([term, str(term).upper(), str(term).lower(), str(term).title()])

    for variante in variantes:
        try:
            for q in page.search_for(variante, quads=True):
                if not any(
                    abs(x.rect.x0 - q.rect.x0) < 1 and abs(x.rect.y0 - q.rect.y0) < 1
                    for x in qs
                ):
                    qs.append(q)
        except Exception:
            pass

    # Respaldo: si el texto literal no aparece, marca las líneas detectadas
    # mediante la comparación normalizada sin acentos ni distinción de caso.
    if not qs:
        for rect in _coincidencias_flexibles_en_pagina(page, term):
            try:
                quad = pymupdf.Quad(rect.tl, rect.tr, rect.bl, rect.br)
                if not any(
                    abs(x.rect.x0 - quad.rect.x0) < 1 and abs(x.rect.y0 - quad.rect.y0) < 1
                    for x in qs
                ):
                    qs.append(quad)
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
        rects_pdf = [q.rect for q in search_quads(page, termino)]
        if not rects_pdf:
            rects_pdf = _coincidencias_flexibles_en_pagina(page, termino)
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

def interactive_image(path, height=650):
    """Muestra una imagen con controles de zoom y apertura fiable en otra pestaña."""
    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")

        data_url = f"data:image/png;base64,{b64}"
        html = rf"""
        <!doctype html>
        <html lang="es">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5, user-scalable=yes, viewport-fit=cover">
          <style>
            * {{ box-sizing: border-box; }}
            html, body {{ margin:0; padding:0; width:100%; background:#f5f7fa; color:#17212b; font-family:Arial,sans-serif; }}
            .toolbar {{ display:flex; flex-wrap:wrap; gap:8px; justify-content:center; padding:8px; position:sticky; top:0; z-index:2; background:#f5f7fa; }}
            button {{ border:0; border-radius:9px; padding:11px 14px; min-height:42px; font-size:15px; font-weight:700; color:white; background:#174a7e; cursor:pointer; touch-action:manipulation; }}
            button.secondary {{ background:#425466; }}
            .viewport {{ width:100%; overflow:auto; -webkit-overflow-scrolling:touch; padding:4px; text-align:center; }}
            #page {{ display:inline-block; transform-origin:top center; max-width:none; width:100%; height:auto; box-shadow:0 2px 10px #0002; }}
            .note {{ text-align:center; padding:4px 10px 12px; font-size:13px; line-height:1.4; }}
          </style>
        </head>
        <body>
          <div class="toolbar">
            <button type="button" onclick="zoom(1.25)">＋ Acercar</button>
            <button type="button" onclick="zoom(0.8)">− Alejar</button>
            <button type="button" class="secondary" onclick="resetZoom()">Restablecer</button>
            <button type="button" onclick="openFullImage()">Abrir imagen en nueva pestaña</button>
          </div>
          <div class="viewport" id="viewport"><img id="page" src="{data_url}" alt="Página del documento"></div>
          <div class="note">Puedes acercar con los botones o usar dos dedos en la pantalla. Al ampliar, desplázate horizontal y verticalmente para revisar el documento.</div>
          <script>
            let scale = 1;
            const page = document.getElementById('page');
            function applyZoom() {{
              page.style.width = (100 * scale) + '%';
              page.style.maxWidth = 'none';
            }}
            function zoom(factor) {{ scale = Math.max(0.5, Math.min(5, scale * factor)); applyZoom(); }}
            function resetZoom() {{ scale = 1; applyZoom(); document.getElementById('viewport').scrollTo(0,0); }}
            function openFullImage() {{
              // Blob URL evita la navegación directa a una data URL, que algunos navegadores bloquean.
              const imageData = '{data_url}';
              const pageHtml = `<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5, user-scalable=yes"><title>Página del documento</title><style>html,body{{margin:0;padding:0;background:#20252b;color:white;font-family:Arial,sans-serif}}.bar{{position:sticky;top:0;background:#20252b;padding:8px;display:flex;gap:8px;justify-content:center;flex-wrap:wrap}}button{{padding:10px 14px;border:0;border-radius:8px;background:#1769aa;color:white;font-size:16px}}.area{{overflow:auto;width:100%;height:calc(100vh - 58px);touch-action:pan-x pan-y pinch-zoom}}img{{display:block;width:100%;height:auto;transform-origin:top left}}#status{{font-size:13px;align-self:center}}</style></head><body><div class="bar"><button onclick="z(1.25)">＋</button><button onclick="z(.8)">−</button><button onclick="r()">Restablecer</button><span id="status">Zoom: 100%</span></div><div class="area" id="area"><img id="im" src="${{imageData}}" alt="Página del documento"></div><script>let s=1;const im=document.getElementById('im');function paint(){{im.style.width=(100*s)+'%';document.getElementById('status').textContent='Zoom: '+Math.round(s*100)+'%'}}function z(f){{s=Math.max(.5,Math.min(5,s*f));paint()}}function r(){{s=1;paint();document.getElementById('area').scrollTo(0,0)}}<\/script></body></html>`;
              const blob = new Blob([pageHtml], {{type:'text/html;charset=utf-8'}});
              const url = URL.createObjectURL(blob);
              const tab = window.open(url, '_blank');
              if (!tab) {{
                // Respaldo si el navegador bloquea ventanas emergentes.
                const a = document.createElement('a'); a.href = imageData; a.download = 'pagina_documento.png'; a.click();
              }}
            }}
          </script>
        </body>
        </html>
        """
        components.html(html, height=height, scrolling=True)
    except Exception as e:
        st.warning(f"No se pudo mostrar la imagen interactiva: {e}")


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
        r"RESCISI[ÓO]N\s+DE",
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
# ACCESO A REPOSITORIO PRIVADO DE GITHUB (SOLO LECTURA)
# ==========================================================
GITHUB_OWNER_DEFAULT = "STUAC-2026"
GITHUB_REPO_DEFAULT = "CARPETA"
GITHUB_BRANCH_DEFAULT = "main"

def _github_config():
    """Lee credenciales desde st.secrets; nunca solicita ni imprime el token."""
    try:
        cfg = st.secrets.get("github", {})
        token = cfg.get("token", "") if hasattr(cfg, "get") else ""
        owner = cfg.get("owner", GITHUB_OWNER_DEFAULT) if hasattr(cfg, "get") else GITHUB_OWNER_DEFAULT
        repo = cfg.get("repo", GITHUB_REPO_DEFAULT) if hasattr(cfg, "get") else GITHUB_REPO_DEFAULT
        branch = cfg.get("branch", GITHUB_BRANCH_DEFAULT) if hasattr(cfg, "get") else GITHUB_BRANCH_DEFAULT
        folder = cfg.get("pdf_folder", "") if hasattr(cfg, "get") else ""
    except Exception:
        token, owner, repo, branch, folder = "", GITHUB_OWNER_DEFAULT, GITHUB_REPO_DEFAULT, GITHUB_BRANCH_DEFAULT, ""
    return str(token).strip(), str(owner).strip(), str(repo).strip(), str(branch).strip(), str(folder).strip().strip("/")

@st.cache_data(show_spinner=False, ttl=300)
def _github_listar_pdfs(owner, repo, branch, folder, token):
    """Obtiene el árbol recursivo y devuelve PDF de la carpeta configurada."""
    api = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}"
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "STUAC-INFORMA"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(api, params={"recursive": "1"}, headers=headers, timeout=60)
    if r.status_code == 401:
        raise RuntimeError("GitHub rechazó la autenticación (401). Revisa el token guardado en los secretos de Streamlit.")
    if r.status_code == 403:
        raise RuntimeError("GitHub denegó el acceso (403). Verifica que el token tenga permiso Contents: Read para CARPETA.")
    if r.status_code == 404:
        raise RuntimeError("No se encontró el repositorio, la rama o no tienes acceso. Confirma owner, repo, branch y permisos.")
    r.raise_for_status()
    data = r.json()
    if data.get("truncated"):
        raise RuntimeError("GitHub devolvió un árbol truncado. Reduce la carpeta configurada en github.pdf_folder.")
    prefijo = folder + "/" if folder else ""
    encontrados = {}
    for item in data.get("tree", []):
        ruta = item.get("path", "")
        if item.get("type") == "blob" and ruta.lower().endswith(".pdf") and ruta.startswith(prefijo):
            nombre = ruta.rsplit("/", 1)[-1]
            # Mantener la ruta completa en la etiqueta para evitar nombres duplicados.
            etiqueta = ruta
            encontrados[etiqueta] = "github://" + ruta
    return encontrados


def _github_descargar_pdf(ruta_repo, token, owner=None, repo=None, branch=None):
    """Descarga bytes PDF desde Contents API usando token de lectura."""
    if not all([owner, repo, branch]):
        _, owner, repo, branch, _ = _github_config()
    ruta = ruta_repo[len("github://"):].lstrip("/")
    api = f"https://api.github.com/repos/{owner}/{repo}/contents/{requests.utils.quote(ruta, safe='/')}"
    headers = {"Accept": "application/vnd.github.raw+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "STUAC-INFORMA"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(api, params={"ref": branch}, headers=headers, timeout=120)
    if r.status_code in (401, 403, 404):
        raise RuntimeError(f"No fue posible descargar {ruta}. HTTP {r.status_code}; revisa token, permiso Contents: Read y ruta del archivo.")
    r.raise_for_status()
    if not r.content.startswith(b"%PDF"):
        raise ValueError(f"El archivo {ruta} no se recibió como PDF válido.")
    return r.content


def _cargar_pdf_github(nombre, identificador):
    """Guarda el PDF privado en caché local para usar el mismo motor de búsqueda."""
    token, owner, repo, branch, _ = _github_config()
    if not token:
        raise RuntimeError("Falta el token de GitHub. Configúralo en .streamlit/secrets.toml; no lo escribas en el código.")
    ruta = os.path.join(PDF_DIR, "GITHUB_" + safe(nombre) + ".pdf")
    # Descargar nuevamente al iniciar cada búsqueda para no reutilizar una
    # copia local desactualizada si el PDF cambió en GitHub.
    contenido = _github_descargar_pdf(identificador, token, owner, repo, branch)
    with open(ruta, "wb") as f:
        f.write(contenido)
    return ruta


def _extraer_texto_ocr_y_crear_capa(page):
    """
    Reconoce texto en páginas escaneadas y lo inserta como capa invisible
    dentro de la página PDF en memoria. Esto permite que:
      - el motor de búsqueda lea el texto reconocido;
      - search_for/save_marked localicen y resalten las palabras OCR;
      - los reportes conserven el número de página y la imagen original.
    Devuelve el texto OCR. No modifica el archivo original de GitHub.
    """
    if not OCR_DISPONIBLE or pytesseract is None or Image is None:
        raise RuntimeError(
            "OCR no disponible: instala pytesseract y Pillow, además de Tesseract."
        )

    pix = page.get_pixmap(matrix=pymupdf.Matrix(2.5, 2.5), alpha=False)
    imagen = Image.open(BytesIO(pix.tobytes("png"))).convert("RGB")

    try:
        idiomas = pytesseract.get_languages(config="")
    except Exception:
        idiomas = []

    idioma = "spa" if "spa" in idiomas else ("eng" if "eng" in idiomas else None)
    if not idioma:
        raise RuntimeError(
            "Tesseract está instalado, pero no tiene instalado el idioma español (spa) ni inglés (eng)."
        )

    datos = pytesseract.image_to_data(
        imagen,
        lang=idioma,
        config="--oem 3 --psm 6",
        output_type=pytesseract.Output.DICT
    )

    escala_x = pix.width / float(page.rect.width)
    escala_y = pix.height / float(page.rect.height)
    lineas = {}

    for i, palabra in enumerate(datos.get("text", [])):
        palabra = str(palabra or "").strip()
        if not palabra:
            continue

        try:
            confianza = float(datos["conf"][i])
        except Exception:
            confianza = 0.0
        if confianza < 20:
            continue

        clave = (
            datos["block_num"][i],
            datos["par_num"][i],
            datos["line_num"][i]
        )
        x = int(datos["left"][i])
        y = int(datos["top"][i])
        w = int(datos["width"][i])
        h = int(datos["height"][i])

        item = lineas.setdefault(
            clave,
            {"palabras": [], "x0": x, "y0": y, "x1": x + w, "y1": y + h}
        )
        item["palabras"].append((int(datos.get("word_num", [i])[i]), palabra))
        item["x0"] = min(item["x0"], x)
        item["y0"] = min(item["y0"], y)
        item["x1"] = max(item["x1"], x + w)
        item["y1"] = max(item["y1"], y + h)

    textos = []
    insertadas = 0

    for item in lineas.values():
        texto_linea = " ".join(
            palabra for _, palabra in sorted(item["palabras"], key=lambda x: x[0])
        ).strip()
        if not texto_linea:
            continue

        x0 = item["x0"] / escala_x
        y0 = item["y0"] / escala_y
        x1 = item["x1"] / escala_x
        y1 = item["y1"] / escala_y
        alto = max(5.0, (y1 - y0) * 0.78)
        tamano = max(5.0, min(16.0, alto))

        # render_mode=3 agrega texto invisible: no tapa la imagen escaneada.
        page.insert_text(
            (x0, max(y0 + tamano, y1 - 1.0)),
            texto_linea,
            fontsize=tamano,
            fontname="helv",
            render_mode=3,
            overlay=True
        )
        textos.append(texto_linea)
        insertadas += 1

    if not insertadas:
        raise RuntimeError(
            "Tesseract no pudo reconocer texto con confianza suficiente en esta página."
        )

    return "\n".join(textos)


def _extraer_texto_pagina_robusto(page):
    """
    Primero intenta extraer la capa de texto nativa. Si no existe,
    intenta OCR y crea una capa invisible para permitir búsquedas y resaltados.
    """
    errores = []
    for modo in ("text", "blocks"):
        try:
            if modo == "text":
                texto = page.get_text("text", sort=True) or page.get_text() or ""
            else:
                bloques = page.get_text("blocks") or []
                texto = "\n".join(
                    str(b[4]) for b in bloques
                    if len(b) > 4 and str(b[4]).strip()
                )
            texto = str(texto).replace("\x00", "").strip()
            if texto:
                return texto, "texto nativo", ""
        except Exception as exc:
            errores.append(f"Extracción {modo}: {type(exc).__name__}: {exc}")

    try:
        texto_ocr = _extraer_texto_ocr_y_crear_capa(page)
        # Recuperar desde la página ya enriquecida, para que el motor
        # normalizado y los resaltados trabajen sobre la misma capa.
        texto_capa = str(page.get_text("text", sort=True) or "").strip()
        return (texto_capa or texto_ocr), "OCR", ""
    except Exception as exc:
        errores.append(f"OCR: {type(exc).__name__}: {exc}")
        return "", "sin texto", " | ".join(errores)


# ==========================================================
# REPOSITORIO LOCAL DE PDF
# ==========================================================
REPOSITORIO_LOCAL_DEFAULT = "REPOSITORIO_LOCAL"

def _ruta_repositorio_local():
    """Resuelve REPOSITORIO_LOCAL junto al programa (o desde el directorio actual)."""
    base = os.path.dirname(os.path.abspath(__file__))
    candidatos = [os.path.join(base, REPOSITORIO_LOCAL_DEFAULT),
                  os.path.abspath(REPOSITORIO_LOCAL_DEFAULT)]
    for ruta in candidatos:
        if os.path.isdir(ruta):
            return ruta
    # Devuelve la ubicación esperada junto al programa para mostrarla al usuario.
    return candidatos[0]

def _listar_pdfs_repositorio_local():
    """Lista recursivamente todos los PDF de REPOSITORIO_LOCAL."""
    raiz = _ruta_repositorio_local()
    encontrados = {}
    if not os.path.isdir(raiz):
        return raiz, encontrados
    for carpeta, dirs, archivos in os.walk(raiz):
        dirs.sort()
        for archivo in sorted(archivos):
            if archivo.lower().endswith('.pdf'):
                ruta = os.path.join(carpeta, archivo)
                relativa = os.path.relpath(ruta, raiz)
                encontrados[relativa] = ruta
    return raiz, encontrados


# ==========================================================
# TIPO DE BÚSQUEDA
# ==========================================================

st.subheader(
    "🔎 Tipo de búsqueda"
)

kind = st.radio(
    "SELECCIONE QUE DESEA BUSCAR:",

    [
        "Persona",
        "Expediente",
        "Vacante",
        "Palabra o frase",
        "📄 Referencia de oficio",
        "📅 Número y fecha de oficio"
    ],

    horizontal=True
)

# Origen documental adicional: mantiene intactos los tipos de búsqueda y
# cambia únicamente el conjunto de PDFs que alimenta el mismo motor de análisis.
fuente_documentos = st.radio(
    "📂 ORIGEN DE LOS DOCUMENTOS:",
    ["Documentos UAdeC (actuales)", "PDF en repositorio privado", "PDF en repositorio local"],
    horizontal=True,
    key="origen_documentos_busqueda"
)


# ==========================================================
# EXTRAER NÚMERO Y FECHA DE OFICIO
# ==========================================================

if kind == "📅 Número y fecha de oficio":

    st.info(
        "Suba uno o varios oficios en PDF. El programa revisará el texto "
        "de cada documento y, cuando sea necesario, intentará leer páginas "
        "escaneadas mediante OCR para localizar el número de oficio y la fecha. "
        "Revise los campos marcados como 'No identificado', porque el diseño "
        "del documento o la calidad del escaneo pueden afectar la extracción."
    )

    archivos_num_fecha = st.file_uploader(
        "📎 Seleccione uno o varios oficios PDF",
        type=["pdf"],
        accept_multiple_files=True,
        key="subir_oficios_numero_fecha"
    )

    procesar_num_fecha = st.button(
        "📅 EXTRAER NÚMERO Y FECHA",
        type="primary",
        use_container_width=True,
        disabled=not archivos_num_fecha
    )

    if procesar_num_fecha:
        resultados_num_fecha = []

        patron_fecha = re.compile(
            r"\b(?:\d{1,2}\s+de\s+"
            r"(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
            r"septiembre|setiembre|octubre|noviembre|diciembre)\s+de\s+\d{4}"
            r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
            re.IGNORECASE
        )
        patron_numero = re.compile(
            r"\b(?:N[ÚU]M(?:ERO)?\.?\s+DE\s+OFICIO|"
            r"OFICIO\s*(?:(?:N[ÚU]M(?:ERO)?\.?|NO\.?|N[º°]|#)\s*)?|"
            r"OF\.?\s*(?:NO\.?|N[ÚU]M(?:ERO)?\.?)?\s*|"
            r"N[ÚU]M(?:ERO)?\.?|NO\.?|N[º°])"
            r"\s*[:#\-]?\s*"
            r"([A-ZÁÉÍÓÚÑ0-9][A-ZÁÉÍÓÚÑ0-9./_-]{1,})",
            re.IGNORECASE
        )

        for archivo_subido in archivos_num_fecha:
            st.write(f"**Procesando:** {archivo_subido.name}")
            progreso = st.progress(0)
            ruta_temporal = os.path.join(
                "Resultados_UAdeC", "_num_fecha_" + safe(archivo_subido.name)
            )
            try:
                with open(ruta_temporal, "wb") as f:
                    f.write(archivo_subido.getvalue())

                documento = pymupdf.open(ruta_temporal)
                numero_oficio = ""
                fecha_oficio = ""
                pagina_numero = ""
                pagina_fecha = ""
                metodos = []
                paginas_cuerpo_texto = []
                total_paginas = max(len(documento), 1)

                for indice, pagina in enumerate(documento):
                    texto = pagina.get_text("text") or ""
                    texto_ocr = ""
                    metodo = "Texto PDF"

                    def localizar_campos(contenido):
                        """Usa la misma extracción de REFERENCIA DE OFICIO:
                        NUMERACION y LUGAR Y FECHA. Los patrones anteriores quedan
                        como respaldo para formatos que no reconozca esa extracción.
                        """
                        lineas = [
                            re.sub(r"\s+", " ", x).strip()
                            for x in contenido.splitlines() if x.strip()
                        ]
                        num = ""
                        fecha = ""
                        pnum = ""
                        pfecha = ""

                        partes = extraer_partes_oficio(contenido)
                        num = str(partes.get("NUMERACION", "") or "").strip()
                        fecha = str(partes.get("LUGAR Y FECHA", "") or "").strip()

                        # Respaldo: conserva búsqueda flexible si el formato del
                        # encabezado no coincide con los patrones NUMERACION/FECHA.
                        for linea in lineas:
                            if not num:
                                mnum = patron_numero.search(linea)
                                if mnum:
                                    candidato = mnum.group(1).strip(" .,:;#-")
                                    if candidato and not re.fullmatch(
                                        r"(?:DIRIGIDO|ENVIADO|ELABORADO|SUSCRITO|CORRESPONDIENTE)",
                                        candidato, re.I
                                    ):
                                        num = candidato
                            if not fecha:
                                mf = patron_fecha.search(linea)
                                if mf:
                                    fecha = linea if re.search(
                                        r"\b(?:Saltillo|Torre[oó]n|Monclova|Piedras\s+Negras|Acu[nñ]a)\b",
                                        linea, re.I
                                    ) else mf.group(0).strip()

                        if num:
                            pnum = str(indice + 1)
                        if fecha:
                            pfecha = str(indice + 1)
                        return num, fecha, pnum, pfecha

                    num_p, fecha_p, pnum_p, pfecha_p = localizar_campos(texto)

                    # En PDFs escaneados o si falta alguno de los campos, aplicar OCR.
                    if (len(texto.strip()) < 25 or not num_p or not fecha_p) and OCR_DISPONIBLE:
                        try:
                            pix = pagina.get_pixmap(matrix=pymupdf.Matrix(3, 3), alpha=False)
                            imagen = Image.open(io.BytesIO(pix.tobytes("png")))
                            try:
                                texto_ocr = pytesseract.image_to_string(imagen, lang="spa", config="--psm 11")
                            except Exception:
                                texto_ocr = pytesseract.image_to_string(imagen, lang="eng", config="--psm 11")
                            num_ocr, fecha_ocr, pnum_ocr, pfecha_ocr = localizar_campos(texto_ocr)
                            if not num_p and num_ocr:
                                num_p, pnum_p = num_ocr, pnum_ocr
                            if not fecha_p and fecha_ocr:
                                fecha_p, pfecha_p = fecha_ocr, pfecha_ocr
                            if num_ocr or fecha_ocr:
                                metodo = "Texto PDF + OCR" if texto.strip() else "OCR"
                        except Exception:
                            pass

                    # Para el cuerpo del texto, preferir el texto nativo del PDF.
                    # En páginas escaneadas sin capa de texto, conservar el resultado OCR.
                    texto_cuerpo_pagina = texto.strip() or texto_ocr.strip()
                    if texto_cuerpo_pagina:
                        paginas_cuerpo_texto.append(
                            f"--- PÁGINA {indice + 1} ---\n{texto_cuerpo_pagina}"
                        )
                    else:
                        paginas_cuerpo_texto.append(
                            f"--- PÁGINA {indice + 1} ---\n[No se pudo extraer texto de esta página]"
                        )

                    if not numero_oficio and num_p:
                        numero_oficio, pagina_numero = num_p, pnum_p
                    if not fecha_oficio and fecha_p:
                        fecha_oficio, pagina_fecha = fecha_p, pfecha_p
                    if metodo not in metodos:
                        metodos.append(metodo)
                    progreso.progress((indice + 1) / total_paginas)
                    if numero_oficio and fecha_oficio:
                        # Se sigue hasta completar la revisión de progreso, pero no se sobreescriben los primeros datos encontrados.
                        pass

                documento.close()
                resultados_num_fecha.append({
                    "ARCHIVO PDF": archivo_subido.name,
                    "NÚMERO DE OFICIO": numero_oficio or "No identificado",
                    "FECHA": fecha_oficio or "No identificada",
                    "CUERPO DEL TEXTO": "\\n\\n".join(paginas_cuerpo_texto).strip()
                })
            except Exception as error:
                resultados_num_fecha.append({
                    "ARCHIVO PDF": archivo_subido.name,
                    "NÚMERO DE OFICIO": "Error de lectura",
                    "FECHA": "Error de lectura",
                    "CUERPO DEL TEXTO": f"No fue posible extraer el cuerpo del texto: {error}"
                })
            finally:
                progreso.empty()

        if resultados_num_fecha:
            st.divider()
            st.subheader("📋 Número y fecha identificados")
            df_num_fecha = pd.DataFrame(resultados_num_fecha)
            st.dataframe(df_num_fecha, use_container_width=True, hide_index=True)

            salida_excel = io.BytesIO()
            with pd.ExcelWriter(salida_excel, engine="openpyxl") as writer:
                df_num_fecha.to_excel(writer, index=False, sheet_name="Numero y fecha")
            st.download_button(
                "📥 Descargar reporte en Excel",
                data=salida_excel.getvalue(),
                file_name="reporte_numero_y_fecha_oficios.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            st.caption(
                "El reporte contiene únicamente el archivo PDF, número de oficio, fecha y cuerpo del texto. "
                "El cuerpo se extrae de la capa de texto del PDF o mediante OCR en páginas escaneadas; "
                "puede requerir revisión manual si el documento tiene sellos, baja resolución o texto manuscrito."
            )

    st.divider()
    st.stop()


# ==========================================================
# REFERENCIA DE OFICIO
# ==========================================================

def _extraer_registro_completo_oficio(pdf_path, nombre_archivo):
    """Extrae los seis campos del reporte desde todas las páginas de un PDF.
    Usa texto nativo y OCR como respaldo; conserva una fila por archivo incluso
    cuando algún campo no pueda identificarse.
    """
    partes_texto = []
    metodos = []
    errores = []
    with pymupdf.open(pdf_path) as doc:
        total_paginas = len(doc)
        for numero_pagina, pagina in enumerate(doc, start=1):
            texto, metodo, error = _extraer_texto_pagina_robusto(pagina)
            texto = str(texto or "").replace("\x00", "").strip()
            if texto:
                partes_texto.append(f"\n[ PÁGINA {numero_pagina} ]\n{texto}")
                metodos.append(metodo)
            elif error:
                errores.append(f"Página {numero_pagina}: {error}")
    texto_completo = "\n".join(partes_texto).strip()
    campos = extraer_partes_oficio(texto_completo) if texto_completo else {}
    nombre, referencia = extraer_nombre_de_referencia(texto_completo)
    # La referencia puede continuar en renglones con escuela/unidad/destinatario.
    # Se conserva sólo el concepto y el nombre antes de esos datos accesorios.
    referencia_limpia = re.split(
        r"\b(?:ESCUELA\s+DE\s+|UNIDAD\s+(?:LAGUNA|SURESTE|NORTE|TORRE[ÓO]N)|SECRETAR[IÍ]A\s+GENERAL|PRESENTE|A\s+FIN\s+DE)\b",
        str(referencia or ""), maxsplit=1, flags=re.IGNORECASE
    )[0].strip(" \t\r\n.-:,;")
    # NOMBRE debe contener sólo la persona, no el concepto administrativo.
    nombre = extraer_nombre_exclusivo(nombre or referencia_limpia)
    # Elimina cualquier resto de líneas de encabezado que el OCR haya unido.
    nombre = re.split(
        r"\b(?:ESCUELA\s+DE\s+|UNIDAD\s+(?:LAGUNA|SURESTE|NORTE|TORRE[ÓO]N)|SECRETAR[IÍ]A\s+GENERAL|PRESENTE|A\s+FIN\s+DE)\b",
        nombre, maxsplit=1, flags=re.IGNORECASE
    )[0].strip(" \t\r\n.-:,;")
    # Si no se detectó REFERENCIA, intenta recuperar un nombre de encabezado
    # habitual sin inventar datos.
    if not nombre:
        m_nombre = re.search(
            r"(?:A|PARA)\s+\n?([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ]+){1,5})",
            texto_completo
        )
        if m_nombre:
            nombre = m_nombre.group(1).strip()
    return {
        "OFICIO": nombre_archivo,
        "NOMBRE": nombre,
        "LUGAR Y FECHA": campos.get("LUGAR Y FECHA", ""),
        "NUMERACION": campos.get("NUMERACION", ""),
        "ASUNTO O REFERENCIA": (
            re.split(r"\b(?:ESCUELA\s+DE\s+|UNIDAD\s+(?:LAGUNA|SURESTE|NORTE|TORRE[ÓO]N)|SECRETAR[IÍ]A\s+GENERAL|PRESENTE|A\s+FIN\s+DE)\b",
                     str(campos.get("ASUNTO O REFERENCIA", "") or referencia_limpia),
                     maxsplit=1, flags=re.IGNORECASE)[0].strip(" \t\r\n.-:,;")
        ),
        "CUERPO O TEXTO": campos.get("CUERPO O TEXTO", ""),
        "_PAGINAS": total_paginas,
        "_CARACTERES": len(texto_completo),
        "_METODO": ", ".join(sorted(set(metodos))) if metodos else "Sin texto",
        "_ERRORES": " | ".join(errores),
    }


if kind == "📄 Referencia de oficio":

    st.info(
        'Este modo permite extraer los datos principales de los oficios. '
        'Cuando el origen sea el repositorio privado de GitHub, podrá generar '
        'un reporte consolidado en Excel con todos los PDF del repositorio.'
    )

    if fuente_documentos in ("PDF en repositorio privado de GitHub", "PDF en repositorio privado") or fuente_documentos == "PDF en repositorio local":
        es_local = fuente_documentos == "PDF en repositorio local"
        st.subheader("📚 Reporte integral de referencias de oficio – Repositorio local" if es_local else "📚 Reporte integral de referencias de oficio – GitHub")
        accion_referencia = st.selectbox(
            "Seleccione la operación:",
            ["Seleccione una operación", "Presentar un reporte en Excel"],
            key="accion_referencia_github"
        )
        if es_local:
            st.caption("El reporte incluirá todos los PDF de REPOSITORIO_LOCAL y sus subcarpetas.")
            ruta_local_ref, pdfs_referencia_github = _listar_pdfs_repositorio_local()
            if not os.path.isdir(ruta_local_ref):
                st.error(f"No existe la carpeta REPOSITORIO_LOCAL: {ruta_local_ref}")
                st.stop()
            st.success(f"Se localizaron {len(pdfs_referencia_github)} archivos PDF en REPOSITORIO_LOCAL.")
        else:
            st.caption("El reporte Excel se construye con todos los archivos PDF encontrados en STUAC-2026/CARPETA, incluidas sus subcarpetas.")
            token_gh, owner_gh, repo_gh, branch_gh, folder_gh = _github_config()
            if not token_gh:
                st.error("No se encontró el token de GitHub. Configura [github].token en .streamlit/secrets.toml con permiso Contents: Read-only.")
                st.stop()
            try:
                with st.spinner("Consultando todos los PDF del repositorio privado..."):
                    pdfs_referencia_github = _github_listar_pdfs(owner_gh, repo_gh, branch_gh, folder_gh, token_gh)
                st.success(f"Se localizaron {len(pdfs_referencia_github)} archivos PDF en {owner_gh}/{repo_gh}.")
            except Exception as exc:
                st.error(f"No fue posible consultar el repositorio privado: {exc}")
                st.stop()

        if not pdfs_referencia_github:
            st.warning("El repositorio no contiene archivos PDF en la ruta configurada.")
            st.stop()

        if accion_referencia != "Presentar un reporte en Excel":
            st.info("Selecciona **Presentar un reporte en Excel** para continuar.")
            st.stop()

        generar_reporte_github = st.button(
            "📊 GENERAR REPORTE DE TODOS LOS OFICIOS EN EXCEL",
            type="primary",
            use_container_width=True,
            key="generar_reporte_integral_referencia_github"
        )
        if generar_reporte_github:
            registros = []
            errores_descarga = []
            barra = st.progress(0)
            estado = st.empty()
            for indice, (ruta_repo, identificador) in enumerate(pdfs_referencia_github.items(), start=1):
                estado.write(f"Procesando PDF {indice} de {len(pdfs_referencia_github)}: **{ruta_repo}**")
                try:
                    ruta_pdf = identificador if es_local else _cargar_pdf_github(ruta_repo, identificador)
                    registro = _extraer_registro_completo_oficio(ruta_pdf, ruta_repo)
                    registros.append(registro)
                except Exception as exc:
                    errores_descarga.append({"OFICIO": ruta_repo, "ERROR": f"{type(exc).__name__}: {exc}"})
                    registros.append({
                        "OFICIO": ruta_repo, "NOMBRE": "", "LUGAR Y FECHA": "",
                        "NUMERACION": "", "ASUNTO O REFERENCIA": "", "CUERPO O TEXTO": "",
                        "_PAGINAS": 0, "_CARACTERES": 0, "_METODO": "Error", "_ERRORES": str(exc)
                    })
                barra.progress(indice / len(pdfs_referencia_github))

            estado.empty()
            barra.empty()
            columnas_reporte = [
                "OFICIO", "NOMBRE", "LUGAR Y FECHA", "NUMERACION",
                "ASUNTO O REFERENCIA", "CUERPO O TEXTO"
            ]
            df_reporte = pd.DataFrame(registros)
            for columna in columnas_reporte:
                if columna not in df_reporte.columns:
                    df_reporte[columna] = ""
            df_reporte = df_reporte[columnas_reporte].fillna("")

            st.subheader("📋 Reporte consolidado de todos los PDF")
            st.caption(f"Archivos incluidos: {len(df_reporte)} · Filas con texto recuperado: {sum(1 for x in registros if x.get('_CARACTERES', 0) > 0)} · Archivos sin texto: {sum(1 for x in registros if x.get('_CARACTERES', 0) == 0)}")
            st.dataframe(df_reporte, use_container_width=True, hide_index=True)

            buffer_reporte = BytesIO()
            with pd.ExcelWriter(buffer_reporte, engine="openpyxl") as writer:
                df_reporte.to_excel(writer, index=False, sheet_name="REPORTE DE OFICIOS")
                df_diagnostico = pd.DataFrame([{
                    "OFICIO": x.get("OFICIO", ""),
                    "PÁGINAS": x.get("_PAGINAS", 0),
                    "CARACTERES EXTRAÍDOS": x.get("_CARACTERES", 0),
                    "MÉTODO DE LECTURA": x.get("_METODO", ""),
                    "OBSERVACIONES": x.get("_ERRORES", "")
                } for x in registros])
                df_diagnostico.to_excel(writer, index=False, sheet_name="DIAGNOSTICO")
                for hoja in writer.book.worksheets:
                    hoja.freeze_panes = "A2"
                    hoja.auto_filter.ref = hoja.dimensions
                    for columna in hoja.columns:
                        letra = columna[0].column_letter
                        max_len = max((len(str(c.value or "")) for c in columna), default=12)
                        hoja.column_dimensions[letra].width = min(max(max_len + 2, 14), 60)
                    for celda in hoja[1]:
                        celda.font = __import__("openpyxl").styles.Font(bold=True, color="FFFFFF")
                        celda.fill = __import__("openpyxl").styles.PatternFill("solid", fgColor="24476B")
            st.download_button(
                "📥 DESCARGAR REPORTE COMPLETO EN EXCEL",
                data=buffer_reporte.getvalue(),
                file_name=("REPORTE_INTEGRAL_OFICIOS_REPOSITORIO_LOCAL.xlsx" if es_local else f"REPORTE_INTEGRAL_OFICIOS_{owner_gh}_{repo_gh}.xlsx"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="descargar_reporte_integral_oficios_github"
            )
            if errores_descarga:
                with st.expander(f"⚠️ Ver archivos con errores ({len(errores_descarga)})"):
                    st.dataframe(pd.DataFrame(errores_descarga), use_container_width=True, hide_index=True)
            st.success("Reporte generado. Se incluyó una fila por cada PDF localizado, incluso cuando algún campo no pudo identificarse.")
        st.stop()

    # Flujo original para documentos locales: se conserva sin cambios.
    st.info(
        'Este modo permite subir uno o varios oficios PDF y obtener automáticamente '
        'el nombre de la persona que aparece después de "REFERENCIA:". '
        'Funciona también con PDFs escaneados mediante OCR.'
    )

    archivos_oficio = st.file_uploader(
        "📎 Seleccione uno o varios oficios PDF",
        type=["pdf"],
        accept_multiple_files=True
    )

    if archivos_oficio:
        ok_ocr, diagnostico = verificar_ocr()
        if not ok_ocr:
            st.warning("Para oficios escaneados se necesita OCR. " + diagnostico)
            st.code("pip install pytesseract pillow")
            st.code("brew install tesseract tesseract-lang")

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
            ruta_temporal = os.path.join("Resultados_UAdeC", "_oficio_" + safe(archivo_subido.name))
            with open(ruta_temporal, "wb") as f:
                f.write(archivo_subido.getvalue())
            st.write(f"**Procesando:** {archivo_subido.name}")
            progreso = st.progress(0)
            try:
                encontrados = ocr_pdf_referencia(ruta_temporal, progreso=progreso, nombre_oficio=archivo_subido.name)
                if encontrados:
                    for item in encontrados:
                        resultados_referencia.append({"OFICIO": archivo_subido.name, **item})
                        try:
                            with pymupdf.open(ruta_temporal) as doc_img:
                                pagina = doc_img[item["PAGINA"] - 1]
                                pix = pagina.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
                                nombre_img = f"Referencia_{safe(archivo_subido.name)}_pagina_{item['PAGINA']}.png"
                                ruta_img = os.path.join(IMG_DIR, nombre_img)
                                pix.save(ruta_img)
                                imagenes_referencia.append({"oficio": archivo_subido.name, "pagina": item["PAGINA"], "imagen": ruta_img})
                        except Exception as error_img:
                            st.warning(f"No se pudo generar la imagen: {error_img}")
                else:
                    st.warning(f"No se encontró REFERENCIA en {archivo_subido.name}.")
            except Exception as error:
                st.error(f"Error procesando {archivo_subido.name}: {error}")
            progreso.empty()

        if resultados_referencia:
            st.divider()
            st.subheader("👤 Persona encontrada en REFERENCIA")
            df_referencia = pd.DataFrame(resultados_referencia)
            patron_destinataria = (
                r"(?:ENF\.?|F\.?)?\s*NORA\s+MIREYA\s+RAMÍREZ\s+SÁNCHEZ"
                r"|SECRETARIA\s+GENERAL\s+DEL\s+STUAC"
                r"|p\s*r\s*e\s*s\s*e\s*n\s*t\s*e\s*[.\-]*"
                r"|A\s+fin\s+de\s+dar\s+cumplimiento\s+a\s+lo\s+establecido[.,;:]*"
            )
            def limpiar_campo_referencia(valor):
                valor = "" if valor is None else str(valor)
                valor = re.sub(r'(?:ESE\s*i\s*/?\s*[“\"”]?|Y\s*Ni\s*[“\"”]?|Y\s*ño\.?\s*/?\s*)(?=\s*(?:SECRETARIA\s+GENERAL\s+DEL\s+STUAC|A\s+fin\s+de\s+dar\s+cumplimiento))', " ", valor, flags=re.IGNORECASE)
                valor = re.sub(patron_destinataria, " ", valor, flags=re.IGNORECASE)
                return re.sub(r"\s+", " ", valor).strip(" \t\r\n.-:,;“”\"/")
            df_referencia["NOMBRE"] = df_referencia["NOMBRE"].fillna("").astype(str).map(limpiar_campo_referencia)
            df_referencia["LUGAR Y FECHA"] = df_referencia["LUGAR Y FECHA"].fillna("").astype(str).str.replace(r"^\s*SALTILLO\s*,?\s*COAHUILA\s+A\s*", "", regex=True, case=False).str.strip()
            df_referencia["ASUNTO O REFERENCIA"] = df_referencia["ASUNTO O REFERENCIA"].fillna("").astype(str).map(limpiar_campo_referencia)
            df_referencia["REFERENCIA"] = df_referencia["REFERENCIA"].fillna("").astype(str).map(lambda v: re.sub(r"\bSin\s+otro\s+particular\b[\s\S]*$", "", v, flags=re.IGNORECASE).strip(" \t\r\n.-:,;“”\"/"))
            columnas = ["OFICIO", "NOMBRE", "LUGAR Y FECHA", "NUMERACION", "ASUNTO O REFERENCIA", "CUERPO O TEXTO", "REFERENCIA"]
            df_referencia = df_referencia[columnas]
            st.dataframe(df_referencia, use_container_width=True, hide_index=True)
            buffer_ref = BytesIO()
            with pd.ExcelWriter(buffer_ref, engine="openpyxl") as writer:
                df_referencia.to_excel(writer, index=False, sheet_name="PERSONA ENCONTRADA EN REFERENCIA")
            st.download_button("📥 Descargar resultados en Excel", data=buffer_ref.getvalue(), file_name="PERSONA_ENCONTRADA_EN_REFERENCIA.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            st.divider()
            st.subheader("🖼️ Página del oficio")
            for i, item in enumerate(imagenes_referencia):
                with st.expander(f"📄 {item['oficio']} — Página {item['pagina']}"):
                    interactive_image(item["imagen"], 520)
                    with open(item["imagen"], "rb") as f:
                        datos = f.read()
                    st.download_button("📥 Descargar página", data=datos, file_name=os.path.basename(item["imagen"]), mime="image/png", key=f"ref_img_{i}", use_container_width=True)
    st.divider()
    st.stop()


# ==========================================================
# MODOS EXISTENTES
# ==========================================================

if kind == "Persona":

    term = st.text_input(
        "👤 Nombre de la persona",
        placeholder=
        "Ejemplo: Mendoza Zamora Miguel Angel"
    )

elif kind == "Expediente":

    term = st.text_input(
        "📁 Número de expediente",
        placeholder="Ejemplo: 13607"
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
        "🔎 PALABRA O FRASE",
        placeholder=(
            "Escriba varias palabras o frases separadas por coma, punto y coma o una por línea, "                               " Ejemplos: Director, Secretario Académico, Vacante, Vacante (por, Sistemas, Arquitectura, Ingeniería,"             " Oficio No. 0865/OM/2026, terna, septiembre, boletín 254/OM/2025"	
        ),
        help=(
            "Puede buscar una o varias palabras/frases. Sepárelas con coma, "
            "punto y coma o escriba una por línea."
        ),
        height=100
    )


# ==========================================================
# NOTA OPCIONAL Y BITÁCORA DE BÚSQUEDAS (VACANTE / PALABRA O FRASE)
# ==========================================================
nota_busqueda = ""
if kind in ("Vacante", "Palabra o frase"):
    nota_busqueda = st.text_area(
        "📝 Nota opcional relacionada con la búsqueda, ",
        placeholder="IMPORTANTE: Escriba una observación, contexto o seguimiento...",
        height=90,
        key="nota_busqueda_vacante_frase"
    )

# El Excel se crea junto al programa y se actualiza agregando una fila por búsqueda.
ARCHIVO_BITACORA_BUSQUEDAS = "BITACORA_BUSQUEDAS_STUAC_INFORMA.xlsx"

def _guardar_bitacora_busqueda(modo, terminos, nota, coincidencias, documentos, dependencias):
    try:
        from openpyxl import load_workbook, Workbook
        from datetime import datetime
        ruta_bitacora = os.path.join(
            os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd(),
            ARCHIVO_BITACORA_BUSQUEDAS
        )
        encabezados = [
            "Fecha y hora", "Tipo de búsqueda", "Búsqueda solicitada", "Nota",
            "Número de coincidencias", "Documentos", "Dependencias"
        ]
        if os.path.exists(ruta_bitacora):
            libro = load_workbook(ruta_bitacora)
            hoja = libro["Búsquedas"] if "Búsquedas" in libro.sheetnames else libro.active
            if hoja.max_row == 1 and hoja.cell(1, 1).value is None:
                hoja.append(encabezados)
        else:
            libro = Workbook()
            hoja = libro.active
            hoja.title = "Búsquedas"
            hoja.append(encabezados)
        hoja.append([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), modo, " | ".join(terminos),
            nota or "", int(coincidencias), int(documentos), int(dependencias)
        ])
        hoja.freeze_panes = "A2"
        hoja.auto_filter.ref = hoja.dimensions
        for columna in hoja.columns:
            letra = columna[0].column_letter
            max_len = max((len(str(c.value or "")) for c in columna), default=10)
            hoja.column_dimensions[letra].width = min(max(max_len + 2, 14), 55)
        libro.save(ruta_bitacora)
        return ruta_bitacora, None
    except Exception as error:
        return None, str(error)

# ==========================================================
# DOCUMENTOS
# ==========================================================

st.subheader(
    "📚 Documentos"
)

if fuente_documentos == "PDF en repositorio local":
    RUTA_REPOSITORIO_LOCAL, PDFS_ACTIVOS = _listar_pdfs_repositorio_local()
    if not os.path.isdir(RUTA_REPOSITORIO_LOCAL):
        st.warning(f"No se encontró la carpeta REPOSITORIO_LOCAL. Créala en: {RUTA_REPOSITORIO_LOCAL}")
    else:
        st.caption(f"Repositorio local: {RUTA_REPOSITORIO_LOCAL} · PDF localizados: {len(PDFS_ACTIVOS)}")
elif fuente_documentos == "PDF en repositorio privado":
    token_gh, owner_gh, repo_gh, branch_gh, folder_gh = _github_config()
    if not token_gh:
        st.warning(
            "Para consultar el repositorio privado configura el token de GitHub en "
            "`.streamlit/secrets.toml`. El token debe tener permiso **Contents: Read-only** "
            "sobre el repositorio STUAC-2026/CARPETA."
        )
        PDFS_ACTIVOS = {}
    else:
        try:
            with st.spinner("Consultando los PDF del repositorio privado de GitHub..."):
                PDFS_ACTIVOS = _github_listar_pdfs(owner_gh, repo_gh, branch_gh, folder_gh, token_gh)
            st.caption(f"Repositorio: {owner_gh}/{repo_gh} · Rama: {branch_gh} · PDF localizados: {len(PDFS_ACTIVOS)}")
        except Exception as exc:
            PDFS_ACTIVOS = {}
            st.error(f"No fue posible consultar el repositorio privado: {exc}")
else:
    PDFS_ACTIVOS = PDFS

choices = ["TODOS LOS DOCUMENTOS"] + list(PDFS_ACTIVOS)

docs = st.multiselect(
    "Seleccione los documentos:",
    choices,
    default=["TODOS LOS DOCUMENTOS"] if PDFS_ACTIVOS else [],
    key="documentos_seleccionados_busqueda"
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

            clave_item = _normalizar_busqueda_flexible(item)
            claves_existentes = {
                _normalizar_busqueda_flexible(x) for x in search_terms
            }
            if item and clave_item not in claves_existentes:
                search_terms.append(item)

    else:
        search_terms = [term.strip()]

    if not search_terms:

        st.warning(
            "Por favor escriba al menos una palabra o frase válida."
        )

        st.stop()

    targets = (
        list(PDFS_ACTIVOS)
        if "TODOS LOS DOCUMENTOS" in docs
        else docs
    )

    if not targets:

        st.warning(
            "No hay documentos seleccionados o no se localizaron PDF en el origen elegido. "
            "Verifique la conexión, la rama y los permisos del repositorio."
        )

        st.stop()

    results = []

    images = []

    # Diagnóstico de lectura: permite distinguir entre una conexión correcta
    # a GitHub, PDF descargados, páginas con texto y búsquedas sin coincidencias.
    diagnostico_lectura = {
        "documentos_intentados": 0,
        "documentos_abiertos": 0,
        "paginas_totales": 0,
        "paginas_con_texto": 0,
        "paginas_sin_texto": 0,
        "caracteres_extraidos": 0,
        "paginas_ocr": 0,
        "caracteres_ocr": 0,
        "errores": []
    }
    muestra_texto = ""

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

            diagnostico_lectura["documentos_intentados"] += 1
            if fuente_documentos == "PDF en repositorio privado":
                pdf = _cargar_pdf_github(name, PDFS_ACTIVOS[name])
            elif fuente_documentos == "PDF en repositorio local":
                pdf = PDFS_ACTIVOS[name]
            else:
                pdf = download_pdf(name, PDFS_ACTIVOS[name])

            # Abrir el PDF y extraer texto en orden de lectura. Algunos PDF
            # necesitan el modo explícito "text" para recuperar correctamente
            # su capa de texto. No se activa OCR si la página ya contiene texto.
            with pymupdf.open(pdf) as doc:
                diagnostico_lectura["documentos_abiertos"] += 1
                for pno, page in enumerate(doc):
                    diagnostico_lectura["paginas_totales"] += 1
                    text, metodo_lectura, error_lectura = _extraer_texto_pagina_robusto(page)
                    text = str(text or "").replace("\x00", "").strip()

                    if text:
                        diagnostico_lectura["paginas_con_texto"] += 1
                        diagnostico_lectura["caracteres_extraidos"] += len(text)
                        if metodo_lectura == "OCR":
                            diagnostico_lectura["paginas_ocr"] += 1
                            diagnostico_lectura["caracteres_ocr"] += len(text)
                        if not muestra_texto:
                            muestra_texto = re.sub(r"\s+", " ", text)[:700]
                    else:
                        diagnostico_lectura["paginas_sin_texto"] += 1
                        if error_lectura:
                            diagnostico_lectura["errores"].append(
                                f"{name}, página {pno + 1}: {error_lectura}"
                            )
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
                        # Búsqueda flexible tipo filtro de Excel (CONTIENTE):
                        # ignora mayúsculas/minúsculas, acentos y diferencias de
                        # puntuación/espacios, incluyendo frases partidas por saltos.
                        texto_normalizado = _normalizar_busqueda_flexible(text)
                        encontrados = []

                        for search_term in search_terms:
                            termino_normalizado = _normalizar_busqueda_flexible(search_term)
                            if termino_normalizado and termino_normalizado in texto_normalizado:
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

        except Exception as e:
            detalle = f"{name}: {type(e).__name__}: {e}"
            diagnostico_lectura["errores"].append(detalle)
            st.error(f"Error procesando {name}: {e}")

        progress.progress(
            (i + 1) / len(targets)
        )

    status.empty()

    # En PALABRA O FRASE puede encontrarse más de un término en la misma
    # página, lo que genera registros repetidos. Para los reportes y la sección
    # de páginas encontradas se conserva únicamente el último registro de cada
    # combinación DOCUMENTO + PAGINA. Otros modos de búsqueda no se modifican.
    if kind == "Palabra o frase":
        resultados_unicos = {}
        for registro in results:
            clave_pagina = (registro.get("DOCUMENTO"), registro.get("PAGINA"))
            # pop + asignación coloca la página según su última aparición.
            resultados_unicos.pop(clave_pagina, None)
            resultados_unicos[clave_pagina] = registro
        results = list(resultados_unicos.values())

        imagenes_unicas = {}
        for registro in images:
            clave_pagina = (registro.get("documento"), registro.get("pagina"))
            imagenes_unicas.pop(clave_pagina, None)
            imagenes_unicas[clave_pagina] = registro
        images = list(imagenes_unicas.values())

    st.divider()

    with st.expander("ℹ️ Resumen de lectura de documentos", expanded=False):
        d = diagnostico_lectura
        c1, c2, c3 = st.columns(3)
        c1.metric("PDF abiertos", d["documentos_abiertos"])
        c2.metric("Páginas con texto", d["paginas_con_texto"])
        c3.metric("Caracteres extraídos", f'{d["caracteres_extraidos"]:,}')

    st.subheader(
        "📊 Reporte de resultados"
    )

    if kind == "Palabra o frase":
        st.info(
            "Términos buscados: "
            + " · ".join(f"**{x}**" for x in search_terms)
            + ". La búsqueda funciona como el filtro CONTIENE de Excel: "
              "no distingue mayúsculas, minúsculas ni acentos y admite "
              "diferencias de puntuación o saltos de línea. También se intenta "
              "identificar la categoría del cuadro donde aparece cada término."
        )


    if not results:

        st.warning(
            "La búsqueda terminó, pero no se encontraron coincidencias para: "
            + ", ".join(search_terms)
        )

        # Diagnóstico visible: evita que una búsqueda vacía parezca que el
        # programa no generó nada y permite saber si el texto fue leído.
        with st.expander("🔎 Diagnóstico de lectura de los PDF", expanded=True):
            d = diagnostico_lectura
            c1, c2, c3 = st.columns(3)
            c1.metric("PDF abiertos", d["documentos_abiertos"])
            c2.metric("Páginas con texto", d["paginas_con_texto"])
            c3.metric("Caracteres extraídos", f'{d["caracteres_extraidos"]:,}')
            st.write(f'PDF intentados: **{d["documentos_intentados"]}**')
            st.write(f'Páginas revisadas: **{d["paginas_totales"]}**')
            st.write(f'Páginas sin texto extraíble después de OCR: **{d["paginas_sin_texto"]}**')
            st.write(f'Páginas recuperadas mediante OCR: **{d["paginas_ocr"]}**')
            st.write(f'Caracteres reconocidos por OCR: **{d["caracteres_ocr"]:,}**')
            if muestra_texto:
                st.caption("Muestra del texto que PyMuPDF sí pudo leer (primeros 700 caracteres):")
                st.code(muestra_texto, language=None)
                st.info(
                    "Los PDF sí contienen texto legible. Si la muestra no contiene "
                    "el término buscado, revisa que la palabra, nombre o expediente "
                    "esté escrito igual en el documento. Si sí aparece, envía esta "
                    "muestra y los términos buscados para ajustar la normalización."
                )
            else:
                st.error(
                    "No se pudo extraer texto ni mediante lectura nativa ni mediante OCR. "
                    "Revisa los errores de Tesseract, el idioma español instalado, "
                    "la integridad del PDF y la respuesta de descarga de GitHub."
                )
            if d["errores"]:
                st.write("Errores detectados:")
                for error in d["errores"][:20]:
                    st.code(error)

        st.info(
            "No se generó un Excel de coincidencias porque no hubo resultados. "
            "El diagnóstico anterior permite identificar si el problema está en "
            "la extracción del texto o en el término de búsqueda."
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

        # Guardar automáticamente en Excel cada búsqueda VACANTE / PALABRA O FRASE.
        if kind in ("Vacante", "Palabra o frase"):
            ruta_log, error_log = _guardar_bitacora_busqueda(
                kind, search_terms, nota_busqueda, len(df),
                df["DOCUMENTO"].nunique() if "DOCUMENTO" in df.columns else 0,
                df["DEPENDENCIA"].nunique() if "DEPENDENCIA" in df.columns else 0
            )
            if ruta_log:
                st.success(f"🗂️ Búsqueda guardada/actualizada en Excel: {os.path.basename(ruta_log)}")
                with open(ruta_log, "rb") as archivo_log:
                    st.download_button(
                        "📥 Descargar bitácora actualizada en Excel",
                        data=archivo_log.read(),
                        file_name=ARCHIVO_BITACORA_BUSQUEDAS,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="descargar_bitacora_busquedas",
                        use_container_width=True
                    )
            else:
                st.warning(f"No se pudo actualizar la bitácora Excel: {error_log}")

        # ==================================================
        # INTEGRACIÓN DE BASES DE AHORRO SINDICAL (GITHUB)
        # ==================================================
        # Se buscan los Excel en el repositorio indicado. Si GitHub no está
        # disponible, se utilizan copias locales colocadas junto al programa.
        REPO_AHORRO = "STUAC-2026/STUAC-INFORMA-2"
        ARCHIVO_ACUMULADO = "ACUMULADO_AHORRO_STUAC_TABLAS_EDITABLE.xlsx"
        ARCHIVO_APORTACIONES = "APORTACION_AHORRO_STUAC_TABLA_EDITABLE.xlsx"

        @st.cache_data(ttl=3600, show_spinner=False)
        def _obtener_archivos_ahorro_github():
            import requests
            from io import BytesIO

            headers = {"Accept": "application/vnd.github+json"}
            api_repo = f"https://api.github.com/repos/{REPO_AHORRO}"
            respuesta_repo = requests.get(api_repo, headers=headers, timeout=20)
            respuesta_repo.raise_for_status()
            info_repo = respuesta_repo.json()
            rama = info_repo.get("default_branch", "main")

            api_arbol = (
                f"https://api.github.com/repos/{REPO_AHORRO}/git/trees/"
                f"{rama}?recursive=1"
            )
            respuesta_arbol = requests.get(api_arbol, headers=headers, timeout=30)
            respuesta_arbol.raise_for_status()
            arbol = respuesta_arbol.json().get("tree", [])

            nombres = [ARCHIVO_ACUMULADO, ARCHIVO_APORTACIONES]
            rutas = {}
            for nombre in nombres:
                coincidencias = [
                    item.get("path", "") for item in arbol
                    if item.get("type") == "blob"
                    and item.get("path", "").split("/")[-1].lower() == nombre.lower()
                ]
                if coincidencias:
                    # Si existen varias copias, se prefiere la ubicada en la raíz.
                    rutas[nombre] = sorted(coincidencias, key=lambda x: ("/" in x, len(x)))[0]

            resultados = {}
            for nombre in nombres:
                ruta = rutas.get(nombre)
                if not ruta:
                    continue
                url = (
                    f"https://raw.githubusercontent.com/{REPO_AHORRO}/"
                    f"{rama}/{ruta}"
                )
                r = requests.get(url, timeout=45)
                r.raise_for_status()
                if not r.content.startswith(b"PK"):
                    raise ValueError(f"El archivo {nombre} descargado no parece ser un Excel válido.")
                resultados[nombre] = r.content
            return resultados

        def _cargar_base_ahorro(nombre_archivo, hoja):
            # Primero GitHub; después, archivos locales como respaldo.
            try:
                archivos = _obtener_archivos_ahorro_github()
                contenido = archivos.get(nombre_archivo)
                if contenido:
                    return pd.read_excel(BytesIO(contenido), sheet_name=hoja), "GitHub"
            except Exception as error_github:
                st.warning(
                    f"No fue posible consultar el repositorio GitHub para "
                    f"{nombre_archivo}. Se intentará la copia local. "
                    f"Detalle: {error_github}"
                )

            rutas_locales = [
                os.path.join(os.getcwd(), nombre_archivo),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), nombre_archivo)
                if "__file__" in globals() else nombre_archivo,
            ]
            for ruta in rutas_locales:
                if os.path.isfile(ruta):
                    try:
                        return pd.read_excel(ruta, sheet_name=hoja), "archivo local"
                    except Exception as error_local:
                        st.warning(f"No se pudo leer {nombre_archivo}: {error_local}")
            return pd.DataFrame(), "no disponible"

        with st.spinner("Consultando las bases de ahorro sindical..."):
            df_acumulado_ahorro, origen_acumulado = _cargar_base_ahorro(
                ARCHIVO_ACUMULADO, "Datos extraídos"
            )
            df_aportaciones_ahorro, origen_aportaciones = _cargar_base_ahorro(
                ARCHIVO_APORTACIONES, "Tabla de aportaciones"
            )

        def _normalizar_texto_ahorro(valor):
            import unicodedata
            texto = str(valor if pd.notna(valor) else "").strip().upper()
            texto = unicodedata.normalize("NFKD", texto)
            texto = "".join(c for c in texto if not unicodedata.combining(c))
            return re.sub(r"[^A-Z0-9]+", " ", texto).strip()

        def _normalizar_expediente_ahorro(valor):
            if pd.isna(valor):
                return ""
            texto = str(valor).strip()
            if texto.endswith(".0"):
                texto = texto[:-2]
            return re.sub(r"\s+", "", texto).upper()

        def _filtrar_base_ahorro(base, tipo_busqueda, termino_busqueda):
            if base.empty or "Exp" not in base.columns:
                return pd.DataFrame()
            coincidencias = base.copy()
            if tipo_busqueda == "Expediente":
                clave = _normalizar_expediente_ahorro(termino_busqueda)
                coincidencias["_EXP_KEY"] = coincidencias["Exp"].map(
                    _normalizar_expediente_ahorro
                )
                coincidencias = coincidencias[coincidencias["_EXP_KEY"] == clave]
            elif tipo_busqueda in ("Persona", "Palabra o frase"):
                clave_nombre = _normalizar_texto_ahorro(termino_busqueda)
                clave_exp = _normalizar_expediente_ahorro(termino_busqueda)
                por_nombre = pd.DataFrame()
                por_exp = pd.DataFrame()
                if clave_nombre and "Nombre" in coincidencias.columns:
                    coincidencias["_NOMBRE_KEY"] = coincidencias["Nombre"].map(
                        _normalizar_texto_ahorro
                    )
                    # En PALABRA O FRASE se aplica criterio tipo Excel:
                    # CONTIENE, sin distinguir acentos ni mayúsculas. En
                    # PERSONA se conserva la coincidencia del nombre completo.
                    if tipo_busqueda == "Palabra o frase":
                        por_nombre = coincidencias[
                            coincidencias["_NOMBRE_KEY"].str.contains(
                                re.escape(clave_nombre), na=False, regex=True
                            )
                        ]
                    else:
                        por_nombre = coincidencias[
                            coincidencias["_NOMBRE_KEY"] == clave_nombre
                        ]
                if clave_exp and clave_exp.isdigit():
                    coincidencias["_EXP_KEY"] = coincidencias["Exp"].map(
                        _normalizar_expediente_ahorro
                    )
                    por_exp = coincidencias[
                        coincidencias["_EXP_KEY"] == clave_exp
                    ]
                coincidencias = pd.concat(
                    [por_nombre, por_exp], ignore_index=True
                ).drop_duplicates()
            else:
                return pd.DataFrame()
            return coincidencias.drop(
                columns=["_EXP_KEY", "_NOMBRE_KEY"], errors="ignore"
            ).drop_duplicates()

        # Solo se vincula información personal cuando la búsqueda identifica
        # expresamente una persona o un expediente. No se atribuyen ahorros a
        # búsquedas generales de vacantes, palabras o frases.
        if kind in ("Persona", "Expediente", "Palabra o frase"):
            terminos_personales = (
                search_terms if kind == "Palabra o frase" else [term]
            )
            acumulados = []
            aportaciones = []
            for termino_personal in terminos_personales:
                encontrado_acumulado = _filtrar_base_ahorro(
                    df_acumulado_ahorro, kind, termino_personal
                )
                encontrado_aportacion = _filtrar_base_ahorro(
                    df_aportaciones_ahorro, kind, termino_personal
                )
                if not encontrado_acumulado.empty:
                    acumulados.append(encontrado_acumulado)
                if not encontrado_aportacion.empty:
                    aportaciones.append(encontrado_aportacion)

            ahorro_acumulado_encontrado = (
                pd.concat(acumulados, ignore_index=True).drop_duplicates()
                if acumulados else pd.DataFrame()
            )
            aportaciones_encontradas = (
                pd.concat(aportaciones, ignore_index=True).drop_duplicates()
                if aportaciones else pd.DataFrame()
            )

            st.markdown("### 💰 Información relacionada STUAC")
            st.caption(
                f"Origen de las bases: carpetas STUAC "
            )

            if not ahorro_acumulado_encontrado.empty:
                st.markdown("#### Ahorro acumulado (no se publica por protección de datos personales)")
                st.dataframe(
                    ahorro_acumulado_encontrado,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info(
                    "No se encontró un registro de ahorro acumulado que coincida "
                    "exactamente con la persona o expediente consultado."
                )

            if not aportaciones_encontradas.empty:
                st.markdown("#### Aportaciones al ahorro (no se publica por protección de datos personales)")
                st.dataframe(
                    aportaciones_encontradas,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info(
                    "No se encontró un registro de aportaciones que coincida "
                    "exactamente con la persona o expediente consultado."
                )
        else:
            st.caption(
                "Para evitar atribuciones incorrectas, solo se muestran registros "
                "cuando el término de búsqueda coincide con un nombre completo o "
                "un expediente de las bases. Las búsquedas generales de vacantes "
                "no identifican por sí mismas a un trabajador."
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