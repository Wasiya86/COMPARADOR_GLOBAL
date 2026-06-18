import streamlit as st
import pandas as pd
import math
import os

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Simulador Almacén", page_icon="📦", layout="centered")

# --- 2. BARRA LATERAL: GUÍA DE PESOS ---
with st.sidebar:
    st.header("📋 Guía de Pesos Estándar")
    st.markdown("Calcula rápidamente el peso total si llevas varios bultos iguales:")
    
    st.markdown("""
    | Material / Formato | Peso Unidad |
    | :--- | :--- |
    | 📦 **Caja Kodak** | 4.0 kg |
    | 📦 **Caja DNP620** | 6.0 kg |
    | 📦 **Caja DNP RX1** | 7.0 kg |
    | 📦 **Caja DX100** | 5.0 kg |
    """)
    
    st.info("💡 **Ejemplo rápido:** Si tienes que enviar 3 cajas medianas, introduce **30.0** en la casilla de Peso Real.")
    st.markdown("---")
    st.markdown("⚠️ *Ante la duda con bultos irregulares, utiliza siempre la báscula para evitar recargos de la agencia.*")

# --- 3. QUITAR ESPACIOS BLANCOS EXTRA (CSS Mágico) ---
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)

# --- 4. CONTROL DE LOGO CORPORATIVO CENTRADO ---
if os.path.exists("logo.png"):
    col1, col_logo, col3 = st.columns([1, 1.5, 1])
    with col_logo:
        st.image("logo.png", use_container_width=True)

st.markdown("<h2 style='text-align: center; color: #333;'>📦 Simulador Global</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666;'>Introduce los datos y pulsa <b>ENTER</b> para calcular.</p>", unsafe_allow_html=True)
st.markdown("---")

# --- INICIALIZAR HISTORIAL EN MEMORIA ---
if 'historial' not in st.session_state:
    st.session_state['historial'] = []

# --- CARGA DE DATOS (Lee tu Excel) ---
@st.cache_data
def load_data():
    file_path = "Super_Simulador_Almacen.xlsx"
    zonas = pd.read_excel(file_path, sheet_name="Zonas_Logistica")
    tarifas_cbl = pd.read_excel(file_path, sheet_name="Tarifas_CBL")
    tarifas_dhl = pd.read_excel(file_path, sheet_name="Tarifas_DHL")
    tarifas_tipsa = pd.read_excel(file_path, sheet_name="Tarifas_TIPSA")
    tarifas_cbl_can = pd.read_excel(file_path, sheet_name="Tarifas_CBL_Canarias")
    tarifas_dhl_can = pd.read_excel(file_path, sheet_name="Tarifas_DHL_Canarias")
    return zonas, tarifas_cbl, tarifas_dhl, tarifas_tipsa, tarifas_cbl_can, tarifas_dhl_can

try:
    zonas, tarifas_cbl, tarifas_dhl, tarifas_tipsa, tarifas_cbl_can, tarifas_dhl_can = load_data()
except Exception as e:
    st.error(f"⚠️ Error al leer el Excel. Comprueba que 'Super_Simulador_Almacen.xlsx' está subido correctamente.")
    st.stop()

# --- FORMULARIO DE ENTRADA (Permite usar el ENTER) ---
with st.form("formulario_envio", clear_on_submit=False):
    tipo_envio = st.radio("Formato del envío:", ["📦 Bulto(s) sueltos", "🪵 Palet Europeo (Base 120x80)"], horizontal=True)
    
    col1, col2 = st.columns(2)
    with col1:
        peso = st.number_input("Peso Real (kg)", min_value=0.1, value=15.0, step=0.5)
    with col2:
        cp = st.text_input("Código Postal (5 dígitos)", value="", max_chars=5)
        
    altura_palet = 140
    if "Palet" in tipo_envio:
        altura_palet = st.number_input("Altura estimada del palet (cm)", min_value=10, max_value=240, value=140, step=10, help="Por defecto 140cm. Ajusta si es más alto o más bajo.")

    calcular = st.form_submit_button("🚀 Calcular Agencia (O pulsa ENTER)", type="primary", use_container_width=True)

# --- LÓGICA DE CÁLCULO ---
if calcular:
    if len(cp) < 2:
        st.warning("Por favor, introduce un Código Postal válido.")
    else:
        prefijo = cp[:2]
        zona_info = zonas[zonas['Prefijo CP'].astype(str).str.zfill(2) == prefijo]
        
        if zona_info.empty:
            st.error("Código Postal no encontrado en la base de datos.")
        else:
            provincia = zona_info.iloc[0]['Provincia']
            z_cbl = str(zona_info.iloc[0]['Zona CBL'])
            z_dhl = str(zona_info.iloc[0]['Zona DHL'])
            z_tipsa = str(zona_info.iloc[0]['Zona TIPSA'])
            
            # --- CÁLCULO DE PESOS TASABLES (Discriminación por volumen) ---
            peso_tasable_cbl = peso
            peso_tasable_dhl = peso
            es_palet = "Palet" in tipo_envio
            
            if es_palet:
                # Volumen en m3 = (1.2m * 0.8m * Altura en metros)
                volumen_m3 = 1.2 * 0.8 * (altura_palet / 100.0)
                
                # CBL: Cubica a 333 kg/m3
                peso_vol_cbl = volumen_m3 * 333
                peso_tasable_cbl = max(peso, peso_vol_cbl)
                
                # DHL: Cubica a 250 kg/m3 SOLO si supera los 50kg reales
                if peso > 50:
                    peso_vol_dhl = volumen_m3 * 250
                    peso_tasable_dhl = max(peso, peso_vol_dhl)
            
            costes = {}
            es_canarias = (z_cbl == "Canarias" or z_cbl == "Especial")
            
            # ==========================================
            # RUTA 1: CANARIAS Y ESPECIALES
            # ==========================================
            if es_canarias:
                dua_cbl = 22.00
                dua_dhl = 23.50
                cp_num = int(cp) if cp.isdigit() else 0
                
                isla_mayor = (35000 <= cp_num <= 35499) or (38000 <= cp_num <= 38699)
                tipo_isla_cbl = "Islas Mayores" if isla_mayor else "Islas Menores"
                
                if (38001 <= cp_num <= 38010) or (35001 <= cp_num <= 35018):
                    reexp_dhl = "Directa (Capital)"
                elif (38100 <= cp_num <= 38699) or (35100 <= cp_num <= 35499):
                    reexp_dhl = "Pueblo"
                else:
                    reexp_dhl = "Interislas"
                
                try:
                    row_cbl = tarifas_cbl_can[tarifas_cbl_can['Hasta Kg'] >= peso_tasable_cbl].iloc[0]
                    base_cbl = row_cbl[tipo_isla_cbl]
                    costes['CBL Marítimo'] = base_cbl + (base_cbl * 0.10) + (base_cbl * 0.08) + 0.50 + dua_cbl
                except:
                    costes['CBL Marítimo'] = float('inf')
                    
                try:
                    row_dhl = tarifas_dhl_can[tarifas_dhl_can['Hasta Kg'] >= peso_tasable_dhl].iloc[0]
                    base_dhl_mar = row_dhl['Marítimo (Base)']
                    base_dhl_aer = row_dhl['Aéreo (Base)']
                    extra_reexp = 0
                    if reexp_dhl == "Pueblo": extra_reexp = row_dhl['Reexp. Pueblo']
                    if reexp_dhl == "Interislas": extra_reexp = row_dhl['Reexp. Interislas']
                    
                    costes['DHL Marítimo'] = ((base_dhl_mar + extra_reexp) * 1.1015) + dua_dhl
                    costes['DHL Aéreo'] = ((base_dhl_aer + extra_reexp) * 1.1015) + dua_dhl
                except:
                    costes['DHL Marítimo'] = float('inf')
                    costes['DHL Aéreo'] = float('inf')
            
            # ==========================================
            # RUTA 2: PENÍNSULA Y BALEARES
            # ==========================================
            else:
                try:
                    tarifa_cbl = tarifas_cbl[tarifas_cbl['Hasta Kg'] >= peso_tasable_cbl].iloc[0][f'Zona {z_cbl}']
                    costes['CBL Logística'] = tarifa_cbl + (tarifa_cbl * 0.10) + (tarifa_cbl * 0.08) + 0.50
                except:
                    costes['CBL Logística'] = float('inf')
                
                try:
                    tarifa_dhl = tarifas_dhl[tarifas_dhl['Hasta Kg'] >= peso_tasable_dhl].iloc[0][f'Zona {z_dhl}']
                    costes['DHL Parcel'] = tarifa_dhl + (tarifa_dhl * 0.1015)
                except:
                    costes['DHL Parcel'] = float('inf')
                
                if z_tipsa != "No Ofertado" and peso <= 50 and not es_palet:
                    try:
                        tarifa_tipsa = tarifas_tipsa[tarifas_tipsa['Hasta Kg'] >= peso].iloc[0][z_tipsa]
                        costes['TIPSA Economy'] = tarifa_tipsa + (tarifa_tipsa * 0.1030)
                    except:
                        costes['TIPSA Economy'] = float('inf')
                else:
                    costes['TIPSA Economy'] = float('inf')
            
            # ==========================================
            # VISUALIZACIÓN DE RESULTADOS
            # ==========================================
            valid_costes = {k: v for k, v in costes.items() if v != float('inf')}
            
            if not valid_costes:
                st.error("No hay servicios disponibles para este rango de peso.")
            else:
                mejor_agencia = min(valid_costes, key=valid_costes.get)
                mejor_precio = valid_costes[mejor_agencia]
                
                # Guardar en el historial
                st.session_state['historial'].insert(0, {
                    "Destino": provincia,
                    "CP": cp,
                    "Formato": "Palet" if es_palet else "Bulto",
                    "Peso Usado (€)": f"CBL: {peso_tasable_cbl:.1f}kg | DHL: {peso_tasable_dhl:.1f}kg" if es_palet else f"{peso} kg",
                    "Agencia": mejor_agencia,
                    "Precio": f"{mejor_precio:.2f} €"
                })
                st.session_state['historial'] = st.session_state['historial'][:5]
                
                st.markdown(f"### 📍 Destino: {provincia}")
                st.success(f"### 🏆 RECOMENDACIÓN: {mejor_agencia}")
                st.metric(label="Coste Total Redondeado (Recargos e Impuestos inc.)", value=f"{mejor_precio:.2f} €")
                
                if es_palet:
                    st.info(f"📊 **Cubicaje calculado ({volumen_m3:.2f} m³):** Basado en {peso}kg reales. Peso tasado en CBL: **{peso_tasable_cbl:.1f} kg** (Ratio 333) | DHL: **{peso_tasable_dhl:.1f} kg** (Ratio 250)")
                
                st.markdown("#### 📊 Comparativa completa:")
                cols_res = st.columns(len(valid_costes))
                for idx, (agencia, precio) in enumerate(valid_costes.items()):
                    with cols_res[idx]:
                        st.metric(label=agencia, value=f"{precio:.2f} €")

# --- MOSTRAR HISTORIAL AL FINAL ---
if st.session_state['historial']:
    st.markdown("### 🕒 Últimos 5 envíos verificados")
    df_hist = pd.DataFrame(st.session_state['historial'])
    st.dataframe(df_hist, use_container_width=True, hide_index=True)
