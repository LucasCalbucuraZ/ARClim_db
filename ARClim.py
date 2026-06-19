#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, tempfile, requests, numpy as np, geopandas as gpd
from shapely.geometry import Point, box
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.cm import ScalarMappable
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import streamlit as st

BASE="https://raw.githubusercontent.com/LucasCalbucuraZ/ARClim_db/main"
SCENARIO="SSP585"

VARIABLE_INFO={
"mean_temperature":{"titulo":"Temperatura media (°C)","vmin":-10,"vmax":25,"cmap":"turbo","unidad":"°C","porcentaje":False},
"coldest_day":{"titulo":"Día más frío (°C)","vmin":-15,"vmax":20,"cmap":"turbo","unidad":"°C","porcentaje":False},
"coldest_night":{"titulo":"Noche más fría (°C)","vmin":-15,"vmax":20,"cmap":"turbo","unidad":"°C","porcentaje":False},
"hottest_day":{"titulo":"Día más cálido (°C)","vmin":0,"vmax":30,"cmap":"turbo","unidad":"°C","porcentaje":False},
"warmest_night":{"titulo":"Noche más cálida (°C)","vmin":0,"vmax":25,"cmap":"turbo","unidad":"°C","porcentaje":False},
"vel_mean":{"titulo":"Velocidad del viento media (m/s)","vmin":0,"vmax":20,"cmap":"turbo","unidad":"m/s","porcentaje":True},
"vel_max":{"titulo":"Velocidad del viento máxima (m/s)","vmin":0,"vmax":20,"cmap":"turbo","unidad":"m/s","porcentaje":True},
"pr_sum":{"titulo":"Precipitación acumulada (mm)","vmin":0,"vmax":100,"cmap":"Blues","unidad":"mm","porcentaje":True},
"ps_mean":{"titulo":"Presión atmosférica media (mbar)","vmin":400,"vmax":1013,"cmap":"turbo","unidad":"mbar","porcentaje":False},
"hurs_mean":{"titulo":"Humedad relativa media (%)","vmin":0,"vmax":100,"cmap":"turbo","unidad":"%","porcentaje":True}
}

def fetch(url,suffix):
    r=requests.get(url)
    r.raise_for_status()
    f=tempfile.NamedTemporaryFile(delete=False,suffix=suffix)
    f.write(r.content)
    f.close()
    return f.name

def download_shp(name,folder):
    exts=["shp","shx","dbf","prj","CPG"]
    os.makedirs(f"SHP/{folder}",exist_ok=True)
    for ext in exts:
        p=f"SHP/{folder}/{name}.{ext}"
        if not os.path.exists(p):
            open(p,"wb").write(requests.get(f"{BASE}/SHP/{folder}/{name}.{ext}").content)

def load_json(season,variable):
    p=fetch(f"{BASE}/{SCENARIO}/{season}/arclim_raster_5km_{variable.lower()}_ssp585_{season}.json",".json")
    g=gpd.read_file(p).to_crs("EPSG:4326")
    os.remove(p)
    return g

def col(df,key):
    return [c for c in df.columns if f"${key}$ssp585" in c][0]

def value(df,lat,lon,c):
    r=df[df.contains(Point(lon,lat))]
    return (np.nan,None) if r.empty else (float(r.iloc[0][c]),r.iloc[0].geometry)

def draw(ax,gdf,c,lat,lon,info,bbox,title):
    g=gdf[gdf.intersects(bbox)]
    v,cell=value(g,lat,lon,c)
    g.plot(column=c,ax=ax,cmap=info["cmap"],vmin=info["vmin"],vmax=info["vmax"],linewidth=.2,edgecolor="black")
    ax.set_extent(bbox.bounds,crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.OCEAN,facecolor="#a6cee3")
    ax.add_feature(cfeature.LAND,facecolor="#e6e1d3")
    ax.coastlines()
    if cell:
        x,y=cell.exterior.xy
        ax.plot(x,y,"r-",linewidth=2)
    ax.set_title(title)
    ax.text(lon-.4,lat+.1,f"{v:.1f} {info['unidad']}",bbox=dict(facecolor="white"))
    return v

def plot_present_future(lat,lon,season,variable):
    info=VARIABLE_INFO[variable]
    bbox=box(lon-2.3,lat-1.35,lon+.9,lat+1)
    g=load_json(season,variable)
    fig,axs=plt.subplots(1,2,figsize=(20,9),subplot_kw={"projection":ccrs.PlateCarree()})
    draw(axs[0],g,col(g,"present"),lat,lon,info,bbox,"Presente (1980–2010)")
    draw(axs[1],g,col(g,"future"),lat,lon,info,bbox,"Futuro (2035–2065)")
    st.pyplot(fig)

def plot_delta(lat,lon,season,variable):
    info=VARIABLE_INFO[variable]
    bbox=box(lon-2.3,lat-1.35,lon+.7,lat+1)
    g=load_json(season,variable)
    c=col(g,"delta")
    fig,ax=plt.subplots(figsize=(9,8),subplot_kw={"projection":ccrs.PlateCarree()})
    g[g.intersects(bbox)].plot(column=c,ax=ax,cmap="RdBu_r",linewidth=.2,edgecolor="black")
    st.pyplot(fig)

st.set_page_config(page_title="ARClim SSP5-8.5",layout="wide")
st.title("Visualizador ARClim SSP5–8.5")
lat=st.number_input("Latitud",value=-26.02)
lon=st.number_input("Longitud",value=-68.88)
season=st.selectbox("Estación",["summer","winter"])
variable=st.selectbox("Variable",list(VARIABLE_INFO))
if st.button("Mostrar gráfico"):
    plot_present_future(lat,lon,season,variable)
    plot_delta(lat,lon,season,variable)

