import streamlit as st
from datetime import date

def create_header(allgemein,selected_standort):
    st.header(allgemein.loc[allgemein["id"]==selected_standort]["title"].values[0],width="content")

    with st.container(horizontal=True,border=True):
        # st_Anlagenfoto(selected_standort,allgemein.loc[allgemein["id"]==selected_standort]["title"].values[0])
        peak = allgemein.loc[allgemein["id"]==selected_standort]["peak"].values[0]
        st.metric("Peak Leistung", f"{round(peak/1_000)} kWp", border=False,height=103)
        st.metric("in Betrieb seit", allgemein.loc[allgemein["id"]==selected_standort]["year"].values[0], border=False,height="stretch")        
        st.metric("Ausrichtung", allgemein.loc[allgemein["id"]==selected_standort]["orientation"].values[0], border=False, height="stretch") # ← ↖ ↑ ↗ → 
        
        gesamt_ertrag = st.session_state[selected_standort].load_total_yield()
        gesamt_ertrag_str = f"{round(gesamt_ertrag/1_000):,}".replace(",", ".")      
        gestriger_ertrag = st.session_state[selected_standort].load_daily_yield_this_month()[ date.today().day-2]  
        gestriger_ertrag = f"{gestriger_ertrag:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")

        st.metric("Gesamtertrag", f"{gesamt_ertrag_str} MWh", f"+{gestriger_ertrag} kWh", border=False,height="stretch")
        
        st.metric("Solarmodule",f"🔆 {allgemein.loc[allgemein['id']== selected_standort]['module_count'].values[0]}",allgemein.loc[allgemein["id"]==selected_standort]["module_brand"].values[0],delta_color="off")
        st.metric("Wechselrichter",f"⚡ {allgemein.loc[allgemein['id']==selected_standort]['transformer_count'].values[0]}",allgemein.loc[allgemein["id"]==selected_standort]["transformer_brand"].values[0],delta_color="off")