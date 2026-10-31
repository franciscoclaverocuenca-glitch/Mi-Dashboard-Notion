"""Panel de progreso para la base de datos «Sprints» de Oposiciones.

Se activa solo si la tabla tiene las columnas de estado, fecha y horas objetivo.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.charts import PALETTE, TEMPLATE

STATUS, DATE, HOURS, TYPE, NAME = "Status", "Due Date", "Target Time", "Tipo", "Task Name"
DONE, FROZEN = "Done", "Congelado"
EXAM_KEYWORD = "EXAMEN"

COLOR_DONE, COLOR_PENDING, COLOR_LATE = PALETTE[0], "#B8C4D6", "#CC6677"


def is_available(df: pd.DataFrame) -> bool:
    return {STATUS, DATE, HOURS} <= set(df.columns) and pd.api.types.is_datetime64_any_dtype(df[DATE])


def active(df: pd.DataFrame) -> pd.DataFrame:
    """Sesiones planificadas: con fecha y sin congelar."""
    return df[(df[STATUS] != FROZEN) & df[DATE].notna()].copy()


def exam_date(df: pd.DataFrame) -> pd.Timestamp | None:
    if NAME in df:
        hits = df[df[NAME].astype(str).str.upper().str.contains(EXAM_KEYWORD, na=False)][DATE].dropna()
        if not hits.empty:
            return hits.max()
    dates = df[DATE].dropna()
    return dates.max() if not dates.empty else None


def summary(df: pd.DataFrame, today: pd.Timestamp) -> dict:
    act = active(df)
    hours = act[HOURS].fillna(0)
    done = act[STATUS] == DONE
    late = ~done & (act[DATE] < today)
    exam = exam_date(df)
    return {
        "sesiones": len(act),
        "hechas": int(done.sum()),
        "pct": done.mean() * 100 if len(act) else 0.0,
        "horas_hechas": hours[done].sum(),
        "horas_total": hours.sum(),
        "atrasadas": int(late.sum()),
        "horas_atrasadas": hours[late].sum(),
        "dias_examen": (exam - today).days if exam is not None else None,
        "examen": exam,
        "congeladas": int((df[STATUS] == FROZEN).sum()),
    }


def _classify(act: pd.DataFrame, today: pd.Timestamp) -> pd.Series:
    done = act[STATUS] == DONE
    return pd.Series(
        ["Hecha" if d else ("Atrasada" if dt < today else "Pendiente") for d, dt in zip(done, act[DATE])],
        index=act.index,
    )


def weekly_chart(df: pd.DataFrame, today: pd.Timestamp) -> go.Figure:
    """Horas objetivo por semana: hechas, atrasadas y pendientes."""
    act = active(df)
    act["Estado"] = _classify(act, today)
    act["Semana"] = act[DATE].dt.to_period("W-SUN").dt.start_time
    table = act.pivot_table(index="Semana", columns="Estado", values=HOURS, aggfunc="sum", fill_value=0)
    fig = go.Figure()
    for estado, color in [("Hecha", COLOR_DONE), ("Atrasada", COLOR_LATE), ("Pendiente", COLOR_PENDING)]:
        if estado in table:
            fig.add_bar(x=table.index, y=table[estado], name=estado, marker_color=color,
                        hovertemplate="%{x|%d/%m/%Y}<br>%{y:.1f} h<extra>" + estado + "</extra>")
    _today_line(fig, today)
    fig.update_layout(template=TEMPLATE, barmode="stack", title="Horas planificadas por semana",
                      yaxis_title="Horas", hovermode="x unified", legend_orientation="h", legend_y=1.08)
    fig.update_xaxes(rangeslider_visible=True)
    return fig


def burnup_chart(df: pd.DataFrame, today: pd.Timestamp) -> go.Figure:
    """Horas acumuladas: plan vs. realmente completadas."""
    act = active(df).sort_values(DATE)
    act[HOURS] = act[HOURS].fillna(0)
    plan = act.groupby(DATE)[HOURS].sum().cumsum()
    done = act[act[STATUS] == DONE].groupby(DATE)[HOURS].sum().cumsum()
    fig = go.Figure()
    fig.add_scatter(x=plan.index, y=plan.values, name="Plan", mode="lines",
                    line={"color": COLOR_PENDING, "width": 2, "dash": "dot"})
    fig.add_scatter(x=done.index, y=done.values, name="Completado", mode="lines",
                    line={"color": COLOR_DONE, "width": 3})
    _today_line(fig, today)
    fig.update_layout(template=TEMPLATE, title="Horas acumuladas: plan vs. completado",
                      yaxis_title="Horas acumuladas", hovermode="x unified",
                      legend={"orientation": "h", "y": -0.15, "x": 0})
    return fig


def type_chart(df: pd.DataFrame, today: pd.Timestamp) -> go.Figure:
    """Horas por tipo de sesión (hechas vs. resto)."""
    act = active(df)
    if TYPE not in act:
        return go.Figure()
    act = act.explode(TYPE)
    act[TYPE] = act[TYPE].fillna("(sin tipo)")
    act["Estado"] = _classify(act, today)
    table = act.pivot_table(index=TYPE, columns="Estado", values=HOURS, aggfunc="sum", fill_value=0)
    table = table.loc[table.sum(axis=1).sort_values().index]
    fig = go.Figure()
    for estado, color in [("Hecha", COLOR_DONE), ("Atrasada", COLOR_LATE), ("Pendiente", COLOR_PENDING)]:
        if estado in table:
            fig.add_bar(y=table.index, x=table[estado], name=estado, orientation="h", marker_color=color,
                        hovertemplate="%{y}: %{x:.1f} h<extra>" + estado + "</extra>")
    fig.update_layout(template=TEMPLATE, barmode="stack", title="Horas por tipo de sesión",
                      xaxis_ticksuffix=" h", legend={"orientation": "h", "y": -0.15, "x": 0},
                      height=max(350, 28 * len(table) + 150))
    return fig


def late_sessions(df: pd.DataFrame, today: pd.Timestamp) -> pd.DataFrame:
    act = active(df)
    late = act[(act[STATUS] != DONE) & (act[DATE] < today)].sort_values(DATE)
    cols = [c for c in [NAME, DATE, HOURS, TYPE, "_url"] if c in late]
    out = late[cols].copy()
    if TYPE in out:
        out[TYPE] = out[TYPE].map(lambda v: ", ".join(v) if isinstance(v, list) else v)
    return out


def _today_line(fig: go.Figure, today: pd.Timestamp) -> None:
    fig.add_vline(x=today, line_width=1, line_dash="dash", line_color="#555")
    fig.add_annotation(x=today, y=1, yref="paper", text="Hoy", showarrow=False, yanchor="bottom")
