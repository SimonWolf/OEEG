from datetime import date
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_yield(
    standort,
    monthly_df: pd.DataFrame | None = None,
    yearly_df: pd.DataFrame | None = None,
    current_year: int | None = None,
    drop_latest_month: bool = True,
) -> go.Figure:
    """Erzeuge kombinierten Plot mit monatlichem und jährlichem Ertrag.

    Parameter:
    - standort: Standort-Objekt mit Methoden `load_yield_per_month` und
      `load_yield_per_year` (wird nur genutzt, wenn DataFrames nicht übergeben werden)
    - monthly_df: Optionaler DataFrame mit Spalten `year`, `month`, `value_sum`
    - yearly_df: Optionaler DataFrame mit Spalten `year`, `value_sum`
    - current_year: Jahr, das visuell hervorgehoben wird (Default: aktuelles Jahr)
    - drop_latest_month: Entfernt den letzten Monatswert aus `monthly_df`
      (gleiches Verhalten wie im Notebook `[:-1]`)
    """
    if current_year is None:
        current_year = date.today().year

    if monthly_df is None:
        monthly_df = standort.load_yield_per_month()
    if yearly_df is None:
        yearly_df = standort.load_yield_per_year()

    monthly_df = monthly_df.copy()
    yearly_df = yearly_df.copy()

    if drop_latest_month and not monthly_df.empty:
        monthly_df = monthly_df.iloc[:-1]

    month_tickvals = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    month_ticktext = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]

    # Fallback-Figur für fehlende Daten
    if monthly_df.empty or yearly_df.empty:
        fig = go.Figure()
        fig.update_layout(
            template="simple_white",
            height=450,
            margin=dict(l=20, r=20, t=40, b=20),
            font=dict(family="sans-serif", size=15),
            hoverlabel=dict(
                bgcolor="white",
                bordercolor="gray",
                font_size=16,
                font_family="sans-serif",
                align="left",
            ),
            annotations=[
                dict(
                    text="Keine Ertragsdaten verfügbar",
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=18),
                )
            ],
        )
        return fig

    band = (
        monthly_df.groupby("month", as_index=False)["value_sum"]
        .agg(min_value="min", max_value="max")
        .sort_values("month")
    )

    years_monthly = sorted(monthly_df["year"].unique())
    bar_colors = [
        "rgb(214,39,40)" if int(y) == int(current_year) else "rgb(31,119,180)"
        for y in yearly_df["year"]
    ]

    fig = make_subplots(
        rows=2,
        cols=1,
        vertical_spacing=0.12,
        subplot_titles=("Monatlicher Ertrag", "Jährlicher Ertrag"),
    )

    fig.add_trace(
        go.Scatter(
            x=band["month"],
            y=band["max_value"] / 1_000,
            mode="lines",
            line=dict(width=0),
            hoverinfo="skip",
            showlegend=False,
            name="Monatliche Spanne",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=band["month"],
            y=band["min_value"] / 1_000,
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(31,119,180,0.15)",
            hoverinfo="skip",
            showlegend=False,
            name="Min-Max pro Monat",
        ),
        row=1,
        col=1,
    )

    for year in years_monthly:
        d = monthly_df[monthly_df["year"] == year].sort_values("month")
        is_current = int(year) == int(current_year)

        fig.add_trace(
            go.Scatter(
                x=d["month"],
                y=d["value_sum"] / 1_000,
                mode="lines",
                name=str(year),
                line=dict(
                    color="rgb(214,39,40)" if is_current else "rgb(31,119,180)",
                    width=3.5 if is_current else 1.2,
                ),
                opacity=1.0 if is_current else 0.35,
                legendgroup=str(year),
                hoverinfo="skip" if not is_current else "all",
                hovertemplate=(
                    "<b>%{customdata} %{x}</b><br>%{y:.1f} MWh<extra></extra>"
                    if is_current
                    else None
                ),
                customdata=[str(year)] * len(d),
            ),
            row=1,
            col=1,
        )

    fig.add_trace(
        go.Bar(
            x=yearly_df["year"],
            y=yearly_df["value_sum"] / 1_000,
            name="Jährlicher Ertrag",
            marker_color=bar_colors,
            hovertemplate="%{y:.1f} MWh<extra></extra>",
        ),
        row=2,
        col=1,
    )

    fig.update_xaxes(
        tickmode="array",
        tickvals=month_tickvals,
        ticktext=month_ticktext,
        title_text="Monat",
        tickfont=dict(size=16, family="sans-serif"),
        showgrid=True,
        zeroline=False,
        showline=True,
        fixedrange=True,
        row=1,
        col=1,
    )
    fig.update_xaxes(
        tickmode="array",
        tickvals=yearly_df["year"].tolist(),
        title_text="Jahr",
        tickfont=dict(size=16, family="sans-serif"),
        showgrid=True,
        zeroline=False,
        showline=True,
        fixedrange=True,
        row=2,
        col=1,
    )

    fig.update_yaxes(
        title_text="Ertrag [MWh]",
        rangemode="tozero",
        tickfont=dict(size=16, family="sans-serif"),
        showgrid=True,
        zeroline=False,
        showline=True,
        fixedrange=True,
        row=1,
        col=1,
    )
    fig.update_yaxes(
        title_text="Ertrag [MWh]",
        rangemode="tozero",
        tickfont=dict(size=16, family="sans-serif"),
        showgrid=True,
        zeroline=False,
        showline=True,
        fixedrange=True,
        row=2,
        col=1,
    )

    fig.update_layout(
        showlegend=False,
        template="simple_white",
        barcornerradius=10,
        height=850,
        margin=dict(l=0, r=0, t=40, b=0),
        dragmode=False,
        font=dict(family="sans-serif", size=15),
        hovermode="closest",
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="gray",
            font_size=16,
            font_family="sans-serif",
            align="left",
        ),
        legend=dict(font=dict(family="sans-serif", size=14)),
    )

    return fig
