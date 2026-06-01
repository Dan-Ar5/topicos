# Sección del Informe — Implementación del Pipeline ETL

**Integrante:** Mabel  
**Curso:** Tópicos de Bases de Datos  

---

## 1. Introducción

El pipeline ETL implementado automatiza la integración de datos de ventas provenientes de dos canales distintos (Web y Catálogo) hacia un Data Warehouse en PostgreSQL. El proceso se divide en tres etapas claramente separadas: Extracción, Transformación y Carga, cada una implementada en un script Python independiente.

---

## 2. Arquitectura del Pipeline

El pipeline sigue la arquitectura clásica ETL con cuatro scripts Python:

| Script | Responsabilidad |
|--------|----------------|
| `extract.py` | Lectura de archivos fuente con Pandas |
| `transform.py` | Limpieza, corrección e integración de datos |
| `load.py` | Conexión y carga en PostgreSQL |
| `main.py` | Orquestador que ejecuta los tres pasos en orden |

---

## 3. Etapa EXTRACT

**Script:** `extract.py`  
**Función principal:** `extract_all(path_catalog, path_web, path_products)`

### Desafíos de lectura detectados

Durante la extracción se identificaron diferencias estructurales importantes entre los archivos fuente:

| Archivo | Separador | Encoding | Particularidad |
|---------|-----------|----------|----------------|
| `Catalog_Orders.txt` | Coma (`,`) | UTF-8 con BOM | Estándar CSV |
| `Web_orders.txt` | Punto y coma (`;`) en datos | UTF-8 con BOM | La **cabecera** usa coma pero los **datos** usan punto y coma. Además, el orden de columnas en los datos difiere del encabezado: `ID, INV, PCODE, DATE, CATALOG, QTY, custnum` |
| `products.txt` | Coma (`,`) | UTF-8 con BOM | Estándar CSV |

### Solución implementada

Para `Web_orders.txt` se utilizó `skiprows=1` para omitir la cabecera mal formateada, y se asignaron manualmente los nombres de columna en el orden real de los datos:

```python
df_web = pd.read_csv(
    path_web,
    sep=';',
    encoding='utf-8-sig',
    skiprows=1,
    header=None,
    names=['ID', 'INV', 'PCODE', 'DATE', 'CATALOG', 'QTY', 'custnum'],
)
```

**Resultado:** 6 767 órdenes de catálogo + 943 órdenes web + 192 productos extraídos correctamente.

---

## 4. Etapa TRANSFORM

**Script:** `transform.py`  
**Funciones:** `fix_pcode()`, `fix_catalog()`, `clean_orders()`, `clean_products()`, `integrate_orders()`, `build_fact()`

### 4.1 Problemas de calidad y soluciones

#### Problema 1 — Fechas en dos formatos distintos

Los archivos de órdenes tenían formatos de fecha incompatibles:

| Archivo | Formato original | Ejemplo | Formato Python |
|---------|-----------------|---------|----------------|
| Catalog_Orders | `M/YY/D H:M:S` | `3/97/7 00:00:00` = 7 mar 1997 | `%m/%y/%d %H:%M:%S` |
| Web_orders | `D/M/YYYY H:M:S` | `17/12/2000 00:00:00` = 17 dic 2000 | `%d/%m/%Y %H:%M:%S` |

**Solución:** La función `clean_orders()` acepta un parámetro `date_format` para manejar cada archivo con su formato específico. El resultado se convierte a tipo `date` puro (sin hora) con `.dt.date`.

#### Problema 2 — Errores OCR en PCODE

Los códigos de producto presentaban confusiones entre la letra `O` y el dígito `0`, así como caracteres especiales `)` y `!`:

| PCODE erróneo | PCODE correcto |
|---------------|---------------|
| `PT2OOO` | `PT2000` |
| `GD16OO` | `GD1600` |
| `GD12))` | `GD1200` |
| `GD10)!` | `GD1010` |
| `sp2000` | `SP2000` |

**Solución — función `fix_pcode()`:**
- Separar el prefijo alfabético (ej. `PT`, `GD`) del sufijo numérico con regex
- Aplicar correcciones únicamente en la parte numérica para no alterar letras válidas del prefijo
- Convertir todo a mayúsculas

```python
def fix_pcode(pcode: str) -> str:
    pcode = pcode.strip().upper()
    match = re.match(r'^([A-Z]+)(.*)$', pcode)
    prefix, numeric_part = match.group(1), match.group(2)
    numeric_part = numeric_part.translate({'O':'0', ')':'0', '!':'0'})
    return prefix + numeric_part
```

#### Problema 3 — Errores ortográficos en CATALOG

| Valor erróneo | Valor correcto |
|---------------|---------------|
| `Gardenings`, `Garden` | `Gardening` |
| `Tosy`, `Toy` | `Toys` |
| `Pet` | `Pets` |
| `Sport` | `Sports` |

**Solución — función `fix_catalog()`:** diccionario de mapeo aplicado con `.apply()`.  
Se conserva el valor original en la columna `catalog_raw` para trazabilidad.

#### Problema 4 — QTY nulos

**Solución:** `pd.to_numeric(..., errors='coerce').fillna(0).astype(int)`

#### Problema 5 — INV con decimales innecesarios

Los números de invoice tenían formato `107707.00`.  
**Solución:** Convertir a entero eliminando la parte decimal.

#### Problema 6 — custnum con espacios extra

**Solución:** `df['custnum'].str.strip()`

### 4.2 Integración de datasets

La función `integrate_orders()` une los DataFrames de catálogo y web mediante `pd.concat()`, elimina duplicados exactos con `drop_duplicates()` y resetea el índice.

**Resultado:** 7 710 órdenes integradas (6 767 catálogo + 943 web, sin duplicados).

### 4.3 Construcción del DataFrame de hechos

La función `build_fact()` realiza un `LEFT JOIN` entre las órdenes integradas y los productos por la columna `pcode`, y calcula:

```
total_price = qty × price
```

Se usa LEFT JOIN para no perder órdenes aunque el producto no exista en el catálogo.

---

## 5. Etapa LOAD

**Script:** `load.py`  
**Función principal:** `load_all(df_orders, df_products, df_fact, db_config)`

### Estrategia de carga

Se utiliza `psycopg2` (sin SQLAlchemy) con `execute_batch()` para inserciones eficientes por lotes. La estrategia `INSERT ... ON CONFLICT DO NOTHING` garantiza **idempotencia**: el pipeline puede ejecutarse múltiples veces sin generar duplicados.

### Orden de carga (respetando claves foráneas)

```
1. dim_product    → 192 productos
2. dim_date       → 1 104 fechas únicas (atributos derivados: día, mes, año, trimestre)
3. dim_customer   → 3 329 clientes únicos
4. dim_channel    → solo lectura (WEB y CATALOG ya existen)
5. fact_sales     → 7 664 hechos de venta
```

### Manejo de errores

Se implementa `try/except/finally` con `rollback()` automático ante cualquier error durante la carga, garantizando la integridad transaccional.

```python
try:
    # ... inserciones ...
    conn.commit()
except Exception as exc:
    conn.rollback()
    raise
finally:
    conn.close()
```

### Nota sobre registros omitidos

46 órdenes fueron omitidas de `fact_sales` porque su `PCODE` no tenía correspondencia en `dim_product`. Esto representa un 0.6% del total y se debe a códigos de producto que no figuran en `products.txt`.

---

## 6. Resultados finales

```
EXTRACCION:
  Catalog_Orders : 6 767 filas
  Web_Orders     :   943 filas
  Products       :   192 filas

TRANSFORMACION:
  Ordenes integradas : 7 710 filas
  Ordenes con producto coincidente: 7 664
  Ordenes sin producto (omitidas) :    46 (0.6%)

CARGA EN POSTGRESQL:
  dim_product    :   192 productos
  dim_date       : 1 104 fechas únicas
  dim_customer   : 3 329 clientes únicos
  fact_sales     : 7 664 hechos de venta cargados
```

---

## 7. Automatización

El script `main.py` orquesta los tres pasos secuencialmente con manejo de errores en cada etapa. Basta ejecutar un único comando para correr el pipeline completo:

```bash
python main.py
```

Los mensajes de progreso en cada paso permiten monitorear la ejecución y detectar problemas rápidamente.

---

## 8. Repositorio GitHub

El proyecto está organizado en GitHub con:
- Scripts separados por responsabilidad (`extract.py`, `transform.py`, `load.py`, `main.py`)
- Carpeta `txt/` con los archivos fuente
- `README.md` con instrucciones de instalación, configuración y uso
- Diagrama visual del pipeline (`etl_pipeline_diagram.png`)
