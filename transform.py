import re
import pandas as pd

# Mapa de correcciones ortograficas para la columna CATALOG
_CATALOG_MAP = {
    'Gardenings': 'Gardening',
    'Garden':     'Gardening',
    'Tosy':       'Toys',
    'Toy':        'Toys',
    'Pet':        'Pets',
    'Sport':      'Sports',
}

# Correcciones OCR para la parte numerica del PCODE: O->0, )->0, !->0
_OCR_FIXES = str.maketrans({'O': '0', ')': '0', '!': '0'})

def fix_pcode(pcode: str) -> str:
    if not isinstance(pcode, str):
        return pcode

    pcode = pcode.strip().upper()

    match = re.match(r'^([A-Z]+)(.*)$', pcode)
    if not match:
        return pcode

    prefix, numeric_part = match.group(1), match.group(2)
    numeric_part = numeric_part.translate(_OCR_FIXES)

    return prefix + numeric_part

def fix_catalog(value: str) -> str:

    if not isinstance(value, str):
        return value
    cleaned = value.strip()
    return _CATALOG_MAP.get(cleaned, cleaned)


def clean_orders(df: pd.DataFrame, date_format: str = '%d/%m/%Y %H:%M:%S') -> pd.DataFrame:
    
    df = df.copy()

    # Normalizar nombres de columnas a minusculas sin espacios
    df.columns = [c.strip().lower() for c in df.columns]

    #  Fecha 
    df['date'] = pd.to_datetime(
        df['date'].str.strip(),
        format=date_format,
        errors='coerce',
    ).dt.date

    #  PCODE 
    df['pcode'] = df['pcode'].apply(fix_pcode)

    #  CATALOG: conservar crudo y limpiar 
    df['catalog_raw'] = df['catalog'].str.strip()
    df['catalog_clean'] = df['catalog_raw'].apply(fix_catalog)
    df.drop(columns=['catalog'], inplace=True)

    #  QTY 
    df['qty'] = pd.to_numeric(df['qty'], errors='coerce').fillna(0).astype(int)

    #  custnum 
    df['custnum'] = df['custnum'].str.strip()

    #  INV: quitar decimales y convertir a entero 
    df['inv'] = (
        pd.to_numeric(df['inv'].str.strip(), errors='coerce')
        .fillna(0)
        .astype(int)
    )

    return df

def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    
    df = df.copy()

    df.columns = [c.strip().lower() for c in df.columns]

    str_cols = df.select_dtypes(include='object').columns
    for col in str_cols:
        df[col] = df[col].str.strip()

    df['pcode'] = df['pcode'].apply(fix_pcode)

    return df


def integrate_orders(df_catalog: pd.DataFrame, df_web: pd.DataFrame) -> pd.DataFrame:
    
    df = pd.concat([df_catalog, df_web], ignore_index=True)
    df = df.drop_duplicates()
    df = df.reset_index(drop=True)

    print(f"  [transform] Ordenes integradas: {len(df):>6} filas "
          f"(cat={len(df_catalog)}, web={len(df_web)})")
    return df


def build_fact(df_orders: pd.DataFrame, df_products: pd.DataFrame) -> pd.DataFrame:
    
    prod_cols = df_products[['pcode', 'type', 'descrip', 'price', 'cost', 'supplier']]

    df_fact = df_orders.merge(prod_cols, on='pcode', how='left')

    df_fact['price'] = pd.to_numeric(df_fact['price'], errors='coerce')
    df_fact['total_price'] = df_fact['qty'] * df_fact['price']

    sin_producto = df_fact['price'].isna().sum()
    if sin_producto > 0:
        print(f"  [transform] Advertencia: {sin_producto} ordenes sin producto coincidente")

    print(f"  [transform] fact_sales preparado: {len(df_fact):>6} filas")
    return df_fact
