"""
extract.py - Modulo de extraccion del pipeline ETL.
Lee los archivos fuente y retorna DataFrames crudos sin transformar.

Formatos reales detectados en los archivos:
  Catalog_Orders.txt : sep=',', quotechar='"', encoding UTF-8 con BOM
  Web_orders.txt     : cabecera en coma (se omite), datos con sep=';',
                       orden de columnas: ID,INV,PCODE,DATE,CATALOG,QTY,custnum
  products.txt       : sep=',', encoding UTF-8 con BOM
"""

import pandas as pd

# Nombres de columnas en el orden real que tienen los datos de Web_orders
_WEB_COLUMNS = ['ID', 'INV', 'PCODE', 'DATE', 'CATALOG', 'QTY', 'custnum']


def extract_all(path_catalog: str, path_web: str, path_products: str):
    """
    Lee los tres archivos fuente y retorna sus DataFrames crudos.

    Parametros
    ----------
    path_catalog : str
        Ruta a Catalog_Orders.txt (sep=',', UTF-8 BOM).
    path_web : str
        Ruta a Web_orders.txt (cabecera en coma, datos en punto y coma).
    path_products : str
        Ruta a products.txt (sep=',', UTF-8 BOM).

    Retorna
    -------
    tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
        (df_catalog, df_web, df_products)
    """
    # --- Catalog: coma como separador, BOM UTF-8 ---
    df_catalog = pd.read_csv(
        path_catalog,
        sep=',',
        encoding='utf-8-sig',
        dtype=str,
        skipinitialspace=True,
    )
    df_catalog['channel'] = 'CATALOG'

    # --- Web: cabecera en coma (se salta), datos en punto y coma.
    #     El orden real de columnas en los datos difiere del encabezado:
    #     ID ; INV ; PCODE ; DATE ; CATALOG ; QTY ; custnum
    df_web = pd.read_csv(
        path_web,
        sep=';',
        encoding='utf-8-sig',
        dtype=str,
        skipinitialspace=True,
        skiprows=1,       # omitir la cabecera con formato coma
        header=None,
        names=_WEB_COLUMNS,
    )
    df_web['channel'] = 'WEB'

    # --- Productos: coma como separador, BOM UTF-8 ---
    df_products = pd.read_csv(
        path_products,
        sep=',',
        encoding='utf-8-sig',
        dtype=str,
        skipinitialspace=True,
    )

    print(f"  [extract] Catalog_Orders : {len(df_catalog):>6} filas")
    print(f"  [extract] Web_Orders     : {len(df_web):>6} filas")
    print(f"  [extract] Products       : {len(df_products):>6} filas")

    return df_catalog, df_web, df_products
