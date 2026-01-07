import streamlit as st
#from utils import  get_Ertrag_dieser_Monat,get_Ertrag_dieses_Jahr,get_Gesamtertrag
from datetime import date,datetime
import numpy as np
from src.ui.anlagenfoto import st_Anlagenfoto
#from backend_leistung import get_heutige_Leistung





st.title("Unsere Solaranlagen")
 
for s in ["muensingen", "karlsruhe", "badboll", "mettingen", "holzgerlingen", "tuebingen", "hospitalhof","waiblingen","esslingen", "geislingen",]:

   

    col1, col2, col3 = st.columns([1,1,1])
    with col1:
            st_Anlagenfoto(s,st.session_state[s].meta.get("title"))
        
    with col2:        
        a, b = st.columns(2,border = False)
        c, d = st.columns(2,border = False)

        a.metric("Peak Leistung", f"{round(st.session_state[s].meta.get('peak')/1_000)} kWp", border=False,height=95)

        b.metric("in Betrieb seit", st.session_state[s].meta.get("year"), border=False,height=95)        
        
        c.metric("Ausrichtung", st.session_state[s].meta.get("orientation"), border=False, height="stretch") # ← ↖ ↑ ↗ → 
        
        
        gestriger_ertrag = st.session_state[s].load_daily_yield_this_month()[date.today().day-2]
        gestriger_ertrag = f"{gestriger_ertrag:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")

        d.metric("Gesamtertrag", f"{round(st.session_state[s].load_total_yield()/1_000)} MWh", f"+{gestriger_ertrag} kWh", border=False,height=103)
        
        panel_col, transformer_col = st.columns([1,1])
        
        panel_col.metric("Solarmodule",f"🔆 {st.session_state[s].meta.get('module_count')}",st.session_state[s].meta.get("module_brand"),delta_color="off")
        transformer_col.metric("Wechselrichter",f"⚡ {st.session_state[s].meta.get('transformer_count')}",st.session_state[s].meta.get("transformer_brand"),delta_color="off")
   

    with col3:
        from numpy.random import default_rng as rng
        changes = list(rng(4).standard_normal(20))
        data_col3 = [sum(changes[:i]) for i in range(20)]
        delta = round(data_col3[-1], 2)
        try:
            temp = st.session_state[s].load_total_power_of_day(date.today(),).P_gesamt.to_numpy() #ttl_hash= int(datetime.now().timestamp() //300)
        
            heutiger_ertrag = st.session_state[s].load_daily_yield_this_month()[date.today().day-1]
            heutiger_ertrag_str = f"{heutiger_ertrag:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
            if temp.shape[0]<2:
                delta = 0
            else:

                delta=temp[-1]
                delta = delta * (5 / 60) / 1000
            delta_str = f"{delta:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")

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
        except Exception as e:
            print(e)
            st.error("🚨 Von heute sind leider keine Daten verfügbar!")
        a, b = st.columns(2)
        ertrag = st.session_state[s].load_daily_yield_this_month()
        ertrag_monat_sum = np.round(ertrag.sum(), 1)
        ertrag_monat_str = f"{ertrag_monat_sum:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
        if ertrag_monat_sum !=0:
            a.metric(
                    "Ertrag dieser Monat:", f"{ertrag_monat_str} kWh", chart_data=ertrag, chart_type="bar", border=True,
                )
        else:
            a.error("🚨 Diesen Monat sind leider keine Daten verfügbar!")
        ertrag = st.session_state[s].load_monthly_yield_this_year()
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
  
# from update_ertragsdaten import update_ertrag
# # from update_leistungsdaten import update_leistung  
# update_ertrag()
#update_leistung()