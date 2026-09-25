"""Análisis del caso NutriVida.

Este archivo se construirá paso a paso. Cada bloque deberá poder explicarse
durante una demostración.
"""


" primero activa el entorno virtual desde la carpeta del proyecto"

from pathlib import Path

import pandas as pd


ARCHIVO = Path(__file__).with_name("Datos_NutriVida.xlsx")
print(ARCHIVO)
print(ARCHIVO.exists())
libro = pd.ExcelFile(ARCHIVO)
print(libro.sheet_names)

# Granularidad de los datos

ventas = pd.read_excel(ARCHIVO, sheet_name="Ventas Historicas")

print(ventas.shape)
print(ventas.columns.tolist())
print(ventas.head())

columnas_categoricas = ["Categoria", "Canal", "Region", "Promocion"]

for columna in columnas_categoricas:
    print(f"\n--- {columna} ---")
    print(ventas[columna].value_counts(dropna=False))


ventas_limpias = ventas.copy()

equivalencias_canal = {
    "E-commerce": "Ecommerce",
    "Super": "Supermercado",
    "SUPERMERCADO": "Supermercado",
}

ventas_limpias["Canal"] = ventas_limpias["Canal"].replace(equivalencias_canal)

print(ventas_limpias["Canal"].value_counts(dropna=False))
cantidad_meses = ventas_limpias["Fecha"].nunique()
cantidad_skus = ventas_limpias["SKU"].nunique()
cantidad_canales = ventas_limpias["Canal"].nunique()
cantidad_regiones = ventas_limpias["Region"].nunique()

filas_esperadas = (
    cantidad_meses
    * cantidad_skus
    * cantidad_canales
    * cantidad_regiones
)

print("Meses:", cantidad_meses)
print("SKU:", cantidad_skus)
print("Canales:", cantidad_canales)
print("Regiones:", cantidad_regiones)
print("Filas esperadas:", filas_esperadas)
print("Filas recibidas:", len(ventas_limpias))

clave = ["Fecha", "SKU", "Canal", "Region"]

duplicados_clave = ventas_limpias.duplicated(
    subset=clave,
    keep=False,
)

duplicados_exactos = ventas_limpias.duplicated(
    keep=False,
)

print("Filas involucradas en claves repetidas:", duplicados_clave.sum())
print("Filas involucradas en duplicados exactos:", duplicados_exactos.sum())

print(
    ventas_limpias.loc[duplicados_clave]
    .sort_values(clave)
    .head(10)
)

print(
    "Duplicados exactos antes de limpiar:",
    ventas.duplicated(keep=False).sum(),
)
ventas_limpias = (
    ventas_limpias
    .drop_duplicates()
    .reset_index(drop=True)
)

print("Filas después de eliminar duplicados:", len(ventas_limpias))
print(
    "Claves repetidas restantes:",
    ventas_limpias.duplicated(subset=clave).sum(),
)
columnas_revision = [
    "Fecha",
    "SKU",
    "Producto",
    "Canal",
    "Region",
    "Unidades",
]

unidades_vacias = (
    ventas_limpias.loc[
        ventas_limpias["Unidades"].isna(),
        columnas_revision,
    ]
    .sort_values(["Fecha", "SKU", "Canal", "Region"])
)

cantidad_vacias = ventas_limpias["Unidades"].isna().sum()
cantidad_ceros = ventas_limpias["Unidades"].eq(0).sum()

print("Unidades vacías:", cantidad_vacias)
print("Unidades con cero explícito:", cantidad_ceros)
print(unidades_vacias.to_string(index=False))

pronostico_real = pd.read_excel(
    ARCHIVO,
    sheet_name="Pronostico vs Real",
)

ventas_por_sku_mes = (
    ventas_limpias
    .groupby(["Fecha", "SKU"], as_index=False)
    .agg(
        unidades_conocidas=("Unidades", "sum"),
        cantidad_vacias=("Unidades", lambda columna: columna.isna().sum()),
    )
)

meses_con_vacios = ventas_por_sku_mes.loc[
    ventas_por_sku_mes["cantidad_vacias"] > 0
]

comparacion_vacios = meses_con_vacios.merge(
    pronostico_real[["Fecha", "SKU", "Venta_Real"]],
    on=["Fecha", "SKU"],
    how="left",
)

comparacion_vacios["diferencia"] = (
    comparacion_vacios["Venta_Real"]
    - comparacion_vacios["unidades_conocidas"]
)

print(
    comparacion_vacios[
        [
            "Fecha",
            "SKU",
            "cantidad_vacias",
            "unidades_conocidas",
            "Venta_Real",
            "diferencia",
        ]
    ].to_string(index=False)
)

print("\n--- TIPOS DE DATOS ---")
print(ventas_limpias.dtypes)

print("\n--- VALORES VACÍOS POR COLUMNA ---")
print(ventas_limpias.isna().sum())

fechas_convertidas = pd.to_datetime(
    ventas_limpias["Fecha"],
    format="%Y-%m",
    errors="coerce",
)

cantidad_fechas_invalidas = fechas_convertidas.isna().sum()

print("\n--- REVISIÓN DE FECHAS ---")
print("Fechas inválidas:", cantidad_fechas_invalidas)
print("Primera fecha:", fechas_convertidas.min())
print("Última fecha:", fechas_convertidas.max())
print("Meses distintos:", fechas_convertidas.nunique())
ventas_limpias["Fecha"] = fechas_convertidas
precios_vacios = ventas_limpias.loc[
    ventas_limpias["Precio_Unitario_USD"].isna(),
    [
        "Fecha",
        "SKU",
        "Producto",
        "Canal",
        "Region",
        "Precio_Unitario_USD",
        "Promocion",
    ],
]

referencias_precio = (
    ventas_limpias
    .dropna(subset=["Precio_Unitario_USD"])
    .groupby(
        ["Fecha", "SKU", "Region"],
        as_index=False,
    )
    .agg(
        precios_distintos=("Precio_Unitario_USD", "nunique"),
        precio_referencia=("Precio_Unitario_USD", "first"),
    )
)

comparacion_precios = precios_vacios.merge(
    referencias_precio,
    on=["Fecha", "SKU", "Region"],
    how="left",
)

print("\n--- REVISIÓN DE PRECIOS VACÍOS ---")
print(comparacion_precios.to_string(index=False))

print(
    "Filas sin precio de referencia:",
    comparacion_precios["precio_referencia"].isna().sum(),
)

print(
    "Filas cuyo grupo tiene varios precios:",
    comparacion_precios["precios_distintos"].gt(1).sum(),
)
precios_costos = pd.read_excel(
    ARCHIVO,
    sheet_name="Precios y Costos",
)

catalogo_precios = precios_costos[
    ["SKU", "Precio_Venta_USD"]
].rename(
    columns={
        "Precio_Venta_USD": "precio_maestro",
    }
)

comparacion_maestro = comparacion_precios.merge(
    catalogo_precios,
    on="SKU",
    how="left",
    validate="many_to_one",
)

comparacion_maestro["diferencia_maestro"] = (
    comparacion_maestro["precio_referencia"]
    - comparacion_maestro["precio_maestro"]
)

print("\n--- PRECIO DE REFERENCIA VS. CATÁLOGO ---")
print(
    comparacion_maestro[
        [
            "Fecha",
            "SKU",
            "Canal",
            "Region",
            "precio_referencia",
            "precio_maestro",
            "diferencia_maestro",
        ]
    ].to_string(index=False)
)

print(
    "SKU sin precio maestro:",
    comparacion_maestro["precio_maestro"].isna().sum(),
)

print(
    "Precios que no coinciden:",
    comparacion_maestro["diferencia_maestro"].abs().gt(0.000001).sum(),
)
precio_por_sku = (
    catalogo_precios
    .set_index("SKU")["precio_maestro"]
)

ventas_limpias["Precio_Fue_Completado"] = (
    ventas_limpias["Precio_Unitario_USD"].isna()
)

ventas_limpias["Precio_Unitario_USD"] = (
    ventas_limpias["Precio_Unitario_USD"]
    .fillna(
        ventas_limpias["SKU"].map(precio_por_sku)
    )
)
print("\n--- RESULTADO DE COMPLETAR PRECIOS ---")

print(
    "Precios completados:",
    ventas_limpias["Precio_Fue_Completado"].sum(),
)

print(
    "Precios vacíos restantes:",
    ventas_limpias["Precio_Unitario_USD"].isna().sum(),
)

print(
    ventas_limpias.loc[
        ventas_limpias["Precio_Fue_Completado"],
        [
            "Fecha",
            "SKU",
            "Canal",
            "Region",
            "Precio_Unitario_USD",
            "Precio_Fue_Completado",
        ],
    ].to_string(index=False)
)

precios_observados = ventas_limpias.loc[
    ~ventas_limpias["Precio_Fue_Completado"]
].copy()

referencias_misma_promocion = (
    precios_observados
    .groupby(
        ["Fecha", "SKU", "Region", "Promocion"],
        as_index=False,
    )
    .agg(
        precios_distintos=("Precio_Unitario_USD", "nunique"),
        precio_referencia=("Precio_Unitario_USD", "first"),
    )
)

comparacion_misma_promocion = precios_vacios.merge(
    referencias_misma_promocion,
    on=["Fecha", "SKU", "Region", "Promocion"],
    how="left",
)

print("\n--- REFERENCIAS CON LA MISMA PROMOCIÓN ---")

print(
    "Filas sin referencia:",
    comparacion_misma_promocion["precio_referencia"].isna().sum(),
)

print(
    "Grupos con precios diferentes:",
    comparacion_misma_promocion["precios_distintos"].gt(1).sum(),
)

print(
    comparacion_misma_promocion[
        [
            "Fecha",
            "SKU",
            "Canal",
            "Region",
            "Promocion",
            "precios_distintos",
            "precio_referencia",
        ]
    ].to_string(index=False)
)

auditoria_precios_sku = (
    precios_observados
    .groupby("SKU", as_index=False)
    .agg(
        precios_distintos=("Precio_Unitario_USD", "nunique"),
        precio_minimo=("Precio_Unitario_USD", "min"),
        precio_maximo=("Precio_Unitario_USD", "max"),
    )
    .merge(
        catalogo_precios,
        on="SKU",
        how="left",
        validate="one_to_one",
    )
)

auditoria_precios_sku["diferencia_minima"] = (
    auditoria_precios_sku["precio_minimo"]
    - auditoria_precios_sku["precio_maestro"]
)

auditoria_precios_sku["diferencia_maxima"] = (
    auditoria_precios_sku["precio_maximo"]
    - auditoria_precios_sku["precio_maestro"]
)

problemas_precio = auditoria_precios_sku.loc[
    auditoria_precios_sku["precios_distintos"].gt(1)
    | auditoria_precios_sku["diferencia_minima"].abs().gt(0.000001)
    | auditoria_precios_sku["diferencia_maxima"].abs().gt(0.000001)
]

print("\n--- AUDITORÍA DE PRECIOS POR SKU ---")
print(auditoria_precios_sku.to_string(index=False))
print("SKU con problemas de precio:", len(problemas_precio))

unidades_negativas = ventas_limpias.loc[
    ventas_limpias["Unidades"].lt(0),
    [
        "Fecha",
        "SKU",
        "Producto",
        "Categoria",
        "Canal",
        "Region",
        "Unidades",
        "Promocion",
    ],
].sort_values(["Fecha", "SKU", "Canal", "Region"])

print("\n--- REVISIÓN DE UNIDADES NEGATIVAS ---")
print("Cantidad de filas negativas:", len(unidades_negativas))
print(unidades_negativas.to_string(index=False))

pronostico_real["Fecha"] = pd.to_datetime(
    pronostico_real["Fecha"],
    format="%Y-%m",
    errors="coerce",
)
comparacion_unidades = ventas_limpias.assign(
    Unidades_Negativas_Como_Cero=(
        ventas_limpias["Unidades"].clip(lower=0)
    )
)
resumen_negativos = (
    comparacion_unidades
    .groupby(["Fecha", "SKU"], as_index=False)
    .agg(
        suma_original=("Unidades", "sum"),
        suma_negativos_como_cero=(
            "Unidades_Negativas_Como_Cero",
            "sum",
        ),
        cantidad_negativas=(
            "Unidades",
            lambda columna: columna.lt(0).sum(),
        ),
    )
)

resumen_negativos = resumen_negativos.loc[
    resumen_negativos["cantidad_negativas"] > 0
]
comparacion_negativos = resumen_negativos.merge(
    pronostico_real[["Fecha", "SKU", "Venta_Real"]],
    on=["Fecha", "SKU"],
    how="left",
    validate="one_to_one",
)

comparacion_negativos["diferencia_con_original"] = (
    comparacion_negativos["Venta_Real"]
    - comparacion_negativos["suma_original"]
)

comparacion_negativos["diferencia_usando_cero"] = (
    comparacion_negativos["Venta_Real"]
    - comparacion_negativos["suma_negativos_como_cero"]
)

print("\n--- NEGATIVOS VS. VENTA REAL ---")
print(comparacion_negativos.to_string(index=False))
ventas_limpias["Unidades_Original"] = (
    ventas_limpias["Unidades"]
)

ventas_limpias["Unidades_Negativa_Corregida"] = (
    ventas_limpias["Unidades"].lt(0)
)

impacto_negativos = (
    ventas_limpias.loc[
        ventas_limpias["Unidades_Negativa_Corregida"],
        "Unidades",
    ]
    .abs()
    .sum()
)

ventas_limpias.loc[
    ventas_limpias["Unidades_Negativa_Corregida"],
    "Unidades",
] = 0
print("\n--- RESULTADO DE CORREGIR NEGATIVOS ---")

print(
    "Filas corregidas:",
    ventas_limpias["Unidades_Negativa_Corregida"].sum(),
)

print(
    "Unidades negativas restantes:",
    ventas_limpias["Unidades"].lt(0).sum(),
)

print(
    "Impacto total en unidades:",
    impacto_negativos,
)

print(
    "Unidades vacías restantes:",
    ventas_limpias["Unidades"].isna().sum(),
)
ceros_originales = ventas_limpias.loc[
    ventas_limpias["Unidades_Original"].eq(0),
    [
        "Fecha",
        "SKU",
        "Producto",
        "Categoria",
        "Canal",
        "Region",
        "Unidades_Original",
        "Promocion",
    ],
].sort_values(["Fecha", "SKU", "Canal", "Region"])

print("\n--- CEROS ORIGINALES ---")
print("Cantidad:", len(ceros_originales))
print(ceros_originales.to_string(index=False))
columnas_para_resumir = [
    "Categoria",
    "Canal",
    "Region",
    "Promocion",
]

for columna in columnas_para_resumir:
    print(f"\nCeros por {columna}:")
    print(ceros_originales[columna].value_counts(dropna=False))
    ceros_por_sku_mes = (
    ceros_originales
    .groupby(["Fecha", "SKU"], as_index=False)
    .size()
    .rename(columns={"size": "cantidad_ceros"})
    .sort_values(
        "cantidad_ceros",
        ascending=False,
    )
)

print("\n--- CEROS POR SKU Y MES ---")
print(ceros_por_sku_mes.to_string(index=False))
inventario = pd.read_excel(
    ARCHIVO,
    sheet_name="Inventario y Quiebres",
)

inventario["Fecha"] = pd.to_datetime(
    inventario["Fecha"],
    format="%Y-%m",
    errors="coerce",
)
ventas_mensuales_sku = (
    ventas_limpias
    .groupby(["Fecha", "SKU"], as_index=False)
    .agg(
        Venta_Desde_Detalle=("Unidades", "sum"),
        Ceros_Originales=(
            "Unidades_Original",
            lambda columna: columna.eq(0).sum(),
        ),
    )
)
pronostico_para_cruce = pronostico_real[
    [
        "Fecha",
        "SKU",
        "Pronostico_Empresa",
        "Venta_Real",
    ]
].rename(
    columns={
        "Venta_Real": "Venta_Real_Pronostico",
    }
)

inventario_para_cruce = inventario[
    [
        "Fecha",
        "SKU",
        "Stock_Inicial",
        "Venta_Real",
        "Stock_Final",
        "Venta_Perdida_Unid",
        "Dias_Cobertura",
    ]
].rename(
    columns={
        "Venta_Real": "Venta_Real_Inventario",
    }
)
contexto_sku_1021 = (
    ventas_mensuales_sku
    .merge(
        pronostico_para_cruce,
        on=["Fecha", "SKU"],
        how="left",
        validate="one_to_one",
    )
    .merge(
        inventario_para_cruce,
        on=["Fecha", "SKU"],
        how="left",
        validate="one_to_one",
    )
)

contexto_sku_1021 = contexto_sku_1021.loc[
    contexto_sku_1021["SKU"].eq("SKU-1021")
    & contexto_sku_1021["Fecha"].dt.year.eq(2025)
].sort_values("Fecha")

print("\n--- CONTEXTO DE SKU-1021 EN 2025 ---")
print(contexto_sku_1021.to_string(index=False))

hojas_originales = pd.read_excel(
    ARCHIVO,
    sheet_name=None,
)

for nombre_hoja, tabla in hojas_originales.items():
    print(f"\n=== {nombre_hoja} ===")

    vacios = tabla.isna().sum()
    vacios = vacios[vacios > 0]

    print("Valores vacíos:")
    if vacios.empty:
        print("Ninguno")
    else:
        print(vacios)

    columnas_numericas = tabla.select_dtypes(
        include="number"
    )

    ceros = columnas_numericas.eq(0).sum()
    ceros = ceros[ceros > 0]

    print("\nCeros en columnas numéricas:")
    if ceros.empty:
        print("Ninguno")
    else:
        print(ceros)

columnas_principales = [
    "Fecha",
    "SKU",
    "Producto",
    "Categoria",
    "Canal",
    "Region",
    "Unidades",
    "Precio_Unitario_USD",
    "Promocion",
]

print("\n--- VACÍOS EN VENTAS LIMPIAS ---")
print(
    ventas_limpias[
        columnas_principales
    ].isna().sum()
)

inventario["Fecha"] = pd.to_datetime(
    inventario["Fecha"],
    format="%Y-%m",
    errors="coerce",
)

inventario["Stock_Final_Es_Cero"] = (
    inventario["Stock_Final"].eq(0)
)

inventario["Venta_Perdida_Es_Positiva"] = (
    inventario["Venta_Perdida_Unid"].gt(0)
)

tabla_stock_y_perdida = pd.crosstab(
    inventario["Stock_Final_Es_Cero"],
    inventario["Venta_Perdida_Es_Positiva"],
    rownames=["Stock final es cero"],
    colnames=["Venta perdida es positiva"],
)

print("\n--- STOCK FINAL VS. VENTA PERDIDA ---")
print(tabla_stock_y_perdida)
excepciones_stock = inventario.loc[
    (
        inventario["Stock_Final"].eq(0)
        & inventario["Venta_Perdida_Unid"].eq(0)
    )
    |
    (
        inventario["Stock_Final"].gt(0)
        & inventario["Venta_Perdida_Unid"].gt(0)
    ),
    [
        "Fecha",
        "SKU",
        "Stock_Inicial",
        "Venta_Real",
        "Stock_Final",
        "Venta_Perdida_Unid",
        "Dias_Cobertura",
    ],
].sort_values(["Fecha", "SKU"])

print("\n--- EXCEPCIONES DE STOCK Y VENTA PERDIDA ---")
print(excepciones_stock.to_string(index=False))

contexto_series = ventas_limpias.sort_values(
    ["SKU", "Canal", "Region", "Fecha"]
).copy()

contexto_series["Unidades_Referencia"] = (
    contexto_series["Unidades"].mask(
        contexto_series["SKU"].eq("SKU-1021")
        & contexto_series["Fecha"].ge("2025-07-01")
    )
)

grupo_serie = [
    "SKU",
    "Canal",
    "Region",
]

contexto_series["Mes_Anterior"] = (
    contexto_series
    .groupby(grupo_serie)["Unidades_Referencia"]
    .shift(1)
)

contexto_series["Mes_Siguiente"] = (
    contexto_series
    .groupby(grupo_serie)["Unidades_Referencia"]
    .shift(-1)
)

contexto_series["Mismo_Mes_Anio_Anterior"] = (
    contexto_series
    .groupby(grupo_serie)["Unidades_Referencia"]
    .shift(12)
)

contexto_series["Mismo_Mes_Anio_Siguiente"] = (
    contexto_series
    .groupby(grupo_serie)["Unidades_Referencia"]
    .shift(-12)
)

contexto_series["Promedio_Meses_Vecinos"] = (
    contexto_series[
        [
            "Mes_Anterior",
            "Mes_Siguiente",
        ]
    ].mean(axis=1)
)

contexto_series["Promedio_Mismo_Mes_Otros_Anios"] = (
    contexto_series[
        [
            "Mismo_Mes_Anio_Anterior",
            "Mismo_Mes_Anio_Siguiente",
        ]
    ].mean(axis=1)
)

# Si conocemos dos extremos, podemos interpolar el valor de las unidades vacías.
# Junio es 1278 y Septiembre es 1598, tenemos dos meses sin valor enmedio.
# Formula: incremento mensual = (valor final - valor inicial) / (meses final - meses inicial) = (1598 - 1278) / (9 - 6) = 106.67
# Enronces Julio = 1278 + 106.67 = 1384.67 y Agosto = 1384.67 + 106.67 = 1491.34
contexto_series["Estimacion_Temporal"] = (
    contexto_series
    .groupby(grupo_serie)["Unidades_Referencia"]
    .transform(
        lambda serie: serie.interpolate(
            method="linear",
            limit_area="inside",
        )
    )
)

# Ahora, tenemos que considerar la estacionalidad, no vendes lo mismo en diciembre que en marzo.
#La pseudo formula va a ser : estimacion estacional = mismo mes de otros años / cantidad de años disponibles
# Por ejemplo, si en mayo de 2024 no hay nada, pero tengo mayo del 23 y 25, la estimacion estacional va a ser la media de mayo de 23 y 25.


contexto_series["Mes_Calendario"] = (
    contexto_series["Fecha"].dt.month
)

grupo_estacional = [
    "SKU",
    "Canal",
    "Region",
    "Mes_Calendario",
]

contexto_series["Estimacion_Estacional"] = (
    contexto_series
    .groupby(grupo_estacional)["Unidades_Referencia"]
    .transform("mean")
)

contexto_unidades_vacias = contexto_series.loc[
    contexto_series["Unidades"].isna(),
    [
        "Fecha",
        "SKU",
        "Canal",
        "Region",
        "Promocion",
        "Mes_Anterior",
        "Mes_Siguiente",
        "Mismo_Mes_Anio_Anterior",
        "Mismo_Mes_Anio_Siguiente",
        "Promedio_Meses_Vecinos",
        "Promedio_Mismo_Mes_Otros_Anios",
        "Estimacion_Temporal",
        "Estimacion_Estacional",
    ],
]

print("\n--- CONTEXTO DE UNIDADES VACÍAS ---")
print(contexto_unidades_vacias.to_string(index=False))

# Para comprobar qué método estima mejor, usamos filas cuyas unidades sí
# conocemos. La estimación temporal de prueba usa solamente los meses vecinos,
# sin mirar el valor real de la fila que estamos evaluando.
contexto_series["Temporal_Prueba"] = (
    contexto_series["Mes_Anterior"]
    + contexto_series["Mes_Siguiente"]
) / 2

# Para probar el método estacional de manera justa, calculamos la suma y la
# cantidad de observaciones del mismo mes, SKU, canal y región. Después retiramos
# el valor actual, como si no lo conociéramos.
suma_estacional = (
    contexto_series
    .groupby(grupo_estacional)["Unidades_Referencia"]
    .transform("sum")
)

cantidad_estacional = (
    contexto_series
    .groupby(grupo_estacional)["Unidades_Referencia"]
    .transform("count")
)

contexto_series["Estacional_Prueba"] = (
    (
        suma_estacional
        - contexto_series["Unidades_Referencia"]
    )
    /
    (
        cantidad_estacional - 1
    )
)

# Comparamos ambos métodos usando exactamente las mismas filas. También quedan
# fuera las unidades vacías y los meses de pausa de Azúcar, porque su columna
# Unidades_Referencia contiene NaN.
datos_prueba = contexto_series.loc[
    contexto_series["Unidades_Referencia"].notna()
    & contexto_series["Temporal_Prueba"].notna()
    & contexto_series["Estacional_Prueba"].notna()
].copy()

datos_prueba["Error_Temporal"] = (
    datos_prueba["Unidades"]
    - datos_prueba["Temporal_Prueba"]
).abs()

datos_prueba["Error_Estacional"] = (
    datos_prueba["Unidades"]
    - datos_prueba["Estacional_Prueba"]
).abs()

datos_prueba["Combinada_Prueba"] = (
    datos_prueba["Temporal_Prueba"]
    + datos_prueba["Estacional_Prueba"]
) / 2

datos_prueba["Error_Combinado"] = (
    datos_prueba["Unidades"]
    - datos_prueba["Combinada_Prueba"]
).abs()


# WAPE = suma de errores absolutos / suma de unidades reales × 100.
wape_temporal = (
    datos_prueba["Error_Temporal"].sum()
    / datos_prueba["Unidades"].sum()
) * 100

wape_estacional = (
    datos_prueba["Error_Estacional"].sum()
    / datos_prueba["Unidades"].sum()
) * 100

wape_combinado = (
    datos_prueba["Error_Combinado"].sum()
    / datos_prueba["Unidades"].sum()
) * 100

print("\n--- PRUEBA DE MÉTODOS PARA COMPLETAR VACÍOS ---")
print("Filas comparadas:", len(datos_prueba))
print(f"WAPE temporal: {wape_temporal:.2f}%")
print(f"WAPE estacional: {wape_estacional:.2f}%")
print(f"WAPE combinado: {wape_combinado:.2f}%")

print("\n--- RESULTADO POR PROMOCIÓN ---")

for promocion, grupo in datos_prueba.groupby("Promocion"):
    total_real = grupo["Unidades"].sum()

    wape_temporal_promocion = (
        grupo["Error_Temporal"].sum()
        / total_real
    ) * 100

    wape_estacional_promocion = (
        grupo["Error_Estacional"].sum()
        / total_real
    ) * 100

    wape_combinado_promocion = (
        grupo["Error_Combinado"].sum()
        / total_real
    ) * 100

    print(f"\nPromocion = {promocion}")
    print("Filas comparadas:", len(grupo))
    print(f"WAPE temporal: {wape_temporal_promocion:.2f}%")
    print(f"WAPE estacional: {wape_estacional_promocion:.2f}%")
    print(f"WAPE combinado: {wape_combinado_promocion:.2f}%")


contexto_series["Unidades_Sin_Promocion"] = (
    contexto_series["Unidades_Referencia"].mask(
        contexto_series["Promocion"].eq(1)
    )
)

contexto_series["Base_Temporal_Sin_Promocion"] = (
    contexto_series
    .groupby(grupo_serie)["Unidades_Sin_Promocion"]
    .transform(
        lambda serie: serie.interpolate(
            method="linear",
            limit_area="inside",
        )
    )
)

contexto_series["Base_Estacional_Sin_Promocion"] = (
    contexto_series
    .groupby(grupo_estacional)["Unidades_Sin_Promocion"]
    .transform("mean")
)

contexto_series["Base_Sin_Promocion"] = (
    contexto_series[
        [
            "Base_Temporal_Sin_Promocion",
            "Base_Estacional_Sin_Promocion",
        ]
    ].mean(axis=1)
)

analisis_promocion = contexto_series.loc[
    contexto_series["Promocion"].eq(1)
    & contexto_series["Unidades_Referencia"].notna()
    & contexto_series["Base_Sin_Promocion"].gt(0)
].copy()

analisis_promocion["Factor_Promocion"] = (
    analisis_promocion["Unidades"]
    / analisis_promocion["Base_Sin_Promocion"]
)

print("\n--- EFECTO OBSERVADO DE LAS PROMOCIONES ---")
print("Promociones analizables:", len(analisis_promocion))
print(
    analisis_promocion["Factor_Promocion"]
    .describe(
        percentiles=[0.25, 0.50, 0.75]
    )
)

skus_con_vacio_promocional = (
    contexto_series.loc[
        contexto_series["Unidades"].isna()
        & contexto_series["Promocion"].eq(1),
        "SKU",
    ]
    .unique()
)

resumen_skus_promocion = (
    analisis_promocion.loc[
        analisis_promocion["SKU"].isin(
            skus_con_vacio_promocional
        )
    ]
    .groupby("SKU")["Factor_Promocion"]
    .agg(
        casos="count",
        factor_promedio="mean",
        factor_mediano="median",
    )
)

print("\n--- PROMOCIONES EN LOS SKU CON VACÍOS ---")
print(resumen_skus_promocion)

# Para que el backtest sea honesto, el factor promocional no sólo debe tomar
# filas promocionales de 2023-2024: las referencias temporal y estacional con
# las que se calcula ese factor también deben limitarse al mismo corte. Si se
# reutilizara Base_Sin_Promocion del bloque completo, el promedio estacional
# podría incorporar 2025 de forma indirecta.
contexto_promocion_entrenamiento = contexto_series.loc[
    contexto_series["Fecha"].dt.year.le(2024)
].copy()
contexto_promocion_entrenamiento["Base_Temporal_Entrenamiento"] = (
    contexto_promocion_entrenamiento
    .groupby(grupo_serie)["Unidades_Sin_Promocion"]
    .transform(
        lambda serie: serie.interpolate(
            method="linear",
            limit_area="inside",
        )
    )
)
contexto_promocion_entrenamiento["Base_Estacional_Entrenamiento"] = (
    contexto_promocion_entrenamiento
    .groupby(grupo_estacional)["Unidades_Sin_Promocion"]
    .transform("mean")
)
contexto_promocion_entrenamiento["Base_Entrenamiento"] = (
    contexto_promocion_entrenamiento[
        [
            "Base_Temporal_Entrenamiento",
            "Base_Estacional_Entrenamiento",
        ]
    ].mean(axis=1)
)
promociones_entrenamiento = contexto_promocion_entrenamiento.loc[
    contexto_promocion_entrenamiento["Promocion"].eq(1)
    & contexto_promocion_entrenamiento["Unidades_Referencia"].notna()
    & contexto_promocion_entrenamiento["Base_Entrenamiento"].gt(0)
].copy()
promociones_entrenamiento["Factor_Promocion"] = (
    promociones_entrenamiento["Unidades"]
    / promociones_entrenamiento["Base_Entrenamiento"]
)

promociones_validacion = analisis_promocion.loc[
    analisis_promocion["Fecha"].dt.year.eq(2025)
].copy()

factor_promocional_por_sku = (
    promociones_entrenamiento
    .groupby("SKU")["Factor_Promocion"]
    .median()
)

factor_promocional_global = (
    promociones_entrenamiento["Factor_Promocion"]
    .median()
)

promociones_validacion["Factor_Estimado"] = (
    promociones_validacion["SKU"]
    .map(factor_promocional_por_sku)
    .fillna(factor_promocional_global)
)
promociones_validacion["Estimacion_Ajustada"] = (
    promociones_validacion["Base_Sin_Promocion"]
    * promociones_validacion["Factor_Estimado"]
)
promociones_validacion["Error_Sin_Ajuste"] = (
    promociones_validacion["Unidades"]
    - promociones_validacion["Base_Sin_Promocion"]
).abs()

promociones_validacion["Error_Ajustado"] = (
    promociones_validacion["Unidades"]
    - promociones_validacion["Estimacion_Ajustada"]
).abs()

total_real_promociones = (
    promociones_validacion["Unidades"].sum()
)

wape_promocion_sin_ajuste = (
    promociones_validacion["Error_Sin_Ajuste"].sum()
    / total_real_promociones
) * 100

wape_promocion_ajustado = (
    promociones_validacion["Error_Ajustado"].sum()
    / total_real_promociones
) * 100

print("\n--- VALIDACIÓN DEL AJUSTE PROMOCIONAL EN 2025 ---")
print("Promociones evaluadas:", len(promociones_validacion))
print(
    f"WAPE sin ajuste promocional: "
    f"{wape_promocion_sin_ajuste:.2f}%"
)
print(
    f"WAPE con ajuste promocional: "
    f"{wape_promocion_ajustado:.2f}%"
)
contexto_series["Estimacion_Combinada"] = (
    contexto_series[
        [
            "Estimacion_Temporal",
            "Estimacion_Estacional",
        ]
    ].mean(axis=1)
)
factor_final_por_sku = (
    analisis_promocion
    .groupby("SKU")["Factor_Promocion"]
    .median()
)

factor_final_global = (
    analisis_promocion["Factor_Promocion"]
    .median()
)

contexto_series["Factor_Promocional_SKU"] = (
    contexto_series["SKU"]
    .map(factor_final_por_sku)
    .fillna(factor_final_global)
)

contexto_series["Estimacion_Promocional"] = (
    contexto_series["Base_Sin_Promocion"]
    * contexto_series["Factor_Promocional_SKU"]
)
contexto_series["Estimacion_Propuesta"] = float("nan")
contexto_series["Metodo_Propuesto"] = ""

vacio_con_promocion = (
    contexto_series["Unidades"].isna()
    & contexto_series["Promocion"].eq(1)
)

vacio_sin_promocion = (
    contexto_series["Unidades"].isna()
    & contexto_series["Promocion"].eq(0)
)

contexto_series.loc[
    vacio_con_promocion,
    "Estimacion_Propuesta",
] = contexto_series.loc[
    vacio_con_promocion,
    "Estimacion_Promocional",
]

contexto_series.loc[
    vacio_con_promocion,
    "Metodo_Propuesto",
] = "Base sin promoción × factor del SKU"

contexto_series.loc[
    vacio_sin_promocion,
    "Estimacion_Propuesta",
] = contexto_series.loc[
    vacio_sin_promocion,
    "Estimacion_Combinada",
]

contexto_series.loc[
    vacio_sin_promocion
    & contexto_series["Estimacion_Temporal"].notna(),
    "Metodo_Propuesto",
] = "Promedio temporal-estacional"

contexto_series.loc[
    vacio_sin_promocion
    & contexto_series["Estimacion_Temporal"].isna(),
    "Metodo_Propuesto",
] = "Estacional de respaldo"

propuestas_unidades = contexto_series.loc[
    contexto_series["Unidades"].isna(),
    [
        "Fecha",
        "SKU",
        "Canal",
        "Region",
        "Promocion",
        "Estimacion_Temporal",
        "Estimacion_Estacional",
        "Base_Sin_Promocion",
        "Factor_Promocional_SKU",
        "Estimacion_Propuesta",
        "Metodo_Propuesto",
    ],
]

print("\n--- PROPUESTAS PARA UNIDADES VACÍAS ---")
print(propuestas_unidades.to_string(index=False))

print(
    "Propuestas todavía vacías:",
    propuestas_unidades["Estimacion_Propuesta"].isna().sum(),
)

grupo_comparable = [
    "SKU",
    "Canal",
    "Region",
    "Promocion",
]

contexto_series["Cantidad_Comparables"] = (
    contexto_series
    .groupby(grupo_comparable)["Unidades_Referencia"]
    .transform("count")
)

contexto_series["Minimo_Comparable"] = (
    contexto_series
    .groupby(grupo_comparable)["Unidades_Referencia"]
    .transform("min")
)

contexto_series["Maximo_Comparable"] = (
    contexto_series
    .groupby(grupo_comparable)["Unidades_Referencia"]
    .transform("max")
)

contexto_series["Propuesta_Fuera_Rango"] = (
    contexto_series["Estimacion_Propuesta"].lt(
        contexto_series["Minimo_Comparable"]
    )
    |
    contexto_series["Estimacion_Propuesta"].gt(
        contexto_series["Maximo_Comparable"]
    )
)

revision_rangos = contexto_series.loc[
    contexto_series["Unidades"].isna(),
    [
        "Fecha",
        "SKU",
        "Canal",
        "Region",
        "Promocion",
        "Cantidad_Comparables",
        "Minimo_Comparable",
        "Estimacion_Propuesta",
        "Maximo_Comparable",
        "Propuesta_Fuera_Rango",
    ],
]

print("\n--- REVISIÓN DE RANGOS DE LAS PROPUESTAS ---")
print(revision_rangos.to_string(index=False))

print(
    "Propuestas fuera del rango histórico:",
    revision_rangos["Propuesta_Fuera_Rango"].sum(),
)

skus_objetivo_promocion = [
    "SKU-1003",
    "SKU-1005",
    "SKU-1008",
]

validacion_skus_objetivo = promociones_validacion.loc[
    promociones_validacion["SKU"].isin(
        skus_objetivo_promocion
    )
].copy()

print("\n--- VALIDACIÓN PROMOCIONAL POR SKU OBJETIVO ---")

for sku, grupo in validacion_skus_objetivo.groupby("SKU"):
    total_real = grupo["Unidades"].sum()

    wape_sin_ajuste_sku = (
        grupo["Error_Sin_Ajuste"].sum()
        / total_real
    ) * 100

    wape_ajustado_sku = (
        grupo["Error_Ajustado"].sum()
        / total_real
    ) * 100

    print(f"\n{sku}")
    print("Promociones evaluadas:", len(grupo))
    print(
        f"WAPE sin ajuste: "
        f"{wape_sin_ajuste_sku:.2f}%"
    )
    print(
        f"WAPE ajustado: "
        f"{wape_ajustado_sku:.2f}%"
    )

ventas_modelo = contexto_series.copy()

ventas_modelo["Unidades_Modelo"] = (
    ventas_modelo["Unidades"].copy()
)

ventas_modelo["Unidad_Fue_Estimada"] = (
    ventas_modelo["Unidades"].isna()
)

ventas_modelo["Metodo_Estimacion"] = "Dato observado"

filas_estimadas = (
    ventas_modelo["Unidad_Fue_Estimada"]
)

ventas_modelo.loc[
    filas_estimadas,
    "Unidades_Modelo",
] = ventas_modelo.loc[
    filas_estimadas,
    "Estimacion_Propuesta",
]

ventas_modelo.loc[
    filas_estimadas,
    "Metodo_Estimacion",
] = ventas_modelo.loc[
    filas_estimadas,
    "Metodo_Propuesto",
]

# Medimos por separado el efecto de completar las 28 unidades vacías.
impacto_estimaciones = (
    ventas_modelo["Unidades_Modelo"].sum()
    - ventas_modelo["Unidades"].sum()
)

# Conservamos el valor original de 13,380, pero evitamos que un probable error
# de captura distorsione el modelo. Para la tabla de modelado utilizamos el
# promedio entre la estimación temporal de prueba y la estacional de prueba.
ventas_modelo["Unidad_Fue_Ajustada_Atipico"] = False
ventas_modelo["Metodo_Ajuste_Atipico"] = "Sin ajuste"

caso_atipico = (
    ventas_modelo["Fecha"].eq("2025-03-01")
    & ventas_modelo["SKU"].eq("SKU-1001")
    & ventas_modelo["Canal"].eq("Supermercado")
    & ventas_modelo["Region"].eq("Norte")
)

valor_modelo_antes_del_ajuste = ventas_modelo.loc[
    caso_atipico,
    "Unidades_Modelo",
].sum()

ventas_modelo.loc[
    caso_atipico,
    "Unidades_Modelo",
] = (
    ventas_modelo.loc[caso_atipico, "Temporal_Prueba"]
    + ventas_modelo.loc[caso_atipico, "Estacional_Prueba"]
) / 2

ventas_modelo.loc[
    caso_atipico,
    "Unidad_Fue_Ajustada_Atipico",
] = True

ventas_modelo.loc[
    caso_atipico,
    "Metodo_Ajuste_Atipico",
] = "Promedio temporal-estacional validado"

valor_modelo_despues_del_ajuste = ventas_modelo.loc[
    caso_atipico,
    "Unidades_Modelo",
].sum()

impacto_ajuste_atipico = (
    valor_modelo_despues_del_ajuste
    - valor_modelo_antes_del_ajuste
)

impacto_neto_modelado = (
    ventas_modelo["Unidades_Modelo"].sum()
    - ventas_modelo["Unidades"].sum()
)

print("\n--- RESULTADO FINAL DE UNIDADES PARA MODELAR ---")
print(
    "Vacíos conservados en Unidades:",
    ventas_modelo["Unidades"].isna().sum(),
)
print(
    "Vacíos en Unidades_Modelo:",
    ventas_modelo["Unidades_Modelo"].isna().sum(),
)
print(
    "Filas estimadas:",
    ventas_modelo["Unidad_Fue_Estimada"].sum(),
)
print(
    "Unidades agregadas mediante estimación:",
    impacto_estimaciones,
)
print(
    "Filas ajustadas por valor atípico:",
    ventas_modelo["Unidad_Fue_Ajustada_Atipico"].sum(),
)
print(
    "Valor original del caso atípico:",
    valor_modelo_antes_del_ajuste,
)
print(
    "Valor para modelado del caso atípico:",
    valor_modelo_despues_del_ajuste,
)
print(
    "Impacto del ajuste atípico:",
    impacto_ajuste_atipico,
)
print(
    "Impacto neto de todos los tratamientos:",
    impacto_neto_modelado,
)

print("\nMétodos utilizados:")
print(
    ventas_modelo.loc[
        ventas_modelo["Unidad_Fue_Estimada"],
        "Metodo_Estimacion",
    ].value_counts()
)

auditoria_sku = (
    ventas_modelo
    .groupby("SKU")
    .agg(
        productos_distintos=("Producto", "nunique"),
        categorias_distintas=("Categoria", "nunique"),
        producto_referencia=("Producto", "first"),
        categoria_referencia=("Categoria", "first"),
    )
    .reset_index()
)

problemas_sku = auditoria_sku.loc[
    auditoria_sku["productos_distintos"].gt(1)
    | auditoria_sku["categorias_distintas"].gt(1)
]

print("\n--- CONSISTENCIA DE SKU ---")
print("SKU revisados:", len(auditoria_sku))
print(
    "SKU con varios productos o categorías:",
    len(problemas_sku),
)

if problemas_sku.empty:
    print("Todos los SKU tienen un producto y una categoría únicos.")
else:
    print(problemas_sku.to_string(index=False))

auditoria_producto = (
    ventas_modelo
    .groupby("Producto")
    .agg(
        sku_distintos=("SKU", "nunique"),
        categorias_distintas=("Categoria", "nunique"),
    )
    .reset_index()
)

problemas_producto = auditoria_producto.loc[
    auditoria_producto["sku_distintos"].gt(1)
    | auditoria_producto["categorias_distintas"].gt(1)
]

print("\n--- CONSISTENCIA DE PRODUCTOS ---")
print("Productos revisados:", len(auditoria_producto))
print(
    "Productos con varios SKU o categorías:",
    len(problemas_producto),
)

if problemas_producto.empty:
    print("Cada producto tiene un SKU y una categoría únicos.")
else:
    print(problemas_producto.to_string(index=False))


ventas_modelo["Es_Pausa_Azucar"] = (
    ventas_modelo["SKU"].eq("SKU-1021")
    & ventas_modelo["Fecha"].ge("2025-07-01")
)

ventas_modelo["Unidades_Auditoria"] = (
    ventas_modelo["Unidades_Modelo"].mask(
        ventas_modelo["Es_Pausa_Azucar"]
    )
)

grupo_extremos = [
    "SKU",
    "Canal",
    "Region",
]

ventas_modelo["Q1_Unidades"] = (
    ventas_modelo
    .groupby(grupo_extremos)["Unidades_Auditoria"]
    .transform(lambda serie: serie.quantile(0.25))
)

ventas_modelo["Q3_Unidades"] = (
    ventas_modelo
    .groupby(grupo_extremos)["Unidades_Auditoria"]
    .transform(lambda serie: serie.quantile(0.75))
)

ventas_modelo["IQR_Unidades"] = (
    ventas_modelo["Q3_Unidades"]
    - ventas_modelo["Q1_Unidades"]
)

ventas_modelo["Limite_Inferior"] = (
    ventas_modelo["Q1_Unidades"]
    - 1.5 * ventas_modelo["IQR_Unidades"]
)

ventas_modelo["Limite_Superior"] = (
    ventas_modelo["Q3_Unidades"]
    + 1.5 * ventas_modelo["IQR_Unidades"]
)

ventas_modelo["Es_Valor_Extremo"] = (
    ventas_modelo["Unidades_Auditoria"].notna()
    &
    (
        ventas_modelo["Unidades_Auditoria"].lt(
            ventas_modelo["Limite_Inferior"]
        )
        |
        ventas_modelo["Unidades_Auditoria"].gt(
            ventas_modelo["Limite_Superior"]
        )
    )
)

valores_extremos = ventas_modelo.loc[
    ventas_modelo["Es_Valor_Extremo"],
    [
        "Fecha",
        "SKU",
        "Producto",
        "Canal",
        "Region",
        "Promocion",
        "Unidades_Modelo",
        "Unidad_Fue_Estimada",
        "Limite_Inferior",
        "Limite_Superior",
    ],
].sort_values(
    ["SKU", "Canal", "Region", "Fecha"]
)

print("\n--- VALORES EXTREMOS DE UNIDADES ---")
print("Cantidad:", len(valores_extremos))
print(valores_extremos.to_string(index=False))

print("\nExtremos según promoción:")
print(valores_extremos["Promocion"].value_counts())

print("\nExtremos que fueron estimados:")
print(valores_extremos["Unidad_Fue_Estimada"].value_counts())

extremos_sin_promocion = ventas_modelo.loc[
    ventas_modelo["Es_Valor_Extremo"]
    & ventas_modelo["Promocion"].eq(0)
].copy()

extremos_altos_sin_promocion = extremos_sin_promocion.loc[
    extremos_sin_promocion["Unidades_Modelo"].gt(
        extremos_sin_promocion["Limite_Superior"]
    )
].copy()

extremos_bajos_sin_promocion = extremos_sin_promocion.loc[
    extremos_sin_promocion["Unidades_Modelo"].lt(
        extremos_sin_promocion["Limite_Inferior"]
    )
].copy()

extremos_altos_sin_promocion["Veces_Sobre_Limite"] = (
    extremos_altos_sin_promocion["Unidades_Modelo"]
    / extremos_altos_sin_promocion["Limite_Superior"]
)

extremos_altos_sin_promocion = (
    extremos_altos_sin_promocion
    .sort_values(
        "Veces_Sobre_Limite",
        ascending=False,
    )
)

print("\n--- EXTREMOS ALTOS SIN PROMOCIÓN ---")
print("Cantidad:", len(extremos_altos_sin_promocion))
print(
    extremos_altos_sin_promocion[
        [
            "Fecha",
            "SKU",
            "Producto",
            "Canal",
            "Region",
            "Unidades_Modelo",
            "Limite_Superior",
            "Veces_Sobre_Limite",
        ]
    ].to_string(index=False)
)

print("\n--- EXTREMOS BAJOS SIN PROMOCIÓN ---")
print("Cantidad:", len(extremos_bajos_sin_promocion))
print(
    extremos_bajos_sin_promocion[
        [
            "Fecha",
            "SKU",
            "Producto",
            "Canal",
            "Region",
            "Unidades_Modelo",
            "Limite_Inferior",
        ]
    ].to_string(index=False)
)

fecha_caso = pd.Timestamp("2025-03-01")
sku_caso = "SKU-1001"

contexto_temporal_caso = ventas_modelo.loc[
    ventas_modelo["SKU"].eq(sku_caso)
    & ventas_modelo["Canal"].eq("Supermercado")
    & ventas_modelo["Region"].eq("Norte")
    &
    (
        ventas_modelo["Fecha"].dt.month.eq(3)
        |
        ventas_modelo["Fecha"].between(
            "2025-01-01",
            "2025-05-01",
        )
    ),
    [
        "Fecha",
        "Unidades",
        "Unidades_Modelo",
        "Promocion",
    ],
].sort_values("Fecha")

print("\n--- HISTORIAL DEL CASO EXTREMO ---")
print(contexto_temporal_caso.to_string(index=False))

detalle_mismo_mes = ventas_modelo.loc[
    ventas_modelo["SKU"].eq(sku_caso)
    & ventas_modelo["Fecha"].eq(fecha_caso),
    [
        "Canal",
        "Region",
        "Unidades_Modelo",
        "Promocion",
    ],
].sort_values(["Canal", "Region"])

print("\n--- SKU-1001 EN MARZO DE 2025 ---")
print(detalle_mismo_mes.to_string(index=False))
print(
    "Total desde el detalle:",
    detalle_mismo_mes["Unidades_Modelo"].sum(),
)

caso_pronostico = pronostico_real.loc[
    pronostico_real["SKU"].eq(sku_caso)
    & pronostico_real["Fecha"].eq(fecha_caso)
]

caso_inventario = inventario.loc[
    inventario["SKU"].eq(sku_caso)
    & inventario["Fecha"].eq(fecha_caso)
]

print("\n--- CASO EN PRONÓSTICO VS. REAL ---")
print(caso_pronostico.to_string(index=False))

print("\n--- CASO EN INVENTARIO Y QUIEBRES ---")
print(caso_inventario.to_string(index=False))

inventario["Stock_Final_Calculado"] = (
    inventario["Stock_Inicial"]
    - inventario["Venta_Real"]
).clip(lower=0)

inventario["Venta_Perdida_Calculada"] = (
    inventario["Venta_Real"]
    - inventario["Stock_Inicial"]
).clip(lower=0)

inventario["Diferencia_Stock_Final"] = (
    inventario["Stock_Final"]
    - inventario["Stock_Final_Calculado"]
)

inventario["Diferencia_Venta_Perdida"] = (
    inventario["Venta_Perdida_Unid"]
    - inventario["Venta_Perdida_Calculada"]
)

print("\n--- VALIDACIÓN DE FÓRMULAS DE INVENTARIO ---")
print(
    "Filas donde no coincide Stock_Final:",
    inventario["Diferencia_Stock_Final"].ne(0).sum(),
)
print(
    "Filas donde no coincide Venta_Perdida:",
    inventario["Diferencia_Venta_Perdida"].ne(0).sum(),
)
print(
    "Máxima diferencia de Stock_Final:",
    inventario["Diferencia_Stock_Final"].abs().max(),
)
print(
    "Máxima diferencia de Venta_Perdida:",
    inventario["Diferencia_Venta_Perdida"].abs().max(),
)
claves_por_hoja = {
    "Pronostico vs Real": [
        "Fecha",
        "SKU",
    ],
    "Inventario y Quiebres": [
        "Fecha",
        "SKU",
    ],
    "Precios y Costos": [
        "SKU",
    ],
}

print("\n--- CLAVES Y DUPLICADOS EN OTRAS HOJAS ---")

for nombre_hoja, columnas_clave in claves_por_hoja.items():
    tabla = hojas_originales[nombre_hoja]

    claves_repetidas = tabla.duplicated(
        subset=columnas_clave,
        keep=False,
    )

    duplicados_exactos = tabla.duplicated(
        keep=False,
    )

    print(f"\n{nombre_hoja}")
    print("Filas:", len(tabla))
    print(
        "Claves únicas:",
        tabla[columnas_clave]
        .drop_duplicates()
        .shape[0],
    )
    print(
        "Filas involucradas en claves repetidas:",
        claves_repetidas.sum(),
    )
    print(
        "Filas involucradas en duplicados exactos:",
        duplicados_exactos.sum(),
    )

    if claves_repetidas.any():
        print(
            tabla.loc[claves_repetidas]
            .sort_values(columnas_clave)
            .to_string(index=False)
        )
for nombre_hoja in [
    "Pronostico vs Real",
    "Inventario y Quiebres",
]:
    tabla = hojas_originales[nombre_hoja]

    filas_esperadas_hoja = (
        tabla["Fecha"].nunique()
        * tabla["SKU"].nunique()
    )

    print(f"\n{nombre_hoja}")
    print("Meses:", tabla["Fecha"].nunique())
    print("SKU:", tabla["SKU"].nunique())
    print("Filas esperadas:", filas_esperadas_hoja)
    print("Filas recibidas:", len(tabla))

    claves_pronostico = pd.MultiIndex.from_frame(
    hojas_originales["Pronostico vs Real"][
        ["Fecha", "SKU"]
    ]
)

claves_inventario = pd.MultiIndex.from_frame(
    hojas_originales["Inventario y Quiebres"][
        ["Fecha", "SKU"]
    ]
)

solo_en_pronostico = claves_pronostico.difference(
    claves_inventario
)

solo_en_inventario = claves_inventario.difference(
    claves_pronostico
)

print("\n--- COBERTURA ENTRE PRONÓSTICO E INVENTARIO ---")
print(
    "Claves solamente en Pronostico vs Real:",
    len(solo_en_pronostico),
)
print(
    "Claves solamente en Inventario y Quiebres:",
    len(solo_en_inventario),
)

ventas_sistema = ventas.copy()

ventas_sistema["Fecha"] = pd.to_datetime(
    ventas_sistema["Fecha"],
    format="%Y-%m",
    errors="coerce",
)

ventas_sistema["Unidades_Sistema"] = (
    ventas_sistema["Unidades"].clip(lower=0)
)

sistema_por_sku_mes = (
    ventas_sistema
    .groupby(
        ["Fecha", "SKU"],
        as_index=False,
    )
    .agg(
        Venta_Sistema=(
            "Unidades_Sistema",
            "sum",
        ),
    )
)

limpia_por_sku_mes = (
    ventas_limpias
    .groupby(
        ["Fecha", "SKU"],
        as_index=False,
    )
    .agg(
        Venta_Limpia=(
            "Unidades",
            "sum",
        ),
    )
)

modelo_por_sku_mes = (
    ventas_modelo
    .groupby(
        ["Fecha", "SKU"],
        as_index=False,
    )
    .agg(
        Venta_Modelo=(
            "Unidades_Modelo",
            "sum",
        ),
        Filas_Estimadas=(
            "Unidad_Fue_Estimada",
            "sum",
        ),
        Filas_Ajustadas_Atipico=(
            "Unidad_Fue_Ajustada_Atipico",
            "sum",
        ),
    )
)

reconciliacion_ventas = (
    pronostico_real[
        [
            "Fecha",
            "SKU",
            "Venta_Real",
        ]
    ]
    .merge(
        sistema_por_sku_mes,
        on=["Fecha", "SKU"],
        how="left",
        validate="one_to_one",
    )
    .merge(
        limpia_por_sku_mes,
        on=["Fecha", "SKU"],
        how="left",
        validate="one_to_one",
    )
    .merge(
        modelo_por_sku_mes,
        on=["Fecha", "SKU"],
        how="left",
        validate="one_to_one",
    )
)

reconciliacion_ventas["Diferencia_Sistema_Empresa"] = (
    reconciliacion_ventas["Venta_Sistema"]
    - reconciliacion_ventas["Venta_Real"]
)

reconciliacion_ventas["Diferencia_Limpia_Empresa"] = (
    reconciliacion_ventas["Venta_Limpia"]
    - reconciliacion_ventas["Venta_Real"]
)

reconciliacion_ventas["Ajuste_Modelo_Sobre_Limpia"] = (
    reconciliacion_ventas["Venta_Modelo"]
    - reconciliacion_ventas["Venta_Limpia"]
)

reconciliacion_ventas["Diferencia_Modelo_Empresa"] = (
    reconciliacion_ventas["Venta_Modelo"]
    - reconciliacion_ventas["Venta_Real"]
)
tolerancia = 0.001

reconciliacion_ventas["Cambio_Tras_Limpieza"] = (
    reconciliacion_ventas[
        "Diferencia_Limpia_Empresa"
    ].abs().gt(tolerancia)
)

reconciliacion_ventas["Cambio_Por_Estimacion"] = (
    reconciliacion_ventas["Filas_Estimadas"].gt(0)
)

reconciliacion_ventas["Cambio_Por_Atipico"] = (
    reconciliacion_ventas[
        "Filas_Ajustadas_Atipico"
    ].gt(0)
)
print("\n--- RECONCILIACIÓN DE VENTAS ---")

print(
    "Diferencias entre sistema y empresa:",
    reconciliacion_ventas[
        "Diferencia_Sistema_Empresa"
    ].abs().gt(tolerancia).sum(),
)

print(
    "SKU-meses cambiados tras limpiar:",
    reconciliacion_ventas[
        "Cambio_Tras_Limpieza"
    ].sum(),
)

print(
    "SKU-meses con estimaciones:",
    reconciliacion_ventas[
        "Cambio_Por_Estimacion"
    ].sum(),
)

print(
    "SKU-meses con ajuste atípico:",
    reconciliacion_ventas[
        "Cambio_Por_Atipico"
    ].sum(),
)

print("\nTotales:")
print(
    reconciliacion_ventas[
        [
            "Venta_Real",
            "Venta_Sistema",
            "Venta_Limpia",
            "Venta_Modelo",
        ]
    ].sum()
)
casos_reconciliacion = reconciliacion_ventas.loc[
    reconciliacion_ventas["Cambio_Tras_Limpieza"]
    | reconciliacion_ventas["Cambio_Por_Estimacion"]
    | reconciliacion_ventas["Cambio_Por_Atipico"],
    [
        "Fecha",
        "SKU",
        "Venta_Real",
        "Venta_Sistema",
        "Venta_Limpia",
        "Venta_Modelo",
        "Diferencia_Limpia_Empresa",
        "Ajuste_Modelo_Sobre_Limpia",
        "Diferencia_Modelo_Empresa",
        "Filas_Estimadas",
        "Filas_Ajustadas_Atipico",
    ],
].sort_values(["Fecha", "SKU"])

print("\n--- SKU-MESES AFECTADOS ---")
print("Cantidad:", len(casos_reconciliacion))
print(casos_reconciliacion.to_string(index=False))

# Reconciliación de inventario. Conservamos las columnas originales y calculamos
# un escenario separado con la demanda limpia de Venta_Modelo.
inventario_reconciliado = (
    reconciliacion_ventas
    .merge(
        inventario[
            [
                "Fecha",
                "SKU",
                "Stock_Inicial",
                "Venta_Real",
                "Stock_Final",
                "Venta_Perdida_Unid",
                "Dias_Cobertura",
            ]
        ].rename(
            columns={
                "Venta_Real": "Venta_Real_Inventario",
            }
        ),
        on=["Fecha", "SKU"],
        how="left",
        validate="one_to_one",
    )
)

inventario_reconciliado["Diferencia_Venta_Entre_Hojas"] = (
    inventario_reconciliado["Venta_Real"]
    - inventario_reconciliado["Venta_Real_Inventario"]
)

inventario_reconciliado["Stock_Final_Modelo"] = (
    inventario_reconciliado["Stock_Inicial"]
    - inventario_reconciliado["Venta_Modelo"]
).clip(lower=0)

inventario_reconciliado["Venta_Perdida_Modelo"] = (
    inventario_reconciliado["Venta_Modelo"]
    - inventario_reconciliado["Stock_Inicial"]
).clip(lower=0)

inventario_reconciliado["Venta_Atendida_Original"] = (
    inventario_reconciliado["Venta_Real_Inventario"]
    - inventario_reconciliado["Venta_Perdida_Unid"]
)

inventario_reconciliado["Venta_Atendida_Modelo"] = (
    inventario_reconciliado["Venta_Modelo"]
    - inventario_reconciliado["Venta_Perdida_Modelo"]
)

inventario_reconciliado["Cambio_Stock_Final"] = (
    inventario_reconciliado["Stock_Final_Modelo"]
    - inventario_reconciliado["Stock_Final"]
)

inventario_reconciliado["Cambio_Venta_Perdida"] = (
    inventario_reconciliado["Venta_Perdida_Modelo"]
    - inventario_reconciliado["Venta_Perdida_Unid"]
)

inventario_reconciliado["Cambio_Venta_Atendida"] = (
    inventario_reconciliado["Venta_Atendida_Modelo"]
    - inventario_reconciliado["Venta_Atendida_Original"]
)

stockouts_originales = (
    inventario_reconciliado["Venta_Perdida_Unid"].gt(0).sum()
)

stockouts_modelo = (
    inventario_reconciliado["Venta_Perdida_Modelo"].gt(0).sum()
)

print("\n--- RECONCILIACIÓN DE INVENTARIO ---")
print(
    "Diferencias de Venta_Real entre hojas:",
    inventario_reconciliado[
        "Diferencia_Venta_Entre_Hojas"
    ].abs().gt(tolerancia).sum(),
)
print("SKU-meses con quiebre original:", stockouts_originales)
print("SKU-meses con quiebre después de limpiar:", stockouts_modelo)
print(
    "Venta perdida original:",
    inventario_reconciliado["Venta_Perdida_Unid"].sum(),
)
print(
    "Venta perdida después de limpiar:",
    inventario_reconciliado["Venta_Perdida_Modelo"].sum(),
)
print(
    "Venta atendida original:",
    inventario_reconciliado["Venta_Atendida_Original"].sum(),
)
print(
    "Venta atendida después de limpiar:",
    inventario_reconciliado["Venta_Atendida_Modelo"].sum(),
)

casos_inventario_cambiado = inventario_reconciliado.loc[
    inventario_reconciliado["Cambio_Stock_Final"].abs().gt(tolerancia)
    | inventario_reconciliado["Cambio_Venta_Perdida"].abs().gt(tolerancia)
].copy()

casos_inventario_cambiado["Magnitud_Cambio"] = (
    casos_inventario_cambiado["Cambio_Stock_Final"].abs()
    + casos_inventario_cambiado["Cambio_Venta_Perdida"].abs()
)

casos_inventario_cambiado = casos_inventario_cambiado.sort_values(
    "Magnitud_Cambio",
    ascending=False,
)

print("\n--- MAYORES CAMBIOS EN INVENTARIO ---")
print("Cantidad de SKU-meses:", len(casos_inventario_cambiado))
print(
    casos_inventario_cambiado[
        [
            "Fecha",
            "SKU",
            "Stock_Inicial",
            "Venta_Real_Inventario",
            "Venta_Modelo",
            "Stock_Final",
            "Stock_Final_Modelo",
            "Venta_Perdida_Unid",
            "Venta_Perdida_Modelo",
            "Cambio_Venta_Atendida",
        ]
    ].head(20).to_string(index=False)
)

# Días de cobertura: cuántos días podría durar el stock final si continuara el
# ritmo promedio de venta del mes, usando meses convencionales de 30 días.
inventario_reconciliado["Dias_Cobertura_Calculados"] = (
    (
        inventario_reconciliado["Stock_Final"]
        / inventario_reconciliado["Venta_Real_Inventario"]
        * 30
    )
    .where(inventario_reconciliado["Venta_Real_Inventario"].gt(0))
    .round(1)
)

cobertura_coincide = (
    inventario_reconciliado["Dias_Cobertura"].isna()
    & inventario_reconciliado["Dias_Cobertura_Calculados"].isna()
) | (
    inventario_reconciliado["Dias_Cobertura"]
    - inventario_reconciliado["Dias_Cobertura_Calculados"]
).abs().le(tolerancia)

print("\n--- VALIDACIÓN DE DÍAS DE COBERTURA ---")
print("Filas revisadas:", len(inventario_reconciliado))
print("Filas que no coinciden:", (~cobertura_coincide).sum())
print(
    "Vacíos esperados cuando Venta_Real es cero:",
    inventario_reconciliado["Dias_Cobertura_Calculados"].isna().sum(),
)

# Nivel de servicio por unidades (fill rate) y por ocurrencia de quiebres.
demanda_original_total = inventario_reconciliado[
    "Venta_Real_Inventario"
].sum()
venta_atendida_original_total = inventario_reconciliado[
    "Venta_Atendida_Original"
].sum()

nivel_servicio_unidades_original = (
    venta_atendida_original_total / demanda_original_total * 100
)

nivel_servicio_ciclos_original = (
    inventario_reconciliado["Venta_Perdida_Unid"].eq(0).mean() * 100
)

demanda_modelo_total = inventario_reconciliado["Venta_Modelo"].sum()
venta_atendida_modelo_total = inventario_reconciliado[
    "Venta_Atendida_Modelo"
].sum()
nivel_servicio_unidades_modelo = (
    venta_atendida_modelo_total / demanda_modelo_total * 100
)

inventario_reconciliado_2025 = inventario_reconciliado.loc[
    inventario_reconciliado["Fecha"].dt.year.eq(2025)
].copy()

nivel_servicio_unidades_original_2025 = (
    inventario_reconciliado_2025["Venta_Atendida_Original"].sum()
    / inventario_reconciliado_2025["Venta_Real_Inventario"].sum()
    * 100
)

nivel_servicio_unidades_modelo_2025 = (
    inventario_reconciliado_2025["Venta_Atendida_Modelo"].sum()
    / inventario_reconciliado_2025["Venta_Modelo"].sum()
    * 100
)

nivel_servicio_ciclos_2025 = (
    inventario_reconciliado_2025["Venta_Perdida_Unid"].eq(0).mean()
    * 100
)

print("\n--- NIVEL DE SERVICIO ---")
print("Nivel declarado por Gerencia: 96.00%")
print(
    f"Nivel por unidades, historial original: "
    f"{nivel_servicio_unidades_original:.2f}%"
)
print(
    f"Nivel por unidades, historial limpio: "
    f"{nivel_servicio_unidades_modelo:.2f}%"
)
print(
    f"SKU-meses sin venta perdida, historial: "
    f"{nivel_servicio_ciclos_original:.2f}%"
)
print(
    f"Nivel por unidades 2025, original: "
    f"{nivel_servicio_unidades_original_2025:.2f}%"
)
print(
    f"Nivel por unidades 2025, limpio: "
    f"{nivel_servicio_unidades_modelo_2025:.2f}%"
)
print(
    f"SKU-meses sin venta perdida 2025: "
    f"{nivel_servicio_ciclos_2025:.2f}%"
)

# Catálogo financiero. Margen_Bruto_pct está expresado como decimal: 0.309
# equivale a 30.9%. Como no existe una columna de costo del producto, se deriva
# un costo unitario teórico a partir del precio y el margen declarado.
catalogo_financiero = precios_costos.copy()
catalogo_financiero["Margen_Bruto_USD_Unid"] = (
    catalogo_financiero["Precio_Venta_USD"]
    * catalogo_financiero["Margen_Bruto_pct"]
)
catalogo_financiero["Costo_Producto_Estimado_USD_Unid"] = (
    catalogo_financiero["Precio_Venta_USD"]
    * (1 - catalogo_financiero["Margen_Bruto_pct"])
)

print("\n--- VALIDACIÓN DE PRECIOS, MÁRGENES Y COSTOS ---")
print(
    "Márgenes fuera del intervalo 0 a 1:",
    (~catalogo_financiero["Margen_Bruto_pct"].between(0, 1)).sum(),
)
print(
    "Precios no positivos:",
    catalogo_financiero["Precio_Venta_USD"].le(0).sum(),
)
print(
    "Costos de almacenaje no positivos:",
    catalogo_financiero[
        "Costo_Almacenaje_Mes_USD_Unid"
    ].le(0).sum(),
)
print(
    "Vida útil no positiva:",
    catalogo_financiero["Vida_Util_Meses"].le(0).sum(),
)

# Rotación 2025 con la fórmula estándar: costo de ventas dividido entre el valor
# promedio del inventario. Es una aproximación porque el archivo no contiene el
# costo contable real ni movimientos de compras/recepciones.
inventario_financiero = inventario_reconciliado.merge(
    catalogo_financiero[
        [
            "SKU",
            "Precio_Venta_USD",
            "Margen_Bruto_pct",
            "Costo_Producto_Estimado_USD_Unid",
            "Costo_Almacenaje_Mes_USD_Unid",
        ]
    ],
    on="SKU",
    how="left",
    validate="many_to_one",
)

inventario_financiero["Inventario_Promedio_Unidades"] = (
    inventario_financiero["Stock_Inicial"]
    + inventario_financiero["Stock_Final"]
) / 2

inventario_financiero["Inventario_Promedio_Valor"] = (
    inventario_financiero["Inventario_Promedio_Unidades"]
    * inventario_financiero["Costo_Producto_Estimado_USD_Unid"]
)

inventario_financiero["Costo_Venta_Atendida"] = (
    inventario_financiero["Venta_Atendida_Original"]
    * inventario_financiero["Costo_Producto_Estimado_USD_Unid"]
)

inventario_financiero["Ingreso_Atendido"] = (
    inventario_financiero["Venta_Atendida_Original"]
    * inventario_financiero["Precio_Venta_USD"]
)

inventario_financiero["Margen_Bruto_USD"] = (
    inventario_financiero["Ingreso_Atendido"]
    * inventario_financiero["Margen_Bruto_pct"]
)

inventario_financiero["Costo_Almacenaje_Estimado"] = (
    inventario_financiero["Inventario_Promedio_Unidades"]
    * inventario_financiero["Costo_Almacenaje_Mes_USD_Unid"]
)

inventario_financiero_2025 = inventario_financiero.loc[
    inventario_financiero["Fecha"].dt.year.eq(2025)
].copy()

costo_ventas_2025 = inventario_financiero_2025[
    "Costo_Venta_Atendida"
].sum()
inventario_promedio_valor_2025 = (
    inventario_financiero_2025["Inventario_Promedio_Valor"].sum()
    / 12
)
rotacion_calculada_2025 = (
    costo_ventas_2025 / inventario_promedio_valor_2025
)

ingreso_atendido_2025 = inventario_financiero_2025[
    "Ingreso_Atendido"
].sum()
margen_bruto_2025 = inventario_financiero_2025[
    "Margen_Bruto_USD"
].sum()
margen_bruto_ponderado_2025 = (
    margen_bruto_2025 / ingreso_atendido_2025 * 100
)
costo_almacenaje_estimado_2025 = inventario_financiero_2025[
    "Costo_Almacenaje_Estimado"
].sum()

print("\n--- ROTACIÓN Y MARGEN 2025 ---")
print("Rotación declarada:", 5.1)
print(f"Rotación estándar aproximada: {rotacion_calculada_2025:.2f}")
print(f"Ingreso atendido: {ingreso_atendido_2025:.2f}")
print(f"Margen bruto USD: {margen_bruto_2025:.2f}")
print(f"Margen bruto ponderado: {margen_bruto_ponderado_2025:.2f}%")
print(
    f"Costo de almacenaje anual estimado: "
    f"{costo_almacenaje_estimado_2025:.2f}"
)

# Reconciliación del Resumen Gerencia.
resumen_gerencia = hojas_originales["Resumen Gerencia"].copy()

def valor_resumen(texto_indicador):
    """Obtiene el valor de la primera fila cuyo indicador contiene el texto."""
    return resumen_gerencia.loc[
        resumen_gerencia["Indicador"].str.contains(
            texto_indicador,
            case=False,
            regex=False,
        ),
        "Valor",
    ].iloc[0]


venta_total_declarada = float(valor_resumen("Venta total 2025"))
ventas_regionales_declaradas = pd.DataFrame(
    {
        "Region": ["Norte", "Centro", "Sur"],
        "Venta_Declarada_USD": [
            float(valor_resumen("Region Norte")),
            float(valor_resumen("Region Centro")),
            float(valor_resumen("Region Sur")),
        ],
    }
)

ventas_sistema_finanzas = ventas_sistema.merge(
    catalogo_financiero[["SKU", "Precio_Venta_USD"]],
    on="SKU",
    how="left",
    validate="many_to_one",
)
ventas_sistema_finanzas["Ingreso_Sistema_USD"] = (
    ventas_sistema_finanzas["Unidades_Sistema"]
    * ventas_sistema_finanzas["Precio_Venta_USD"]
)

ingreso_sistema_region_2025 = (
    ventas_sistema_finanzas.loc[
        ventas_sistema_finanzas["Fecha"].dt.year.eq(2025)
    ]
    .groupby("Region", as_index=False)
    .agg(Ingreso_Sistema_USD=("Ingreso_Sistema_USD", "sum"))
)

ventas_modelo_2025 = ventas_modelo.loc[
    ventas_modelo["Fecha"].dt.year.eq(2025)
].copy()
ventas_modelo_2025["Ingreso_Modelo_USD"] = (
    ventas_modelo_2025["Unidades_Modelo"]
    * ventas_modelo_2025["Precio_Unitario_USD"]
)
ingreso_modelo_region_2025 = (
    ventas_modelo_2025
    .groupby("Region", as_index=False)
    .agg(Ingreso_Modelo_USD=("Ingreso_Modelo_USD", "sum"))
)

reconciliacion_regiones_2025 = (
    ventas_regionales_declaradas
    .merge(
        ingreso_sistema_region_2025,
        on="Region",
        how="left",
        validate="one_to_one",
    )
    .merge(
        ingreso_modelo_region_2025,
        on="Region",
        how="left",
        validate="one_to_one",
    )
)
reconciliacion_regiones_2025["Dif_Declarada_Sistema"] = (
    reconciliacion_regiones_2025["Venta_Declarada_USD"]
    - reconciliacion_regiones_2025["Ingreso_Sistema_USD"]
)
reconciliacion_regiones_2025["Dif_Declarada_Modelo"] = (
    reconciliacion_regiones_2025["Venta_Declarada_USD"]
    - reconciliacion_regiones_2025["Ingreso_Modelo_USD"]
)

suma_regiones_declaradas = ventas_regionales_declaradas[
    "Venta_Declarada_USD"
].sum()
ingreso_sistema_total_2025 = ingreso_sistema_region_2025[
    "Ingreso_Sistema_USD"
].sum()
ingreso_modelo_total_2025 = ingreso_modelo_region_2025[
    "Ingreso_Modelo_USD"
].sum()

print("\n--- RECONCILIACIÓN DEL RESUMEN GERENCIA ---")
print(f"Venta total declarada: {venta_total_declarada:.2f}")
print(f"Suma de regiones declaradas: {suma_regiones_declaradas:.2f}")
print(
    f"Diferencia total vs regiones declaradas: "
    f"{venta_total_declarada - suma_regiones_declaradas:.2f}"
)
print(f"Ingreso desde sistema original: {ingreso_sistema_total_2025:.2f}")
print(f"Ingreso desde demanda limpia: {ingreso_modelo_total_2025:.2f}")
print(f"Ingreso realmente atendido: {ingreso_atendido_2025:.2f}")
print("\nComparación por región:")
print(reconciliacion_regiones_2025.to_string(index=False))

print("\n--- LIMITACIÓN DE PROMOCIONES ---")
print(
    "La columna Promocion solo indica 0 o 1; no informa tipo, descuento, "
    "intensidad ni duración. Los efectos históricos se pueden medir, pero "
    "una promoción futura requiere un calendario de promociones o un ajuste manual."
)

# ---------------------------------------------------------------------------
# Evaluación histórica del pronóstico de la empresa
# ---------------------------------------------------------------------------

evaluacion_empresa = (
    pronostico_real[
        [
            "Fecha",
            "SKU",
            "Categoria",
            "Pronostico_Empresa",
            "Venta_Real",
        ]
    ]
    .merge(
        modelo_por_sku_mes[
            [
                "Fecha",
                "SKU",
                "Venta_Modelo",
            ]
        ],
        on=["Fecha", "SKU"],
        how="left",
        validate="one_to_one",
    )
)

evaluacion_empresa["Anio"] = evaluacion_empresa["Fecha"].dt.year
evaluacion_empresa["Es_Periodo_Inactivo_Azucar"] = (
    evaluacion_empresa["SKU"].eq("SKU-1021")
    & evaluacion_empresa["Fecha"].ge("2025-07-01")
)


def calcular_metricas_pronostico(tabla, columna_real, columna_pronostico):
    """Calcula WAPE y sesgo de un pronóstico sobre una tabla determinada."""
    real = tabla[columna_real]
    pronostico = tabla[columna_pronostico]
    error = pronostico - real

    return pd.Series(
        {
            "observaciones": len(tabla),
            "demanda_real": real.sum(),
            "WAPE_pct": error.abs().sum() / real.sum() * 100,
            "Sesgo_pct": error.sum() / real.sum() * 100,
        }
    )


metricas_empresa_reportadas = calcular_metricas_pronostico(
    evaluacion_empresa,
    "Venta_Real",
    "Pronostico_Empresa",
)

metricas_empresa_limpias = calcular_metricas_pronostico(
    evaluacion_empresa,
    "Venta_Modelo",
    "Pronostico_Empresa",
)

evaluacion_empresa_activos = evaluacion_empresa.loc[
    ~evaluacion_empresa["Es_Periodo_Inactivo_Azucar"]
].copy()

metricas_empresa_activos = calcular_metricas_pronostico(
    evaluacion_empresa_activos,
    "Venta_Modelo",
    "Pronostico_Empresa",
)

metricas_empresa_2025_activos = calcular_metricas_pronostico(
    evaluacion_empresa_activos.loc[
        evaluacion_empresa_activos["Anio"].eq(2025)
    ],
    "Venta_Modelo",
    "Pronostico_Empresa",
)

metricas_empresa_por_anio = (
    evaluacion_empresa
    .groupby("Anio")
    .apply(
        lambda grupo: calcular_metricas_pronostico(
            grupo,
            "Venta_Modelo",
            "Pronostico_Empresa",
        ),
        include_groups=False,
    )
    .reset_index()
)

metricas_empresa_por_categoria = (
    evaluacion_empresa
    .groupby("Categoria")
    .apply(
        lambda grupo: calcular_metricas_pronostico(
            grupo,
            "Venta_Modelo",
            "Pronostico_Empresa",
        ),
        include_groups=False,
    )
    .reset_index()
    .sort_values("WAPE_pct")
)

print("\n--- DESEMPEÑO HISTÓRICO DEL PRONÓSTICO EMPRESARIAL ---")
print("Contra Venta_Real reportada:")
print(metricas_empresa_reportadas.to_string())
print("\nContra Venta_Modelo limpia:")
print(metricas_empresa_limpias.to_string())
print("\nContra Venta_Modelo excluyendo la pausa de Azúcar:")
print(metricas_empresa_activos.to_string())
print("\nAño 2025 excluyendo la pausa de Azúcar:")
print(metricas_empresa_2025_activos.to_string())
print("\nPor año contra Venta_Modelo:")
print(metricas_empresa_por_anio.to_string(index=False))
print("\nPor categoría contra Venta_Modelo:")
print(metricas_empresa_por_categoria.to_string(index=False))

# ---------------------------------------------------------------------------
# Tabla principal para pronosticar por SKU
# ---------------------------------------------------------------------------

demanda_sku = (
    ventas_modelo
    .groupby(
        [
            "Fecha",
            "SKU",
            "Producto",
            "Categoria",
        ],
        as_index=False,
    )
    .agg(Demanda=("Unidades_Modelo", "sum"))
    .sort_values(["SKU", "Fecha"])
)

print("\n--- TABLA MENSUAL PRINCIPAL POR SKU ---")
print("Filas:", len(demanda_sku))
print("Series SKU:", demanda_sku["SKU"].nunique())
print(
    "Meses por serie:",
    demanda_sku.groupby("SKU").size().value_counts(),
)
print(demanda_sku.head(10).to_string(index=False))

# ---------------------------------------------------------------------------
# Ejemplo didáctico por SKU: mismo mes del año anterior
# ---------------------------------------------------------------------------

claves_serie_sku = [
    "SKU",
    "Producto",
    "Categoria",
]

fecha_corte_sku_ejemplo = pd.Timestamp("2024-12-01")
historial_sku_prueba = demanda_sku.loc[
    demanda_sku["Fecha"].le(fecha_corte_sku_ejemplo)
].copy()

fechas_futuras_sku_ejemplo = pd.DataFrame(
    {
        "Fecha": pd.date_range(
            fecha_corte_sku_ejemplo + pd.offsets.MonthBegin(1),
            periods=6,
            freq="MS",
        )
    }
)

base_futura_sku_ejemplo = (
    demanda_sku[claves_serie_sku]
    .drop_duplicates()
    .merge(fechas_futuras_sku_ejemplo, how="cross")
)

# Para enero de 2025 buscamos enero de 2024; para febrero de 2025 buscamos
# febrero de 2024, etc. La referencia siempre debe pertenecer al historial.
base_futura_sku_ejemplo["Fecha_Referencia"] = (
    base_futura_sku_ejemplo["Fecha"] - pd.DateOffset(years=1)
)

referencia_anual_sku_ejemplo = historial_sku_prueba[
    claves_serie_sku + ["Fecha", "Demanda"]
].rename(
    columns={
        "Fecha": "Fecha_Referencia",
        "Demanda": "Pronostico_Mismo_Mes_Anterior",
    }
)

pronostico_anual_sku_ejemplo = base_futura_sku_ejemplo.merge(
    referencia_anual_sku_ejemplo,
    on=claves_serie_sku + ["Fecha_Referencia"],
    how="left",
    validate="many_to_one",
)

comparacion_anual_sku_ejemplo = pronostico_anual_sku_ejemplo.merge(
    demanda_sku[claves_serie_sku + ["Fecha", "Demanda"]],
    on=claves_serie_sku + ["Fecha"],
    how="left",
    validate="one_to_one",
)

metricas_anual_sku_ejemplo = calcular_metricas_pronostico(
    comparacion_anual_sku_ejemplo,
    "Demanda",
    "Pronostico_Mismo_Mes_Anterior",
)

empresa_semestre_sku_ejemplo = evaluacion_empresa.loc[
    evaluacion_empresa["Fecha"].between("2025-01-01", "2025-06-01")
].copy()
metricas_empresa_semestre_sku_ejemplo = calcular_metricas_pronostico(
    empresa_semestre_sku_ejemplo,
    "Venta_Modelo",
    "Pronostico_Empresa",
)

print("\n--- MISMO MES DEL AÑO ANTERIOR: NIVEL SKU ---")
print("Filas pronosticadas:", len(pronostico_anual_sku_ejemplo))
print(
    "Fechas de referencia posteriores al corte:",
    pronostico_anual_sku_ejemplo["Fecha_Referencia"].gt(
        fecha_corte_sku_ejemplo
    ).sum(),
)
print(
    "Modelo anual: "
    f"WAPE {metricas_anual_sku_ejemplo['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_anual_sku_ejemplo['Sesgo_pct']:.2f}%"
)
print(
    "Empresa, mismo nivel y semestre: "
    f"WAPE {metricas_empresa_semestre_sku_ejemplo['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_empresa_semestre_sku_ejemplo['Sesgo_pct']:.2f}%"
)

print("\nEjemplo SKU-1001:")
print(
    comparacion_anual_sku_ejemplo.loc[
        comparacion_anual_sku_ejemplo["SKU"].eq("SKU-1001"),
        [
            "Fecha",
            "Fecha_Referencia",
            "Pronostico_Mismo_Mes_Anterior",
            "Demanda",
        ],
    ].to_string(index=False)
)

# ---------------------------------------------------------------------------
# Ejemplo didáctico por SKU: promedio estacional
# ---------------------------------------------------------------------------

# Identificamos el mes calendario. Para pronosticar enero se promedian todos los
# eneros disponibles antes del corte; para febrero, todos los febreros, etc.
historial_estacional_sku_ejemplo = historial_sku_prueba.copy()
historial_estacional_sku_ejemplo["Mes_Calendario"] = (
    historial_estacional_sku_ejemplo["Fecha"].dt.month
)

promedio_estacional_sku_ejemplo = (
    historial_estacional_sku_ejemplo
    .groupby(
        claves_serie_sku + ["Mes_Calendario"],
        as_index=False,
    )
    .agg(Pronostico_Promedio_Estacional=("Demanda", "mean"))
)

pronostico_estacional_sku_ejemplo = base_futura_sku_ejemplo.copy()
pronostico_estacional_sku_ejemplo["Mes_Calendario"] = (
    pronostico_estacional_sku_ejemplo["Fecha"].dt.month
)
pronostico_estacional_sku_ejemplo = (
    pronostico_estacional_sku_ejemplo.merge(
        promedio_estacional_sku_ejemplo,
        on=claves_serie_sku + ["Mes_Calendario"],
        how="left",
        validate="many_to_one",
    )
)

comparacion_estacional_sku_ejemplo = (
    pronostico_estacional_sku_ejemplo.merge(
        demanda_sku[claves_serie_sku + ["Fecha", "Demanda"]],
        on=claves_serie_sku + ["Fecha"],
        how="left",
        validate="one_to_one",
    )
)

metricas_estacional_sku_ejemplo = calcular_metricas_pronostico(
    comparacion_estacional_sku_ejemplo,
    "Demanda",
    "Pronostico_Promedio_Estacional",
)

print("\n--- PROMEDIO ESTACIONAL: NIVEL SKU ---")
print("Filas pronosticadas:", len(pronostico_estacional_sku_ejemplo))
print(
    "Pronósticos vacíos:",
    pronostico_estacional_sku_ejemplo[
        "Pronostico_Promedio_Estacional"
    ].isna().sum(),
)
print(
    "Promedio estacional: "
    f"WAPE {metricas_estacional_sku_ejemplo['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_estacional_sku_ejemplo['Sesgo_pct']:.2f}%"
)
print(
    "Mismo mes anterior: "
    f"WAPE {metricas_anual_sku_ejemplo['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_anual_sku_ejemplo['Sesgo_pct']:.2f}%"
)
print(
    "Empresa: "
    f"WAPE {metricas_empresa_semestre_sku_ejemplo['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_empresa_semestre_sku_ejemplo['Sesgo_pct']:.2f}%"
)

print("\nEjemplo estacional SKU-1001:")
print(
    comparacion_estacional_sku_ejemplo.loc[
        comparacion_estacional_sku_ejemplo["SKU"].eq("SKU-1001"),
        [
            "Fecha",
            "Pronostico_Promedio_Estacional",
            "Demanda",
        ],
    ].to_string(index=False)
)

# ---------------------------------------------------------------------------
# Ejemplo didáctico por SKU: nivel reciente ponderado × estacionalidad
# ---------------------------------------------------------------------------

# A) Creamos un índice estacional. Un índice de 1.20 significa que ese mes suele
# estar 20% arriba del promedio mensual del SKU; 0.80 significa 20% abajo.
promedio_general_sku_ejemplo = (
    historial_estacional_sku_ejemplo
    .groupby(claves_serie_sku, as_index=False)
    .agg(Promedio_General=("Demanda", "mean"))
)

indices_estacionales_sku_ejemplo = (
    promedio_estacional_sku_ejemplo.merge(
        promedio_general_sku_ejemplo,
        on=claves_serie_sku,
        how="left",
        validate="many_to_one",
    )
)
indices_estacionales_sku_ejemplo["Indice_Estacional"] = (
    indices_estacionales_sku_ejemplo[
        "Pronostico_Promedio_Estacional"
    ]
    / indices_estacionales_sku_ejemplo["Promedio_General"]
)

# Tomamos los tres meses más recientes y les quitamos temporalmente su efecto
# estacional. Así octubre, noviembre y diciembre quedan en una escala comparable.
recientes_ponderados_sku_ejemplo = (
    historial_sku_prueba
    .sort_values("Fecha")
    .groupby(claves_serie_sku, group_keys=False)
    .tail(3)
    .copy()
)
recientes_ponderados_sku_ejemplo["Mes_Calendario"] = (
    recientes_ponderados_sku_ejemplo["Fecha"].dt.month
)
recientes_ponderados_sku_ejemplo = (
    recientes_ponderados_sku_ejemplo.merge(
        indices_estacionales_sku_ejemplo[
            claves_serie_sku
            + ["Mes_Calendario", "Indice_Estacional"]
        ],
        on=claves_serie_sku + ["Mes_Calendario"],
        how="left",
        validate="many_to_one",
    )
    .sort_values(claves_serie_sku + ["Fecha"])
)

recientes_ponderados_sku_ejemplo["Orden_Recencia"] = (
    recientes_ponderados_sku_ejemplo
    .groupby(claves_serie_sku)
    .cumcount()
    + 1
)
pesos_recencia_ejemplo = {
    1: 0.20,
    2: 0.30,
    3: 0.50,
}
recientes_ponderados_sku_ejemplo["Peso"] = (
    recientes_ponderados_sku_ejemplo["Orden_Recencia"].map(
        pesos_recencia_ejemplo
    )
)
recientes_ponderados_sku_ejemplo["Demanda_Sin_Estacionalidad"] = (
    recientes_ponderados_sku_ejemplo["Demanda"]
    / recientes_ponderados_sku_ejemplo["Indice_Estacional"]
)
recientes_ponderados_sku_ejemplo["Nivel_Ponderado"] = (
    recientes_ponderados_sku_ejemplo["Demanda_Sin_Estacionalidad"]
    * recientes_ponderados_sku_ejemplo["Peso"]
)

nivel_actual_sku_ejemplo = (
    recientes_ponderados_sku_ejemplo
    .groupby(claves_serie_sku, as_index=False)
    .agg(
        Nivel_Actual=("Nivel_Ponderado", "sum"),
        Suma_Pesos=("Peso", "sum"),
    )
)

# B) Aplicamos el índice de cada mes futuro al nivel actual calculado.
pronostico_ponderado_sku_ejemplo = base_futura_sku_ejemplo.copy()
pronostico_ponderado_sku_ejemplo["Mes_Calendario"] = (
    pronostico_ponderado_sku_ejemplo["Fecha"].dt.month
)
pronostico_ponderado_sku_ejemplo = (
    pronostico_ponderado_sku_ejemplo
    .merge(
        nivel_actual_sku_ejemplo,
        on=claves_serie_sku,
        how="left",
        validate="many_to_one",
    )
    .merge(
        indices_estacionales_sku_ejemplo[
            claves_serie_sku
            + ["Mes_Calendario", "Indice_Estacional"]
        ],
        on=claves_serie_sku + ["Mes_Calendario"],
        how="left",
        validate="many_to_one",
    )
)
pronostico_ponderado_sku_ejemplo["Pronostico_Ponderado_Estacional"] = (
    pronostico_ponderado_sku_ejemplo["Nivel_Actual"]
    * pronostico_ponderado_sku_ejemplo["Indice_Estacional"]
)

comparacion_ponderada_sku_ejemplo = (
    pronostico_ponderado_sku_ejemplo.merge(
        demanda_sku[claves_serie_sku + ["Fecha", "Demanda"]],
        on=claves_serie_sku + ["Fecha"],
        how="left",
        validate="one_to_one",
    )
)
metricas_ponderadas_sku_ejemplo = calcular_metricas_pronostico(
    comparacion_ponderada_sku_ejemplo,
    "Demanda",
    "Pronostico_Ponderado_Estacional",
)

print("\n--- NIVEL PONDERADO × ÍNDICE ESTACIONAL: NIVEL SKU ---")
print(
    "Suma mínima y máxima de pesos:",
    nivel_actual_sku_ejemplo["Suma_Pesos"].min(),
    nivel_actual_sku_ejemplo["Suma_Pesos"].max(),
)
print(
    "Índices no válidos:",
    indices_estacionales_sku_ejemplo["Indice_Estacional"].isna().sum()
    + indices_estacionales_sku_ejemplo["Indice_Estacional"].le(0).sum(),
)
print(
    "Modelo ponderado estacional: "
    f"WAPE {metricas_ponderadas_sku_ejemplo['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_ponderadas_sku_ejemplo['Sesgo_pct']:.2f}%"
)
print(
    "Mismo mes anterior: "
    f"WAPE {metricas_anual_sku_ejemplo['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_anual_sku_ejemplo['Sesgo_pct']:.2f}%"
)

print("\nCálculo del nivel actual de SKU-1001:")
print(
    recientes_ponderados_sku_ejemplo.loc[
        recientes_ponderados_sku_ejemplo["SKU"].eq("SKU-1001"),
        [
            "Fecha",
            "Demanda",
            "Indice_Estacional",
            "Demanda_Sin_Estacionalidad",
            "Peso",
            "Nivel_Ponderado",
        ],
    ].to_string(index=False)
)
print("\nPronóstico ponderado de SKU-1001:")
print(
    comparacion_ponderada_sku_ejemplo.loc[
        comparacion_ponderada_sku_ejemplo["SKU"].eq("SKU-1001"),
        [
            "Fecha",
            "Nivel_Actual",
            "Indice_Estacional",
            "Pronostico_Ponderado_Estacional",
            "Demanda",
        ],
    ].to_string(index=False)
)


def pronosticar_ponderado_estacional_sku(
    tabla_demanda,
    fecha_corte,
    pesos=(0.20, 0.30, 0.50),
):
    """Pronostica seis meses con nivel reciente e índices de años completos."""
    fecha_corte = pd.Timestamp(fecha_corte)
    historial = tabla_demanda.loc[
        tabla_demanda["Fecha"].le(fecha_corte)
    ].copy()

    # Si el corte no es diciembre, el año en curso está incompleto y no debe
    # utilizarse para calcular la forma estacional de los doce meses.
    ultimo_anio_completo = (
        fecha_corte.year
        if fecha_corte.month == 12
        else fecha_corte.year - 1
    )
    historial_estacional = historial.loc[
        historial["Fecha"].dt.year.le(ultimo_anio_completo)
    ].copy()
    historial_estacional["Mes_Calendario"] = (
        historial_estacional["Fecha"].dt.month
    )

    promedio_general = (
        historial_estacional
        .groupby(claves_serie_sku, as_index=False)
        .agg(Promedio_General=("Demanda", "mean"))
    )
    indices = (
        historial_estacional
        .groupby(
            claves_serie_sku + ["Mes_Calendario"],
            as_index=False,
        )
        .agg(Promedio_Mes=("Demanda", "mean"))
        .merge(
            promedio_general,
            on=claves_serie_sku,
            how="left",
            validate="many_to_one",
        )
    )
    indices["Indice_Estacional"] = (
        indices["Promedio_Mes"] / indices["Promedio_General"]
    )

    recientes = (
        historial
        .sort_values("Fecha")
        .groupby(claves_serie_sku, group_keys=False)
        .tail(len(pesos))
        .copy()
    )
    recientes["Mes_Calendario"] = recientes["Fecha"].dt.month
    recientes = (
        recientes.merge(
            indices[
                claves_serie_sku
                + ["Mes_Calendario", "Indice_Estacional"]
            ],
            on=claves_serie_sku + ["Mes_Calendario"],
            how="left",
            validate="many_to_one",
        )
        .sort_values(claves_serie_sku + ["Fecha"])
    )
    recientes["Orden_Recencia"] = (
        recientes.groupby(claves_serie_sku).cumcount()
    )
    mapa_pesos = dict(enumerate(pesos))
    recientes["Peso"] = recientes["Orden_Recencia"].map(mapa_pesos)
    recientes["Nivel_Ponderado"] = (
        recientes["Demanda"]
        / recientes["Indice_Estacional"]
        * recientes["Peso"]
    )
    nivel = (
        recientes.groupby(claves_serie_sku, as_index=False)
        .agg(
            Nivel_Actual=("Nivel_Ponderado", "sum"),
            Suma_Pesos=("Peso", "sum"),
        )
    )

    fechas_futuras = pd.DataFrame(
        {
            "Fecha": pd.date_range(
                fecha_corte + pd.offsets.MonthBegin(1),
                periods=6,
                freq="MS",
            )
        }
    )
    futuro = (
        tabla_demanda[claves_serie_sku]
        .drop_duplicates()
        .merge(fechas_futuras, how="cross")
    )
    futuro["Mes_Calendario"] = futuro["Fecha"].dt.month
    futuro = (
        futuro
        .merge(
            nivel,
            on=claves_serie_sku,
            how="left",
            validate="many_to_one",
        )
        .merge(
            indices[
                claves_serie_sku
                + ["Mes_Calendario", "Indice_Estacional"]
            ],
            on=claves_serie_sku + ["Mes_Calendario"],
            how="left",
            validate="many_to_one",
        )
    )
    futuro["Pronostico_Ponderado_Estacional"] = (
        futuro["Nivel_Actual"] * futuro["Indice_Estacional"]
    )
    return futuro


# Segunda ventana: mantenemos los pesos elegidos antes de mirar julio-diciembre.
pronostico_ponderado_sku_segunda_prueba = (
    pronosticar_ponderado_estacional_sku(
        demanda_sku,
        "2025-06-01",
        pesos=(0.20, 0.30, 0.50),
    )
)
comparacion_ponderada_sku_segunda_prueba = (
    pronostico_ponderado_sku_segunda_prueba.merge(
        demanda_sku[claves_serie_sku + ["Fecha", "Demanda"]],
        on=claves_serie_sku + ["Fecha"],
        how="left",
        validate="one_to_one",
    )
)
comparacion_ponderada_sku_segunda_prueba["Es_Pausa_Azucar"] = (
    comparacion_ponderada_sku_segunda_prueba["SKU"].eq("SKU-1021")
)

segunda_prueba_activos = comparacion_ponderada_sku_segunda_prueba.loc[
    ~comparacion_ponderada_sku_segunda_prueba["Es_Pausa_Azucar"]
].copy()
metricas_ponderadas_segunda_prueba = calcular_metricas_pronostico(
    comparacion_ponderada_sku_segunda_prueba,
    "Demanda",
    "Pronostico_Ponderado_Estacional",
)
metricas_ponderadas_segunda_activos = calcular_metricas_pronostico(
    segunda_prueba_activos,
    "Demanda",
    "Pronostico_Ponderado_Estacional",
)

# Referencia anual en el mismo segundo semestre.
pronostico_anual_segunda_prueba = demanda_sku.loc[
    demanda_sku["Fecha"].between("2024-07-01", "2024-12-01"),
    claves_serie_sku + ["Fecha", "Demanda"],
].copy()
pronostico_anual_segunda_prueba["Fecha"] = (
    pronostico_anual_segunda_prueba["Fecha"] + pd.DateOffset(years=1)
)
pronostico_anual_segunda_prueba = pronostico_anual_segunda_prueba.rename(
    columns={"Demanda": "Pronostico_Mismo_Mes_Anterior"}
)
comparacion_anual_segunda_prueba = pronostico_anual_segunda_prueba.merge(
    demanda_sku[claves_serie_sku + ["Fecha", "Demanda"]],
    on=claves_serie_sku + ["Fecha"],
    how="left",
    validate="one_to_one",
)
comparacion_anual_segunda_activos = comparacion_anual_segunda_prueba.loc[
    ~comparacion_anual_segunda_prueba["SKU"].eq("SKU-1021")
].copy()
metricas_anual_segunda_activos = calcular_metricas_pronostico(
    comparacion_anual_segunda_activos,
    "Demanda",
    "Pronostico_Mismo_Mes_Anterior",
)

# Unimos ambas ventanas activas para ver el desempeño anual completo.
ponderado_primera_para_total = comparacion_ponderada_sku_ejemplo[
    ["Fecha", "SKU", "Demanda", "Pronostico_Ponderado_Estacional"]
]
ponderado_segunda_para_total = segunda_prueba_activos[
    ["Fecha", "SKU", "Demanda", "Pronostico_Ponderado_Estacional"]
]
ponderado_total_2025 = pd.concat(
    [ponderado_primera_para_total, ponderado_segunda_para_total],
    ignore_index=True,
)
metricas_ponderadas_total_2025 = calcular_metricas_pronostico(
    ponderado_total_2025,
    "Demanda",
    "Pronostico_Ponderado_Estacional",
)

anual_primera_para_total = comparacion_anual_sku_ejemplo[
    ["Fecha", "SKU", "Demanda", "Pronostico_Mismo_Mes_Anterior"]
]
anual_segunda_para_total = comparacion_anual_segunda_activos[
    ["Fecha", "SKU", "Demanda", "Pronostico_Mismo_Mes_Anterior"]
]
anual_total_2025 = pd.concat(
    [anual_primera_para_total, anual_segunda_para_total],
    ignore_index=True,
)
metricas_anual_total_2025 = calcular_metricas_pronostico(
    anual_total_2025,
    "Demanda",
    "Pronostico_Mismo_Mes_Anterior",
)

print("\n--- VALIDACIÓN JULIO-DICIEMBRE 2025: PESOS FIJOS ---")
print(
    "Ponderado, incluyendo Azúcar pausada: "
    f"WAPE {metricas_ponderadas_segunda_prueba['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_ponderadas_segunda_prueba['Sesgo_pct']:.2f}%"
)
print(
    "Ponderado, solamente SKU activos: "
    f"WAPE {metricas_ponderadas_segunda_activos['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_ponderadas_segunda_activos['Sesgo_pct']:.2f}%"
)
print(
    "Mismo mes anterior, solamente SKU activos: "
    f"WAPE {metricas_anual_segunda_activos['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_anual_segunda_activos['Sesgo_pct']:.2f}%"
)
print("\n--- RESULTADO CONJUNTO DE LAS DOS VENTANAS ACTIVAS ---")
print(
    "Ponderado estacional: "
    f"WAPE {metricas_ponderadas_total_2025['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_ponderadas_total_2025['Sesgo_pct']:.2f}%"
)
print(
    "Mismo mes anterior: "
    f"WAPE {metricas_anual_total_2025['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_anual_total_2025['Sesgo_pct']:.2f}%"
)

# ---------------------------------------------------------------------------
# Promociones separadas y experimento controlado de pesos
# ---------------------------------------------------------------------------


def calcular_metricas_riesgo(tabla, columna_real, columna_pronostico):
    """Separa el error que queda corto del error que pronostica de más."""
    metricas = calcular_metricas_pronostico(
        tabla,
        columna_real,
        columna_pronostico,
    )
    real = tabla[columna_real]
    pronostico = tabla[columna_pronostico]
    faltante = (real - pronostico).clip(lower=0).sum()
    excedente = (pronostico - real).clip(lower=0).sum()
    metricas["Subestimacion_pct"] = faltante / real.sum() * 100
    metricas["Sobreestimacion_pct"] = excedente / real.sum() * 100
    return metricas


# Los factores se entrenaron previamente con promociones de 2023-2024 y se
# validaron en 2025. Dividimos las ventas promocionales entre el factor del SKU
# para aproximar cuál habría sido su demanda base sin campaña.
ventas_base_sin_promocion = ventas_modelo.copy()
ventas_base_sin_promocion["Factor_Promocional_Modelo"] = (
    ventas_base_sin_promocion["SKU"]
    .map(factor_promocional_por_sku)
    .fillna(factor_promocional_global)
)
ventas_base_sin_promocion["Unidades_Base_Sin_Promocion"] = (
    ventas_base_sin_promocion["Unidades_Modelo"].where(
        ventas_base_sin_promocion["Promocion"].eq(0),
        ventas_base_sin_promocion["Unidades_Modelo"]
        / ventas_base_sin_promocion["Factor_Promocional_Modelo"],
    )
)

demanda_sku_base_sin_promocion = (
    ventas_base_sin_promocion
    .groupby(["Fecha"] + claves_serie_sku, as_index=False)
    .agg(Demanda=("Unidades_Base_Sin_Promocion", "sum"))
)

# Proporción de las nueve combinaciones canal-región marcadas en promoción. Es
# una aproximación transparente porque no conocemos intensidad ni duración.
calendario_promocional_sku = (
    ventas_base_sin_promocion
    .groupby(["Fecha", "SKU"], as_index=False)
    .agg(Proporcion_Promocion=("Promocion", "mean"))
)


def evaluar_pesos_con_promocion(fecha_corte, pesos, excluir_pausa=True):
    """Evalúa una combinación suponiendo conocido el calendario promocional."""
    pronostico_base = pronosticar_ponderado_estacional_sku(
        demanda_sku_base_sin_promocion,
        fecha_corte,
        pesos=pesos,
    )
    evaluacion = (
        pronostico_base
        .merge(
            calendario_promocional_sku,
            on=["Fecha", "SKU"],
            how="left",
            validate="many_to_one",
        )
        .merge(
            demanda_sku[claves_serie_sku + ["Fecha", "Demanda"]],
            on=claves_serie_sku + ["Fecha"],
            how="left",
            validate="one_to_one",
        )
    )
    evaluacion["Factor_Promocional_Modelo"] = (
        evaluacion["SKU"]
        .map(factor_promocional_por_sku)
        .fillna(factor_promocional_global)
    )
    evaluacion["Multiplicador_Promocional"] = (
        1
        + evaluacion["Proporcion_Promocion"].fillna(0)
        * (evaluacion["Factor_Promocional_Modelo"] - 1)
    )
    evaluacion["Pronostico_Con_Promocion"] = (
        evaluacion["Pronostico_Ponderado_Estacional"]
        * evaluacion["Multiplicador_Promocional"]
    )

    if excluir_pausa:
        evaluacion = evaluacion.loc[
            ~(
                evaluacion["SKU"].eq("SKU-1021")
                & evaluacion["Fecha"].ge("2025-07-01")
            )
        ].copy()

    metricas = calcular_metricas_riesgo(
        evaluacion,
        "Demanda",
        "Pronostico_Con_Promocion",
    )
    return evaluacion, metricas


# Generamos pesos en pasos de 10%, exigiendo que los meses recientes no reciban
# menos importancia que los antiguos. También añadimos el promedio igualitario.
combinaciones_pesos = []
for peso_antiguo_entero in range(11):
    for peso_intermedio_entero in range(11 - peso_antiguo_entero):
        peso_reciente_entero = (
            10 - peso_antiguo_entero - peso_intermedio_entero
        )
        pesos = (
            peso_antiguo_entero / 10,
            peso_intermedio_entero / 10,
            peso_reciente_entero / 10,
        )
        if pesos[0] <= pesos[1] <= pesos[2]:
            combinaciones_pesos.append(pesos)

combinaciones_pesos.append((1 / 3, 1 / 3, 1 / 3))
combinaciones_pesos = list(dict.fromkeys(combinaciones_pesos))

resultados_pesos_primera_ventana = []
for pesos in combinaciones_pesos:
    _, metricas = evaluar_pesos_con_promocion(
        "2024-12-01",
        pesos,
    )
    resultados_pesos_primera_ventana.append(
        {
            "Peso_Antiguo": pesos[0],
            "Peso_Intermedio": pesos[1],
            "Peso_Reciente": pesos[2],
            "WAPE_pct": metricas["WAPE_pct"],
            "Sesgo_pct": metricas["Sesgo_pct"],
            "Subestimacion_pct": metricas["Subestimacion_pct"],
            "Sobreestimacion_pct": metricas["Sobreestimacion_pct"],
        }
    )

resultados_pesos_primera_ventana = pd.DataFrame(
    resultados_pesos_primera_ventana
).sort_values("WAPE_pct")

mejor_wape_pesos = resultados_pesos_primera_ventana["WAPE_pct"].min()
alternativas_riesgo_pesos = resultados_pesos_primera_ventana.loc[
    resultados_pesos_primera_ventana["WAPE_pct"].le(
        mejor_wape_pesos + 0.50
    )
].copy()

# Dentro de una tolerancia pequeña de precisión, elegimos primero el que menos
# demanda deja por debajo y usamos WAPE como desempate.
ganador_pesos = alternativas_riesgo_pesos.sort_values(
    ["Subestimacion_pct", "WAPE_pct"]
).iloc[0]
pesos_seleccionados = (
    ganador_pesos["Peso_Antiguo"],
    ganador_pesos["Peso_Intermedio"],
    ganador_pesos["Peso_Reciente"],
)

evaluacion_pesos_primera, metricas_pesos_primera = (
    evaluar_pesos_con_promocion(
        "2024-12-01",
        pesos_seleccionados,
    )
)
evaluacion_pesos_segunda, metricas_pesos_segunda = (
    evaluar_pesos_con_promocion(
        "2025-06-01",
        pesos_seleccionados,
    )
)
evaluacion_pesos_total = pd.concat(
    [evaluacion_pesos_primera, evaluacion_pesos_segunda],
    ignore_index=True,
)
metricas_pesos_total = calcular_metricas_riesgo(
    evaluacion_pesos_total,
    "Demanda",
    "Pronostico_Con_Promocion",
)

# Comparadores anuales en el mismo alcance activo.
metricas_anual_total_riesgo = calcular_metricas_riesgo(
    anual_total_2025,
    "Demanda",
    "Pronostico_Mismo_Mes_Anterior",
)
empresa_2025_activa_riesgo = evaluacion_empresa.loc[
    evaluacion_empresa["Fecha"].dt.year.eq(2025)
    & ~evaluacion_empresa["Es_Periodo_Inactivo_Azucar"]
].copy()
metricas_empresa_2025_riesgo = calcular_metricas_riesgo(
    empresa_2025_activa_riesgo,
    "Venta_Modelo",
    "Pronostico_Empresa",
)

print("\n--- AUDITORÍA DE PROMOCIONES EN MESES RECIENTES ---")
for nombre, inicio, fin in [
    ("Octubre-diciembre 2024", "2024-10-01", "2024-12-01"),
    ("Abril-junio 2025", "2025-04-01", "2025-06-01"),
]:
    bloque = ventas_base_sin_promocion.loc[
        ventas_base_sin_promocion["Fecha"].between(inicio, fin)
    ]
    print(
        nombre,
        "- filas promocionales:",
        int(bloque["Promocion"].sum()),
        "- SKU con promoción:",
        bloque.loc[bloque["Promocion"].eq(1), "SKU"].nunique(),
    )

print("\n--- MEJORES PESOS EN ENERO-JUNIO 2025 ---")
print(
    resultados_pesos_primera_ventana.head(10).to_string(
        index=False
    )
)
print("\nPesos seleccionados por precisión y menor subestimación:")
print(
    f"Antiguo {pesos_seleccionados[0]:.0%}, "
    f"intermedio {pesos_seleccionados[1]:.0%}, "
    f"reciente {pesos_seleccionados[2]:.0%}"
)

print("\n--- VALIDACIÓN DE PESOS Y PROMOCIONES ---")
print(
    "Primera ventana: "
    f"WAPE {metricas_pesos_primera['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_pesos_primera['Sesgo_pct']:.2f}%, "
    f"subestimación {metricas_pesos_primera['Subestimacion_pct']:.2f}%"
)
print(
    "Segunda ventana: "
    f"WAPE {metricas_pesos_segunda['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_pesos_segunda['Sesgo_pct']:.2f}%, "
    f"subestimación {metricas_pesos_segunda['Subestimacion_pct']:.2f}%"
)
print(
    "Ambas ventanas: "
    f"WAPE {metricas_pesos_total['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_pesos_total['Sesgo_pct']:.2f}%, "
    f"subestimación {metricas_pesos_total['Subestimacion_pct']:.2f}%, "
    f"sobreestimación {metricas_pesos_total['Sobreestimacion_pct']:.2f}%"
)
print(
    "Mismo mes anterior: "
    f"WAPE {metricas_anual_total_riesgo['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_anual_total_riesgo['Sesgo_pct']:.2f}%, "
    f"subestimación {metricas_anual_total_riesgo['Subestimacion_pct']:.2f}%"
)
print(
    "Empresa 2025: "
    f"WAPE {metricas_empresa_2025_riesgo['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_empresa_2025_riesgo['Sesgo_pct']:.2f}%, "
    f"subestimación {metricas_empresa_2025_riesgo['Subestimacion_pct']:.2f}%"
)
print(
    "Nota: el resultado promocional supone que se informa de antemano "
    "qué combinaciones estarán en promoción."
)


def evaluar_promocion_recurrente(fecha_corte, pesos):
    """Prueba la recurrencia usando sólo promociones conocidas al corte."""
    fecha_corte = pd.Timestamp(fecha_corte)
    historial_promocional = ventas_base_sin_promocion.loc[
        ventas_base_sin_promocion["Fecha"].le(fecha_corte)
    ].copy()
    historial_promocional["Mes_Calendario"] = (
        historial_promocional["Fecha"].dt.month
    )
    historial_promocional["Anio"] = (
        historial_promocional["Fecha"].dt.year
    )

    anios_promocion = (
        historial_promocional.loc[
            historial_promocional["Promocion"].eq(1)
        ]
        .groupby(["SKU", "Mes_Calendario"], as_index=False)
        .agg(Anios_Con_Promocion=("Anio", "nunique"))
    )
    proporcion_historica = (
        historial_promocional
        .groupby(["SKU", "Mes_Calendario"], as_index=False)
        .agg(Proporcion_Historica=("Promocion", "mean"))
        .merge(
            anios_promocion,
            on=["SKU", "Mes_Calendario"],
            how="left",
            validate="one_to_one",
        )
    )
    proporcion_historica["Anios_Con_Promocion"] = (
        proporcion_historica["Anios_Con_Promocion"].fillna(0)
    )
    proporcion_historica["Proporcion_Esperada"] = (
        proporcion_historica["Proporcion_Historica"].where(
            proporcion_historica["Anios_Con_Promocion"].ge(2),
            0.0,
        )
    )

    pronostico = pronosticar_ponderado_estacional_sku(
        demanda_sku_base_sin_promocion,
        fecha_corte,
        pesos=pesos,
    )
    evaluacion = (
        pronostico
        .merge(
            proporcion_historica[
                ["SKU", "Mes_Calendario", "Proporcion_Esperada"]
            ],
            on=["SKU", "Mes_Calendario"],
            how="left",
            validate="many_to_one",
        )
        .merge(
            demanda_sku[claves_serie_sku + ["Fecha", "Demanda"]],
            on=claves_serie_sku + ["Fecha"],
            how="left",
            validate="one_to_one",
        )
    )
    evaluacion["Factor_Promocional_Modelo"] = (
        evaluacion["SKU"]
        .map(factor_promocional_por_sku)
        .fillna(factor_promocional_global)
    )
    evaluacion["Pronostico_Recurrente"] = (
        evaluacion["Pronostico_Ponderado_Estacional"]
        * (
            1
            + evaluacion["Proporcion_Esperada"]
            * (evaluacion["Factor_Promocional_Modelo"] - 1)
        )
    )
    evaluacion = evaluacion.loc[
        ~(
            evaluacion["SKU"].eq("SKU-1021")
            & evaluacion["Fecha"].ge("2025-07-01")
        )
    ].copy()
    metricas = calcular_metricas_riesgo(
        evaluacion,
        "Demanda",
        "Pronostico_Recurrente",
    )
    return evaluacion, metricas


recurrencia_primera, metricas_recurrencia_primera = (
    evaluar_promocion_recurrente(
        "2024-12-01",
        pesos_seleccionados,
    )
)
recurrencia_segunda, metricas_recurrencia_segunda = (
    evaluar_promocion_recurrente(
        "2025-06-01",
        pesos_seleccionados,
    )
)
recurrencia_total_2025 = pd.concat(
    [recurrencia_primera, recurrencia_segunda],
    ignore_index=True,
)
metricas_recurrencia_total = calcular_metricas_riesgo(
    recurrencia_total_2025,
    "Demanda",
    "Pronostico_Recurrente",
)

print("\n--- VALIDACIÓN REALISTA DE PROMOCIÓN RECURRENTE ---")
print(
    "Primera ventana: "
    f"WAPE {metricas_recurrencia_primera['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_recurrencia_primera['Sesgo_pct']:.2f}%"
)
print(
    "Segunda ventana: "
    f"WAPE {metricas_recurrencia_segunda['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_recurrencia_segunda['Sesgo_pct']:.2f}%"
)
print(
    "Ambas ventanas: "
    f"WAPE {metricas_recurrencia_total['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_recurrencia_total['Sesgo_pct']:.2f}%, "
    f"subestimación {metricas_recurrencia_total['Subestimacion_pct']:.2f}%, "
    f"sobreestimación {metricas_recurrencia_total['Sobreestimacion_pct']:.2f}%"
)
print(
    "Esta métrica sí corresponde a inferir promociones sin conocer el "
    "calendario real futuro."
)

# ---------------------------------------------------------------------------
# Escenario de protección contra el sesgo negativo
# ---------------------------------------------------------------------------

# Elegimos el porcentaje únicamente con la primera ventana. Después lo dejamos
# fijo y lo probamos en la segunda; así evitamos escogerlo viendo el futuro.
porcentajes_proteccion = [0.00, 0.02, 0.04, 0.06, 0.08, 0.10]
resultados_proteccion_primera = []

for porcentaje in porcentajes_proteccion:
    prueba = recurrencia_primera.copy()
    prueba["Pronostico_Protegido"] = (
        prueba["Pronostico_Recurrente"] * (1 + porcentaje)
    )
    metricas = calcular_metricas_riesgo(
        prueba,
        "Demanda",
        "Pronostico_Protegido",
    )
    resultados_proteccion_primera.append(
        {
            "Proteccion_pct": porcentaje * 100,
            "WAPE_pct": metricas["WAPE_pct"],
            "Sesgo_pct": metricas["Sesgo_pct"],
            "Subestimacion_pct": metricas["Subestimacion_pct"],
            "Sobreestimacion_pct": metricas["Sobreestimacion_pct"],
        }
    )

resultados_proteccion_primera = pd.DataFrame(
    resultados_proteccion_primera
)
resultados_proteccion_primera["Sesgo_Absoluto_pct"] = (
    resultados_proteccion_primera["Sesgo_pct"].abs()
)

# El objetivo específico de esta prueba es corregir el sesgo. WAPE se utiliza
# como desempate si dos porcentajes dejan el sesgo igual de cerca de cero.
ganador_proteccion = resultados_proteccion_primera.sort_values(
    ["Sesgo_Absoluto_pct", "WAPE_pct"]
).iloc[0]
proteccion_seleccionada = ganador_proteccion["Proteccion_pct"] / 100


def aplicar_y_evaluar_proteccion(tabla, porcentaje):
    """Aplica un colchón visible y devuelve las métricas correspondientes."""
    evaluacion = tabla.copy()
    evaluacion["Pronostico_Protegido"] = (
        evaluacion["Pronostico_Recurrente"] * (1 + porcentaje)
    )
    metricas = calcular_metricas_riesgo(
        evaluacion,
        "Demanda",
        "Pronostico_Protegido",
    )
    return evaluacion, metricas


proteccion_primera, metricas_proteccion_primera = (
    aplicar_y_evaluar_proteccion(
        recurrencia_primera,
        proteccion_seleccionada,
    )
)
proteccion_segunda, metricas_proteccion_segunda = (
    aplicar_y_evaluar_proteccion(
        recurrencia_segunda,
        proteccion_seleccionada,
    )
)
proteccion_total_2025 = pd.concat(
    [proteccion_primera, proteccion_segunda],
    ignore_index=True,
)
metricas_proteccion_total = calcular_metricas_riesgo(
    proteccion_total_2025,
    "Demanda",
    "Pronostico_Protegido",
)

print("\n--- PRUEBA DE PROTECCIÓN CONTRA SUBESTIMACIÓN ---")
print(resultados_proteccion_primera.to_string(index=False))
print(
    "Protección seleccionada con la primera ventana:",
    f"{proteccion_seleccionada:.0%}",
)
print(
    "Primera ventana protegida: "
    f"WAPE {metricas_proteccion_primera['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_proteccion_primera['Sesgo_pct']:.2f}%, "
    f"subestimación "
    f"{metricas_proteccion_primera['Subestimacion_pct']:.2f}%, "
    f"sobreestimación "
    f"{metricas_proteccion_primera['Sobreestimacion_pct']:.2f}%"
)
print(
    "Segunda ventana protegida: "
    f"WAPE {metricas_proteccion_segunda['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_proteccion_segunda['Sesgo_pct']:.2f}%, "
    f"subestimación "
    f"{metricas_proteccion_segunda['Subestimacion_pct']:.2f}%, "
    f"sobreestimación "
    f"{metricas_proteccion_segunda['Sobreestimacion_pct']:.2f}%"
)
print(
    "Ambas ventanas protegidas: "
    f"WAPE {metricas_proteccion_total['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_proteccion_total['Sesgo_pct']:.2f}%, "
    f"subestimación "
    f"{metricas_proteccion_total['Subestimacion_pct']:.2f}%, "
    f"sobreestimación "
    f"{metricas_proteccion_total['Sobreestimacion_pct']:.2f}%"
)


def resumir_robustez_segmento(tabla, columnas_grupo):
    """Compara recomendado y protegido dentro de cada segmento."""
    filas = []
    for valores, bloque in tabla.groupby(columnas_grupo, dropna=False):
        if not isinstance(valores, tuple):
            valores = (valores,)
        recomendado = calcular_metricas_riesgo(
            bloque,
            "Demanda",
            "Pronostico_Recurrente",
        )
        protegido = calcular_metricas_riesgo(
            bloque,
            "Demanda",
            "Pronostico_Protegido",
        )
        fila = dict(zip(columnas_grupo, valores))
        fila.update(
            {
                "Observaciones": len(bloque),
                "Demanda_Real": bloque["Demanda"].sum(),
                "WAPE_Recomendado_pct": recomendado["WAPE_pct"],
                "Sesgo_Recomendado_pct": recomendado["Sesgo_pct"],
                "Subestimacion_Recomendado_pct": recomendado[
                    "Subestimacion_pct"
                ],
                "Sobreestimacion_Recomendado_pct": recomendado[
                    "Sobreestimacion_pct"
                ],
                "WAPE_Protegido_pct": protegido["WAPE_pct"],
                "Sesgo_Protegido_pct": protegido["Sesgo_pct"],
                "Subestimacion_Protegido_pct": protegido[
                    "Subestimacion_pct"
                ],
                "Sobreestimacion_Protegido_pct": protegido[
                    "Sobreestimacion_pct"
                ],
            }
        )
        filas.append(fila)

    resultado = pd.DataFrame(filas)
    resultado["Cambio_WAPE_pct"] = (
        resultado["WAPE_Protegido_pct"]
        - resultado["WAPE_Recomendado_pct"]
    )
    resultado["Cambio_Subestimacion_pct"] = (
        resultado["Subestimacion_Protegido_pct"]
        - resultado["Subestimacion_Recomendado_pct"]
    )
    resultado["Proteccion_Mejora_WAPE"] = (
        resultado["Cambio_WAPE_pct"].lt(0)
    )
    resultado["Proteccion_Reduce_Subestimacion"] = (
        resultado["Cambio_Subestimacion_pct"].lt(0)
    )
    return resultado


robustez_sku_2025 = resumir_robustez_segmento(
    proteccion_total_2025,
    ["SKU", "Producto", "Categoria"],
).sort_values("WAPE_Protegido_pct", ascending=False)

robustez_categoria_2025 = resumir_robustez_segmento(
    proteccion_total_2025,
    ["Categoria"],
).sort_values("WAPE_Protegido_pct", ascending=False)

proteccion_total_2025["Mes_Calendario"] = (
    proteccion_total_2025["Fecha"].dt.month
)
robustez_mes_2025 = resumir_robustez_segmento(
    proteccion_total_2025,
    ["Mes_Calendario"],
).sort_values("Mes_Calendario")

print("\n--- ROBUSTEZ DEL ESCENARIO PROTEGIDO POR SEGMENTO ---")
print(
    "SKU donde mejora WAPE:",
    int(robustez_sku_2025["Proteccion_Mejora_WAPE"].sum()),
    "de",
    len(robustez_sku_2025),
)
print(
    "SKU donde reduce subestimación:",
    int(
        robustez_sku_2025[
            "Proteccion_Reduce_Subestimacion"
        ].sum()
    ),
    "de",
    len(robustez_sku_2025),
)
print("\nResultado por categoría:")
print(robustez_categoria_2025.to_string(index=False))
print("\nCinco SKU con mayor WAPE protegido:")
print(
    robustez_sku_2025[
        [
            "SKU",
            "Producto",
            "Categoria",
            "WAPE_Recomendado_pct",
            "WAPE_Protegido_pct",
            "Cambio_WAPE_pct",
            "Sesgo_Protegido_pct",
        ]
    ].head(5).to_string(index=False)
)

# Detalle fila por fila para explicar cuánto proyectó cada modelo y cuánto se
# equivocó en cada SKU-mes de las dos ventanas de 2025.
detalle_validacion_2025 = (
    proteccion_total_2025[
        [
            "Fecha",
            "SKU",
            "Producto",
            "Categoria",
            "Demanda",
            "Proporcion_Esperada",
            "Pronostico_Recurrente",
            "Pronostico_Protegido",
        ]
    ]
    .rename(
        columns={
            "Demanda": "Venta_Real",
            "Proporcion_Esperada": "Proporcion_Promocion_Esperada",
            "Pronostico_Recurrente": "Pronostico_Recomendado",
        }
    )
    .merge(
        anual_total_2025[
            ["Fecha", "SKU", "Pronostico_Mismo_Mes_Anterior"]
        ],
        on=["Fecha", "SKU"],
        how="left",
        validate="one_to_one",
    )
    .merge(
        ponderado_total_2025[
            ["Fecha", "SKU", "Pronostico_Ponderado_Estacional"]
        ],
        on=["Fecha", "SKU"],
        how="left",
        validate="one_to_one",
    )
    .merge(
        empresa_2025_activa_riesgo[
            ["Fecha", "SKU", "Pronostico_Empresa"]
        ],
        on=["Fecha", "SKU"],
        how="left",
        validate="one_to_one",
    )
)

modelos_detalle_2025 = {
    "Empresa": "Pronostico_Empresa",
    "Mismo_Mes_Anterior": "Pronostico_Mismo_Mes_Anterior",
    "Ponderado_Estacional": "Pronostico_Ponderado_Estacional",
    "Recomendado": "Pronostico_Recomendado",
    "Protegido": "Pronostico_Protegido",
}
for nombre, columna in modelos_detalle_2025.items():
    error = detalle_validacion_2025[columna] - detalle_validacion_2025[
        "Venta_Real"
    ]
    detalle_validacion_2025[f"Error_{nombre}"] = error
    detalle_validacion_2025[f"Error_Abs_{nombre}"] = error.abs()
    detalle_validacion_2025[f"Error_pct_{nombre}"] = (
        error
        / detalle_validacion_2025["Venta_Real"].replace(0, pd.NA)
        * 100
    )

detalle_validacion_2025 = detalle_validacion_2025.sort_values(
    ["Fecha", "Categoria", "SKU"]
)

# ---------------------------------------------------------------------------
# Pronóstico revisado enero-junio 2026 por SKU
# ---------------------------------------------------------------------------

# Generamos primero la demanda orgánica, sin promociones futuras explícitas.
pronostico_sku_2026_revisado = pronosticar_ponderado_estacional_sku(
    demanda_sku_base_sin_promocion,
    "2025-12-01",
    pesos=pesos_seleccionados,
)
pronostico_sku_2026_revisado = pronostico_sku_2026_revisado.rename(
    columns={
        "Pronostico_Ponderado_Estacional": (
            "Pronostico_Modelo_Sin_Promocion"
        )
    }
)

# Una promoción es recurrente si apareció para el mismo SKU y mes calendario
# en por lo menos dos años distintos. La proporción histórica considera todas
# las combinaciones canal-región observadas en los tres años.
historial_promociones_recurrentes = ventas_base_sin_promocion.copy()
historial_promociones_recurrentes["Mes_Calendario"] = (
    historial_promociones_recurrentes["Fecha"].dt.month
)
historial_promociones_recurrentes["Anio"] = (
    historial_promociones_recurrentes["Fecha"].dt.year
)

anios_con_promocion = (
    historial_promociones_recurrentes.loc[
        historial_promociones_recurrentes["Promocion"].eq(1)
    ]
    .groupby(["SKU", "Mes_Calendario"], as_index=False)
    .agg(Anios_Con_Promocion=("Anio", "nunique"))
)
proporcion_promocional_historica = (
    historial_promociones_recurrentes
    .groupby(["SKU", "Mes_Calendario"], as_index=False)
    .agg(Proporcion_Promocion_Historica=("Promocion", "mean"))
)
recurrencia_promocional = proporcion_promocional_historica.merge(
    anios_con_promocion,
    on=["SKU", "Mes_Calendario"],
    how="left",
    validate="one_to_one",
)
recurrencia_promocional["Anios_Con_Promocion"] = (
    recurrencia_promocional["Anios_Con_Promocion"].fillna(0).astype(int)
)
recurrencia_promocional["Promocion_Recurrente"] = (
    recurrencia_promocional["Anios_Con_Promocion"].ge(2)
)
recurrencia_promocional["Proporcion_Promocion_Esperada"] = (
    recurrencia_promocional["Proporcion_Promocion_Historica"].where(
        recurrencia_promocional["Promocion_Recurrente"],
        0.0,
    )
)

pronostico_sku_2026_revisado = pronostico_sku_2026_revisado.merge(
    recurrencia_promocional,
    on=["SKU", "Mes_Calendario"],
    how="left",
    validate="many_to_one",
)
pronostico_sku_2026_revisado["Factor_Promocional_SKU"] = (
    pronostico_sku_2026_revisado["SKU"]
    .map(factor_promocional_por_sku)
    .fillna(factor_promocional_global)
)
pronostico_sku_2026_revisado["Multiplicador_Promo_Recurrente"] = (
    1
    + pronostico_sku_2026_revisado[
        "Proporcion_Promocion_Esperada"
    ]
    * (
        pronostico_sku_2026_revisado["Factor_Promocional_SKU"]
        - 1
    )
)
pronostico_sku_2026_revisado["Pronostico_Promo_Recurrente"] = (
    pronostico_sku_2026_revisado[
        "Pronostico_Modelo_Sin_Promocion"
    ]
    * pronostico_sku_2026_revisado[
        "Multiplicador_Promo_Recurrente"
    ]
)

# La pausa observada tiene prioridad sobre patrones históricos. Conservamos el
# cálculo previo a la regla para auditoría y luego fijamos ambos escenarios en 0.
pronostico_sku_2026_revisado["Estado_SKU"] = "Activo"
pronostico_sku_2026_revisado["Regla_Pausa_Aplicada"] = False
pausa_azucar_2026 = pronostico_sku_2026_revisado["SKU"].eq("SKU-1021")
pronostico_sku_2026_revisado.loc[
    pausa_azucar_2026,
    "Estado_SKU",
] = "Pausado"
pronostico_sku_2026_revisado.loc[
    pausa_azucar_2026,
    "Regla_Pausa_Aplicada",
] = True
pronostico_sku_2026_revisado.loc[
    pausa_azucar_2026,
    "Proporcion_Promocion_Esperada",
] = 0.0
pronostico_sku_2026_revisado.loc[
    pausa_azucar_2026,
    "Multiplicador_Promo_Recurrente",
] = 1.0
pronostico_sku_2026_revisado.loc[
    pausa_azucar_2026,
    [
        "Pronostico_Modelo_Sin_Promocion",
        "Pronostico_Promo_Recurrente",
    ],
] = 0.0

# El recomendado adopta la hipótesis solicitada: promoción sólo cuando existe
# recurrencia histórica. Los ajustes permiten modificarla en vivo sin alterar la
# base ni el historial.
pronostico_sku_2026_revisado["Pronostico_Recomendado"] = (
    pronostico_sku_2026_revisado["Pronostico_Promo_Recurrente"]
)
pronostico_sku_2026_revisado["Proteccion_Sesgo_pct"] = (
    proteccion_seleccionada
)
pronostico_sku_2026_revisado["Pronostico_Protegido"] = (
    pronostico_sku_2026_revisado["Pronostico_Recomendado"]
    * (1 + pronostico_sku_2026_revisado["Proteccion_Sesgo_pct"])
)
pronostico_sku_2026_revisado["Ajuste_Manual_pct"] = 0.0
pronostico_sku_2026_revisado["Ajuste_Manual_Unidades"] = 0.0
pronostico_sku_2026_revisado["Pronostico_Final"] = (
    pronostico_sku_2026_revisado["Pronostico_Recomendado"]
    * (
        1
        + pronostico_sku_2026_revisado["Ajuste_Manual_pct"]
    )
    + pronostico_sku_2026_revisado["Ajuste_Manual_Unidades"]
).clip(lower=0)

# Distribución regional: participación histórica del mismo SKU y mes. Al usar
# una participación, las tres regiones deben regresar exactamente al total SKU.
historico_region_reparto = (
    ventas_modelo
    .groupby(
        [
            "Fecha",
            "SKU",
            "Producto",
            "Categoria",
            "Region",
        ],
        as_index=False,
    )
    .agg(Demanda_Region=("Unidades_Modelo", "sum"))
)
historico_region_reparto["Mes_Calendario"] = (
    historico_region_reparto["Fecha"].dt.month
)
participaciones_region = (
    historico_region_reparto
    .groupby(
        claves_serie_sku + ["Region", "Mes_Calendario"],
        as_index=False,
    )
    .agg(Demanda_Region_Historica=("Demanda_Region", "sum"))
)
participaciones_region["Demanda_SKU_Mes_Historica"] = (
    participaciones_region
    .groupby(claves_serie_sku + ["Mes_Calendario"])[
        "Demanda_Region_Historica"
    ]
    .transform("sum")
)
participaciones_region["Participacion_Region"] = (
    participaciones_region["Demanda_Region_Historica"]
    / participaciones_region["Demanda_SKU_Mes_Historica"]
)

pronostico_region_2026_revisado = (
    pronostico_sku_2026_revisado.merge(
        participaciones_region[
            claves_serie_sku
            + ["Mes_Calendario", "Region", "Participacion_Region"]
        ],
        on=claves_serie_sku + ["Mes_Calendario"],
        how="left",
        validate="one_to_many",
    )
)
for columna_origen, columna_region in [
    ("Pronostico_Modelo_Sin_Promocion", "Pronostico_Base_Region"),
    ("Pronostico_Recomendado", "Pronostico_Recomendado_Region"),
    ("Pronostico_Protegido", "Pronostico_Protegido_Region"),
    ("Pronostico_Final", "Pronostico_Final_Region"),
]:
    pronostico_region_2026_revisado[columna_region] = (
        pronostico_region_2026_revisado[columna_origen]
        * pronostico_region_2026_revisado["Participacion_Region"]
    )

validacion_region_2026 = (
    pronostico_region_2026_revisado
    .groupby(["Fecha", "SKU"], as_index=False)
    .agg(
        Total_Regiones=("Pronostico_Final_Region", "sum"),
        Total_SKU=("Pronostico_Final", "first"),
        Suma_Participaciones=("Participacion_Region", "sum"),
    )
)
validacion_region_2026["Diferencia"] = (
    validacion_region_2026["Total_Regiones"]
    - validacion_region_2026["Total_SKU"]
)

# Desglose operativo adicional para permitir filtros y ajustes por canal. El
# modelo principal continúa en SKU-mes; aquí sólo repartimos cada total entre
# las nueve combinaciones Canal + Región usando la participación histórica del
# mismo SKU y mes calendario.
historico_canal_region_reparto = (
    ventas_modelo
    .groupby(
        [
            "Fecha",
            "SKU",
            "Producto",
            "Categoria",
            "Canal",
            "Region",
        ],
        as_index=False,
    )
    .agg(Demanda_Canal_Region=("Unidades_Modelo", "sum"))
)
historico_canal_region_reparto["Mes_Calendario"] = (
    historico_canal_region_reparto["Fecha"].dt.month
)
participaciones_canal_region = (
    historico_canal_region_reparto
    .groupby(
        claves_serie_sku
        + ["Canal", "Region", "Mes_Calendario"],
        as_index=False,
    )
    .agg(
        Demanda_Canal_Region_Historica=(
            "Demanda_Canal_Region",
            "sum",
        )
    )
)
participaciones_canal_region["Demanda_SKU_Mes_Historica"] = (
    participaciones_canal_region
    .groupby(claves_serie_sku + ["Mes_Calendario"])[
        "Demanda_Canal_Region_Historica"
    ]
    .transform("sum")
)
participaciones_canal_region["Participacion_Canal_Region"] = (
    participaciones_canal_region["Demanda_Canal_Region_Historica"]
    / participaciones_canal_region["Demanda_SKU_Mes_Historica"]
)
pronostico_canal_region_2026 = pronostico_sku_2026_revisado.merge(
    participaciones_canal_region[
        claves_serie_sku
        + [
            "Mes_Calendario",
            "Canal",
            "Region",
            "Participacion_Canal_Region",
        ]
    ],
    on=claves_serie_sku + ["Mes_Calendario"],
    how="left",
    validate="one_to_many",
)
for columna_origen, columna_detalle in [
    ("Pronostico_Modelo_Sin_Promocion", "Pronostico_Base"),
    ("Pronostico_Recomendado", "Pronostico_Recomendado_Detalle"),
    ("Pronostico_Protegido", "Pronostico_Protegido_Detalle"),
    ("Pronostico_Final", "Pronostico_Final_Detalle"),
]:
    pronostico_canal_region_2026[columna_detalle] = (
        pronostico_canal_region_2026[columna_origen]
        * pronostico_canal_region_2026["Participacion_Canal_Region"]
    )

columnas_canal_region_2026 = [
    "Fecha",
    "SKU",
    "Producto",
    "Categoria",
    "Canal",
    "Region",
    "Estado_SKU",
    "Participacion_Canal_Region",
    "Factor_Promocional_SKU",
    "Proporcion_Promocion_Esperada",
    "Pronostico_Base",
    "Pronostico_Recomendado_Detalle",
    "Pronostico_Protegido_Detalle",
    "Pronostico_Final_Detalle",
]
pronostico_canal_region_2026 = (
    pronostico_canal_region_2026[columnas_canal_region_2026]
    .sort_values(["Fecha", "Categoria", "SKU", "Canal", "Region"])
)
validacion_canal_region_2026 = (
    pronostico_canal_region_2026
    .groupby(["Fecha", "SKU"], as_index=False)
    .agg(
        Total_Detalle=("Pronostico_Final_Detalle", "sum"),
        Suma_Participaciones=("Participacion_Canal_Region", "sum"),
    )
    .merge(
        pronostico_sku_2026_revisado[
            ["Fecha", "SKU", "Pronostico_Final"]
        ],
        on=["Fecha", "SKU"],
        how="left",
        validate="one_to_one",
    )
)
validacion_canal_region_2026["Diferencia"] = (
    validacion_canal_region_2026["Total_Detalle"]
    - validacion_canal_region_2026["Pronostico_Final"]
)

columnas_sku_2026 = [
    "Fecha",
    "Mes_Calendario",
    "SKU",
    "Producto",
    "Categoria",
    "Estado_SKU",
    "Nivel_Actual",
    "Indice_Estacional",
    "Pronostico_Modelo_Sin_Promocion",
    "Anios_Con_Promocion",
    "Promocion_Recurrente",
    "Proporcion_Promocion_Esperada",
    "Factor_Promocional_SKU",
    "Multiplicador_Promo_Recurrente",
    "Pronostico_Promo_Recurrente",
    "Pronostico_Recomendado",
    "Proteccion_Sesgo_pct",
    "Pronostico_Protegido",
    "Ajuste_Manual_pct",
    "Ajuste_Manual_Unidades",
    "Pronostico_Final",
    "Regla_Pausa_Aplicada",
]
pronostico_sku_2026_revisado = (
    pronostico_sku_2026_revisado[columnas_sku_2026]
    .sort_values(["Fecha", "Categoria", "SKU"])
)

# Para cada pronóstico 2026 dejamos al lado lo vendido en el mismo mes de los
# tres años disponibles. Esta tabla no es otro modelo: explica el contexto que
# una persona puede revisar antes de aceptar una cifra.
historial_mismo_mes = demanda_sku.copy()
historial_mismo_mes["Anio"] = historial_mismo_mes["Fecha"].dt.year
historial_mismo_mes["Mes_Calendario"] = (
    historial_mismo_mes["Fecha"].dt.month
)
historial_mismo_mes = (
    historial_mismo_mes.pivot_table(
        index=["SKU", "Producto", "Categoria", "Mes_Calendario"],
        columns="Anio",
        values="Demanda",
        aggfunc="sum",
    )
    .reset_index()
    .rename(
        columns={
            2023: "Venta_Mismo_Mes_2023",
            2024: "Venta_Mismo_Mes_2024",
            2025: "Venta_Mismo_Mes_2025",
        }
    )
)

trazabilidad_pronostico_2026 = (
    pronostico_sku_2026_revisado.merge(
        historial_mismo_mes,
        on=["SKU", "Producto", "Categoria", "Mes_Calendario"],
        how="left",
        validate="many_to_one",
    )
)
trazabilidad_pronostico_2026["Variacion_Recomendado_vs_2025_pct"] = (
    (
        trazabilidad_pronostico_2026["Pronostico_Recomendado"]
        / trazabilidad_pronostico_2026[
            "Venta_Mismo_Mes_2025"
        ].replace(0, pd.NA)
    )
    - 1
) * 100
trazabilidad_pronostico_2026 = trazabilidad_pronostico_2026.sort_values(
    ["Fecha", "Categoria", "SKU"]
)

columnas_region_2026 = [
    "Fecha",
    "SKU",
    "Producto",
    "Categoria",
    "Region",
    "Estado_SKU",
    "Participacion_Region",
    "Pronostico_Base_Region",
    "Pronostico_Recomendado_Region",
    "Pronostico_Protegido_Region",
    "Pronostico_Final_Region",
]
pronostico_region_2026_revisado = (
    pronostico_region_2026_revisado[columnas_region_2026]
    .sort_values(["Fecha", "Categoria", "SKU", "Region"])
)

resumen_mensual_2026_revisado = (
    pronostico_sku_2026_revisado
    .groupby("Fecha", as_index=False)
    .agg(
        Base_Sin_Promocion=(
            "Pronostico_Modelo_Sin_Promocion",
            "sum",
        ),
        Promo_Recurrente=("Pronostico_Promo_Recurrente", "sum"),
        Recomendado=("Pronostico_Recomendado", "sum"),
        Protegido=("Pronostico_Protegido", "sum"),
        Final=("Pronostico_Final", "sum"),
    )
)

resumen_categoria_2026_revisado = (
    pronostico_sku_2026_revisado
    .groupby(["Fecha", "Categoria"], as_index=False)
    .agg(Pronostico_Final=("Pronostico_Final", "sum"))
)

promociones_recurrentes_2026 = (
    pronostico_sku_2026_revisado.loc[
        pronostico_sku_2026_revisado["Promocion_Recurrente"]
        & ~pronostico_sku_2026_revisado["Regla_Pausa_Aplicada"]
    ]
    .copy()
)

instrucciones_revisadas = pd.DataFrame(
    {
        "Tema": [
            "Nivel principal",
            "Pesos",
            "Base sin promoción",
            "Promoción recurrente",
            "Pronóstico recomendado",
            "Pronóstico protegido",
            "Azúcar",
            "Regiones",
            "Limitación",
        ],
        "Definicion": [
            "Pronóstico mensual por SKU",
            "0% mes antiguo, 50% intermedio y 50% reciente",
            "Nivel ponderado por índice estacional, con promociones históricas normalizadas",
            "Mismo SKU y mes con promoción en al menos dos años; se usa la proporción histórica",
            "Base más promoción recurrente; admite ajuste manual visible",
            "Escenario separado con protección contra el sesgo negativo",
            "SKU-1021 permanece en cero hasta reactivación manual",
            "El total SKU se reparte mediante participación histórica del mismo mes",
            "La recurrencia no sustituye un calendario de promociones recibido",
        ],
    }
)

CARPETA_RESULTADOS = Path(__file__).with_name("resultados")
CARPETA_RESPALDOS_CSV = CARPETA_RESULTADOS / "respaldos_csv"
CARPETA_VERSIONES_ANTERIORES = (
    CARPETA_RESULTADOS / "versiones_anteriores"
)
for carpeta_salida in [
    CARPETA_RESULTADOS,
    CARPETA_RESPALDOS_CSV,
    CARPETA_VERSIONES_ANTERIORES,
]:
    carpeta_salida.mkdir(parents=True, exist_ok=True)

SALIDA_PRONOSTICO_REVISADO = (
    CARPETA_RESULTADOS / "Pronostico_NutriVida_2026_FINAL.xlsx"
)
with pd.ExcelWriter(
    SALIDA_PRONOSTICO_REVISADO,
    engine="openpyxl",
) as escritor:
    instrucciones_revisadas.to_excel(
        escritor,
        sheet_name="LEEME",
        index=False,
    )
    demanda_sku.to_excel(
        escritor,
        sheet_name="Historico SKU",
        index=False,
    )
    historico_region_reparto.to_excel(
        escritor,
        sheet_name="Historico Region",
        index=False,
    )
    historico_canal_region_reparto.to_excel(
        escritor,
        sheet_name="Historico Canal Region",
        index=False,
    )
    pronostico_sku_2026_revisado.to_excel(
        escritor,
        sheet_name="Pronostico SKU",
        index=False,
    )
    pronostico_region_2026_revisado.to_excel(
        escritor,
        sheet_name="Desglose Region",
        index=False,
    )
    pronostico_canal_region_2026.to_excel(
        escritor,
        sheet_name="Desglose Canal Region",
        index=False,
    )
    resumen_mensual_2026_revisado.to_excel(
        escritor,
        sheet_name="Resumen Mensual",
        index=False,
    )
    resumen_categoria_2026_revisado.to_excel(
        escritor,
        sheet_name="Resumen Categoria",
        index=False,
    )
    promociones_recurrentes_2026.to_excel(
        escritor,
        sheet_name="Promos Recurrentes",
        index=False,
    )
    resultados_pesos_primera_ventana.to_excel(
        escritor,
        sheet_name="Validacion Pesos",
        index=False,
    )
    resultados_proteccion_primera.to_excel(
        escritor,
        sheet_name="Validacion Proteccion",
        index=False,
    )
    robustez_sku_2025.to_excel(
        escritor,
        sheet_name="Robustez SKU",
        index=False,
    )
    robustez_categoria_2025.to_excel(
        escritor,
        sheet_name="Robustez Categoria",
        index=False,
    )
    robustez_mes_2025.to_excel(
        escritor,
        sheet_name="Robustez Mes",
        index=False,
    )
    detalle_validacion_2025.to_excel(
        escritor,
        sheet_name="Detalle Validacion",
        index=False,
    )
    trazabilidad_pronostico_2026.to_excel(
        escritor,
        sheet_name="Trazabilidad 2026",
        index=False,
    )
    validacion_region_2026.to_excel(
        escritor,
        sheet_name="Control Regiones",
        index=False,
    )

# Copias en CSV para poder revisar los resultados sin un lector de Excel.
pronostico_sku_2026_revisado.to_csv(
    CARPETA_RESPALDOS_CSV / "Pronostico_SKU_2026.csv",
    index=False,
)
pronostico_region_2026_revisado.to_csv(
    CARPETA_RESPALDOS_CSV / "Desglose_Region_2026.csv",
    index=False,
)
pronostico_canal_region_2026.to_csv(
    CARPETA_RESPALDOS_CSV / "Desglose_Canal_Region_2026.csv",
    index=False,
)
resumen_mensual_2026_revisado.to_csv(
    CARPETA_RESPALDOS_CSV / "Resumen_Mensual_2026.csv",
    index=False,
)
promociones_recurrentes_2026.to_csv(
    CARPETA_RESPALDOS_CSV / "Promociones_Recurrentes_2026.csv",
    index=False,
)
resultados_proteccion_primera.to_csv(
    CARPETA_RESPALDOS_CSV / "Validacion_Proteccion_2026.csv",
    index=False,
)
robustez_sku_2025.to_csv(
    CARPETA_RESPALDOS_CSV / "Robustez_SKU_2025.csv",
    index=False,
)
robustez_categoria_2025.to_csv(
    CARPETA_RESPALDOS_CSV / "Robustez_Categoria_2025.csv",
    index=False,
)
robustez_mes_2025.to_csv(
    CARPETA_RESPALDOS_CSV / "Robustez_Mes_2025.csv",
    index=False,
)
detalle_validacion_2025.to_csv(
    CARPETA_RESPALDOS_CSV / "Detalle_Validacion_Modelos_2025.csv",
    index=False,
)
trazabilidad_pronostico_2026.to_csv(
    CARPETA_RESPALDOS_CSV / "Trazabilidad_Pronostico_2026.csv",
    index=False,
)

print("\n--- PRONÓSTICO REVISADO ENERO-JUNIO 2026 ---")
print("Filas SKU:", len(pronostico_sku_2026_revisado))
print("Filas regionales:", len(pronostico_region_2026_revisado))
print(
    "Combinaciones con promoción recurrente activa:",
    len(promociones_recurrentes_2026),
)
print(
    "Total base sin promoción:",
    round(
        pronostico_sku_2026_revisado[
            "Pronostico_Modelo_Sin_Promocion"
        ].sum(),
        2,
    ),
)
print(
    "Total recomendado con recurrencia:",
    round(pronostico_sku_2026_revisado["Pronostico_Recomendado"].sum(), 2),
)
print(
    "Total protegido contra subestimación:",
    round(pronostico_sku_2026_revisado["Pronostico_Protegido"].sum(), 2),
)
print(
    "Máxima diferencia regiones vs SKU:",
    validacion_region_2026["Diferencia"].abs().max(),
)
print(
    "Máxima diferencia canal-región vs SKU:",
    validacion_canal_region_2026["Diferencia"].abs().max(),
)
print(
    "Suma mínima y máxima de participaciones:",
    validacion_region_2026["Suma_Participaciones"].min(),
    validacion_region_2026["Suma_Participaciones"].max(),
)
print("Archivo generado:", SALIDA_PRONOSTICO_REVISADO)
print("\nResumen mensual revisado:")
print(resumen_mensual_2026_revisado.to_string(index=False))

# ---------------------------------------------------------------------------
# Tabla secundaria para análisis y distribución regional
# ---------------------------------------------------------------------------

demanda_sku_region = (
    ventas_modelo
    .groupby(
        [
            "Fecha",
            "SKU",
            "Producto",
            "Categoria",
            "Region",
        ],
        as_index=False,
    )
    .agg(Demanda=("Unidades_Modelo", "sum"))
    .sort_values(["SKU", "Region", "Fecha"])
)

print("\n--- TABLA MENSUAL POR SKU Y REGIÓN ---")
print("Filas:", len(demanda_sku_region))
print(
    "Series SKU-región:",
    demanda_sku_region.groupby(["SKU", "Region"]).ngroups,
)
print(
    "Meses por serie:",
    demanda_sku_region
    .groupby(["SKU", "Region"])
    .size()
    .value_counts()
)
print(demanda_sku_region.head(10).to_string(index=False))

claves_serie_region = [
    "SKU",
    "Producto",
    "Categoria",
    "Region",
]

# ---------------------------------------------------------------------------
# Ejemplo didáctico: modelo que repite el último dato
# ---------------------------------------------------------------------------

# Fingimos que estamos al cierre de diciembre de 2024. Los datos de 2025 se
# conservan en demanda_sku_region, pero no pueden entrar al historial de prueba.
fecha_corte_ejemplo = pd.Timestamp("2024-12-01")

historial_prueba = demanda_sku_region.loc[
    demanda_sku_region["Fecha"].le(fecha_corte_ejemplo)
].copy()

# Como cada serie está ordenada por fecha, tail(1) conserva su última fila.
ultimo_por_serie = (
    historial_prueba
    .sort_values("Fecha")
    .groupby(claves_serie_region, as_index=False)
    .tail(1)
)

print("\n--- HISTORIAL DISPONIBLE PARA LA PRUEBA ---")
print("Primera fecha:", historial_prueba["Fecha"].min())
print("Última fecha:", historial_prueba["Fecha"].max())
print("Filas:", len(historial_prueba))

print("\n--- ÚLTIMO DATO DE CADA SERIE ---")
print("Filas:", len(ultimo_por_serie))
print(
    ultimo_por_serie[
        ["Fecha", "SKU", "Region", "Demanda"]
    ]
    .head(10)
    .to_string(index=False)
)

# Creamos los seis meses posteriores a la fecha de corte. MS significa
# "month start": cada fecha corresponde al primer día del mes.
fechas_futuras_ejemplo = pd.DataFrame(
    {
        "Fecha": pd.date_range(
            fecha_corte_ejemplo + pd.offsets.MonthBegin(1),
            periods=6,
            freq="MS",
        )
    }
)

# Extraemos las 75 combinaciones únicas de SKU y región. Producto y categoría
# viajan como etiquetas para usarlos después en filtros y gráficas.
series_ejemplo = demanda_sku_region[
    claves_serie_region
].drop_duplicates()

# how="cross" combina cada una de las 75 series con cada uno de los seis meses:
# 75 × 6 = 450 filas que todavía no tienen valor pronosticado.
base_futura_ejemplo = series_ejemplo.merge(
    fechas_futuras_ejemplo,
    how="cross",
)

# Conservamos únicamente las claves y la última demanda. Renombramos Demanda
# porque, a partir de aquí, ya representa un pronóstico y no un valor real.
referencia_ultimo_ejemplo = ultimo_por_serie[
    claves_serie_region + ["Demanda"]
].rename(columns={"Demanda": "Pronostico_Ultimo"})

# Cada serie futura encuentra una sola referencia histórica. La validación
# many_to_one comprueba que no haya dos últimos valores para la misma serie.
pronostico_ultimo_ejemplo = base_futura_ejemplo.merge(
    referencia_ultimo_ejemplo,
    on=claves_serie_region,
    how="left",
    validate="many_to_one",
)

print("\n--- FECHAS FUTURAS DEL EJEMPLO ---")
print(fechas_futuras_ejemplo.to_string(index=False))
print("\n--- PRONÓSTICO QUE REPITE EL ÚLTIMO DATO ---")
print("Filas:", len(pronostico_ultimo_ejemplo))
print(
    pronostico_ultimo_ejemplo.loc[
        pronostico_ultimo_ejemplo["SKU"].eq("SKU-1001")
        & pronostico_ultimo_ejemplo["Region"].eq("Norte"),
        ["Fecha", "SKU", "Region", "Pronostico_Ultimo"],
    ].to_string(index=False)
)

# Destapamos las respuestas: unimos el pronóstico con la demanda que realmente
# ocurrió entre enero y junio de 2025. one_to_one exige una sola observación real
# para cada fila pronosticada.
comparacion_ultimo_ejemplo = pronostico_ultimo_ejemplo.merge(
    demanda_sku_region[
        claves_serie_region + ["Fecha", "Demanda"]
    ],
    on=claves_serie_region + ["Fecha"],
    how="left",
    validate="one_to_one",
)

comparacion_ultimo_ejemplo["Error"] = (
    comparacion_ultimo_ejemplo["Pronostico_Ultimo"]
    - comparacion_ultimo_ejemplo["Demanda"]
)
comparacion_ultimo_ejemplo["Error_Absoluto"] = (
    comparacion_ultimo_ejemplo["Error"].abs()
)

wape_ultimo_ejemplo = (
    comparacion_ultimo_ejemplo["Error_Absoluto"].sum()
    / comparacion_ultimo_ejemplo["Demanda"].sum()
    * 100
)
sesgo_ultimo_ejemplo = (
    comparacion_ultimo_ejemplo["Error"].sum()
    / comparacion_ultimo_ejemplo["Demanda"].sum()
    * 100
)

print("\n--- EVALUACIÓN DEL MODELO ÚLTIMO DATO ---")
print(f"WAPE: {wape_ultimo_ejemplo:.2f}%")
print(f"Sesgo: {sesgo_ultimo_ejemplo:.2f}%")
print("\nEjemplo SKU-1001, región Norte:")
print(
    comparacion_ultimo_ejemplo.loc[
        comparacion_ultimo_ejemplo["SKU"].eq("SKU-1001")
        & comparacion_ultimo_ejemplo["Region"].eq("Norte"),
        [
            "Fecha",
            "Pronostico_Ultimo",
            "Demanda",
            "Error",
            "Error_Absoluto",
        ],
    ].to_string(index=False)
)

# ---------------------------------------------------------------------------
# Ejemplo didáctico: promedio de los últimos tres meses
# ---------------------------------------------------------------------------

# tail(3) conserva octubre, noviembre y diciembre de 2024 para cada serie. El
# segundo groupby calcula un único promedio por SKU y región.
ultimos_tres_ejemplo = (
    historial_prueba
    .sort_values("Fecha")
    .groupby(claves_serie_region, group_keys=False)
    .tail(3)
)

promedio_tres_ejemplo = (
    ultimos_tres_ejemplo
    .groupby(claves_serie_region, as_index=False)
    .agg(Pronostico_Promedio_3=("Demanda", "mean"))
)

# Reutilizamos las mismas 450 filas futuras. El promedio de cada serie se
# repite en los seis meses porque este modelo todavía no conoce estacionalidad.
pronostico_promedio_tres_ejemplo = base_futura_ejemplo.merge(
    promedio_tres_ejemplo,
    on=claves_serie_region,
    how="left",
    validate="many_to_one",
)

comparacion_promedio_tres_ejemplo = (
    pronostico_promedio_tres_ejemplo.merge(
        demanda_sku_region[
            claves_serie_region + ["Fecha", "Demanda"]
        ],
        on=claves_serie_region + ["Fecha"],
        how="left",
        validate="one_to_one",
    )
)

comparacion_promedio_tres_ejemplo["Error"] = (
    comparacion_promedio_tres_ejemplo["Pronostico_Promedio_3"]
    - comparacion_promedio_tres_ejemplo["Demanda"]
)
comparacion_promedio_tres_ejemplo["Error_Absoluto"] = (
    comparacion_promedio_tres_ejemplo["Error"].abs()
)

wape_promedio_tres_ejemplo = (
    comparacion_promedio_tres_ejemplo["Error_Absoluto"].sum()
    / comparacion_promedio_tres_ejemplo["Demanda"].sum()
    * 100
)
sesgo_promedio_tres_ejemplo = (
    comparacion_promedio_tres_ejemplo["Error"].sum()
    / comparacion_promedio_tres_ejemplo["Demanda"].sum()
    * 100
)

print("\n--- EVALUACIÓN DEL PROMEDIO DE TRES MESES ---")
print("Filas usadas para calcular promedios:", len(ultimos_tres_ejemplo))
print("Promedios SKU-región:", len(promedio_tres_ejemplo))
print(f"WAPE: {wape_promedio_tres_ejemplo:.2f}%")
print(f"Sesgo: {sesgo_promedio_tres_ejemplo:.2f}%")

print("\nÚltimos tres meses de SKU-1001, región Norte:")
print(
    ultimos_tres_ejemplo.loc[
        ultimos_tres_ejemplo["SKU"].eq("SKU-1001")
        & ultimos_tres_ejemplo["Region"].eq("Norte"),
        ["Fecha", "Demanda"],
    ].to_string(index=False)
)

print("\nPronóstico y resultado de SKU-1001, región Norte:")
print(
    comparacion_promedio_tres_ejemplo.loc[
        comparacion_promedio_tres_ejemplo["SKU"].eq("SKU-1001")
        & comparacion_promedio_tres_ejemplo["Region"].eq("Norte"),
        [
            "Fecha",
            "Pronostico_Promedio_3",
            "Demanda",
            "Error",
            "Error_Absoluto",
        ],
    ].to_string(index=False)
)

# La empresa sólo entrega pronóstico por SKU, no por región. Para compararnos
# justamente, sumamos nuestras tres regiones y evaluamos el mismo semestre.
ultimo_agregado_sku_ejemplo = (
    comparacion_ultimo_ejemplo
    .groupby(["Fecha", "SKU"], as_index=False)
    .agg(
        Demanda=("Demanda", "sum"),
        Pronostico=("Pronostico_Ultimo", "sum"),
    )
)
promedio_tres_agregado_sku_ejemplo = (
    comparacion_promedio_tres_ejemplo
    .groupby(["Fecha", "SKU"], as_index=False)
    .agg(
        Demanda=("Demanda", "sum"),
        Pronostico=("Pronostico_Promedio_3", "sum"),
    )
)
empresa_mismo_semestre_ejemplo = evaluacion_empresa.loc[
    evaluacion_empresa["Fecha"].between("2025-01-01", "2025-06-01")
].copy()

metricas_ultimo_sku_ejemplo = calcular_metricas_pronostico(
    ultimo_agregado_sku_ejemplo,
    "Demanda",
    "Pronostico",
)
metricas_promedio_tres_sku_ejemplo = calcular_metricas_pronostico(
    promedio_tres_agregado_sku_ejemplo,
    "Demanda",
    "Pronostico",
)
metricas_empresa_semestre_ejemplo = calcular_metricas_pronostico(
    empresa_mismo_semestre_ejemplo,
    "Venta_Modelo",
    "Pronostico_Empresa",
)

print("\n--- COMPARACIÓN JUSTA A NIVEL SKU: ENERO-JUNIO 2025 ---")
print(
    "Último dato: "
    f"WAPE {metricas_ultimo_sku_ejemplo['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_ultimo_sku_ejemplo['Sesgo_pct']:.2f}%"
)
print(
    "Promedio de 3: "
    f"WAPE {metricas_promedio_tres_sku_ejemplo['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_promedio_tres_sku_ejemplo['Sesgo_pct']:.2f}%"
)
print(
    "Empresa: "
    f"WAPE {metricas_empresa_semestre_ejemplo['WAPE_pct']:.2f}%, "
    f"sesgo {metricas_empresa_semestre_ejemplo['Sesgo_pct']:.2f}%"
)


def pronosticar_seis_meses(tabla_demanda, fecha_corte):
    """Genera cuatro pronósticos usando solo datos disponibles al corte."""
    fecha_corte = pd.Timestamp(fecha_corte)
    historial = tabla_demanda.loc[
        tabla_demanda["Fecha"].le(fecha_corte)
    ].copy()

    fechas_futuras = pd.DataFrame(
        {
            "Fecha": pd.date_range(
                fecha_corte + pd.offsets.MonthBegin(1),
                periods=6,
                freq="MS",
            )
        }
    )

    series = tabla_demanda[claves_serie_region].drop_duplicates()
    base = series.merge(fechas_futuras, how="cross")

    # Último dato conocido: mantiene el último mes durante todo el horizonte.
    ultimo_dato = (
        historial
        .sort_values("Fecha")
        .groupby(claves_serie_region, as_index=False)
        .tail(1)[claves_serie_region + ["Demanda"]]
        .rename(columns={"Demanda": "Pronostico_Ultimo"})
    )
    base = base.merge(
        ultimo_dato,
        on=claves_serie_region,
        how="left",
        validate="many_to_one",
    )

    # Promedio reciente: nivel medio de los últimos tres meses disponibles.
    promedio_tres = (
        historial
        .sort_values("Fecha")
        .groupby(claves_serie_region, group_keys=False)
        .tail(3)
        .groupby(claves_serie_region, as_index=False)
        .agg(Pronostico_Promedio_3=("Demanda", "mean"))
    )
    base = base.merge(
        promedio_tres,
        on=claves_serie_region,
        how="left",
        validate="many_to_one",
    )

    # Naive estacional: utiliza exactamente el mismo mes del año anterior.
    base["Fecha_Referencia"] = base["Fecha"] - pd.DateOffset(years=1)
    referencia_anual = historial[
        claves_serie_region + ["Fecha", "Demanda"]
    ].rename(
        columns={
            "Fecha": "Fecha_Referencia",
            "Demanda": "Pronostico_Mismo_Mes_Anterior",
        }
    )
    base = base.merge(
        referencia_anual,
        on=claves_serie_region + ["Fecha_Referencia"],
        how="left",
        validate="many_to_one",
    )

    # Promedio estacional: promedio de ese mes calendario en años anteriores.
    historial["Mes_Calendario"] = historial["Fecha"].dt.month
    promedio_estacional = (
        historial
        .groupby(
            claves_serie_region + ["Mes_Calendario"],
            as_index=False,
        )
        .agg(Pronostico_Promedio_Estacional=("Demanda", "mean"))
    )
    base["Mes_Calendario"] = base["Fecha"].dt.month
    base = base.merge(
        promedio_estacional,
        on=claves_serie_region + ["Mes_Calendario"],
        how="left",
        validate="many_to_one",
    )

    # Combinación simple de nivel reciente y patrón estacional.
    base["Pronostico_Combinado"] = base[
        [
            "Pronostico_Promedio_3",
            "Pronostico_Promedio_Estacional",
        ]
    ].mean(axis=1)

    base["Fecha_Corte"] = fecha_corte
    return base


pronosticos_backtest = []

for fecha_corte in ["2024-12-01", "2025-06-01"]:
    bloque = pronosticar_seis_meses(
        demanda_sku_region,
        fecha_corte,
    )
    bloque = bloque.merge(
        demanda_sku_region[
            claves_serie_region + ["Fecha", "Demanda"]
        ],
        on=claves_serie_region + ["Fecha"],
        how="left",
        validate="one_to_one",
    )
    pronosticos_backtest.append(bloque)

backtest_region = pd.concat(
    pronosticos_backtest,
    ignore_index=True,
)

backtest_region["Es_Periodo_Inactivo_Azucar"] = (
    backtest_region["SKU"].eq("SKU-1021")
    & backtest_region["Fecha"].ge("2025-07-01")
)

columnas_modelos = [
    "Pronostico_Ultimo",
    "Pronostico_Promedio_3",
    "Pronostico_Mismo_Mes_Anterior",
    "Pronostico_Promedio_Estacional",
    "Pronostico_Combinado",
]

resultados_backtest = []

for columna_modelo in columnas_modelos:
    metricas_todas = calcular_metricas_pronostico(
        backtest_region,
        "Demanda",
        columna_modelo,
    )
    metricas_activas = calcular_metricas_pronostico(
        backtest_region.loc[
            ~backtest_region["Es_Periodo_Inactivo_Azucar"]
        ],
        "Demanda",
        columna_modelo,
    )

    resultados_backtest.append(
        {
            "Modelo": columna_modelo,
            "WAPE_Todos_pct": metricas_todas["WAPE_pct"],
            "Sesgo_Todos_pct": metricas_todas["Sesgo_pct"],
            "WAPE_Activos_pct": metricas_activas["WAPE_pct"],
            "Sesgo_Activos_pct": metricas_activas["Sesgo_pct"],
        }
    )

resultados_backtest = pd.DataFrame(resultados_backtest).sort_values(
    "WAPE_Activos_pct"
)

# También evaluamos al nivel SKU-mes para compararlo con el pronóstico de la
# empresa, que no está desglosado por región.
backtest_sku = (
    backtest_region
    .groupby(
        ["Fecha_Corte", "Fecha", "SKU", "Categoria"],
        as_index=False,
    )
    .agg(
        Demanda=("Demanda", "sum"),
        **{
            columna: (columna, "sum")
            for columna in columnas_modelos
        },
    )
)

backtest_sku["Es_Periodo_Inactivo_Azucar"] = (
    backtest_sku["SKU"].eq("SKU-1021")
    & backtest_sku["Fecha"].ge("2025-07-01")
)

resultados_backtest_sku = []

for columna_modelo in columnas_modelos:
    metricas = calcular_metricas_pronostico(
        backtest_sku.loc[
            ~backtest_sku["Es_Periodo_Inactivo_Azucar"]
        ],
        "Demanda",
        columna_modelo,
    )
    resultados_backtest_sku.append(
        {
            "Modelo": columna_modelo,
            "WAPE_Activos_pct": metricas["WAPE_pct"],
            "Sesgo_Activos_pct": metricas["Sesgo_pct"],
        }
    )

resultados_backtest_sku = pd.DataFrame(
    resultados_backtest_sku
).sort_values("WAPE_Activos_pct")

print("\n--- BACKTEST DE SEIS MESES POR SKU Y REGIÓN ---")
print("Filas de demanda mensual:", len(demanda_sku_region))
print("Series SKU-región:", demanda_sku_region.groupby(
    claves_serie_region
).ngroups)
print(resultados_backtest.to_string(index=False))

print("\n--- BACKTEST AGREGADO A SKU-MES ---")
print(resultados_backtest_sku.to_string(index=False))

# Revisamos cada ventana por separado. Esto evita elegir un modelo que parezca
# bueno únicamente porque un semestre compensa los errores del otro.
resultados_por_corte = []

for fecha_corte, bloque_corte in backtest_region.groupby("Fecha_Corte"):
    bloque_activo = bloque_corte.loc[
        ~bloque_corte["Es_Periodo_Inactivo_Azucar"]
    ]

    for columna_modelo in columnas_modelos:
        metricas = calcular_metricas_pronostico(
            bloque_activo,
            "Demanda",
            columna_modelo,
        )
        resultados_por_corte.append(
            {
                "Fecha_Corte": fecha_corte,
                "Modelo": columna_modelo,
                "WAPE_Activos_pct": metricas["WAPE_pct"],
                "Sesgo_Activos_pct": metricas["Sesgo_pct"],
            }
        )

resultados_por_corte = pd.DataFrame(resultados_por_corte).sort_values(
    ["Fecha_Corte", "WAPE_Activos_pct"]
)

resultados_sku_por_corte = []

for fecha_corte, bloque_corte in backtest_sku.groupby("Fecha_Corte"):
    bloque_activo = bloque_corte.loc[
        ~bloque_corte["Es_Periodo_Inactivo_Azucar"]
    ]

    for columna_modelo in columnas_modelos:
        metricas = calcular_metricas_pronostico(
            bloque_activo,
            "Demanda",
            columna_modelo,
        )
        resultados_sku_por_corte.append(
            {
                "Fecha_Corte": fecha_corte,
                "Modelo": columna_modelo,
                "WAPE_Activos_pct": metricas["WAPE_pct"],
                "Sesgo_Activos_pct": metricas["Sesgo_pct"],
            }
        )

resultados_sku_por_corte = pd.DataFrame(
    resultados_sku_por_corte
).sort_values(["Fecha_Corte", "WAPE_Activos_pct"])

print("\n--- ESTABILIDAD POR CORTE: SKU Y REGIÓN ---")
print(resultados_por_corte.to_string(index=False))

print("\n--- ESTABILIDAD POR CORTE: SKU AGREGADO ---")
print(resultados_sku_por_corte.to_string(index=False))

# ---------------------------------------------------------------------------
# Pronóstico final: enero a junio de 2026
# ---------------------------------------------------------------------------

# Elegimos el modelo combinado porque al nivel operativo SKU-región conserva
# casi la mejor precisión y tiene menos sesgo negativo que el promedio
# estacional puro. No aplicamos un factor promocional futuro explícito; los
# efectos de promociones pasadas sí permanecen dentro de los promedios.
pronostico_2026 = pronosticar_seis_meses(
    demanda_sku_region,
    "2025-12-01",
)

pronostico_2026["Pronostico_Antes_Regla"] = (
    pronostico_2026["Pronostico_Combinado"].clip(lower=0)
)

# SKU-1021 presenta cero venta, cero pronóstico y cero inventario de agosto a
# diciembre de 2025. Lo tratamos como pausado: el modelo no debe reactivarlo
# solo por encontrar ventas en los mismos meses de años anteriores.
pronostico_2026["Estado_SKU"] = "Activo"
pronostico_2026["Motivo_Regla"] = "Sin regla especial"

mascara_azucar_pausada = pronostico_2026["SKU"].eq("SKU-1021")
pronostico_2026.loc[mascara_azucar_pausada, "Estado_SKU"] = "Pausado"
pronostico_2026.loc[
    mascara_azucar_pausada,
    "Motivo_Regla",
] = "Pausa observada desde 2025-07; requiere reactivación manual"

pronostico_2026["Pronostico_Base"] = pronostico_2026[
    "Pronostico_Antes_Regla"
]
pronostico_2026.loc[mascara_azucar_pausada, "Pronostico_Base"] = 0.0

# Escenario opcional para el objetivo secundario de reducir faltantes. El
# backtest mostró que el modelo combinado quedó corto en promedio. Corregimos
# exactamente ese sesgo, sin presentarlo como una nueva predicción neutral.
sesgo_combinado_activos = resultados_backtest.loc[
    resultados_backtest["Modelo"].eq("Pronostico_Combinado"),
    "Sesgo_Activos_pct",
].iloc[0]
factor_correccion_sesgo = 1 / (1 + sesgo_combinado_activos / 100)

pronostico_2026["Pronostico_Proteccion"] = (
    pronostico_2026["Pronostico_Base"] * factor_correccion_sesgo
)
pronostico_2026.loc[
    mascara_azucar_pausada,
    "Pronostico_Proteccion",
] = 0.0

# Estas dos columnas serán controles editables en el dashboard. El porcentaje
# sirve para subir o bajar una proyección; las unidades permiten reactivar un
# producto cuyo pronóstico base es cero.
pronostico_2026["Ajuste_Manual_pct"] = 0.0
pronostico_2026["Ajuste_Manual_Unidades"] = 0.0
pronostico_2026["Pronostico_Final"] = (
    pronostico_2026["Pronostico_Base"]
    * (1 + pronostico_2026["Ajuste_Manual_pct"])
    + pronostico_2026["Ajuste_Manual_Unidades"]
).clip(lower=0)

columnas_pronostico_final = [
    "Fecha",
    "SKU",
    "Producto",
    "Categoria",
    "Region",
    "Estado_SKU",
    "Pronostico_Promedio_3",
    "Pronostico_Promedio_Estacional",
    "Pronostico_Antes_Regla",
    "Pronostico_Base",
    "Pronostico_Proteccion",
    "Ajuste_Manual_pct",
    "Ajuste_Manual_Unidades",
    "Pronostico_Final",
    "Motivo_Regla",
]

pronostico_2026 = pronostico_2026[
    columnas_pronostico_final
].sort_values(["Fecha", "Categoria", "SKU", "Region"])

columnas_redondeables = [
    "Pronostico_Promedio_3",
    "Pronostico_Promedio_Estacional",
    "Pronostico_Antes_Regla",
    "Pronostico_Base",
    "Pronostico_Proteccion",
    "Pronostico_Final",
]
pronostico_2026[columnas_redondeables] = pronostico_2026[
    columnas_redondeables
].round(2)

resumen_pronostico_sku = (
    pronostico_2026
    .groupby(
        ["Fecha", "SKU", "Producto", "Categoria", "Estado_SKU"],
        as_index=False,
    )
    .agg(
        Pronostico_Base=("Pronostico_Base", "sum"),
        Pronostico_Proteccion=("Pronostico_Proteccion", "sum"),
        Pronostico_Final=("Pronostico_Final", "sum"),
    )
)

resumen_pronostico_categoria = (
    pronostico_2026
    .groupby(["Fecha", "Categoria"], as_index=False)
    .agg(
        Pronostico_Base=("Pronostico_Base", "sum"),
        Pronostico_Proteccion=("Pronostico_Proteccion", "sum"),
        Pronostico_Final=("Pronostico_Final", "sum"),
    )
)

resumen_pronostico_region = (
    pronostico_2026
    .groupby(["Fecha", "Region"], as_index=False)
    .agg(
        Pronostico_Base=("Pronostico_Base", "sum"),
        Pronostico_Proteccion=("Pronostico_Proteccion", "sum"),
        Pronostico_Final=("Pronostico_Final", "sum"),
    )
)

# Control de razonabilidad: comparamos el total de enero-junio pronosticado con
# los mismos seis meses de cada año histórico. No es una corrección; es una
# revisión para detectar resultados absurdamente altos o bajos.
historico_enero_junio = (
    demanda_sku_region.loc[
        demanda_sku_region["Fecha"].dt.month.le(6)
    ]
    .assign(Anio=lambda tabla: tabla["Fecha"].dt.year)
    .groupby("Anio", as_index=False)
    .agg(Unidades=("Demanda", "sum"))
)

total_pronostico_2026 = pronostico_2026["Pronostico_Base"].sum()
total_enero_junio_2025 = historico_enero_junio.loc[
    historico_enero_junio["Anio"].eq(2025),
    "Unidades",
].iloc[0]
variacion_pronostico_vs_2025 = (
    total_pronostico_2026 / total_enero_junio_2025 - 1
) * 100

comparacion_semestral = pd.concat(
    [
        historico_enero_junio.assign(Tipo="Histórico"),
        pd.DataFrame(
            {
                "Anio": [2026],
                "Unidades": [total_pronostico_2026],
                "Tipo": ["Pronóstico base"],
            }
        ),
    ],
    ignore_index=True,
)

instrucciones_salida = pd.DataFrame(
    {
        "Campo": [
            "Método seleccionado",
            "Periodo",
            "Nivel de cálculo",
            "Ajuste_Manual_pct",
            "Ajuste_Manual_Unidades",
            "Pronostico_Proteccion",
            "Pronostico_Final",
            "Regla SKU-1021",
            "Promociones futuras",
        ],
        "Explicacion": [
            "Promedio de los últimos 3 meses y del mismo mes calendario histórico",
            "Enero a junio de 2026",
            "SKU y región; después se puede sumar por SKU, categoría o región",
            "0.10 sube 10%; -0.10 baja 10%",
            "Cantidad absoluta que se suma; permite reactivar una base igual a cero",
            "Base corregida por el sesgo de subestimación observado; escenario opcional",
            "Base × (1 + porcentaje) + unidades; nunca menor que cero",
            "Se mantiene en cero por pausa observada; puede reactivarse si se reciben datos",
            "No se agrega un factor futuro; promociones históricas permanecen en los promedios",
        ],
    }
)

SALIDA_PRONOSTICO = (
    CARPETA_VERSIONES_ANTERIORES
    / "Pronostico_NutriVida_2026_INICIAL.xlsx"
)

with pd.ExcelWriter(SALIDA_PRONOSTICO, engine="openpyxl") as escritor:
    instrucciones_salida.to_excel(
        escritor,
        sheet_name="LEEME",
        index=False,
    )
    demanda_sku_region.to_excel(
        escritor,
        sheet_name="Historico Modelo",
        index=False,
    )
    pronostico_2026.to_excel(
        escritor,
        sheet_name="Detalle SKU Region",
        index=False,
    )
    resumen_pronostico_sku.to_excel(
        escritor,
        sheet_name="Resumen SKU",
        index=False,
    )
    resumen_pronostico_categoria.to_excel(
        escritor,
        sheet_name="Resumen Categoria",
        index=False,
    )
    resumen_pronostico_region.to_excel(
        escritor,
        sheet_name="Resumen Region",
        index=False,
    )
    resultados_backtest.to_excel(
        escritor,
        sheet_name="Validacion Modelos",
        index=False,
    )
    comparacion_semestral.to_excel(
        escritor,
        sheet_name="Comparacion Semestral",
        index=False,
    )

print("\n--- PRONÓSTICO FINAL ENERO-JUNIO 2026 ---")
print("Filas SKU-región:", len(pronostico_2026))
print("SKU:", pronostico_2026["SKU"].nunique())
print("Regiones:", pronostico_2026["Region"].nunique())
print("Meses:", pronostico_2026["Fecha"].nunique())
print(
    "Unidades del pronóstico base:",
    round(pronostico_2026["Pronostico_Base"].sum(), 2),
)
print(
    "Factor de corrección del escenario de protección:",
    round(factor_correccion_sesgo, 4),
)
print(
    "Unidades del escenario de protección:",
    round(pronostico_2026["Pronostico_Proteccion"].sum(), 2),
)
print("Filas pausadas de SKU-1021:", mascara_azucar_pausada.sum())
print("Archivo generado:", SALIDA_PRONOSTICO)
print(
    "Variación contra enero-junio 2025:",
    f"{variacion_pronostico_vs_2025:.2f}%",
)

print("\nComparación enero-junio:")
print(comparacion_semestral.to_string(index=False))

print("\nResumen mensual:")
print(
    pronostico_2026
    .groupby("Fecha", as_index=False)
    .agg(Pronostico_Base=("Pronostico_Base", "sum"))
    .to_string(index=False)
)
