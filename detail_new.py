from datetime import date
import pandas as pd
import polars as pl
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from backend_leistung import get_day_and_update

from utils import  get_Ertrag_dieser_Monat,get_Ertrag_dieses_Jahr,get_Gesamtertrag

#from ui_calendar import plot_calendar_heatmap
from calendar_plot import plot_calendar_heatmap

import pandas as pd

import datetime
standorte = ["badboll","esslingen","geislingen","holzgerlingen","hospitalhof","karlsruhe","mettingen","muensingen","tuebingen","waiblingen"]
allgemein = pd.read_csv("allgemein.csv")
with st.sidebar:
    def format(s):
        return f":red-badge[:material/error: {allgemein.loc[allgemein['id']==s]['title'].values[0]}]"
        return f":greenray-badge[:material/check: {allgemein.loc[allgemein['id']==s]['title'].values[0]}]"
        return f":orange-badge[:material/warning: {allgemein.loc[allgemein['id']==s]['title'].values[0]}]"
        return allgemein.loc[allgemein["id"]==s]["title"].values[0]#+":orange-badge[:material/warning: Auffälligkeiten!]" # :green-badge[:material/check: Alles in Ordnung!] :red-badge[:material/error: Fehlende Daten!]"
    selected_standort = st.radio(
    "**Aktueller Status:**",
    standorte,
    format_func=format,
    captions=["" for s in standorte],
    label_visibility="visible"
)
# selected_standort = st.pills("Standort", standorte, selection_mode="single",default="badboll")



if "selected_date" not in st.session_state:
    st.session_state.selected_date = datetime.date.today().isoformat()


LAT, LON, TZ = 48.39, 9.36, "Europe/Berlin"
#ALTITUDE = 411
#STANDORT = "muensingen"
FILE_PATH = "app/data/leistung.parquet"

#TILT = 30.0                # PV-Modul Neigung (°)
#AZIMUTH =155.0             # PV-Ausrichtung (°) – 180 = Süden

# Farben / Styling
BASE_COLOR = "#FFCC00"
#NUM_LAYERS = 6
#ALPHAS = np.linspace(0.03, 0.30, NUM_LAYERS)
WR_DASH = ['dot', 'dash', 'dashdot', 'longdashdot', 'dot', 'dash', 'dashdot']

from ui_tagesleistung import load_pv_data, get_sun_times, create_pv_plot

#from ui_utils import st_Anlagenfoto

st.header(allgemein.loc[allgemein["id"]==selected_standort]["title"].values[0],width="content")

with st.container(horizontal=True,border=True):
    # st_Anlagenfoto(selected_standort,allgemein.loc[allgemein["id"]==selected_standort]["title"].values[0])
    peak = allgemein.loc[allgemein["id"]==selected_standort]["peak"].values[0]
    st.metric("Peak Leistung", f"{round(peak/1_000)} kWp", border=False,height=103)
    st.metric("in Betrieb seit", allgemein.loc[allgemein["id"]==selected_standort]["year"].values[0], border=False,height="stretch")        
    st.metric("Ausrichtung", allgemein.loc[allgemein["id"]==selected_standort]["orientation"].values[0], border=False, height="stretch") # ← ↖ ↑ ↗ → 
    
    gesamt_ertrag = get_Gesamtertrag(selected_standort)
    gesamt_ertrag_str = f"{round(gesamt_ertrag/1_000):,}".replace(",", ".")      
    gestriger_ertrag = get_Ertrag_dieser_Monat(selected_standort)[ date.today().day-2]  
    gestriger_ertrag = f"{gestriger_ertrag:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")

    st.metric("Gesamtertrag", f"{gesamt_ertrag_str} MWh", f"+{gestriger_ertrag} kWh", border=False,height="stretch")
    
    st.metric("Solarmodule",f"🔆 {allgemein.loc[allgemein['id']== selected_standort]['module_count'].values[0]}",allgemein.loc[allgemein["id"]==selected_standort]["module_brand"].values[0],delta_color="off")
    st.metric("Wechselrichter",f"⚡ {allgemein.loc[allgemein['id']==selected_standort]['transformer_count'].values[0]}",allgemein.loc[allgemein["id"]==selected_standort]["transformer_brand"].values[0],delta_color="off")
   
    
with st.container(horizontal=True,horizontal_alignment="center"):


    option_map = {
            0: "kW",
            1: "kWp",    
        }
    selection = st.segmented_control(
        "Einheit:",
        options=option_map.keys(),
        format_func=lambda option: option_map[option],
        selection_mode="single",
        default=0,
        help="Mit :blue-background[**kWp**] wird die Leistung **relativ zur Gesamtleistung** der Anlage angezeigt.",
        label_visibility="visible"
    )
    st.space("stretch")
    st.date_input(label="Datum:",width=100,format="MM.DD.YYYY",label_visibility="visible")
    st.space("stretch")
    option_map = {
            0: "Gesamt",
            1: "Wechselrichter",    
            2: "Strings",   
        }
    selection = st.segmented_control(
        "Anzeige:",
        options=option_map.keys(),
        format_func=lambda option: option_map[option],
        selection_mode="single",
        default=0,
        help='''
:red[Streamlit] :orange[can] :green[write] :blue[text] :violet[in],
        
Hello :gray[pretty] :rainbow[colors] and :blue-background[highlight] text.
        ''',
        label_visibility="visible"
    )
    
    
try:
    leistung_gesamt, leistung_wr = load_pv_data(FILE_PATH, selected_standort, pd.to_datetime(st.session_state.selected_date ).date())
    sunrise, sunset = get_sun_times(LAT, LON, TZ, pd.Timestamp(pd.to_datetime(st.session_state.selected_date ).date(), tz=TZ))
    times = pd.date_range(start=sunrise.floor('min'), end=sunset.ceil('min'), freq='1min', tz=TZ)

    #EFFICENCY=40
    #p_dc_simple = compute_clearsky_pv(LAT, LON, TZ, times, TILT, AZIMUTH, EFFICENCY)

    fig = create_pv_plot(leistung_gesamt, leistung_wr, sunrise, sunset)
    st.plotly_chart(fig,selection_mode="points",on_select="rerun",config={
        "displayModeBar": False,
        "displaylogo": False,
        "doubleClick": False,
        "scrollZoom": False,
        "staticPlot": False,
        "editSelection": False,
        "responsive":False,
        #"modeBarButtonsToAdd": ["select2d", "lasso2d","pan2d"],
        #"modeBarButtonsToRemove": ["zoom2d",  "autoScale2d", "resetScale2d"]
    },)
except Exception as e:
    st.error("Keine Daten verfügbar!")
    
##################################################################################################

ertrag = (
    pd.read_parquet("app/data/ertrag.parquet")
      .assign(date=lambda df: pd.to_datetime(df["date"]).dt.date)
      .loc[lambda df: df["standort"] == selected_standort]
)

start = (pd.Timestamp.today() - pd.DateOffset(years=1)).date()
end   = pd.Timestamp.today().date()

ertrag = (
    ertrag.loc[lambda df: df["date"] >= start]
          .groupby("date").sum()
          .reindex(pd.date_range(start, end, freq="D"))
          .rename_axis("date")
          .reset_index()
          .assign(value=lambda df: df["value"].fillna(0))   # <-- Fill
)

#custom, colorscale with warm yellow tones
Yellows = [[0.0, 'rgb(255, 250, 220)'],[1.0, 'rgb(255, 180, 0)']]

# add a small rounded box in black to the plot


# fig_heatmap.show(config={
#     "displayModeBar": False,
#     "displaylogo": False,
#     "doubleClick": False,
#     # "scrollZoom": False,
#     "staticPlot": False,
#     #"modeBarButtonsToAdd": ["select2d", "lasso2d","pan2d"],
#     #"modeBarButtonsToRemove": ["zoom2d",  "autoScale2d", "resetScale2d"]
# })





with st.container(horizontal=True):
    option_map = {
    0: ":material/sunny: Ertrag",
    1: ":material/error: Fehler",
  
}
    ertrag_oder_fehler = st.segmented_control(
        "Tool",
        options=option_map.keys(),
        format_func=lambda option: option_map[option],
        selection_mode="single",
        default=0,
        label_visibility="hidden"
    )
    st.space("stretch")
    option_map = {
        0: ":material/Bolt: Gesamt",
        1: "WR1",
        2: "WR2",
        3: "WR3",
    
    }
    selection = st.segmented_control(
        "Tool",
        options=option_map.keys(),
        format_func=lambda option: option_map[option],
        selection_mode="single",
        default=0,
        label_visibility="hidden"
)

if ertrag_oder_fehler == 0:
    # fig_heatmap = plot_calendar_heatmap(ertrag, 
    #                                     date_col='date', 
    #                                     value_col='value', 
    #                                     colorscale=Yellows, 
    #                                     title='Calendar Heatmap (Heatmap)', 
    #                                     locale_name='de_DE', 
    #                                     scale=30,
    #                                     grid_width=4,
    #                                     highlight_date=pd.to_datetime(st.session_state.selected_date ).date())
    fig_heatmap = plot_calendar_heatmap(ertrag, 
                                        date_col='date', 
                                        value_col='value', 
                                        formatting_colorscale=Yellows, 
                                        formatting_locale='de_DE', 
                                        formatting_scale=30,
                                        grid_width=4,
                                        formatting_value_formatter= lambda value: round(value/1_000),
                                        highlight_date=pd.to_datetime(st.session_state.selected_date).date())
    
else:
    from errors import compute_final_for_standort
    df = compute_final_for_standort(selected_standort).to_pandas().sort_values(by="date")
    df = df.loc[df.date.dt.date>(date.today()-pd.Timedelta(days=365))]
    fig_heatmap = plot_calendar_heatmap(df, 
                                        date_col='date', 
                                        value_col='mean_correlation', 
                                        formatting_colorscale="Reds_r", 
                                        formatting_locale='de_DE', 
                                        formatting_scale=30,
                                        grid_width=4,
                                        formatting_value_formatter= lambda value: round(float(value)*100),
                                        formatting_zmin=0,
                                        formatting_zmax=1,
                                        highlight_date=pd.to_datetime(st.session_state.selected_date).date())
    # fig_heatmap = plot_calendar_heatmap(df.to_pandas(), date_col='date', value_col='mean_correlation', colorscale="Reds", title='Calendar Heatmap (Heatmap)', locale_name='de_DE', scale=30,grid_width=4,
    #             highlight_date=pd.to_datetime(st.session_state.selected_date ).date())

# placeholder_plot = st.empty()#container(width=1350,height=210)#1350 210
# with placeholder_plot: 
event = st.plotly_chart(fig_heatmap,selection_mode="points",on_select="rerun",config={
    "displayModeBar": False,
    "displaylogo": False,
    "doubleClick": False,
    "scrollZoom": False,
    "staticPlot": False,
    "editSelection": False,
    "responsive":False,
    #"modeBarButtonsToAdd": ["select2d", "lasso2d","pan2d"],
    #"modeBarButtonsToRemove": ["zoom2d",  "autoScale2d", "resetScale2d"]
})
if event:
    try: 
        print(event.selection.points[0]["text"])
        st.session_state.selected_date = event.selection.points[0]["text"].split("'")[1]
        st.rerun()
    except Exception:
        pass
    
    
