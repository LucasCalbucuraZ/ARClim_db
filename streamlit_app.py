# streamlit_app.py

import streamlit as st
from ARClim import plot_present_future, plot_delta_present_future

st.set_page_config(page_title="Cambio Climático", layout="wide")

st.title("Visualización de Cambio Climático ARClim")

lat = st.number_input("Latitud (°S)", min_value=-90.0, max_value=0.0, value=-26.02, step=0.01)
lon = st.number_input("Longitud (°O)", min_value=-90.0, max_value=0.0, value=-68.88, step=0.01)
season = st.selectbox("Estación", ["summer", "winter"])
variable = st.selectbox("Variable", [
    "mean_temperature", "coldest_day", "coldest_night", "hottest_day", "warmest_night",
    "vel_mean", "vel_max", "pr_sum", "ps_mean", "hurs_mean"
])

modo = st.radio("¿Qué deseas visualizar?", ["Presente y Futuro", "Diferencia (Delta)"])

if st.button("Mostrar gráfico"):
    try:
        if modo == "Presente y Futuro":
            plot_present_future(lat, lon, season, variable)
        else:
            plot_delta_present_future(lat, lon, season, variable)
        st.pyplot()
    except Exception as e:
        st.error(f"Ocurrió un error: {e}")
