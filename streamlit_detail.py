import streamlit as st
import time
from datetime import date
import pandas as pd
import streamlit as st
from src.ui.year import plot_calendar_heatmap
from src.ui.day import plot_day
from src.ui.detail.header import create_header

print("RERUN WHOLE SCRIPT")

standorte = ["badboll","esslingen","geislingen","holzgerlingen","hospitalhof","karlsruhe","mettingen","muensingen","tuebingen","waiblingen"]
Yellows = [[0.0, 'rgb(255, 250, 220)'],[1.0, 'rgb(255, 180, 0)']]
allgemein = pd.read_csv("data/allgemein.csv")

with st.sidebar:
    def format(s):
        try: 
            res = st.session_state[s].load_total_power_of_day(date.today())
            res = res.loc[res.Datetime.dt.date == date.today()]
            # loc by todays date
            if res is None or res.empty:
                return f":red-badge[:material/error:] {st.session_state[s].meta['title']}"
            else:
                return f":green-badge[:material/check:] {st.session_state[s].meta['title']}"
        except Exception:
            return f":red-badge[:material/error:] {st.session_state[s].meta['title']}"
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
    st.session_state.selected_date = date.today().isoformat()

def on_click():
    print("on_click called")
    if "heatmap_state" in st.session_state:
        if len(st.session_state.heatmap_state.selection.points) > 0:
            selected_date = st.session_state.heatmap_state.selection.points[0]["text"].split("'")[1]
        else:
            selected_date = date.today().isoformat()
    else:
        selected_date = date.today().isoformat()

    st.session_state.selected_date = selected_date
    print("Selected date set to:", selected_date)

create_header(allgemein,selected_standort)

   
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

day_plot_ph = st.container(height=450,border=False)
try:
    dt = pd.Timestamp(pd.to_datetime(st.session_state.selected_date ).date(), tz="Europe/Berlin")
    fig = plot_day(
        st.session_state[selected_standort].load_total_power_of_day(dt),
        st.session_state[selected_standort].load_wr_power_of_day(dt),
        *st.session_state[selected_standort].calculate_sunrise_times(dt)
    )
    day_plot_ph.plotly_chart(
        fig,
        selection_mode="points",
        on_select="ignore",
        config={
            "displayModeBar": False,
            "displaylogo": False,
            "doubleClick": False,
            "scrollZoom": False,
            "staticPlot": False,
            "editSelection": False,
            "responsive": False,
        },
    )
except Exception:
    st.error("Keine Daten verfügbar!")




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
    #   
    #                                   highlight_date=pd.to_datetime(st.session_state.selected_date ).date())
    Yellows = [[0.0, 'rgb(255, 250, 220)'],[1.0, 'rgb(255, 180, 0)']]

    fig_heatmap = plot_calendar_heatmap(st.session_state[selected_standort].load_daily_yield_last_year(), 
                                        date_col='date', 
                                        value_col='value_sum', 
                                        formatting_colorscale=Yellows, 
                                        formatting_locale='de', 
                                        formatting_scale=30,
                                        grid_width=4,
                                        formatting_value_formatter= lambda value: f"⚡ {round(value)} kWh",
                                        highlight_date=st.session_state.selected_date)
    
else:
    Reds = [[0.0,'rgb(226, 55, 33)' ],[0.8,'rgb(233, 116, 99)'],[1.0, 'rgb(254, 245, 244)']]
    fig_heatmap = plot_calendar_heatmap(st.session_state[selected_standort].calculate_error_statistics(), 
                                        date_col='date', 
                                        value_col='mean_correlation', 
                                        formatting_colorscale=Reds, 
                                        formatting_locale='de', 
                                        formatting_scale=30,
                                        grid_width=4,
                                        formatting_value_formatter= lambda value: f"⚡ {round(value*100)} %",
                                        highlight_date=st.session_state.selected_date)


heatmap_container = st.container(border=False,height=210,horizontal_alignment="center")


with heatmap_container:
    # fig_heatmap = plot_calendar_heatmap(st.session_state[selected_standort].load_daily_yield_last_year(), 
    #                             date_col='date', 
    #                             value_col='value_sum', 
    #                             formatting_colorscale=Yellows, 
    #                             formatting_locale='de', 
    #                             formatting_scale=30,
    #                             grid_width=4,
    #                             formatting_value_formatter= lambda value: f"⚡ {round(value)} kWh",
    #                            # highlight_date=pd.to_datetime(st.session_state.selected_date ).date(),
    #                             highlight_date= st.session_state.selected_date
    #                            )
    event = st.plotly_chart(
                fig_heatmap,
                selection_mode="points",
                on_select=on_click,
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
                key="heatmap_state",
            )
