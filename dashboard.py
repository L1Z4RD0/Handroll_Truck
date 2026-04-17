import streamlit as st
import pandas as pd
from streamlit_apexjs import st_apexcharts
from database import conectar
import time

# Configuración de la página
st.set_page_config(page_title="Handroll Truck - Control Center", layout="wide")

# CSS Corporativo para KPIs
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stMetricValue"] { color: #00e396 !important; font-weight: bold; font-size: 1.8rem; }
    [data-testid="stMetricLabel"] { color: #feb019 !important; }
    div[data-testid="metric-container"] {
        background-color: #1b1e23;
        border: 1px solid #2d3139;
        padding: 15px;
        border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

def get_data():
    try:
        conn = conectar()
        query = "SELECT track_id, tipo_vehiculo, tipo, timestamp FROM eventos_vehiculos ORDER BY timestamp DESC"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

# Contenedor principal para la actualización automática
dashboard_placeholder = st.empty()

while True:
    df = get_data()
    
    with dashboard_placeholder.container():
        st.title("🛡️ Centro de Control Handroll Truck")
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            hoy = pd.Timestamp.now().date()
            df_hoy = df[df['timestamp'].dt.date == hoy]
            
            # --- KPIs SUPERIORES ---
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Flujo Total Hoy", len(df_hoy))
            
            df['hora'] = df['timestamp'].dt.hour
            hora_pick = df['hora'].mode()[0] if not df.empty else 0
            col2.metric("Hora de Mayor Tráfico", f"{hora_pick}:00")
            
            dias = df['timestamp'].dt.date.nunique()
            col3.metric("Promedio Diario", round(len(df)/dias, 1) if dias > 0 else 0)
            col4.metric("Estado del Sistema", "ACTIVO", delta="Online")

            st.write("---")

            # --- GRÁFICOS APEXCHARTS Y TABLA ---
            col_chart, col_table = st.columns([1, 1.2])

            with col_chart:
                st.subheader("📊 Distribución de Flota")
                counts = df['tipo_vehiculo'].value_counts()
                
                # Opciones generales del gráfico
                options = {
                    "chart": {
                        "background": "transparent"
                    },
                    "labels": counts.index.tolist(),
                    "colors": ['#008FFB', '#00E396', '#FEB019'],
                    "legend": {"position": "bottom", "labels": {"colors": "#fff"}},
                    "plotOptions": {
                        "pie": {
                            "donut": {
                                "labels": {
                                    "show": True, 
                                    "total": {"show": True, "color": "#fff", "label": "Total"}
                                }
                            }
                        }
                    }
                }
                
                # LLAMADA CORREGIDA: Pasamos los argumentos requeridos explícitamente
                st_apexcharts(
                    options, 
                    series=counts.tolist(), 
                    types="donut", # Usamos "types" en plural, según tu primer error
                    width="100%"
                )

            with col_table:
                st.subheader("📑 Registro Detallado (Tiempo Real)")
                st.dataframe(
                    df.head(8),
                    column_config={
                        "track_id": "ID Vehículo",
                        "tipo_vehiculo": "Clase",
                        "tipo": "Acción",
                        "timestamp": "Fecha/Hora"
                    },
                    hide_index=True,
                    use_container_width=True
                )
        else:
            st.info("Esperando datos del sistema de cámaras...")

    # Tiempo de espera antes de la siguiente actualización (en segundos)
    time.sleep(3)