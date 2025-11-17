import streamlit as st
from utils import OverviewDatenManager, get_Ertrag_dieser_Monat,get_Ertrag_dieses_Jahr,get_Gesamtertrag,get_heutige_Leistung
import polars as pl
from datetime import date
import numpy as np
from ui_utils import st_Anlagenfoto
from update_ertragsdaten import update_ertrag
from update_leistungsdaten import update_leistung


STANDORTE = ["muensingen", "karlsruhe", "badboll", "mettingen", "holzgerlingen", "tuebingen", "hospitalhof","waiblingen","esslingen", "geislingen",]


st.title("Unsere Solaranlagen")
manager = OverviewDatenManager(standorte=STANDORTE)
#← ↖ ↑ ↗ → ←↘ ↓ ↙→
helper_map={
            "badboll": "↓ S", "esslingen":"↙ SW", "geislingen":"↙ SW", "holzgerlingen":"↓ S", "hospitalhof":"↓ S",
    "karlsruhe":"↓ SSW", "mettingen":"↓ S", "muensingen":"↓ S", "tuebingen":"↓ SSO", "waiblingen":"↙ SW"
        }

data = manager.get_dataframe()

def qualitäts_emoji(wert):
        if wert >= 0.93:
            return "✅"      # alles gut
        elif wert >= 0.5:
            return "⚠️"      # Warnung
        else:
            return "❌"      # Fehler
        
        
placeholders = {}
for s in STANDORTE:
    temp = data.loc[data.s==s]
    
    #st.header(temp.Standort.iloc[0])
    
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
            st_Anlagenfoto(s,temp.Standort.iloc[0])
        
    with col2:        
        a, b = st.columns(2)
        c, d = st.columns(2)
        a.metric("Peak Leistung", f"{round(int(temp["AnlagenKWP"].iloc[0])/1_000)} kWp", border=False)
        
        jahr= temp["HPInbetrieb"].iloc[0].strip().strip("\"")[-4:]
        if s == "muensingen":
            b.metric("in Betrieb seit", "2017", border=False)
        else:
            b.metric("in Betrieb seit", temp["HPInbetrieb"].iloc[0].strip().strip("\"")[-4:], border=False)        
        
        c.metric("Ausrichtung", helper_map[s], border=False) # ← ↖ ↑ ↗ → 
        gesamt_ertrag = get_Gesamtertrag(s)
        gesamt_ertrag_str = f"{gesamt_ertrag:,}".replace(",", ".")
        
        d.metric("Gesamtertrag", f"{gesamt_ertrag_str} kWh", "+3 kWh", border=False)
      

    with col3:
        from numpy.random import default_rng as rng
        import ast 
        changes = list(rng(4).standard_normal(20))
        data_col3 = [sum(changes[:i]) for i in range(20)]
        delta = round(data_col3[-1], 2)
        temp = data.loc[data.s==s]
        temp = get_heutige_Leistung(s)
        if len(temp)>0:
            heute = date.today()
            heutiger_ertrag = get_Ertrag_dieser_Monat(s)[ heute.day-1]
            print("*"*100)
            print(heute.day,get_Ertrag_dieser_Monat(s))
            heutiger_ertrag_str = f"{heutiger_ertrag:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
            delta=temp[-1]
            delta = delta * (5 / 60) / 1000
            delta_str = f"{delta:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")
            st.metric("heute Sa. 15. November 2025 ", f"{heutiger_ertrag_str} kWh", f"{delta_str} kWh", chart_data=np.round(temp/1000,1), chart_type="area", border=True    )
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

manager.update_quality_only()
manager.update_last_day_only()
data = manager.get_dataframe()

for s in data["s"].unique():
    
    temp = data.loc[data.s==s]
    temp = temp[["letzter Tag", "Datenqualität"]].reset_index()
    temp.columns=["Wechselrichter","letzter Tag", "Datenqualität"]
    temp["Datenqualität"] = temp["Datenqualität"].apply(qualitäts_emoji)
  
from update_ertragsdaten import update_ertrag
from update_leistungsdaten import update_leistung  
update_ertrag()
update_leistung()