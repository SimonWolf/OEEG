import pandas as pd
import numpy as np
import plotly.graph_objects as go

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
NUM_LAYERS = 10
ALPHAS = np.linspace(0.03, 0.30, NUM_LAYERS)
WR_DASH = ['dot', 'dash', 'dashdot', 'longdashdot', 'dot', 'dash', 'dashdot']



def plot_day(leistung_gesamt, leistung_wr, sunrise, sunset):
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

    # Einzel-WR-Leistung
    for i, wr in enumerate(leistung_wr["wr"].unique()[::-1]):
        temp_x = pd.to_datetime(leistung_wr.loc[leistung_wr["wr"]==wr]["Datetime"])
        temp_y = leistung_wr.loc[leistung_wr["wr"]==wr]["value"] / 1_000
        fig.add_trace(go.Scatter(
            x=temp_x, y=temp_y, mode="lines",
            line=dict(color="#365FB7", width=2, dash=WR_DASH[i % len(WR_DASH)]),
            name=f"WR {wr}",
            hovertemplate="%{y:.2f} kW"
        ))

    # Gesamtleistung (nach den WR-Traces hinzufügen, damit sie in der Legende zuletzt erscheint)
    fig.add_trace(go.Scatter(
        x=x, y=y_kw, mode="lines", line=dict(color=BASE_COLOR, width=4),
        name="Gesamt", hovertemplate="%{y:.2f} kW"
    ))
    # Layout
    fig.update_layout(
        template="simple_white",
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
            tickfont=dict(size=16, family="sans-serif"),
        ),
        dragmode=False,
        font=dict(family="sans-serif", size=15),
        yaxis=dict(title="Leistung (kW)", showgrid=True, gridcolor="#f2f2f2", zeroline=False, tickfont=dict(size=16, family="sans-serif")),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", bordercolor="gray", font_size=16, font_family="sans-serif", align="left"),
        legend=dict(font=dict(family="sans-serif", size=14))
    )
    fig.update_yaxes(range=[0, max(y_kw)])
    fig.update_layout(
        xaxis=dict(showgrid=True, zeroline=False, showline=True,fixedrange = True),
        yaxis=dict(showgrid=True, zeroline=False, showline=True,fixedrange = True),
    )
    return fig