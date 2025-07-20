import streamlit as st
import pandas as pd
from utils import OverviewDatenManager



st.title("Übersicht aller Solaranlagen")
manager = OverviewDatenManager(standorte=[
    "badboll", "esslingen", "geislingen", "holzgerlingen", "hospitalhof",
    "karlsruhe", "mettingen", "muensingen", "tuebingen", "waiblingen"
])



data = manager.get_dataframe()

def qualitäts_emoji(wert):
        if wert >= 0.93:
            return "✅"      # alles gut
        elif wert >= 0.5:
            return "⚠️"      # Warnung
        else:
            return "❌"      # Fehler
        
        
placeholders = {}
for s in data["s"].unique():
    temp = data.loc[data.s==s]
    
    st.header(temp.Standort.iloc[0])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.image(f"https://www.oekumenische-energiegenossenschaft.de/datenlogger/{s}/visualisierung/solaranlage.jpg",width=300)

    with col2:
        temp = data.loc[data.s==s]
        temp = temp[["HPTitel","HPBetreiber","Max. Leistung","HPModul","HPWR","HPInbetrieb","HPAusricht"]]
        temp.columns = ["Titel","Betreiber","Max. Leistung","Module","Wechselrichter","Inbetrieb seit","Ausricht"]
        temp = temp.iloc[0]
        temp = temp.str.strip().str.strip("\"")
        def try_fix_encoding(text):
            try:
                return text.encode("latin1").decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                return text  # Rückgabe des Originals, wenn's nicht geht

        # Anwendung auf Series:
        temp = temp.apply(try_fix_encoding)
        
        st.dataframe(temp)
    with col3:
        st.caption("Status Wechselrichter:")
        placeholders[s] = st.empty()
        
        temp = data.loc[data.s==s]
        temp = temp[["letzter Tag", "Datenqualität"]].reset_index()
        temp.columns=["Wechselrichter","letzter Tag", "Datenqualität"]
        temp["Datenqualität"] = temp["Datenqualität"].apply(qualitäts_emoji)
        placeholders[s].dataframe(
            temp,
            column_config={
                "letzter Tag": st.column_config.AreaChartColumn(
                    "letzter Tag",
                    width="medium",
                    help="The kwH consumption in the last 24 hours",
                    y_min=0,
                    y_max=10_000,
                ),
            
            },
            hide_index=True,
            height=35 * len(temp) + 37,
            row_height=35,
            # selection_mode="single-row",
            # on_select="rerun"
            
        )
    st.divider()

manager.update_quality_only()
manager.update_last_day_only()
data = manager.get_dataframe()

for s in data["s"].unique():
    
    temp = data.loc[data.s==s]
    temp = temp[["letzter Tag", "Datenqualität"]].reset_index()
    temp.columns=["Wechselrichter","letzter Tag", "Datenqualität"]
    temp["Datenqualität"] = temp["Datenqualität"].apply(qualitäts_emoji)
    

    placeholders[s].dataframe(
        temp,
        column_config={
            "letzter Tag": st.column_config.AreaChartColumn(
                "letzter Tag",
                width="medium",
                help="The kwH consumption in the last 24 hours",
                y_min=0,
                y_max=10_000,
            ),
        
        },
        hide_index=True,
        height=35 * len(temp) + 37,
        row_height=35,
        # selection_mode="single-row",
        # on_select="rerun"
        
    )