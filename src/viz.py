"""Shared Plotly theme so every figure reads as one system.

Categorical colours are assigned to *entities* in a fixed order (a region keeps
its colour whatever else is on the chart); sequential scales are a single hue;
diverging scales are blue <-> red around a neutral grey.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DIVERGING = ["#0d366b", "#3987e5", "#9ec5f4", "#f0efec", "#f3a3a3", "#e34948", "#8f1d1d"]
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}
MUTED = "#b5b3ad"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e7e6e2"
SURFACE = "#fcfcfb"

# Fixed entity -> colour assignments (never re-ranked when a filter drops a series).
REGION_COLOURS = {
    "World": TEXT_2,
    "Africa": CATEGORICAL[0],
    "Americas": CATEGORICAL[1],
    "Asia": CATEGORICAL[2],
    "Europe": CATEGORICAL[3],
    "Oceania": CATEGORICAL[4],
}
CROP_COLOURS = {"Wheat": CATEGORICAL[0], "Maize (corn)": CATEGORICAL[1], "Rice": CATEGORICAL[2],
                "Soya beans": CATEGORICAL[3], "Potatoes": CATEGORICAL[4]}

_template = go.layout.Template()
_template.layout = go.Layout(
    font=dict(family="Inter, Helvetica Neue, Arial, sans-serif", size=13, color=TEXT),
    paper_bgcolor=SURFACE,
    plot_bgcolor=SURFACE,
    colorway=CATEGORICAL,
    title=dict(x=0.02, xanchor="left", font=dict(size=17, color=TEXT)),
    margin=dict(l=60, r=30, t=70, b=60),
    hovermode="closest",
    hoverlabel=dict(bgcolor="#ffffff", bordercolor=GRID, font=dict(color=TEXT, size=12)),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(color=TEXT_2)),
    xaxis=dict(showgrid=False, zeroline=False, linecolor=GRID, ticks="outside", tickcolor=GRID,
               title=dict(font=dict(color=TEXT_2))),
    yaxis=dict(gridcolor=GRID, gridwidth=1, zeroline=False, showline=False, title=dict(font=dict(color=TEXT_2))),
)
_template.data.scatter = [go.Scatter(line=dict(width=2), marker=dict(size=8, line=dict(width=2, color=SURFACE)))]
_template.data.bar = [go.Bar(marker=dict(line=dict(width=0)))]
pio.templates["foodsys"] = _template
pio.templates.default = "foodsys"


def colour_for_region(name: str, fallback_index: int = 6) -> str:
    return REGION_COLOURS.get(name, CATEGORICAL[fallback_index])


def line_chart(df, x, y, colour_col, title, y_title, x_title="", colour_map=None, hover_fmt=":.2f", unit=""):
    """Multi-series line chart with entity-stable colours and end-point labels."""
    fig = go.Figure()
    for i, (name, g) in enumerate(df.groupby(colour_col, sort=False)):
        colour = (colour_map or {}).get(name) or colour_for_region(name, i % 8)
        g = g.sort_values(x)
        fig.add_trace(go.Scatter(
            x=g[x], y=g[y], name=str(name), mode="lines", line=dict(color=colour, width=2),
            hovertemplate=f"<b>{name}</b><br>%{{x}}: %{{y{hover_fmt}}}{unit}<extra></extra>"))
    fig.update_layout(title=title, xaxis_title=x_title, yaxis_title=y_title, hovermode="x unified")
    return fig


def bar_chart(df, x, y, title, y_title, colour=CATEGORICAL[0], orientation="v", hover_fmt=":,.1f", unit="",
              text=None, colour_col=None, colour_map=None):
    fig = go.Figure()
    if colour_col:
        for i, (name, g) in enumerate(df.groupby(colour_col, sort=False)):
            c = (colour_map or {}).get(name) or colour_for_region(name, i % 8)
            fig.add_trace(_bar(g, x, y, str(name), c, orientation, hover_fmt, unit, text))
    else:
        fig.add_trace(_bar(df, x, y, "", colour, orientation, hover_fmt, unit, text))
        fig.update_layout(showlegend=False)
    fig.update_layout(title=title, bargap=0.35)
    if orientation == "h":
        fig.update_layout(xaxis_title=y_title, yaxis=dict(autorange="reversed", gridcolor=SURFACE),
                          xaxis=dict(gridcolor=GRID, showgrid=True))
    else:
        fig.update_layout(yaxis_title=y_title)
    return fig


def _bar(g, x, y, name, colour, orientation, hover_fmt, unit, text):
    kw = dict(name=name, marker=dict(color=colour), hovertemplate=f"<b>%{{customdata}}</b><br>%{{{ 'x' if orientation=='h' else 'y'}{hover_fmt}}}{unit}<extra></extra>")
    label = g[text] if text else None
    if orientation == "h":
        return go.Bar(x=g[y], y=g[x], orientation="h", customdata=g[x], text=label, textposition="outside", **kw)
    return go.Bar(x=g[x], y=g[y], customdata=g[x], text=label, textposition="outside", **kw)


def scatter_chart(df, x, y, title, x_title, y_title, label_col="area", colour_col="region", log_x=False,
                  log_y=False, size_col=None, trend=None, hover_extra=None):
    fig = go.Figure()
    for i, (name, g) in enumerate(df.groupby(colour_col, sort=True)):
        colour = colour_for_region(name, i % 8)
        size = 9 if size_col is None else (8 + 30 * (g[size_col].fillna(0) / df[size_col].max()) ** 0.5)
        extra = "" if hover_extra is None else "<br>" + "<br>".join(f"{k}: %{{customdata[{j+1}]}}" for j, k in enumerate(hover_extra))
        custom = g[[label_col] + (hover_extra or [])].round(2).values
        fig.add_trace(go.Scatter(
            x=g[x], y=g[y], mode="markers", name=str(name),
            marker=dict(color=colour, size=size, opacity=0.85, line=dict(width=1.5, color=SURFACE)),
            customdata=custom,
            hovertemplate=f"<b>%{{customdata[0]}}</b><br>{x_title}: %{{x:,.2f}}<br>{y_title}: %{{y:,.2f}}{extra}<extra></extra>"))
    if trend is not None:
        tx, ty, label = trend
        fig.add_trace(go.Scatter(x=tx, y=ty, mode="lines", name=label, line=dict(color=TEXT_2, width=2, dash="dot"),
                                 hoverinfo="skip"))
    fig.update_layout(title=title, xaxis_title=x_title, yaxis_title=y_title)
    if log_x:
        fig.update_xaxes(type="log", tickvals=_log_ticks(df[x]))
    if log_y:
        fig.update_yaxes(type="log", tickvals=_log_ticks(df[y]))
    return fig


def _log_ticks(series):
    """1-2-5 tick positions spanning the data range, for readable log axes."""
    import numpy as np
    s = series[series > 0]
    lo, hi = np.floor(np.log10(s.min())), np.ceil(np.log10(s.max()))
    ticks = [m * 10 ** e for e in range(int(lo), int(hi) + 1) for m in (1, 2, 5)]
    return [t for t in ticks if s.min() * 0.8 <= t <= s.max() * 1.25]


def legend_bottom(fig, height=None):
    """Move the legend under the plot (used with subplot titles, which sit where the legend would)."""
    fig.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="left", x=0),
                      margin=dict(b=90))
    if height:
        fig.update_layout(height=height)
    return fig


def heatmap(z, x, y, title, colorscale=None, zmid=None, unit="", fmt=":.1f"):
    fig = go.Figure(go.Heatmap(
        z=z, x=x, y=y, colorscale=colorscale or SEQUENTIAL, zmid=zmid, xgap=2, ygap=2,
        hovertemplate=f"%{{y}} · %{{x}}: %{{z{fmt}}}{unit}<extra></extra>",
        colorbar=dict(thickness=10, outlinewidth=0)))
    fig.update_layout(title=title, yaxis=dict(autorange="reversed", showgrid=False), xaxis=dict(showgrid=False))
    return fig
