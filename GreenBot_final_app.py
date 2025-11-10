import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import numpy as np

# -----------------------------
# Configuración de la página
# -----------------------------
st.set_page_config(page_title="GreenBot", page_icon="🌿", layout="wide")

# Colores
PRIMARY = "#2E7D32"   # verde oscuro
SECONDARY = "#A5D6A7" # verde claro
BG = "#E8F5E9"        # fondo pálido

st.markdown(f"""
    <style>
    .reportview-container {{background: {BG};}}
    .stButton>button {{background-color: {SECONDARY}; color: #1B5E20; border-radius:8px;}}
    .stButton>button:hover {{background-color: {PRIMARY}; color: white;}}
    .main-title {{text-align:center; color:{PRIMARY}; font-size:30px; font-weight:700;}}
    .subtitle {{text-align:center; color:#33691E; margin-bottom:12px;}}
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-title'>🌱 GreenBot</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Buscador de puntos limpios · Colina</div>", unsafe_allow_html=True)

# -----------------------------
# Cargar datos
# -----------------------------
DATAFILE = "GreenBot_BASEDATOS_Actualizada.xlsx"

@st.cache_data(ttl=600)
def cargar_datos(path=DATAFILE):
    try:
        df = pd.read_excel(path)
    except Exception as e:
        st.error(f"Error al cargar la base de datos: {e}")
        return pd.DataFrame()
    # Normalizar nombres de columnas (si vienen con pequeñas variaciones)
    df.columns = [c.strip() for c in df.columns]
    # Asegurar columnas obligatorias
    for col in ["Nombre Punto Limpio", "Dirección", "Materiales que recibe", "Horario", "Latitud", "Longitud", "Comuna", "Tipo de punto"]:
        if col not in df.columns:
            df[col] = ""
    # Convertir coordenadas a numérico
    df["Latitud"] = pd.to_numeric(df["Latitud"], errors="coerce")
    df["Longitud"] = pd.to_numeric(df["Longitud"], errors="coerce")
    return df

df = cargar_datos()

if df.empty:
    st.warning("La base de datos está vacía o no se pudo cargar. Asegúrate de subir 'GreenBot_BASEDATOS_Actualizada.xlsx' en la carpeta del proyecto.")
    st.stop()

# -----------------------------
# Sidebar: filtros y botones
# -----------------------------
with st.sidebar:
    st.header("Filtros")
    comunas = sorted(df["Comuna"].fillna("").unique())
    comunas = [c for c in comunas if c]
    comuna_sel = st.selectbox("Selecciona comuna", options=["Todas"] + comunas, index=0)
    # Lista de materiales extraída del dataset
    materiales_raw = df["Materiales que recibe"].fillna("").astype(str).str.replace(";", ",").str.replace("/", ",").str.replace("|", ",").str.lower()
    materiales_set = sorted({m.strip() for cell in materiales_raw for m in (cell.split(",") if isinstance(cell,str) else []) if m.strip()})
    materiales_sel = st.multiselect("Materiales (elige uno o varios)", options=[m.title() for m in materiales_set], default=[])
    st.markdown("---")
    st.markdown("Acciones")
    if st.button("Mostrar todos los puntos"):
        comuna_sel = "Todas"
        materiales_sel = []
    if st.button("Recargar datos"):
        df = cargar_datos()
        st.success("Datos actualizados.")

# -----------------------------
# Filtrado
# -----------------------------
filtered = df.copy()
if comuna_sel != "Todas" and comuna_sel != None:
    filtered = filtered[filtered["Comuna"].str.lower() == comuna_sel.lower()]
if materiales_sel:
    # Filtrar si la fila contiene cualquiera de los materiales seleccionados
    mask = pd.Series(False, index=filtered.index)
    for m in materiales_sel:
        mask = mask | filtered["Materiales que recibe"].str.lower().str.contains(m.lower(), na=False)
    filtered = filtered[mask]

st.markdown(f"### Resultados: {len(filtered)} puntos encontrados")

# -----------------------------
# Layout principal: lista + mapa
# -----------------------------
col1, col2 = st.columns([1,2])

with col1:
    st.markdown("#### Lista de puntos")
    if filtered.empty:
        st.info("No hay puntos que coincidan con los filtros seleccionados.")
    else:
        for idx, row in filtered.reset_index().iterrows():
            st.markdown(f"**{row['Nombre Punto Limpio']}**  \n📍 {row['Dirección']}  \n🕒 {row['Horario']}  \n♻️ {row['Materiales que recibe']}  \n🧾 Tipo: {row['Tipo de punto']}  \n---")
            if st.button(f"Mostrar en el mapa: {row['Nombre Punto Limpio']}", key=f"show_{idx}"):
                st.session_state['focus_lat'] = row['Latitud']
                st.session_state['focus_lon'] = row['Longitud']

with col2:
    st.markdown("#### Mapa interactivo (clic en un marcador para más info)")
    # Centro del mapa
    if not filtered["Latitud"].dropna().empty and not filtered["Longitud"].dropna().empty:
        lat0 = filtered["Latitud"].dropna().mean()
        lon0 = filtered["Longitud"].dropna().mean()
    else:
        lat0, lon0 = -33.3039, -70.6722  # centro por defecto (Colina)
    m = folium.Map(location=[lat0, lon0], zoom_start=12, tiles="CartoDB positron")
    mc = MarkerCluster().add_to(m)
    for _, r in filtered.iterrows():
        if pd.notna(r["Latitud"]) and pd.notna(r["Longitud"]):
            popup = folium.Popup(f"<b>{r['Nombre Punto Limpio']}</b><br>{r['Dirección']}<br>Horario: {r['Horario']}<br>Materiales: {r['Materiales que recibe']}<br>Tipo: {r['Tipo de punto']}", max_width=300)
            folium.Marker(location=[r["Latitud"], r["Longitud"]], popup=popup, tooltip=r['Nombre Punto Limpio'], icon=folium.Icon(color='green', icon='recycle', prefix='fa')).add_to(mc)
    # Si el usuario pidió enfocar un punto concreto
    if 'focus_lat' in st.session_state and 'focus_lon' in st.session_state:
        try:
            folium.Marker([st.session_state['focus_lat'], st.session_state['focus_lon']], popup="Enfoque", icon=folium.Icon(color='red')).add_to(m)
            m.location = [st.session_state['focus_lat'], st.session_state['focus_lon']]
            m.zoom_start = 15
        except Exception:
            pass
    st_folium(m, width=700, height=550)

# -----------------------------
# Chatbot simple (sugerencias y respuestas predefinidas)
# -----------------------------
st.markdown("---")
st.markdown("### 🤖 Chat GreenBot (sugerencias rápidas)")
q = st.text_input("Haz una pregunta sobre reciclaje (ej: 'vidrio', 'plástico', 'papel'):", key="q_input")

if q:
    ql = q.lower()
    if "vidrio" in ql:
        st.success("♻️ Consejo: Lava y quita tapas. Puedes llevar vidrio a los puntos fijos marcados en el mapa.")
    elif "plástico" in ql or "pet" in ql:
        st.success("♻️ Consejo: Aplasta botellas PET para ahorrar espacio y retira tapas si corresponde.")
    elif "papel" in ql or "cartón" in ql:
        st.success("♻️ Consejo: Mantén el papel seco y plegado; lleva a puntos que acepten papel y cartón.")
    else:
        st.info("GreenBot está aprendiendo. Si necesitas información específica, selecciona filtros y revisa la lista de puntos.")

st.markdown("<div style='text-align:center; color:gray; margin-top:10px;'>Desarrollado por GreenBot 💚</div>", unsafe_allow_html=True)
