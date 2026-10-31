"""Convierte las páginas JSON de Notion en un DataFrame de pandas."""

from __future__ import annotations

from typing import Any

import pandas as pd


def _plain_text(rich: list[dict] | None) -> str:
    return "".join(part.get("plain_text", "") for part in (rich or []))


def _date_start(value: dict | None) -> str | None:
    return value.get("start") if value else None


def _formula_value(f: dict) -> Any:
    kind = f.get("type")
    if kind == "date":
        return _date_start(f.get("date"))
    return f.get(kind)


def _rollup_value(r: dict) -> Any:
    kind = r.get("type")
    if kind == "number":
        return r.get("number")
    if kind == "date":
        return _date_start(r.get("date"))
    if kind == "array":
        values = [parse_property(item) for item in r.get("array", [])]
        values = [v for v in values if v not in (None, "", [])]
        if values and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
            return sum(values)
        return ", ".join(str(v) for v in values)
    return None


def parse_property(prop: dict) -> Any:
    """Extrae un valor Python simple de una propiedad de Notion."""
    kind = prop.get("type")
    value = prop.get(kind)

    if kind in ("title", "rich_text"):
        return _plain_text(value)
    if kind in ("number", "checkbox", "url", "email", "phone_number", "created_time", "last_edited_time"):
        return value
    if kind in ("select", "status"):
        return value.get("name") if value else None
    if kind == "multi_select":
        return [opt.get("name") for opt in value or []]
    if kind == "date":
        return _date_start(value)
    if kind == "people":
        return ", ".join(p.get("name") or p.get("id", "") for p in value or [])
    if kind in ("created_by", "last_edited_by"):
        return (value or {}).get("name")
    if kind == "relation":
        return len(value or [])
    if kind == "files":
        return ", ".join(f.get("name", "") for f in value or [])
    if kind == "formula":
        return _formula_value(value or {})
    if kind == "rollup":
        return _rollup_value(value or {})
    if kind == "unique_id":
        if not value:
            return None
        prefix = value.get("prefix")
        return f"{prefix}-{value.get('number')}" if prefix else value.get("number")
    if kind == "verification":
        return (value or {}).get("state")
    return None


def pages_to_dataframe(pages: list[dict]) -> pd.DataFrame:
    """Una fila por página; una columna por propiedad."""
    rows = []
    for page in pages:
        row = {name: parse_property(prop) for name, prop in page.get("properties", {}).items()}
        row["_url"] = page.get("url")
        row["_creado"] = page.get("created_time")
        rows.append(row)
    df = pd.DataFrame(rows)
    return coerce_types(df, pages[0]["properties"] if pages else {})


DATE_TYPES = {"date", "created_time", "last_edited_time"}
NUMBER_TYPES = {"number", "relation"}


def coerce_types(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    """Convierte columnas de fecha y número a sus tipos de pandas."""
    for col in df.columns:
        kind = schema.get(col, {}).get("type")
        if kind == "formula" or kind == "rollup":
            kind = None  # tipo variable: inferir abajo
        if kind in DATE_TYPES or col == "_creado":
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True).dt.tz_localize(None)
        elif kind in NUMBER_TYPES:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        elif kind is None and col not in ("_url",):
            converted = pd.to_numeric(df[col], errors="coerce")
            if df[col].notna().sum() and converted.notna().sum() == df[col].notna().sum():
                df[col] = converted
    return df


def classify_columns(df: pd.DataFrame) -> dict[str, list[str]]:
    """Agrupa columnas por tipo para poblar los selectores de la interfaz."""
    visible = [c for c in df.columns if not c.startswith("_") or c == "_creado"]
    numeric, dates, categorical, multi = [], [], [], []
    for col in visible:
        series = df[col]
        if pd.api.types.is_bool_dtype(series):
            categorical.append(col)
        elif pd.api.types.is_numeric_dtype(series):
            numeric.append(col)
        elif pd.api.types.is_datetime64_any_dtype(series):
            dates.append(col)
        elif series.map(lambda v: isinstance(v, list)).any():
            multi.append(col)
            categorical.append(col)
        else:
            nunique = series.nunique(dropna=True)
            if 0 < nunique <= max(50, len(series) // 2):
                categorical.append(col)
    return {"numeric": numeric, "date": dates, "categorical": categorical, "multi": multi}
