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
    file_path = "Super_Simulador_Almacen.xlsx"
    zonas = pd.read_excel(file_path, sheet_name="Zonas_Logistica")
    tarifas_cbl = pd.read_excel(file_path, sheet_name="Tarifas_CBL")
    tarifas_dhl = pd.read_excel(file_path, sheet_name="Tarifas_DHL")
    tarifas_tipsa = pd.read_excel(file_path, sheet_name="Tarifas_TIPSA")
    # Cargamos también las pestañas de Canarias
    tarifas_cbl_can = pd.read_excel(file_path, sheet_name="Tarifas_CBL_Canarias")
    tarifas_dhl_can = pd.read_excel(file_path, sheet_name="Tarifas_DHL_Canarias")
    return zonas, tarifas_cbl, tarifas_dhl, tarifas_tipsa, tarifas_cbl_can, tarifas_dhl_can

try:
    zonas, tarifas_cbl, tarifas_dhl, tarifas_tipsa, tarifas_cbl_can, tarifas_dhl_can = load_data()
except Exception as e:
    st.error(f"⚠️ Error al leer el Excel. Comprueba que 'Super_Simulador_Almacen.xlsx' está subido correctamente.")
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
        zona_info = zonas[zonas['Prefijo CP'].astype(str).str.zfill(2) == prefijo]
        
        if zona_info.empty:
            st.error("Código Postal no encontrado en la base de datos.")
        else:
            provincia = zona_info.iloc[0]['Provincia']
            z_cbl = str(zona_info.iloc[0]['Zona CBL'])
            z_dhl = str(zona_info.iloc[0]['Zona DHL'])
            z_tipsa = str(zona_info.iloc[0]['Zona TIPSA'])
            
            costes = {}
            
            # ==========================================
            # RUTA 1: CANARIAS Y ESPECIALES
            # ==========================================
            if z_cbl == "Canarias" or z_cbl == "Especial":
                st.info(f"🌴 **Destino Insular/Especial detectado:** {provincia}")
                
                st.markdown("### 🛃 Parámetros de Aduana (DUA)")
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    dua_cbl = st.number_input("DUA Export. CBL (€)", value=22.00, step=1.0, disabled=True)
                    st.caption("Fijo por contrato")
                with col_d2:
                    dhl_bajo_valor = st.radio("¿DHL Bajo Valor?", options=["No (23.50€)", "Sí (5.00€)"])
                    dua_dhl = 5.00 if "Sí" in dhl_bajo_valor else 23.50
                
                st.markdown("---")
                cp_num = int(cp) if cp.isdigit() else 0
                
                # Lógica CBL (Mayor vs Menor)
                isla_mayor = (35000 <= cp_num <= 35499) or (38000 <= cp_num <= 38699)
                tipo_isla_cbl = "Islas Mayores" if isla_mayor else "Islas Menores"
                
                # Lógica DHL (Reexpedición)
                if (38001 <= cp_num <= 38010) or (35001 <= cp_num <= 35018):
                    reexp_dhl = "Directa (Capital)"
                elif (38100 <= cp_num <= 38699) or (35100 <= cp_num <= 35499):
                    reexp_dhl = "Pueblo"
                else:
                    reexp_dhl = "Interislas"
                    
                st.write(f"**Cálculo geográfico:** CBL = {tipo_isla_cbl} | DHL = Ruta {reexp_dhl}")
                
                # Cálculos Canarias
                try:
                    row_cbl = tarifas_cbl_can[tarifas_cbl_can['Hasta Kg'] >= peso].iloc[0]
                    base_cbl = row_cbl[tipo_isla_cbl]
                    costes['CBL (Marítimo)'] = base_cbl + (base_cbl * 0.10) + (base_cbl * 0.08) + 0.50 + dua_cbl
                except:
                    costes['CBL (Marítimo)'] = float('inf')
                    
                try:
                    row_dhl = tarifas_dhl_can[tarifas_dhl_can['Hasta Kg'] >= peso].iloc[0]
                    base_dhl_mar = row_dhl['Marítimo (Base)']
                    base_dhl_aer = row_dhl['Aéreo (Base)']
                    extra_reexp = 0
                    if reexp_dhl == "Pueblo": extra_reexp = row_dhl['Reexp. Pueblo']
                    if reexp_dhl == "Interislas": extra_reexp = row_dhl['Reexp. Interislas']
                    
                    costes['DHL (Marítimo)'] = ((base_dhl_mar + extra_reexp) * 1.1015) + dua_dhl
                    costes['DHL (Aéreo)'] = ((base_dhl_aer + extra_reexp) * 1.1015) + dua_dhl
                except:
                    costes['DHL (Marítimo)'] = float('inf')
                    costes['DHL (Aéreo)'] = float('inf')
                    
                costes['TIPSA Economy'] = float('inf') # Sin datos
                
            # ==========================================
            # RUTA 2: PENÍNSULA Y BALEARES
            # ==========================================
            else:
                st.info(f"📍 **Destino detectado:** {provincia} (Zona CBL: {z_cbl} | Zona DHL: {z_dhl})")
                
                # CÁLCULO CBL
                try:
                    tarifa_cbl = tarifas_cbl[tarifas_cbl['Hasta Kg'] >= peso].iloc[0][f'Zona {z_cbl}']
                    costes['CBL Logística'] = tarifa_cbl + (tarifa_cbl * 0.10) + (tarifa_cbl * 0.08) + 0.50
                except:
                    costes['CBL Logística'] = float('inf')
                
                # CÁLCULO DHL
                try:
                    tarifa_dhl = tarifas_dhl[tarifas_dhl['Hasta Kg'] >= peso].iloc[0][f'Zona {z_dhl}']
                    costes['DHL Parcel'] = tarifa_dhl + (tarifa_dhl * 0.1015)
                except:
                    costes['DHL Parcel'] = float('inf')
                
                # CÁLCULO TIPSA
                if z_tipsa != "No Ofertado" and peso <= 50:
                    try:
                        tarifa_tipsa = tarifas_tipsa[tarifas_tipsa['Hasta Kg'] >= peso].iloc[0][z_tipsa]
                        costes['TIPSA Economy'] = tarifa_tipsa + (tarifa_tipsa * 0.1030)
                    except:
                        costes['TIPSA Economy'] = float('inf')
                else:
                    costes['TIPSA Economy'] = float('inf')
            
            # ==========================================
            # RESULTADOS VISUALES (Común para ambas rutas)
            # ==========================================
            if all(v == float('inf') for v in costes.values()):
                st.error("No hay agencias disponibles para ese peso o destino.")
            else:
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
