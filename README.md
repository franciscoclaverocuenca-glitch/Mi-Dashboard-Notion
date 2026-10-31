# 📊 Mi Dashboard Notion

Aplicación web interactiva en **Python + Streamlit** que se conecta a la **API de Notion**, descarga todas las filas de una base de datos y genera gráficos interactivos con **Plotly**:

- 📊 **Barras**: agrupa por cualquier columna categórica (select, status, multi-select, checkbox…), apila por una segunda columna y elige el modo horizontal o el *Top N*.
- 📈 **Líneas**: evolución temporal por día, semana, mes, trimestre o año, con una línea por categoría, modo acumulado y selector de rango.
- 🥧 **Sectores**: distribución por categoría (con estilo donut y agrupación de las porciones pequeñas en «Otros»).
- 🗂️ **Datos**: tabla con enlace a cada página de Notion y exportación a CSV.

Todas las vistas admiten agregaciones (recuento, suma, media, mediana, mínimo, máximo), filtros por fecha y por columna en la barra lateral, y un **modo demo** con datos ficticios para probar sin token.

---

## 📁 Estructura del proyecto

```
Mi-Dashboard-Notion/
├── app.py                         # Aplicación Streamlit (interfaz, filtros, pestañas)
├── src/
│   ├── __init__.py
│   ├── notion_api.py              # Cliente de la API de Notion (paginación, reintentos, errores)
│   ├── parser.py                  # Convierte las propiedades de Notion en un DataFrame
│   ├── charts.py                  # Gráficos Plotly: barras, líneas y sectores
│   └── sample_data.py             # Datos de ejemplo para el modo demo
├── tests/
│   └── test_app.py                # Pruebas con pytest
├── .streamlit/
│   ├── config.toml                # Tema de la app
│   └── secrets.toml.example       # Plantilla de secretos (copiar a secrets.toml)
├── .env.example                   # Alternativa: plantilla de variables de entorno
├── databases.toml                 # Bases de datos del selector (nombre = ID)
├── requirements.txt               # Dependencias de la aplicación
├── requirements-dev.txt           # Dependencias + pytest
└── README.md
```

---

## 🔑 Paso 1 · Crear la integración de Notion y obtener el token

1. Abre **<https://www.notion.so/profile/integrations>** (en Notion: *Configuración* → *Conexiones* → *Desarrollar o gestionar integraciones*).
2. Pulsa **«+ Nueva integración»**.
3. Rellena:
   - **Nombre**: `Mi Dashboard` (o el que quieras).
   - **Espacio de trabajo asociado**: el workspace donde está tu base de datos.
   - **Tipo**: **Interna** (*Internal*).
4. Pulsa **Guardar** y entra en la integración.
5. En la pestaña **Capacidades** (*Capabilities*) asegúrate de que está marcado **«Leer contenido»** (*Read content*). Las capacidades de escritura no son necesarias. Guarda los cambios.
6. En la pestaña **Configuración** (*Configuration*), en **«Secreto de integración interna»**, pulsa **Mostrar** y luego **Copiar**.
   El token empieza por **`ntn_`** (las integraciones antiguas empiezan por `secret_`).

> ⚠️ El token da acceso a todo lo que compartas con la integración. Trátalo como una contraseña: no lo pegues en el código ni lo subas a GitHub.

## 🔗 Paso 2 · Compartir la base de datos con la integración

Sin este paso la API devuelve **404 (object_not_found)** aunque el token sea correcto.

1. Abre la base de datos en Notion **como página completa** (no una vista enlazada dentro de otra página).
2. Pulsa el menú **`•••`** (arriba a la derecha) → **Conexiones** (*Connections*) → **Añadir conexiones**.
3. Busca y selecciona tu integración (`Mi Dashboard`) y confirma con **Confirmar**.

## 🆔 Paso 3 · Obtener el ID de la base de datos

Con la base de datos abierta como página completa, pulsa **`•••` → Copiar enlace**. Obtendrás algo así:

```
https://www.notion.so/miworkspace/a1b2c3d4e5f60718293a4b5c6d7e8f90?v=0f1e2d3c4b5a69788796a5b4c3d2e1f0
                                  └──────────── ID de la base de datos ───┘   └── ID de la vista (no sirve) ──┘
```

El **ID** son los **32 caracteres** que van **antes de `?v=`**. Puedes pegar en la app tanto el ID como la URL completa: la aplicación extrae el ID automáticamente.

### Bases de datos ya configuradas

El archivo [`databases.toml`](databases.toml) ya incluye las seis bases de datos de la página **🏅 Oposiciones**: Sprints, Proyectos, Objetivos, Planes Mensuales, Planes Semanales y Calendario. Se eligen en el desplegable **«Base de datos»** de la barra lateral. Para añadir otra, escribe una línea `"Nombre" = "ID"` en ese archivo, o elige «Otra (pegar ID o URL)…» en la app.

> 💡 Si conectas la integración a la página **🏅 Oposiciones** (Paso 2), todas las bases de datos que contiene quedan compartidas de una vez.

## ⚙️ Paso 4 · Configurar el token en el proyecto

Elige **una** de estas opciones (la app las busca en este orden: `secrets.toml` → variables de entorno → barra lateral).

**Opción A — `secrets.toml` de Streamlit (recomendada)**

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edita `.streamlit/secrets.toml`:

```toml
NOTION_TOKEN = "ntn_tu_token_aqui"
NOTION_DATABASE_ID = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
```

**Opción B — archivo `.env`**

```bash
cp .env.example .env
```

Edita `.env`:

```dotenv
NOTION_TOKEN=ntn_tu_token_aqui
NOTION_DATABASE_ID=a1b2c3d4e5f60718293a4b5c6d7e8f90
```

**Opción C — variables de entorno** (macOS / Linux)

```bash
export NOTION_TOKEN="ntn_tu_token_aqui"
export NOTION_DATABASE_ID="a1b2c3d4e5f60718293a4b5c6d7e8f90"
```

En Windows (PowerShell): `$env:NOTION_TOKEN="ntn_tu_token_aqui"`.

**Opción D — barra lateral**: desactiva «Usar datos de ejemplo» y pega el token y el ID directamente en la app (no se guardan).

`secrets.toml` y `.env` están en `.gitignore`, así que **no se subirán a GitHub**.

---

## 🚀 Paso 5 · Instalar y ejecutar

Requiere **Python 3.10 o superior**.

```bash
git clone https://github.com/franciscoclaverocuenca-glitch/Mi-Dashboard-Notion.git
```

```bash
cd Mi-Dashboard-Notion
```

```bash
python -m venv .venv
```

```bash
source .venv/bin/activate
```

(En Windows: `.venv\Scripts\activate`)

```bash
pip install -r requirements.txt
```

```bash
streamlit run app.py
```

Se abrirá **<http://localhost:8501>**. Si has configurado el token, la app carga tu base de datos; si no, arranca en modo demo. Los datos se guardan en caché 10 minutos: usa **🔄 Recargar datos** para forzar una nueva descarga.

### Ejecutar las pruebas

```bash
pip install -r requirements-dev.txt
```

```bash
python -m pytest
```

---

## ☁️ Desplegar en Streamlit Community Cloud (opcional)

1. Sube el repositorio a GitHub (sin `secrets.toml`).
2. En **<https://share.streamlit.io>** pulsa **Create app** y elige el repositorio, la rama `main` y el archivo `app.py`.
3. En **Advanced settings → Secrets** pega el mismo contenido que en `secrets.toml`:
   ```toml
   NOTION_TOKEN = "ntn_tu_token_aqui"
   NOTION_DATABASE_ID = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
   ```
4. Pulsa **Deploy**.

---

## 🧩 Tipos de propiedades soportados

| Tipo en Notion | Se convierte en | Uso en gráficos |
|---|---|---|
| Título, Texto, URL, Email, Teléfono | texto | categoría (si tiene pocos valores distintos) |
| Número | número | valor (suma, media…) |
| Select, Estado, Checkbox | texto / booleano | categoría |
| Multi-select | lista | categoría (cada opción cuenta por separado) |
| Fecha, Creado, Última edición | fecha | eje temporal en líneas |
| Persona, Creado por, Archivos | texto | categoría |
| Relación | nº de páginas relacionadas | valor |
| Fórmula, Rollup | número / fecha / texto según el resultado | según el tipo |
| ID único | texto (`PREFIJO-123`) o número | — |

## 🛠️ Solución de problemas

| Error | Causa y solución |
|---|---|
| **401 unauthorized** | Token incorrecto o incompleto. Vuelve a copiarlo (Paso 1.6) sin espacios. |
| **403 restricted_resource** | La integración no tiene la capacidad «Leer contenido» (Paso 1.5). |
| **404 object_not_found** | La base de datos no está compartida con la integración (Paso 2) o el ID es de una vista/página, no de la base de datos (Paso 3). |
| **400 validation_error** sobre *data sources* | La base de datos tiene varias fuentes de datos (función nueva de Notion). Usa el ID de una base de datos con una sola fuente o ábrela como página completa y copia de nuevo su enlace. |
| **429 rate_limited** | Límite de ~3 peticiones/s. La app reintenta automáticamente. |
| Gráfico de líneas sin datos | La base de datos no tiene ninguna propiedad de tipo Fecha. |

La app usa la versión de la API `2022-06-28` (endpoint `POST /v1/databases/{id}/query`), con paginación automática de 100 en 100 filas.
