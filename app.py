Python
import streamlit as st
import pandas as pd
import math

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Simulador Almacén", page_icon="📦", layout="centered")

st.title("📦 Simulador de Envíos - Almacén")
st.markdown("Introduce los datos del bulto para calcular la agencia más rentable.")

# --- CARGA DE DATOS (Lee tu Excel) ---
@st.cache_data
def load_data():
    # Asegúrate de que el Excel se llama exactamente así y está en la misma carpeta
    file_path = "Super_Simulador_Almacen.xlsx"
    zonas = pd.read_excel(file_path, sheet_name="Zonas_Logistica")
    tarifas_cbl = pd.read_excel(file_path, sheet_name="Tarifas_CBL")
    tarifas_dhl = pd.read_excel(file_path, sheet_name="Tarifas_DHL")
    tarifas_tipsa = pd.read_excel(file_path, sheet_name="Tarifas_TIPSA")
    return zonas, tarifas_cbl, tarifas_dhl, tarifas_tipsa

try:
    zonas, tarifas_cbl, tarifas_dhl, tarifas_tipsa = load_data()
except Exception as e:
    st.error(f"⚠️ Error al leer el Excel. Comprueba que 'Super_Simulador_Almacen.xlsx' está subido. Detalle: {e}")
    st.stop()

# --- INTERFAZ DE USUARIO ---
col1, col2 = st.columns(2)
with col1:
    peso = st.number_input("Peso Real (kg)", min_value=0.1, value=15.0, step=0.5)
with col2:
    cp = st.text_input("Código Postal (5 dígitos)", value="", max_chars=5)

if st.button("🚀 Calcular Agencia Más Barata", type="primary", use_container_width=True):
    if len(cp) < 2:
        st.warning("Por favor, introduce un Código Postal válido.")
    else:
        prefijo = cp[:2]
        
        # 1. Buscar Provincia y Zonas
        zona_info = zonas[zonas['Prefijo CP'].astype(str).str.zfill(2) == prefijo]
        
        if zona_info.empty:
            st.error("Código Postal no encontrado en la base de datos.")
        else:
            provincia = zona_info.iloc[0]['Provincia']
            z_cbl = str(zona_info.iloc[0]['Zona CBL'])
            z_dhl = str(zona_info.iloc[0]['Zona DHL'])
            z_tipsa = str(zona_info.iloc[0]['Zona TIPSA'])
            
            st.info(f"📍 **Destino detectado:** {provincia}")
            
            # Si es Canarias, Ceuta o Melilla, lanzamos aviso (por ahora simplificado)
            if z_cbl == "Canarias" or z_cbl == "Especial":
                st.warning("⚠️ Este destino es Insular/Especial. La lógica avanzada de Canarias y aduanas requiere el panel específico.")
            else:
                costes = {}
                
                # --- CÁLCULO CBL ---
                try:
                    tarifa_cbl = tarifas_cbl[tarifas_cbl['Hasta Kg'] >= peso].iloc[0][f'Zona {z_cbl}']
                    coste_cbl = tarifa_cbl + (tarifa_cbl * 0.10) + (tarifa_cbl * 0.08) + 0.50
                    costes['CBL Logística'] = coste_cbl
                except:
                    costes['CBL Logística'] = float('inf')
                
                # --- CÁLCULO DHL ---
                try:
                    tarifa_dhl = tarifas_dhl[tarifas_dhl['Hasta Kg'] >= peso].iloc[0][f'Zona {z_dhl}']
                    coste_dhl = tarifa_dhl + (tarifa_dhl * 0.1015)
                    costes['DHL Parcel'] = coste_dhl
                except:
                    costes['DHL Parcel'] = float('inf')
                
                # --- CÁLCULO TIPSA ---
                if z_tipsa != "No Ofertado" and peso <= 50:
                    try:
                        tarifa_tipsa = tarifas_tipsa[tarifas_tipsa['Hasta Kg'] >= peso].iloc[0][z_tipsa]
                        coste_tipsa = tarifa_tipsa + (tarifa_tipsa * 0.1030)
                        costes['TIPSA Economy'] = coste_tipsa
                    except:
                        costes['TIPSA Economy'] = float('inf')
                else:
                    costes['TIPSA Economy'] = float('inf') # Penalización por peso excedido
                
                # --- RESULTADOS ---
                mejor_agencia = min(costes, key=costes.get)
                mejor_precio = costes[mejor_agencia]
                
                st.success(f"### 🏆 ENVIAR POR: {mejor_agencia} \n ### 💶 {mejor_precio:.2f} €")
                
                st.markdown("---")
                st.markdown("#### Resto de opciones:")
                for agencia, precio in costes.items():
                    if agencia != mejor_agencia:
                        if precio == float('inf'):
                            st.write(f"- **{agencia}:** Fuera de rango o no ofertado.")
                        else:
                            st.write(f"- **{agencia}:** {precio:.2f} €")