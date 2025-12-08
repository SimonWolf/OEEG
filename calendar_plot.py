import numpy as np
import pandas as pd
import plotly.graph_objects as go
import locale
import calendar
from typing import Callable

def _prepare_grid(df: pd.DataFrame, date_col: str, value_col: str) -> tuple[pd.Timestamp, np.ndarray, int, int]:
    """Compute Monday-aligned start date, z-grid values (rows=weekdays, cols=weeks).

    Pads the grid so that the first column starts on the Monday before the first
    date in the DataFrame, and the last column ends on the Sunday after the last
    date. Missing days are left as NaN so no information is lost.

    Returns (start_monday, z_vals, rows, cols) where:
    - start_monday: Monday before/at the first date (normalized)
    - z_vals: 7xN array of values (NaN for missing)
    - rows: 7 (Monday..Sunday)
    - cols: number of weeks spanned including padding
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    if df.empty:
        return pd.Timestamp.today().normalize(), np.empty((7, 0)), 7, 0

    min_date = df[date_col].min().normalize()
    max_date = df[date_col].max().normalize()
    # Align start to Monday and end to Sunday
    start_monday = min_date - pd.Timedelta(days=min_date.weekday())
    end_sunday = max_date + pd.Timedelta(days=(6 - max_date.weekday()))

    total_days = (end_sunday - start_monday).days + 1
    cols = total_days // 7
    rows = 7

    z_vals = np.zeros((rows, cols), dtype=float)
    z_vals[:] = np.nan

    for _, r in df.iterrows():
        d = pd.to_datetime(r[date_col]).normalize()
        offset = (d - start_monday).days
        wi = offset // 7
        wd = d.weekday()
        if 0 <= wd < rows and 0 <= wi < cols:
            z_vals[wd, wi] = r[value_col]

    return start_monday, z_vals, rows, cols


def _rounded_path(x0: float, y0: float, x1: float, y1: float, r: float) -> str:
    """Create an SVG path for a rounded rectangle covering [x0,x1]x[y0,y1]."""
    return (
        f"M{x0+r},{y0} "
        f"L{x1-r},{y0} "
        f"Q{x1},{y0} {x1},{y0+r} "
        f"L{x1},{y1-r} "
        f"Q{x1},{y1} {x1-r},{y1} "
        f"L{x0+r},{y1} "
        f"Q{x0},{y1} {x0},{y1-r} "
        f"L{x0},{y0+r} "
        f"Q{x0},{y0} {x0+r},{y0} Z"
    )

def _month_ticktext(start: pd.Timestamp, end: pd.Timestamp, cols: int) -> list[str]:
    """Generate month labels positioned at the column where the 1st of each month falls."""
    ticktext = [''] * cols
    month_start = pd.Timestamp(start.year, start.month, 1)
    if start.day != 1:
        # move to first of next month
        month_start = (pd.Timestamp(start.year + 1, 1, 1)
                       if start.month == 12 else pd.Timestamp(start.year, start.month + 1, 1))
    while month_start <= end:
        wi = ((month_start - start).days // 7)
        if 0 <= wi < cols:
            ticktext[wi] = month_start.strftime('%b')
        # advance one month
        month_start = (pd.Timestamp(month_start.year + 1, 1, 1)
                       if month_start.month == 12 else pd.Timestamp(month_start.year, month_start.month + 1, 1))
    return ticktext

def _weekday_labels(rows: int = 7, locale_name: str | None = None, fmt: str = '%a') -> list[str]:
    """Return localized weekday labels starting Monday, length `rows`.

    Uses Python `locale` and `datetime.strftime` with `fmt` (default `%a`).
    Falls back to English if the locale cannot be set.
    """
    from datetime import datetime, timedelta
    base_monday = datetime(2025, 1, 6)
    current = locale.getlocale(locale.LC_TIME)
    restored = False
    try:
        if locale_name:
            locale.setlocale(locale.LC_TIME, locale_name)
            restored = True
        labels = []
        for i in range(rows):
            s = (base_monday + timedelta(days=i)).strftime(fmt)
            if s.endswith('.'):
                s = s[:-1]
            labels.append(s)
    except Exception:
        labels = ['Mon ', 'Tue ', 'Wed ', 'Thu ', 'Fri ', 'Sat ', 'Sun '][:rows]
    finally:
        if restored and current is not None:
            try:
                locale.setlocale(locale.LC_TIME, current)
            except Exception:
                pass
    return labels


def plot_calendar_heatmap(
    df: pd.DataFrame,
    date_col: str = 'date',
    value_col: str = 'value',

    highlight_date: str | pd.Timestamp | None = None,

    grid_width: float = 3.0,
    grid_round: float = 0.3,
    
    formatting_locale: str  = "de",
    formatting_scale: int = 45,
    formatting_font_size: int = 20,
    formatting_zmin : float|None = None,
    formatting_zmax : float|None = None,
    formatting_colorscale: str = 'Reds',
    formatting_value_formatter: Callable[[float], str] | None = None,
) -> go.Figure:
    """Render a fast calendar heatmap with clean structure and localized labels.

    - Weeks run horizontally; weekdays (Mon..Sun) run vertically.
    - Grid is Monday-aligned and padded with NaNs (no data loss).
    - Heatmap renders colors; hover is provided by a lightweight scatter overlay.
    - Month labels appear at the week column containing the first day of each month.

    Parameters are kept explicit for spacing, typography, and localization.

    highlight_date: Optional date (string or Timestamp). If set, the matching
    cell gets an extra black outline.
    """

    # 1) Build Monday-aligned grid and localized weekday labels
    start, z_vals, rows, cols = _prepare_grid(df.copy(), date_col, value_col)
    
    days = _weekday_labels(rows=rows, locale_name=formatting_locale, fmt='%a')

    # 2) Build hover text per cell (localized if possible)
    def _format_value(val: float) -> str:
        try:
            return formatting_value_formatter(val) if formatting_value_formatter else f"⚡ {val} kWh"
        except Exception:
            return f"⚡ {val} kWh"

    def _cell_hover(i: int, j: int) -> str:
        val = z_vals[i, j]
        if not np.isfinite(val):
            return ''
        cell_date = (start + pd.Timedelta(days=int(j * 7 + i))).date()
        current = locale.getlocale(locale.LC_TIME)
        restored = False
        try:
            if formatting_locale:
                locale.setlocale(locale.LC_TIME, formatting_locale)
                restored = True
            weekday = cell_date.strftime('%a')
            day = cell_date.day
            month = cell_date.strftime('%B')
            year = cell_date.strftime('%y')
            return f"<b>{weekday}, {day}. {month} {year}</b><br>{_format_value(val)}"
        except Exception:
            return f"<b>{cell_date.strftime('%Y-%m-%d')}</b><br>{_format_value(val)}"
        finally:
            if restored and current is not None:
                try:
                    locale.setlocale(locale.LC_TIME, current)
                except Exception:
                    pass

    hover_text = [[_cell_hover(i, j) for j in range(cols)] for i in range(rows)]

    # 3) Base heatmap (hover disabled; scatter provides hover)
    fig = go.Figure(
        data=go.Heatmap(
            z=z_vals,
            x=np.arange(cols),
            y=np.arange(rows),
            colorscale=formatting_colorscale,
            zmin=formatting_zmin,
            zmax = formatting_zmax,
            #zmax=np.nanmax(z_vals) if np.isfinite(z_vals).any() else None,
            showscale=False,
            hoverinfo='skip',
        )
    )

    # 4) Scatter overlay supplying hover text (one marker per populated cell)
    scatter_x, scatter_y, scatter_ht = [], [], []
    for i in range(rows):
        for j in range(cols):
            text = hover_text[i][j]
            if text:
                scatter_x.append(j)
                scatter_y.append(i)
                scatter_ht.append(text)
    if scatter_x:
        fig.add_trace(
            go.Scatter(
            x=scatter_x,
            y=scatter_y,
            mode='markers',
            marker=dict(color='black', size=max(20, int(formatting_scale * 0.15))),
            opacity=0,  # visible hover without visual dots
            text=scatter_ht,
            hoverinfo='text',
            showlegend=False,
            hoverlabel=dict(font=dict(size=formatting_font_size)),
            )
        )

    # 5) Axes: weekday ticks (Y) and localized month labels (X)
    fig.update_yaxes(
        tickvals=np.arange(rows),
        ticktext=days,
        range=[-0.5, rows - 0.5],
        ticklabelposition='outside',
        tickfont=dict(size=formatting_font_size),
        #automargin=True,
        ticklabeloverflow='allow',
    )

    end_date = pd.to_datetime(df[date_col]).max().normalize()
    current = locale.getlocale(locale.LC_TIME)
    restored = False
    try:
        if formatting_locale:
            locale.setlocale(locale.LC_TIME, formatting_locale)
            restored = True
        x_ticktext = [''] * cols
        month_start = pd.Timestamp(start.year, start.month, 1)
        if start.day != 1:
            month_start = (
                pd.Timestamp(start.year + 1, 1, 1)
                if start.month == 12
                else pd.Timestamp(start.year, start.month + 1, 1)
            )
        while month_start <= end_date:
            wi = ((month_start - start).days // 7)
            if 0 <= wi < cols:
                x_ticktext[wi] = (
                    calendar.month_abbr[month_start.month]
                )
            month_start = (
                pd.Timestamp(month_start.year + 1, 1, 1)
                if month_start.month == 12
                else pd.Timestamp(month_start.year, month_start.month + 1, 1)
            )
    except Exception:
        x_ticktext = _month_ticktext(start, end_date, cols)
    finally:
        if restored and current is not None:
            try:
                locale.setlocale(locale.LC_TIME, current)
            except Exception:
                pass

    fig.update_xaxes(
        tickvals=np.arange(cols),
        ticktext=x_ticktext,
        range=[-0.5 - 0.3, cols - 0.5],
        tickfont=dict(size=formatting_font_size),
    )

    # 6) Layout and aesthetics
    fig.update_layout(
        plot_bgcolor='white',
        hoverlabel=dict(bgcolor='rgba(255,255,255,0.2)'),
        yaxis=dict(scaleanchor='x', scaleratio=1),
        xaxis=dict(constrain='domain'),
        width=int(cols * formatting_scale),
        height=int(rows * formatting_scale),
        margin=dict(l=0, r=0, t=14, b=0),
        paper_bgcolor='white',
        dragmode=False,
    )

    fig.update_layout(
        xaxis=dict(showgrid=False, zeroline=False, showline=False),
        yaxis=dict(showgrid=False, zeroline=False, showline=False),
    )

    # 7) Single-path white overlay to create rounded inner gaps
    eps = 20
    outer = (
        f"M{-eps} {-eps} L{cols-1+0.5+eps} {-eps} "
        f"L{cols-1+0.5+eps} {rows-1+0.5+eps} L{-eps} {rows-1+0.5+eps} Z"
    )
    holes = [
        _rounded_path(j - 0.5, i - 0.5, j + 0.5, i + 0.5, r=grid_round)
        for i in range(rows)
        for j in range(cols)
    ]
    combined_path = " ".join([outer] + holes)

    fig.add_shape(
        type='path',
        path=combined_path,
        fillcolor='white',
        fillrule='evenodd',
        line=dict(color='rgba(255,255,255,1)', width=grid_width),
        layer='above',
    )

    # 8) Optional highlight for a specific date
    if highlight_date is not None:
        try:
            hd = pd.to_datetime(highlight_date).normalize()
            offset_days = (hd - start).days
            if 0 <= offset_days < cols * 7:
                week_index = offset_days // 7
                weekday_index = hd.weekday()
                # Expand the shape by grid_width/2 on all sides
                expand =0.1
                fig.add_shape(
                    type='path',
                    path=_rounded_path(
                        week_index - 0.5 - expand,
                        weekday_index - 0.5 - expand,
                        week_index + 0.5 + expand,
                        weekday_index + 0.5 + expand,
                        r=grid_round ,
                    ),
                    fillcolor='rgba(0,0,0,0)',
                    line=dict(color='black', width=grid_width),
                    layer='above',
                )
        except Exception:
            pass
        except Exception:
            pass

    return fig




# from calendar_plot import plot_calendar_heatmap
# import pandas as pd


# ertrag = pd.read_parquet("app/data/ertrag.parquet")
# #column date to 2010-03-23 to datetime
# ertrag["date"] = pd.to_datetime(ertrag["date"]).dt.date
# ertrag = ertrag.loc[ertrag.standort=="muensingen"]
# #select only last year
# ertrag = ertrag.loc[ertrag["date"] >= pd.to_datetime("2025-01-01").date()]
# ertrag = ertrag.groupby("date").sum().reset_index()
# #custom, colorscale with warm yellow tones
# Yellows = [[0.0, 'rgb(255, 255, 255)'],[1.0, 'rgb(255, 180, 0)']]
# fig_heatmap = plot_calendar_heatmap(ertrag, date_col='date', value_col='value', colorscale=Yellows, title='Calendar Heatmap (Heatmap)', locale_name='de_DE', scale=30,grid_width=4,
#             highlight_date=pd.to_datetime("2025-06-21").date())
# # add a small rounded box in black to the plot


# fig_heatmap.show(config={
#     "displayModeBar": False,
#     "displaylogo": False,
#     "doubleClick": False,
#     # "scrollZoom": False,
#     "staticPlot": False,
#     "modeBarButtonsToAdd": ["select2d", "lasso2d","pan2d"],
#     "modeBarButtonsToRemove": ["zoom2d",  "autoScale2d", "resetScale2d"]
# })
