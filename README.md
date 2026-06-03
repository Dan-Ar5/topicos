# Pipeline ETL — Data Warehouse

Proyecto de laboratorio ETL construido con **Python + Pandas + PostgreSQL**.  
Integra ventas de dos canales (Web y Catálogo) en un esquema Star de Data Warehouse.

## Integrantes

| Nombre | Rol |
|--------|-----|
| Mabel | Implementación del Pipeline ETL, GitHub, Diagrama |
| Paúl | Análisis Exploratorio / EDA |
| Gersson| Diseño del esquema DW, informe |

## Estructura del repositorio

```
TOPICOS/
├── txt/
│   ├── Catalog_Orders.txt   # Órdenes por catálogo (6 767 registros)
│   ├── Web_orders.txt       # Órdenes web (943 registros)
│   └── products.txt         # Catálogo de productos (192 registros)
├── extract.py               # Paso 1 – Lectura de archivos fuente
├── transform.py             # Paso 2 – Limpieza e integración
├── load.py                  # Paso 3 – Carga en PostgreSQL
├── main.py                  # Orquestador principal
├── diagrama_etl.py          # Genera el diagrama visual del pipeline
└── README.md
```

## Requisitos

```bash
pip install pandas psycopg2-binary sqlalchemy
```

- Python 3.8+
- PostgreSQL 12+ con la base de datos `ETL` y el esquema Star ya creado

## Configuración

Editar `main.py` con tus credenciales PostgreSQL:

```python
DB_CONFIG = {
    'host':     'localhost',
    'port':     5432,
    'dbname':   'ETL',
    'user':     'postgres',
    'password': 'tu_password',
}
```

## Ejecución

```bash
# Correr el pipeline completo
python main.py

# Generar el diagrama ETL (guarda etl_pipeline_diagram.png)
python diagrama_etl.py
```

## Flujo del Pipeline ETL

```
Catalog_Orders.txt ──┐
Web_orders.txt       ├──► EXTRACT ──► TRANSFORM ──► LOAD ──► PostgreSQL DW
products.txt         ──┘
```

### EXTRACT (`extract.py`)
- Lee `Catalog_Orders.txt` con `sep=','`, encoding UTF-8 BOM
- Lee `Web_orders.txt` omitiendo la cabecera en formato coma, datos con `sep=';'`
- Lee `products.txt` con `sep=','`
- Agrega columna `channel = 'CATALOG'` / `'WEB'`

### TRANSFORM (`transform.py`)

| Problema detectado | Solución aplicada |
|--------------------|-------------------|
| PCODEs con OCR errors (`O`, `)`, `!` en lugar de `0`) | `fix_pcode()` con regex + traducción |
| CATALOG con errores ortográficos (`Tosy`, `Pet`, `Garden`…) | `fix_catalog()` con mapa de correcciones |
| Fechas en dos formatos distintos | `%m/%y/%d` (Catalog) y `%d/%m/%Y` (Web) |
| QTY nulos | Reemplazados con `0` |
| INV con decimales `.00` | Convertido a entero |
| custnum con espacios extra | `str.strip()` |
| Duplicados exactos | `drop_duplicates()` |

### LOAD (`load.py`)
Carga en orden respetando claves foráneas con `INSERT ... ON CONFLICT DO NOTHING`:

1. `dim_product` — 192 productos
2. `dim_date` — 1 104 fechas únicas
3. `dim_customer` — 3 329 clientes únicos
4. `dim_channel` — solo lectura (ya contiene WEB y CATALOG)
5. `fact_sales` — **7 664 hechos de venta**

## Esquema Star (Data Warehouse)

```
              dim_date
                 │
dim_channel ── fact_sales ── dim_customer
                 │
            dim_product
```

| Tabla | Descripción |
|-------|-------------|
| `fact_sales` | Tabla de hechos: qty, total_price, FK a todas las dimensiones |
| `dim_date` | Dimensión tiempo: día, mes, año, trimestre |
| `dim_customer` | Dimensión cliente |
| `dim_product` | Dimensión producto: tipo, precio, costo, proveedor |
| `dim_channel` | Dimensión canal: WEB / CATALOG |

## Resultados de la carga

```
== PASO 1: EXTRACCION ==
  [extract] Catalog_Orders :   6767 filas
  [extract] Web_Orders     :    943 filas
  [extract] Products       :    192 filas

== PASO 2: TRANSFORMACION ==
  [transform] Ordenes integradas:   7710 filas
  [transform] fact_sales preparado: 7710 filas

== PASO 3: CARGA ==
  [load] dim_product  :    192 filas procesadas
  [load] dim_date     :   1104 fechas unicas insertadas
  [load] dim_customer :   3329 clientes unicos insertados
  [load] fact_sales   :   7664 filas insertadas
  [load] Commit exitoso.
```
