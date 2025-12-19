import streamlit as st
import time
from datetime import date
import pandas as pd
import streamlit as st
from src.ui.year import plot_calendar_heatmap
from src.ui.day import plot_day

import datetime
print("RERUN WHOLE SCRIPT")
standorte = ["badboll","esslingen","geislingen","holzgerlingen","hospitalhof","karlsruhe","mettingen","muensingen","tuebingen","waiblingen"]

allgemein = pd.read_csv("data/allgemein.csv")

with st.sidebar:
    def format(s):
        return f":red-badge[:material/error: {allgemein.loc[allgemein['id']==s]['title'].values[0]}]"
        # return f":greenray-badge[:material/check: {allgemein.loc[allgemein['id']==s]['title'].values[0]}]"
        # return f":orange-badge[:material/warning: {allgemein.loc[allgemein['id']==s]['title'].values[0]}]"
        # return allgemein.loc[allgemein["id"]==s]["title"].values[0]#+":orange-badge[:material/warning: Auffälligkeiten!]" # :green-badge[:material/check: Alles in Ordnung!] :red-badge[:material/error: Fehlende Daten!]"
    selected_standort = st.radio(
    "**Aktueller Status:**",
    standorte,
    format_func=format,
    captions=["" for s in standorte],
    label_visibility="visible"
)


if "selected_date" not in st.session_state:
    st.session_state.selected_date = datetime.date.today().isoformat()

TZ = "Europe/Berlin"


#from ui_utils import st_Anlagenfoto

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
   

##############################################################################


Yellows = [[0.0, 'rgb(255, 250, 220)'],[1.0, 'rgb(255, 180, 0)']]




@st.fragment
def fragment():
   # print("START:", st.session_state.selected_date)
    heatmap_container = st.container(border=False,height=210,horizontal_alignment="center")

    fig_heatmap = plot_calendar_heatmap(st.session_state[selected_standort].load_daily_yield_last_year(), 
                                    date_col='date', 
                                    value_col='value_sum', 
                                    formatting_colorscale=Yellows, 
                                    formatting_locale='de', 
                                    formatting_scale=30,
                                    grid_width=4,
                                    formatting_value_formatter= lambda value: f"⚡ {round(value)} kWh",
                                    highlight_date=pd.to_datetime(st.session_state.selected_date ).date())

    event = heatmap_container.plotly_chart(
                fig_heatmap,
                selection_mode="points",
                on_select="rerun",
                config={
                    "displayModeBar": False,
                    "displaylogo": False,
                    "doubleClick": False,
                    "scrollZoom": False,
                    "staticPlot": False,
                    "editSelection": False,
                    "responsive": False,
                },
                width="content",
            )
    if len(event.selection.points) >0:
    # print(event)
        selected = event.selection.points[0]["text"].split("'")[1]
        st.session_state.selected_date = selected
        print("END: SELECTION", st.session_state.selected_date)
    else:
        
        print("END: NO SELECTION", st.session_state.selected_date)

fragment()



