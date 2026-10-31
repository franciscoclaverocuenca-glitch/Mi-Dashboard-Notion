"""Cliente mínimo para la API REST de Notion.

Solo usa `requests` para que el flujo sea transparente: autenticación con el
token de integración, consulta paginada de la base de datos y manejo de errores
con mensajes claros en español.
"""

from __future__ import annotations

import re
import time
from typing import Any

import requests

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
PAGE_SIZE = 100  # máximo permitido por la API
_ID_RE = re.compile(r"([0-9a-fA-F]{32})|([0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})")


class NotionAPIError(RuntimeError):
    """Error devuelto por la API de Notion con un mensaje legible."""


def extract_database_id(value: str) -> str:
    """Devuelve el ID (32 caracteres hex) a partir de un ID o de una URL de Notion.

    Acepta:
      * ``a1b2c3...`` (32 hex)
      * ``a1b2c3d4-e5f6-....`` (UUID con guiones)
      * ``https://www.notion.so/workspace/Mi-DB-a1b2c3...?v=...``
    """
    if not value or not value.strip():
        raise ValueError("El ID de la base de datos está vacío.")
    # Ignorar el parámetro ?v= (es el ID de la vista, no de la base de datos)
    cleaned = value.strip().split("?")[0]
    matches = _ID_RE.findall(cleaned)
    if not matches:
        raise ValueError(
            "No se reconoce el ID de la base de datos. Debe tener 32 caracteres "
            "hexadecimales o ser la URL completa de la base de datos."
        )
    raw = next(m for m in matches[-1] if m)
    return raw.replace("-", "").lower()


class NotionClient:
    def __init__(self, token: str, timeout: int = 30, max_retries: int = 3) -> None:
        if not token or not token.strip():
            raise ValueError("Falta el token de integración de Notion.")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token.strip()}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            }
        )

    # ------------------------------------------------------------------ #
    def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        url = f"{NOTION_API_URL}{path}"
        for attempt in range(self.max_retries + 1):
            try:
                resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
            except requests.RequestException as exc:
                if attempt < self.max_retries:
                    time.sleep(2**attempt)
                    continue
                raise NotionAPIError(f"No se pudo conectar con Notion: {exc}") from exc

            # 429 = límite de peticiones (≈3 req/s). Respetar Retry-After.
            if resp.status_code == 429 and attempt < self.max_retries:
                time.sleep(float(resp.headers.get("Retry-After", 2**attempt)))
                continue
            if resp.status_code >= 500 and attempt < self.max_retries:
                time.sleep(2**attempt)
                continue
            if not resp.ok:
                raise NotionAPIError(self._explain_error(resp))
            return resp.json()
        raise NotionAPIError("Se agotaron los reintentos contra la API de Notion.")

    @staticmethod
    def _explain_error(resp: requests.Response) -> str:
        try:
            body = resp.json()
            code, message = body.get("code", ""), body.get("message", resp.text)
        except ValueError:
            code, message = "", resp.text
        hints = {
            401: "El token no es válido. Revisa que empiece por 'ntn_' o 'secret_' y que esté completo.",
            403: "La integración no tiene permisos de lectura (activa 'Read content' en sus capacidades).",
            404: "No se encuentra la base de datos. ¿La has compartido con la integración "
            "(menú ••• → Conexiones → tu integración)? ¿El ID es correcto?",
        }
        hint = hints.get(resp.status_code, "")
        return f"Error {resp.status_code} {code}: {message}" + (f"\n\n💡 {hint}" if hint else "")

    # ------------------------------------------------------------------ #
    def get_database(self, database_id: str) -> dict:
        """Metadatos de la base de datos (título y esquema de propiedades)."""
        return self._request("GET", f"/databases/{database_id}")

    def query_database(
        self,
        database_id: str,
        filter_: dict | None = None,
        sorts: list | None = None,
        max_pages: int | None = None,
    ) -> list[dict]:
        """Descarga todas las filas (páginas) de la base de datos, siguiendo la paginación."""
        results: list[dict] = []
        cursor: str | None = None
        while True:
            payload: dict[str, Any] = {"page_size": PAGE_SIZE}
            if cursor:
                payload["start_cursor"] = cursor
            if filter_:
                payload["filter"] = filter_
            if sorts:
                payload["sorts"] = sorts
            data = self._request("POST", f"/databases/{database_id}/query", json=payload)
            results.extend(data.get("results", []))
            if max_pages and len(results) >= max_pages:
                return results[:max_pages]
            if not data.get("has_more"):
                return results
            cursor = data.get("next_cursor")
