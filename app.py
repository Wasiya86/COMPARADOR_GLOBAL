import streamlit as st
import pandas as pd
import math
import os
import numpy as np
import plotly.express as px

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Simulador Almacén", page_icon="📦", layout="wide")

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

# --- 3. QUITAR ESPACIOS BLANCOS EXTRA ---
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
    _, col_centro, _ = st.columns([2, 1, 2])
    with col_centro:
        st.image("logo.png", width=300)
st.markdown("<h2 style='text-align: center; color: #333;'>📦 Portal Logístico Global</h2>", unsafe_allow_html=True)
st.markdown("---")

# ==========================================
# CREACIÓN DE PESTAÑAS (TABS)
# ==========================================
tab1, tab2 = st.tabs(["📦 Simulador de Envíos", "📊 Auditoría Logística"])

# ==========================================
# PESTAÑA 1: SIMULADOR OPERATIVO
# ==========================================
with tab1:
    # --- INICIALIZAR HISTORIAL EN MEMORIA ---
    if 'historial' not in st.session_state:
        st.session_state['historial'] = []

    # --- CARGA DE DATOS ---
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
        st.error("⚠️ Error al leer el Excel. Comprueba que 'Super_Simulador_Almacen.xlsx' está subido correctamente.")
        st.stop()

    # --- FORMULARIO DE ENTRADA ---
    with st.form("formulario_envio", clear_on_submit=False):
        tipo_envio = st.radio("Formato del envío:", ["📦 Bulto(s) sueltos", "🪵 Palet Europeo (Base 120x80)"], horizontal=True)
        
        col1_form, col2_form = st.columns(2)
        with col1_form:
            peso = st.number_input("Peso Real (kg)", min_value=0.1, value=15.0, step=0.5)
        with col2_form:
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
                
                # --- CÁLCULO DE PESOS TASABLES (Nuevas condiciones DHL) ---
                peso_tasable_cbl = peso
                peso_tasable_dhl = peso
                es_palet = "Palet" in tipo_envio
                ratio_dhl_aplicado = 167
                
                if es_palet:
                    volumen_m3 = 1.2 * 0.8 * (altura_palet / 100.0)
                    peso_tasable_cbl = peso
                    peso_vol_dhl = volumen_m3 * ratio_dhl_aplicado
                    peso_tasable_dhl = max(peso, peso_vol_dhl)
                
                costes = {}
                es_canarias = (z_cbl == "Canarias" or z_cbl == "Especial")
                
                # RUTA 1: CANARIAS Y ESPECIALES
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
                
                # RUTA 2: PENÍNSULA Y BALEARES
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
                
                # --- VISUALIZACIÓN DE RESULTADOS Y ESTRATEGIA ---
                valid_costes = {k: v for k, v in costes.items() if v != float('inf')}
                
                if not valid_costes:
                    st.error("No hay servicios disponibles para este rango de peso.")
                else:
                    mejor_agencia = min(valid_costes, key=valid_costes.get)
                    mejor_precio = valid_costes[mejor_agencia]
                    
                    alerta_estrategica = None
                    if es_palet and 'CBL Logística' in valid_costes and 'DHL Parcel' in valid_costes:
                        ahorro = valid_costes['DHL Parcel'] - valid_costes['CBL Logística']
                        if peso_tasable_dhl == peso_tasable_cbl:
                            mejor_agencia = "DHL Parcel"
                            mejor_precio = valid_costes['DHL Parcel']
                            alerta_estrategica = "🏆 **PRIORIDAD DHL:** Al no haber penalización de volumen, compensa usar DHL para evitar el 27,7% de retrasos de CBL."
                        elif mejor_agencia == "CBL Logística":
                            alerta_estrategica = f"⚠️ **USAR CBL CON PRECAUCIÓN:** Ahorras {ahorro:.2f} € porque DHL te facturaría {peso_tasable_dhl:.1f} kg (aire). Úsalo solo si la mercancía NO es urgente."

                    provincias_andalucia = ['Sevilla', 'Málaga', 'Almería', 'Granada', 'Huelva', 'Cádiz', 'Córdoba', 'Jaén']
                    if provincia in provincias_andalucia and mejor_agencia == "CBL Logística":
                        alerta_estrategica = "🚨 **ALERTA ANDALUCÍA:** CBL tiene un 40% de fallos en esta zona. Se recomienda forzar el envío por DHL."

                    st.session_state['historial'].insert(0, {
                        "Destino": provincia, "CP": cp, "Formato": "Palet" if es_palet else "Bulto",
                        "Peso (kg)": peso, "Agencia": mejor_agencia, "Precio": f"{mejor_precio:.2f} €"
                    })
                    st.session_state['historial'] = st.session_state['historial'][:5]
                    
                    st.markdown(f"### 📍 Destino: {provincia}")
                    st.success(f"### 🏆 RECOMENDACIÓN: {mejor_agencia}")
                    st.metric(label="Coste Total Redondeado (Recargos e Impuestos inc.)", value=f"{mejor_precio:.2f} €")
                    
                    if alerta_estrategica:
                        st.warning(alerta_estrategica)
                    
                    if es_palet:
                        st.info(f"📊 **Cálculo aplicado:** Palet de {volumen_m3:.2f} m³. DHL cubicado a **167 kg/m³** (**{peso_tasable_dhl:.1f} kg** facturables). CBL cotizado por peso real (**{peso} kg**).")
                    
                    st.markdown("#### 📊 Comparativa completa:")
                    cols_res = st.columns(len(valid_costes))
                    for idx, (agencia, precio) in enumerate(valid_costes.items()):
                        with cols_res[idx]:
                            if agencia == mejor_agencia:
                                st.metric(label=f"⭐ {agencia}", value=f"{precio:.2f} €")
                            else:
                                st.metric(label=agencia, value=f"{precio:.2f} €")

    # --- MOSTRAR HISTORIAL ---
    if st.session_state['historial']:
        st.markdown("---")
        st.markdown("### 🕒 Últimos 5 envíos verificados")
        df_hist = pd.DataFrame(st.session_state['historial'])
        st.dataframe(df_hist, use_container_width=True, hide_index=True)

# ==========================================
# PESTAÑA 2: DASHBOARD DE AUDITORÍA
# ==========================================
with tab2:
    st.markdown("### 📊 Cuadro de Mandos: Auditoría de Proveedores")
    
    # 1. CONEXIÓN A GOOGLE SHEETS
    url_google_sheet = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQiHaIV7qP1PSCSTSSNlePsJNa3ySK_lGyBUqccQH_vtWgzz3lOVlqeDeCBgSVyXe3mmJuyf0F29t1e/pub?output=csv"
    
    try:
        df = pd.read_csv(url_google_sheet)
        
        # Procesamiento y limpieza
        df['Fecha Salida'] = pd.to_datetime(df['Fecha Salida'], format='%d/%m/%Y', errors='coerce')
        df['Fecha Entrega'] = pd.to_datetime(df['Fecha Entrega'], format='%d/%m/%Y', errors='coerce')
        df = df.dropna(subset=['Fecha Salida', 'Fecha Entrega'])
        
        # Normalizar nombres de provincias a título (ej. "SEVILLA" o "Sevilla" -> "Sevilla")
        df['Provincia'] = df['Provincia'].astype(str).str.strip().str.title()
        
        df['Dias Habiles'] = np.busday_count(df['Fecha Salida'].values.astype('datetime64[D]'), df['Fecha Entrega'].values.astype('datetime64[D]'))
        df['Retraso'] = df['Dias Habiles'] > 2
        
        # --- FILTROS SUPERIORES ---
        col_filtro1, col_filtro2 = st.columns([2, 2])
        with col_filtro1:
            agencia_filtro = st.selectbox("🔍 Filtrar por Agencia:", ["Todas", "DHL", "CBL"])
            
        if agencia_filtro != "Todas":
            df_filtrado = df[df['Agencia'] == agencia_filtro]
        else:
            df_filtrado = df
            
        df_retrasos = df_filtrado[df_filtrado['Retraso'] == True]
        
        # --- TARJETAS DE KPIs SUPERIORES ---
        total_envios = len(df_filtrado)
        total_retrasos = len(df_retrasos)
        tasa_global_fallo = (total_retrasos / total_envios * 100) if total_envios > 0 else 0
        
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("📦 Total Envíos Analizados", f"{total_envios:,}")
        kpi2.metric("🚨 Total Incidencias / Retrasos", f"{total_retrasos:,}", delta=f"-{tasa_global_fallo:.1f}% fallo", delta_color="inverse")
        kpi3.metric("⏱️ Días Máximos de Retraso", f"{df_filtrado['Dias Habiles'].max()} días hábiles")
        
        st.markdown("---")
        
        # --- PREPARAR DATOS PARA GRÁFICOS ---
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            st.markdown("#### 📍 Top 10 Provincias con Mayor Tasa de Fallo")
            
            # Calcular % de fallo por provincia
            stats_prov = df_filtrado.groupby(['Provincia', 'Agencia']).agg(
                Total=('Retraso', 'count'),
                Fallos=('Retraso', 'sum')
            ).reset_index()
            
            stats_prov['Tasa Fallo (%)'] = (stats_prov['Fallos'] / stats_prov['Total']) * 100
            
            # Filtramos solo las que tienen fallos y nos quedamos con el Top 10 real
            stats_prov = stats_prov[stats_prov['Fallos'] > 0]
            stats_prov = stats_prov.sort_values(by='Tasa Fallo (%)', ascending=False).head(10)
            # Ordenar ascendente para que la barra más alta quede arriba en el gráfico horizontal
            stats_prov = stats_prov.sort_values(by='Tasa Fallo (%)', ascending=True)
            
            if stats_prov.empty:
                st.info("No hay suficientes datos de retrasos con este filtro.")
            else:
                fig_prov = px.bar(
                    stats_prov, x='Tasa Fallo (%)', y='Provincia', color='Agencia', 
                    barmode='group', orientation='h',
                    color_discrete_map={'DHL': '#D40511', 'CBL': '#004B87'},
                    text_auto='.1f'
                )
                fig_prov.update_layout(
                    xaxis_title="Tasa de Fallo (%)", yaxis_title="",
                    margin=dict(l=10, r=10, t=10, b=10), height=380,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_prov, use_container_width=True)
            
        with col_graf2:
            st.markdown("#### 🚨 Top 10 Mayores Retrasos en Días")
            
            top_peores = df_retrasos.sort_values(by='Dias Habiles', ascending=False).head(10).copy()
            # Convertimos expedicion a string para que el gráfico lo trate como categoría discreta y no amontone números raros en el eje X
            top_peores['Expedicion'] = top_peores['Expedicion'].astype(str)
            
            if top_peores.empty:
                st.success("¡Excelente! No hay retrasos registrados con los filtros actualizados.")
            else:
                fig_top = px.bar(
                    top_peores, x='Expedicion', y='Dias Habiles', color='Agencia',
                    text='Provincia',
                    color_discrete_map={'DHL': '#D40511', 'CBL': '#004B87'}
                )
                fig_top.update_traces(textposition='outside')
                fig_top.update_layout(
                    xaxis_title="Nº de Expedición", yaxis_title="Días Hábiles",
                    margin=dict(l=10, r=10, t=10, b=10), height=380,
                    xaxis={'type': 'category'},
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_top, use_container_width=True)
            
        st.markdown("---")
        st.markdown("#### 📋 Detalle de Expediciones con Incumplimiento (> 2 días)")
        
        # Formatear fechas para visualización limpia en tabla
        df_retrasos_show = df_retrasos.copy()
        df_retrasos_show['Fecha Salida'] = df_retrasos_show['Fecha Salida'].dt.strftime('%d/%m/%Y')
        df_retrasos_show['Fecha Entrega'] = df_retrasos_show['Fecha Entrega'].dt.strftime('%d/%m/%Y')
        
        st.dataframe(
            df_retrasos_show[['Agencia', 'Expedicion', 'Provincia', 'Fecha Salida', 'Fecha Entrega', 'Dias Habiles']]
            .sort_values('Dias Habiles', ascending=False), 
            use_container_width=True, 
            hide_index=True
        )
        
    except Exception as e:
        st.error(f"⚠️ Error al cargar el panel de auditoría: {e}")
