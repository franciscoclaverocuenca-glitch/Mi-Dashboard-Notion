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
