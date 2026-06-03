import psycopg2
import psycopg2.extras
import pandas as pd
from typing import Dict

# Helpers de conexión
def _get_connection(db_config: Dict):
    """Crea y retorna una conexión psycopg2 a partir del diccionario de config."""
    return psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        dbname=db_config['dbname'],
        user=db_config['user'],
        password=db_config['password'],
    )

# Carga de dimensiones
def _load_dim_product(cur, df_products: pd.DataFrame):
    sql = """
        INSERT INTO dim_product (pcode, type, description, price, cost, supplier)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (pcode) DO NOTHING;
    """
    rows = []
    for _, row in df_products.iterrows():
        rows.append((
            row.get('pcode'),
            row.get('type'),
            row.get('descrip'),
            _to_float(row.get('price')),
            _to_float(row.get('cost')),
            row.get('supplier'),
        ))
    psycopg2.extras.execute_batch(cur, sql, rows)
    print(f"  [load] dim_product  : {len(rows):>6} filas procesadas")


def _load_dim_date(cur, df_orders: pd.DataFrame):
    sql = """
        INSERT INTO dim_date (full_date, day, month, year, quarter, month_name, weekday)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (full_date) DO NOTHING;
    """
    fechas_unicas = df_orders['date'].dropna().unique()
    rows = []
    for fecha in fechas_unicas:
        ts = pd.Timestamp(fecha)
        rows.append((
            fecha,
            ts.day,
            ts.month,
            ts.year,
            ts.quarter,
            ts.month_name(),
            ts.day_name(),
        ))
    psycopg2.extras.execute_batch(cur, sql, rows)
    print(f"  [load] dim_date     : {len(rows):>6} fechas únicas insertadas")


def _load_dim_customer(cur, df_orders: pd.DataFrame):
    sql = """
        INSERT INTO dim_customer (customer_name)
        VALUES (%s)
        ON CONFLICT (customer_name) DO NOTHING;
    """
    clientes = df_orders['custnum'].dropna().unique()
    rows = [(str(c),) for c in clientes]
    psycopg2.extras.execute_batch(cur, sql, rows)
    print(f"  [load] dim_customer : {len(rows):>6} clientes únicos insertados")


def _get_channel_map(cur) -> Dict[str, int]:
    cur.execute("SELECT channel_id, channel_name FROM dim_channel;")
    return {row[1]: row[0] for row in cur.fetchall()}


def _get_date_map(cur) -> Dict:
    """Retorna {full_date → date_id} para todas las fechas cargadas."""
    cur.execute("SELECT date_id, full_date FROM dim_date;")
    return {row[1]: row[0] for row in cur.fetchall()}


def _get_customer_map(cur) -> Dict[str, int]:
    """Retorna {customer_name → customer_id} para todos los clientes cargados."""
    cur.execute("SELECT customer_id, customer_name FROM dim_customer;")
    return {row[1]: row[0] for row in cur.fetchall()}


def _get_product_map(cur) -> Dict[str, int]:
    """Retorna {pcode → product_id} para todos los productos cargados."""
    cur.execute("SELECT product_id, pcode FROM dim_product;")
    return {row[1]: row[0] for row in cur.fetchall()}

# Carga de fact_sales
def _load_fact_sales(cur, df_fact: pd.DataFrame,
                     date_map: Dict, customer_map: Dict,
                     product_map: Dict, channel_map: Dict):
    sql = """
        INSERT INTO fact_sales
            (date_id, customer_id, product_id, channel_id,
             transaction_id, inv_number, catalog_raw, catalog_clean,
             qty, total_price)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING;
    """
    rows = []
    omitidas = 0

    for _, row in df_fact.iterrows():
        date_id     = date_map.get(row['date'])
        customer_id = customer_map.get(str(row['custnum']).strip() if pd.notna(row['custnum']) else None)
        product_id  = product_map.get(row['pcode'])
        channel_id  = channel_map.get(row['channel'])

        # Omitir filas con FK no resolubles (product_id tambien es NOT NULL en BD)
        if None in (date_id, customer_id, product_id, channel_id):
            omitidas += 1
            continue

        rows.append((
            date_id,
            customer_id,
            product_id,
            channel_id,
            row.get('id'),
            row.get('inv'),
            row.get('catalog_raw'),
            row.get('catalog_clean'),
            int(row['qty']),
            _to_float(row.get('total_price')),
        ))

    if omitidas:
        print(f"  [load] fact_sales   : {omitidas} filas omitidas por FK no resuelta")

    psycopg2.extras.execute_batch(cur, sql, rows)
    print(f"  [load] fact_sales   : {len(rows):>6} filas insertadas")

# Función pública principal
def load_all(df_orders: pd.DataFrame, df_products: pd.DataFrame,
             df_fact: pd.DataFrame, db_config: Dict):
                 
    conn = None
    try:
        conn = _get_connection(db_config)
        conn.autocommit = False
        cur = conn.cursor()

        # 1. Dimensión producto
        _load_dim_product(cur, df_products)

        # 2. Dimensión fecha
        _load_dim_date(cur, df_orders)

        # 3. Dimensión cliente
        _load_dim_customer(cur, df_orders)

        # 4. Leer mapas de IDs (dim_channel ya existe)
        channel_map  = _get_channel_map(cur)
        date_map     = _get_date_map(cur)
        customer_map = _get_customer_map(cur)
        product_map  = _get_product_map(cur)

        # 5. Tabla de hechos
        _load_fact_sales(cur, df_fact, date_map, customer_map, product_map, channel_map)

        conn.commit()
        print("  [load] Commit exitoso.")

    except Exception as exc:
        if conn:
            conn.rollback()
            print(f"  [load] ERROR — rollback ejecutado: {exc}")
        raise
    finally:
        if conn:
            conn.close()

# Utilitarios internos
def _to_float(value):
    """Convierte un valor a float; retorna None si no es convertible."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
