"""Gráficos interactivos con Plotly: barras, líneas y sectores."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

AGGREGATIONS = {
    "Recuento": "count",
    "Suma": "sum",
    "Media": "mean",
    "Mediana": "median",
    "Mínimo": "min",
    "Máximo": "max",
}

FREQUENCIES = {"Día": "D", "Semana": "W-MON", "Mes": "MS", "Trimestre": "QS", "Año": "YS"}

PALETTE = px.colors.qualitative.Safe
TEMPLATE = "plotly_white"


def _explode(df: pd.DataFrame, col: str | None) -> pd.DataFrame:
    """Expande columnas multi-select (listas) a una fila por opción."""
    if col and col in df and df[col].map(lambda v: isinstance(v, list)).any():
        out = df.explode(col)
        out[col] = out[col].fillna("(sin valor)")
        return out
    return df


def _label(df: pd.DataFrame, col: str | None) -> pd.DataFrame:
    if col and col in df:
        df = df.copy()
        df[col] = df[col].astype("object").where(df[col].notna(), "(sin valor)").astype(str)
    return df


def aggregate(
    df: pd.DataFrame,
    group_cols: list[str],
    value_col: str | None,
    agg: str,
) -> tuple[pd.DataFrame, str]:
    """Agrupa y devuelve (tabla, nombre de la columna de valor)."""
    if agg == "count" or not value_col:
        out = df.groupby(group_cols, dropna=False).size().reset_index(name="Recuento")
        return out, "Recuento"
    out = df.groupby(group_cols, dropna=False)[value_col].agg(agg).reset_index()
    return out, value_col


def _empty(msg: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font={"size": 16})
    fig.update_layout(template=TEMPLATE, xaxis_visible=False, yaxis_visible=False)
    return fig


def bar_chart(
    df: pd.DataFrame,
    category: str,
    value_col: str | None,
    agg: str,
    color: str | None = None,
    horizontal: bool = False,
    top_n: int | None = None,
) -> go.Figure:
    data = _explode(_explode(df, category), color)
    data = _label(_label(data, category), color)
    groups = [category] + ([color] if color and color != category else [])
    table, ycol = aggregate(data, groups, value_col, agg)
    if table.empty:
        return _empty("No hay datos para mostrar")

    order = table.groupby(category)[ycol].sum().sort_values(ascending=False)
    if top_n:
        order = order.head(top_n)
        table = table[table[category].isin(order.index)]

    x, y = (ycol, category) if horizontal else (category, ycol)
    fig = px.bar(
        table,
        x=x,
        y=y,
        color=color if color and color != category else None,
        orientation="h" if horizontal else "v",
        text_auto=".3~s",
        template=TEMPLATE,
        color_discrete_sequence=PALETTE,
        category_orders={category: list(order.index)},
        title=f"{_agg_name(agg)} de {value_col or 'elementos'} por {category}",
    )
    fig.update_layout(barmode="stack", legend_title_text=color or "", hovermode="closest")
    if horizontal:
        fig.update_yaxes(autorange="reversed")
    return fig


def line_chart(
    df: pd.DataFrame,
    date_col: str,
    value_col: str | None,
    agg: str,
    freq: str = "MS",
    color: str | None = None,
    cumulative: bool = False,
) -> go.Figure:
    data = df.dropna(subset=[date_col])
    if data.empty:
        return _empty(f"La columna '{date_col}' no tiene fechas")
    data = _label(_explode(data, color), color)
    data = data.assign(_periodo=data[date_col].dt.to_period(_period_alias(freq)).dt.start_time)

    groups = ["_periodo"] + ([color] if color else [])
    table, ycol = aggregate(data, groups, value_col, agg)
    table = table.sort_values("_periodo")
    if cumulative:
        if color:
            table[ycol] = table.groupby(color)[ycol].cumsum()
        else:
            table[ycol] = table[ycol].cumsum()

    fig = px.line(
        table,
        x="_periodo",
        y=ycol,
        color=color,
        markers=True,
        template=TEMPLATE,
        color_discrete_sequence=PALETTE,
        labels={"_periodo": date_col},
        title=f"{_agg_name(agg)} de {value_col or 'elementos'} a lo largo del tiempo"
        + (" (acumulado)" if cumulative else ""),
    )
    fig.update_layout(hovermode="x unified", legend_title_text=color or "")
    fig.update_xaxes(rangeslider_visible=True)
    return fig


def pie_chart(
    df: pd.DataFrame,
    category: str,
    value_col: str | None,
    agg: str,
    donut: bool = True,
    top_n: int | None = 8,
) -> go.Figure:
    data = _label(_explode(df, category), category)
    table, ycol = aggregate(data, [category], value_col, agg)
    table = table[table[ycol] > 0].sort_values(ycol, ascending=False)
    if table.empty:
        return _empty("No hay valores positivos para mostrar")

    if top_n and len(table) > top_n:
        rest = pd.DataFrame({category: ["Otros"], ycol: [table.iloc[top_n:][ycol].sum()]})
        table = pd.concat([table.head(top_n), rest], ignore_index=True)

    fig = px.pie(
        table,
        names=category,
        values=ycol,
        hole=0.45 if donut else 0,
        template=TEMPLATE,
        color_discrete_sequence=PALETTE,
        title=f"Distribución de {value_col or 'elementos'} por {category}",
    )
    fig.update_traces(textposition="inside", textinfo="percent+label", sort=False)
    return fig


def _agg_name(agg: str) -> str:
    return next((k for k, v in AGGREGATIONS.items() if v == agg), agg)


def _period_alias(freq: str) -> str:
    return {"D": "D", "W-MON": "W-SUN", "MS": "M", "QS": "Q", "YS": "Y"}[freq]
