"""
main.py - Orquestador del pipeline ETL.
Ejecuta en orden: Extraccion -> Transformacion -> Carga.
"""

import sys
import os

from extract import extract_all
from transform import clean_orders, clean_products, integrate_orders, build_fact
from load import load_all


# ─────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────

DB_CONFIG = {
    'host':     'localhost',
    'port':     5432,
    'dbname':   'ETL',
    'user':     'postgres',
    'password': 'Choquecondo05',
}

# Rutas a los archivos fuente (ajustar según la ubicación real)
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
PATH_CATALOG    = os.path.join(BASE_DIR, 'txt', 'Catalog_Orders.txt')
PATH_WEB        = os.path.join(BASE_DIR, 'txt', 'Web_orders.txt')
PATH_PRODUCTS   = os.path.join(BASE_DIR, 'txt', 'products.txt')


# ─────────────────────────────────────────────
# Pipeline principal
# ─────────────────────────────────────────────

def run_pipeline():
    """Ejecuta el pipeline ETL completo: extract → transform → load."""

    # ── Paso 1: Extracción ──────────────────────
    print("\n== PASO 1: EXTRACCION ==")
    try:
        df_catalog_raw, df_web_raw, df_products_raw = extract_all(
            PATH_CATALOG, PATH_WEB, PATH_PRODUCTS
        )
    except FileNotFoundError as e:
        print(f"  [extract] ERROR — archivo no encontrado: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"  [extract] ERROR inesperado: {e}")
        sys.exit(1)
    print("  [extract] Extraccion completada.\n")

    # Paso 2: Transformacion
    print("== PASO 2: TRANSFORMACION ==")
    try:
        # Catalog usa formato M/YY/D (ej: 3/97/7 = 7 marzo 1997)
        df_catalog_clean  = clean_orders(df_catalog_raw, date_format='%m/%y/%d %H:%M:%S')
        # Web usa formato D/M/YYYY (ej: 17/12/2000)
        df_web_clean      = clean_orders(df_web_raw, date_format='%d/%m/%Y %H:%M:%S')
        df_products_clean = clean_products(df_products_raw)

        df_orders = integrate_orders(df_catalog_clean, df_web_clean)
        df_fact   = build_fact(df_orders, df_products_clean)
    except Exception as e:
        print(f"  [transform] ERROR inesperado: {e}")
        sys.exit(1)
    print("  [transform] Transformacion completada.\n")

    # Paso 3: Carga
    print("== PASO 3: CARGA ==")
    try:
        load_all(df_orders, df_products_clean, df_fact, DB_CONFIG)
    except Exception as e:
        print(f"  [load] ERROR inesperado durante la carga: {e}")
        sys.exit(1)
    print("  [load] Carga completada.\n")

    print("== PIPELINE FINALIZADO EXITOSAMENTE ==\n")


if __name__ == '__main__':
    run_pipeline()
