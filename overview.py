import streamlit as st
import pandas as pd



st.title("Übersicht aller Solaranlagen")
data = pd.read_pickle("overview.pkl")

st.dataframe(
    data,
    column_config={
        "letzter Tag": st.column_config.AreaChartColumn(
            "letzter Tag",
            width="medium",
            help="The kwH consumption in the last 24 hours",
            y_min=0,
            y_max=10_000,
        ),
        #"AnlagenKWP": st.column_config.NumberColumn(
        #    "Max. Leistung",
        #    width="small",
        #    help="The installed capacity of the solar panels in KWp",
        #    format="%.2f KWp",
        #),
        #"days":st.column_config.ImageColumn(
        #    "Aktualität",
        #),
    },
    hide_index=False,
    height=35 * len(data) + 37,
    row_height=35,
    # selection_mode="single-row",
    # on_select="rerun"
    
)
