"""Reglas de validación, limpieza y auditoría de los archivos de entrada.

Este es el archivo que debes abrir cuando quieras cambiar qué ocurre con
duplicados, vacíos, negativos, precios, nombres de canal o datos atípicos.
Las columnas originales se conservan; las transformaciones para modelar viven
en columnas separadas y en el diagnóstico devuelto.
"""

from io import BytesIO
from pathlib import Path

import pandas as pd


HOJAS_REQUERIDAS = {
    "Ventas Historicas": {
        "Fecha", "SKU", "Producto", "Categoria", "Canal", "Region",
        "Unidades", "Precio_Unitario_USD", "Promocion",
    },
    "Precios y Costos": {
        "SKU", "Precio_Venta_USD", "Margen_Bruto_pct",
        "Costo_Almacenaje_Mes_USD_Unid", "Vida_Util_Meses",
    },
}
CANAL_CANONICO = {
    "e-commerce": "Ecommerce",
    "ecommerce": "Ecommerce",
    "super": "Supermercado",
    "supermercado": "Supermercado",
    "mayorista": "Mayorista",
}
REGION_CANONICA = {
    "norte": "Norte",
    "centro": "Centro",
    "sur": "Sur",
}


def abrir_excel(origen):
    """Abre una ruta o los bytes de un archivo cargado."""
    if isinstance(origen, (str, Path)):
        return pd.ExcelFile(origen)
    return pd.ExcelFile(BytesIO(origen))


def preparar_catalogo_financiero(catalogo):
    """Valida los datos económicos sin convertirlos en demanda."""
    catalogo = catalogo.copy()
    catalogo["SKU"] = catalogo["SKU"].astype("string").str.strip().str.upper()
    if catalogo["SKU"].isna().any() or catalogo["SKU"].eq("").any():
        raise ValueError("La hoja Precios y Costos contiene SKU vacíos.")
    if catalogo["SKU"].duplicated().any():
        raise ValueError(
            "La hoja Precios y Costos contiene SKU repetidos; debe quedar una "
            "sola referencia económica por SKU."
        )
    numericas = [
        "Precio_Venta_USD",
        "Margen_Bruto_pct",
        "Costo_Almacenaje_Mes_USD_Unid",
        "Vida_Util_Meses",
    ]
    for columna in numericas:
        catalogo[columna] = pd.to_numeric(
            catalogo[columna], errors="coerce"
        )
    if catalogo[numericas].isna().any().any():
        columnas = catalogo[numericas].columns[
            catalogo[numericas].isna().any()
        ].tolist()
        raise ValueError(
            "Hay valores económicos vacíos o no numéricos en: "
            + ", ".join(columnas)
        )
    if catalogo["Precio_Venta_USD"].le(0).any():
        raise ValueError("Precio_Venta_USD debe ser mayor que cero.")
    if not catalogo["Margen_Bruto_pct"].between(0, 1).all():
        raise ValueError(
            "Margen_Bruto_pct debe expresarse como decimal entre 0 y 1."
        )
    if catalogo["Costo_Almacenaje_Mes_USD_Unid"].lt(0).any():
        raise ValueError(
            "Costo_Almacenaje_Mes_USD_Unid no puede ser negativo."
        )
    if catalogo["Vida_Util_Meses"].le(0).any():
        raise ValueError("Vida_Util_Meses debe ser mayor que cero.")
    catalogo["Costo_Producto_Estimado_USD_Unid"] = (
        catalogo["Precio_Venta_USD"]
        * (1 - catalogo["Margen_Bruto_pct"])
    )
    catalogo["Margen_Bruto_USD_Unid"] = (
        catalogo["Precio_Venta_USD"]
        * catalogo["Margen_Bruto_pct"]
    )
    return catalogo


def enriquecer_pronostico_financiero(futuro, catalogo):
    """Añade economía unitaria; no altera el pronóstico de unidades."""
    catalogo = preparar_catalogo_financiero(catalogo)
    columnas = [
        "SKU", "Precio_Venta_USD", "Margen_Bruto_pct",
        "Costo_Producto_Estimado_USD_Unid", "Margen_Bruto_USD_Unid",
        "Costo_Almacenaje_Mes_USD_Unid", "Vida_Util_Meses",
    ]
    existentes = [col for col in columnas[1:] if col in futuro.columns]
    futuro = futuro.drop(columns=existentes).merge(
        catalogo[columnas], on="SKU", how="left", validate="many_to_one"
    )
    if futuro[columnas[1:]].isna().any().any():
        faltantes = sorted(
            futuro.loc[futuro["Precio_Venta_USD"].isna(), "SKU"].unique()
        )
        raise ValueError(
            "No existe información económica para: " + ", ".join(faltantes)
        )
    return futuro


def validar_plantilla(origen):
    """Comprueba hojas y columnas mínimas."""
    libro = abrir_excel(origen)
    errores = []
    for hoja, columnas in HOJAS_REQUERIDAS.items():
        if hoja not in libro.sheet_names:
            errores.append(f"Falta la hoja: {hoja}")
            continue
        actuales = set(pd.read_excel(libro, sheet_name=hoja, nrows=0))
        faltantes = sorted(columnas - actuales)
        if faltantes:
            errores.append(
                f"En {hoja} faltan columnas: {', '.join(faltantes)}"
            )
    return errores, libro


def limpiar_tablas_nuevas(ventas, catalogo):
    """Limpia ventas y catálogo ya cargados, conservando diagnóstico."""
    ventas = ventas.copy()
    catalogo = preparar_catalogo_financiero(catalogo)
    diagnostico = {
        "filas_originales": len(ventas),
        "duplicados_retirados": int(ventas.duplicated().sum()),
        "unidades_vacias": int(ventas["Unidades"].isna().sum()),
        "unidades_negativas": int(ventas["Unidades"].lt(0).sum()),
        "precios_vacios": int(ventas["Precio_Unitario_USD"].isna().sum()),
    }
    limpia = ventas.drop_duplicates().copy()
    columnas_texto = [
        "SKU", "Producto", "Categoria", "Canal", "Region",
    ]
    for columna in columnas_texto:
        limpia[columna] = limpia[columna].astype("string").str.strip()
    campos_vacios = {
        columna: int(
            (limpia[columna].isna() | limpia[columna].eq("")).sum()
        )
        for columna in columnas_texto
    }
    campos_vacios = {
        columna: cantidad
        for columna, cantidad in campos_vacios.items()
        if cantidad
    }
    if campos_vacios:
        descripcion = ", ".join(
            f"{columna}: {cantidad}"
            for columna, cantidad in campos_vacios.items()
        )
        raise ValueError(
            "Hay identificadores vacíos que no pueden inferirse: "
            + descripcion
        )
    limpia["SKU"] = limpia["SKU"].str.upper()
    canal_normalizado = limpia["Canal"].str.casefold()
    limpia["Canal"] = canal_normalizado.map(CANAL_CANONICO).fillna(
        limpia["Canal"]
    )
    region_normalizada = limpia["Region"].str.casefold()
    limpia["Region"] = region_normalizada.map(REGION_CANONICA).fillna(
        limpia["Region"]
    )
    limpia["Fecha"] = pd.to_datetime(limpia["Fecha"], errors="coerce")
    if limpia["Fecha"].isna().any():
        raise ValueError("Hay fechas que no pudieron convertirse.")

    limpia["Unidades"] = pd.to_numeric(
        limpia["Unidades"], errors="coerce"
    )
    limpia["Precio_Unitario_USD"] = pd.to_numeric(
        limpia["Precio_Unitario_USD"], errors="coerce"
    )
    limpia["Promocion"] = pd.to_numeric(
        limpia["Promocion"], errors="coerce"
    )
    promociones_invalidas = limpia.loc[
        ~limpia["Promocion"].isin([0, 1]), "Promocion"
    ]
    if len(promociones_invalidas):
        raise ValueError(
            "Promocion debe conservar valores 0 y 1. Si cambió su significado "
            "o formato, primero hay que definir cómo convertir la nueva columna."
        )

    consistencia_sku = limpia.groupby("SKU").agg(
        Productos=("Producto", "nunique"),
        Categorias=("Categoria", "nunique"),
    )
    sku_inconsistentes = consistencia_sku.loc[
        consistencia_sku["Productos"].gt(1)
        | consistencia_sku["Categorias"].gt(1)
    ]
    if len(sku_inconsistentes):
        raise ValueError(
            "Un mismo SKU aparece con varios productos o categorías: "
            + ", ".join(sku_inconsistentes.index.astype(str))
        )

    claves = ["Fecha", "SKU", "Canal", "Region"]
    claves_repetidas = limpia.duplicated(claves, keep=False)
    if claves_repetidas.any():
        raise ValueError(
            "Después de retirar copias exactas quedaron claves repetidas en "
            "Fecha + SKU + Canal + Region. Deben revisarse antes de sumar ventas."
        )

    precios = catalogo.set_index("SKU")["Precio_Venta_USD"]
    limpia["Precio_Unitario_USD"] = limpia[
        "Precio_Unitario_USD"
    ].fillna(limpia["SKU"].map(precios))
    if limpia["Precio_Unitario_USD"].isna().any():
        faltantes = sorted(
            limpia.loc[
                limpia["Precio_Unitario_USD"].isna(), "SKU"
            ].unique()
        )
        raise ValueError(
            "Quedaron precios sin referencia para: " + ", ".join(faltantes)
        )
    limpia.loc[limpia["Unidades"].lt(0), "Unidades"] = 0
    limpia = limpia.sort_values(["SKU", "Canal", "Region", "Fecha"])
    grupo = ["SKU", "Canal", "Region"]
    limpia["Mes"] = limpia["Fecha"].dt.month

    # Una pausa estructural no debe utilizarse como estacionalidad cero. Se
    # detecta de forma general: seis meses recientes completos en cero por SKU.
    agregado_sku = (
        limpia.groupby(["Fecha", "SKU"], as_index=False)
        .agg(Unidades_SKU=("Unidades", "sum"))
    )
    ultimas_seis = sorted(agregado_sku["Fecha"].unique())[-6:]
    pausa_sku = (
        agregado_sku.loc[agregado_sku["Fecha"].isin(ultimas_seis)]
        .groupby("SKU")["Unidades_SKU"]
        .agg(lambda s: len(s) == len(ultimas_seis) and s.eq(0).all())
    )
    skus_pausados_limpieza = pausa_sku.loc[pausa_sku].index
    limpia["Unidades_Referencia"] = limpia["Unidades"].mask(
        limpia["SKU"].isin(skus_pausados_limpieza)
        & limpia["Fecha"].isin(ultimas_seis)
    )

    temporal = (
        limpia.groupby(grupo)["Unidades_Referencia"]
        .transform(
            lambda serie: serie.interpolate(
                method="linear", limit_area="inside"
            )
        )
    )
    estacional = limpia.groupby(grupo + ["Mes"])[
        "Unidades_Referencia"
    ].transform("mean")
    propuesta_regular = pd.concat(
        [temporal, estacional], axis=1
    ).mean(axis=1)

    # Si el vacío estaba marcado como promoción, primero estimamos su base sin
    # campaña y luego aplicamos el efecto mediano observado del mismo SKU.
    unidades_sin_promocion = limpia["Unidades_Referencia"].mask(
        limpia["Promocion"].eq(1)
    )
    base_temporal = unidades_sin_promocion.groupby(
        [limpia[columna] for columna in grupo]
    ).transform(
        lambda serie: serie.interpolate(
            method="linear", limit_area="inside"
        )
    )
    base_estacional = unidades_sin_promocion.groupby(
        [limpia[columna] for columna in grupo + ["Mes"]]
    ).transform("mean")
    base_sin_promocion = pd.concat(
        [base_temporal, base_estacional], axis=1
    ).mean(axis=1)
    promocionales_observadas = (
        limpia["Promocion"].eq(1)
        & limpia["Unidades_Referencia"].notna()
        & base_sin_promocion.gt(0)
    )
    factores_observados = (
        limpia.loc[promocionales_observadas, "Unidades_Referencia"]
        / base_sin_promocion.loc[promocionales_observadas]
    )
    factores_por_sku = factores_observados.groupby(
        limpia.loc[promocionales_observadas, "SKU"]
    ).median()
    factor_global = (
        float(factores_observados.median())
        if len(factores_observados) else 1.0
    )
    factor_fila = limpia["SKU"].map(factores_por_sku).fillna(
        factor_global
    )
    propuesta_promocional = base_sin_promocion * factor_fila
    propuesta = propuesta_regular.where(
        limpia["Promocion"].eq(0), propuesta_promocional
    )
    limpia["Unidades_Modelo"] = limpia["Unidades"].fillna(propuesta)
    limpia["Unidades_Modelo"] = limpia["Unidades_Modelo"].fillna(
        estacional
    ).fillna(temporal)
    if limpia["Unidades_Modelo"].isna().any():
        raise ValueError(
            "Quedaron unidades sin referencias. Deben revisarse manualmente."
        )

    # Ajuste conservador de atípicos altos sin promoción: sólo se activa cuando
    # el dato supera por más de dos veces el límite IQR de su propia serie. El
    # valor original se conserva en Unidades y el reemplazo vive en
    # Unidades_Modelo con una bandera explícita.
    sin_promocion = limpia["Promocion"].eq(0)
    estadisticas = (
        limpia.loc[sin_promocion]
        .groupby(grupo)["Unidades_Modelo"]
        .quantile([0.25, 0.75])
        .unstack()
        .rename(columns={0.25: "Q1", 0.75: "Q3"})
    )
    estadisticas["Limite_Superior"] = (
        estadisticas["Q3"]
        + 1.5 * (estadisticas["Q3"] - estadisticas["Q1"])
    )
    limpia = limpia.merge(
        estadisticas[["Limite_Superior"]],
        left_on=grupo,
        right_index=True,
        how="left",
    )
    atipico_alto = (
        sin_promocion
        & limpia["Limite_Superior"].gt(0)
        & limpia["Unidades_Modelo"].gt(
            limpia["Limite_Superior"] * 2
        )
    )
    referencia_sin_atipico = limpia["Unidades_Modelo"].mask(atipico_alto)
    anterior_atipico = referencia_sin_atipico.groupby(
        [limpia[columna] for columna in grupo]
    ).shift(1)
    siguiente_atipico = referencia_sin_atipico.groupby(
        [limpia[columna] for columna in grupo]
    ).shift(-1)
    temporal_atipico = pd.concat(
        [anterior_atipico, siguiente_atipico], axis=1
    ).mean(axis=1)
    estacional_atipico = referencia_sin_atipico.groupby(
        [limpia[columna] for columna in grupo + ["Mes"]]
    ).transform("mean")
    propuesta_atipico = pd.concat(
        [temporal_atipico, estacional_atipico], axis=1
    ).mean(axis=1)
    limpia["Unidad_Fue_Ajustada_Atipico"] = atipico_alto
    limpia.loc[atipico_alto, "Unidades_Modelo"] = propuesta_atipico.loc[
        atipico_alto
    ]
    limpia = limpia.drop(columns=["Limite_Superior"])
    diagnostico["atipicos_altos_ajustados"] = int(atipico_alto.sum())
    diagnostico["filas_limpias"] = len(limpia)
    return limpia, diagnostico


def limpiar_archivo_nuevo(libro):
    """Lee y limpia una plantilla nueva."""
    ventas = pd.read_excel(libro, sheet_name="Ventas Historicas")
    catalogo = pd.read_excel(libro, sheet_name="Precios y Costos")
    return limpiar_tablas_nuevas(ventas, catalogo)


def auditar_reconciliacion_ventas(
    ventas_limpias, libro, ventas_crudas=None
):
    """Compara el detalle observado con las hojas consolidadas disponibles."""
    detalle = (
        ventas_limpias.groupby(["Fecha", "SKU"], as_index=False)
        .agg(Venta_Desde_Detalle=("Unidades", "sum"))
    )
    fuente = None
    if ventas_crudas is not None:
        fuente = ventas_crudas[["Fecha", "SKU", "Unidades"]].copy()
        fuente["Fecha"] = pd.to_datetime(fuente["Fecha"], errors="coerce")
        fuente["Unidades"] = pd.to_numeric(
            fuente["Unidades"], errors="coerce"
        )
        fuente.loc[fuente["Unidades"].lt(0), "Unidades"] = 0
        fuente = (
            fuente.groupby(["Fecha", "SKU"], as_index=False)
            .agg(Venta_Desde_Fuente=("Unidades", "sum"))
        )
    resultados = {}
    for hoja, clave in [
        ("Pronostico vs Real", "pronostico_real"),
        ("Inventario y Quiebres", "inventario"),
    ]:
        if hoja not in libro.sheet_names:
            resultados[f"reconciliacion_{clave}_disponible"] = False
            continue
        tabla_consolidada_completa = pd.read_excel(libro, sheet_name=hoja)
        consolidado = tabla_consolidada_completa.copy()
        columnas = {"Fecha", "SKU", "Venta_Real"}
        if not columnas.issubset(consolidado.columns):
            resultados[f"reconciliacion_{clave}_disponible"] = False
            continue
        consolidado = consolidado[["Fecha", "SKU", "Venta_Real"]].copy()
        consolidado["Fecha"] = pd.to_datetime(
            consolidado["Fecha"], errors="coerce"
        )
        consolidado["Venta_Real"] = pd.to_numeric(
            consolidado["Venta_Real"], errors="coerce"
        )
        comparacion = consolidado.merge(
            detalle, on=["Fecha", "SKU"], how="left", validate="one_to_one"
        )
        ambos_vacios = (
            comparacion["Venta_Real"].isna()
            & comparacion["Venta_Desde_Detalle"].isna()
        )
        diferencia = (
            comparacion["Venta_Desde_Detalle"]
            - comparacion["Venta_Real"]
        )
        no_coincide = ~(ambos_vacios | diferencia.abs().le(0.01))
        resultados[f"reconciliacion_{clave}_disponible"] = True
        resultados[f"reconciliacion_{clave}_diferencias"] = int(
            no_coincide.sum()
        )
        resultados[f"reconciliacion_{clave}_detalle"] = (
            comparacion.loc[
                no_coincide,
                ["Fecha", "SKU", "Venta_Real", "Venta_Desde_Detalle"],
            ]
            .assign(Diferencia=lambda x: x["Venta_Desde_Detalle"] - x["Venta_Real"])
            .sort_values(["Fecha", "SKU"])
        )
        if fuente is not None:
            comparacion_fuente = consolidado.merge(
                fuente,
                on=["Fecha", "SKU"],
                how="left",
                validate="one_to_one",
            )
            ambos_vacios_fuente = (
                comparacion_fuente["Venta_Real"].isna()
                & comparacion_fuente["Venta_Desde_Fuente"].isna()
            )
            diferencia_fuente = (
                comparacion_fuente["Venta_Desde_Fuente"]
                - comparacion_fuente["Venta_Real"]
            )
            no_coincide_fuente = ~(
                ambos_vacios_fuente | diferencia_fuente.abs().le(0.01)
            )
            resultados[f"reconciliacion_{clave}_fuente_diferencias"] = int(
                no_coincide_fuente.sum()
            )
            resultados[f"reconciliacion_{clave}_fuente_detalle"] = (
                comparacion_fuente.loc[
                    no_coincide_fuente,
                    ["Fecha", "SKU", "Venta_Real", "Venta_Desde_Fuente"],
                ]
                .assign(
                    Diferencia=lambda x: (
                        x["Venta_Desde_Fuente"] - x["Venta_Real"]
                    )
                )
                .sort_values(["Fecha", "SKU"])
            )
        if clave == "inventario":
            columnas_inventario = {
                "Stock_Inicial", "Venta_Real", "Stock_Final",
                "Venta_Perdida_Unid", "Dias_Cobertura",
            }
            if columnas_inventario.issubset(
                tabla_consolidada_completa.columns
            ):
                inventario_auditado = tabla_consolidada_completa.copy()
                for columna in columnas_inventario:
                    inventario_auditado[columna] = pd.to_numeric(
                        inventario_auditado[columna], errors="coerce"
                    )
                stock_calculado = (
                    inventario_auditado["Stock_Inicial"]
                    - inventario_auditado["Venta_Real"]
                ).clip(lower=0)
                perdida_calculada = (
                    inventario_auditado["Venta_Real"]
                    - inventario_auditado["Stock_Inicial"]
                ).clip(lower=0)
                cobertura_calculada = (
                    inventario_auditado["Stock_Final"]
                    / inventario_auditado["Venta_Real"].replace(0, pd.NA)
                    * 30
                )
                resultados["inventario_formula_stock_diferencias"] = int(
                    (inventario_auditado["Stock_Final"] - stock_calculado)
                    .abs().gt(0.01).sum()
                )
                resultados["inventario_formula_perdida_diferencias"] = int(
                    (
                        inventario_auditado["Venta_Perdida_Unid"]
                        - perdida_calculada
                    ).abs().gt(0.01).sum()
                )
                cobertura_coincide = (
                    (
                        inventario_auditado["Dias_Cobertura"].isna()
                        & cobertura_calculada.isna()
                    )
                    | (
                        inventario_auditado["Dias_Cobertura"]
                        - cobertura_calculada
                    ).abs().le(0.11)
                )
                resultados["inventario_formula_cobertura_diferencias"] = int(
                    (~cobertura_coincide).sum()
                )
    return resultados
