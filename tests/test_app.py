import pandas as pd
import pytest

from src.charts import bar_chart, line_chart, pie_chart
from src.notion_api import extract_database_id
from src.parser import classify_columns, pages_to_dataframe
from src.sample_data import sample_dataframe

DB_ID = "a1b2c3d4e5f60718293a4b5c6d7e8f90"


def _page(name, estado, tags, fecha, importe):
    return {
        "url": "https://www.notion.so/x",
        "created_time": "2026-01-01T10:00:00.000Z",
        "properties": {
            "Nombre": {"type": "title", "title": [{"plain_text": name}]},
            "Estado": {"type": "status", "status": {"name": estado}},
            "Etiquetas": {"type": "multi_select", "multi_select": [{"name": t} for t in tags]},
            "Fecha": {"type": "date", "date": {"start": fecha, "end": None}},
            "Importe": {"type": "number", "number": importe},
            "Total": {"type": "formula", "formula": {"type": "number", "number": importe * 2}},
            "Hecho": {"type": "checkbox", "checkbox": estado == "Hecho"},
        },
    }


PAGES = [
    _page("A", "Hecho", ["x", "y"], "2026-03-01", 10),
    _page("B", "Pendiente", ["x"], "2026-04-15T09:30:00.000+02:00", 20),
    _page("C", "Hecho", [], "2026-04-20", 30),
]


@pytest.mark.parametrize(
    "value",
    [
        DB_ID,
        "a1b2c3d4-e5f6-0718-293a-4b5c6d7e8f90",
        f"https://www.notion.so/miworkspace/Mi-DB-{DB_ID}?v=ffffffffffffffffffffffffffffffff",
    ],
)
def test_extract_database_id(value):
    assert extract_database_id(value) == DB_ID


def test_extract_database_id_invalid():
    with pytest.raises(ValueError):
        extract_database_id("no-es-un-id")


def test_pages_to_dataframe_types():
    df = pages_to_dataframe(PAGES)
    assert list(df["Nombre"]) == ["A", "B", "C"]
    assert pd.api.types.is_datetime64_any_dtype(df["Fecha"])
    assert pd.api.types.is_numeric_dtype(df["Importe"])
    assert pd.api.types.is_numeric_dtype(df["Total"])
    cols = classify_columns(df)
    assert "Estado" in cols["categorical"]
    assert "Etiquetas" in cols["multi"]
    assert "Fecha" in cols["date"]


def test_charts_build():
    df = pages_to_dataframe(PAGES)
    fig = bar_chart(df, "Etiquetas", "Importe", "sum")
    totals = dict(zip(fig.data[0].x, fig.data[0].y))
    assert totals == {"x": 30, "y": 10, "(sin valor)": 30}
    assert line_chart(df, "Fecha", None, "count", "MS").data
    pie = pie_chart(df, "Estado", "Importe", "sum")
    assert dict(zip(pie.data[0].labels, pie.data[0].values)) == {"Hecho": 40, "Pendiente": 20}


def test_sample_data_all_charts():
    df = sample_dataframe()
    for freq in ["D", "W-MON", "MS", "QS", "YS"]:
        assert line_chart(df, "Fecha", "Horas", "mean", freq, color="Estado", cumulative=True).data
    assert bar_chart(df, "Categoría", None, "count", color="Etiquetas", horizontal=True, top_n=3).data
    assert pie_chart(df, "Etiquetas", "Importe (€)", "sum", top_n=3).data


def test_unsupported_and_rollup_properties():
    page = {
        "properties": {
            "Task Name": {"type": "title", "title": [{"plain_text": "T"}]},
            "Crear Sprint": {"type": "button", "button": {}},
            "Worked time": {"type": "rollup", "rollup": {"type": "array", "array": [
                {"type": "formula", "formula": {"type": "number", "number": 1.5}},
                {"type": "formula", "formula": {"type": "number", "number": 2}},
            ]}},
            "Project": {"type": "relation", "relation": [{"id": "x"}], "has_more": False},
        }
    }
    df = pages_to_dataframe([page])
    assert df.loc[0, "Worked time"] == 3.5
    assert df.loc[0, "Project"] == 1


def test_databases_toml_ids_valid():
    import tomllib
    from pathlib import Path

    dbs = tomllib.loads((Path(__file__).parents[1] / "databases.toml").read_text())["databases"]
    assert len(dbs) == 6
    for value in dbs.values():
        assert len(extract_database_id(value)) == 32
