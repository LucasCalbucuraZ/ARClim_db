#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
import tempfile
import numpy as np
import rasterio
from rasterio.plot import show
from rasterio.transform import rowcol, xy
import geopandas as gpd
from shapely.geometry import box
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
import matplotlib.colors as mcolors
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import streamlit as st

# ====================
# FUNCIONES AUXILIARES
# ====================

def load_tiff_from_github(url):
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Error al descargar archivo: {url}")
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".tif")
    temp_file.write(response.content)
    temp_file.close()
    return temp_file.name

def download_shapefile_from_github(name, folder):
    base_url = "https://raw.githubusercontent.com/LucasCalbucuraZ/ARClim_db/main/SHP"
    exts = ['shp', 'shx', 'dbf', 'prj', 'CPG']
    os.makedirs(f"SHP/{folder}", exist_ok=True)
    for ext in exts:
        url = f"{base_url}/{folder}/{name}.{ext}"
        local_path = f"SHP/{folder}/{name}.{ext}"
        if not os.path.exists(local_path):
            r = requests.get(url)
            if r.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(r.content)

def get_bbox(lat, lon):
    return box(lon - 2.3, lat - 1.35, lon + 0.7, lat + 1.0)

def load_shapefiles(bbox):
    download_shapefile_from_github("Comunas", "Comunas")
    download_shapefile_from_github("Regional", "Regiones")
    gdf_comunas = gpd.read_file("SHP/Comunas/Comunas.shp").to_crs("EPSG:4326")
    gdf_regiones = gpd.read_file("SHP/Regiones/Regional.shp").to_crs("EPSG:4326")
    return gdf_comunas[gdf_comunas.intersects(bbox)].copy(), gdf_regiones[gdf_regiones.intersects(bbox)].copy()

def get_variable_info():
    return {
        "mean_temperature": {"titulo": "Temperatura media (°C)", "vmin": -10, "vmax": 25, "cmap": "turbo", "unidad": "°C"},
        "coldest_day": {"titulo": "Día más frío (°C)", "vmin": -15, "vmax": 20, "cmap": "turbo", "unidad": "°C"},
        "coldest_night": {"titulo": "Noche más fría (°C)", "vmin": -15, "vmax": 20, "cmap": "turbo", "unidad": "°C"},
        "hottest_day": {"titulo": "Día más cálido (°C)", "vmin": 0, "vmax": 30, "cmap": "turbo", "unidad": "°C"},
        "warmest_night": {"titulo": "Noche más cálida (°C)", "vmin": 0, "vmax": 25, "cmap": "turbo", "unidad": "°C"},
        "vel_mean": {"titulo": "Velocidad del viento media (m/s)", "vmin": 0, "vmax": 20, "cmap": "turbo", "unidad": "m/s"},
        "vel_max": {"titulo": "Velocidad del viento máxima (m/s)", "vmin": 0, "vmax": 20, "cmap": "turbo", "unidad": "m/s"},
        "pr_sum": {"titulo": "Precipitación acumulada (mm)", "vmin": 0, "vmax": 100, "cmap": "Blues", "unidad": "mm"},
        "ps_mean": {"titulo": "Presión atmosférica media (mbar)", "vmin": 400, "vmax": 1013, "cmap": "turbo", "unidad": "mbar"},
        "hurs_mean": {"titulo": "Humedad relativa media (%)", "vmin": 0, "vmax": 100, "cmap": "turbo", "unidad": "%"},
    }

# ====================
# FUNCIONES DE GRAFICADO
# ====================

def plot_tiff_map(lat, lon, season, variable, periodo):
    info = get_variable_info()[variable]
    bbox = get_bbox(lat, lon)
    gdf_comunas, gdf_regiones = load_shapefiles(bbox)
    
    url = f"https://raw.githubusercontent.com/LucasCalbucuraZ/ARClim_db/main/{season}/{variable}/{variable}_{periodo}_{season}_latlon.tif"
    local_path = load_tiff_from_github(url)

    with rasterio.open(local_path) as src:
        data = src.read(1)
        transform = src.transform
        fila, columna = rowcol(transform, lon, lat)
        valor = data[fila, columna] if np.isfinite(data[fila, columna]) else np.nan
        x_min, y_max = xy(transform, fila, columna, offset='ul')
        x_max, y_min = xy(transform, fila, columna, offset='lr')

    fig, ax = plt.subplots(figsize=(8.5, 9), subplot_kw={'projection': ccrs.PlateCarree()})
    ax.add_feature(cfeature.OCEAN, facecolor='#a6cee3')
    ax.add_feature(cfeature.LAND, facecolor='#e6e1d3')
    ax.set_extent([bbox.bounds[0], bbox.bounds[2], bbox.bounds[1], bbox.bounds[3]], crs=ccrs.PlateCarree())
    ax.coastlines()
    
    img = show(data, transform=transform, ax=ax, cmap=info["cmap"], vmin=info["vmin"], vmax=info["vmax"])
    cbar = plt.colorbar(img.get_images()[0], ax=ax, orientation='vertical', shrink=0.6, pad=0.02)
    cbar.set_label(info["titulo"])

    ax.set_title(f"{info['titulo']} - {'Presente' if periodo == 'present' else 'Futuro'}")
    ax.text(lon - 0.4, lat + 0.1, f'{valor:.1f} {info["unidad"]}', fontsize=13, bbox=dict(facecolor='white'))

    for geom in gdf_regiones.geometry:
        ax.add_geometries([geom], crs=ccrs.PlateCarree(), facecolor='none', edgecolor='black', linewidth=1)
    for geom in gdf_comunas.geometry:
        ax.add_geometries([geom], crs=ccrs.PlateCarree(), facecolor='none', edgecolor='black', linewidth=0.5)

    os.remove(local_path)
    st.pyplot(fig)

def plot_delta_present_future(lat, lon, season, variable):
    info = get_variable_info()[variable]
    bbox = get_bbox(lat, lon)
    gdf_comunas, gdf_regiones = load_shapefiles(bbox)

    base_url = f"https://raw.githubusercontent.com/LucasCalbucuraZ/ARClim_db/main/{season}/{variable}/"
    url_present = base_url + f"{variable}_present_{season}_latlon.tif"
    url_future = base_url + f"{variable}_future_{season}_latlon.tif"

    path_p = load_tiff_from_github(url_present)
    path_f = load_tiff_from_github(url_future)

    with rasterio.open(path_p) as src_p, rasterio.open(path_f) as src_f:
        data_p = src_p.read(1).astype(np.float32)
        data_f = src_f.read(1).astype(np.float32)
        transform = src_p.transform
        delta = data_f - data_p
        fila, columna = rowcol(transform, lon, lat)
        valor = delta[fila, columna] if np.isfinite(delta[fila, columna]) else np.nan
        x_min, y_max = xy(transform, fila, columna, offset='ul')
        x_max, y_min = xy(transform, fila, columna, offset='lr')

    fig, ax = plt.subplots(figsize=(8.5, 9), subplot_kw={'projection': ccrs.PlateCarree()})
    ax.add_feature(cfeature.OCEAN, facecolor='#a6cee3')
    ax.add_feature(cfeature.LAND, facecolor='#e6e1d3')
    ax.set_extent([bbox.bounds[0], bbox.bounds[2], bbox.bounds[1], bbox.bounds[3]], crs=ccrs.PlateCarree())
    ax.coastlines()

    img = ax.imshow(delta, transform=transform, cmap='RdBu_r', extent=(bbox.bounds[0], bbox.bounds[2], bbox.bounds[1], bbox.bounds[3]), origin='upper')
    cbar = plt.colorbar(img, ax=ax, orientation='vertical', shrink=0.6, pad=0.02)
    cbar.set_label(f"Diferencia de {info['titulo']}")

    ax.set_title(f"Diferencia entre Futuro y Presente")
    ax.text(lon - 0.4, lat + 0.1, f'{valor:.1f} {info["unidad"]}', fontsize=13, bbox=dict(facecolor='white'))

    for geom in gdf_regiones.geometry:
        ax.add_geometries([geom], crs=ccrs.PlateCarree(), facecolor='none', edgecolor='black', linewidth=1)
    for geom in gdf_comunas.geometry:
        ax.add_geometries([geom], crs=ccrs.PlateCarree(), facecolor='none', edgecolor='black', linewidth=0.5)

    os.remove(path_p)
    os.remove(path_f)
    st.pyplot(fig)

# ====================
# STREAMLIT UI
# ====================

st.set_page_config(page_title="Cambio Climático ARClim", layout="wide")
st.title("Visualización de Cambio Climático ARClim")

with st.sidebar:
    lat = st.number_input("Latitud (°S)", -90.0, 0.0, -26.02, step=0.01)
    lon = st.number_input("Longitud (°O)", -90.0, 0.0, -68.88, step=0.01)
    season = st.selectbox("Estación", ["summer", "winter"])
    variable = st.selectbox("Variable", list(get_variable_info().keys()))
    show = st.button("Mostrar gráficos")

if show:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Presente")
        plot_tiff_map(lat, lon, season, variable, "present")
    with col2:
        st.subheader("Futuro")
        plot_tiff_map(lat, lon, season, variable, "future")

    st.markdown("<h3 style='text-align: center;'>Delta (Futuro - Presente)</h3>", unsafe_allow_html=True)
    plot_delta_present_future(lat, lon, season, variable)
