"""Datos de ejemplo para probar el dashboard sin conectarse a Notion."""

from __future__ import annotations

import numpy as np
import pandas as pd


def sample_dataframe(rows: int = 120, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    estados = ["Pendiente", "En curso", "Hecho", "Bloqueado"]
    categorias = ["Marketing", "Ventas", "Producto", "Soporte", "Finanzas"]
    etiquetas = ["Urgente", "Cliente", "Interno", "Q4", "Mejora"]
    fechas = pd.Timestamp("2026-01-01") + pd.to_timedelta(rng.integers(0, 300, rows), unit="D")
    return pd.DataFrame(
        {
            "Nombre": [f"Tarea {i + 1}" for i in range(rows)],
            "Estado": rng.choice(estados, rows, p=[0.25, 0.3, 0.38, 0.07]),
            "Categoría": rng.choice(categorias, rows),
            "Etiquetas": [list(rng.choice(etiquetas, rng.integers(1, 3), replace=False)) for _ in range(rows)],
            "Fecha": fechas,
            "Importe (€)": rng.gamma(2.0, 450.0, rows).round(2),
            "Horas": rng.integers(1, 40, rows),
            "Completado": rng.random(rows) > 0.5,
        }
    )


def sample_sprints(seed: int = 3) -> pd.DataFrame:
    """Imita la base de datos «Sprints» (mismas columnas que en Notion)."""
    rng = np.random.default_rng(seed)
    today = pd.Timestamp.now().normalize()
    dates = pd.date_range(today - pd.Timedelta(days=120), today + pd.Timedelta(days=230), freq="D")
    dates = dates.repeat(2)
    n = len(dates)
    tipos = ["OPO: Temario", "OPO: Programación", "OPO: Practica", "MST: Estudio", "MST: Practicas", "ENG: Estudio"]
    past = dates < today
    status = np.where(past, rng.choice(["Done", "Not started", "Congelado"], n, p=[0.75, 0.15, 0.10]),
                      rng.choice(["Not started", "Congelado"], n, p=[0.9, 0.1]))
    df = pd.DataFrame({
        "Task Name": [f"Tema {rng.integers(1, 70)} · Estudio" for _ in range(n)],
        "Status": status,
        "Due Date": dates,
        "Target Time": rng.choice([0.3, 0.5, 0.75, 1.0, 1.5, 2.0], n),
        "Tipo": [[t] for t in rng.choice(tipos, n, p=[0.4, 0.15, 0.15, 0.15, 0.1, 0.05])],
        "Complexity": rng.choice(["High", "Medium", "Low"], n),
    })
    exam = pd.DataFrame({"Task Name": ["Opos · DÍA DEL EXAMEN"], "Status": ["Not started"],
                         "Due Date": [dates.max() + pd.Timedelta(days=1)], "Target Time": [None],
                         "Tipo": [["OPO: Temario"]], "Complexity": [None]})
    return pd.concat([df, exam], ignore_index=True)
