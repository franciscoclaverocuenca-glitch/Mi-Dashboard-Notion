"""Mi Dashboard Notion — aplicación Streamlit.

Ejecutar con:  streamlit run app.py
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from src.charts import AGGREGATIONS, FREQUENCIES, bar_chart, line_chart, pie_chart
from src.notion_api import NotionAPIError, NotionClient, extract_database_id
from src.parser import classify_columns, pages_to_dataframe
from src.sample_data import sample_dataframe

try:  # python-dotenv es opcional: permite usar un archivo .env en local
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

st.set_page_config(page_title="Mi Dashboard Notion", page_icon="📊", layout="wide")


# --------------------------------------------------------------------------- #
# Configuración
# --------------------------------------------------------------------------- #
def get_setting(name: str) -> str:
    """Lee primero de .streamlit/secrets.toml y después de variables de entorno."""
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:  # no existe secrets.toml
        pass
    return os.getenv(name, "")


@st.cache_data(ttl=600, show_spinner="Descargando datos de Notion…")
def load_notion(token: str, database_id: str) -> tuple[str, pd.DataFrame]:
    client = NotionClient(token)
    meta = client.get_database(database_id)
    title = "".join(t.get("plain_text", "") for t in meta.get("title", [])) or "Base de datos"
    pages = client.query_database(database_id)
    return title, pages_to_dataframe(pages)


def sidebar_connection() -> tuple[str, pd.DataFrame] | None:
    st.sidebar.header("🔌 Conexión")
    demo = st.sidebar.toggle("Usar datos de ejemplo", value=not get_setting("NOTION_TOKEN"))
    if demo:
        st.sidebar.info("Modo demo: datos ficticios. Desactívalo para usar tu base de datos.")
        return "Datos de ejemplo", sample_dataframe()

    token = st.sidebar.text_input(
        "Token de integración", value=get_setting("NOTION_TOKEN"), type="password",
        help="Empieza por 'ntn_' (o 'secret_' en integraciones antiguas).",
    )
    db_input = st.sidebar.text_input(
        "ID o URL de la base de datos", value=get_setting("NOTION_DATABASE_ID"),
    )
    if st.sidebar.button("🔄 Recargar datos", width="stretch"):
        load_notion.clear()

    if not token or not db_input:
        st.info("Introduce el token y el ID de la base de datos en la barra lateral (ver README.md).")
        return None
    try:
        return load_notion(token, extract_database_id(db_input))
    except (ValueError, NotionAPIError) as exc:
        st.error(str(exc))
        return None


# --------------------------------------------------------------------------- #
# Filtros
# --------------------------------------------------------------------------- #
def sidebar_filters(df: pd.DataFrame, cols: dict[str, list[str]]) -> pd.DataFrame:
    st.sidebar.header("🔎 Filtros")
    filtered = df

    for col in cols["date"][:1]:
        dates = df[col].dropna()
        if dates.empty:
            continue
        lo, hi = dates.min().date(), dates.max().date()
        rng = st.sidebar.date_input(f"Rango de '{col}'", value=(lo, hi), min_value=lo, max_value=hi)
        if isinstance(rng, tuple) and len(rng) == 2:
            mask = filtered[col].between(pd.Timestamp(rng[0]), pd.Timestamp(rng[1]) + pd.Timedelta(days=1))
            filtered = filtered[mask | filtered[col].isna()]

    for col in st.sidebar.multiselect("Filtrar por columnas", cols["categorical"]):
        if col in cols["multi"]:
            options = sorted({v for vals in df[col].dropna() for v in vals})
            chosen = st.sidebar.multiselect(col, options, default=options)
            filtered = filtered[filtered[col].map(lambda vals: bool(set(vals or []) & set(chosen)))]
        else:
            options = sorted(df[col].dropna().astype(str).unique())
            chosen = st.sidebar.multiselect(col, options, default=options)
            filtered = filtered[filtered[col].astype(str).isin(chosen)]
    return filtered


def value_controls(key: str, numeric: list[str]) -> tuple[str | None, str]:
    """Selector de agregación + columna numérica."""
    c1, c2 = st.columns(2)
    agg_label = c1.selectbox("Agregación", list(AGGREGATIONS), key=f"{key}_agg")
    agg = AGGREGATIONS[agg_label]
    value = None
    if agg != "count":
        if not numeric:
            c2.warning("No hay columnas numéricas; se usará el recuento.")
            return None, "count"
        value = c2.selectbox("Columna numérica", numeric, key=f"{key}_val")
    return value, agg


# --------------------------------------------------------------------------- #
# Interfaz principal
# --------------------------------------------------------------------------- #
def main() -> None:
    st.title("📊 Mi Dashboard Notion")
    loaded = sidebar_connection()
    if loaded is None:
        return
    title, df = loaded
    if df.empty:
        st.warning("La base de datos no tiene filas (o la integración no puede verlas).")
        return

    cols = classify_columns(df)
    data = sidebar_filters(df, cols)
    st.caption(f"Fuente: **{title}** · {len(data)} de {len(df)} filas tras aplicar filtros")

    # KPIs
    kpis = st.columns(1 + min(3, len(cols["numeric"])))
    kpis[0].metric("Elementos", f"{len(data):,}".replace(",", "."))
    for box, col in zip(kpis[1:], cols["numeric"]):
        box.metric(f"Total {col}", f"{data[col].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    tab_bar, tab_line, tab_pie, tab_data = st.tabs(["📊 Barras", "📈 Líneas", "🥧 Sectores", "🗂️ Datos"])

    with tab_bar:
        if not cols["categorical"]:
            st.info("No hay columnas categóricas (select, status, multi-select…) para agrupar.")
        else:
            c1, c2, c3 = st.columns(3)
            category = c1.selectbox("Eje de categorías", cols["categorical"], key="bar_cat")
            color = c2.selectbox("Color / apilar por", [None] + cols["categorical"], key="bar_color",
                                 format_func=lambda v: "— Ninguno —" if v is None else v)
            top_n = c3.slider("Mostrar las N primeras", 3, 50, 15, key="bar_top")
            value, agg = value_controls("bar", cols["numeric"])
            horizontal = st.toggle("Barras horizontales", key="bar_h")
            st.plotly_chart(bar_chart(data, category, value, agg, color, horizontal, top_n),
                            width="stretch")

    with tab_line:
        if not cols["date"]:
            st.info("No hay columnas de fecha. Añade una propiedad 'Fecha' a tu base de datos.")
        else:
            c1, c2, c3 = st.columns(3)
            date_col = c1.selectbox("Columna de fecha", cols["date"], key="line_date")
            freq = FREQUENCIES[c2.selectbox("Agrupar por", list(FREQUENCIES), index=2, key="line_freq")]
            color = c3.selectbox("Una línea por", [None] + cols["categorical"], key="line_color",
                                 format_func=lambda v: "— Ninguno —" if v is None else v)
            value, agg = value_controls("line", cols["numeric"])
            cumulative = st.toggle("Acumulado", key="line_cum")
            st.plotly_chart(line_chart(data, date_col, value, agg, freq, color, cumulative),
                            width="stretch")

    with tab_pie:
        if not cols["categorical"]:
            st.info("No hay columnas categóricas para el gráfico de sectores.")
        else:
            c1, c2 = st.columns(2)
            category = c1.selectbox("Categoría", cols["categorical"], key="pie_cat")
            top_n = c2.slider("Máximo de porciones (resto = 'Otros')", 3, 20, 8, key="pie_top")
            value, agg = value_controls("pie", cols["numeric"])
            if agg not in ("count", "sum"):
                st.caption("ℹ️ En sectores lo habitual es usar Recuento o Suma.")
            donut = st.toggle("Estilo donut", value=True, key="pie_donut")
            st.plotly_chart(pie_chart(data, category, value, agg, donut, top_n), width="stretch")

    with tab_data:
        show = data.copy()
        for col in cols["multi"]:
            show[col] = show[col].map(lambda v: ", ".join(v) if isinstance(v, list) else v)
        st.dataframe(show, width="stretch", hide_index=True,
                     column_config={"_url": st.column_config.LinkColumn("Abrir en Notion")})
        st.download_button("⬇️ Descargar CSV", show.to_csv(index=False).encode("utf-8"),
                           file_name="notion_export.csv", mime="text/csv")


if __name__ == "__main__":
    main()
