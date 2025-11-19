import streamlit as st
from utils import OverviewDatenManager, get_Ertrag_dieser_Monat,get_Ertrag_dieses_Jahr,get_Gesamtertrag,get_heutige_Leistung
import polars as pl
from datetime import date
import numpy as np
from ui_utils import st_Anlagenfoto,render_device
from update_ertragsdaten import update_ertrag
from update_leistungsdaten import update_leistung
import pandas as pd
import os
if not os.path.exists("app/data/ertrag.parquet"):
    update_ertrag()
if not os.path.exists("app/data/leistung.parquet"):
    update_leistung()


allgemein = pd.read_csv("allgemein.csv")

st.title("Unsere Solaranlagen")
 
for s in ["muensingen", "karlsruhe", "badboll", "mettingen", "holzgerlingen", "tuebingen", "hospitalhof","waiblingen","esslingen", "geislingen",]:

    col1, col2, col3 = st.columns([1,1,1])
    with col1:
            st_Anlagenfoto(s,allgemein.loc[allgemein["id"]==s]["title"].values[0])
        
    with col2:        
        a, b = st.columns(2,border = False)
        c, d = st.columns(2,border = False)
        peak = allgemein.loc[allgemein["id"]==s]["peak"].values[0]
        a.metric("Peak Leistung", f"{round(peak/1_000)} kWp", border=False,height=95)
        

        b.metric("in Betrieb seit", allgemein.loc[allgemein["id"]==s]["year"].values[0], border=False,height=95)        
        
        c.metric("Ausrichtung", allgemein.loc[allgemein["id"]==s]["orientation"].values[0], border=False, height="stretch") # ← ↖ ↑ ↗ → 
        
        
        gesamt_ertrag = get_Gesamtertrag(s)
        gesamt_ertrag_str = f"{gesamt_ertrag:,}".replace(",", ".")        
        d.metric("Gesamtertrag", f"{gesamt_ertrag_str} kWh", "+3 kWh", border=False,height=103)
        
        panel_col, transformer_col = st.columns([1,1])
        
        panel_col.metric("Solarmodule",f"🔆 {allgemein.loc[allgemein["id"]==s]["module_count"].values[0]}",allgemein.loc[allgemein["id"]==s]["module_brand"].values[0],delta_color="off")
        transformer_col.metric("Wechselrichter",f"⚡ {allgemein.loc[allgemein["id"]==s]["transformer_count"].values[0]}",allgemein.loc[allgemein["id"]==s]["transformer_brand"].values[0],delta_color="off")
   

    with col3:
        from numpy.random import default_rng as rng
        import ast 
        changes = list(rng(4).standard_normal(20))
        data_col3 = [sum(changes[:i]) for i in range(20)]
        delta = round(data_col3[-1], 2)
        temp = get_heutige_Leistung(s)
        if len(temp)>0:
            heute = date.today()
            heutiger_ertrag = get_Ertrag_dieser_Monat(s)[ heute.day-1]

            heutiger_ertrag_str = f"{heutiger_ertrag:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
            delta=temp[-1]
            delta = delta * (5 / 60) / 1000
            delta_str = f"{delta:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")
            from datetime import datetime

            wochentag = {
                0: "Mo.",
                1: "Di.",
                2: "Mi.",
                3: "Do.",
                4: "Fr.",
                5: "Sa.",
                6: "So."
            }

            heute = datetime.now()
            datum = f"heute {wochentag[heute.weekday()]} {heute.day:02d}. {heute.strftime('%B')} {heute.year}"
            st.metric(datum, f"{heutiger_ertrag_str} kWh", f"{delta_str} kWh", chart_data=np.round(temp/1000,1), chart_type="area", border=True    )
        else:
            st.error("🚨 Von heute sind leider keine Daten verfügbar!")
        a, b = st.columns(2)
        ertrag = get_Ertrag_dieser_Monat(s)
        ertrag_monat_sum = np.round(ertrag.sum(), 1)
        ertrag_monat_str = f"{ertrag_monat_sum:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
        if ertrag_monat_sum !=0:
            a.metric(
                    "Ertrag dieser Monat:", f"{ertrag_monat_str} kWh", chart_data=ertrag, chart_type="bar", border=True,
                )
        else:
            a.error("🚨 Diesen Monat sind leider keine Daten verfügbar!")
        ertrag = get_Ertrag_dieses_Jahr(s)
        ertrag_jahr_sum = np.round(ertrag.sum())
        ertrag_jahr_str = f"{ertrag_jahr_sum:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
        if ertrag_jahr_sum !=0:
            b.metric(
                "Ertrag dieses Jahr:", f"{ertrag_jahr_str} kWh", chart_data=ertrag, chart_type="bar", border=True,
            )
        else:
            b.error("🚨 Dieses Jahr sind leider keine Daten verfügbar!")
      
    
    st.space()
    st.divider()
    st.space()

# manager.update_quality_only()
# manager.update_last_day_only()
# data = manager.get_dataframe()

# for s in data["s"].unique():
    
#     temp = data.loc[data.s==s]
#     temp = temp[["letzter Tag", "Datenqualität"]].reset_index()
#     temp.columns=["Wechselrichter","letzter Tag", "Datenqualität"]
#     temp["Datenqualität"] = temp["Datenqualität"].apply(qualitäts_emoji)
  
from update_ertragsdaten import update_ertrag
from update_leistungsdaten import update_leistung  
update_ertrag()
update_leistung()