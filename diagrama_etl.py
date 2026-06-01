"""
diagrama_etl.py - Genera el diagrama visual del pipeline ETL como imagen PNG.
Ejecutar: python diagrama_etl.py
Salida  : etl_pipeline_diagram.png
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch


# ── Colores ──────────────────────────────────────────────
C_SOURCE    = '#4A90D9'   # azul - fuentes de datos
C_EXTRACT   = '#5BA85A'   # verde - extraccion
C_TRANSFORM = '#E07B39'   # naranja - transformacion
C_LOAD      = '#8E5CA8'   # violeta - carga
C_DW        = '#C0392B'   # rojo - data warehouse
C_TEXT      = '#FFFFFF'
C_BG        = '#F8F9FA'

fig, ax = plt.subplots(figsize=(18, 10))
fig.patch.set_facecolor(C_BG)
ax.set_facecolor(C_BG)
ax.set_xlim(0, 18)
ax.set_ylim(0, 10)
ax.axis('off')


def box(ax, x, y, w, h, color, title, lines=None, fontsize=9):
    """Dibuja una caja con titulo y lineas de contenido."""
    rect = mpatches.FancyBboxPatch(
        (x, y), w, h,
        boxstyle='round,pad=0.15',
        facecolor=color, edgecolor='white', linewidth=2,
        zorder=3
    )
    ax.add_patch(rect)
    # Titulo
    ax.text(x + w / 2, y + h - 0.32, title,
            ha='center', va='center', fontsize=fontsize + 1,
            fontweight='bold', color=C_TEXT, zorder=4)
    # Contenido
    if lines:
        step = (h - 0.55) / len(lines)
        for i, line in enumerate(lines):
            ax.text(x + w / 2, y + h - 0.62 - i * step, line,
                    ha='center', va='center', fontsize=fontsize - 1,
                    color=C_TEXT, zorder=4)


def arrow(ax, x1, y1, x2, y2):
    """Dibuja una flecha entre dos puntos."""
    ax.annotate('',
        xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(
            arrowstyle='->', color='#2C3E50',
            lw=2.5, connectionstyle='arc3,rad=0.0'
        ),
        zorder=5
    )


# ── Titulo principal ─────────────────────────────────────
ax.text(9, 9.55, 'Pipeline ETL — Data Warehouse',
        ha='center', va='center', fontsize=16,
        fontweight='bold', color='#2C3E50')
ax.text(9, 9.15, 'Empresa de ventas Web y Catalogo  |  Python + Pandas + PostgreSQL',
        ha='center', va='center', fontsize=10, color='#555555')

# ── FUENTES DE DATOS (columna izquierda) ─────────────────
box(ax, 0.3, 6.5, 2.8, 1.3, C_SOURCE, 'Catalog_Orders.txt',
    ['6 767 registros', 'sep=,  |  UTF-8 BOM', 'Fecha: M/YY/D'])

box(ax, 0.3, 4.9, 2.8, 1.3, C_SOURCE, 'Web_Orders.txt',
    ['943 registros', 'sep=;  |  UTF-8 BOM', 'Fecha: D/M/YYYY'])

box(ax, 0.3, 3.3, 2.8, 1.3, C_SOURCE, 'products.txt',
    ['192 registros', 'sep=,  |  UTF-8 BOM', 'ID, TYPE, PCODE, PRICE...'])

# Etiqueta seccion
ax.text(1.7, 8.1, 'FUENTES', ha='center', fontsize=9,
        fontweight='bold', color=C_SOURCE)

# ── EXTRACT ───────────────────────────────────────────────
box(ax, 3.7, 4.3, 2.8, 3.2, C_EXTRACT, 'EXTRACT',
    [
        'extract.py',
        '',
        'pd.read_csv()',
        'sep=,  /  sep=;',
        'encoding=utf-8-sig',
        'skiprows=1 (Web)',
        '',
        'Agrega columna',
        "channel='WEB'/'CATALOG'",
    ])

# ── TRANSFORM ─────────────────────────────────────────────
box(ax, 7.1, 2.5, 3.4, 5.3, C_TRANSFORM, 'TRANSFORM',
    [
        'transform.py',
        '',
        'fix_pcode()',
        'O->0  |  )->0  |  !->0',
        '',
        'fix_catalog()',
        'Tosy->Toys  Pet->Pets...',
        '',
        'clean_orders()',
        'Parseo de fechas',
        'QTY nulos -> 0',
        'INV decimal -> int',
        'custnum strip()',
        '',
        'integrate_orders()',
        'Concat + dedup',
        '',
        'build_fact()',
        'JOIN ordenes x productos',
        'total_price = qty x price',
    ], fontsize=8)

# ── LOAD ──────────────────────────────────────────────────
box(ax, 11.1, 4.0, 2.8, 3.8, C_LOAD, 'LOAD',
    [
        'load.py',
        '',
        'dim_product',
        '192 filas',
        '',
        'dim_date',
        '1 104 fechas',
        '',
        'dim_customer',
        '3 329 clientes',
        '',
        'fact_sales',
        '7 664 hechos',
    ])

# ── DATA WAREHOUSE ────────────────────────────────────────
box(ax, 14.5, 6.2, 3.2, 1.5, C_DW, 'dim_date',
    ['date_id, full_date', 'day/month/year/quarter'])

box(ax, 14.5, 4.5, 3.2, 1.5, C_DW, 'dim_customer',
    ['customer_id', 'customer_name'])

box(ax, 14.5, 2.8, 3.2, 1.5, C_DW, 'dim_product',
    ['product_id, pcode', 'type, price, cost'])

box(ax, 14.5, 1.1, 3.2, 1.5, C_DW, 'dim_channel',
    ['channel_id', "WEB / CATALOG"])

# fact_sales en el centro-derecha
box(ax, 11.1, 0.3, 6.6, 0.65, C_DW, 'fact_sales  (7 664 filas)',
    None, fontsize=9)
ax.text(14.4, 0.62, 'sale_id | date_id | customer_id | product_id | channel_id | inv_number | qty | total_price',
        ha='center', va='center', fontsize=7, color=C_TEXT, zorder=4)

ax.text(14.4, 8.2, 'DATA WAREHOUSE', ha='center', fontsize=9,
        fontweight='bold', color=C_DW)
ax.text(14.4, 7.85, 'Esquema STAR — PostgreSQL',
        ha='center', fontsize=8, color='#555555')

# ── FLECHAS ───────────────────────────────────────────────
# Fuentes -> Extract
arrow(ax, 3.1, 7.15, 3.7, 6.5)
arrow(ax, 3.1, 5.55, 3.7, 5.55)
arrow(ax, 3.1, 3.95, 3.7, 4.6)

# Extract -> Transform
arrow(ax, 6.5, 5.9, 7.1, 5.9)

# Transform -> Load
arrow(ax, 10.5, 5.9, 11.1, 5.9)

# Load -> DW tables
arrow(ax, 13.9, 7.0, 14.5, 7.2)
arrow(ax, 13.9, 6.2, 14.5, 5.8)
arrow(ax, 13.9, 5.4, 14.5, 4.1)
arrow(ax, 13.9, 4.7, 14.5, 2.6)
arrow(ax, 13.9, 4.2, 12.4, 0.95)

# ── Leyenda de calidad ───────────────────────────────────
ax.text(0.3, 2.7, 'Problemas de calidad resueltos:', fontsize=8,
        fontweight='bold', color='#2C3E50')
problemas = [
    '* PCODEs con errores OCR (O->0, )->0)',
    '* CATALOG con errores ortograficos',
    '* Fechas en 2 formatos distintos',
    '* QTY nulos reemplazados con 0',
    '* INV con decimales (.00)',
    '* custnum con espacios extra',
]
for i, p in enumerate(problemas):
    ax.text(0.3, 2.35 - i * 0.32, p, fontsize=7.5, color='#444444')

plt.tight_layout()
plt.savefig('etl_pipeline_diagram.png', dpi=150, bbox_inches='tight',
            facecolor=C_BG)
print('Diagrama guardado: etl_pipeline_diagram.png')
