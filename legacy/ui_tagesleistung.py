from datetime import date
import pandas as pd
import polars as pl
import numpy as np
import plotly.graph_objects as go
import pvlib

from backend_leistung import get_day_and_update
# ------------------------------------------
# CONFIG / PARAMETER
# ------------------------------------------
LAT, LON, TZ = 48.39, 9.36, "Europe/Berlin"
ALTITUDE = 411
STANDORT = "muensingen"
FILE_PATH = "app/data/leistung.parquet"

TILT = 30.0                # PV-Modul Neigung (°)
AZIMUTH =155.0             # PV-Ausrichtung (°) – 180 = Süden

# Farben / Styling
BASE_COLOR = "#FFCC00"
NUM_LAYERS = 6
ALPHAS = np.linspace(0.03, 0.30, NUM_LAYERS)
WR_DASH = ['dot', 'dash', 'dashdot', 'longdashdot', 'dot', 'dash', 'dashdot']

# ------------------------------------------
# FUNKTIONEN
# ------------------------------------------
def load_pv_data(file_path: str, standort: str, datum: date):
    """Lade PV-Leistungsdaten aus Parquet-Datei und aggregiere Gesamtleistung."""
   # df_polars = pl.scan_parquet(file_path)
    df_polars = pl.LazyFrame(get_day_and_update(standort,datum))
    # Gesamtleistung je Zeitpunkt
    leistung_gesamt = (
        df_polars
        .filter(
            (pl.col("standort").str.to_lowercase() == standort.lower()) &
            (pl.col("Datetime").dt.date() == datum) &
            (pl.col("string") == -1) &
            (pl.col("sensor") == "P")
        )
        .group_by("Datetime")
        .agg(pl.col("value").sum().alias("P_gesamt"))
        .sort("Datetime")
        .collect(engine="streaming")
        .to_pandas()
    )
    
    # Einzel-WR-Leistung
    leistung_wr = (
        df_polars
        .filter(
            (pl.col("standort").str.to_lowercase() == standort.lower()) &
            (pl.col("Datetime").dt.date() == datum) &
            (pl.col("string") == -1) &
            (pl.col("sensor") == "P")
        )
        .sort("Datetime")
        .collect(engine="streaming")
        .to_pandas()
    )
    
    return leistung_gesamt, leistung_wr

def get_sun_times(lat: float, lon: float, tz: str, datum: pd.Timestamp):
    """Berechne Sonnenaufgang und -untergang."""
    location = pvlib.location.Location(lat, lon, tz=tz, altitude=ALTITUDE)
    times_for_sun = pd.DatetimeIndex([datum + pd.Timedelta(hours=12)], tz=tz)
    sun_df = location.get_sun_rise_set_transit(times_for_sun, method='spa')
    return sun_df['sunrise'].iloc[0], sun_df['sunset'].iloc[0]

# def compute_clearsky_pv(lat: float, lon: float, tz: str, times: pd.DatetimeIndex,
#                         tilt: float, azimuth: float, eff: float):
#     """Berechne theoretische maximale PV-Leistung (Clearsky)."""
#     location = pvlib.location.Location(lat, lon, tz=tz, altitude=ALTITUDE)
#     clearsky = location.get_clearsky(times, model='ineichen')
#     solarpos = location.get_solarposition(times)
    
#     dni_extra = pvlib.irradiance.get_extra_radiation(times)
#     poa = pvlib.irradiance.get_total_irradiance(
#         surface_tilt=tilt,
#         surface_azimuth=azimuth,
#         solar_zenith=solarpos['apparent_zenith'],
#         solar_azimuth=solarpos['azimuth'],
#         dni=clearsky['dni'],
#         ghi=clearsky['ghi'],
#         dhi=clearsky['dhi'],
#         dni_extra=dni_extra,
#         model='haydavies'
#     )
    
#     p_dc_simple = poa['poa_global']  * eff
#     return p_dc_simple

def create_pv_plot(leistung_gesamt, leistung_wr, sunrise, sunset):
    """Erzeuge Plotly-Figure mit Gesamt- und WR-Leistung + Clearsky."""
    x = pd.to_datetime(leistung_gesamt["Datetime"])
    y_kw = leistung_gesamt["P_gesamt"].to_numpy() / 1000.0

    fig = go.Figure()

    # Gefüllte Layers
    for i in range(NUM_LAYERS):
        frac = (i + 1) / NUM_LAYERS
        y_layer = y_kw * frac
        fill_mode = "tozeroy" if i == 0 else "tonexty"
        rgba = f"rgba(255,204,0,{ALPHAS[i]:.3f})"
        fig.add_trace(go.Scatter(
            x=x, y=y_layer, mode="lines", line=dict(width=0),
            fill=fill_mode, fillcolor=rgba, hoverinfo="skip", showlegend=False
        ))

    # Gesamtleistung
    fig.add_trace(go.Scatter(
        x=x, y=y_kw, mode="lines", line=dict(color=BASE_COLOR, width=4),
        name="Gesamt", hovertemplate="%{y:.2f} kW"
    ))

    # Einzel-WR-Leistung
    for i, wr in enumerate(leistung_wr["wr"].unique()):
        temp_x = pd.to_datetime(leistung_wr.loc[leistung_wr["wr"]==wr]["Datetime"])
        temp_y = leistung_wr.loc[leistung_wr["wr"]==wr]["value"] / 1_000
        fig.add_trace(go.Scatter(
            x=temp_x, y=temp_y, mode="lines",
            line=dict(color="#365FB7", width=2, dash=WR_DASH[i % len(WR_DASH)]),
            name=f"WR {wr}",
            hovertemplate="%{y:.2f} kW"
        ))

    #Clearsky / theoretisches Maximum
    # fig.add_trace(go.Scatter(
    #     x=p_dc_simple.index,
    #     y=p_dc_simple/1000,
    #     mode="lines",
    #     line=dict(color="orange", width=2, dash="dot"),
    #     name="Clearsky Max"
    # ))
    
    # fig.add_trace(go.Scatter(
    #     x=df.index,
    #     y=df["Watts"]/1000,
    #     mode="lines",
    #     line=dict(color="orange", width=2, dash="dot"),
    #     name="Vorhersage"
    # ))

    # Layout
    fig.update_layout(
        template="simple_white",
        #margin=dict(l=60, r=20, t=30, b=60),
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(
            title="Uhrzeit",
            tickformat="%H:%M",
            showgrid=False,
            showline=True,
            linewidth=1,
            linecolor="#cccccc",
            range=[sunrise, sunset],
            showspikes=True,
            spikecolor="gray",
            spikethickness=3,
            spikesnap="cursor",
            spikemode="across",
            tickfont=dict(size=16),
        ),
        dragmode=False,
        font_size=15,
        yaxis=dict(title="Leistung (kW)", showgrid=True, gridcolor="#f2f2f2", zeroline=False,tickfont=dict(size=16),),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", bordercolor="gray", font_size=16, font_family="Arial", align="left", )
    )
    fig.update_yaxes(range=[0, max(y_kw)])
    fig.update_layout(
        xaxis=dict(showgrid=True, zeroline=False, showline=True,fixedrange = True),
        yaxis=dict(showgrid=True, zeroline=False, showline=True,fixedrange = True),
    )
    return fig

# ------------------------------------------
# MAIN
# ------------------------------------------
